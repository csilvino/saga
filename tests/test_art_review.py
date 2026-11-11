"""The art reviewer: Gemini's verdicts are faked, the image model too; what is tested is the loop
(fix by editing, redo from the background, give up after REVIEW_ROUNDS and tell the creator)."""

import asyncio
import copy

import pytest
from PIL import Image

from backend.services import scene_art
from backend.ses import blueprint

OK = {"ok": True, "problems": [], "fix": "", "redo": False}


def bad(problem="a passagem não aparece", fix="Open a dark archway; keep everything else identical", redo=False):
    return {"ok": False, "problems": [problem], "fix": fix, "redo": redo}


@pytest.fixture
def game(tmp_path, monkeypatch):
    """A one-scene project on disk, a fake Gemini (verdicts from a queue) and a fake image editor."""
    (tmp_path / "backgrounds").mkdir()
    Image.new("RGB", (64, 36), "navy").save(tmp_path / "backgrounds/Scene_base.png")
    state = {"project": {"name": "T", "start_scene": "s1", "scenes": {"s1": {
        "id": "s1", "name": "Biblioteca", "description": "Estantes altas.",
        "objects": [
            {"id": "bg", "name": "Background", "type": "background", "sprite": "backgrounds/Scene_base.png"},
            {"id": "o1", "name": "estante", "type": "móvel", "description": "Uma estante de carvalho.",
             "position": {"x": 769, "y": 655}, "size": {"width": 160, "height": 228},
             "properties": {"painted": True}}],
        "variants": [{"when": "flag(estante_movida)", "change": "a estante foi empurrada, passagem à mostra"}]}}},
        "verdicts": [], "edits": [], "asked": []}
    ps = scene_art.project_service
    monkeypatch.setattr(ps, "load_project", lambda name: copy.deepcopy(state["project"]))
    monkeypatch.setattr(ps, "load_project_path", lambda name: tmp_path)
    monkeypatch.setattr(ps, "save_project_data", lambda name, p: state.__setitem__("project", copy.deepcopy(p)))

    async def ask(contents, hint, model=None):
        state["asked"].append(hint)
        if hint == "instrução de edição":
            return {"instruction": "Slide the bookcase left; a dark archway opens"}
        if hint == "posições":
            return [{"id": "o1", "found": True, "box_2d": [500, 300, 800, 450]}]
        return state["verdicts"].pop(0)

    async def edit(root, base, instruction):
        state["edits"].append((base, instruction))
        return Image.new("RGB", (64, 36), "black")

    monkeypatch.setattr(scene_art, "_ask_json", ask)
    monkeypatch.setattr(scene_art, "_apply_edit", edit)
    state["root"] = tmp_path
    return state


def variant(state):
    return state["project"]["scenes"]["s1"]["variants"][0]


def run(coro):
    return asyncio.run(coro)


def test_a_good_variant_is_kept_at_once(game):
    game["verdicts"] = [OK]
    r = run(scene_art.create_variant("T", "Biblioteca", "flag(estante_movida)", "passagem à mostra"))
    assert r["problems"] == [] and len(game["edits"]) == 1
    assert (game["root"] / variant(game)["background"]).exists()
    assert "review" not in variant(game)


def test_a_missing_change_is_fixed_by_editing_the_variant(game):
    game["verdicts"] = [bad(), OK]
    r = run(scene_art.create_variant("T", "Biblioteca", "flag(estante_movida)", "passagem à mostra"))
    first, second = game["edits"]
    assert first[0] == "backgrounds/Scene_base.png"
    assert second[0].startswith("backgrounds/Variant_") and "archway" in second[1]
    assert r["problems"] == [] and variant(game)["background"] == r["background"]
    assert not (game["root"] / second[0]).exists()          # the rejected picture is gone
    assert (game["root"] / "backgrounds/Scene_base.png").exists()


def test_a_variant_that_drifted_is_made_again_from_the_background(game):
    game["verdicts"] = [bad("o teto ganhou pinturas", "Plain stone ceiling", redo=True), OK]
    run(scene_art.create_variant("T", "Biblioteca", "flag(estante_movida)", "passagem à mostra"))
    assert [e[0] for e in game["edits"]] == ["backgrounds/Scene_base.png"] * 2
    assert "Plain stone ceiling" in game["edits"][1][1]


