"""
Módulo de Exportação de Projeto para a Saga Engine Editor.
"""
import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from runtime.data_models import Project

def export_project(project: Project, output_path: Path):
    """
    Exporta um projeto da Saga Engine para uma pasta executável.

    Args:
        project: A instância do projeto a ser exportado.
        output_path: O caminho para a pasta onde o jogo exportado será salvo.
    """
    if not output_path.exists():
        output_path.mkdir(parents=True, exist_ok=True)

    print(f"Iniciando exportação do projeto '{project.name}' para '{output_path}'...")

    # 1. Criar estrutura de pastas no destino
    game_data_path = output_path / "data"
    game_assets_path = output_path / "assets"
    game_runtime_path = output_path / "runtime"
    game_shared_path = output_path / "shared"

    game_data_path.mkdir(exist_ok=True)
    game_assets_path.mkdir(exist_ok=True)
    game_runtime_path.mkdir(exist_ok=True)
    game_shared_path.mkdir(exist_ok=True)

    # 2. Salvar o project.json atualizado
    project_json_path = game_data_path / "project.json"
    try:
        project_data_to_save = project.to_dict()
        with open(project_json_path, "w", encoding="utf-8") as f:
            json.dump(project_data_to_save, f, indent=2)
        print(f"  - project.json salvo em '{project_json_path}'")
    except Exception as e:
        print(f"Erro ao salvar project.json: {e}")
        raise

    # 3. Copiar assets (sprites, audio, etc.)
    # Esta é uma implementação simplificada. Em um editor real,
    # os assets seriam gerenciados de forma mais granular.
    source_assets_path = Path(project.project_path) / "assets"
    if source_assets_path.exists():
        try:
            shutil.copytree(source_assets_path, game_assets_path, dirs_exist_ok=True)
            print(f"  - Assets copiados de '{source_assets_path}' para '{game_assets_path}'")
        except Exception as e:
            print(f"Aviso: Erro ao copiar assets: {e}")
    else:
        print(f"Aviso: Pasta de assets '{source_assets_path}' não encontrada no projeto de origem.")

    # 4. Copiar arquivos essenciais do runtime
    # Copia o conteúdo da pasta 'runtime' do projeto da engine
    source_engine_runtime_path = Path(__file__).parent.parent / "runtime"
    try:
        # Ignora __pycache__ e outros arquivos temporários
        shutil.copytree(source_engine_runtime_path, game_runtime_path, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'), dirs_exist_ok=True)
        print(f"  - Runtime da engine copiado para '{game_runtime_path}'")
    except Exception as e:
        print(f"Erro ao copiar runtime da engine: {e}")
        raise

    # 5. Copiar arquivos essenciais do shared
    source_engine_shared_path = Path(__file__).parent.parent / "shared"
    try:
        shutil.copytree(source_engine_shared_path, game_shared_path, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'), dirs_exist_ok=True)
        print(f"  - Módulos compartilhados da engine copiados para '{game_shared_path}'")
    except Exception as e:
        print(f"Erro ao copiar módulos compartilhados da engine: {e}")
        raise

    # 6. Criar um script de inicialização para o jogo exportado
    # Este script chamará o runtime/main.py com o caminho do projeto exportado
    launcher_script_content = f"""
import sys
from pathlib import Path

# Adiciona o diretório raiz do jogo exportado ao sys.path
sys.path.append(str(Path(__file__).parent))

# Define o caminho do projeto exportado
exported_project_path = Path(__file__).parent / "data"

# Importa e executa o main do runtime
from runtime.main import main as runtime_main
from runtime.main import Game # Importa a classe Game para poder instanciá-la

if __name__ == "__main__":
    # Instancia o jogo com o caminho do projeto exportado
    game_window = Game(str(exported_project_path))
    game_window.setup()
    arcade.run()
"""
    launcher_path = output_path / "launch_game.py"
    try:
        with open(launcher_path, "w", encoding="utf-8") as f:
            f.write(launcher_script_content)
        print(f"  - Script de inicialização '{launcher_path}' criado.")
    except Exception as e:
        print(f"Erro ao criar script de inicialização: {e}")
        raise

    print(f"Exportação do projeto '{project.name}' concluída com sucesso!")

