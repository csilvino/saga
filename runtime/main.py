"""
Saga Engine - Runtime
"""
import arcade
import sys
from pathlib import Path

# Adiciona o diretório raiz do projeto ao sys.path
# para permitir importações de outros módulos como 'runtime'.
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

from runtime.project_loader import load_project_data, ProjectLoadError
from runtime.data_models import Project
from runtime.scene_manager import SceneManager
from runtime.audio_manager import AudioManager

# --- Constantes ---
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_TITLE = "Saga Engine"
DEMO_PROJECT_PATH = ROOT_DIR / "projects" / "demo"


class Game(arcade.Window):
    """
    Classe principal do jogo.
    """

    def __init__(self, project_path: str):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        arcade.set_background_color(arcade.csscolor.BLACK)

        self.project_path = project_path
        self.project: Project | None = None
        self.scene_manager: SceneManager | None = None
        self.audio_manager: AudioManager | None = None

    def setup(self):
        """
        Configura o jogo para uma nova partida.
        """
        try:
            project_data = load_project_data(self.project_path)
            self.project = Project.from_dict(project_data, self.project_path)
            self.set_caption(f"{self.project.name} - {SCREEN_TITLE}")

            # Inicializa os gerenciadores
            self.audio_manager = AudioManager(self.project)
            self.scene_manager = SceneManager(self.project)
            self.scene_manager.go_to_scene(self.project.start_scene)

        except ProjectLoadError as e:
            print(f"Erro fatal ao carregar o projeto: {e}")
            self.close()
            return

    def on_draw(self):
        """
        Renderiza a tela.
        """
        self.clear()

        if self.scene_manager:
            self.scene_manager.on_draw()
        else:
            # Fallback se o SceneManager não for inicializado
            arcade.draw_text(
                "Falha ao inicializar o SceneManager",
                self.width / 2,
                self.height / 2,
                arcade.color.RED,
                font_size=40,
                anchor_x="center",
            )

    def on_update(self, delta_time: float):
        """
        Lógica do jogo e atualizações de estado.
        """
        if self.scene_manager and self.scene_manager.current_scene:
            self.scene_manager.current_scene.objects_list.update()


    def on_key_press(self, key, modifiers):
        """
        Chamado quando uma tecla é pressionada.
        """
        if key == arcade.key.ESCAPE:
            self.close()

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int):
        """
        Chamado quando um botão do mouse é pressionado.
        """
        if self.scene_manager:
            self.scene_manager.on_mouse_press(x, y, button, modifiers)


def main():
    """
    Função principal que inicia o jogo.
    """
    window = Game(str(DEMO_PROJECT_PATH))
    window.setup()
    arcade.run()


if __name__ == "__main__":
    main()
