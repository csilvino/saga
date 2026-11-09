from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
import uuid
import logging

from backend.services.project_service import project_service

router = APIRouter(prefix="/api/scenes", tags=["scenes"])
logger = logging.getLogger(__name__)

# Modelo para criação de cena, com a verificação de existência
class SceneCreateRequest(BaseModel):
    project_name: str
    scene_name: str
    description: Optional[str] = ""
    check_if_exists: bool = Field(default=True, description="Se True, a API primeiro verifica se uma cena com o mesmo nome já existe.")

# Modelo para atualização de cena
class SceneUpdateRequest(BaseModel):
    project_name: str
    scene_id: str
    updates: Dict[str, Any]

# Modelo para definir o background
class SetBackgroundRequest(BaseModel):
    project_name: str
    scene_id: str
    background_path: str

# Modelo para atualização de SES
class SESUpdateRequest(BaseModel):
    project_name: str
    scene_id: str
    ses: str

@router.post("/create")
async def create_scene(request: SceneCreateRequest):
    """
    Cria uma nova cena em um projeto, com verificação opcional de existência.
    """
    try:
        project = project_service.load_project(request.project_name)
        
        # Lógica da "guarda técnica"
        if request.check_if_exists:
            for scene_id, scene_data in project.get("scenes", {}).items():
                if scene_data.get("name", "").lower() == request.scene_name.lower():
                    logger.warning(f"Cena '{request.scene_name}' já existe com ID: {scene_id}")
                    return {
                        "success": True,
                        "message": f"Cena '{request.scene_name}' já existe.",
                        "scene_id": scene_id,
                        "created": False
                    }

        scene_id = f"scene_{uuid.uuid4().hex[:8]}"
        new_scene = {
            "id": scene_id,
            "name": request.scene_name,
            # "background": "", # Removido
            "objects": [
                {
                    "id": f"background_{uuid.uuid4().hex[:8]}",
                    "name": "Background",
                    "type": "background",
                    "sprite": "",
                    "position": {"x": 960, "y": 540},
                    "origin": {"x": 960, "y": 540},
                    "size": {"width": 1920, "height": 1080},
                    "scale": {"x": 1, "y": 1},
                    "rotation": 0,
                    "zIndex": 0,
                    "actions": [],
                    "ses": "// Script para o Background\n"
                }
            ],
            "hotspots": [],
            "actions": [],
            "description": request.description or "",
            "exits": {},
            "ses": f"// Script da cena {request.scene_name} (SES v2). Ex.: on first_enter {{ say \"...\" }}\n"
        }
        
        if "scenes" not in project:
            project["scenes"] = {}
        
        project["scenes"][scene_id] = new_scene
        
        if "start_scene" not in project or not project["start_scene"]:
            project["start_scene"] = scene_id
            
        project_service.save_project_data(request.project_name, project)
        
        return {
            "success": True, 
            "scene_id": scene_id, 
            "scene_name": request.scene_name, 
            "message": f"Cena '{request.scene_name}' criada com sucesso.",
            "created": True
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Projeto '{request.project_name}' não encontrado.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar cena: {str(e)}")

@router.post("/update")
async def update_scene(request: SceneUpdateRequest):
    """
    Atualiza as propriedades de uma cena.
    """
    try:
        project = project_service.load_project(request.project_name)
        
        if request.scene_id not in project.get("scenes", {}):
            raise HTTPException(status_code=404, detail=f"Cena com ID '{request.scene_id}' não encontrada.")
            
        project["scenes"][request.scene_id].update(request.updates)
        
        project_service.save_project_data(request.project_name, project)
        
        return {"success": True, "message": "Cena atualizada com sucesso.", "updated_scene": project["scenes"][request.scene_id]}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Projeto '{request.project_name}' não encontrado.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar cena: {str(e)}")

@router.post("/set-background")
async def set_scene_background(request: SetBackgroundRequest):
    """
    Define a imagem de fundo para uma cena específica.
    """
    try:
        project = project_service.load_project(request.project_name)
        
        if request.scene_id not in project.get("scenes", {}):
            raise HTTPException(status_code=404, detail=f"Cena com ID '{request.scene_id}' não encontrada.")
        
        project_path = project_service.load_project_path(request.project_name)
        if not (project_path / request.background_path).exists():
             raise HTTPException(status_code=404, detail=f"Arquivo de background '{request.background_path}' não encontrado no projeto.")

        scene = project["scenes"][request.scene_id]
        
        # Encontra ou cria o objeto de background
        bg_obj = None
        for obj in scene.get("objects", []):
            if obj.get("type") == "background" or obj.get("name") == "Background":
                bg_obj = obj
                break
        
        if bg_obj:
            bg_obj["sprite"] = request.background_path
        else:
            # Caso não exista (cenas antigas), cria um
            new_bg_obj = {
                "id": f"background_{uuid.uuid4().hex[:8]}",
                "name": "Background",
                "type": "background",
                "sprite": request.background_path,
                "position": {"x": 960, "y": 540},
                "origin": {"x": 960, "y": 540},
                "size": {"width": 1920, "height": 1080},
                "scale": {"x": 1, "y": 1},
                "rotation": 0,
                "zIndex": 0,
                "actions": [],
                "ses": "// Script para o Background\n"
            }
            if "objects" not in scene:
                scene["objects"] = []
            scene["objects"].append(new_bg_obj)
        
        # Limpa o campo antigo se existir
        if "background" in scene:
            del scene["background"]
        
        project_service.save_project_data(request.project_name, project)
        
        return {"success": True, "message": f"Background da cena '{scene['name']}' definido."}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Projeto '{request.project_name}' não encontrado.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao definir background: {str(e)}")

@router.post("/update-ses")
async def update_scene_ses(request: SESUpdateRequest):
    """
    Atualiza o script SES de uma cena.
    """
    try:
        project = project_service.load_project(request.project_name)
        
        if request.scene_id not in project.get("scenes", {}):
            raise HTTPException(status_code=404, detail=f"Cena com ID '{request.scene_id}' não encontrada.")
            
        project["scenes"][request.scene_id]["ses"] = request.ses
        
        project_service.save_project_data(request.project_name, project)
        
        return {"success": True, "message": "Script SES da cena atualizado com sucesso."}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Projeto '{request.project_name}' não encontrado.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar SES da cena: {str(e)}")

@router.delete("/")
async def delete_scene(
    project_name: str = Query(..., description="Nome do projeto"),
    scene_id: str = Query(..., description="ID da cena a ser deletada")
):
    """
    Deleta uma cena de um projeto.
    """
    logger.info(f"Recebida solicitação para deletar cena: {scene_id} do projeto: {project_name}")
    try:
        project = project_service.load_project(project_name)
        
        if scene_id not in project.get("scenes", {}):
            logger.warning(f"Tentativa de deletar cena inexistente: {scene_id}")
            raise HTTPException(status_code=404, detail="Cena não encontrada.")
        
        if project.get("start_scene") == scene_id:
            logger.warning(f"Tentativa de deletar cena inicial: {scene_id}")
            raise HTTPException(status_code=400, detail="Não é possível deletar a cena inicial.")

        del project["scenes"][scene_id]
        logger.info(f"Cena {scene_id} removida da estrutura em memória.")

        project_service.save_project_data(project_name, project)
        logger.info(f"Projeto {project_name} salvo com sucesso após deleção.")

        return {"success": True, "message": "Cena deletada com sucesso."}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Projeto '{project_name}' não encontrado.")
    except Exception as e:
        logger.error(f"Erro ao deletar cena: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao deletar cena: {str(e)}")
