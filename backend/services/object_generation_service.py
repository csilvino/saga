import random
from typing import Dict, Any

def get_placeholder(object_type: str, mode: str = "emoji") -> str:
    """Gera um placeholder para o sprite de um objeto."""
    if mode == "emoji":
        # Mapeia tipos de objeto para emojis relevantes
        emoji_map = {
            "personagem": "🧍",
            "item": "❓",
            "porta": "🚪",
            "mesa": "🪑",
            "cadeira": "🪑",
            "estante": "📚",
            "chave": "🔑",
            "default": "📦"
        }
        # Encontra a chave mais próxima no mapa de emojis
        for key, emoji in emoji_map.items():
            if key in object_type.lower():
                return emoji
        return emoji_map["default"]
    elif mode == "text":
        return f"[{object_type.upper()}]"
    else:
        return "placeholder.png"

def generate_ses_template(object_name: str, description: str, object_type: str) -> str:
    """Gera um template de script SES baseado no tipo e descrição do objeto."""
    base_script = f"// Script para o objeto {object_name}\n\n"
    
    # Adiciona um bloco 'on examine' com a descrição
    examine_script = f"on examine {{\n  narrate('{description}')\n}}\n\n"
    
    # Adiciona blocos específicos por tipo
    type_specific_script = ""
    if "porta" in object_type.lower():
        type_specific_script = """on interact {
  if get_state('trancada') {
    narrate('A porta está trancada.')
  } else {
    narrate('Você abre a porta.')
    // Adicione aqui a lógica para mudar de cena
  }
}
"""
    elif "chave" in object_type.lower():
        type_specific_script = """on interact {
  narrate('Você pegou a chave.')
  add_to_inventory(self.id)
  destroy(self)
}
"""
    elif "item" in object_type.lower():
        type_specific_script = """on interact {
  narrate('Você pegou o item.')
  add_to_inventory(self.id)
  destroy(self)
}
"""
    else:
        type_specific_script = """on interact {
  narrate('Não parece fazer nada por enquanto.')
}
"""
        
    return base_script + examine_script + type_specific_script

def calculate_smart_position(scene_data: Dict[str, Any], object_type: str) -> Dict[str, int]:
    """Calcula uma posição inicial inteligente para um novo objeto."""
    scene_width = scene_data.get("size", {}).get("width", 1920)
    scene_height = scene_data.get("size", {}).get("height", 1080)
    
    # Evita sobreposição com objetos existentes
    existing_positions = [obj.get("position", {"x": 0, "y": 0}) for obj in scene_data.get("objects", [])]
    
    for _ in range(20): # Tenta 20 vezes encontrar um lugar
        x = random.randint(int(scene_width * 0.1), int(scene_width * 0.9))
        y = random.randint(int(scene_height * 0.5), int(scene_height * 0.9)) # Prefere a metade inferior da tela
        
        is_overlapping = False
        for pos in existing_positions:
            distance = ((pos["x"] - x)**2 + (pos["y"] - y)**2)**0.5
            if distance < 150: # Se estiver a menos de 150 pixels de outro objeto
                is_overlapping = True
                break
        
        if not is_overlapping:
            return {"x": x, "y": y}
            
    # Se não encontrar um lugar depois de 20 tentativas, retorna uma posição aleatória
    return {"x": random.randint(200, scene_width - 200), "y": random.randint(200, scene_height - 200)}
