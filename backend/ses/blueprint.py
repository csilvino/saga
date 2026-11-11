"""
A game's blueprint (the "ficha"): one YAML (or JSON) file that says everything about a text
adventure: map, objects, SES scripts, art direction, picture variants and the tests that prove
it can be won. The build turns it into project.json, deterministically:

    1. check     the blueprint's shape, every script's syntax, references, reachability, unused
                 items, flags read but never set, hidden objects nobody shows;
    2. assemble  scenes, exits and objects with the director's own tools (no step limit). A rebuild
                 keeps what the art already made (backgrounds, sprites, positions, variants) for
                 scenes and objects that keep their names, and keeps their ids, so saves still work;
    3. test      plays the solution to the victory and every listed death;
    4. explore   an automatic player that tries the actions that change something and tells which
                 scenes and endings it reached (it needs no solution);
    5. art       (separate, slow) the pictures still missing: scenes, then variants.

The LLM writes the blueprint; the build answers with a report it can act on before any GPU time
is spent. Format: docs/FICHA.md. Example: projects/Neve sobre o Claustro/ficha.yaml.
"""

from __future__ import annotations

import asyncio
import copy
import json
from collections import deque
from typing import Any, Callable, Dict, List, Optional, Tuple

from backend.ses import director_tools as dt
from backend.ses.engine import GameEngine, INV, playtest
from backend.ses.language import If, SESError, Stmt, parse, parse_condition, walk, walk_conds
from backend.ses.world import World, slug

FILE_NAME = "ficha.yaml"

# object fields the art writes; a rebuild carries them over from the previous project.json
VISUAL_FIELDS = ("sprite", "position", "origin", "size", "scale", "rotation", "zIndex", "animation", "animations")
VISUAL_PROPS = ("painted",)


class BlueprintError(Exception):
    """The blueprint cannot even be assembled; `problems` says why."""

    def __init__(self, problems: List[dict]):
        super().__init__("; ".join(p["msg"] for p in problems))
        self.problems = problems


def problem(level: str, msg: str, where: str = "") -> dict:
    return {"nivel": level, "msg": msg, **({"onde": where} if where else {})}


# --- reading --------------------------------------------------------------------------------

def load(text: str) -> dict:
    """The blueprint from YAML or JSON text."""
    import yaml
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        where = f" (linha {mark.line + 1}, coluna {mark.column + 1})" if mark else ""
        raise BlueprintError([problem("erro", f"a ficha não é um YAML válido{where}: "
                                               f"{getattr(e, 'problem', None) or e}")])
    if not isinstance(data, dict):
        raise BlueprintError([problem("erro", "a ficha precisa ser um objeto com 'nome' e 'cenas'")])
    return data


def dump(blueprint: dict) -> str:
    import yaml

    class Dumper(yaml.SafeDumper):
        pass

    def text(dumper, value):
        style = "|" if "\n" in value else None
        return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)

    Dumper.add_representer(str, text)
    return yaml.dump(blueprint, Dumper=Dumper, allow_unicode=True, sort_keys=False, width=110)


def _list(value) -> list:
    return value if isinstance(value, list) else ([] if value is None else [value])


def shape_problems(bp: dict) -> List[dict]:
    """What is missing or malformed in the blueprint itself (before building anything)."""
    out = []
    if not str(bp.get("nome") or "").strip():
        out.append(problem("erro", "falta 'nome' (o nome do jogo)"))
    scenes = bp.get("cenas")
    if not isinstance(scenes, list) or not scenes:
        return out + [problem("erro", "'cenas' precisa ser uma lista com pelo menos uma cena")]
    names = {}
    objects = {}
    for i, s in enumerate(scenes):
        if not isinstance(s, dict) or not str(s.get("nome") or "").strip():
            out.append(problem("erro", f"a cena nº {i + 1} não tem 'nome'"))
            continue
        key = slug(s["nome"])
        if key in names:
            out.append(problem("erro", f"duas cenas com o nome {s['nome']!r}"))
        names[key] = s["nome"]
        if not isinstance(s.get("saidas") or {}, dict):
            out.append(problem("erro", "'saidas' precisa ser um mapa direção: cena", s["nome"]))
        for o in _list(s.get("objetos")):
            if not isinstance(o, dict) or not str(o.get("nome") or "").strip():
                out.append(problem("erro", "objeto sem 'nome'", s["nome"]))
                continue
            k = slug(o["nome"])
            if k in objects:
                out.append(problem("erro", f"dois objetos com o nome {o['nome']!r} "
                                           f"({objects[k]} e {s['nome']}); use nomes diferentes", s["nome"]))
            objects[k] = s["nome"]
        for v in _list(s.get("variantes")):
            if not isinstance(v, dict) or not v.get("quando") or not v.get("mudanca"):
                out.append(problem("erro", "variante precisa de 'quando' (condição SES) e 'mudanca'", s["nome"]))
                continue
            try:
                parse_condition(str(v["quando"]))
            except SESError as e:
                out.append(problem("erro", f"variante: condição {v['quando']!r} inválida: {e}", s["nome"]))
    start = bp.get("inicio")
    if start and slug(start) not in names:
        out.append(problem("erro", f"'inicio' aponta para {start!r}, que não é uma cena"))
    ref = (bp.get("arte") or {}).get("referencia")
    if ref and slug(ref) not in names:
        out.append(problem("erro", f"arte.referencia aponta para {ref!r}, que não é uma cena"))
    tests = bp.get("testes") or {}
    if not tests.get("solucao"):
        out.append(problem("aviso", "sem testes.solucao: ninguém prova que o jogo pode ser vencido"))
    elif not tests.get("vitoria"):
        out.append(problem("erro", "testes.vitoria: diga um trecho do texto do 'end' de vitória"))
    return out


