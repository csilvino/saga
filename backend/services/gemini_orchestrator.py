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

from google import genai
from google.genai import types

from backend.config.user_settings import get_gemini_model
from backend.services.project_service import project_service
from backend.ses import director_tools
from backend.services import saga_tools
from backend.services.saga_tools import GUIDE, IMAGE_TOOLS, READ_ONLY

logger = logging.getLogger(__name__)

MAX_STEPS = 30

SYSTEM_PROMPT = 'Você é o Diretor do Saga Engine: constrói adventures em texto dentro do editor, usando as ferramentas.' + "\n" + GUIDE


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
        result = await saga_tools.run_tool(self.project_name, name, args)
        if isinstance(result, dict) and result.pop("_image", None):     # a picture is no text for the chat
            result["image"] = "imagem gerada, mas o Diretor não recebe imagens; quem confere é o usuário no editor"
        return result


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
