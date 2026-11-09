import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from backend.services.gemini_orchestrator import GeminiAssetOrchestrator
from backend.config.user_settings import get_gemini_key

async def run_automation():
    api_key = get_gemini_key()
    if not api_key:
        print("Erro: API Key não encontrada.")
        return

    orchestrator = GeminiAssetOrchestrator(api_key=api_key)
    
    ref_scene_id = "scene_a311d29f-19c9-4f87-9358-48fa71a8a7cc"
    
    prompt = f"""
Você é o Diretor Calixto. Vamos FINALIZAR a expansão de "Calixto Island".
IMPORTANTE: As cenas de Campo Pantanoso até Praia já existem. 
Oceano pode estar sem background.

COMPLETE estas 3 cenas finais:
1. Oceano (Garanta que tenha background e descrição)
2. Margem da Ilha (Chegada à ilha principal)
3. Clareira e Túmulo (A cena final)

Use a cena de referência "{ref_scene_id}" para o estilo das imagens.
Cada cena deve ter: create_scene (if exists), background, descrição e saídas.
"""
    
    context = {
        "project_name": "Calixto Island",
        "current_scene_id": "scene_dbfba2ac" # ID da cena Oceano (ou próxima)
    }

    print(f"\n🚀 Finalizando as 3 cenas finais da Ilha Calixto...")
    try:
        result = await orchestrator.process_command(prompt, context=context)
        print("\n✅ PROCESSO FINALIZADO")
        print(f"RESPOSTA: {result['text_response']}")
    except Exception as e:
        print(f"\n❌ ERRO: {e}")

if __name__ == "__main__":
    asyncio.run(run_automation())
