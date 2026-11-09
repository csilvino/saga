from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
import logging

from backend.services.gemini_orchestrator import GeminiAssetOrchestrator
from backend.config.user_settings import get_gemini_key
from backend.services.project_service import project_service

router = APIRouter(prefix="/api/orchestrator", tags=["orchestrator"])
logger = logging.getLogger(__name__)

class CommandRequest(BaseModel):
    prompt: str
    context: Optional[Dict[str, Any]] = None
    recent_messages: Optional[List[str]] = None

@router.post("/command")
async def execute_orchestrator_command(request: CommandRequest):
    """
    Recebe um comando em linguagem natural, enriquece o contexto e o passa para o orquestrador Gemini.
    """
    api_key = get_gemini_key()
    if not api_key:
        raise HTTPException(status_code=400, detail="A chave da API do Gemini não está configurada.")

    try:
        # Carrega o projeto completo para ter acesso a todas as cenas
        if request.context and 'project_name' in request.context:
            project_data = project_service.load_project(request.context['project_name'])

            # Cria uma lista resumida de todas as cenas (ID e nome)
            all_scenes_summary = [
                {
                    "id": scene_id, 
                    "name": scene.get("name"),
                    "exits": scene.get("exits", {})
                }
                for scene_id, scene in project_data.get("scenes", {}).items()
            ]

            # Adiciona a lista de todas as cenas ao contexto
            request.context['all_scenes'] = all_scenes_summary
            
            # Adiciona metadados de consciência (Memória e Inventário)
            metadata = project_data.get("metadata", {})
            request.context['ai_memory'] = {
                "action_history": metadata.get("action_history", [])[:10], # Últimas 10 ações
                "deleted_objects": metadata.get("deleted_objects", []),
                "narrative_directives": metadata.get("narrative_directives", ""),
                "recent_game_log": request.recent_messages or [] # O que o jogador acabou de ler
            }

        orchestrator = GeminiAssetOrchestrator(api_key=api_key)
        
        # Enriquecimento final do prompt para garantir que a Gemini entenda o que é contexto e o que é comando
        if request.context:
            context_header = "=== ESTADO ATUAL DO JOGO (REFERÊNCIA DE CONTEXTO) ===\n"
            context_footer = "\n=== FIM DO CONTEXTO ===\n"
            context_str = json.dumps(request.context, indent=2)
            prompt_with_context = f"{context_header}{context_str}{context_footer}\n\nMENSAGEM DO USUÁRIO: {request.prompt}"
            result = await orchestrator.process_command(prompt_with_context)
        else:
            result = await orchestrator.process_command(request.prompt)
            
        return result
    except Exception as e:
        logger.error(f"Erro ao executar o comando do orquestrador: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno do orquestrador: {str(e)}")