def test_what_is_still_wrong_goes_to_the_creator(game):
    game["verdicts"] = [bad()] * (scene_art.REVIEW_ROUNDS + 1)
    r = run(scene_art.create_variant("T", "Biblioteca", "flag(estante_movida)", "passagem à mostra"))
    assert len(game["edits"]) == 1 + scene_art.REVIEW_ROUNDS
    assert r["problems"] == ["a passagem não aparece"]
    assert variant(game)["review"]["problems"] == ["a passagem não aparece"]
    status = blueprint.art_status(game["project"])
    assert status["arte_revisar"] == ["Biblioteca [flag(estante_movida)]: a passagem não aparece"]
    assert status["pronta"]                                  # it has a picture; the warning is apart


def test_the_edit_instruction_says_where_the_object_is(game, monkeypatch):
    seen = {}

    async def ask(contents, hint, model=None):
        seen.setdefault(hint, contents)
        return {"instruction": "x"} if hint == "instrução de edição" else OK
    monkeypatch.setattr(scene_art, "_ask_json", ask)
    run(scene_art.create_variant("T", "Biblioteca", "flag(estante_movida)", "passagem à mostra"))
    assert "estante (left of centre, middle of the picture)" in seen["instrução de edição"]


def test_reviewing_an_existing_scene_keeps_its_picture_and_places_objects_again(game):
    game["project"]["scenes"]["s1"]["variants"][0]["background"] = "backgrounds/Scene_base.png"
    game["verdicts"] = [bad("a lareira já está acesa", "The fireplace is cold and dark"), OK, OK]
    r = run(scene_art.review_scene("T", "Biblioteca", fix=True))
    scene = game["project"]["scenes"]["s1"]
    bg = next(o for o in scene["objects"] if o["type"] == "background")
    assert r["fixed"] == ["cenário"] and bg["sprite"] != "backgrounds/Scene_base.png"
    assert (game["root"] / "backgrounds/Scene_base.png").exists()    # the project's own picture stays
    assert "review" not in bg
    assert scene["objects"][1]["position"] == {"x": round((576 + 864) / 2), "y": round((540 + 864) / 2)}


def test_report_only_does_not_touch_the_pictures(game):
    game["project"]["scenes"]["s1"]["variants"][0]["background"] = "backgrounds/Scene_base.png"
    game["verdicts"] = [bad("a lareira já está acesa"), OK]
    r = run(scene_art.review_scene("T", "Biblioteca"))
    assert r["background"] == ["a lareira já está acesa"] and game["edits"] == []
    assert blueprint.art_status(game["project"])["arte_revisar"] == ["Biblioteca: a lareira já está acesa"]


def test_a_new_picture_clears_the_old_review():
    scene = {"objects": [{"type": "background", "sprite": "a.png", "review": {"problems": ["x"]}}]}
    scene_art.set_background(scene, "b.png")
    assert "review" not in scene["objects"][0]


def test_where():
    assert scene_art.where({"position": {"x": 100, "y": 100}}) == "far left, upper part of the picture"
    assert scene_art.where({"position": {"x": 960, "y": 1000}}) == "centre, lower part of the picture"


def test_when_the_reviewer_is_unreachable_nothing_false_is_stored(game, monkeypatch):
    async def ask(contents, hint, model=None):
        if hint == "instrução de edição":
            return {"instruction": "x"}
        raise RuntimeError("503 UNAVAILABLE")
    monkeypatch.setattr(scene_art, "_ask_json", ask)
    r = run(scene_art.create_variant("T", "Biblioteca", "flag(estante_movida)", "passagem à mostra"))
    assert r["reviewed"] is False and r["problems"] == [] and "review" not in variant(game)
    out = run(scene_art.review_scene("T", "Biblioteca"))
    assert out["background"] is None and out["variants"]["flag(estante_movida)"] is None
    assert blueprint.art_status(game["project"])["arte_revisar"] == []


def test_a_daily_quota_is_recognised_and_not_waited_on():
    err = RuntimeError("429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota "
                       "* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, "
                       "limit: 20, model: gemini-3.6-flash, description: Generate content requests per day limit exceeded "
                       "on Free Tier.\nPlease retry in 18h59m51.532031871s.'}}")
    msg = scene_art._daily_quota_message(err, "models/gemini-3.5-flash")
    assert "gemini-3.5-flash" in msg and "20 pedidos por dia" in msg and "18h59m51s" in msg
    per_minute = RuntimeError("429 RESOURCE_EXHAUSTED. Quota exceeded ... requests per minute. Please retry in 31s.")
    assert scene_art._daily_quota_message(per_minute, "m") is None