# --- assembling -----------------------------------------------------------------------------

def _scene_bg(scene: dict) -> Optional[dict]:
    return next((o for o in scene.get("objects", []) if o.get("type") == "background"), None)


def has_art(scene: dict) -> bool:
    bg = _scene_bg(scene)
    return bool(bg and bg.get("sprite"))


def assemble(bp: dict, previous: Optional[dict] = None) -> Tuple[dict, List[dict]]:
    """project.json from the blueprint; `previous` (the current project) donates art and ids."""
    shape = [p for p in shape_problems(bp) if p["nivel"] == "erro"]
    if shape:
        raise BlueprintError(shape)
    out: List[dict] = []
    pres = bp.get("apresentacao") or {}
    name = str(bp["nome"]).strip()
    p = {"name": name, "version": str(bp.get("versao") or "1.0.0"), "start_scene": "", "navigation_mode": "text",
         "metadata": {"action_history": [], "deleted_objects": [], "narrative_directives": ""},
         "scenes": {}, "assets": {"sprites": {}, "items": {}, "audio": {}},
         "presentation": {"style": pres.get("estilo", "classico"), "layout": pres.get("layout", "classico"),
                          "retro": bool(pres.get("retro", False))},
         "launcher": {"title": name, "description": str(bp.get("descricao") or ""), "version": "1.0.0"}}
    if previous:
        for key in ("metadata", "assets", "launcher"):
            if previous.get(key):
                p[key] = copy.deepcopy(previous[key])
        p["launcher"].update({"title": name, "description": str(bp.get("descricao") or p["launcher"].get("description", ""))})
    if bp.get("arte"):
        p["art"] = {"style": str(bp["arte"].get("estilo") or ""), "reference": str(bp["arte"].get("referencia") or "")}

    def tool(name_, **args):
        r = dt.run_tool(p, name_, args)
        if "error" in r:
            errs = r.get("script_errors") or []
            detail = "; ".join(f"linha {e['line']}, coluna {e['col']}: {e['message']}" for e in errs)
            where = args.get("scene") or args.get("from_scene") or args.get("name") or ""
            out.append(problem("erro", f"{name_}: {r['error']}" + (f" — {detail}" if detail else ""),
                               f"{where} / {args.get('name', '')}".strip(" /")))
        return r

    scenes = bp["cenas"]
    for s in scenes:
        tool("create_scene", name=s["nome"], description=str(s.get("descricao") or "").strip(),
             script=str(s.get("script") or ""))

    # exits: what each scene declares wins; the way back is added unless declared otherwise
    declared = {(slug(s["nome"]), dt.slug(d)) for s in scenes for d in (s.get("saidas") or {})}
    for s in scenes:
        for d, target in (s.get("saidas") or {}).items():
            back, one_way = None, False
            if isinstance(target, dict):
                back = target.get("volta")
                one_way = back is False
                target = target.get("para")
            back_dir = slug(back) if isinstance(back, str) else dt.OPPOSITE.get(slug(d))
            if back_dir and (slug(target), back_dir) in declared:
                one_way = True                    # the other scene says where its exit goes
            r = tool("connect_scenes", from_scene=s["nome"], direction=d, to_scene=target,
                     back_direction=back if isinstance(back, str) else None, one_way=one_way)
            if r.get("warning"):
                out.append(problem("aviso", r["warning"], s["nome"]))

    for s in scenes:
        for o in _list(s.get("objetos")):
            r = tool("create_object", scene=s["nome"], name=o["nome"], description=str(o.get("descricao") or "").strip(),
                     portable=bool(o.get("pegavel")), hidden=bool(o.get("escondido")),
                     aliases=[str(a) for a in _list(o.get("apelidos"))], script=str(o.get("script") or ""),
                     object_type=str(o.get("tipo") or "item"))
            for w in r.get("warnings") or []:
                if "(ainda)" in w["message"]:      # objects created later; analyze() checks the final project
                    continue
                out.append(problem("aviso", f"script de {o['nome']}: linha {w['line']}: {w['message']}", s["nome"]))
        sid = World(p).find_scene(s["nome"])
        if sid:
            p["scenes"][sid]["variants"] = [{"when": str(v["quando"]), "change": str(v["mudanca"])}
                                            for v in _list(s.get("variantes"))]
    if bp.get("inicio"):
        tool("set_start_scene", scene=bp["inicio"])
    if previous:
        p = carry_art(previous, p)
    return p, out


