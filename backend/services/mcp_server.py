"""
The Saga MCP server: the same tools the Director uses, for the user's own AI (Claude, ChatGPT,
Gemini...) to build games from outside the editor.

It runs inside the Saga server (mounted at /mcp by backend/main.py), so it shares the projects,
the art and sound jobs and their locks with the editor. Connect a client to
http://127.0.0.1:8070/mcp/ (streamable HTTP). It only answers this machine: the tools write
into the projects and there is no login yet.

Every tool takes `project` (the project's name) on top of the Director's own arguments, since an
outside AI is not "inside" a project the way the editor is.
"""

import json
import logging
from typing import Any, Dict, List

from mcp import types
from mcp.server.lowlevel import Server

from backend.services import saga_tools
from backend.services.project_service import ROOT_DIR, project_service

logger = logging.getLogger(__name__)

INSTRUCTIONS = (
    "Você está construindo um adventure de texto e imagem no Saga Engine, com as ferramentas deste servidor. "
    "Comece com list_projects (ou create_project) e leia get_guide uma vez: ele explica a ficha do jogo, "
    "a linguagem de scripts SES e como fazer a arte. Toda ferramenta pede `project` = o nome do projeto. "
    "Arte e som são lentos: create_scene_art leva ~8 min; start_game_art e start_game_sound rodam em segundo "
    "plano, e get_job_status diz quando terminaram."
)

PROJECT_ARG = {"type": "string", "description": "nome do projeto (veja list_projects)"}

# Tools of the MCP server itself (the rest come from saga_tools, shared with the Director).
OWN_TOOLS: List[Dict[str, Any]] = [
    {"name": "list_projects", "description": "Os projetos (jogos) que existem neste Saga.",
     "schema": {"type": "object", "properties": {}}, "read_only": True},
    {"name": "create_project", "description": "Cria um projeto vazio com esse nome, para começar um jogo novo.",
     "schema": {"type": "object", "properties": {"name": {"type": "string", "description": "nome do jogo"}},
                "required": ["name"]}, "read_only": False},
    {"name": "get_guide", "description": ("Como construir um jogo no Saga: o jeito de trabalhar, a linguagem de "
                                          "scripts SES e o formato da ficha. Leia uma vez antes de começar."),
     "schema": {"type": "object", "properties": {}}, "read_only": True},
    {"name": "get_job_status", "description": ("Andamento da arte ou do som que start_game_art/start_game_sound "
                                               "começaram: se ainda roda, as últimas linhas do log e o que falta."),
     "schema": {"type": "object", "properties": {
         "project": PROJECT_ARG,
         "kind": {"type": "string", "enum": ["arte", "som"], "description": "arte ou som"}},
         "required": ["project", "kind"]}, "read_only": True},
]


def _with_project(schema: Dict[str, Any]) -> Dict[str, Any]:
    schema = json.loads(json.dumps(schema))
    schema.setdefault("properties", {})
    schema["properties"] = {"project": PROJECT_ARG, **schema["properties"]}
    schema["required"] = ["project"] + [r for r in schema.get("required", []) if r != "project"]
    return schema


def tools() -> List[types.Tool]:
    out = []
    for t in OWN_TOOLS:
        out.append(types.Tool(name=t["name"], description=t["description"], inputSchema=t["schema"],
                              annotations=types.ToolAnnotations(readOnlyHint=t["read_only"])))
    for t in saga_tools.catalog():
        out.append(types.Tool(name=t["name"], description=t["description"], inputSchema=_with_project(t["schema"]),
                              annotations=types.ToolAnnotations(readOnlyHint=t["read_only"])))
    return out


def list_projects() -> List[str]:
    root = ROOT_DIR / "projects"
    return sorted(p.name for p in root.iterdir() if (p / "project.json").is_file()) if root.is_dir() else []


async def call(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    args = dict(args or {})
    if name == "list_projects":
        return {"projects": list_projects()}
    if name == "get_guide":
        return {"guide": saga_tools.GUIDE}
    if name == "create_project":
        try:
            project_service.create_project(str(args.get("name") or "").strip())
        except ValueError as e:
            return {"error": str(e)}
        return {"created": args.get("name")}
    project = str(args.pop("project", "") or "").strip()
    if not project:
        return {"error": "falta o argumento `project` (o nome do projeto; veja list_projects)"}
    if project not in list_projects():
        return {"error": f"o projeto {project!r} não existe. Projetos: {', '.join(list_projects()) or 'nenhum'}"}
    if name == "get_job_status":
        from backend.api.routes import blueprint as routes
        status = routes.art_status if args.get("kind") != "som" else routes.sound_status
        return await status(project)
    return await saga_tools.run_tool(project, name, args)


async def _list_tools(ctx, params) -> types.ListToolsResult:
    return types.ListToolsResult(tools=tools())


async def _call_tool(ctx, params: types.CallToolRequestParams) -> types.CallToolResult:
    result = await call(params.name, params.arguments or {})
    image = result.pop("_image", None) if isinstance(result, dict) else None   # render_scene's picture
    logger.info("mcp %s -> %s", params.name, json.dumps(result, ensure_ascii=False, default=str)[:200])
    text = json.dumps(result, ensure_ascii=False, default=str, indent=1)
    content: List[Any] = [types.TextContent(text=text)]
    if image:
        content.append(types.ImageContent(data=image, mimeType="image/jpeg"))
    return types.CallToolResult(content=content, isError=isinstance(result, dict) and "error" in result)


server = Server("saga", version="0.1.0", title="Saga Engine",
                description="Cria e edita adventures do Saga Engine", instructions=INSTRUCTIONS,
                on_list_tools=_list_tools, on_call_tool=_call_tool)

_http_app = server.streamable_http_app(streamable_http_path="/", host="127.0.0.1")


async def app(scope, receive, send):
    """The MCP endpoint, for this machine only (the Saga server listens on every interface)."""
    client = (scope.get("client") or ("", 0))[0]
    if scope["type"] == "http" and client not in ("127.0.0.1", "::1", "localhost"):
        await send({"type": "http.response.start", "status": 403,
                    "headers": [(b"content-type", b"text/plain; charset=utf-8")]})
        await send({"type": "http.response.body", "body": "MCP do Saga: só neste computador".encode("utf-8")})
        return
    await _http_app(scope, receive, send)


def run():
    """The session manager's task group; backend/main.py keeps it open for the server's lifetime."""
    return server.session_manager.run()
