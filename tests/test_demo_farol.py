"""The demo project O Farol (a copy in tests/fixtures; the game itself may be deleted) must stay winnable."""

import json
from pathlib import Path

from backend.ses.engine import playtest
from backend.ses.language import validate

ROOT = Path(__file__).resolve().parents[1]


def test_demo_is_winnable_and_scripts_are_valid():
    import importlib.util
    spec = importlib.util.spec_from_file_location("demo", ROOT / "tools" / "build_demo_farol.py")
    demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo)
    project = json.loads((ROOT / "tests" / "fixtures" / "o_farol_project.json").read_text(encoding="utf-8"))
    for scene in project["scenes"].values():
        assert validate(scene.get("ses", ""), project, "scene")["ok"]
        for obj in scene["objects"]:
            assert validate(obj.get("ses", ""), project, "object")["ok"], obj["name"]
    r = playtest(project, demo.SOLUTION)
    assert r["final_state"]["ended"] and "FIM" in r["final_state"]["ended"]
    assert not r["script_errors"]