def carry_art(old: dict, new: dict) -> dict:
    """Keeps ids, pictures and placements of scenes and objects that kept their names."""
    old_scenes = {slug(s.get("name")): (sid, s) for sid, s in (old.get("scenes") or {}).items()}
    old_objs = {}
    for s in (old.get("scenes") or {}).values():
        for o in s.get("objects", []):
            if o.get("type") != "background":
                old_objs[slug(o.get("name"))] = o
    rename = {}
    for sid, s in new["scenes"].items():
        match = old_scenes.get(slug(s.get("name")))
        if not match:
            continue
        old_sid, old_s = match
        rename[sid] = old_sid
        old_bg, bg = _scene_bg(old_s), _scene_bg(s)
        if old_bg and bg:
            s["objects"][s["objects"].index(bg)] = copy.deepcopy(old_bg)
        done = {v.get("when"): v for v in old_s.get("variants") or [] if v.get("background")}
        for v in s.get("variants") or []:
            if v["when"] in done:
                v["background"] = done[v["when"]]["background"]
        for o in s["objects"]:
            prev = old_objs.get(slug(o.get("name")))
            if o.get("type") == "background" or not prev:
                continue
            o["id"] = prev["id"]
            for f in VISUAL_FIELDS:
                if f in prev:
                    o[f] = copy.deepcopy(prev[f])
            for f in VISUAL_PROPS:
                if f in (prev.get("properties") or {}):
                    o.setdefault("properties", {})[f] = prev["properties"][f]
    scenes = {}
    for sid, s in new["scenes"].items():
        nid = rename.get(sid, sid)
        s["id"] = nid
        s["exits"] = {d: rename.get(t, t) for d, t in (s.get("exits") or {}).items()}
        scenes[nid] = s
    new["scenes"] = scenes
    new["start_scene"] = rename.get(new.get("start_scene"), new.get("start_scene"))
    return new


# --- static analysis ------------------------------------------------------------------------

def _scripts(project):
    """(owner name, scene id, parsed script) for every script in the project."""
    world = World(project)
    for sid, s in world.scenes.items():
        if (s.get("ses") or "").strip():
            yield s.get("name"), sid, s["ses"]
        for o in s.get("objects", []):
            if o.get("type") != "background" and (o.get("ses") or "").strip():
                yield o.get("name"), sid, o["ses"]


def analyze(project: dict) -> List[dict]:
    out = []
    world = World(project)
    flags_set, flags_read, shown, used, links, ends = set(), {}, set(), set(), [], []
    useful_own = set()                 # items whose own script does something beyond describing itself
    for owner, sid, src in _scripts(project):
        try:
            script = parse(src)
        except SESError as e:
            out.append(problem("erro", f"script de {owner}: {e}", world.scene_name(sid)))
            continue
        for h in script.handlers:
            if h.with_ref is not None:
                used.add(slug(h.with_ref.name))
            if h.event not in ("examine", "take", "drop") or any(
                    isinstance(n, Stmt) and n.op not in ("say", "stop") for n in walk(h.body)):
                useful_own.add(slug(owner))
            for node in walk(h.body):
                if isinstance(node, Stmt):
                    op, a = node.op, node.args
                    if op in ("set", "inc", "dec"):
                        flags_set.add(slug(a[0].name))
                    elif op == "show":
                        shown.add(slug(a[0].name))
                    if op in ("take", "move", "drop") and a and a[0] is not None:
                        shown.add(slug(a[0].name))        # a hidden thing handed to the player also counts
                    elif op == "link":
                        where = world.find_scene(a[2].name) if a[2] else sid
                        links.append((where, world.find_scene(a[1].name)))
                    elif op == "goto":
                        links.append((sid, world.find_scene(a[0].name)))
                    elif op == "end":
                        ends.append((owner, a[0]))
                    if op in ("remove", "move") and a and a[0] is not None:
                        used.add(slug(a[0].name))
                    obj_refs = {"take": [0], "drop": [0], "remove": [0], "show": [0], "hide": [0], "move": [0]}
                    scene_refs = {"move": [1], "goto": [0], "link": [1, 2], "unlink": [1]}
                    for kind, table in (("objeto", obj_refs), ("cena", scene_refs)):
                        for i in table.get(op, []):
                            ref = a[i] if i < len(a) else None
                            if ref is None or ref.name in ("self", "this"):
                                continue
                            found = world.find_object(ref.name) if kind == "objeto" else world.find_scene(ref.name)
                            if not found:
                                out.append(problem("erro", f"script de {owner}: {kind} {ref.name!r} não existe",
                                                   world.scene_name(sid)))
                if isinstance(node, If):
                    for c in walk_conds(node.cond):
                        if c.kind == "call" and c.args[0] == "flag":
                            flags_read.setdefault(slug(c.args[1].name), owner)
                        elif c.kind == "compare":
                            flags_read.setdefault(slug(c.args[0].args[1].name), owner)
                        elif c.kind == "call" and c.args[0] in ("has", "here"):
                            used.add(slug(c.args[1].name))
    for s in world.scenes.values():
        for v in s.get("variants") or []:
            try:
                for c in walk_conds(parse_condition(v.get("when", ""))):
                    if c.kind == "call" and c.args[0] == "flag":
                        flags_read.setdefault(slug(c.args[1].name), f"variante de {s.get('name')}")
            except SESError:
                pass

    for f, owner in sorted(flags_read.items()):
        if f not in flags_set:
            out.append(problem("erro", f"a flag {f!r} é testada ({owner}) mas nenhum script a marca com set"))
    if not ends:
        out.append(problem("erro", "nenhum 'end': o jogo não tem final"))

    # reachability over exits plus every exit a script can open
    graph: Dict[str, set] = {sid: set(world.base_exits(sid).values()) for sid in world.scenes}
    for a, b in links:
        if a and b:
            graph.setdefault(a, set()).add(b)
    start = world.find_scene(project.get("start_scene"))
    seen, todo = {start}, [start]
    while todo:
        for nxt in graph.get(todo.pop(), ()):
            if nxt in world.scenes and nxt not in seen:
                seen.add(nxt)
                todo.append(nxt)
    for sid, s in world.scenes.items():
        if sid not in seen:
            out.append(problem("erro", f"a cena {s.get('name')!r} não tem caminho a partir do início"))

    for oid, o in world.objects.items():
        props = o.get("properties") or {}
        names = {slug(n) for n in world.object_names(oid)}
        if props.get("hidden") and not names & shown:
            out.append(problem("erro", f"{o.get('name')!r} começa escondido e nenhum script o mostra "
                                       f"(show) ou entrega (take/move)",
                               world.scene_name(world.home[oid])))
        if props.get("portable") and not names & used and slug(o.get("name")) not in useful_own:
            out.append(problem("aviso", f"o item {o.get('name')!r} pode ser pego mas nenhum script o usa (se for só uma pista para ler, tudo bem)",
                               world.scene_name(world.home[oid])))
        if not (o.get("description") or "").strip():
            out.append(problem("aviso", f"{o.get('name')!r} sem descrição (a arte depende dela)",
                               world.scene_name(world.home[oid])))
    return out


