import os
from pathlib import Path

base_dir = Path("D:/PythonProject/saga/backend")
dirs = [
    "api/routes",
    "services",
    "models",
    "schemas"
]

for d in dirs:
    path = base_dir / d
    path.mkdir(parents=True, exist_ok=True)
    (path / "__init__.py").touch()
    print(f"Created: {path}")

# Criar arquivos placeholder para rotas
(base_dir / "api/routes/projects.py").touch()
(base_dir / "api/routes/scenes.py").touch()
(base_dir / "api/routes/dialogs.py").touch()
(base_dir / "api/routes/ai.py").touch()

print("Backend structure created successfully.")
