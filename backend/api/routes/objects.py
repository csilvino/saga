from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

import uuid

from backend.services.project_service import project_service
from backend.services import object_generation_service
from backend.config.user_settings import PLACEHOLDER_MODE

router = APIRouter(prefix="/api/objects", tags=["objects"])

# Modelo para criação de um novo objeto, simplificado para a IA
class ObjectCreateRequest(BaseModel):
    project_name: str
    scene_id: str
    object_name: str
    description: Optional[str] = "Um objeto misterioso."
    object_type: Optional[str] = "item"

# Modelo para atualização de um objeto
class ObjectUpdateRequest(BaseModel):
    project_name: str
    scene_id: str
    object_id: str
    updates: Dict[str, Any]

class ObjectSESUpdateRequest(BaseModel):
    project_name: str
    scene_id: str
    object_id: str
    ses: str

@router.post("/create")
async def create_object(request: ObjectCreateRequest):
    """
    Cria um novo objeto (GameObject) completo dentro de uma cena,
    gerando placeholder, script SES e posição inteligente.
    """
    try:
        project = project_service.load_project(request.project_name)
        
        if request.scene_id not in project.get("scenes", {}):
            raise HTTPException(status_code=404, detail=f"Cena com ID '{request.scene_id}' não encontrada.")
        
        scene = project["scenes"][request.scene_id]

        # 1. Gerar placeholder
        sprite_placeholder = object_generation_service.get_placeholder(request.object_type, PLACEHOLDER_MODE)

        # 2. Gerar script SES
        ses_script = object_generation_service.generate_ses_template(request.object_name, request.description, request.object_type)

        # 3. Calcular posição inteligente
        position = object_generation_service.calculate_smart_position(scene, request.object_type)

        # 4. Montar o novo objeto
        object_id = f"game_object_{uuid.uuid4().hex[:8]}"
        new_object = {
            "id": object_id,
            "name": request.object_name,
            "type": request.object_type,
            "sprite": sprite_placeholder,
            "position": position,
            "size": {"width": 100, "height": 100}, # Tamanho padrão inicial
            "properties": {},
            "actions": [],
            "ses": ses_script
        }
        
        if "objects" not in scene:
            scene["objects"] = []
            
        scene["objects"].append(new_object)
        
        project_service.save_project_data(request.project_name, project)
        
        return {
            "success": True,
            "object_id": object_id,
            "message": f"Objeto '{request.object_name}' criado na cena com placeholder e script inicial."
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Projeto '{request.project_name}' não encontrado.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar objeto: {str(e)}")

@router.post("/update")
async def update_object(request: ObjectUpdateRequest):
    """
    Atualiza as propriedades de um objeto existente.
    """
    try:
        project = project_service.load_project(request.project_name)
        
        if request.scene_id not in project.get("scenes", {}):
            raise HTTPException(status_code=404, detail=f"Cena com ID '{request.scene_id}' não encontrada.")
        
        scene = project["scenes"][request.scene_id]
        
        object_index = -1
        for i, obj in enumerate(scene.get("objects", [])):
            if obj.get("id") == request.object_id:
                object_index = i
                break
        
        if object_index == -1:
            raise HTTPException(status_code=404, detail=f"Objeto com ID '{request.object_id}' não encontrado na cena.")
            
        # Atualiza o dicionário do objeto com os novos dados
        scene["objects"][object_index].update(request.updates)
        
        project_service.save_project_data(request.project_name, project)
        
        return {"success": True, "message": "Objeto atualizado com sucesso.", "updated_object": scene["objects"][object_index]}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Projeto '{request.project_name}' não encontrado.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar objeto: {str(e)}")

@router.post("/update-ses")
async def update_object_ses(request: ObjectSESUpdateRequest):
    """
    Atualiza o script SES de um objeto.
    """
    try:
        project = project_service.load_project(request.project_name)
        
        if request.scene_id not in project.get("scenes", {}):
            raise HTTPException(status_code=404, detail=f"Cena com ID '{request.scene_id}' não encontrada.")
        
        scene = project["scenes"][request.scene_id]
        
        object_index = -1
        for i, obj in enumerate(scene.get("objects", [])):
            if obj.get("id") == request.object_id:
                object_index = i
                break
        
        if object_index == -1:
            raise HTTPException(status_code=404, detail=f"Objeto com ID '{request.object_id}' não encontrado na cena.")
            
        scene["objects"][object_index]["ses"] = request.ses
        
        project_service.save_project_data(request.project_name, project)
        
        return {"success": True, "message": "Script SES do objeto atualizado com sucesso."}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Projeto '{request.project_name}' não encontrado.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar SES do objeto: {str(e)}")

@router.delete("/")
async def delete_object(project_name: str, scene_id: str, object_id: str):
    """
    Deleta um objeto de uma cena.
    """
    try:
        project = project_service.load_project(project_name)
        
        if scene_id not in project.get("scenes", {}):
            raise HTTPException(status_code=404, detail="Cena não encontrada.")
            
        scene = project["scenes"][scene_id]
        
        original_object_count = len(scene.get("objects", []))
        scene["objects"] = [obj for obj in scene.get("objects", []) if obj.get("id") != object_id]
        
        if len(scene["objects"]) == original_object_count:
            raise HTTPException(status_code=404, detail="Objeto não encontrado na cena.")
            
        project_service.save_project_data(project_name, project)
        
        return {"success": True, "message": "Objeto deletado com sucesso."}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Projeto '{project_name}' não encontrado.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao deletar objeto: {str(e)}")

# ================= NEW TOOLS FOR AI ORCHESTRATION =================

class ObjectMoveRequest(BaseModel):
    project_name: str
    object_id: str
    source_scene_id: str
    target_scene_id: str
    new_position: Optional[Dict[str, int]] = None

class ObjectSwapRequest(BaseModel):
    project_name: str
    scene_id: str
    object_id_a: str
    object_id_b: str

@router.post("/move")
async def move_object(request: ObjectMoveRequest):
    """
    Move um objeto de uma cena para outra.
    """
    try:
        project = project_service.load_project(request.project_name)
        
        # Validate Source
        if request.source_scene_id not in project.get("scenes", {}):
            raise HTTPException(status_code=404, detail=f"Cena de origem '{request.source_scene_id}' não encontrada.")
        source_scene = project["scenes"][request.source_scene_id]
        
        # Validate Target
        if request.target_scene_id not in project.get("scenes", {}):
            raise HTTPException(status_code=404, detail=f"Cena de destino '{request.target_scene_id}' não encontrada.")
        target_scene = project["scenes"][request.target_scene_id]
        
        # Find Object
        obj_to_move = None
        for obj in source_scene.get("objects", []):
            if obj["id"] == request.object_id:
                obj_to_move = obj
                break
        
        if not obj_to_move:
            raise HTTPException(status_code=404, detail=f"Objeto '{request.object_id}' não encontrado na cena de origem.")
        
        # Remove from Source
        source_scene["objects"] = [o for o in source_scene["objects"] if o["id"] != request.object_id]
        
        # Update Position if requested
        if request.new_position:
            obj_to_move["position"] = request.new_position
            
        # Add to Target
        if "objects" not in target_scene:
            target_scene["objects"] = []
        target_scene["objects"].append(obj_to_move)
        
        project_service.save_project_data(request.project_name, project)
        
        return {
            "success": True, 
            "message": f"Objeto movido de {request.source_scene_id} para {request.target_scene_id}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao mover objeto: {str(e)}")

@router.post("/swap")
async def swap_objects(request: ObjectSwapRequest):
    """
    Troca a posição de dois objetos dentro da mesma cena.
    """
    try:
        project = project_service.load_project(request.project_name)
        
        if request.scene_id not in project.get("scenes", {}):
            raise HTTPException(status_code=404, detail="Cena não encontrada.")
        scene = project["scenes"][request.scene_id]
        
        obj_a = None
        obj_b = None
        
        for obj in scene.get("objects", []):
            if obj["id"] == request.object_id_a:
                obj_a = obj
            elif obj["id"] == request.object_id_b:
                obj_b = obj
                
        if not obj_a or not obj_b:
            raise HTTPException(status_code=404, detail="Um ou ambos os objetos não foram encontrados.")
            
        # Swap Positions
        pos_a = obj_a.get("position", {"x": 0, "y": 0}).copy()
        pos_b = obj_b.get("position", {"x": 0, "y": 0}).copy()
        
        obj_a["position"] = pos_b
        obj_b["position"] = pos_a
        
        project_service.save_project_data(request.project_name, project)
        
        return {
            "success": True,
            "message": "Posições trocadas com sucesso."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao trocar objetos: {str(e)}")