# --- tests ----------------------------------------------------------------------------------

def run_tests(project: dict, tests: dict) -> Tuple[List[dict], List[dict]]:
    """(results, problems): the solution must reach the victory, each death its own ending."""
    results, out = [], []
    win = str(tests.get("vitoria") or "").strip()
    cases = []
    if tests.get("solucao"):
        cases.append(("solução", [str(c) for c in tests["solucao"]], win, True))
    for d in _list(tests.get("mortes")):
        if isinstance(d, dict):
            cases.append((f"morte: {d.get('nome') or '?'}", [str(c) for c in _list(d.get("comandos"))],
                          str(d.get("fim") or "").strip(), False))
    for label, commands, expect, is_win in cases:
        r = playtest(project, commands)
        if is_win:
            results_depth = puzzle_actions(project, commands)
        ended = r["final_state"].get("ended")
        steps = len(r["transcript"]) - 1
        ok = bool(ended) and (not expect or expect.lower() in ended.lower())
        if is_win and ok and steps < len(commands):
            ok = False
            reason = f"terminou no comando {steps} de {len(commands)}"
        elif not ended:
            reason = "o jogo não terminou"
        elif not ok:
            reason = f"terminou com outro texto: {ended[:120]!r}"
        else:
            reason = ""
        refused = [step["command"] for step in r["transcript"][1:]
                   if any(m.startswith(("Não entendi", "Você não vê", "Não dá para ir", "Nada acontece",
                                        "Não dá para pegar")) for m in step["messages"])]
        results.append({"teste": label, "ok": ok, "comandos": len(commands), "fim": (ended or "")[:160],
                        **({"acoes_de_puzzle": results_depth} if is_win else {}),
                        **({"motivo": reason} if reason else {}),
                        **({"comandos_recusados": refused[:8]} if refused else {})})
        if not ok:
            last = r["transcript"][-1]
            out.append(problem("erro", f"{label}: {reason}; último comando {last['command']!r} → "
                                       f"{' '.join(last['messages'])[:200]!r}"))
        if refused:
            out.append(problem("erro" if is_win else "aviso",
                               f"{label}: o jogo recusou {len(refused)} comando(s): {', '.join(refused[:8])}. "
                               "O que você acha que acontece não é o que o jogo faz; confira nomes e lugares."))
        if r["script_errors"]:
            out.append(problem("erro", f"{label}: scripts com erro: {r['script_errors']}"))
    return results, out


