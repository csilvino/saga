"""
The game's blueprint (ficha.yaml): read it, check it, build the project from it and make the art
and the sounds still missing, in the background (GET /art and GET /sound show how far they got).
"""

import asyncio
import logging
import time
from typing import Dict, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from backend.services.project_service import project_service
from backend.ses import blueprint

router = APIRouter(prefix="/api/blueprint", tags=["blueprint"])
logger = logging.getLogger(__name__)

ART_JOBS: Dict[str, dict] = {}          # project name -> {"running", "log", "result", "started"}
SOUND_JOBS: Dict[str, dict] = {}        # the same, for the sounds


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
    if SOUND_JOBS.get(req.project_name, {}).get("running"):
        raise HTTPException(status_code=409, detail="os sons deste jogo estão sendo gerados; espere terminar")
    return await asyncio.to_thread(blueprint.build, req.project_name, req.text, True)


def _start_job(jobs: Dict[str, dict], project_name: str, work, what: str) -> dict:
    """Runs work(project_name, say) in the background; one job per project at a time."""
    _root(project_name)
    job = jobs.get(project_name)
    if job and job["running"]:
        return job
    job = {"running": True, "log": [], "result": None, "started": time.time()}
    jobs[project_name] = job

    def say(msg):
        job["log"].append(f"{time.strftime('%H:%M:%S')} {msg}")
        del job["log"][:-200]

    async def run():
        try:
            job["result"] = await work(project_name, say)
        except Exception as e:                       # noqa: BLE001 - shown to the user
            logger.exception("%s de %s", what, project_name)
            job["result"] = {"erro": str(e)}
        finally:
            job["running"] = False
            say("fim")

    asyncio.create_task(run())
    return job


@router.post("/sound/{project_name}")
async def start_sound(project_name: str):
    from backend.services import sound_gen
    return _start_job(SOUND_JOBS, project_name, sound_gen.make_sounds, "som")


@router.get("/sound/{project_name}")
async def sound_status(project_name: str):
    job = SOUND_JOBS.get(project_name)
    try:
        status = blueprint.sound_status(project_service.load_project(project_name))
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"running": bool(job and job["running"]), "log": (job or {}).get("log", [])[-40:],
            "result": (job or {}).get("result"), **status}


@router.post("/art/{project_name}")
async def start_art(project_name: str):
    return _start_job(ART_JOBS, project_name, blueprint.make_art, "arte")


@router.get("/art/{project_name}")
async def art_status(project_name: str):
    from backend.services import scene_art
    job = ART_JOBS.get(project_name)
    try:
        project = project_service.load_project(project_name)
        status = blueprint.art_status(project)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"running": bool(job and job["running"]), "log": (job or {}).get("log", [])[-40:],
            "result": (job or {}).get("result"), "cenas": scene_art.scene_art_list(project), **status}


# --- per scene: where its pictures come from; the web AI route (prompts out, pictures in) -------

class ArtSource(BaseModel):
    source: str                         # local | gemini | web


def _art_call(project_name: str):
    if ART_JOBS.get(project_name, {}).get("running"):
        raise HTTPException(status_code=409, detail="a arte deste jogo está sendo gerada; espere terminar")


@router.put("/art-source/{project_name}/{scene_id}")
async def put_art_source(project_name: str, scene_id: str, req: ArtSource):
    from backend.services import scene_art
    _art_call(project_name)
    try:
        return scene_art.set_art_source(project_name, scene_id, req.source)
    except (scene_art.ArtError, ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/web-art/{project_name}/{scene_id}")
async def get_web_prompts(project_name: str, scene_id: str):
    from backend.services import scene_art
    try:
        return await scene_art.web_prompts(project_name, scene_id)
    except (scene_art.ArtError, ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/web-art/{project_name}/{scene_id}/{kind}")
async def post_web_image(project_name: str, scene_id: str, kind: str, file: UploadFile = File(...)):
    """kind: background | sprites | variant:N"""
    from backend.services import scene_art
    _art_call(project_name)
    data = await file.read()
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="imagem grande demais (máximo 25 MB)")
    try:
        return await scene_art.web_upload(project_name, scene_id, kind, data)
    except (scene_art.ArtError, ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))
