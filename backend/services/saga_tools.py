"""
Everything an AI can do to a Saga game, in one place, for every way an AI reaches the engine:

- the Director (gemini_orchestrator): a Gemini chat inside the editor, with the user's Gemini key;
- the MCP server (mcp_server): the user's own AI (Claude, ChatGPT, Gemini...) from outside.

Both describe the tools from the same declarations and run them through run_tool(), so a tool
behaves the same whoever calls it, and a fix here fixes both.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx
from google.genai import types

from backend.services.project_service import project_service
from backend.ses import blueprint, director_tools
from backend.ses.language import REFERENCE

logger = logging.getLogger(__name__)

SAGA_API_URL = "http://127.0.0.1:8070"

# How to build a game well, for whichever AI is building it (the Director adds who it is on top).
RULES = """
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
- create_scene_art e create_background_variant já revisam e corrigem a imagem sozinhas; o que
  sobrar vem em "problems". Para conferir uma cena feita antes, use review_scene_art (fix=true corrige).
"""

GUIDE = RULES + "\n" + REFERENCE + 2 * chr(10) + blueprint.REFERENCE

BLUEPRINT_TOOLS = {"get_blueprint", "check_blueprint", "save_blueprint", "start_game_art", "start_game_sound"}
READ_ONLY = director_tools.READ_ONLY | {"get_blueprint", "check_blueprint", "start_game_art", "start_game_sound"}
ART_TOOLS = {"create_scene_art", "edit_scene_background", "create_background_variant", "review_scene_art"}

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
        name="start_game_sound",
        description=("Começa a gerar em segundo plano os sons que faltam (som ambiente das cenas, sons de objetos e os "
                     "play \"...\" dos scripts), a partir da ficha. Minutos; devolve na hora. Só quando o usuário pedir."),
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
            "only_new_sprites": types.Schema(type="BOOLEAN", description=(
                "true: mantém o cenário e todos os sprites já feitos e faz só os dos objetos que ainda não têm "
                "sprite (um objeto criado depois da arte da cena). Depois ajuste com place_object.")),
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
        name="review_scene_art",
        description=("Revisa a arte de uma cena como um jogador veria: o cenário mostra os objetos fixos, "
                     "concorda com o texto e com o estado inicial; cada variante mostra a mudança e nada mais. "
                     "fix=true também corrige (GPU, ~5 min por correção). Devolve o que ainda está errado."),
        parameters=types.Schema(type="OBJECT", properties={
            "scene": types.Schema(type="STRING", description="id ou nome da cena (já com arte)"),
            "fix": types.Schema(type="BOOLEAN", description="true: corrige o que achar"),
        }, required=["scene"])),
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
    types.FunctionDeclaration(
        name="render_scene",
        description=("A cena como o jogador a vê: o cenário (ou a variante que vale com essas flags) e os sprites "
                     "no lugar; objetos ainda sem imagem aparecem como caixa vermelha. Use depois de mexer na arte "
                     "ou nas posições para CONFERIR o resultado. Rápido."),
        parameters=types.Schema(type="OBJECT", properties={
            "scene": types.Schema(type="STRING", description="id ou nome da cena"),
            "flags": types.Schema(type="ARRAY", items=types.Schema(type="STRING"),
                                  description="flags ligadas, para ver uma variante (ex.: porta_aberta)"),
        }, required=["scene"])),
    types.FunctionDeclaration(
        name="import_background",
        description=("Usa uma imagem feita fora do Saga (outro gerador, um arquivo do criador) como cenário da cena, "
                     "cortada em 16:9; com `when`, como a variante mostrada enquanto essa condição SES valer."),
        parameters=types.Schema(type="OBJECT", properties={
            "scene": types.Schema(type="STRING", description="id ou nome da cena"),
            "source": types.Schema(type="STRING", description="URL http(s) ou caminho de arquivo neste computador (png, jpg, webp)"),
            "when": types.Schema(type="STRING", description="opcional: condição SES da variante, ex.: flag(porta_aberta)"),
            "change": types.Schema(type="STRING", description="opcional: o que a variante muda (para a revisão)"),
        }, required=["scene", "source"])),
    types.FunctionDeclaration(
        name="import_sprite",
        description=("Usa uma imagem feita fora do Saga como sprite de um objeto ou personagem. Por padrão recorta "
                     "o fundo; as margens vazias são cortadas e a proporção é mantida. Depois confira com render_scene "
                     "e ajuste com place_object."),
        parameters=types.Schema(type="OBJECT", properties={
            "object": types.Schema(type="STRING", description="id ou nome do objeto"),
            "source": types.Schema(type="STRING", description="URL http(s) ou caminho de arquivo neste computador (png, jpg, webp)"),
            "remove_background": types.Schema(type="BOOLEAN", description="recortar o fundo (padrão true; false se a imagem já é transparente)"),
            "x": types.Schema(type="INTEGER", description="centro horizontal, 0 a 1920 (padrão: onde o objeto já está)"),
            "y": types.Schema(type="INTEGER", description="centro vertical, 0 a 1080"),
            "height": types.Schema(type="INTEGER", description="altura em px (padrão: a atual)"),
        }, required=["object", "source"])),
    types.FunctionDeclaration(
        name="import_sound",
        description=("Usa um som feito fora do Saga (efeito, voz, música). kind ambient = som de fundo da cena (em "
                     "loop); object = som de um objeto (mode loop, ou random de vez em quando); play = o som de um "
                     "play \"...\" de script, como uma fala ou uma porta, e `text` tem de ser exatamente o texto do play."),
        parameters=types.Schema(type="OBJECT", properties={
            "source": types.Schema(type="STRING", description="URL http(s) ou caminho de arquivo neste computador (ogg, mp3, wav)"),
            "kind": types.Schema(type="STRING", description="ambient, object ou play"),
            "scene": types.Schema(type="STRING", description="kind ambient: id ou nome da cena"),
            "object": types.Schema(type="STRING", description="kind object: id ou nome do objeto"),
            "text": types.Schema(type="STRING", description="kind play: o texto exato do play \"...\"; nos outros, uma descrição do som"),
            "mode": types.Schema(type="STRING", description="kind object: loop ou random"),
        }, required=["source", "kind"])),
]

ASSET_TOOLS = {"render_scene", "import_background", "import_sprite", "import_sound"}
READ_ONLY = READ_ONLY | {"render_scene"}


# --- the catalogue, as JSON Schema (for MCP and any other caller) --------------------------------

def _json_schema(s: Optional[types.Schema]) -> Dict[str, Any]:
    if s is None:
        return {"type": "object", "properties": {}}
    out: Dict[str, Any] = {"type": str(getattr(s.type, "value", s.type)).lower()}
    if s.description:
        out["description"] = s.description
    if s.properties:
        out["properties"] = {k: _json_schema(v) for k, v in s.properties.items()}
    if s.required:
        out["required"] = list(s.required)
    if s.items:
        out["items"] = _json_schema(s.items)
    return out


def _param(kind: str, desc: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {"type": kind.lower()}
    if kind == "ARRAY":
        out["items"] = {"type": "string"}
    if desc:
        out["description"] = desc
    return out


def catalog() -> List[Dict[str, Any]]:
    """[{name, description, schema (JSON Schema of the arguments), read_only}] for every tool."""
    tools = []
    for name, (_, desc, params, required) in director_tools.TOOLS.items():
        schema: Dict[str, Any] = {"type": "object",
                                  "properties": {k: _param(kind, d) for k, (kind, d) in params.items()}}
        if required:
            schema["required"] = list(required)
        tools.append({"name": name, "description": desc, "schema": schema, "read_only": name in READ_ONLY})
    for decl in IMAGE_TOOLS:
        tools.append({"name": decl.name, "description": decl.description, "schema": _json_schema(decl.parameters),
                      "read_only": decl.name in READ_ONLY})
    return tools


# --- running a tool ------------------------------------------------------------------------------

async def run_tool(project_name: str, name: str, args: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Runs one tool on one project. Errors come back as {"error": ...} for the AI to read and fix."""
    args = args or {}
    try:
        if name in director_tools.TOOLS:
            project = project_service.load_project(project_name)
            result = director_tools.run_tool(project, name, args)
            if name not in director_tools.READ_ONLY and "error" not in result:
                project_service.save_project_data(project_name, project)
            return result
        if name in BLUEPRINT_TOOLS:
            return await _blueprint_tool(project_name, name, args)
        if name in ART_TOOLS:
            return await _art_tool(project_name, name, args)
        if name in ASSET_TOOLS:
            return await _asset_tool(project_name, name, args)
        if name == "generate_image_and_set_as_background":
            return await _generate_background(project_name, args)
        if name == "generate_sprite_for_object":
            return await _generate_sprite(project_name, args)
        if name == "analyze_scene_background":
            project = project_service.load_project(project_name)
            sid = director_tools._scene(project, args.get("scene"))
            return await _post("/api/genai/analyze-scene", {"project_name": project_name, "scene_id": sid})
        return {"error": f"ferramenta desconhecida: {name}"}
    except director_tools.ToolError as e:
        return {"error": str(e)}
    except Exception as e:                     # the model gets the error and can try something else
        logger.exception("tool %s failed", name)
        return {"error": f"{type(e).__name__}: {e}"}