def puzzle_actions(project: dict, commands: List[str]) -> List[str]:
    """The solution's commands that change the game other than walking or picking something up:
    opening, using, pushing, reading what reveals something. A measure of how much puzzle there is."""
    from backend.ses.engine import find_verb
    engine = GameEngine(project)
    state = engine.start()["state"]
    out = []
    for cmd in commands:
        nxt = engine.command(state, cmd)["state"]
        verb = find_verb(slug(cmd.split()[0])) if cmd.split() else None
        if verb not in (None, "go", "take") and _core(nxt) != _core(state) and not nxt.get("ended"):
            out.append(cmd)
        state = nxt
        if state.get("ended"):
            break
    return out


def progress(project: dict, commands: List[str]) -> set:
    """What a play-through unlocked on its way: flags set, hidden things revealed, passages opened."""
    engine = GameEngine(project)
    state = engine.start()["state"]
    seen = set()
    for cmd in commands:
        state = engine.command(state, cmd)["state"]
        seen |= {f"flag {k}" for k, v in state["flags"].items() if v not in (None, False, 0, "")}
        seen |= {f"{engine.world.object_name(o)} visível" for o, v in state["visible"].items() if v}
        seen |= {f"passagem {d} em {engine.world.scene_name(s)}"
                 for s, ex in state["exits"].items() for d, tgt in ex.items() if tgt}
        if state.get("ended"):
            break
    return seen


# --- automatic exploration ------------------------------------------------------------------

VERB_WORDS = {"examine": "examinar", "open": "abrir", "close": "fechar", "push": "empurrar", "pull": "puxar",
              "talk": "falar com", "use": "usar", "take": "pegar"}


def _core(state: dict) -> str:
    """What matters for progress. Counters are capped at 5 so 'talk to the seagull' forever is not
    an endless supply of new states."""
    flags = {k: (max(-5, min(5, v)) if isinstance(v, (int, float)) and not isinstance(v, bool) else v)
             for k, v in state["flags"].items()}
    return json.dumps([flags, state["where"], state["visible"], state["exits"], state.get("ended")], sort_keys=True)


def explore(project: dict, win: str = "", budget: int = 25000) -> dict:
    """An automatic player. Free moves and taking loose items cost nothing; every other action that
    changes the game is a step. It goes depth-first over game states (not over positions): it keeps
    doing whatever changes something and backs up when stuck, until it finds the victory or spends
    `budget` engine commands. Adventures mostly move forward, so this finds wins quickly."""
    engine = GameEngine(project)
    world = engine.world
    scripted = {}
    for oid in world.objects:
        sc = engine.scripts.get(oid)
        scripted[oid] = {h.event for h in sc.handlers} if sc else set()
        if sc and any(h.event == "use" and h.with_ref is not None for h in sc.handlers):
            scripted[oid].add("use_with")
    names = {oid: world.object_name(oid) for oid in world.objects}
    calls = 0
    endings: Dict[str, List[str]] = {}
    visited_scenes = set()

    def run(state, cmd):
        nonlocal calls
        calls += 1
        return engine.command(state, cmd)["state"]

    def actions(state):
        engine.state = state
        here, inv = engine.here(), engine.inventory()
        for oid in here + inv:
            for ev in scripted[oid] & {"examine", "open", "close", "push", "pull", "talk", "use", "take"}:
                if ev == "take" and oid in inv:
                    continue
                yield f"{VERB_WORDS[ev]} {names[oid]}"
        for a in inv:
            for b in here + inv:
                if a != b and ("use_with" in scripted[b] or "use_with" in scripted[a]):
                    yield f"usar {names[a]} em {names[b]}"

    def tour(state, path, take):
        """One continuous walk (out and back along every two-way exit) through every scene reachable
        without changing the game, picking up loose items when `take`. Returns where it stood at
        each scene, the walk's end, and the moves that changed the game (deaths, scenes with
        scripts, one-way exits), which become steps of their own."""
        spots, jumps, seen_s = [], [], set()
        cur = [state, path]

        def visit():
            st, pth = cur
            seen_s.add(st["scene"])
            visited_scenes.add(st["scene"])
            if take:
                engine.state = st
                for oid in engine.here():
                    props = world.objects[oid].get("properties") or {}
                    if props.get("portable") and "take" not in scripted[oid]:
                        st = run(st, f"pegar {names[oid]}")
                        pth = pth + [f"pegar {names[oid]}"]
                cur[:] = [st, pth]
            spots.append((st, pth))
            engine.state = st
            for d, target in list(engine.exits().items()):
                if target in seen_s:
                    continue
                st0, pth0 = cur
                nxt = run(st0, d)
                if nxt["scene"] == st0["scene"]:
                    continue
                if _core(nxt) != _core(st0):
                    visited_scenes.add(nxt["scene"])
                    jumps.append((nxt, pth0 + [d]))
                    continue
                engine.state = nxt
                back = next((bd for bd, tgt in engine.exits().items() if tgt == st0["scene"]), None)
                if back is None:                      # one way: a step of its own, with what we carry
                    jumps.append((nxt, pth0 + [d]))
                    continue
                cur[:] = [nxt, pth0 + [d]]
                visit()
                st1, pth1 = cur
                ret = run(st1, back)
                if ret["scene"] != st0["scene"] or _core(ret) != _core(st1):
                    jumps.append((ret, pth1 + [back]))
                    cur[:] = [st0, pth0]               # cannot come back cleanly: forget that branch
                    continue
                cur[:] = [ret, pth1 + [back]]

        visit()
        return spots, cur, jumps

    def settle(state, path):
        """Collect everything first, then stand at each scene with all of it."""
        _, (full, full_path), jumps = tour(state, path, True)
        spots, _, more = tour(full, full_path, False)
        return spots, jumps + more

    start = engine.start()["state"]
    stack = [(start, [])]
    seen = set()
    won = None
    while stack and calls < budget and not won:
        state, path = stack.pop()
        if state.get("ended"):
            text = state["ended"]
            endings.setdefault(text, path)
            if win and win.lower() in text.lower():
                won = path
            continue
        spots, jumps = settle(state, path)
        key = (_core(spots[-1][0] if spots else state), min(s["scene"] for s, _ in spots) if spots else state["scene"])
        if key in seen:
            continue
        seen.add(key)
        nexts = list(jumps)
        here_core = _core(spots[-1][0]) if spots else _core(state)
        for st, pth in spots:
            for cmd in actions(st):
                nxt = run(st, cmd)
                if _core(nxt) != here_core:
                    nexts.append((nxt, pth + [cmd]))
        for nxt, pth in nexts:                    # endings now: a victory one step away is never missed
            if nxt.get("ended"):
                endings.setdefault(nxt["ended"], pth)
                if win and win.lower() in nxt["ended"].lower():
                    won = pth
        stack.extend(reversed([x for x in nexts if not x[0].get("ended")]))
    return {"venceu": won is not None, "caminho": won or [], "comandos_testados": calls,
            "estados": len(seen), "cenas_visitadas": sorted(world.scene_name(s) for s in visited_scenes),
            "cenas_nao_visitadas": sorted(world.scene_name(s) for s in world.scenes if s not in visited_scenes),
            "finais": [{"texto": t[:160], "comandos": len(p)} for t, p in endings.items()],
            "esgotou": calls >= budget}


