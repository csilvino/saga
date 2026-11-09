import requests
import json

BASE_URL = "http://localhost:8070"

def test_extraction():
    # 1. Obter um projeto e uma cena (usando o primeiro da lista ou criando um mock)
    print("Listando projetos...")
    projects = requests.get(f"{BASE_URL}/api/projects/list").json()
    if not projects:
        print("Nenhum projeto encontrado. Crie um projeto primeiro.")
        return
    
    project_name = projects[0]
    print(f"Usando projeto: {project_name}")
    
    # Carregar projeto
    project = requests.post(f"{BASE_URL}/api/projects/load", json={"name": project_name}).json()['project']
    
    # Pegar uma cena com background
    scene_with_bg = None
    for sid, scene in project['scenes'].items():
        bg_path = scene.get('background', '')
        # Procurar por backgrounds na pasta correta
        if bg_path and 'backgrounds/' in bg_path:
            scene_with_bg = scene
            break
            
    if not scene_with_bg:
        # Se não houver, tentar qualquer background
        for sid, scene in project['scenes'].items():
            if scene.get('background'):
                scene_with_bg = scene
                break
    
    if not scene_with_bg:
        print("Nenhuma cena com background encontrada.")
        return

    print(f"Usando cena: {scene_with_bg['name']} com background: {scene_with_bg['background']}")

    # Simular uma seleção (um quadrado no meio da imagem)
    # Assumindo 1920x1080
    selection = [
        {"x": 800, "y": 400},
        {"x": 1100, "y": 400},
        {"x": 1100, "y": 700},
        {"x": 800, "y": 700}
    ]

    payload = {
        "project_name": project_name,
        "scene_id": scene_with_bg['id'],
        "image_path": scene_with_bg['background'],
        "selection_points": selection
    }

    print("Enviando requisição de extração...")
    response = requests.post(f"{BASE_URL}/api/genai/edit/extract-object", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print("Sucesso!")
        print(json.dumps(data, indent=2))
    else:
        print(f"Erro: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_extraction()
