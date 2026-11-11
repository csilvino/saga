"""Looping animations from the ficha (backend/ses/animation.py): parsing, the built project, the
art for moving parts (a clock's pendulum) and the rebuild that keeps them."""

import asyncio
import copy

import numpy as np
import pytest
from PIL import Image, ImageDraw

from backend.services import scene_art, sprite_cut
from backend.ses import animation, blueprint as bp

FICHA = """
nome: Relojoaria
inicio: Loja
cenas:
  - nome: Loja
    descricao: Uma loja de relógios.
    animacao: {tipo: tremular, cor: amarelo}
    objetos:
      - nome: relógio de pêndulo
        descricao: Um relógio de pêndulo alto de madeira escura.
        partes:
          - nome: pêndulo
            descricao: Um pêndulo de latão com um disco dourado.
            animacao: {tipo: balanco, angulo: 12, periodo: 2}
            onde: [0.5, 0.5]
            altura: 0.4
      - nome: vela
        descricao: Uma vela acesa.
        animacao: tremular
      - nome: placa
        descricao: Uma placa pendurada.
        animacao: {tipo: balanco}
    script: |
      on enter { end "Fim. Vitória" }
"""


def build(text=FICHA, previous=None):
    p, problems = bp.assemble(bp.load(text), previous)
    assert not [x for x in problems if x["nivel"] == "erro"], problems
    return p


def objs(p):
    s = next(iter(p["scenes"].values()))
    return {o["name"]: o for o in s["objects"]}


def test_a_type_alone_takes_the_defaults_and_names_become_colours():
    assert animation.parse_effect("balanço") == ({"type": "swing", "amount": 8, "period": 2.0}, [])
    e, errs = animation.parse_effect({"tipo": "pulsar", "intensidade": 0.8, "cor": "roxo"})
    assert e == {"type": "pulse", "amount": 0.8, "period": 2.5, "color": "#c88cff"} and not errs
    assert animation.parse_effect("tremular")[0]["color"] == "#ffa040"


@pytest.mark.parametrize("raw, says", [
    ({"tipo": "girar"}, "não existe"),
    ({"tipo": "balanco", "angulo": 500}, "entre"),
    ({"tipo": "balanco", "amplitude": 5}, "use 'angulo'"),
    ({"tipo": "flutuar", "cor": "azul"}, "só vale"),
    ({"tipo": "pulsar", "cor": "cor-de-burro"}, "desconhecida"),
    ({"tipo": "balanco", "velocidade": 2}, "não conheço"),
    ({"tipo": "balanco", "periodo": 0}, "periodo"),
])
def test_mistakes_are_explained(raw, says):
    assert any(says in m for m in animation.parse_effect(raw)[1])


def test_the_ficha_checks_animations_and_parts():
    bad = FICHA.replace("angulo: 12", "angulo: 99").replace("onde: [0.5, 0.5]", "onde: [2, 0.5]")
    msgs = [p["msg"] for p in bp.shape_problems(bp.load(bad))]
    assert any("pêndulo" in m and "'angulo'" in m for m in msgs)
    assert any("'onde'" in m for m in msgs)


def test_the_built_project_has_the_effects_and_moving_objects_become_sprites():
    p = build()
    o = objs(p)
    clock, candle, sign = o["relógio de pêndulo"], o["vela"], o["placa"]
    assert clock["parts"][0]["effect"] == {"type": "swing", "amount": 12, "period": 2}
    assert clock["parts"][0]["at"] == {"x": 0.5, "y": 0.5} and clock["parts"][0]["height"] == 0.4
    assert candle["effect"]["type"] == "flicker"
    assert next(iter(p["scenes"].values()))["effect"]["color"] == "#ffd75a"
    assert scene_art.is_sprite(clock) and scene_art.is_sprite(sign)      # parts / swinging pixels
    assert not scene_art.is_sprite(candle)                               # only light on top: painted


def test_the_sheet_has_the_object_drawn_without_its_part_then_the_part():
    clock = objs(build())["relógio de pêndulo"]
    items = scene_art.sheet_items([clock])
    assert [i["id"] for i in items] == [clock["id"], clock["id"] + "#0"]
    assert "WITHOUT its pêndulo" in items[0]["description"]
    assert "hanging straight down" in items[1]["description"]