# --- the whole build --------------------------------------------------------------------------

def check(bp: dict, previous: Optional[dict] = None, explore_budget: int = 25000) -> Tuple[Optional[dict], dict]:
    """(project or None, report). The project is None when the blueprint cannot be assembled."""
    problems = shape_problems(bp)
    if any(p["nivel"] == "erro" for p in problems):
        return None, {"ok": False, "problemas": problems}
    try:
        project, build_problems = assemble(bp, previous)
    except BlueprintError as e:
        return None, {"ok": False, "problemas": problems + e.problems}
    problems += build_problems + analyze(project)
    tests = bp.get("testes") or {}
    results, test_problems = run_tests(project, tests)
    problems += test_problems
    req = bp.get("requisitos") or {}
    sol = next((r for r in results if r["teste"] == "solução"), None)
    if req.get("puzzles") and sol is not None:
        n = len(sol.get("acoes_de_puzzle") or [])
        if n < int(req["puzzles"]):
            problems.append(problem("erro", f"requisitos.puzzles = {req['puzzles']}, mas a solução só tem {n} ações de "
                                            f"puzzle ({', '.join(sol.get('acoes_de_puzzle') or []) or 'nenhuma'}); "
                                            "andar e pegar não contam. Encadeie mais puzzles: um item que só se "
                                            "consegue com outro, uma passagem que só abre depois de algo."))
    if req.get("mortes"):
        deaths = {r["fim"] for r in results if r["teste"].startswith("morte") and r["ok"]}
        if len(deaths) < int(req["mortes"]):
            problems.append(problem("erro", f"requisitos.mortes = {req['mortes']}, mas os testes provam só "
                                            f"{len(deaths)} morte(s) diferente(s)"))
    if req.get("cenas") and len(bp.get("cenas") or []) < int(req["cenas"]):
        problems.append(problem("erro", f"requisitos.cenas = {req['cenas']}, mas a ficha tem {len(bp.get('cenas') or [])}"))
    exploration = explore(project, str(tests.get("vitoria") or ""), explore_budget) if explore_budget else None
    if exploration and exploration["venceu"]:
        replay = playtest(project, exploration["caminho"])["final_state"].get("ended") or ""
        exploration["confirmado"] = str(tests.get("vitoria") or "").lower() in replay.lower()
        exploration["acoes_de_puzzle"] = puzzle_actions(project, exploration["caminho"])
        if exploration["confirmado"] and sol and sol["ok"]:
            missing = sorted(progress(project, [str(c) for c in tests["solucao"]])
                             - progress(project, exploration["caminho"]))
            if missing:
                problems.append(problem("erro", "ATALHO: o jogador automático venceu sem passar por: "
                                        + ", ".join(missing) + ". Ações de puzzle dele: "
                                        + (", ".join(exploration["acoes_de_puzzle"]) or "nenhuma")
                                        + ". Feche a passagem ou exija isso no script que leva à vitória (uma passagem que o "
                                        "script abre mas que já existia em saidas é um furo)."))
    if exploration and exploration["cenas_nao_visitadas"]:
        problems.append(problem("aviso", "o jogador automático não chegou a: "
                                + ", ".join(exploration["cenas_nao_visitadas"])))
    world = World(project)
    report = {
        "ok": not any(p["nivel"] == "erro" for p in problems),
        "jogo": project["name"],
        "numeros": {"cenas": len(world.scenes), "objetos": len(world.objects),
                    "pegaveis": sum(1 for o in world.objects.values() if (o.get("properties") or {}).get("portable")),
                    "variantes": sum(len(s.get("variants") or []) for s in world.scenes.values())},
        "problemas": problems,
        "testes": results,
        **({"explorador": exploration} if exploration else {}),
        "arte": art_status(project),
    }
    return project, report


