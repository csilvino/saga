import sys
import os
import torch

# Adiciona a pasta raiz do projeto ao sys.path para garantir que o ambiente seja consistente
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("--- Verificando Dispositivo PyTorch ---")

try:
    # A instalação do ROCm/HIP no Windows faz o PyTorch detectar a GPU AMD como um dispositivo 'cuda'
    is_gpu_available = torch.cuda.is_available()
    
    if is_gpu_available:
        device_name = torch.cuda.get_device_name(0)
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        
        print(f"\n✅ SUCESSO! GPU detectada via HIP SDK.")
        print(f"   - Dispositivo: cuda")
        print(f"   - Nome: {device_name}")
        print(f"   - VRAM: {vram_gb:.2f} GB")
        print("\nAceleração por GPU está FUNCIONANDO!")
        
    else:
        print("\n⚠️ GPU não detectada pelo PyTorch.")
        print("   - Dispositivo: cpu")
        print("\nO sistema usará a CPU. Causas comuns:")
        print("   1. O HIP SDK não foi instalado corretamente.")
        print("   2. O computador não foi reiniciado após a instalação do HIP SDK.")
        print("   3. A versão do PyTorch não é compatível com a versão do seu driver AMD/HIP SDK.")

except Exception as e:
    print(f"\n❌ ERRO INESPERADO durante a verificação:")
    print(f"   - {e}")
    print("\nIsso pode indicar um problema na instalação do PyTorch ou do driver da GPU.")

print("\n--- Teste Concluído ---")
