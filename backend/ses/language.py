"""
SES — Saga Engine Script, version 2.

A small language for the logic of text adventures, written by people and by the AI director.
Everything described in REFERENCE is implemented here (parser) and in engine.py (execution);
nothing else is accepted: unknown words are syntax errors with a line and a column.

A script is a list of handlers:

    on examine { say "Uma chave enferrujada." }
    on use with chave {
        if flag(porta_aberta) { say "Já está aberta." }
        else { set porta_aberta; link norte to biblioteca; say "A porta range e abre." }
    }
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, List, Optional, Union

# --- What the language knows -----------------------------------------------------------------

# events an object can handle (the player's verbs), and events of a scene
OBJECT_EVENTS = ("examine", "take", "drop", "use", "open", "close", "push", "pull", "talk")
SCENE_EVENTS = ("enter", "first_enter")
EVENTS = OBJECT_EVENTS + SCENE_EVENTS

# statement -> argument shape (used by the parser and by REFERENCE)
STATEMENTS = {
    "say":    'say "texto"                     mostra um texto ao jogador',
    "take":   "take [obj]                      põe o objeto (ou este) no inventário",
    "drop":   "drop [obj]                      larga o objeto na cena atual",
    "remove": "remove [obj]                    tira o objeto do jogo (some de vez)",
    "show":   "show obj                        mostra um objeto escondido (propriedade hidden)",
    "hide":   "hide [obj]                      esconde o objeto",
    "move":   "move obj to cena                leva o objeto para outra cena",
    "goto":   "goto cena                       leva o jogador para outra cena",
    "link":   "link direção to cena [in cena]  abre/cria uma saída (na cena atual ou na indicada)",
    "unlink": "unlink direção [in cena]        fecha uma saída",
    "set":    "set flag  |  set flag = valor  marca uma flag (true) ou dá um valor (número ou texto)",
    "clear":  "clear flag                      apaga a flag",
    "inc":    "inc flag [n]                    soma n (1) à flag",
    "dec":    "dec flag [n]                    subtrai n (1) da flag",
    "end":    'end "texto"                     termina o jogo com esse texto (vitória ou fim)',
    "play":   'play "descrição do som"         toca um som (a geração cria o som pela descrição)',
    "stop":   "stop                            para o script aqui",
}

CONDITIONS = {
    "has":     "has(obj)          o jogador tem o objeto",
    "here":    "here(obj)         o objeto está visível na cena atual",
    "flag":    "flag(f)           a flag está marcada  (flag(f) == 3, flag(f) > 1, flag(f) == \"x\")",
    "in":      "in(cena)          o jogador está nessa cena",
    "visited": "visited(cena)     o jogador já esteve na cena",
}

DIRECTIONS = ("norte", "sul", "leste", "oeste", "nordeste", "noroeste", "sudeste", "sudoeste",
              "cima", "baixo", "entrar", "sair")


# --- Errors ----------------------------------------------------------------------------------

class SESError(Exception):
    def __init__(self, message: str, line: int = 0, col: int = 0):
        super().__init__(message)
        self.message, self.line, self.col = message, line, col

    def __str__(self):
        return f"linha {self.line}, coluna {self.col}: {self.message}" if self.line else self.message

    def as_dict(self):
        return {"line": self.line, "col": self.col, "message": self.message}


# --- Tokens ----------------------------------------------------------------------------------

@dataclass
class Token:
    kind: str          # name, string, number, op, eof
    value: Any
    line: int
    col: int


TOKEN_RE = re.compile(r"""
    (?P<ws>[ \t\r]+)
  | (?P<nl>\n)
  | (?P<comment>//[^\n]*|\#[^\n]*)
  | (?P<string>"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*')
  | (?P<number>-?\d+(?:\.\d+)?)
  | (?P<name>[A-Za-z_À-ÿ][A-Za-z0-9_À-ÿ]*)
  | (?P<op>==|!=|>=|<=|[{}();=<>!,])
""", re.VERBOSE)


def tokenize(src: str) -> List[Token]:
    tokens, pos, line, line_start = [], 0, 1, 0
    while pos < len(src):
        m = TOKEN_RE.match(src, pos)
        col = pos - line_start + 1
        if not m:
            ch = src[pos]
            if ch in "\"'":
                raise SESError("texto sem aspas de fechamento", line, col)
            raise SESError(f"caractere inesperado {ch!r}", line, col)
        kind = m.lastgroup
        text = m.group()
        if kind == "nl":
            line += 1
            line_start = m.end()
        elif kind == "string":
            body = text[1:-1]
            body = re.sub(r"\\(.)", lambda e: {"n": "\n", "t": "\t"}.get(e.group(1), e.group(1)), body)
            tokens.append(Token("string", body, line, col))
        elif kind == "number":
            tokens.append(Token("number", float(text) if "." in text else int(text), line, col))
        elif kind in ("name", "op"):
            tokens.append(Token(kind, text, line, col))
        pos = m.end()
    tokens.append(Token("eof", None, line, pos - line_start + 1))
    return tokens


# --- AST -------------------------------------------------------------------------------------

@dataclass
class Ref:
    """A reference to an object or a scene: an id, a name, or 'self'."""
    name: str
    line: int
    col: int


@dataclass
class Stmt:
    op: str
    args: List[Any]
    line: int
    col: int


@dataclass
class If:
    cond: Any
    then: List[Any]
    orelse: List[Any]
    line: int
    col: int


@dataclass
class Cond:
    kind: str                    # call, not, and, or, const
    args: List[Any] = field(default_factory=list)
    line: int = 0
    col: int = 0


@dataclass
class Handler:
    event: str
    with_ref: Optional[Ref]
    body: List[Union[Stmt, If]]
    line: int


@dataclass
class Script:
    handlers: List[Handler]

    def find(self, event: str, with_obj_ids=None, resolve=None) -> Optional[Handler]:
        """The handler for an event: 'on E with X' when X matches, else plain 'on E'."""
        plain = None
        for h in self.handlers:
            if h.event != event:
                continue
            if h.with_ref is None:
                plain = plain or h
            elif with_obj_ids and resolve and resolve(h.with_ref) in with_obj_ids:
                return h
        return plain


# --- Parser ----------------------------------------------------------------------------------

class Parser:
    def __init__(self, src: str):
        self.tokens = tokenize(src)
        self.i = 0

    # helpers
    @property
    def tok(self) -> Token:
        return self.tokens[self.i]

    def advance(self) -> Token:
        t = self.tokens[self.i]
        self.i += 1
        return t

    def error(self, msg, tok=None):
        t = tok or self.tok
        return SESError(msg, t.line, t.col)

    def at(self, kind, value=None):
        t = self.tok
        return t.kind == kind and (value is None or t.value == value)

    def at_word(self, *words):
        return self.tok.kind == "name" and self.tok.value in words

    def expect_op(self, op):
        if not self.at("op", op):
            got = "fim do script" if self.tok.kind == "eof" else repr(self.tok.value)
            raise self.error(f"esperava '{op}', encontrei {got}")
        return self.advance()

    def expect_word(self, word):
        if not self.at_word(word):
            got = "fim do script" if self.tok.kind == "eof" else repr(self.tok.value)
            raise self.error(f"esperava '{word}', encontrei {got}")
        return self.advance()

    def ref(self, what="um objeto ou cena") -> Ref:
        t = self.tok
        if t.kind in ("name", "string"):
            self.advance()
            return Ref(str(t.value), t.line, t.col)
        got = "fim do script" if t.kind == "eof" else repr(t.value)
        raise self.error(f"esperava {what}, encontrei {got}")

    def end_of_statement(self):
        return self.at("op", ";") or self.at("op", "}") or self.tok.kind == "eof"

    def statement_starts(self):
        return self.at_word(*STATEMENTS, "if")

    def optional_ref(self) -> Optional[Ref]:
        """An argument that may be left out (take, drop, remove, hide): absent before ';', '}',
        a new line's statement or the end."""
        if self.end_of_statement():
            return None
        if self.tok.kind == "name" and self.tok.value in STATEMENTS or self.at_word("if", "else"):
            if self.tokens[self.i - 1].line != self.tok.line:
                return None
        return self.ref()

    # grammar
    def parse(self) -> Script:
        handlers = []
        while self.tok.kind != "eof":
            handlers.append(self.handler())
        return Script(handlers)

    def handler(self) -> Handler:
        start = self.tok
        if not self.at_word("on"):
            got = repr(self.tok.value)
            raise self.error(f"um script é uma lista de 'on <evento> {{ ... }}'; encontrei {got}")
        self.advance()
        ev = self.tok
        if ev.kind != "name" or ev.value not in EVENTS:
            raise self.error(f"evento desconhecido {ev.value!r}; eventos: {', '.join(EVENTS)}", ev)
        self.advance()
        with_ref = None
        if self.at_word("with"):
            self.advance()
            with_ref = self.ref("o objeto depois de 'with'")
        body = self.block()
        return Handler(ev.value, with_ref, body, start.line)

    def block(self) -> list:
        self.expect_op("{")
        body = []
        while not self.at("op", "}"):
            if self.tok.kind == "eof":
                raise self.error("bloco sem '}' de fechamento")
            if self.at("op", ";"):
                self.advance()
                continue
            body.append(self.statement())
            t, prev = self.tok, self.tokens[self.i - 1]
            if t.kind in ("name", "string", "number") and t.line == prev.line and not isinstance(body[-1], If):
                raise self.error(f"esperava ';' ou nova linha antes de {t.value!r} — "
                                 f"nomes com espaço vão entre aspas, ex.: \"chave de ferro\"")
        self.advance()
        return body

    def statement(self):
        t = self.tok
        if t.kind != "name":
            raise self.error(f"esperava um comando, encontrei {t.value!r}")
        word = t.value
        if word == "if":
            return self.if_statement()
        if word not in STATEMENTS:
            raise self.error(f"comando desconhecido {word!r}; comandos: {', '.join(STATEMENTS)}, if")
        self.advance()
        line, col = t.line, t.col
        if word in ("say", "end", "play"):
            s = self.tok
            if s.kind != "string":
                raise self.error(f"'{word}' precisa de um texto entre aspas")
            self.advance()
            return Stmt(word, [s.value], line, col)
        if word in ("take", "drop", "remove", "hide"):
            return Stmt(word, [self.optional_ref()], line, col)
        if word == "show":
            return Stmt(word, [self.ref()], line, col)
        if word == "goto":
            return Stmt(word, [self.ref("uma cena")], line, col)
        if word == "move":
            obj = self.ref()
            self.expect_word("to")
            return Stmt(word, [obj, self.ref("uma cena")], line, col)
        if word == "link":
            d = self.ref("uma direção")
            self.expect_word("to")
            target = self.ref("uma cena")
            where = None
            if self.at_word("in"):
                self.advance()
                where = self.ref("uma cena")
            return Stmt(word, [d, target, where], line, col)
        if word == "unlink":
            d = self.ref("uma direção")
            where = None
            if self.at_word("in"):
                self.advance()
                where = self.ref("uma cena")
            return Stmt(word, [d, where], line, col)
        if word == "set":
            name = self.ref("o nome da flag")
            value = True
            if self.at("op", "="):
                self.advance()
                value = self.literal()
            return Stmt(word, [name, value], line, col)
        if word == "clear":
            return Stmt(word, [self.ref("o nome da flag")], line, col)
        if word in ("inc", "dec"):
            name = self.ref("o nome da flag")
            n = 1
            if self.tok.kind == "number":
                n = self.advance().value
            return Stmt(word, [name, n], line, col)
        if word == "stop":
            return Stmt(word, [], line, col)
        raise self.error(f"comando {word!r} não tratado")    # pragma: no cover

    def literal(self):
        t = self.tok
        if t.kind in ("number", "string"):
            self.advance()
            return t.value
        if self.at_word("true", "false"):
            self.advance()
            return t.value == "true"
        raise self.error("esperava um número, um texto entre aspas, true ou false")

    def if_statement(self) -> If:
        t = self.advance()
        cond = self.condition()
        then = self.block()
        orelse = []
        if self.at_word("else"):
            self.advance()
            orelse = [self.if_statement()] if self.at_word("if") else self.block()
        return If(cond, then, orelse, t.line, t.col)

    # conditions: or > and > not > comparison/call
    def condition(self):
        left = self.cond_and()
        while self.at_word("or"):
            t = self.advance()
            left = Cond("or", [left, self.cond_and()], t.line, t.col)
        return left

    def cond_and(self):
        left = self.cond_not()
        while self.at_word("and"):
            t = self.advance()
            left = Cond("and", [left, self.cond_not()], t.line, t.col)
        return left

    def cond_not(self):
        if self.at_word("not") or self.at("op", "!"):
            t = self.advance()
            return Cond("not", [self.cond_not()], t.line, t.col)
        return self.cond_atom()

    def cond_atom(self):
        t = self.tok
        if self.at("op", "("):
            self.advance()
            c = self.condition()
            self.expect_op(")")
            return c
        if self.at_word("true", "false"):
            self.advance()
            return Cond("const", [t.value == "true"], t.line, t.col)
        if t.kind == "name" and t.value in CONDITIONS:
            self.advance()
            self.expect_op("(")
            arg = self.ref()
            self.expect_op(")")
            call = Cond("call", [t.value, arg], t.line, t.col)
            if t.value == "flag" and self.tok.kind == "op" and self.tok.value in ("==", "!=", ">", "<", ">=", "<="):
                op = self.advance().value
                return Cond("compare", [call, op, self.literal()], t.line, t.col)
            return call
        got = "fim do script" if t.kind == "eof" else repr(t.value)
        raise self.error(f"esperava uma condição ({', '.join(CONDITIONS)}, not, and, or), encontrei {got}")


def parse(src: str) -> Script:
    """Parses a script; raises SESError with the line and column of the first error."""
    return Parser(src or "").parse()


def parse_condition(src: str) -> Cond:
    """Parses a lone condition, e.g. 'flag(porta_aberta)' (scene background variants)."""
    p = Parser(" ".join((src or "").split()))
    if p.tok.kind == "eof":
        raise SESError("condição vazia", 1, 1)
    c = p.condition()
    if p.tok.kind != "eof":
        raise p.error(f"sobrou {p.tok.value!r} depois da condição")
    return c


# --- Validation against a project -----------------------------------------------------------

def walk(body):
    for node in body:
        yield node
        if isinstance(node, If):
            yield from walk(node.then)
            yield from walk(node.orelse)


def walk_conds(c):
    if isinstance(c, Cond):
        yield c
        for a in c.args:
            yield from walk_conds(a)


def validate(src: str, project: dict = None, owner_kind: str = "object") -> dict:
    """
    {"ok": bool, "errors": [{line, col, message}], "warnings": [...]}.
    Errors: syntax. Warnings: references to objects or scenes that do not exist (yet), events that
    do not fit the owner (an object never receives 'enter').
    """
    try:
        script = parse(src)
    except SESError as e:
        return {"ok": False, "errors": [e.as_dict()], "warnings": []}
    warnings = []
    events = OBJECT_EVENTS if owner_kind == "object" else SCENE_EVENTS
    for h in script.handlers:
        if h.event not in events:
            warnings.append({"line": h.line, "col": 1, "message":
                             f"'on {h.event}' nunca acontece em {'um objeto' if owner_kind == 'object' else 'uma cena'}"})
    if project is not None:
        from backend.ses.world import World
        world = World(project)

        def check(ref, kind):
            if ref is None or ref.name in ("self", "this"):
                return
            found = world.find_object(ref.name) if kind == "object" else world.find_scene(ref.name)
            if not found:
                warnings.append({"line": ref.line, "col": ref.col,
                                 "message": f"{'objeto' if kind == 'object' else 'cena'} {ref.name!r} não existe (ainda)"})

        for h in script.handlers:
            check(h.with_ref, "object")
            for node in walk(h.body):
                if isinstance(node, Stmt):
                    if node.op in ("take", "drop", "remove", "show", "hide"):
                        check(node.args[0], "object")
                    elif node.op == "move":
                        check(node.args[0], "object")
                        check(node.args[1], "scene")
                    elif node.op == "goto":
                        check(node.args[0], "scene")
                    elif node.op == "link":
                        check(node.args[1], "scene")
                        check(node.args[2], "scene")
                    elif node.op == "unlink":
                        check(node.args[1], "scene")
                elif isinstance(node, If):
                    for c in walk_conds(node.cond):
                        if c.kind == "call" and c.args[0] in ("has", "here"):
                            check(c.args[1], "object")
                        elif c.kind == "call" and c.args[0] in ("in", "visited"):
                            check(c.args[1], "scene")
    return {"ok": True, "errors": [], "warnings": warnings}


# --- Reference (for the AI prompt, the README and the editor) --------------------------------

REFERENCE = f"""SES (Saga Engine Script) — a lógica do jogo. Um script é uma lista de handlers:
  on <evento> {{ comandos }}            on <evento> with <obj> {{ ... }}  (ex.: usar chave na porta)
Eventos de objeto: {', '.join(OBJECT_EVENTS)}.  Eventos de cena: {', '.join(SCENE_EVENTS)}.
Se o objeto tem 'on <evento>', ele substitui o comportamento padrão (ex.: 'on take' decide se pega).
Sem handler: examine mostra a descrição; take pega se o objeto for portable; o resto diz que nada acontece.

Comandos (separe com ';' ou quebra de linha):
""" + "\n".join("  " + s for s in STATEMENTS.values()) + """
  if <condição> { ... } else if <condição> { ... } else { ... }

Condições (combine com not, and, or e parênteses):
""" + "\n".join("  " + c for c in CONDITIONS.values()) + f"""

Referências: id ou nome do objeto/cena (nomes com espaço entre aspas); 'self' é o próprio objeto.
Direções: {', '.join(DIRECTIONS)} (ou qualquer nome de saída, como "porta").
Comentários: // ou #.

Exemplo (objeto 'porta' na cena 'hall'):
  on examine {{ if flag(porta_aberta) {{ say "A porta está aberta." }} else {{ say "Uma porta de carvalho, trancada." }} }}
  on open {{ if flag(porta_aberta) {{ say "Já está aberta." }} else {{ say "Está trancada." }} }}
  on use with chave {{
    if flag(porta_aberta) {{ say "Já está aberta." }}
    else {{ set porta_aberta; link norte to biblioteca; remove chave; say "A chave gira e a porta se abre." }}
  }}
"""
