"""
The AI director: a Gemini chat with function calling that builds the adventure in the editor.

- Text-adventure tools (backend/ses/director_tools.py) run in-process on project.json.
- Image tools call the existing image endpoints of this same server.
- One chat per project is kept in memory, so the director remembers the conversation while the
  editor is open (POST /api/orchestrator/reset forgets it). Calls are async: the server keeps
  answering the editor while the model thinks.
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, Optional

import httpx
from google import genai
from google.genai import types

from backend.config.user_settings import get_gemini_model
from backend.services.project_service import project_service
from backend.ses import director_tools
from backend.ses.language import REFERENCE

logger = logging.getLogger(__name__)

SAGA_API_URL = "http://127.0.0.1:8070"
MAX_STEPS = 30

SYSTEM_PROMPT = """Você é o Diretor do Saga Engine: constrói adventures em texto dentro do editor, usando as ferramentas.

Como trabalhar:
- Execute, não descreva. Para pedidos grandes ("crie um jogo de mistério"), planeje rapidamente
  (cenas, objetos, um puzzle com solução) e construa tudo com as ferramentas.
- Use ids ou nomes nas ferramentas. Se não sabe o que existe, chame get_project.
- Saídas: connect_scenes para passagens abertas. Passagem que abre durante o jogo: não conecte;
  use 'link direção to cena' no script que a abre.
- Lógica (portas, puzzles, personagens, final) vai em scripts SES. Se a ferramenta devolver
  script_errors, corrija e chame de novo. Avisos sobre objetos que "não existem ainda" somem
  depois que você cria esses objetos.
- Todo jogo precisa de um final: um 'end "texto"' alcançável.
- Antes de dizer que terminou, rode playtest com a solução e confira o transcript. Se algo
  falhar, conserte e teste de novo.
- Responda ao usuário em português, curto: o que foi feito e como jogar/vencer.
- Imagens (generate_image_and_set_as_background, generate_sprite_for_object) só quando o
  usuário pedir arte; elas são lentas e custam créditos.

