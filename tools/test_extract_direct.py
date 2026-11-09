import requests
import json

BASE_URL = "http://localhost:8070"

def test_extraction_direct():
    """Test com caminho direto para um background conhecido"""
    
    # Usar um background que sabemos que existe
    payload = {
        "project_name": "Calixto Island",
        "scene_id": "scene_001",  # ID não importa para este teste
        "image_path": "backgrounds/Gemini_Generated_Image_8phyzw8phyzw8phy.png",
        "selection_points": [
            {"x": 500, "y": 300},
            {"x": 800, "y": 300},
            {"x": 800, "y": 600},
            {"x": 500, "y": 600}
        ]
    }

    print("Testando extração com background conhecido...")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(f"{BASE_URL}/api/genai/edit/extract-object", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print("\n✅ SUCESSO!")
        print(json.dumps(data, indent=2))
    else:
        print(f"\n❌ Erro: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_extraction_direct()
