"""
Gerenciador de Cenas e Lógica de Cena para o Runtime.
"""
from __future__ import annotations
import arcade
from pathlib import Path
from typing import Dict, TYPE_CHECKING

from runtime.data_models import Scene as SceneData, Action
from runtime.character import Character
from runtime.pathfinding import find_path
from runtime.inventory import Inventory, Item
from runtime.dialog_manager import DialogManager
from runtime.sagascript import SagaScriptParser, SagaScriptInterpreter
from runtime.audio_manager import AudioManager
from runtime.persistence import GameState, save_game, load_game

if TYPE_CHECKING:
    from runtime.data_models import Project

# --- Constantes ---
GRID_SIZE = 64 # Tamanho de cada célula do grid para pathfinding


class Scene:
    """
    Representa uma cena ativa no jogo, com seus assets carregados.
    """

    def __init__(self, manager: SceneManager, project: Project, scene_data: SceneData):
        self.manager = manager
        self.project = project
        self.scene_data = scene_data
        self.project_path = Path(project.project_path)
        
        # Assets e objetos da cena
        # Lista específica para o background (exigência do Arcade 3.0+)
        self.background_list: arcade.SpriteList = arcade.SpriteList()
        
        self.objects_list: arcade.SpriteList = arcade.SpriteList()
        self.player_character: Character | None = None # Referência ao personagem do jogador
        self.blocking_sprites: arcade.SpriteList = arcade.SpriteList() # Sprites que bloqueiam o caminho

        # Pathfinding
        self.pathfinding_grid: arcade.AStarBarrierList | None = None

    def load(self):
        """
        Carrega os assets e objetos necessários para esta cena.
        """
        # Limpa listas da cena anterior
        self.objects_list.clear()
        self.blocking_sprites.clear()
        self.background_list.clear() # Limpa a lista de background
        self.player_character = None

        # Carrega o background como um Sprite
        background_path = self.project_path / self.scene_data.background
        if background_path.exists():
            # Cria um sprite para o fundo
            background_sprite = arcade.Sprite()
            # Carrega a textura
            texture = arcade.load_texture(str(background_path))
            background_sprite.texture = texture
            # Posiciona no centro da tela
            background_sprite.center_x = texture.width / 2
            background_sprite.center_y = texture.height / 2
            
            # Adiciona à lista de background
            self.background_list.append(background_sprite)
        else:
            print(f"Aviso: Imagem de fundo não encontrada em '{background_path}'")

        # Carrega os objetos da cena (personagens, etc.)
        for obj_data in self.scene_data.objects:
            character = Character(obj_data)
            
            # Encontra o asset do sprite correspondente
            sprite_asset = self.project.assets.sprites.get(obj_data.sprite)
            if not sprite_asset:
                print(f"Aviso: Sprite asset '{obj_data.sprite}' não encontrado.")
                continue

            # Carrega a textura
            texture_path = self.project_path / sprite_asset.path
            if texture_path.exists():
                character.texture = arcade.load_texture(str(texture_path))
            else:
                print(f"Aviso: Textura não encontrada em '{texture_path}'")
                continue
            
            # Define a posição
            character.center_x = obj_data.position.x
            character.center_y = obj_data.position.y
            
            self.objects_list.append(character)
            
            # Por enquanto, assume que o primeiro objeto do tipo 'prop' é o personagem do jogador
            if obj_data.type == "prop" and self.player_character is None:
                self.player_character = character

        # Configura o grid de pathfinding
        if self.player_character:
            self.pathfinding_grid = arcade.AStarBarrierList(
                moving_sprite=self.player_character,
                blocking_sprites=self.blocking_sprites,
                grid_size=GRID_SIZE,
                left=0,
                right=self.scene_data.size.width,
                bottom=0,
                top=self.scene_data.size.height
            )

    def on_draw(self):
        """
        Desenha a cena.
        """
        # Desenha a lista de background (agora correto para Arcade 3.0)
        self.background_list.draw()
        
        if len(self.background_list) == 0:
             arcade.draw_text(f"Cena: {self.scene_data.name}", 10, 10, arcade.color.WHITE, font_size=20)
        
        self.objects_list.draw()

    def _execute_action(self, action: Action):
        """
        Executa uma ação definida no projeto.
        """
        print(f"Executando ação: {action.type} com parâmetros {action.params}")
        if action.type == "go_to_scene":
            target_scene_id = action.params.get("scene")
            if target_scene_id:
                self.manager.go_to_scene(target_scene_id)
        elif action.type == "add_item":
            item_id = action.params.get("item_id")
            if item_id:
                item_asset = self.project.assets.items.get(item_id)
                if item_asset:
                    # Carrega a textura do item
                    texture_path = self.project_path / item_asset.path
                    if texture_path.exists():
                        item_texture = arcade.load_texture(str(texture_path))
                        item = Item(id=item_id, name=item_asset.name, description=item_asset.description, texture=item_texture)
                        self.manager.inventory.add_item(item)
                    else:
                        print(f"Erro: Textura do item '{item_id}' não encontrada em '{texture_path}'")
                else:
                    print(f"Erro: Item asset '{item_id}' não encontrado no projeto.")
        elif action.type == "remove_item":
            item_id = action.params.get("item_id")
            if item_id:
                self.manager.inventory.remove_item(item_id)
        elif action.type == "combine_items":
            item1_id = action.params.get("item1_id")
            item2_id = action.params.get("item2_id")
            result_item_id = action.params.get("result_item_id")
            if item1_id and item2_id and result_item_id:
                if self.manager.inventory.has_item(item1_id) and self.manager.inventory.has_item(item2_id):
                    self.manager.inventory.remove_item(item1_id)
                    self.manager.inventory.remove_item(item2_id)
                    # Adiciona o item resultante
                    item_asset = self.project.assets.items.get(result_item_id)
                    if item_asset:
                        texture_path = self.project_path / item_asset.path
                        if texture_path.exists():
                            item_texture = arcade.load_texture(str(texture_path))
                            item = Item(id=result_item_id, name=item_asset.name, description=item_asset.description, texture=item_texture)
                            self.manager.inventory.add_item(item)
                        else:
                            print(f"Erro: Textura do item '{result_item_id}' não encontrada em '{texture_path}'")
                    else:
                        print(f"Erro: Item asset '{result_item_id}' não encontrado no projeto.")
                else:
                    print("Erro: O jogador não possui os itens necessários para a combinação.")
        elif action.type == "start_dialog":
            dialog_id = action.params.get("dialog_id")
            if dialog_id:
                dialog = self.project.dialogs.get(dialog_id)
                if dialog:
                    self.manager.dialog_manager.start_dialog(dialog)
                else:
                    print(f"Erro: Diálogo '{dialog_id}' não encontrado no projeto.")
        elif action.type == "run_script":
            script_id = action.params.get("script_id")
            if script_id:
                script_text = self.project.scripts.get(script_id)
                if script_text:
                    parser = SagaScriptParser()
                    commands = parser.parse(script_text)
                    interpreter = SagaScriptInterpreter(self.manager)
                    interpreter.execute(commands)
                else:
                    print(f"Erro: Script '{script_id}' não encontrado no projeto.")
        elif action.type == "play_music":
            music_id = action.params.get("music_id")
            if music_id:
                self.manager.audio_manager.play_music(music_id)
        elif action.type == "play_sound":
            sound_id = action.params.get("sound_id")
            if sound_id:
                self.manager.audio_manager.play_sound(sound_id)
        elif action.type == "stop_music":
            self.manager.audio_manager.stop_music()
        elif action.type == "save_game":
            slot = action.params.get("slot", 1)
            self.manager.save_game(slot)
        elif action.type == "load_game":
            slot = action.params.get("slot", 1)
            self.manager.load_game(slot)


    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int):
        """
        Processa cliques do mouse para esta cena.
        """
        hotspot_clicked = False
        for hotspot in self.scene_data.hotspots:
            if hotspot.enabled and arcade.geometry.is_point_in_polygon(x, y, hotspot.shape.points):
                print(f"Hotspot '{hotspot.name}' clicado!")
                self._execute_action(hotspot.action)
                hotspot_clicked = True
                break
        
        if not hotspot_clicked:
            if self.project.navigation_mode == "pathfinding":
                if self.player_character and self.pathfinding_grid:
                    start_pos = (self.player_character.center_x, self.player_character.center_y)
                    end_pos = (x, y)
                    path = find_path(start_pos, end_pos, self.pathfinding_grid, GRID_SIZE)
                    if path:
                        print(f"Caminho encontrado para ({x}, {y}): {path}")
                        self.player_character.walk_to(path) # Personagem andará pelo caminho
                    else:
                        print(f"Nenhum caminho encontrado para ({x}, {y}).")
                else:
                    print("Personagem do jogador ou grid de pathfinding não disponível.")
            elif self.project.navigation_mode == "first_person":
                print(f"Nenhum hotspot clicado. No modo 'first_person', cliques no fundo não fazem nada.")


