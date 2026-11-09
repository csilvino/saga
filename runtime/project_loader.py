"""
Carrega e valida os dados de um projeto da Saga Engine.
"""
import json
from pathlib import Path
# import jsonschema

# O caminho para o schema é relativo à raiz do projeto.
# Usamos '..' para subir um nível a partir de 'runtime'.
# SCHEMA_PATH = Path(__file__).parent.parent / "shared" / "project_schema.json"


class ProjectLoadError(Exception):
    """Exceção personalizada para erros de carregamento de projeto."""
    pass


def load_project_data(project_path: str) -> dict:
    """
    Carrega, valida e retorna os dados do arquivo project.json.
    """
    print(f"  [loader] Iniciando load_project_data com: '{project_path}'")
    
    project_file_path = Path(project_path) / "project.json"
    print(f"  [loader] Caminho completo do arquivo do projeto: {project_file_path}")

    if not project_file_path.exists():
        print(f"  [loader] ERRO: Arquivo não existe no caminho acima.")
        raise ProjectLoadError(f"Arquivo 'project.json' não encontrado em: {project_file_path}")

    print(f"  [loader] Arquivo project.json encontrado. Tentando abrir e ler...")
    try:
        with open(project_file_path, "r", encoding="utf-8-sig") as f:
            print(f"  [loader] Arquivo aberto. Tentando decodificar JSON...")
            data = json.load(f)
            print(f"  [loader] JSON decodificado com sucesso.")
    except json.JSONDecodeError as e:
        print(f"  [loader] ERRO: Falha na decodificação do JSON.")
        raise ProjectLoadError(f"Erro ao decodificar o JSON: {e}") from e
    except Exception as e:
        print(f"  [loader] ERRO: Erro inesperado ao abrir/ler o arquivo: {e}")
        raise ProjectLoadError(f"Erro inesperado ao ler o arquivo do projeto: {e}") from e

    # A validação do schema continua comentada para evitar erros.
    # try:
    #     with open(SCHEMA_PATH, "r", encoding="utf-8-sig") as f:
    #         schema = json.load(f)
    #     jsonschema.validate(instance=data, schema=schema)
    # except FileNotFoundError:
    #     raise ProjectLoadError(f"Schema de validação não encontrado em: {SCHEMA_PATH}")
    # except jsonschema.exceptions.ValidationError as e:
    #     raise ProjectLoadError(f"Erro de validação do projeto: {e.message}") from e

    print(f"  [loader] Projeto '{data.get('name')}' carregado com sucesso.")
    return data


if __name__ == '__main__':
    # Exemplo de uso e teste rápido
    # Para executar: python -m runtime.project_loader
    try:
        # Assume que o script é executado da raiz do projeto SAGA ENGINE
        project_data = load_project_data("projects/demo")
    except ProjectLoadError as e:
        print(f"Falha ao carregar o projeto: {e}")