def art_status(project: dict) -> dict:
    scenes = project.get("scenes") or {}
    missing = [s.get("name") for s in scenes.values() if not has_art(s)]
    variants = [f"{s.get('name')}: {v.get('when')}" for s in scenes.values()
                for v in s.get("variants") or [] if not v.get("background")]
    return {"cenas_sem_arte": missing, "variantes_sem_arte": variants,
            "pronta": not missing and not variants}


def export(project: dict) -> dict:
    """A blueprint from an existing project (to start using blueprints on a game made by hand)."""
    world = World(project)
    scenes = []
    for sid, s in world.scenes.items():
        exits = {}
        for d, target in (s.get("exits") or {}).items():
            back = (world.scenes.get(target) or {}).get("exits") or {}
            opposite = dt.OPPOSITE.get(slug(d))
            name = world.scene_name(target)
            if back.get(opposite) == sid:
                exits[d] = name
            else:
                exits[d] = {"para": name, "volta": False}
        objs = []
        for o in s.get("objects", []):
            if o.get("type") == "background":
                continue
            props = o.get("properties") or {}
            entry = {"nome": o.get("name"), "descricao": (o.get("description") or "").strip()}
            if o.get("type") and o["type"] != "item":
                entry["tipo"] = o["type"]
            if props.get("portable"):
                entry["pegavel"] = True
            if props.get("hidden"):
                entry["escondido"] = True
            if props.get("aliases"):
                entry["apelidos"] = list(props["aliases"])
            if (o.get("ses") or "").strip():
                entry["script"] = o["ses"].strip() + "\n"
            objs.append(entry)
        entry = {"nome": s.get("name"), "descricao": (s.get("description") or "").strip()}
        if (s.get("ses") or "").strip():
            entry["script"] = s["ses"].strip() + "\n"
        if exits:
            entry["saidas"] = exits
        if objs:
            entry["objetos"] = objs
        variants = [{"quando": v["when"], "mudanca": v.get("change") or "(descreva a mudança)"}
                    for v in s.get("variants") or [] if v.get("when")]
        if variants:
            entry["variantes"] = variants
        scenes.append(entry)
    pres = project.get("presentation") or {}
    bp = {"nome": project.get("name"), "descricao": (project.get("launcher") or {}).get("description", ""),
          "inicio": world.scene_name(project.get("start_scene")),
          "apresentacao": {"estilo": pres.get("style", "classico"), "layout": pres.get("layout", "classico"),
                           "retro": bool(pres.get("retro"))}}
    if project.get("art"):
        bp["arte"] = {"estilo": project["art"].get("style", ""), "referencia": project["art"].get("reference", "")}
    bp["cenas"] = scenes
    bp["testes"] = {"vitoria": "", "solucao": [], "mortes": []}
    return bp


# --- on disk: projects/<name>/ficha.yaml ------------------------------------------------------

def project_dir(name: str):
    from backend.services.project_service import ROOT_DIR
    return ROOT_DIR / "projects" / name


def build(project_name: str, text: Optional[str] = None, save: bool = True,
          explore_budget: int = 25000) -> dict:
    """Checks the blueprint (the given text, or the project's ficha.yaml) and, when it has no
    errors and `save`, writes ficha.yaml and project.json (creating the project if needed).
    Returns the report."""
    from backend.services.project_service import project_service
    root = project_dir(project_name)
    if text is None:
        if not (root / FILE_NAME).exists():
            return {"ok": False, "problemas": [problem("erro", f"o projeto {project_name!r} não tem {FILE_NAME}")]}
        text = (root / FILE_NAME).read_text(encoding="utf-8")
    try:
        bp = load(text)
    except BlueprintError as e:
        return {"ok": False, "problemas": e.problems}
    if slug(bp.get("nome")) != slug(project_name):
        return {"ok": False, "problemas": [problem("erro", f"a ficha é do jogo {bp.get('nome')!r}, "
                                                           f"não de {project_name!r}")]}
    previous = project_service.load_project(project_name) if (root / "project.json").exists() else None
    project, report = check(bp, previous, explore_budget)
    report["salvo"] = False
    if project is not None and report["ok"] and save:
        for sub in ("backgrounds", "sprites", "items", "audio", "fonts"):
            (root / sub).mkdir(parents=True, exist_ok=True)
        (root / FILE_NAME).write_text(text, encoding="utf-8")
        project["name"] = project_name
        project_service.save_project_data(project_name, project)
        report["salvo"] = True
    return report


