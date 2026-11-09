"""
SagaScript Parser e Interpreter

Este módulo é responsável por ler e executar a linguagem de script da Saga Engine.

Sintaxe Básica:
- Cada comando ocupa uma linha.
- Comentários começam com '#'.
- Argumentos são separados por espaços. Strings com espaços devem estar entre aspas duplas.

Comandos Iniciais:
- say <character_id> "Texto da fala"
- walk <character_id> <x> <y>
- give <item_id>
- take <item_id>
- start_dialog <dialog_id>
- go_to_scene <scene_id>
"""
from __future__ import annotations
import shlex
from typing import List, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from runtime.scene_manager import SceneManager

class SagaScriptParser:
    """
    Analisa uma string de script e a transforma em uma lista de comandos.
    """
    def parse(self, script_text: str) -> List[List[str]]:
        """
        Converte o texto do script em uma lista de comandos tokenizados.
        """
        commands = []
        lines = script_text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            try:
                # shlex lida com argumentos entre aspas de forma inteligente
                tokens = shlex.split(line)
                if tokens:
                    commands.append(tokens)
            except ValueError as e:
                print(f"Erro de parsing no SagaScript na linha: '{line}'. Erro: {e}")
        return commands

class SagaScriptInterpreter:
    """
    Executa uma lista de comandos SagaScript pré-analisados.
    """
    def __init__(self, scene_manager: SceneManager):
        self.scene_manager = scene_manager
        self.project = scene_manager.project
        self.current_scene = scene_manager.current_scene

    def execute(self, commands: List[List[str]]):
        """
        Executa uma lista de comandos.
        """
        print(f"Executando script com {len(commands)} comandos.")
        for command in commands:
            self._execute_command(command)

    def _execute_command(self, command: List[str]):
        """
        Executa um único comando.
        """
        verb = command[0].lower()
        args = command[1:]

        print(f"  > Executando: {verb} {args}")

        # Mapeia o verbo do comando para um método handler
        handler = getattr(self, f"_handle_{verb}", None)
        if handler:
            try:
                handler(args)
            except Exception as e:
                print(f"Erro ao executar comando '{verb}': {e}")
        else:
            print(f"Aviso: Comando SagaScript desconhecido '{verb}'.")

    # --- Handlers de Comandos ---

    def _handle_say(self, args: List[str]):
        # Por enquanto, apenas imprime no console. Futuramente, integrará com a UI de diálogo.
        if len(args) < 2:
            raise ValueError("Comando 'say' requer <character_id> e <text>.")
        character_id, text = args[0], args[1]
        print(f"[DIÁLOGO] {character_id}: {text}")

    def _handle_walk(self, args: List[str]):
        if len(args) < 3:
            raise ValueError("Comando 'walk' requer <character_id>, <x> e <y>.")
        char_id, x_str, y_str = args[0], args[1], args[2]
        
        # Encontra o personagem na cena atual
        character = next((obj for obj in self.current_scene.objects_list if obj.game_object_data.id == char_id), None)
        if not character:
            raise ValueError(f"Personagem '{char_id}' não encontrado na cena.")
            
        # Calcula o caminho e o move
        start_pos = (character.center_x, character.center_y)
        end_pos = (int(x_str), int(y_str))
        
        from runtime.pathfinding import find_path, GRID_SIZE # Importação local para evitar ciclo
        path = find_path(start_pos, end_pos, self.current_scene.pathfinding_grid, GRID_SIZE)
        if path:
            character.walk_to(path)
        else:
            print(f"Aviso: Não foi possível encontrar um caminho para '{char_id}' até ({x_str}, {y_str}).")

    def _handle_give(self, args: List[str]):
        if len(args) < 1:
            raise ValueError("Comando 'give' requer <item_id>.")
        item_id = args[0]
        
        item_asset = self.project.assets.items.get(item_id)
        if not item_asset:
            raise ValueError(f"Item asset '{item_id}' não definido no projeto.")
            
        from runtime.inventory import Item # Importação local
        texture_path = self.project.project_path / item_asset.path
        item_texture = arcade.load_texture(str(texture_path))
        item = Item(id=item_id, name=item_asset.name, description=item_asset.description, texture=item_texture)
        self.scene_manager.inventory.add_item(item)

    def _handle_take(self, args: List[str]):
        if len(args) < 1:
            raise ValueError("Comando 'take' requer <item_id>.")
        item_id = args[0]
        self.scene_manager.inventory.remove_item(item_id)

    def _handle_start_dialog(self, args: List[str]):
        if len(args) < 1:
            raise ValueError("Comando 'start_dialog' requer <dialog_id>.")
        dialog_id = args[0]
        dialog = self.project.dialogs.get(dialog_id)
        if not dialog:
            raise ValueError(f"Diálogo '{dialog_id}' não encontrado no projeto.")
        self.scene_manager.dialog_manager.start_dialog(dialog)

    def _handle_go_to_scene(self, args: List[str]):
        if len(args) < 1:
            raise ValueError("Comando 'go_to_scene' requer <scene_id>.")
        scene_id = args[0]
        self.scene_manager.go_to_scene(scene_id)
