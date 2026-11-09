"""The AI director's tools, used the way the model uses them (names instead of ids)."""

from backend.ses.director_tools import run_tool


def build():
    p = {"name": "t", "scenes": {}, "start_scene": ""}
    assert run_tool(p, "create_scene", {"name": "Cela", "description": "Uma cela úmida."})["created"]
    assert run_tool(p, "create_scene", {"name": "Corredor", "description": "Tochas nas paredes."})["created"]
    assert run_tool(p, "create_scene", {"name": "Cela", "description": "x"})["created"] is False
    r = run_tool(p, "create_object", {"scene": "Cela", "name": "grampo", "description": "Um grampo de cabelo.",
                                      "portable": True})
    assert r["created"]
    r = run_tool(p, "create_object", {"scene": "Cela", "name": "grade", "description": "Barras de ferro.",
                                      "script": 'on use with grampo { link norte to corredor; say "Clique!" }'})
    assert r["created"] and r["warnings"] == []
    run_tool(p, "connect_scenes", {"from_scene": "Corredor", "direction": "leste", "to_scene": "Cela",
                                   "one_way": True})
    run_tool(p, "set_script", {"target": "Corredor", "script": 'on first_enter { end "Livre!" }'})
    return p


def test_build_and_win():
    p = build()
    assert p["scenes"][p["start_scene"]]["name"] == "Cela"
    r = run_tool(p, "playtest", {"commands": ["pegar grampo", "usar grampo na grade", "norte"]})
    assert r["ended"] == "Livre!", r["transcript"]
    assert "Clique!" in r["transcript"]


def test_bad_script_is_rejected_with_position():
    p = build()
    before = [o["ses"] for o in p["scenes"][p["start_scene"]]["objects"]]
    r = run_tool(p, "set_script", {"target": "grade", "script": "on use with grampo {\n  narrate('x')\n}"})
    assert "error" in r and r["script_errors"][0]["line"] == 2
    assert [o["ses"] for o in p["scenes"][p["start_scene"]]["objects"]] == before


def test_errors_are_returned_not_raised():
    p = build()
    assert "não existe" in run_tool(p, "get_scene", {"scene": "Torre"})["error"]
    assert "error" in run_tool(p, "nope", {})
    assert "argumentos" in run_tool(p, "create_scene", {})["error"]


def test_connect_two_way_and_delete_scene_cleans_exits():
    p = build()
    r = run_tool(p, "connect_scenes", {"from_scene": "Cela", "direction": "sul", "to_scene": "Corredor"})
    assert "back" in r
    ids = {s["name"]: i for i, s in p["scenes"].items()}
    assert p["scenes"][ids["Corredor"]]["exits"]["norte"] == ids["Cela"]
    run_tool(p, "delete_scene", {"scene": "Corredor"})
    assert p["scenes"][ids["Cela"]]["exits"] == {}


def test_overview_lists_objects_and_problems():
    p = build()
    p["scenes"][p["start_scene"]]["objects"][1]["ses"] = "on click { }"
    o = run_tool(p, "get_project", {})
    names = [x["name"] for s in o["scenes"] for x in s["objects"]]
    assert "grampo" in names and "Background" not in names
    assert o["script_problems"]


def test_move_and_update_object():
    p = build()
    run_tool(p, "update_object", {"object": "grampo", "move_to_scene": "Corredor", "aliases": ["clip"]})
    s = run_tool(p, "get_scene", {"scene": "Corredor"})
    assert s["objects"][0]["properties"]["aliases"] == ["clip"]


def test_update_object_script_and_unknown_args():
    p = build()
    r = run_tool(p, "update_object", {"object": "grampo", "script": 'on examine { say "Brilha." }'})
    assert "error" not in r
    r = run_tool(p, "playtest", {"commands": ["examinar grampo"]})
    assert "Brilha." in r["transcript"]
    r = run_tool(p, "update_object", {"object": "grampo", "cor": "azul"})
    assert "cor" in r["error"] and "description" in r["error"]
