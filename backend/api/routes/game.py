"""
Playing a project as a text adventure. The server keeps no session: the client holds the game state
returned by /start and /command and sends it back with the next command.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.project_service import project_service
from backend.ses.engine import GameEngine, playtest
from backend.ses.language import REFERENCE, validate

router = APIRouter(prefix="/api/game", tags=["game"])
ses_router = APIRouter(prefix="/api/ses", tags=["ses"])
logger = logging.getLogger(__name__)

SAVE_DIR = Path(__file__).resolve().parents[3] / "savegame"


class StartRequest(BaseModel):
    project_name: str


class CommandRequest(BaseModel):
    project_name: str
    command: str
    state: Optional[Dict[str, Any]] = None


class PlaytestRequest(BaseModel):
    project_name: str
    commands: List[str]


class SaveGameRequest(BaseModel):
    project_name: str
    save_name: str
    state: Dict[str, Any]


class ValidateRequest(BaseModel):
    script: str
    project_name: Optional[str] = None
    owner_kind: str = "object"          # object | scene


def load(project_name: str) -> dict:
    try:
        return project_service.load_project(project_name)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Projeto '{project_name}' não encontrado: {e}")


@router.post("/start")
async def start_game(request: StartRequest):
    return GameEngine(load(request.project_name)).start()


@router.post("/command")
async def game_command(request: CommandRequest):
    engine = GameEngine(load(request.project_name))
    if not request.state:
        return engine.start()
    return engine.command(request.state, request.command)


@router.post("/playtest")
async def game_playtest(request: PlaytestRequest):
    return playtest(load(request.project_name), request.commands)


def save_path(project_name: str, save_name: str) -> Path:
    def safe(s):
        return re.sub(r"[^A-Za-z0-9_-]+", "_", s).strip("_") or "save"
    return SAVE_DIR / f"{safe(project_name)}__{safe(save_name)}.json"


@router.post("/save")
async def save_game(request: SaveGameRequest):
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    data = {"saved_at": datetime.now().isoformat(timespec="seconds"), "state": request.state}
    save_path(request.project_name, request.save_name).write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"success": True, "message": f"Jogo salvo como '{request.save_name}'."}


@router.get("/load/{project_name}/{save_name}")
async def load_game(project_name: str, save_name: str):
    path = save_path(project_name, save_name)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Save não encontrado.")
    data = json.loads(path.read_text(encoding="utf-8"))
    out = GameEngine(load(project_name)).command(data["state"], "olhar")
    return {"success": True, **out}


@ses_router.post("/validate")
async def validate_script(request: ValidateRequest):
    project = load(request.project_name) if request.project_name else None
    return validate(request.script, project, request.owner_kind)


@ses_router.get("/reference")
async def ses_reference():
    return {"reference": REFERENCE}
