import sys
import os
from pathlib import Path

# Adiciona a pasta raiz do projeto ao sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print(f"Adicionado ao path: {project_root}")

try:
    from backend.services.zluda_detector import ZLUDADetector
    from backend.config.user_settings import get_zluda_config
    
    print("\n--- Iniciando Teste de Detecção ZLUDA ---")
    
    # Pega a configuração do user_settings.py
    use_zluda, zluda_path = get_zluda_config()
    
    if not use_zluda:
        print("🟡 ZLUDA está desabilitado em user_settings.py. Teste abortado.")
    else:
        # Roda a detecção
        device = ZLUDADetector.get_optimal_device()
        print("----------------------------------------")
        print(f"✅ Teste concluído. Dispositivo selecionado: {device}")
        print("----------------------------------------\n")
        if device == 'cuda':
            print("🎉 Sucesso! Sua GPU AMD está sendo usada para aceleração.")
        else:
            print("⚠️ O sistema usará a CPU. Verifique os logs acima para entender o motivo.")

except ImportError as e:
    print(f"\n❌ ERRO: Não foi possível importar um módulo. Verifique se o arquivo existe e se o PYTHONPATH está correto.")
    print(f"Detalhes: {e}")
except Exception as e:
    print(f"\n❌ ERRO INESPERADO: Ocorreu um erro durante a execução.")
    print(f"Detalhes: {e}")
