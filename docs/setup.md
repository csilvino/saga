# Setup do Ambiente  Saga Engine

1) Criar virtualenv (Windows PowerShell)
   python -m venv .venv
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
   & ".\.venv\Scripts\Activate.ps1"

2) Instalar dependências
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   python -m pip install -r requirements-dev.txt

3) Instalar pre-commit (opcional)
   python -m pip install pre-commit
   pre-commit install

4) Rodar testes
   python -m pytest

5) Validar projetos (exemplo)
   python tools\validate_project.py projects\demo\project.json

Observações:
- Use o Python do .venv para todas as operações acima.
- Se estiver usando o GitHub Actions / CI, replique os mesmos passos no pipeline.
