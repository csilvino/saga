from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
import re
import os
import json
from datetime import datetime
from pathlib import Path

from backend.services.project_service import project_service
from backend.services.text_parser import text_parser
from backend.services.ses_interpreter import ses_runtime

router = APIRouter(prefix="/api/game", tags=["game"])
logger = logging.getLogger(__name__)

class GameCommandRequest(BaseModel):
    project_name: str
    scene_id: str
    command: str
    inventory: List[Dict[str, Any]] = []
    game_state: Dict[str, Any] = {}

class SaveGameRequest(BaseModel):
    project_name: str
    save_name: str # e.g., 'auto', 'slot1'
    state: Dict[str, Any] # O objeto JSON completo do estado (scene_id, log, inventory)

def extract_narrate_text(ses_script: str) -> Optional[str]:
    """
    Tenta extrair o texto de um comando narrate('...') de um script SES simples.
    Isso é um parser rudimentar enquanto não temos o interpretador completo.
    """
    if not ses_script:
        return None
    # Procura por narrate('texto') ou narrate("texto")
    match = re.search(r"narrate\(['\"](.+?)['\"]\)", ses_script)
    if match:
        return match.group(1)
    return None

@router.post("/command")
async def process_game_command(request: GameCommandRequest):
    """
    Processa um comando de texto do jogador (estilo Adventure).
    """
    try:
        project = project_service.load_project(request.project_name)
        
        if request.scene_id not in project.get("scenes", {}):
            raise HTTPException(status_code=404, detail="Cena não encontrada.")
            
        scene = project["scenes"][request.scene_id]
        
        # Coleta objetos visíveis na cena (com metadados extras para o parser)
        visible_objects = []
        for obj in scene.get("objects", []):
            visible_objects.append({
                "id": obj["id"], 
                "name": obj["name"],
                "description": obj.get("description"), # Descrição simples
                "ses": obj.get("ses") # Script completo
            })
            
        # Adiciona objetos do inventário ao contexto
        # Nota: O inventário do request pode não ter o script completo, idealmente carregaríamos do projeto se tivéssemos IDs persistentes
        context_objects = visible_objects + request.inventory
        
        # Tratamento especial para AJUDA (antes do parser)
        if request.command.upper().strip() in ["AJUDA", "HELP", "COMANDOS"]:
            return {
                "success": True,
                "action": "HELP",
                "message": "COMANDOS DISPONÍVEIS:\n- OLHAR / EXAMINAR [objeto]\n- PEGAR [objeto]\n- USAR [objeto]\n- INVENTARIO\n- NORTE, SUL, LESTE, OESTE"
            }

        # O Parser faz a mágica
        result = text_parser.parse_command(request.command, context_objects)
        
        # Lógica de Resposta Padrão
        if result["action"] == "UNKNOWN":
            return {"success": False, "message": result["message"]}
            
        if result["action"] != "NONE" and not result.get("target_id") and result.get("target_name"):
             return {"success": False, "message": result["message"]}

        # Lógica de Execução (Runtime Simples)
        response_message = result.get("message") or "OK."
        
        # Lógica de Navegação (Mudar de Cena via Exits)
        direction_map = {
            "GO_N": "NORTE", "GO_S": "SUL", "GO_E": "LESTE", "GO_W": "OESTE",
            "GO_U": "CIMA", "BAIXO": "BAIXO", "GO_D": "BAIXO"
        }
        
        if result["action"] in direction_map:
            direction_key = direction_map[result["action"]]
            exits = scene.get("exits", {})
            if direction_key in exits:
                target_scene_id = exits[direction_key]
                target_scene = project["scenes"].get(target_scene_id)
                if target_scene:
                    return {
                        "success": True,
                        "action": "NAVIGATE",
                        "target_id": target_scene_id,
                        "message": f"Você vai para {target_scene.get('name')}."
                    }
            else:
                return {"success": False, "message": f"Não há saída para o {direction_key} aqui."}

        # 1. Execução de Script SES (se existir)
        ses_effects = []
        ses_context = {
            "target_id": result.get("target_id"),
            "game_state": request.game_state,
            "inventory": request.inventory,
            "project_name": request.project_name,
            "scene_id": request.scene_id
        }

        if result["action"] == "LOOK" and result.get("target_id"):
            target_obj = next((o for o in context_objects if o["id"] == result["target_id"]), None)
            if target_obj and target_obj.get("ses"):
                ses_effects = ses_runtime.execute_block(target_obj["ses"], "examine", ses_context)
        
        # Se for USE/PICKUP/INTERACT ou novos verbos de ação
        elif result["action"] in ["USE", "PICKUP", "OPEN", "PUSH", "PULL", "MOVE_UP", "MOVE_DOWN", "EXIT", "SIT", "ENTER"] and result.get("target_id"):
            target_obj = next((o for o in context_objects if o["id"] == result["target_id"]), None)
            if target_obj and target_obj.get("ses"):
                ses_effects = ses_runtime.execute_block(target_obj["ses"], "interact", ses_context)

        # Processa os efeitos do SES
        if ses_effects:
            for effect in ses_effects:
                if effect["type"] == "MESSAGE":
                    response_message = effect["content"]
                elif effect["type"] == "NAVIGATE":
                    return {
                        "success": True,
                        "action": "NAVIGATE",
                        "target_id": effect["target_id"],
                        "message": response_message
                    }
                elif effect["type"] == "PICKUP":
                    # Força a ação customizada vinda do script
                    return {
                        "success": True,
                        "action": "PICKUP",
                        "target_id": effect["target_id"],
                        "message": response_message
                    }
                elif effect["type"] == "DESTROY":
                    # No momento apenas retorna, o frontend terá que lidar com a remoção visual
                    return {
                        "success": True,
                        "action": "DESTROY",
                        "target_id": effect["target_id"],
                        "message": response_message
                    }

        # 2. Lógica de Resposta Padrão (Fallback)
        # Se for LOOK e não teve SES complexo
        if result["action"] == "LOOK" and result.get("target_id") and not ses_effects:
            target_obj = next((o for o in context_objects if o["id"] == result["target_id"]), None)
            if target_obj:
                desc_text = target_obj.get("description")
                if desc_text:
                    response_message = desc_text
                else:
                    response_message = f"Você vê {target_obj['name']}."

        return {
            "success": True,
            "action": result["action"],
            "target_id": result.get("target_id"),
            "target_name": result.get("target_name"),
            "message": response_message
        }
        
    except Exception as e:
        logger.error(f"Erro ao processar comando: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/save")
