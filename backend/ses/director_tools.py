"""
The AI director's tools for building a text adventure. Plain functions over project.json (no HTTP
round trips), each returning a small dict the model can read. Scripts are validated before they are
saved, and the errors go back to the model so it can fix them; playtest lets it play what it built.

Every tool takes the project dict and keyword arguments; TOOLS describes them for the model.
Object and scene arguments accept an id or a name.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from backend.ses.engine import GameEngine, playtest as run_playtest
from backend.ses.language import validate
from backend.ses.world import World, slug
from backend.services import object_generation_service

OPPOSITE = {"norte": "sul", "sul": "norte", "leste": "oeste", "oeste": "leste",
            "nordeste": "sudoeste", "sudoeste": "nordeste", "noroeste": "sudeste", "sudeste": "noroeste",
            "cima": "baixo", "baixo": "cima", "entrar": "sair", "sair": "entrar"}


class ToolError(Exception):
    pass


# --- lookup helpers --------------------------------------------------------------------------

def _scene(project, ref) -> str:
    sid = World(project).find_scene(ref)
    if not sid:
        names = ", ".join(f"{s.get('name')} ({i})" for i, s in project.get("scenes", {}).items())
        raise ToolError(f"cena {ref!r} não existe. Cenas: {names or 'nenhuma'}")
    return sid


def _object(project, ref, scene=None):
    world = World(project)
    prefer = [o.get("id") for o in project["scenes"][scene].get("objects", [])] if scene else None
    oid = world.find_object(ref, prefer)
    if not oid:
        raise ToolError(f"objeto {ref!r} não existe")
    sid = world.home[oid]
    return oid, sid, world.objects[oid]


def _check_script(project, script, owner_kind):
    if not (script or "").strip():
        return {"ok": True, "errors": [], "warnings": []}
    return validate(script, project, owner_kind)


def _script_rejected(result):
    return {"error": "script com erro de sintaxe — nada foi salvo; corrija e chame de novo",
            "script_errors": result["errors"]}


# --- tools -----------------------------------------------------------------------------------

def get_project(project):
    """Overview: scenes, exits, objects and script problems."""
    out = []
    problems = []
    for sid, s in project.get("scenes", {}).items():
        objs = []
        for o in s.get("objects", []):
            if o.get("type") == "background":
                continue
            p = o.get("properties") or {}
            objs.append({"id": o["id"], "name": o.get("name"),
                         **({"portable": True} if p.get("portable") else {}),
                         **({"hidden": True} if p.get("hidden") else {}),
                         **({"script": True} if (o.get("ses") or "").strip() and "on " in o.get("ses", "") else {})})
            if (o.get("ses") or "").strip():
                r = validate(o["ses"], None, "object")
                if not r["ok"]:
                    problems.append({"object": o["id"], "errors": r["errors"]})
        if (s.get("ses") or "").strip():
            r = validate(s["ses"], None, "scene")
            if not r["ok"]:
                problems.append({"scene": sid, "errors": r["errors"]})
        out.append({"id": sid, "name": s.get("name"), "description": (s.get("description") or "")[:240],
                    "exits": s.get("exits") or {}, "objects": objs})
    return {"name": project.get("name"), "start_scene": project.get("start_scene"),
            "scenes": out, "script_problems": problems}


def get_scene(project, scene):
    """Everything about a scene, including descriptions and scripts."""
    sid = _scene(project, scene)
    s = project["scenes"][sid]
    return {"id": sid, "name": s.get("name"), "description": s.get("description") or "",
            "exits": s.get("exits") or {}, "script": s.get("ses") or "",
            "objects": [{"id": o["id"], "name": o.get("name"), "description": o.get("description") or "",
                         "properties": o.get("properties") or {}, "script": o.get("ses") or ""}
                        for o in s.get("objects", []) if o.get("type") != "background"]}


def create_scene(project, name, description="", script=""):
    """Creates a scene (or returns the existing one with this name)."""
    existing = World(project).find_scene(name)
    if existing:
        return {"created": False, "scene_id": existing, "message": "já existia uma cena com esse nome"}
    check = _check_script(project, script, "scene")
    if not check["ok"]:
        return _script_rejected(check)
    sid = f"scene_{uuid.uuid4().hex[:8]}"
    project.setdefault("scenes", {})[sid] = {
        "id": sid, "name": name, "description": description, "exits": {},
        "objects": [{"id": f"background_{uuid.uuid4().hex[:8]}", "name": "Background", "type": "background",
                     "sprite": "", "position": {"x": 960, "y": 540}, "origin": {"x": 960, "y": 540},
                     "size": {"width": 1920, "height": 1080}, "scale": {"x": 1, "y": 1}, "rotation": 0,
                     "zIndex": 0, "properties": {}, "actions": [], "ses": ""}],
        "hotspots": [], "actions": [], "ses": script or "",
    }
    if not project.get("start_scene") or project["start_scene"] not in project["scenes"]:
        project["start_scene"] = sid
    return {"created": True, "scene_id": sid, "warnings": check["warnings"]}


def update_scene(project, scene, name=None, description=None):
    sid = _scene(project, scene)
    s = project["scenes"][sid]
    if name:
        s["name"] = name
    if description is not None:
        s["description"] = description
    return {"updated": sid}


def connect_scenes(project, from_scene, direction, to_scene, back_direction=None, one_way=False):
    """An exit from_scene --direction--> to_scene, and the way back (opposite direction) unless one_way."""
    a, b = _scene(project, from_scene), _scene(project, to_scene)
    d = slug(direction)
    project["scenes"][a].setdefault("exits", {})[d] = b
    result = {"exit": f"{project['scenes'][a]['name']} --{d}--> {project['scenes'][b]['name']}"}
    if not one_way:
        back = slug(back_direction) if back_direction else OPPOSITE.get(d)
        if not back:
            return {**result, "warning": f"sem volta: diga back_direction para '{d}'"}
        project["scenes"][b].setdefault("exits", {})[back] = a
        result["back"] = f"{project['scenes'][b]['name']} --{back}--> {project['scenes'][a]['name']}"
    return result


def disconnect(project, scene, direction):
    sid = _scene(project, scene)
    removed = (project["scenes"][sid].get("exits") or {}).pop(slug(direction), None)
    return {"removed": bool(removed)}


def set_start_scene(project, scene):
    project["start_scene"] = _scene(project, scene)
    return {"start_scene": project["start_scene"]}


def create_object(project, scene, name, description, portable=False, hidden=False, aliases=None,
                  script="", object_type="item"):
    sid = _scene(project, scene)
    check = _check_script(project, script, "object")
    if not check["ok"]:
        return _script_rejected(check)
    s = project["scenes"][sid]
    oid = f"obj_{slug(name)[:24] or 'objeto'}_{uuid.uuid4().hex[:4]}"
    s.setdefault("objects", []).append({
        "id": oid, "name": name, "type": object_type or "item",
        "sprite": object_generation_service.get_placeholder(object_type or "item", "emoji"),
        "position": object_generation_service.calculate_smart_position(s, object_type or "item"),
        "size": {"width": 100, "height": 100}, "scale": {"x": 1, "y": 1}, "rotation": 0, "zIndex": 10,
        "description": description,
        "properties": {"portable": bool(portable), "hidden": bool(hidden), "aliases": list(aliases or [])},
        "actions": [], "ses": script or "",
    })
    return {"created": oid, "scene": sid, "warnings": check["warnings"]}


def update_object(project, object, name=None, description=None, portable=None, hidden=None,
                  aliases=None, move_to_scene=None, script=None):
    oid, sid, obj = _object(project, object)
    warnings = []
    if script is not None:
        check = _check_script(project, script, "object")
        if not check["ok"]:
            return _script_rejected(check)
        obj["ses"] = script
        warnings = check["warnings"]
    props = obj.setdefault("properties", {})
    if name:
        obj["name"] = name
    if description is not None:
        obj["description"] = description
    if portable is not None:
        props["portable"] = bool(portable)
    if hidden is not None:
        props["hidden"] = bool(hidden)
    if aliases is not None:
        props["aliases"] = list(aliases)
    if move_to_scene:
        target = _scene(project, move_to_scene)
        project["scenes"][sid]["objects"].remove(obj)
        project["scenes"][target].setdefault("objects", []).append(obj)
        sid = target
    return {"updated": oid, "scene": sid, **({"warnings": warnings} if warnings else {})}


def set_script(project, target, script):
    """Replaces the SES script of an object or a scene (validated first)."""
    world = World(project)
    sid = world.find_scene(target)
    oid = None if sid else world.find_object(target)
    if not sid and not oid:
        raise ToolError(f"{target!r} não é um objeto nem uma cena")
    check = _check_script(project, script, "scene" if sid else "object")
    if not check["ok"]:
        return _script_rejected(check)
    if sid:
        project["scenes"][sid]["ses"] = script
    else:
        world.objects[oid]["ses"] = script
    return {"saved": sid or oid, "warnings": check["warnings"]}


def delete_object(project, object):
    oid, sid, obj = _object(project, object)
    project["scenes"][sid]["objects"].remove(obj)
    return {"deleted": oid}


def delete_scene(project, scene):
    sid = _scene(project, scene)
    del project["scenes"][sid]
    for s in project["scenes"].values():
        s["exits"] = {d: t for d, t in (s.get("exits") or {}).items() if t != sid}
    if project.get("start_scene") == sid:
        project["start_scene"] = next(iter(project["scenes"]), "")
    return {"deleted": sid}


def set_presentation(project, style=None, layout=None, retro=None):
    p = project.setdefault("presentation", {})
    if style is not None:
        if style not in ("classico", "moderno"):
            raise ToolError("style: 'classico' ou 'moderno'")
        p["style"] = style
    if layout is not None:
        if layout not in ("classico", "paineis"):
            raise ToolError("layout: 'classico' ou 'paineis'")
        p["layout"] = layout
    if retro is not None:
        p["retro"] = bool(retro)
    return {"presentation": p}


def playtest(project, commands):
    """Plays from the start with these commands and returns what the player would read."""
    r = run_playtest(project, list(commands or []))
    lines = []
    for step in r["transcript"]:
        if step["command"] is not None:
            lines.append(f"> {step['command']}")
        lines.extend(step["messages"])
    st = r["final_state"]
    return {"transcript": "\n".join(lines)[-6000:],
            "ended": st.get("ended"), "flags": st.get("flags"), "scene": st.get("scene"),
            "inventory": [o["name"] for o in (r["view"] or {}).get("inventory", [])],
            "script_errors": r["script_errors"]}


# --- registry --------------------------------------------------------------------------------

S, I, B, A = "STRING", "INTEGER", "BOOLEAN", "ARRAY"

TOOLS = {
    "get_project": (get_project, "Visão geral do projeto: cenas, saídas, objetos e scripts com erro. Chame antes de mudar algo que você não criou nesta conversa.", {}, []),
    "get_scene": (get_scene, "Detalhes de uma cena: descrição, saídas, objetos com descrições e scripts.",
                  {"scene": (S, "id ou nome da cena")}, ["scene"]),
    "create_scene": (create_scene, "Cria uma cena (sala). A descrição é o que o jogador lê ao entrar; não liste nela as saídas nem os objetos, o motor já mostra.",
                     {"name": (S, ""), "description": (S, "texto de ambientação, 1 a 3 frases"),
                      "script": (S, "script SES da cena (opcional): on enter / on first_enter")}, ["name", "description"]),
    "update_scene": (update_scene, "Renomeia uma cena ou troca a descrição.",
                     {"scene": (S, ""), "name": (S, ""), "description": (S, "")}, ["scene"]),
    "connect_scenes": (connect_scenes, "Cria a saída from_scene --direction--> to_scene e a volta na direção oposta (a menos que one_way). Para uma passagem que começa fechada, NÃO conecte: use 'link' no script que a abre.",
                       {"from_scene": (S, ""), "direction": (S, "norte, sul, leste, oeste, cima, baixo, entrar, sair..."),
                        "to_scene": (S, ""), "back_direction": (S, "direção da volta, se não for a oposta"),
                        "one_way": (B, "")}, ["from_scene", "direction", "to_scene"]),
    "disconnect": (disconnect, "Remove uma saída de uma cena.", {"scene": (S, ""), "direction": (S, "")}, ["scene", "direction"]),
    "set_start_scene": (set_start_scene, "Define a cena onde o jogo começa.", {"scene": (S, "")}, ["scene"]),
    "create_object": (create_object, "Cria um objeto numa cena. 'portable' = o jogador pode pegar. 'hidden' = só aparece depois de 'show' num script. O script SES é validado; se tiver erro nada é criado e os erros voltam.",
                      {"scene": (S, ""), "name": (S, "nome que o jogador digita, ex.: 'chave enferrujada'"),
                       "description": (S, "o que o jogador lê ao examinar"), "portable": (B, ""), "hidden": (B, ""),
                       "aliases": (A, "outros nomes, ex.: ['chave']"), "script": (S, "script SES (opcional)"),
                       "object_type": (S, "item, porta, personagem, móvel...")}, ["scene", "name", "description"]),
    "update_object": (update_object, "Muda nome, descrição, portable, hidden, aliases, script, ou move o objeto para outra cena.",
                      {"object": (S, "id ou nome"), "name": (S, ""), "description": (S, ""), "portable": (B, ""),
                       "hidden": (B, ""), "aliases": (A, ""), "move_to_scene": (S, ""),
                       "script": (S, "novo script SES (validado)")}, ["object"]),
    "set_script": (set_script, "Troca o script SES de um objeto ou de uma cena. É validado; erros voltam com linha e coluna e nada é salvo.",
                   {"target": (S, "id ou nome do objeto ou da cena"), "script": (S, "")}, ["target", "script"]),
    "delete_object": (delete_object, "Apaga um objeto.", {"object": (S, "")}, ["object"]),
    "delete_scene": (delete_scene, "Apaga uma cena e as saídas que levavam a ela.", {"scene": (S, "")}, ["scene"]),
    "set_presentation": (set_presentation, "Como o jogo se apresenta. style 'classico' = texto estilo adventure de 8 bits ('📍 Local. Vejo: ... Saídas: ...'); layout 'classico' = imagem em cima e texto embaixo, 'paineis' = inventário e texto em painéis laterais; retro = ilustração pixelada com paleta reduzida.",
                         {"style": (S, "classico ou moderno"), "layout": (S, "classico ou paineis"), "retro": (B, "")}, []),
    "playtest": (playtest, "Joga do início com estes comandos (como o jogador digitaria) e devolve o que ele leria. Use para provar que o puzzle tem solução e que o jogo termina.",
                 {"commands": (A, "ex.: ['olhar', 'pegar chave', 'norte', 'usar chave na porta']")}, ["commands"]),
}

READ_ONLY = {"get_project", "get_scene", "playtest"}


def run_tool(project: dict, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Runs a tool on the project dict (mutating it). Errors come back as {'error': ...}."""
    if name not in TOOLS:
        return {"error": f"ferramenta desconhecida: {name}"}
    fn, _, params, _ = TOOLS[name]
    unknown = sorted(set(args or {}) - set(params))
    if unknown:
        return {"error": f"argumentos desconhecidos {unknown}; {name} aceita: {sorted(params) or 'nenhum'}"}
    args = {k: v for k, v in (args or {}).items() if v is not None}
    try:
        return fn(project, **args)
    except ToolError as e:
        return {"error": str(e)}
    except TypeError as e:
        return {"error": f"argumentos inválidos: {e}"}
