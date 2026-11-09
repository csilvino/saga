import sys
from pathlib import Path
import inspect

# Adiciona o diretório raiz ao path para que possamos importar o backend
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

try:
    from backend.api.routes import yolo_detection
    print("✅ Módulo 'yolo_detection' importado com sucesso.")
    
    # Inspeciona o router
    if hasattr(yolo_detection, 'router'):
        print("✅ Objeto 'router' encontrado no módulo.")
        router = yolo_detection.router
        
        print("\n--- Rotas Registradas no yolo_detection.router ---")
        for route in router.routes:
            print(f"  - Path: {route.path}")
            print(f"    Methods: {route.methods}")
            print(f"    Name: {route.name}")
        print("--------------------------------------------------")
        
        if not router.routes:
            print("⚠️ AVISO: Nenhuma rota foi registrada no objeto router.")
            
    else:
        print("❌ ERRO: Objeto 'router' não encontrado no módulo 'yolo_detection'.")

except ImportError as e:
    print(f"❌ ERRO: Falha ao importar o módulo 'yolo_detection'.")
    print(f"   Detalhe: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

