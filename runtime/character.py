"""
Módulo do Personagem para a Saga Engine.
"""
import arcade
from typing import List, Tuple
from runtime.data_models import GameObject

# --- Constantes ---
CHARACTER_SPEED = 200  # Pixels por segundo

class Character(arcade.Sprite):
    """
    Representa um personagem ou objeto animado na cena.
    """
    def __init__(self, game_object_data: GameObject):
        super().__init__()

        self.game_object_data = game_object_data

        # Atributos de movimento
        self.path: List[Tuple[float, float]] = []
        self.current_path_index = 0
        self.is_walking = False
        self.speed = CHARACTER_SPEED

    def update_animation(self, delta_time: float = 1/60):
        """
        Atualiza a animação do sprite.
        """
        # Futuramente: trocar a textura com base no estado (is_walking) e direção.
        pass

    def walk_to(self, path: List[Tuple[float, float]]):
        """
        Define um novo caminho para o personagem seguir.
        """
        if not path:
            return
        self.path = path
        self.current_path_index = 0
        self.is_walking = True
        print(f"Personagem '{self.game_object_data.id}' iniciando caminho.")

    def on_update(self, delta_time: float = 1/60):
        """
        Atualiza a posição e o estado do personagem.
        """
        if not self.is_walking or not self.path:
            return

        # Pega o próximo ponto no caminho
        target_pos = self.path[self.current_path_index]
        
        # Calcula a direção e a distância
        start_x, start_y = self.center_x, self.center_y
        dest_x, dest_y = target_pos
        
        dx = dest_x - start_x
        dy = dest_y - start_y
        distance = (dx**2 + dy**2)**0.5

        # Se estiver perto o suficiente do ponto, avança para o próximo
        if distance < 5:
            self.current_path_index += 1
            # Se o caminho terminou, para de andar
            if self.current_path_index >= len(self.path):
                self.is_walking = False
                self.path = []
                print(f"Personagem '{self.game_object_data.id}' chegou ao destino.")
            return

        # Normaliza o vetor de direção e calcula a velocidade
        self.change_x = (dx / distance) * self.speed
        self.change_y = (dy / distance) * self.speed

        # Move o sprite
        self.center_x += self.change_x * delta_time
        self.center_y += self.change_y * delta_time
