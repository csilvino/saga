# Style Guide — Saga Engine

Base: PEP8 (Python 3.10+). Ferramentas recomendadas: black, isort, ruff (ou flake8), pre-commit.

Principais regras
- Formatação automática: black (use as opções padrão).
- Ordenação de imports: isort com profile = black.
- Linting: ruff (preferido) ou flake8.
- Tipagem: usar type hints em APIs públicas; preferir clareza.
- Nomenclatura:
  - pacotes/módulos: snake_case
  - classes: PascalCase
  - funções/variáveis: snake_case
  - constantes: UPPER_SNAKE_CASE
- Docstrings: preferir Google style; fornecer resumo + parâmetros/retorno quando relevante.
- Logging: use logging.getLogger(__name__); não use prints em bibliotecas.
- Exceptions: criar classes específicas em shared/exceptions.py quando adequado.
- Tests: pytest; arquivos test_*.py; usar fixtures para setup.
- Commits: prefixos (feat/, fix/, chore/, docs/, test/). Mensagens curtas + detalhamento no corpo.

Hooks e processos
- Executar `black .` e `isort .` antes de commitar; preferir pre-commit para automatizar.
- Rodar testes localmente antes do PR.

Exceções e conselhos práticos
- Em código de protótipo, priorizar clareza e iteração; converter para estilo estrito antes do merge em develop.
- Evitar complexidade desnecessária: prefira funções pequenas e testáveis.