def test_a_part_hangs_from_its_point_on_the_object():
    part = Image.new("RGBA", (40, 200), (200, 160, 40, 255))
    img, rect = sprite_cut.fit_part(part, [100, 100, 300, 500], {"x": 0.5, "y": 0.5}, 0.4)
    assert rect["y"] == 0.5 and rect["h"] == 0.4                         # 160 px of the object's 400
    assert abs(rect["x"] + rect["w"] / 2 - 0.5) < 1e-3                   # centred on the hanging point
    assert abs(rect["w"] - 32 / 200) < 1e-3                              # its own proportions


def test_a_rebuild_keeps_the_part_pictures_while_the_part_is_the_same():
    old = build()
    part = objs(old)["relógio de pêndulo"]["parts"][0]
    part.update(sprite="sprites/Part_x.png", rect={"x": 0.4, "y": 0.5, "w": 0.2, "h": 0.4})
    again = objs(build(previous=copy.deepcopy(old)))["relógio de pêndulo"]["parts"][0]
    assert again["sprite"] == "sprites/Part_x.png" and again["effect"]["amount"] == 12
    changed = objs(build(FICHA.replace("disco dourado", "disco de prata"), copy.deepcopy(old)))
    assert not changed["relógio de pêndulo"]["parts"][0].get("sprite")    # a new description: a new picture


def test_export_writes_the_animations_back():
    exported = bp.export(build())
    scene = exported["cenas"][0]
    assert scene["animacao"]["tipo"] == "tremular" and scene["animacao"]["cor"] == "amarelo"
    clock = next(o for o in scene["objetos"] if o["nome"] == "relógio de pêndulo")
    assert clock["partes"][0]["animacao"] == {"tipo": "balanco", "angulo": 12, "periodo": 2}
    again = bp.assemble(bp.load(bp.dump(exported)))[0]
    assert objs(again)["relógio de pêndulo"]["parts"][0]["effect"]["amount"] == 12


def test_an_uploaded_sheet_places_the_part_on_its_object(tmp_path, monkeypatch):
    p = build()
    sid = next(iter(p["scenes"]))
    state = {"p": p}
    ps = scene_art.project_service
    monkeypatch.setattr(ps, "load_project", lambda name: copy.deepcopy(state["p"]))
    monkeypatch.setattr(ps, "load_project_path", lambda name: tmp_path)
    monkeypatch.setattr(ps, "save_project_data", lambda name, x: state.__setitem__("p", copy.deepcopy(x)))
    (tmp_path / "backgrounds").mkdir()
    Image.new("RGB", (1920, 1080), "navy").save(tmp_path / "backgrounds" / "bg.png")
    scene_art.set_background(state["p"]["scenes"][sid], "backgrounds/bg.png")
    clock_id = objs(state["p"])["relógio de pêndulo"]["id"]
    sign_id = objs(state["p"])["placa"]["id"]
    state["p"]["scenes"][sid]["web_art"] = {"boxes": {clock_id: [800, 200, 1000, 900], sign_id: [100, 100, 300, 300]}}

    def remove_bg(img):
        a = np.asarray(img.convert("RGB")).astype(int)
        alpha = (np.abs(a - 200).sum(-1) > 60).astype(np.uint8) * 255
        return Image.fromarray(np.dstack([a.astype(np.uint8), alpha]))
    monkeypatch.setattr(sprite_cut, "_remove_bg", remove_bg)
    sheet = Image.new("RGB", (1200, 500), (200, 200, 200))
    d = ImageDraw.Draw(sheet)
    for x0, w, h in ((80, 160, 380), (480, 40, 200), (800, 200, 120)):    # clock, pendulum, sign
        d.rectangle([x0, 60, x0 + w, 60 + h], fill=(120, 60, 20))
    import io
    buf = io.BytesIO()
    sheet.save(buf, "PNG")
    r = asyncio.run(scene_art.web_upload("T", sid, "sprites", buf.getvalue()))
    assert r["sprites"] == ["relógio de pêndulo", "relógio de pêndulo/pêndulo", "placa"]
    clock = objs(state["p"])["relógio de pêndulo"]
    part = clock["parts"][0]
    assert (tmp_path / part["sprite"]).exists() and part["rect"]["y"] == 0.5
    assert scene_art.scene_art_list(state["p"])[0]["sprites_done"] == 3