""" + REFERENCE

IMAGE_TOOLS = [
    types.FunctionDeclaration(
        name="generate_image_and_set_as_background",
        description="Gera uma imagem de fundo e aplica numa cena (lento; só se o usuário pedir arte).",
        parameters=types.Schema(type="OBJECT", properties={
            "scene": types.Schema(type="STRING", description="id ou nome da cena"),
            "prompt": types.Schema(type="STRING", description="o que a imagem deve mostrar"),
            "reference_scene": types.Schema(type="STRING", description="cena cujo estilo deve ser seguido"),
        }, required=["scene", "prompt"])),
    types.FunctionDeclaration(
        name="generate_sprite_for_object",
        description="Gera um sprite para um objeto e aplica nele (lento; só se o usuário pedir arte).",
        parameters=types.Schema(type="OBJECT", properties={
            "object": types.Schema(type="STRING", description="id ou nome do objeto"),
            "description": types.Schema(type="STRING", description="aparência do sprite"),
        }, required=["object", "description"])),
    types.FunctionDeclaration(
        name="analyze_scene_background",
        description="Descreve o estilo visual da imagem de fundo de uma cena (para gerar outra no mesmo estilo).",
        parameters=types.Schema(type="OBJECT", properties={
            "scene": types.Schema(type="STRING", description="id ou nome da cena"),
        }, required=["scene"])),
]


def _schema(kind, desc):
    if kind == "ARRAY":
        return types.Schema(type="ARRAY", items=types.Schema(type="STRING"), description=desc or None)
    return types.Schema(type=kind, description=desc or None)


def tool_declarations():
    decls = []
    for name, (_, desc, params, required) in director_tools.TOOLS.items():
        props = {k: _schema(kind, d) for k, (kind, d) in params.items()}
        decls.append(types.FunctionDeclaration(
            name=name, description=desc,
            parameters=types.Schema(type="OBJECT", properties=props, required=required) if props else None))
    return [types.Tool(function_declarations=decls + IMAGE_TOOLS)]


def _plain(value):
    """Function-call args from the SDK (MapComposite, RepeatedComposite) -> plain Python."""
    if hasattr(value, "items"):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)) or (hasattr(value, "__iter__") and not isinstance(value, (str, bytes))):
        return [_plain(v) for v in value]
    return value


class DirectorSession:
    def __init__(self, api_key: str, project_name: str):
        self.project_name = project_name
        self.model = get_gemini_model()
        self.client = genai.Client(api_key=api_key)
        self.chat = self.client.aio.chats.create(
            model=self.model,
            config=types.GenerateContentConfig(tools=tool_declarations(), system_instruction=SYSTEM_PROMPT,
                                               automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)))
        self.lock = asyncio.Lock()

    async def send(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        async with self.lock:
            return await self._send(text, context or {})

    async def _send(self, text, context):
        header = [f"[projeto: {self.project_name}"]
        if context.get("scene_id"):
            header.append(f"cena aberta no editor: {context['scene_id']}")
        if context.get("selected_object_id"):
            header.append(f"objeto selecionado: {context['selected_object_id']}")
        message = "; ".join(header) + "]\n" + text
        log = []
        changed = False
        try:
            response = await self._send_message(message)
        except Exception as e:
            return {"text_response": f"Erro da IA: {short_error(e)}", "tool_responses": [], "project_changed": False}
        for _ in range(MAX_STEPS):
            parts = (response.candidates[0].content.parts if response.candidates and response.candidates[0].content
                     else None) or []
            calls = [p.function_call for p in parts if p.function_call and p.function_call.name]
            if not calls:
                reply = "".join(p.text for p in parts if getattr(p, "text", None)).strip()
                return {"text_response": reply or "Feito.", "tool_responses": log, "project_changed": changed}
            results = []
            for call in calls:
                args = _plain(call.args or {})
                result = await self.run_tool(call.name, args)
                if call.name not in director_tools.READ_ONLY and "error" not in result:
                    changed = True
                logger.info("director %s %s -> %s", call.name, json.dumps(args, ensure_ascii=False)[:200],
                            json.dumps(result, ensure_ascii=False)[:200])
                log.append({"tool": call.name, "args": args, "result": result})
                results.append(types.Part.from_function_response(name=call.name, response=result))
            try:
                response = await self._send_message(results)
            except Exception as e:
                # what was done stays done; tell the user and let them say "continue"
                return {"text_response": f"Erro da IA no meio do trabalho ({short_error(e)}). "
                                         f"{len(log)} ações já foram feitas; peça para continuar.",
                        "tool_responses": log, "project_changed": changed}
        return {"text_response": f"Parei depois de {MAX_STEPS} passos; peça para continuar.",
                "tool_responses": log, "project_changed": changed}

    async def _send_message(self, payload, retries=5):
        """send_message, waiting out the per-minute quota (free tier: 15 requests/minute)."""
        for attempt in range(retries + 1):
            try:
                return await self.chat.send_message(payload)
            except Exception as e:
                text = str(e)
                if attempt == retries or not ("429" in text or "RESOURCE_EXHAUSTED" in text or "503" in text):
                    raise
                if "429" in text and "per day" in text.lower():
                    raise
                m = re.search(r"retry in ([\d.]+)s", text) or re.search(r"retryDelay'?:\s*'(\d+)s", text)
                wait = min(float(m.group(1)) + 1 if m else 10 * (attempt + 1), 65)
                logger.warning("Gemini %s; tentando de novo em %.0fs", text[:60], wait)
                await asyncio.sleep(wait)

    async def run_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if name in director_tools.TOOLS:
                project = project_service.load_project(self.project_name)
                result = director_tools.run_tool(project, name, args)
                if name not in director_tools.READ_ONLY and "error" not in result:
                    project_service.save_project_data(self.project_name, project)
                return result
            if name == "generate_image_and_set_as_background":
                return await self.generate_background(args)
            if name == "generate_sprite_for_object":
                return await self.generate_sprite(args)
            if name == "analyze_scene_background":
                project = project_service.load_project(self.project_name)
                sid = director_tools._scene(project, args.get("scene"))
                return await self.post("/api/genai/analyze-scene", {"project_name": self.project_name, "scene_id": sid})
            return {"error": f"ferramenta desconhecida: {name}"}
        except director_tools.ToolError as e:
            return {"error": str(e)}
        except Exception as e:                     # the model gets the error and can try something else
            logger.exception("tool %s failed", name)
            return {"error": f"{type(e).__name__}: {e}"}

    # --- images (existing endpoints) ----------------------------------------------------------

    async def post(self, path, payload):
        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(SAGA_API_URL + path, json=payload)
            if r.status_code >= 400:
                return {"error": f"{path} respondeu {r.status_code}: {r.text[:300]}"}
            return r.json()

    def background_path(self, project, sid):
        for obj in project["scenes"][sid].get("objects", []):
            if obj.get("type") == "background" and obj.get("sprite"):
                return obj["sprite"].split("?")[0]
        return None

    async def generate_background(self, args):
        project = project_service.load_project(self.project_name)
        sid = director_tools._scene(project, args.get("scene"))
        payload = {"project_name": self.project_name, "output_type": "backgrounds", "width": 1920, "height": 1080,
                   "prompt": f"2D painted point-and-click adventure background, {args.get('prompt', '')}",
                   "negative_prompt": "text, watermark, blurry, distorted"}
        if args.get("reference_scene"):
            ref = self.background_path(project, director_tools._scene(project, args["reference_scene"]))
            if ref:
                payload["reference_image_path"] = ref
        image = await self.post("/api/genai/generate-image", payload)
        if not image.get("image_path"):
            return image if "error" in image else {"error": f"sem imagem: {image}"}
        return await self.post("/api/scenes/set-background", {
            "project_name": self.project_name, "scene_id": sid, "background_path": image["image_path"]})

    async def generate_sprite(self, args):
        image = await self.post("/api/genai/generate-image", {
            "project_name": self.project_name, "output_type": "sprites", "width": 512, "height": 512,
            "prompt": f"isolated game sprite of {args.get('description', '')}, transparent background, 2D illustration",
            "negative_prompt": "background, scenery, text, watermark"})
        if not image.get("image_path"):
            return image if "error" in image else {"error": f"sem imagem: {image}"}
        project = project_service.load_project(self.project_name)
        oid, _, obj = director_tools._object(project, args.get("object"))
        obj["sprite"] = image["image_path"]
        project_service.save_project_data(self.project_name, project)
        return {"object": oid, "sprite": image["image_path"]}


def short_error(e: Exception) -> str:
    text = str(e)
    if "RESOURCE_EXHAUSTED" in text or "429" in text:
        return "limite de uso da Gemini atingido (cota por minuto ou por dia); tente em instantes ou troque o modelo"
    if "API_KEY_INVALID" in text:
        return "chave da Gemini inválida"
    return text[:300]


_sessions: Dict[str, DirectorSession] = {}


def get_session(api_key: str, project_name: str) -> DirectorSession:
    s = _sessions.get(project_name)
    if s is None or s.model != get_gemini_model():
        s = _sessions[project_name] = DirectorSession(api_key, project_name)
    return s


def reset_session(project_name: Optional[str] = None):
    if project_name:
        _sessions.pop(project_name, None)
    else:
        _sessions.clear()