async def save_game(request: SaveGameRequest):
    """
    Salva o estado atual do jogo em um arquivo JSON.
    """
    try:
        # Define o caminho do diretório (um nível acima de backend para d:/PythonProject/saga/savegame)
        save_dir = Path(__file__).parent.parent.parent.parent / "savegame"
        if not save_dir.exists():
            save_dir.mkdir(parents=True, exist_ok=True)
            
        file_path = save_dir / f"{request.project_name}_{request.save_name}.json"
        
        # Adiciona metadados ao estado
        request.state["last_saved"] = datetime.now().isoformat()
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(request.state, f, indent=4, ensure_ascii=False)
            
        return {"success": True, "message": f"Jogo salvo como '{request.save_name}'."}
        
    except Exception as e:
        logger.error(f"Erro ao salvar jogo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao salvar: {str(e)}")

@router.get("/load/{project_name}/{save_name}")
async def load_game(project_name: str, save_name: str):
    """
    Carrega um estado salvo.
    """
    try:
        save_dir = Path(__file__).parent.parent.parent.parent / "savegame"
        file_path = save_dir / f"{project_name}_{save_name}.json"
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Arquivo de save não encontrado.")
            
        with open(file_path, "r", encoding="utf-8") as f:
            state = json.load(f)
            
        return {"success": True, "state": state}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao carregar jogo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao carregar: {str(e)}")