async def _art_tool(project_name: str, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    from backend.services import scene_art
    try:
        if name == "create_scene_art":
            return await scene_art.create_scene_art(
                project_name, args.get("scene"), args.get("style", ""),
                args.get("reference_scene", ""), bool(args.get("keep_background")),
                only_new_sprites=bool(args.get("only_new_sprites")))
        if name == "edit_scene_background":
            return await scene_art.edit_background(project_name, args.get("scene"), args.get("change", ""))
        if name == "create_background_variant":
            return await scene_art.create_variant(
                project_name, args.get("scene"), args.get("when", ""), args.get("change", ""))
        return await scene_art.review_scene(project_name, args.get("scene"), bool(args.get("fix")))
    except scene_art.ArtError as e:
        return {"error": str(e)}


async def _asset_tool(project_name: str, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    from backend.services import asset_tools
    a = {k: v for k, v in args.items() if v is not None}
    try:
        if name == "render_scene":
            return await asyncio.to_thread(asset_tools.render_scene, project_name, a.get("scene"), a.get("flags"))
        if name == "import_background":
            return await asset_tools.import_background(project_name, a.get("scene"), a.get("source"),
                                                       a.get("when", ""), a.get("change", ""))
        if name == "import_sprite":
            return await asset_tools.import_sprite(project_name, a.get("object"), a.get("source"),
                                                   bool(a.get("remove_background", True)),
                                                   a.get("x"), a.get("y"), a.get("height"))
        return await asset_tools.import_sound(project_name, a.get("source"), a.get("kind", ""), a.get("scene", ""),
                                              a.get("object", ""), a.get("text", ""), a.get("mode", "loop"))
    except asset_tools.AssetError as e:
        return {"error": str(e)}


async def _blueprint_tool(project_name: str, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    from backend.api.routes import blueprint as routes
    if name == "get_blueprint":
        return await routes.get_blueprint(project_name)
    if name == "start_game_art":
        job = await routes.start_art(project_name)
        return {"started": True, "running": job["running"],
                **blueprint.art_status(project_service.load_project(project_name))}
    if name == "start_game_sound":
        job = await routes.start_sound(project_name)
        return {"started": True, "running": job["running"],
                **blueprint.sound_status(project_service.load_project(project_name))}
    text = args.get("text") or ""
    save = name == "save_blueprint"
    if save and routes.ART_JOBS.get(project_name, {}).get("running"):
        return {"error": "a arte deste jogo está sendo gerada; espere terminar para salvar a ficha"}
    report = await asyncio.to_thread(blueprint.build, project_name, text, save)
    if "explorador" in report:                  # the model needs the verdict, not the 56 commands
        report["explorador"]["caminho"] = len(report["explorador"]["caminho"])
    return report


# --- images through the existing endpoints of this same server ------------------------------------

async def _post(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
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


def _background_path(project: Dict[str, Any], sid: str) -> Optional[str]:
    for obj in project["scenes"][sid].get("objects", []):
        if obj.get("type") == "background" and obj.get("sprite"):
            return obj["sprite"].split("?")[0]
    return None


async def _generate_background(project_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    project = project_service.load_project(project_name)
    sid = director_tools._scene(project, args.get("scene"))
    payload = {"project_name": project_name, "output_type": "backgrounds", "width": 1920, "height": 1080,
               "prompt": f"2D painted point-and-click adventure background, {args.get('prompt', '')}",
               "negative_prompt": "text, watermark, blurry, distorted"}
    if args.get("reference_scene"):
        ref = _background_path(project, director_tools._scene(project, args["reference_scene"]))
        if ref:
            payload["reference_image_path"] = ref
    image = await _post("/api/genai/generate-image", payload)
    if not image.get("image_path"):
        return image if "error" in image else {"error": f"sem imagem: {image}"}
    return await _post("/api/scenes/set-background", {
        "project_name": project_name, "scene_id": sid, "background_path": image["image_path"]})


async def _generate_sprite(project_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    image = await _post("/api/genai/generate-image", {
        "project_name": project_name, "output_type": "sprites", "width": 512, "height": 512,
        "prompt": f"isolated game sprite of {args.get('description', '')}, transparent background, 2D illustration",
        "negative_prompt": "background, scenery, text, watermark"})
    if not image.get("image_path"):
        return image if "error" in image else {"error": f"sem imagem: {image}"}
    project = project_service.load_project(project_name)
    oid, _, obj = director_tools._object(project, args.get("object"))
    obj["sprite"] = image["image_path"]
    project_service.save_project_data(project_name, project)
    return {"object": oid, "sprite": image["image_path"]}
