"""SES v2 language and text-adventure engine.  Run: python -m pytest tests/test_ses.py"""

import pytest

from backend.ses.engine import GameEngine, playtest
from backend.ses.language import REFERENCE, SESError, parse, validate


def project():
    return {
        "start_scene": "hall",
        "scenes": {
            "hall": {
                "id": "hall", "name": "Hall de Entrada",
                "description": "Um hall empoeirado. Uma porta de carvalho ao norte.",
                "exits": {"sul": "jardim"},
                "ses": 'on first_enter { say "Você chega pela primeira vez." }',
                "objects": [
                    {"id": "bg", "name": "Background", "type": "background"},
                    {"id": "porta", "name": "Porta de Carvalho", "type": "sprite",
                     "description": "Uma porta pesada.",
                     "ses": """
                        on examine { if flag(porta_aberta) { say "Aberta." } else { say "Trancada." } }
                        on use with chave {
                            if flag(porta_aberta) { say "Já está aberta." }
                            else { set porta_aberta; link norte to biblioteca; remove chave; say "A porta abre." }
                        }"""},
                    {"id": "tapete", "name": "Tapete", "description": "Um tapete velho.",
                     "ses": 'on push { show alcapao; say "Há um alçapão sob o tapete!" }'},
                    {"id": "alcapao", "name": "Alçapão", "properties": {"hidden": True},
                     "description": "Uma tampa de madeira no chão."},
                ],
            },
            "jardim": {
                "id": "jardim", "name": "Jardim", "description": "Flores mortas.",
                "exits": {"norte": "hall"},
                "objects": [
                    {"id": "chave", "name": "Chave Enferrujada", "description": "Uma chave antiga.",
                     "properties": {"portable": True, "aliases": ["chave velha"]}},
                    {"id": "pedra", "name": "Pedra", "description": "Uma pedra enorme."},
                ],
            },
            "biblioteca": {
                "id": "biblioteca", "name": "Biblioteca", "description": "Estantes até o teto.",
                "exits": {"sul": "hall"},
                "ses": 'on enter { inc visitas }  on first_enter { end "Você encontrou a biblioteca. Fim!" }',
                "objects": [],
            },
        },
    }


# --- language --------------------------------------------------------------------------------

def test_parse_nested_if_and_conditions():
    s = parse("""
        on use with chave {
            if has(chave) and not flag(x) or (visited(hall) and flag(n) >= 2) { say "a" }
            else if flag(y) == "azul" { say "b" }
            else { say "c"; stop }
        }
        on examine { say 'ok' }  // comment
    """)
    assert [h.event for h in s.handlers] == ["use", "examine"]
    assert s.handlers[0].with_ref.name == "chave"


@pytest.mark.parametrize("src,line,col,piece", [
    ('on examine { say "x" ', 1, 22, "'}'"),
    ('on examine {\n  narrate("x")\n}', 2, 3, "comando desconhecido"),
    ('on clique { }', 1, 4, "evento desconhecido"),
    ('on examine { say "sem fim }', 1, 18, "aspas"),
    ('on examine { if has(chave { } }', 1, 27, "')'"),
    ('say "x"', 1, 1, "on <evento>"),
    ('on examine { if get_state("trancada") { } }', 1, 17, "condição"),
    ('on examine { take chave de ferro }', 1, 25, "aspas"),
])
def test_syntax_errors_have_line_and_column(src, line, col, piece):
    with pytest.raises(SESError) as e:
        parse(src)
    assert (e.value.line, e.value.col) == (line, col), str(e.value)
    assert piece in e.value.message


def test_take_without_argument_before_next_line():
    s = parse("on take {\n take\n say \"peguei\"\n}")
    assert [st.op for st in s.handlers[0].body] == ["take", "say"]
    assert s.handlers[0].body[0].args == [None]


def test_validate_warns_about_missing_references():
    r = validate('on use with martelo { goto porao; take chave }', project())
    assert r["ok"]
    msgs = " ".join(w["message"] for w in r["warnings"])
    assert "martelo" in msgs and "porao" in msgs and "chave" not in msgs


def test_validate_reports_syntax_error():
    r = validate('on examine { say }')
    assert not r["ok"] and r["errors"][0]["line"] == 1


def test_reference_mentions_every_statement():
    for word in ("say", "take", "link", "end", "has(obj)", "first_enter"):
        assert word in REFERENCE


# --- engine ----------------------------------------------------------------------------------

def test_full_playthrough():
    r = playtest(project(), [
        "norte",                         # no exit yet
        "examinar porta",
        "sul", "pegar pedra", "pegue a chave velha", "inventário", "n",
        "usar chave na porta", "examinar porta", "norte",
    ])
    steps = [" | ".join(step["messages"]) for step in r["transcript"]]
    assert "Não dá para ir" in steps[1]
    t = {step["command"]: " | ".join(step["messages"]) for step in r["transcript"]}
    assert "primeira vez" in t[None]
    assert steps[2].startswith("Trancada")
    assert t["examinar porta"] == "Aberta."
    assert "Não dá para pegar" in t["pegar pedra"]
    assert "Você pegou Chave Enferrujada" in t["pegue a chave velha"]
    assert "Chave Enferrujada" in t["inventário"]
    assert "A porta abre" in t["usar chave na porta"]
    assert "Biblioteca" in t["norte"] and "Fim!" in t["norte"]
    st = r["final_state"]
    assert st["ended"] and st["flags"] == {"porta_aberta": True}   # end stops: on enter never ran
    assert st["where"]["chave"] == "@gone"