class SceneManager:
    """
    Gerencia as cenas do jogo, incluindo o carregamento e a transição.
    """

    def __init__(self, project: Project):
        self.project = project
        self.audio_manager = AudioManager(project)
        self.scenes: Dict[str, Scene] = {}
        self.current_scene: Scene | None = None
        self.inventory = Inventory()
        self.dialog_manager = DialogManager()
        self._load_all_scenes()

    def _load_all_scenes(self):
        """
        Pré-carrega as definições de todas as cenas do projeto.
        """
        for scene_id, scene_data in self.project.scenes.items():
            scene = Scene(self, self.project, scene_data)
            self.scenes[scene_id] = scene

    def go_to_scene(self, scene_id: str):
        """
        Muda para a cena especificada.
        """
        if scene_id not in self.scenes:
            print(f"Erro: Tentativa de ir para cena inexistente '{scene_id}'")
            return
        
        if self.current_scene and self.current_scene.scene_data.id == scene_id:
            return

        print(f"Transicionando para a cena: {scene_id}")
        self.current_scene = self.scenes[scene_id]
        self.current_scene.load()

    def save_game(self, slot: int):
        """
        Coleta o estado atual do jogo e o salva.
        """
        if not self.current_scene or not self.current_scene.player_character:
            print("Erro: Não é possível salvar o jogo sem uma cena ou personagem.")
            return

        game_state = GameState(
            current_scene_id=self.current_scene.scene_data.id,
            player_position=(self.current_scene.player_character.center_x, self.current_scene.player_character.center_y),
            inventory_items=list(self.inventory.items.keys())
        )
        save_game(game_state, slot)

    def load_game(self, slot: int):
        """
        Carrega um estado de jogo e o aplica.
        """
        game_state = load_game(slot)
        if game_state:
            self.apply_game_state(game_state)

    def apply_game_state(self, game_state: GameState):
        """
        Aplica um estado de jogo carregado.
        """
        print(f"Aplicando estado do jogo: {game_state}")
        # Restaura o inventário
        self.inventory.items.clear()
        for item_id in game_state.inventory_items:
            item_asset = self.project.assets.items.get(item_id)
            if item_asset:
                texture_path = self.project.project_path / item_asset.path
                if texture_path.exists():
                    item_texture = arcade.load_texture(str(texture_path))
                    item = Item(id=item_id, name=item_asset.name, description=item_asset.description, texture=item_texture)
                    self.inventory.add_item(item)
        
        # Muda para a cena correta
        self.go_to_scene(game_state.current_scene_id)
        
        # Restaura a posição do jogador
        if self.current_scene and self.current_scene.player_character:
            self.current_scene.player_character.center_x, self.current_scene.player_character.center_y = game_state.player_position

    def on_draw(self):
        """
        Chama o método de desenho da cena atual e da UI de diálogo.
        """
        if self.current_scene:
            self.current_scene.on_draw()
        
        if self.dialog_manager.is_active:
            self._draw_dialog_ui()

    def _draw_dialog_ui(self):
        """
        Desenha a UI de diálogo.
        """
        if not self.dialog_manager.current_node:
            return

        node = self.dialog_manager.current_node
        if node.type == "line":
            arcade.draw_text(node.text, 100, 100, arcade.color.WHITE, 24)
        elif node.type == "choice":
            for i, choice in enumerate(node.choices):
                arcade.draw_text(f"{i+1}: {choice.text}", 100, 150 + i * 50, arcade.color.YELLOW, 20)

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int):
        """
        Delega o evento de clique para a cena atual ou para o diálogo.
        """
        if self.dialog_manager.is_active:
            # Lógica de clique para o diálogo
            if self.dialog_manager.current_node.type == "line":
                self.dialog_manager.advance_dialog()
            elif self.dialog_manager.current_node.type == "choice":
                # Lógica para escolher uma opção (simplificada)
                # Aqui, estamos apenas avançando para a primeira escolha
                self.dialog_manager.advance_dialog(0)
        elif self.current_scene:
            self.current_scene.on_mouse_press(x, y, button, modifiers)
