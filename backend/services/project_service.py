from pathlib import Path
import json
import os
from typing import Dict, Any, Optional
import shutil
from fastapi import HTTPException

ROOT_DIR = Path(__file__).parent.parent.parent

class ProjectLoadError(Exception):
    """Exceção para erros durante o carregamento de um projeto."""
    pass

class ProjectService:
    def __init__(self):
        self._project: Dict[str, Any] = {}
        self._project_path: Optional[Path] = None

    @property
    def project(self) -> Dict[str, Any]:
        """Retorna os dados do projeto atualmente carregado."""
        if not self._project:
            raise ProjectLoadError("Nenhum projeto está carregado.")
        return self._project

    @property
    def project_path(self) -> Optional[Path]:
        """Retorna o caminho para a pasta do projeto atualmente carregado."""
        return self._project_path

    def _ensure_project_structure(self, project_dir: Path):
        """Garante que a estrutura de pastas de assets exista."""
        project_dir.mkdir(parents=True, exist_ok=True)
        for sub_dir in ["sprites", "backgrounds", "audio", "items", "fonts"]:
            (project_dir / sub_dir).mkdir(exist_ok=True)

    def load_project_path(self, project_name: str) -> Path:
        """Carrega o caminho de um projeto e o define como ativo."""
        project_dir = ROOT_DIR / "projects" / project_name
        if not project_dir.exists():
            raise ProjectLoadError(f"Pasta do projeto '{project_name}' não encontrada.")
        self._project_path = project_dir
        return project_dir

    def load_project(self, project_name: str) -> Dict[str, Any]:
        """Carrega os dados de um projeto e define-o como ativo."""
        project_dir = self.load_project_path(project_name)
        project_file = project_dir / "project.json"
        
        
        if not project_file.exists():
            raise ProjectLoadError(f"Arquivo 'project.json' não encontrado em '{project_dir}'.")
        
        with open(project_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            self._project = data
        
        return self._project

    def save_project_data(self, project_name: str, project_data: Dict[str, Any]):
        """Salva os dados de um projeto."""
        if not project_name:
            raise ValueError("O nome do projeto não pode ser vazio.")

        project_dir = ROOT_DIR / "projects" / project_name
        self._ensure_project_structure(project_dir)

        project_file = project_dir / "project.json"
        backup_file = project_dir / "project.json.bak"
        
        # Faz backup antes de salvar
        if project_file.exists():
            shutil.copy2(project_file, backup_file)

        # Escreve diretamente no arquivo
        with open(project_file, "w", encoding="utf-8") as f:
            json.dump(project_data, f, indent=2, ensure_ascii=False)

        if self._project_path and self._project_path.name == project_name:
            self._project = project_data

    def create_backup(self, project_name: str):
        """Cria um backup do arquivo project.json."""
        project_dir = ROOT_DIR / "projects" / project_name
        project_file = project_dir / "project.json"
        backup_file = project_dir / "project.json.bak"
        
        if project_file.exists():
            shutil.copy2(project_file, backup_file)

    def restore_backup(self, project_name: str) -> Dict[str, Any]:
        """Restaura o projeto a partir do último backup."""
        project_dir = ROOT_DIR / "projects" / project_name
        project_file = project_dir / "project.json"
        backup_file = project_dir / "project.json.bak"
        
        if not backup_file.exists():
            raise HTTPException(status_code=404, detail="Nenhum backup encontrado para este projeto.")
            
        shutil.copy2(backup_file, project_file)
        
        # Recarrega os dados na memória
        return self.load_project(project_name)

    def create_project(self, project_name: str):
        """Cria um novo projeto com a estrutura de pastas e o project.json padrão."""
        project_dir = ROOT_DIR / "projects" / project_name
        if project_dir.exists():
            raise ValueError(f"O projeto '{project_name}' já existe.")

        default_project = {
            "name": project_name,
            "start_scene": "default",
            "launcher": {
                "title": project_name,
                "description": "Inicie sua jornada épica com o Saga Engine.",
                "flyer_image": "/flyer_calixto.png",
                "version": "1.0.0"
            },
            "scenes": {
                "default": {
                    "id": "default",
                    "name": "Cena de Exemplo",
                    "background": "",
                    "objects": [],
                    "hotspots": []
                }
            },
            "metadata": {
                "action_history": [],
                "deleted_objects": [],
                "narrative_directives": ""
            }
        }
        # Usa o método de salvamento unificado
        self.save_project_data(project_name, default_project)

    def log_action(self, project_name: str, action_type: str, description: str):
        """Registra uma ação no histórico do projeto."""
        try:
            project_data = self.load_project(project_name)
            if "metadata" not in project_data:
                project_data["metadata"] = {
                    "action_history": [],
                    "deleted_objects": [],
                    "narrative_directives": ""
                }
            
            history = project_data["metadata"].get("action_history", [])
            # Mantém apenas as últimas 50 ações
            history.insert(0, {
                "type": action_type,
                "description": description,
                "timestamp": project_data.get("last_modified", "") # Ou gerar timestamp real
            })
            project_data["metadata"]["action_history"] = history[:50]
            
            # Se a ação for um delete, registra em uma lista especial para a IA saber o que existia
            if action_type.upper() == "DELETE":
                deleted = project_data["metadata"].get("deleted_objects", [])
                deleted.insert(0, {"description": description})
                project_data["metadata"]["deleted_objects"] = deleted[:20]

            self.save_project_data(project_name, project_data)
        except Exception as e:
            pass # Silenciosamente falha no log para evitar WinError 233

    def cleanup_history(self, project_name: str):
        """Remove entradas consecutivas idênticas no histórico de ações."""
        try:
            project_data = self.load_project(project_name)
            if "metadata" not in project_data or "action_history" not in project_data["metadata"]:
                return

            history = project_data["metadata"]["action_history"]
            if not history:
                return

            new_history = []
            for i, entry in enumerate(history):
                if i == 0:
                    new_history.append(entry)
                    continue
                
                # Compara com a anterior (ignorando timestamp se necessário, mas aqui comparamos o objeto todo)
                prev = new_history[-1]
                if entry["type"] == prev["type"] and entry["description"] == prev["description"]:
                    continue
                
                new_history.append(entry)

            if len(new_history) != len(history):
                project_data["metadata"]["action_history"] = new_history
                self.save_project_data(project_name, project_data)
                return True
            return False
        except Exception as e:
            return False

# Instância única do serviço para gerenciar o estado do projeto
project_service = ProjectService()

# Funções de dependência para o FastAPI
def get_project() -> Dict[str, Any]:
    """Dependência do FastAPI para obter o projeto ativo."""
    if not project_service.project:
        raise HTTPException(status_code=400, detail="Nenhum projeto foi carregado. Por favor, carregue um projeto primeiro.")
    return project_service.project

def get_project_path() -> Path:
    """Dependência do FastAPI para obter o caminho do projeto ativo."""
    if not project_service.project_path:
        raise HTTPException(status_code=400, detail="Nenhum projeto foi carregado. Por favor, carregue um projeto primeiro.")
    return project_service.project_path
