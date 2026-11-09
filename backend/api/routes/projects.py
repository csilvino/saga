from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Any, List, Dict
from pathlib import Path
import logging

from backend.services.project_service import project_service, ProjectLoadError, ROOT_DIR

# Configuração do logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["projects"])

class ProjectCreate(BaseModel):
    name: str

class ProjectData(BaseModel):
    project: Dict[str, Any]

@router.get("/list")
async def list_projects() -> List[str]:
    projects_dir = ROOT_DIR / "projects"
    logger.info(f"Buscando projetos em: {projects_dir.resolve()}")
    
    if not projects_dir.is_dir():
        logger.warning(f"O diretório de projetos não foi encontrado ou não é um diretório.")
        return []
        
    try:
        project_list = [d.name for d in projects_dir.iterdir() if d.is_dir()]
        logger.info(f"Projetos encontrados: {project_list}")
        return project_list
    except Exception as e:
        logger.error(f"Erro ao listar os projetos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno ao listar projetos.")


# Rota de teste para depuração
@router.post("/test")
async def test_route():
    return {"status": "success", "message": "A rota de teste POST funcionou!"}

@router.post("/load")
async def load_project(project_create: ProjectCreate):
    try:
        project_data = project_service.load_project(project_create.name)
        return {"project": project_data}
    except ProjectLoadError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        # Não usamos logger.error aqui para evitar propagação de WinError 233 se o stdout estiver quebrado
        return {
            "detail": f"Erro interno no servidor: {str(e)}",
            "traceback": error_details
        }

@router.post("/save")
async def save_project(project_data: ProjectData):
    try:
        project = project_data.project
        project_name = project.get("name")
        if not project_name:
            raise HTTPException(status_code=400, detail="Nome do projeto não encontrado nos dados.")
        
        project_service.save_project_data(project_name, project)
        return {"status": "success", "message": "Projeto salvo com sucesso."}
    except Exception as e:
        logger.error(f"Erro ao salvar projeto: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao salvar o projeto: {e}")

@router.post("/create")
async def create_project(project_create: ProjectCreate):
    try:
        project_service.create_project(project_create.name)
        return {"status": "success", "message": f"Projeto '{project_create.name}' criado com sucesso."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar o projeto: {e}")
