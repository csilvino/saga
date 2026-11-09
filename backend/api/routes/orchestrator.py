import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config.user_settings import get_gemini_key
from backend.services.gemini_orchestrator import get_session, reset_session

router = APIRouter(prefix="/api/orchestrator", tags=["orchestrator"])
logger = logging.getLogger(__name__)


class CommandRequest(BaseModel):
    prompt: str
    context: Optional[Dict[str, Any]] = None


class ResetRequest(BaseModel):
    project_name: Optional[str] = None


@router.post("/command")
async def execute_orchestrator_command(request: CommandRequest):
    """A message to the AI director; it acts on the project with tools and answers in text."""
    api_key = get_gemini_key()
    if not api_key:
        raise HTTPException(status_code=400, detail="Configure sua chave da Gemini em Configurações > API Key.")
    context = request.context or {}
    project_name = context.get("project_name")
    if not project_name:
        raise HTTPException(status_code=400, detail="Abra um projeto antes de falar com o Diretor.")
    scene = context.get("active_scene")
    ctx = {"scene_id": scene.get("id") if isinstance(scene, dict) else scene,
           "selected_object_id": context.get("selected_object_id")}
    try:
        return await get_session(api_key, project_name).send(request.prompt, ctx)
    except Exception as e:
        logger.error("orchestrator: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro da IA: {e}")


@router.post("/reset")
async def reset_orchestrator(request: ResetRequest):
    """Forgets the director's conversation (for one project or all)."""
    reset_session(request.project_name)
    return {"success": True}
