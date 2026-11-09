# Saga Engine

![Saga Engine](https://img.shields.io/badge/Saga%20Engine-v0.1.0-blue)
![Python](https://img.shields.io/badge/Python-3.10+-yellow)
![License](https://img.shields.io/badge/License-MIT-green)

A Saga Engine é uma engine de código aberto para a criação de jogos 2D do gênero point-and-click adventure, inspirada em clássicos como *Monkey Island* e *Full Throttle*.

O projeto é dividido em dois componentes principais:
- **Runtime:** O motor que executa o jogo final, construído com Python e a biblioteca Arcade.
- **Editor:** Uma IDE visual para montar o jogo, construída com Python e PySide6.

> 🚧 **Em desenvolvimento.** O projeto ainda não tem uma versão utilizável: o backend de IA e o editor web
> funcionam em partes e mudam com frequência. Veja `TODO.md` e `docs/CHANGELOG.md` para o andamento.

## Tecnologias Utilizadas

- **Linguagem Principal:** Python 3.10+
- **Runtime:**
  - **Gráficos 2D:** [Arcade](https://api.arcade.academy/en/latest/)
  - **Formatos de Dados:** JSON
- **Editor:**
  - **Interface Gráfica:** [PySide6](https://doc.qt.io/qtforpython/)
  - **Manipulação de Imagens:** [Pillow](https://python-pillow.org/)
- **Integração com IA:**
  - **API:** Gemini
- **Ferramentas:**
  - **Gerenciador de Pacotes:** Pip
  - **Controle de Versão:** Git

## Estrutura do Projeto

```
/
├── .github/          # Configurações do GitHub (Actions, etc.)
├── docs/             # Documentação do projeto
├── editor/           # Código-fonte do Editor Visual
├── projects/         # Projetos de jogos criados com a engine
│   └── demo/         # Projeto de demonstração
├── runtime/          # Código-fonte do Runtime da engine
├── shared/           # Módulos e esquemas compartilhados
├── tests/            # Testes automatizados
├── tools/            # Scripts e ferramentas auxiliares
├── .gitignore        # Arquivos ignorados pelo Git
├── LICENSE           # Licença do projeto
├── pyproject.toml    # Configurações do projeto Python
├── requirements.txt  # Dependências principais
├── README.md         # Este arquivo
└── TODO.md           # Lista de tarefas do desenvolvimento
```

## Instalação

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/csilvino/saga.git
    cd saga
    ```

2.  **Crie e ative um ambiente virtual:**
    ```bash
    # Windows
    python -m venv .venv
    .\.venv\Scripts\activate

    # macOS / Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
    ```

## Como Usar

O editor atual é uma aplicação web (React + Vite) que conversa com um backend FastAPI.

1. **Chaves (opcionais):** copie `.env.example` para `.env` e preencha. A chave do Gemini também pode
   ser informada nas configurações do editor (fica em `~/.saga_engine_settings.json`, fora do projeto).
2. **Backend** (porta 8070):
   ```bash
   python -m backend.main
   ```
3. **Frontend** (porta 5173):
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

`projects/Calixto Island` é um projeto de exemplo, com cenários e sprites gerados por IA.

## Licença

Este projeto está licenciado sob a Licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.
