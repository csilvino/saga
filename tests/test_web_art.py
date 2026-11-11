"""Scene art from three sources (scene["art_source"]): the local worker, the Gemini image API, or
pictures the creator makes on a web AI and uploads. Gemini (prompts, positions) is faked, and so is
the background remover (rembg): a light-grey sheet is cut by colour."""

import asyncio
import copy
import io

import numpy as np
import pytest
from PIL import Image, ImageDraw

from backend.services import scene_art, sprite_cut
from backend.ses import blueprint


def png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture
def game(tmp_path, monkeypatch):
    """One scene with a painted object (estante), two sprites (lanterna, chave) and a variant."""
    state = {"project": {"name": "T", "start_scene": "s1", "art": {"style": "", "reference": "Biblioteca"},
                         "scenes": {"s1": {
        "id": "s1", "name": "Biblioteca", "description": "Estantes altas.",
        "objects": [
            {"id": "bg", "name": "Background", "type": "background", "sprite": ""},
            {"id": "o1", "name": "estante", "type": "móvel", "description": "Uma estante de carvalho.",
             "position": {"x": 900, "y": 600}, "size": {"width": 100, "height": 100}, "properties": {}},
            {"id": "o2", "name": "lanterna", "type": "item", "description": "Uma lanterna a óleo.",
             "position": {"x": 400, "y": 800}, "size": {"width": 100, "height": 100},
             "properties": {"portable": True}},
            {"id": "o3", "name": "chave", "type": "item", "description": "Uma chave de ferro.",
             "position": {"x": 1400, "y": 800}, "size": {"width": 100, "height": 100},
             "properties": {"portable": True}}],
        "variants": [{"when": "flag(estante_movida)", "change": "a estante foi empurrada"}]}}},
        "asked": []}
    ps = scene_art.project_service
    monkeypatch.setattr(ps, "load_project", lambda name: copy.deepcopy(state["project"]))
    monkeypatch.setattr(ps, "load_project_path", lambda name: tmp_path)
    monkeypatch.setattr(ps, "save_project_data", lambda name, p: state.__setitem__("project", copy.deepcopy(p)))

    async def ask(contents, hint, model=None):
        state["asked"].append(hint)
        if hint == "plano de prompts":
            return {"background_prompt": "a stone library with a tall oak bookcase",
                    "sprites": [{"id": "o2", "prompt": "an oil lantern"}, {"id": "o3", "prompt": "an iron key"}]}
        if hint == "posições":
            return [{"id": "o1", "found": True, "box_2d": [300, 400, 700, 550]},
                    {"id": "o2", "found": True, "box_2d": [700, 200, 850, 280]},
                    {"id": "o3", "found": True, "box_2d": [750, 700, 850, 760]}]
        raise AssertionError(hint)

    def remove_bg(img):                    # the sheet's light grey becomes transparent
        a = np.asarray(img.convert("RGB")).astype(int)
        alpha = (np.abs(a - 200).sum(-1) > 60).astype(np.uint8) * 255
        return Image.fromarray(np.dstack([a.astype(np.uint8), alpha]))

    monkeypatch.setattr(scene_art, "_ask_json", ask)
    monkeypatch.setattr(sprite_cut, "_remove_bg", remove_bg)
    state["root"] = tmp_path
    return state


def scene(game):
    return game["project"]["scenes"]["s1"]


def obj(game, oid):
    return next(o for o in scene(game)["objects"] if o["id"] == oid)


def run(coro):
    return asyncio.run(coro)


def sheet(n=2):
    img = Image.new("RGB", (1200, 500), (200, 200, 200))
    d = ImageDraw.Draw(img)
    for i in range(n):
        d.rectangle([100 + i * 500, 100, 300 + i * 500, 400], fill=(150, 60, 20))
    return img


def test_the_source_is_per_scene_and_kept_when_the_game_is_rebuilt(game):
    assert scene_art.art_source(scene(game)) == "local"
    scene_art.set_art_source("T", "Biblioteca", "web")
    assert scene(game)["art_source"] == "web"
    with pytest.raises(scene_art.ArtError):
        scene_art.set_art_source("T", "Biblioteca", "photoshop")
    new = {"scenes": {"x": {"id": "x", "name": "Biblioteca", "objects": [], "exits": {}}}, "start_scene": "x"}
    assert blueprint.carry_art(game["project"], new)["scenes"]["s1"]["art_source"] == "web"


