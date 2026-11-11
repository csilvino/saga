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
from backend.ses import blueprint, director_tools
from backend.ses.language import REFERENCE

logger = logging.getLogger(__name__)

SAGA_API_URL = "http://127.0.0.1:8070"
MAX_STEPS = 30

SYSTEM_PROMPT = """Você é o Diretor do Saga Engine: constrói adventures em texto dentro do editor, usando as ferramentas.

Como trabalhar:
- Execute, não descreva.
- JOGO INTEIRO ("crie um jogo de mistério", "um adventure como X"): escreva a FICHA do jogo (formato
  abaixo) e chame check_blueprint. Ela aponta furos de lógica, roda a sua solução e cada morte, e um
  jogador automático tenta vencer sozinho. Corrija a ficha e confira de novo até "ok": true, e só então
  chame save_blueprint, que monta o projeto inteiro de uma vez. Mudanças grandes num jogo que tem ficha:
  get_blueprint, edite, confira e salve de novo (a arte já feita é mantida). A arte do jogo inteiro:
  start_game_art (roda sozinha em segundo plano, horas).
- Ajustes pequenos (uma cena, um objeto, um script): use as ferramentas diretas abaixo.
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
- Arte só quando o usuário pedir (lenta: ~8 min por cena). Use create_scene_art, uma cena por vez:
  ela gera o cenário com os objetos fixos pintados, os sprites dos itens que podem sumir/aparecer
  (pegáveis, escondidos, personagens) e posiciona tudo. Primeira cena sem reference_scene; as
  outras com reference_scene = a primeira. Se ela relatar problemas (objeto que não aparece),
  chame de novo para a mesma cena. Antes da arte, confira que cada objeto tem descrição visual.
- Objetos pintados que mudam de estado (porta que abre, lâmpada que acende, gaveta aberta): depois da
  arte da cena, crie a variante com create_background_variant, usando a mesma flag que o script
  marca (ex.: when "flag(porta_aberta)", change "a porta de ferro agora está aberta, escada visível").
- Se o cenário saiu contradizendo a história (lâmpada acesa que devia estar apagada, porta aberta
  que devia estar trancada, fogo onde não há), corrija com edit_scene_background: ela edita a mesma
  imagem e mantém as áreas clicáveis. O gerador ignora negações no prompt; a edição não.

""" + REFERENCE + 2 * chr(10) + blueprint.REFERENCE

BLUEPRINT_TOOLS = {"get_blueprint", "check_blueprint", "save_blueprint", "start_game_art"}
READ_ONLY = director_tools.READ_ONLY | {"get_blueprint", "check_blueprint", "start_game_art"}

