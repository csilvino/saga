"""
The game's blueprint (ficha.yaml): read it, check it, build the project from it and make the art
still missing, in the background (GET /art shows how far it got).
"""

import asyncio
import logging
import time
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.project_service import project_service
from backend.ses import blueprint

router = APIRouter(prefix="/api/blueprint", tags=["blueprint"])
logger = logging.getLogger(__name__)

ART_JOBS: Dict[str, dict] = {}          # project name -> {"running", "log", "result", "started"}


class BlueprintText(BaseModel):
    project_name: str
    text: Optional[str] = None          # None: the ficha.yaml already saved in the project


def _root(name: str):
    try:
        return project_service.load_project_path(name)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Projeto '{name}' não encontrado: {e}")


@router.get("/{project_name}")
async def get_blueprint(project_name: str):
    """The saved ficha.yaml; a project without one gets a draft exported from its project.json."""
    root = _root(project_name)
    path = root / blueprint.FILE_NAME
    if path.exists():
        return {"text": path.read_text(encoding="utf-8"), "exported": False}
    try:
        project = project_service.load_project(project_name)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"text": blueprint.dump(blueprint.export(project)), "exported": True}


@router.post("/check")
async def check_blueprint(req: BlueprintText):
    return await asyncio.to_thread(blueprint.build, req.project_name, req.text, False)


@router.post("/build")
async def build_blueprint(req: BlueprintText):
    if ART_JOBS.get(req.project_name, {}).get("running"):
        raise HTTPException(status_code=409, detail="a arte deste jogo está sendo gerada; espere terminar")
    return await asyncio.to_thread(blueprint.build, req.project_name, req.text, True)


@router.post("/art/{project_name}")
async def start_art(project_name: str):
    _root(project_name)
    job = ART_JOBS.get(project_name)
    if job and job["running"]:
        return job
    job = {"running": True, "log": [], "result": None, "started": time.time()}
    ART_JOBS[project_name] = job

    def say(msg):
        job["log"].append(f"{time.strftime('%H:%M:%S')} {msg}")
        del job["log"][:-200]

    async def run():
        try:
            job["result"] = await blueprint.make_art(project_name, say)
        except Exception as e:                       # noqa: BLE001 - shown to the user
            logger.exception("arte de %s", project_name)
            job["result"] = {"erro": str(e)}
        finally:
            job["running"] = False
            say("fim")

    asyncio.create_task(run())
    return job


@router.get("/art/{project_name}")
async def art_status(project_name: str):
    job = ART_JOBS.get(project_name)
    try:
        status = blueprint.art_status(project_service.load_project(project_name))
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"running": bool(job and job["running"]), "log": (job or {}).get("log", [])[-40:],
            "result": (job or {}).get("result"), **status}