def test_generating_a_web_scene_is_refused_with_a_clear_message(game):
    scene_art.set_art_source("T", "Biblioteca", "web")
    with pytest.raises(scene_art.ArtError, match="na web"):
        run(scene_art.create_scene_art("T", "Biblioteca"))


def test_the_prompts_are_written_once_and_list_the_sprites_in_order(game):
    p = run(scene_art.web_prompts("T", "Biblioteca"))
    assert "bookcase" in p["background_prompt"] and "16:9" in p["background_prompt"]
    assert p["sprites"] == ["lanterna", "chave"]
    assert p["sprites_prompt"].index("oil lantern") < p["sprites_prompt"].index("iron key")
    assert p["variants"][0]["when"] == "flag(estante_movida)" and "empurrada" in p["variants"][0]["prompt"]
    run(scene_art.web_prompts("T", "Biblioteca"))
    assert game["asked"].count("plano de prompts") == 1          # kept until the scene's text changes


def test_an_uploaded_background_is_cropped_and_its_objects_located(game):
    r = run(scene_art.web_upload("T", "Biblioteca", "background", png(Image.new("RGB", (1024, 1024), "navy"))))
    bg = scene_art.background_path(scene(game))
    with Image.open(game["root"] / bg) as im:
        assert im.size == (1920, 1080)
    assert r["painted"] == ["estante"] and obj(game, "o1")["properties"]["painted"]
    assert set(scene(game)["web_art"]["boxes"]) == {"o2", "o3"}        # where the sprites will stand


def test_an_uploaded_sheet_becomes_placed_sprites(game):
    run(scene_art.web_upload("T", "Biblioteca", "background", png(Image.new("RGB", (1920, 1080), "navy"))))
    r = run(scene_art.web_upload("T", "Biblioteca", "sprites", png(sheet(2))))
    assert r["sprites"] == ["lanterna", "chave"]
    lant = obj(game, "o2")
    assert (game["root"] / lant["sprite"]).exists()
    assert lant["position"]["x"] < obj(game, "o3")["position"]["x"]  # left to right, as in the prompt
    assert 384 <= lant["position"]["x"] <= 538                         # inside the box Gemini chose


def test_a_sheet_with_the_wrong_number_of_objects_is_refused(game):
    run(scene_art.web_upload("T", "Biblioteca", "background", png(Image.new("RGB", (1920, 1080), "navy"))))
    with pytest.raises(scene_art.ArtError, match="2 objetos separados"):
        run(scene_art.web_upload("T", "Biblioteca", "sprites", png(sheet(1))))


def test_sprites_and_variants_need_the_background_first(game):
    for kind in ("sprites", "variant:0"):
        with pytest.raises(scene_art.ArtError, match="primeiro"):
            run(scene_art.web_upload("T", "Biblioteca", kind, png(sheet(2))))


def test_an_uploaded_variant_fills_that_variant(game):
    run(scene_art.web_upload("T", "Biblioteca", "background", png(Image.new("RGB", (1920, 1080), "navy"))))
    run(scene_art.web_upload("T", "Biblioteca", "variant:0", png(Image.new("RGB", (1600, 900), "black"))))
    assert scene(game)["variants"][0]["background"].startswith("backgrounds/Variant_")
    with pytest.raises(scene_art.ArtError, match="não existe"):
        run(scene_art.web_upload("T", "Biblioteca", "variant:3", png(sheet(1))))


def test_a_file_that_is_not_a_picture_is_refused(game):
    with pytest.raises(scene_art.ArtError, match="não é uma imagem"):
        run(scene_art.web_upload("T", "Biblioteca", "background", b"hello"))


def test_make_art_leaves_the_web_scenes_to_the_creator(game, monkeypatch):
    scene_art.set_art_source("T", "Biblioteca", "web")
    monkeypatch.setattr(blueprint, "art_status", lambda p: {})
    from backend.services.project_service import project_service
    said = []
    r = run(blueprint.make_art("T", said.append))
    assert r["feitas"] == [] and r["falhas"] == [] and any("na web" in s for s in said)