IMAGE_TOOLS = [
    types.FunctionDeclaration(
        name="get_blueprint",
        description="A ficha (YAML) do jogo deste projeto. Se o projeto ainda não tem ficha, devolve um rascunho tirado do projeto atual.",
        parameters=None),
    types.FunctionDeclaration(
        name="check_blueprint",
        description=("Confere uma ficha sem salvar nada: erros de script, cenas sem caminho, flags que ninguém marca, "
                     "objetos escondidos que nunca aparecem, itens sem uso; roda a solução, as mortes e um jogador "
                     "automático. Devolve o relatório."),
        parameters=types.Schema(type="OBJECT", properties={
            "text": types.Schema(type="STRING", description="a ficha inteira, em YAML"),
        }, required=["text"])),
    types.FunctionDeclaration(
        name="save_blueprint",
        description=("Confere a ficha e, se não houver erros, monta o projeto inteiro a partir dela (cenas, saídas, objetos, "
                     "scripts) e a guarda no projeto. A arte já feita das cenas e objetos que mantêm o nome é preservada."),
        parameters=types.Schema(type="OBJECT", properties={
            "text": types.Schema(type="STRING", description="a ficha inteira, em YAML"),
        }, required=["text"])),
    types.FunctionDeclaration(
        name="start_game_art",
        description=("Começa a gerar em segundo plano toda a arte que falta: cenas (a de referência primeiro) e variantes. "
                     "Demora horas; devolve na hora. Use só quando o usuário pedir a arte."),
        parameters=None),
    types.FunctionDeclaration(
        name="create_scene_art",
        description=("Cria a arte completa de UMA cena: cenário com os objetos fixos pintados e clicáveis, "
                     "sprites (fundo transparente) dos objetos pegáveis/escondidos/personagens, posicionados. "
                     "Lenta (~8 min). Devolve o que foi feito e problemas."),
        parameters=types.Schema(type="OBJECT", properties={
            "scene": types.Schema(type="STRING", description="id ou nome da cena"),
            "style": types.Schema(type="STRING", description="direção de arte (pode ser em português): época, luz, clima, paleta"),
            "reference_scene": types.Schema(type="STRING", description="cena já com arte cujo estilo deve ser seguido"),
            "keep_background": types.Schema(type="BOOLEAN", description="true: mantém o cenário atual e refaz só sprites e posições"),
        }, required=["scene"])),
    types.FunctionDeclaration(
        name="edit_scene_background",
        description=("Corrige o cenário atual de uma cena editando a própria imagem (mesmo enquadramento, "
                     "áreas clicáveis continuam valendo). Lenta (~5 min)."),
        parameters=types.Schema(type="OBJECT", properties={
            "scene": types.Schema(type="STRING", description="id ou nome da cena"),
            "change": types.Schema(type="STRING", description="o que corrigir (pode ser em português)"),
        }, required=["scene", "change"])),
    types.FunctionDeclaration(
        name="create_background_variant",
        description=("Cria uma versão do cenário de uma cena com algo mudado (porta aberta, lâmpada acesa), "
                     "mesmo enquadramento; o jogo mostra essa versão enquanto a condição SES for verdadeira. "
                     "Lenta (~5 min)."),
        parameters=types.Schema(type="OBJECT", properties={
            "scene": types.Schema(type="STRING", description="id ou nome da cena (já com arte)"),
            "when": types.Schema(type="STRING", description="condição SES, ex.: flag(porta_aberta)"),
            "change": types.Schema(type="STRING", description="o que muda na imagem (pode ser em português)"),
        }, required=["scene", "when", "change"])),
    types.FunctionDeclaration(
        name="generate_image_and_set_as_background",
        description=("Gera uma imagem de fundo e aplica numa cena (lenta: minutos; só se o usuário pedir arte). "
                     "Para várias cenas: gere a primeira sem referência e as outras com reference_scene = a primeira, "
                     "para manter o mesmo estilo. Uma cena por vez."),
        parameters=types.Schema(type="OBJECT", properties={
            "scene": types.Schema(type="STRING", description="id ou nome da cena"),
            "prompt": types.Schema(type="STRING", description="em INGLÊS: o que a imagem mostra (lugar, objetos, luz, estilo); sem personagens nem texto"),
            "reference_scene": types.Schema(type="STRING", description="cena (já com imagem) cujo estilo, paleta e luz devem ser seguidos"),
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
                if call.name not in READ_ONLY and "error" not in result:
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
            if name in BLUEPRINT_TOOLS:
                return await self.blueprint_tool(name, args)
            if name == "create_scene_art":
                from backend.services import scene_art
                try:
                    return await scene_art.create_scene_art(
                        self.project_name, args.get("scene"), args.get("style", ""),
                        args.get("reference_scene", ""), bool(args.get("keep_background")))
                except scene_art.ArtError as e:
                    return {"error": str(e)}
            if name == "edit_scene_background":
                from backend.services import scene_art
                try:
                    return await scene_art.edit_background(self.project_name, args.get("scene"), args.get("change", ""))
                except scene_art.ArtError as e:
                    return {"error": str(e)}
            if name == "create_background_variant":
                from backend.services import scene_art
                try:
                    return await scene_art.create_variant(
                        self.project_name, args.get("scene"), args.get("when", ""), args.get("change", ""))
                except scene_art.ArtError as e:
                    return {"error": str(e)}
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

    async def blueprint_tool(self, name, args):
        from backend.api.routes import blueprint as routes
        if name == "get_blueprint":
            return await routes.get_blueprint(self.project_name)
        if name == "start_game_art":
            job = await routes.start_art(self.project_name)
            return {"started": True, "running": job["running"],
                    **blueprint.art_status(project_service.load_project(self.project_name))}
        text = args.get("text") or ""
        save = name == "save_blueprint"
        if save and routes.ART_JOBS.get(self.project_name, {}).get("running"):
            return {"error": "a arte deste jogo está sendo gerada; espere terminar para salvar a ficha"}
        report = await asyncio.to_thread(blueprint.build, self.project_name, text, save)
        if "explorador" in report:                  # the model needs the verdict, not the 56 commands
            report["explorador"]["caminho"] = len(report["explorador"]["caminho"])
        return report

    # --- images (existing endpoints) ----------------------------------------------------------

    async def post(self, path, payload):
        async with httpx.AsyncClient(timeout=1200) as client:   # local images take minutes
            r = await client.post(SAGA_API_URL + path, json=payload)
            if r.status_code >= 400:
                if "limit: 0" in r.text:
                    # free-tier keys have no quota at all for image models: waiting does not help
                    return {"error": "o modelo de imagem configurado não tem cota no plano gratuito desta chave "
                                     "(limite 0). Para gerar imagens é preciso ativar o faturamento no Google "
                                     "AI Studio ou usar a geração local. Explique isso ao usuário; não tente de novo."}
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
