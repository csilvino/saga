from pathlib import Path

from tools.validate_project import validate_file


def test_demo_valid(tmp_path):
    proj = Path("projects/demo/project.json")
    schema = Path("shared/project_schema.json")
    assert proj.exists()
    assert schema.exists()
    assert validate_file(proj, schema) is True