def test_reverse_use_order_and_unknown_object():
    eng = GameEngine(project())
    st = eng.start()["state"]
    st["where"]["chave"] = "@inventory"
    out = eng.command(st, "usar porta com chave")       # the handler is on the porta, either order works
    assert "A porta abre" in " ".join(out["messages"])
    out = eng.command(out["state"], "pegar dragão")
    assert "não vê" in out["messages"][0]


def test_hidden_object_and_state_is_not_shared():
    eng = GameEngine(project())
    st0 = eng.start()["state"]
    assert "Alçapão" not in str(eng.view()["objects"])
    out = eng.command(st0, "empurrar tapete")
    assert "alçapão" in out["messages"][0]
    assert any(o["id"] == "alcapao" for o in out["view"]["objects"])
    assert st0["visible"] == {}                        # the old state was not mutated
    assert "madeira" in eng.command(out["state"], "examinar alcapao")["messages"][0]


def test_drop_and_take_back():
    eng = GameEngine(project())
    st = eng.command(eng.start()["state"], "s")["state"]
    st = eng.command(st, "pegar chave")["state"]
    st = eng.command(st, "n")["state"]
    out = eng.command(st, "largar chave")
    assert "largou" in out["messages"][0]
    assert any(o["id"] == "chave" for o in out["view"]["objects"])


def test_broken_old_script_falls_back_to_description():
    p = project()
    p["scenes"]["jardim"]["objects"][1]["ses"] = "on click { narrate('v1') }"
    eng = GameEngine(p)
    start = eng.start()
    assert any("aviso" in m and "Pedra" in m for m in start["messages"])
    st = eng.command(start["state"], "sul")["state"]
    assert eng.command(st, "examinar pedra")["messages"] == ["Uma pedra enorme."]


def test_goto_loop_is_stopped():
    p = project()
    p["scenes"]["jardim"]["ses"] = "on enter { goto hall }"
    p["scenes"]["hall"]["ses"] = "on enter { goto jardim }"
    eng = GameEngine(p)
    out = eng.start()
    assert any("ciclo" in m for m in out["messages"])


def test_runtime_error_is_reported_not_raised():
    p = project()
    p["scenes"]["hall"]["objects"][2]["ses"] = "on push { take martelo }"
    eng = GameEngine(p)
    out = eng.command(eng.start()["state"], "empurrar tapete")
    assert "martelo" in out["messages"][0] and "erro" in out["messages"][0]


def test_ended_game_refuses_commands():
    eng = GameEngine(project())
    st = eng.start()["state"]
    st["ended"] = "Fim."
    assert "terminou" in " ".join(eng.command(st, "olhar")["messages"])


def test_docs_cover_the_whole_language():
    from pathlib import Path
    from backend.ses.language import CONDITIONS, EVENTS, STATEMENTS
    doc = (Path(__file__).resolve().parents[1] / "docs" / "SES.md").read_text(encoding="utf-8")
    for word in list(STATEMENTS) + [f"{c}(" for c in CONDITIONS] + list(EVENTS):
        assert f"`{word}" in doc or f"{word} " in doc, word


def test_background_variant_follows_state():
    from backend.ses.engine import GameEngine
    project = {"start_scene": "s1", "scenes": {"s1": {
        "id": "s1", "name": "Base", "description": "Uma porta.",
        "variants": [{"when": "flag(porta_aberta)", "background": "backgrounds/aberta.png"},
                     {"when": "isto não é condição (", "background": "backgrounds/quebrada.png"}],
        "objects": [{"id": "porta", "name": "porta", "type": "porta", "description": "Uma porta.",
                     "properties": {}, "ses": 'on open { set porta_aberta; say "Abriu." }'}]}}}
    eng = GameEngine(project)
    out = eng.start()
    assert out["view"]["background"] is None
    out = eng.command(out["state"], "abrir porta")
    assert out["view"]["background"] == "backgrounds/aberta.png"


def test_classic_presentation_and_abbreviations():
    from backend.ses.engine import GameEngine
    project = {"start_scene": "s1", "presentation": {"style": "classico"}, "scenes": {
        "s1": {"id": "s1", "name": "Porão", "description": "Escuro e úmido.", "exits": {"norte": "s2"},
               "objects": [{"id": "balde", "name": "balde", "type": "item", "description": "Um balde.",
                            "properties": {"portable": True}}]},
        "s2": {"id": "s2", "name": "Sala", "description": "", "objects": []}}}
    eng = GameEngine(project)
    out = eng.start()
    text = "\n".join(out["messages"])
    assert "📍 Porão. Escuro e úmido." in text and "Vejo: balde." in text and "Saídas: norte." in text
    out = eng.command(out["state"], "PEG BALDE")           # 8-bit style abbreviation
    assert out["state"]["where"]["balde"] == "@inventory"
    out = eng.command(out["state"], "EXA BAL")
    assert "Um balde." in out["messages"]
    out = eng.command(out["state"], "N")
    assert out["view"]["scene_id"] == "s2"
