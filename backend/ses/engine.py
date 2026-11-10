"""
The text-adventure engine: the player's command -> SES handlers -> new state + messages.

The engine is stateless between requests: the whole game state is a JSON-able dict the client keeps
and sends back with every command (and that /api/game/save stores). The project is never modified
by playing.

    engine = GameEngine(project)
    out = engine.start()                       # {"state", "messages", "view"}
    out = engine.command(out["state"], "pegar a chave")
"""

from __future__ import annotations

import copy
from typing import Dict, List, Optional

from backend.ses.language import (Cond, parse_condition, DIRECTIONS, If, OBJECT_EVENTS, Ref, SESError, Script,
                                  Stmt, parse)
from backend.ses.world import World, is_scenery, obj_description, slug

INV = "@inventory"
GONE = "@gone"
MAX_DEPTH = 8           # goto -> on enter -> goto ... chains


class StopScript(Exception):
    pass


# --- Player command vocabulary (Portuguese first, a few English words) -------------------------

VERBS = {
    "look":      ["olhar", "olha", "olhe", "ver", "veja", "look"],
    "examine":   ["examinar", "examina", "examine", "x", "inspecionar", "inspeciona", "ler", "leia",
                  "observar", "observa", "analisar"],
    "take":      ["pegar", "pega", "pegue", "apanhar", "apanha", "levar", "leva", "recolher", "take", "get"],
    "drop":      ["largar", "larga", "largue", "soltar", "solta", "deixar", "deixa", "drop"],
    "use":       ["usar", "usa", "use", "utilizar", "aplicar", "colocar", "coloca", "por", "poe", "pôr", "põe",
                  "inserir", "destrancar", "destranca"],
    "open":      ["abrir", "abre", "abra", "open"],
    "close":     ["fechar", "fecha", "feche", "close"],
    "push":      ["empurrar", "empurra", "empurre", "apertar", "aperta", "pressionar", "push", "press"],
    "pull":      ["puxar", "puxa", "puxe", "pull"],
    "talk":      ["falar", "fala", "fale", "conversar", "conversa", "perguntar", "talk"],
    "go":        ["ir", "vai", "va", "vá", "andar", "anda", "seguir", "segue", "caminhar", "go", "walk"],
    "inventory": ["inventario", "inventário", "inv", "i", "mochila", "inventory"],
    "help":      ["ajuda", "help", "comandos", "?"],
}
VERB_OF = {slug(w) or w: v for v, words in VERBS.items() for w in words}


def find_verb(word: str) -> Optional[str]:
    """The verb of a word, also accepting 8-bit style abbreviations ("peg", "exa", "abr"): a
    prefix of 3+ letters that belongs to a single verb."""
    if word in VERB_OF:
        return VERB_OF[word]
    if len(word) < 3 or word in DIR_ALIASES:
        return None
    verbs = {v for w, v in VERB_OF.items() if len(w) >= 3 and w.startswith(word)}
    return verbs.pop() if len(verbs) == 1 else None

DIR_ALIASES = {
    "n": "norte", "s": "sul", "l": "leste", "e": "leste", "o": "oeste", "w": "oeste",
    "ne": "nordeste", "no": "noroeste", "se": "sudeste", "so": "sudoeste",
    "north": "norte", "south": "sul", "east": "leste", "west": "oeste",
    "subir": "cima", "sobe": "cima", "acima": "cima", "up": "cima",
    "descer": "baixo", "desce": "baixo", "abaixo": "baixo", "down": "baixo",
    "entra": "entrar", "dentro": "entrar", "sai": "sair", "fora": "sair",
}

STOPWORDS = {"o", "a", "os", "as", "um", "uma", "uns", "umas", "de", "do", "da", "dos", "das",
             "para", "pro", "pra", "ao", "à", "the", "to", "at"}
# "usar X em Y": these split the first object from the second
LINKS = {"em", "no", "na", "nos", "nas", "com", "sobre", "dentro", "on", "with", "in"}

HELP = ("Comandos: olhar, examinar <coisa>, pegar <coisa>, largar <coisa>, usar <coisa> [em <coisa>], "
        "abrir/fechar <coisa>, empurrar/puxar <coisa>, falar com <alguém>, inventário, "
        "ir <direção> (ou só norte, sul, leste, oeste, cima, baixo, entrar, sair). "
        "Pode abreviar: N, S, L, O, I, PEG CHAVE, EXA PORTA.")


