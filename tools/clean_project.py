import json
from pathlib import Path
import sys

# Adiciona o diretório raiz ao path para importar módulos do backend se necessário
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

PROJECT_NAME = "Calixto Island"
PROJECT_PATH = ROOT_DIR / "projects" / PROJECT_NAME / "project.json"

def clean_project():
    if not PROJECT_PATH.exists():
        print(f"Erro: Projeto '{PROJECT_NAME}' não encontrado em {PROJECT_PATH}")
        return

    print(f"Lendo projeto: {PROJECT_PATH}")
    with open(PROJECT_PATH, "r", encoding="utf-8") as f:
        project_data = json.load(f)

    scenes = project_data.get("scenes", {})
    print(f"Total de cenas encontradas: {len(scenes)}")

    # IDs das cenas para MANTER
    # 1. A cena inicial (Sala)
    start_scene_id = project_data.get("start_scene", "scene_1")
    
    # 2. A cena Porão que tem o background gerado (identificada pelos logs anteriores)
    # Se não tiver certeza, vamos manter apenas a inicial e deixar a IA criar de novo.
    # Mas pelo log, a scene_9b38028e tinha o background.
    target_porao_id = "scene_9b38028e"

    scenes_to_keep = {start_scene_id}
    
    # Verifica se a cena Porão alvo existe e tem background
    if target_porao_id in scenes and scenes[target_porao_id].get("background"):
        print(f"Mantendo cena Porão com background: {target_porao_id}")
        scenes_to_keep.add(target_porao_id)
    else:
        print("Cena Porão alvo não encontrada ou sem background. Será removida se existir.")

    # Reconstrói o dicionário de cenas
    new_scenes = {}
    deleted_count = 0
    
    for scene_id, scene in scenes.items():
        if scene_id in scenes_to_keep:
            new_scenes[scene_id] = scene
        else:
            print(f"Removendo cena: {scene.get('name')} ({scene_id})")
            deleted_count += 1

    project_data["scenes"] = new_scenes
    
    print(f"\nResumo:")
    print(f"Cenas mantidas: {len(new_scenes)}")
    print(f"Cenas removidas: {deleted_count}")

    # Salva o arquivo limpo
    with open(PROJECT_PATH, "w", encoding="utf-8") as f:
        json.dump(project_data, f, indent=2, ensure_ascii=False)
    
    print("✅ Projeto limpo e salvo com sucesso!")

if __name__ == "__main__":
    clean_project()
