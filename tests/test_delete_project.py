"""The start screen's trash button: the project's folder moves to .lixeira/ (recoverable)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.routes import projects


def client(tmp_path, monkeypatch):
    (tmp_path / "projects" / "Jogo A").mkdir(parents=True)
    (tmp_path / "projects" / "Jogo A" / "project.json").write_text("{}", encoding="utf-8")
    (tmp_path / "segredo").mkdir()
    monkeypatch.setattr(projects, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(projects, "TRASH_DIR", tmp_path / ".lixeira")
    app = FastAPI()
    app.include_router(projects.router)
    return TestClient(app)


def test_a_deleted_project_goes_to_the_trash_with_its_files(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    r = c.delete("/api/projects/Jogo%20A")
    assert r.status_code == 200
    assert not (tmp_path / "projects" / "Jogo A").exists()
    [moved] = list((tmp_path / ".lixeira").iterdir())
    assert moved.name.startswith("Jogo A__") and (moved / "project.json").exists()
    assert c.get("/api/projects/list").json() == []


def test_only_a_project_folder_can_be_deleted(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    assert c.delete("/api/projects/Nao%20existe").status_code == 404
    assert c.delete("/api/projects/..%2Fsegredo").status_code in (404, 405)
    assert (tmp_path / "segredo").exists() and (tmp_path / "projects" / "Jogo A").exists()