def norm_dir(word: str) -> str:
    w = slug(word)
    return DIR_ALIASES.get(w, w)


class GameEngine:
    def __init__(self, project: dict):
        self.project = project
        self.world = World(project)
        self.scripts: Dict[str, Script] = {}     # owner id -> parsed script
        self.script_errors: Dict[str, SESError] = {}
        for oid, obj in self.world.objects.items():
            self._load_script(oid, obj.get("ses"))
        for sid, scene in self.world.scenes.items():
            self._load_script(sid, scene.get("ses"))

    def _load_script(self, owner, src):
        if not src or not src.strip():
            return
        try:
            self.scripts[owner] = parse(src)
        except SESError as e:
            # an old or broken script: the object still works with its description and defaults
            self.script_errors[owner] = e

    # --- state -------------------------------------------------------------------------------

    def new_state(self) -> dict:
        start = self.world.find_scene(self.project.get("start_scene")) or next(iter(self.world.scenes), None)
        return {"scene": start, "where": {}, "visible": {}, "flags": {}, "exits": {},
                "visited": [], "ended": None, "turns": 0}

    def start(self) -> dict:
        self.state = self.new_state()
        self.out: List[str] = []
        if not self.state["scene"]:
            return {"state": self.state, "messages": ["Este projeto ainda não tem cenas."], "view": None}
        for owner, err in self.script_errors.items():
            self.out.append(f"[aviso: o script de {self._owner_name(owner)} não foi carregado — {err}]")
        self._enter(self.state["scene"], 0)
        return self._result()

    def command(self, state: dict, text: str) -> dict:
        self.state = copy.deepcopy(state) if state else self.new_state()
        self.out = []
        if self.state.get("ended"):
            self.out.append(self.state["ended"])
            self.out.append("(O jogo terminou. Recomece para jogar de novo.)")
            return self._result()
        text = (text or "").strip()
        if text:
            self.state["turns"] = self.state.get("turns", 0) + 1
            self._do(text)
        return self._result()

    def _result(self) -> dict:
        return {"state": self.state, "messages": self.out, "view": self.view()}

    # where things are
    def location(self, oid: str) -> Optional[str]:
        return self.state["where"].get(oid, self.world.home.get(oid))

    def is_visible(self, oid: str) -> bool:
        if oid in self.state["visible"]:
            return self.state["visible"][oid]
        return not (self.world.objects[oid].get("properties") or {}).get("hidden", False)

    def inventory(self) -> List[str]:
        return [oid for oid, loc in self.state["where"].items() if loc == INV]

    def here(self) -> List[str]:
        sid = self.state["scene"]
        return [oid for oid in self.world.objects if self.location(oid) == sid and self.is_visible(oid)]

    def exits(self, sid: Optional[str] = None) -> Dict[str, str]:
        sid = sid or self.state["scene"]
        exits = dict(self.world.base_exits(sid))
        for d, target in (self.state["exits"].get(sid) or {}).items():
            if target:
                exits[d] = target
            else:
                exits.pop(d, None)
        return exits

    def view(self) -> Optional[dict]:
        sid = self.state.get("scene")
        if not sid:
            return None
        scene = self.world.scenes.get(sid) or {}
        return {
            "scene_id": sid,
            "scene_name": scene.get("name") or sid,
            "description": (scene.get("description") or "").strip(),
            "objects": [{"id": o, "name": self.world.object_name(o)} for o in self.here()],
            "inventory": [{"id": o, "name": self.world.object_name(o)} for o in self.inventory()],
            "exits": {d: self.world.scene_name(t) for d, t in self.exits().items()},
            "background": self.background(sid),
            "ended": self.state.get("ended"),
            "turns": self.state.get("turns", 0),
        }

    def background(self, sid: str) -> Optional[str]:
        """The scene picture for the current state: the last variant whose condition holds
        (scene["variants"] = [{"when": "flag(porta_aberta)", "background": "backgrounds/x.png"}]),
        else None (= the scene's own background)."""
        chosen = None
        for v in (self.world.scenes.get(sid) or {}).get("variants") or []:
            try:
                if v.get("background") and self._cond(sid, parse_condition(v.get("when", ""))):
                    chosen = v["background"]
            except SESError:
                continue
        return chosen

    # --- the player's command -----------------------------------------------------------------

    def _do(self, text: str):
        words = [w for w in (slug(t) for t in text.replace(",", " ").split()) if w]
        if not words:
            return
        first = words[0]
        verb = find_verb(first)

        # a bare direction ("norte", "n", "subir") or an exit name ("porta")
        if verb is None or verb == "go":
            rest = words
            if verb == "go":
                rest = [w for w in words[1:] if w not in STOPWORDS and w not in ("pela", "pelo")]
            if rest:
                d = norm_dir(rest[0]) if len(rest) == 1 else slug(" ".join(rest))
                if d in self.exits() or d in DIRECTIONS or verb == "go":
                    return self._go(d)
            if verb == "go":
                return self.say("Ir para onde? Saídas: " + self._exit_list())
            return self.say("Não entendi. Digite 'ajuda' para ver os comandos.")

        if verb == "help":
            return self.say(HELP)
        if verb == "inventory":
            inv = self.inventory()
            return self.say("Você carrega: " + ", ".join(self.world.object_name(o) for o in inv) + "."
                            if inv else "Você não carrega nada.")

        rest = [w for w in words[1:] if w not in STOPWORDS]
        if verb == "look" and not rest:
            return self._look()
        if verb == "look":
            verb = "examine"
        if verb == "talk" and rest and rest[0] == "com":
            rest = rest[1:]

        first_words, second_words = rest, []
        if verb == "use":
            for i, w in enumerate(rest):
                if w in LINKS and i > 0:
                    first_words, second_words = rest[:i], rest[i + 1:]
                    break
        if not first_words:
            return self.say({"examine": "Examinar o quê?", "take": "Pegar o quê?", "drop": "Largar o quê?",
                             "use": "Usar o quê?"}.get(verb, "Em quê?"))

        target = self._match(first_words)
        if not target:
            if verb in ("open", "close") and slug(" ".join(first_words)) in self.exits():
                return self.say("É só seguir por ali: " + " ".join(first_words) + ".")
            return self.say(f"Você não vê nenhum(a) '{' '.join(first_words)}' aqui.")
        other = None
        if second_words:
            other = self._match(second_words)
            if not other:
                return self.say(f"Você não vê nenhum(a) '{' '.join(second_words)}' aqui.")

        if verb == "use" and other:
            # 'usar chave na porta': the porta's 'on use with chave', or the chave's 'on use with porta'
            if self._run_event(other, "use", target):
                return
            if self._run_event(target, "use", other):
                return
            return self.say("Nada acontece.")
        if self._run_event(target, verb, None):
            return
        self._default(verb, target)

    def _match(self, words: List[str]) -> Optional[str]:
        """The object in scope (here + inventory) best named by these words."""
        phrase = "_".join(words)
        scope = self.here() + self.inventory()
        best, best_score = None, 0
        for oid in scope:
            names = [slug(n) for n in self.world.object_names(oid)] + [slug(oid)]
            for n in names:
                if not n:
                    continue
                n_words = [w for w in n.split("_") if w not in STOPWORDS]
                if phrase == n or phrase == "_".join(n_words):
                    score = 100
                elif all(w in n_words or any(nw.startswith(w) and len(w) >= 3 for nw in n_words) for w in words):
                    score = 10 + len(words)
                else:
                    continue
                if score > best_score:
                    best, best_score = oid, score
        return best

    def _default(self, verb: str, oid: str):
        obj = self.world.objects[oid]
        name = self.world.object_name(oid)
        props = obj.get("properties") or {}
        if verb == "examine":
            return self.say(obj_description(obj) or f"Nada de especial em {name}.")
        if verb == "take":
            if self.location(oid) == INV:
                return self.say(f"Você já está com {name}.")
            if props.get("portable"):
                self.state["where"][oid] = INV
                return self.say(f"Você pegou {name}.")
            return self.say("Não dá para pegar isso.")
        if verb == "drop":
            if self.location(oid) != INV:
                return self.say(f"Você não está com {name}.")
            self.state["where"][oid] = self.state["scene"]
            return self.say(f"Você largou {name}.")
        if verb == "use":
            return self.say(f"Usar {name} em quê?" if props.get("portable") else "Nada acontece.")
        if verb in ("open", "close"):
            return self.say("Isso não abre." if verb == "open" else "Isso não fecha.")
        if verb == "talk":
            return self.say(f"{name} não responde.")
        return self.say("Nada acontece.")

    @property
    def classic(self) -> bool:
        """'classico' presentation: the 8-bit illustrated adventure layout ("📍 Local. Vejo: ...")."""
        return (self.project.get("presentation") or {}).get("style") == "classico"

    def _look(self):
        sid = self.state["scene"]
        scene = self.world.scenes.get(sid) or {}
        name = scene.get("name") or sid
        desc = (scene.get("description") or "").strip()
        things = ", ".join(self.world.object_name(o) for o in self.here())
        if self.classic:
            self.say(f"📍 {name}." + (f" {desc}" if desc else ""))
            if things:
                self.say(f"Vejo: {things}.")
        else:
            self.say(f"== {name} ==")
            if desc:
                self.say(desc)
            if things:
                self.say(f"Você vê: {things}.")
        self.say("Saídas: " + self._exit_list())

    def _exit_list(self) -> str:
        exits = self.exits()
        return ", ".join(exits) + "." if exits else "nenhuma à vista."

    def _go(self, direction: str):
        target = self.exits().get(direction)
        if not target:
            return self.say(f"Não dá para ir para {direction}. Saídas: {self._exit_list()}")
        if target not in self.world.scenes:
            return self.say(f"[erro do projeto: a saída {direction} leva a uma cena que não existe: {target}]")
        self._enter(target, 0)

    def _enter(self, sid: str, depth: int):
        self.state["scene"] = sid
        first = sid not in self.state["visited"]
        if first:
            self.state["visited"].append(sid)
        self._look()
        script = self.scripts.get(sid)
        if not script:
            return
        for event in (("first_enter", "enter") if first else ("enter",)):
            h = script.find(event)
            if self.state.get("ended") or self.state["scene"] != sid:
                break
            if h:
                self._run(sid, h.body, depth)

    # --- running scripts ----------------------------------------------------------------------

    def _run_event(self, oid: str, event: str, with_oid: Optional[str]) -> bool:
        script = self.scripts.get(oid)
        if not script:
            return False
        h = script.find(event, [with_oid] if with_oid else None,
                        lambda ref: self._resolve_obj(ref, oid))
        if h is None or (with_oid and h.with_ref is None):
            # 'on use' without 'with' answers 'usar X', not 'usar X em Y'
            return False
        self._run(oid, h.body, 0)
        return True

    def _run(self, owner: str, body, depth: int):
        self._pending_goto = None
        try:
            self._exec_block(owner, body)
        except StopScript:
            pass
        except SESError as e:
            self.say(f"[erro no script de {self._owner_name(owner)}, {e}]")
        goto, self._pending_goto = self._pending_goto, None
        if goto and not self.state.get("ended"):
            if depth >= MAX_DEPTH:
                self.say("[erro: scripts mudando de cena em ciclo — parei]")
            else:
                self._enter(goto, depth + 1)

    def _exec_block(self, owner, body):
        for node in body:
            if isinstance(node, If):
                self._exec_block(owner, node.then if self._cond(owner, node.cond) else node.orelse)
            else:
                self._exec(owner, node)

    def _owner_name(self, owner):
        return self.world.object_name(owner) if owner in self.world.objects else self.world.scene_name(owner)

    def _resolve_obj(self, ref: Optional[Ref], owner: str) -> Optional[str]:
        if ref is None or ref.name in ("self", "this"):
            return owner if owner in self.world.objects else None
        return self.world.find_object(ref.name, prefer=self.here() + self.inventory())

    def _obj(self, ref, owner) -> str:
        oid = self._resolve_obj(ref, owner)
        if not oid:
            name = ref.name if ref else "self"
            raise SESError(f"objeto {name!r} não existe", ref.line if ref else 0, ref.col if ref else 0)
        return oid

    def _scene(self, ref) -> str:
        sid = self.world.find_scene(ref.name)
        if not sid:
            raise SESError(f"cena {ref.name!r} não existe", ref.line, ref.col)
        return sid

    def _exec(self, owner: str, s: Stmt):
        op, a = s.op, s.args
        st = self.state
        if op == "say":
            self.say(a[0])
        elif op == "take":
            st["where"][self._obj(a[0], owner)] = INV
        elif op == "drop":
            st["where"][self._obj(a[0], owner)] = st["scene"]
        elif op == "remove":
            st["where"][self._obj(a[0], owner)] = GONE
        elif op == "show":
            st["visible"][self._obj(a[0], owner)] = True
        elif op == "hide":
            st["visible"][self._obj(a[0], owner)] = False
        elif op == "move":
            st["where"][self._obj(a[0], owner)] = self._scene(a[1])
        elif op == "goto":
            self._pending_goto = self._scene(a[0])
        elif op == "link":
            where = self._scene(a[2]) if a[2] else st["scene"]
            st["exits"].setdefault(where, {})[norm_dir(a[0].name)] = self._scene(a[1])
        elif op == "unlink":
            where = self._scene(a[1]) if a[1] else st["scene"]
            st["exits"].setdefault(where, {})[norm_dir(a[0].name)] = None
        elif op == "set":
            st["flags"][slug(a[0].name)] = a[1]
        elif op == "clear":
            st["flags"].pop(slug(a[0].name), None)
        elif op in ("inc", "dec"):
            key = slug(a[0].name)
            cur = st["flags"].get(key, 0)
            cur = cur if isinstance(cur, (int, float)) and not isinstance(cur, bool) else 0
            st["flags"][key] = cur + (a[1] if op == "inc" else -a[1])
        elif op == "end":
            st["ended"] = a[0]
            self.say(a[0])
            raise StopScript()
        elif op == "stop":
            raise StopScript()

    def _cond(self, owner, c: Cond) -> bool:
        if c.kind == "const":
            return c.args[0]
        if c.kind == "not":
            return not self._cond(owner, c.args[0])
        if c.kind == "and":
            return self._cond(owner, c.args[0]) and self._cond(owner, c.args[1])
        if c.kind == "or":
            return self._cond(owner, c.args[0]) or self._cond(owner, c.args[1])
        if c.kind == "compare":
            _, ref = c.args[0].args
            value = self.state["flags"].get(slug(ref.name))
            op, lit = c.args[1], c.args[2]
            if op in ("==", "!="):
                if value is None and lit is False:
                    value = False
                return (value == lit) == (op == "==")
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                value = 0
            if not isinstance(lit, (int, float)):
                raise SESError("comparação com < ou > precisa de número", c.line, c.col)
            return {">": value > lit, "<": value < lit, ">=": value >= lit, "<=": value <= lit}[op]
        name, ref = c.args
        if name == "flag":
            v = self.state["flags"].get(slug(ref.name))
            return v not in (None, False, 0, "")
        if name == "has":
            return self.location(self._obj(ref, owner)) == INV
        if name == "here":
            oid = self._obj(ref, owner)
            return self.location(oid) == self.state["scene"] and self.is_visible(oid)
        if name == "in":
            return self.state["scene"] == self._scene(ref)
        if name == "visited":
            return self._scene(ref) in self.state["visited"]
        raise SESError(f"condição {name!r} desconhecida", c.line, c.col)   # pragma: no cover

    def say(self, text: str):
        self.out.append(text)


def playtest(project: dict, commands: List[str]) -> dict:
    """Plays a list of commands from the start; returns the transcript (used by the AI and tests)."""
    engine = GameEngine(project)
    out = engine.start()
    transcript = [{"command": None, "messages": out["messages"]}]
    state = out["state"]
    for cmd in commands:
        out = engine.command(state, cmd)
        state = out["state"]
        transcript.append({"command": cmd, "messages": out["messages"]})
        if state.get("ended"):
            break
    return {"transcript": transcript, "final_state": state, "view": out["view"],
            "script_errors": {engine._owner_name(k): str(v) for k, v in engine.script_errors.items()}}
