import asyncio
import os
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path para importar os serviços
sys.path.append(str(Path(__file__).parent.parent))

from backend.services.gemini_orchestrator import GeminiAssetOrchestrator
from backend.config.user_settings import get_gemini_key
from backend.services.project_service import project_service

async def verify_consciousness():
    api_key = get_gemini_key()
    if not api_key:
        print("Erro: API Key não encontrada.")
        return

    orchestrator = GeminiAssetOrchestrator(api_key=api_key)
    project_name = "test_consciousness_project"
    
    # 1. Preparar projeto de teste
    try:
        project_service.create_project(project_name)
    except ValueError:
        pass # Já existe
    
    # Simular histórico e diretrizes
    project_service.log_action(project_name, "CREATE", "Criou a cena 'Laboratório'.")
    project_service.log_action(project_name, "UPDATE", "Adicionou um frasco de veneno duplicado.")
    
    project_data = project_service.load_project(project_name)
    project_data["metadata"]["narrative_directives"] = "O jogo deve ter um tom de mistério noir. Evite descrições alegres."
    project_service.save_project_data(project_name, project_data)

    # 2. Simular comando que exige consciência
    context = {
        "project_name": project_name,
        "current_scene_id": "default",
        "ai_memory": {
            "action_history": project_data["metadata"]["action_history"],
            "narrative_directives": project_data["metadata"]["narrative_directives"]
        }
    }

    print("\n--- TESTE 1: RECONHECIMENTO DE HISTÓRICO ---")
    prompt = "Notei que algo está errado no histórico recente. O que foi feito de errado e como você pode consertar?"
    result = await orchestrator.process_command(prompt, context=context)
    print(f"RESPOSTA DA IA: {result['text_response']}")

    print("\n--- TESTE 2: DIRETRIZES NARRATIVAS ---")
    prompt = "Descreva uma nova cena: 'Beco Escuro'."
    result = await orchestrator.process_command(prompt, context=context)
    print(f"RESPOSTA DA IA: {result['text_response']}")

if __name__ == "__main__":
    asyncio.run(verify_consciousness())
