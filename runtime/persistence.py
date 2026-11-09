"""
Módulo de Persistência para a Saga Engine.
"""
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Optional, Tuple

SAVE_GAME_DIR = Path.home() / ".saga_engine" / "saves"

@dataclass
class GameState:
    """
    Representa os dados de um jogo salvo.
    """
    current_scene_id: str
    player_position: Tuple[float, float]
    inventory_items: List[str]
    # Futuramente, podemos adicionar outras variáveis de estado aqui
    # game_variables: Dict[str, any]

def save_game(game_state: GameState, slot: int):
    """
    Salva o estado do jogo em um arquivo JSON.
    """
    SAVE_GAME_DIR.mkdir(parents=True, exist_ok=True)
    save_path = SAVE_GAME_DIR / f"save_{slot}.json"
    
    try:
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(asdict(game_state), f, indent=2)
        print(f"Jogo salvo com sucesso no slot {slot} em: {save_path}")
    except Exception as e:
        print(f"Erro ao salvar o jogo no slot {slot}: {e}")

def load_game(slot: int) -> Optional[GameState]:
    """
    Carrega o estado do jogo de um arquivo JSON.
    """
    save_path = SAVE_GAME_DIR / f"save_{slot}.json"
    
    if not save_path.exists():
        print(f"Aviso: Nenhum jogo salvo encontrado no slot {slot}.")
        return None
        
    try:
        with open(save_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            game_state = GameState(**data)
            print(f"Jogo carregado com sucesso do slot {slot}.")
            return game_state
    except Exception as e:
        print(f"Erro ao carregar o jogo do slot {slot}: {e}")
        return None

if __name__ == '__main__':
    # Exemplo de uso
    # Cria um estado de jogo de exemplo
    state = GameState(
        current_scene_id="scene_1",
        player_position=(400.0, 300.0),
        inventory_items=["key_01", "galho"]
    )
    
    # Salva o jogo no slot 1
    save_game(state, 1)
    
    # Carrega o jogo do slot 1
    loaded_state = load_game(1)
    
    if loaded_state:
        assert loaded_state.current_scene_id == "scene_1"
        assert loaded_state.inventory_items == ["key_01", "galho"]
        print("\nTeste de salvar/carregar concluído com sucesso.")