async def make_art(project_name: str, progress: Optional[Callable[[str], None]] = None) -> dict:
    """The pictures still missing: first the reference scene, then the others, then the variants.
    Each finished picture is saved at once, so this can stop and resume any time."""
    from backend.services import scene_art
    from backend.services.project_service import project_service
    say = progress or (lambda m: None)
    project = project_service.load_project(project_name)
    art = project.get("art") or {}
    style, ref = art.get("style", ""), art.get("reference", "")
    world = World(project)
    ref_id = world.find_scene(ref) or project.get("start_scene")
    order = [ref_id] + [sid for sid in project["scenes"] if sid != ref_id]
    done, failed = [], []
    for sid in order:
        scene = project_service.load_project(project_name)["scenes"].get(sid)
        if not scene or has_art(scene):
            continue
        name = scene.get("name")
        ref_name = "" if sid == ref_id else world.scene_name(ref_id)
        for attempt in (1, 2, 3):
            say(f"cena {name} (tentativa {attempt})")
            try:
                r = await scene_art.create_scene_art(project_name, sid, style, ref_name, progress=say)
                done.append(name)
                if r.get("problems"):
                    say(f"{name}: {r['problems']}")
                break
            except Exception as e:                       # noqa: BLE001 - keep going with the rest
                say(f"{name}: falhou ({str(e)[:200]})")
                if attempt == 3:
                    failed.append(f"{name}: {str(e)[:200]}")
                else:                                    # Gemini 503/429 spikes pass in a minute or two
                    await asyncio.sleep(90 * attempt)
    for sid in order:
        scene = project_service.load_project(project_name)["scenes"].get(sid) or {}
        for i, v in enumerate(scene.get("variants") or []):
            if v.get("background") or not has_art(scene):
                continue
            say(f"variante {scene.get('name')}: {v['when']}")
            try:
                await scene_art.create_variant(project_name, sid, v["when"], v.get("change") or "")
                done.append(f"{scene.get('name')}: {v['when']}")
            except Exception as e:                       # noqa: BLE001
                failed.append(f"{scene.get('name')} {v['when']}: {e}")
    return {"feitas": done, "falhas": failed, **art_status(project_service.load_project(project_name))}


# --- for the director's prompt and the docs -------------------------------------------------

REFERENCE = """FICHA DO JOGO (YAML): o jogo inteiro num arquivo só; o Saga confere, monta e testa.
nome: Nome do Jogo                      # igual ao nome do projeto
descricao: uma frase para a tela inicial
inicio: Nome da Cena                    # onde o jogador começa
apresentacao: {estilo: classico, layout: classico, retro: false}
arte:
  estilo: direção de arte (época, luz, clima, paleta), em português ou inglês
  referencia: Nome da Cena              # gerada primeiro; as outras copiam o estilo dela
cenas:
  - nome: Portaria
    descricao: 2 ou 3 frases de ambientação (sem listar saídas nem objetos)
    script: |                           # opcional, SES da cena: on enter / on first_enter
      on first_enter { say "..." }
    saidas:
      norte: Claustro                   # a volta (sul) é criada sozinha
      leste: {para: Abismo, volta: false}   # só ida
    variantes:                          # outra versão do cenário enquanto a condição valer
      - quando: flag(porta_aberta)
        mudanca: a porta de ferro agora está aberta, escada visível
    objetos:
      - nome: balcão
        descricao: aparência visual (vira imagem) e o que o jogador lê ao examinar
        tipo: movel                     # item, movel, porta, personagem...
        pegavel: false
        escondido: false                # true: só aparece com show/take num script
        apelidos: [balcao]
        script: |
          on open { show fosforos; say "..." }
requisitos: {cenas: 7, puzzles: 4, mortes: 2}   # o que o usuário pediu; a verificação cobra
testes:
  vitoria: trecho do texto do end de vitória
  solucao: [pegar lanterna, sul, abrir balcao, ...]   # comandos como o jogador digita
  mortes:
    - nome: cripta sem luz
      comandos: [sul, leste, baixo]
      fim: trecho do texto do end dessa morte
Regras: ponha em requisitos o que o usuário pediu (cenas, puzzles, mortes): "ações de puzzle" são os
comandos da solução que mudam o jogo sem ser andar ou pegar (abrir, usar X em Y, empurrar, ler o que
revela algo). Um item pegável precisa servir para algo. Nomes de cenas e de objetos únicos no jogo inteiro. Passagem que abre durante o jogo não vai em
saidas: o script que a abre faz 'link direção to cena'. A verificação aponta: script com erro, cena sem
caminho, flag testada que ninguém marca, objeto escondido que nunca aparece, item sem uso, e roda a
solução, cada morte e um jogador automático que tenta vencer sozinho."""
