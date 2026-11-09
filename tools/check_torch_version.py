import torch
import sys
import os

print("--- Diagnóstico PyTorch ---")
print(f"Python Executável: {sys.executable}")
print(f"PyTorch Versão: {torch.__version__}")
print(f"CUDA Disponível: {torch.cuda.is_available()}")
print(f"CUDA Version (Torch): {torch.version.cuda}")

if torch.cuda.is_available():
    print(f"GPU Atual: {torch.cuda.current_device()}")
    print(f"Nome da GPU: {torch.cuda.get_device_name(0)}")
else:
    print("\n⚠️ GPU não detectada.")
    print("Se você tem uma placa NVIDIA, provavelmente precisa instalar a versão do PyTorch com CUDA.")
    print("Comando sugerido:")
    print("pip uninstall torch torchvision torchaudio")
    print("pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")

try:
    import diffusers
    print(f"\nDiffusers Versão: {diffusers.__version__}")
except ImportError:
    print("\nDiffusers não instalado.")
