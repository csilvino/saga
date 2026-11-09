# Saga Engine

![Status](https://img.shields.io/badge/status-em%20desenvolvimento-orange)
![Python](https://img.shields.io/badge/Python-3.10+-yellow)
![License](https://img.shields.io/badge/License-MIT-green)

Uma engine de adventures em que **a IA opera o editor**. Você descreve o jogo ("um mistério numa
mansão, 4 salas, a chave está escondida no relógio"), e o Diretor (Gemini com ferramentas) cria as
cenas, os objetos e a lógica. Depois ele **joga o próprio jogo** para conferir se o puzzle tem
solução e chega ao fim. Você continua no editor, pedindo mudanças ou editando à mão.

O caminho é este: primeiro **adventures em texto**, que já funcionam, e depois **point & click**, com
cenários e sprites gerados por IA (já há ferramentas para isso, ainda cruas).

> 🚧 **Em desenvolvimento.** A parte de texto funciona de ponta a ponta; o point & click e
> várias telas do editor ainda são experimentais. Veja [`TODO.md`](TODO.md).

## O que existe hoje

- **SES, a linguagem de script** ([`docs/SES.md`](docs/SES.md)): é pequena e tem parser de
  verdade, com erros que dizem linha e coluna. Cobre handlers (`on examine`, `on use with chave`...),
  flags, `if`/`else`, saídas que abrem durante o jogo e final. Ela tem testes.
- **Motor de adventure em texto** (`backend/ses/engine.py`):
  - entende comandos em português (`pegar a chave velha`, `usar chave na porta`, `n`, `inventário`);
  - guarda o estado completo do jogo (inventário, flags, objetos movidos, saídas abertas);
  - não guarda sessão no servidor: o cliente devolve o estado a cada comando.
- **O Diretor** (`backend/services/gemini_orchestrator.py` e `backend/ses/director_tools.py`):
  - ferramentas para criar e ligar cenas, criar objetos e salvar scripts, todos validados;
  - uma ferramenta `playtest`, para a IA jogar o jogo que construiu;
  - conversa com memória por projeto e espera a cota da Gemini quando ela estoura.
- **Editor web** (React + Vite):
  - canvas de cenas, propriedades do objeto (descrição, "pode ser pego", escondido, outros nomes);
  - editor de script que valida enquanto você digita;
  - chat com o Diretor e o player de texto.
- **Projeto de exemplo** [`projects/O Farol`](projects/O%20Farol/project.json): um adventure curto
  (6 cenas) escrito em SES. A solução está em [`tools/build_demo_farol.py`](tools/build_demo_farol.py).

Um trecho real, de quando o Diretor criou e testou um jogo sozinho:

```
> leste
== Canto da Cabana ==
Um canto escuro e empoeirado da cabana, onde tábuas soltas rangem sob seus pés.
> examinar tabuas
Você mexe nas tábuas e acha uma chave!
> pegar chave
...
> usar chave na porta
A chave abre a porta com um estalo!
> norte
Parabéns! Você escapou da cabana e alcançou a liberdade na floresta!
```

## Instalação

```bash
git clone https://github.com/csilvino/saga.git
cd saga
python -m venv .venv
# Windows: .\.venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

1. **Sua chave da Gemini.** A IA usa a chave de cada pessoa; não há login.
   - Crie a sua no [Google AI Studio](https://aistudio.google.com/apikey).
   - Cadastre no editor em **Configurações → API Keys** (botão "Configurar IA" no topo); "Salvar e
     testar" confere se ela funciona.
   - Ali mesmo você escolhe o modelo de texto e o de imagem.
   - A chave fica só no seu computador, em `~/.saga_engine_settings.json`, fora do projeto.
2. **Backend**, na porta 8070:
   ```bash
   python -m backend.main
   ```
3. **Frontend**, na porta 5173:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
4. Abra o projeto **O Farol** e clique em jogar. Ou crie um projeto vazio e peça ao Diretor:
   *"crie um adventure curto de fuga de uma cabana, com um objeto escondido e um final; teste a solução"*.

No plano gratuito da Gemini, o limite é de cerca de 15 chamadas por minuto, e cada passo do Diretor
gasta uma. Num jogo pequeno ele leva de 1 a 2 minutos, porque espera o limite sozinho.

## Testes

```bash
pip install pytest
python -m pytest tests/test_ses.py tests/test_director_tools.py tests/test_demo_farol.py
```

## Estrutura

```
backend/
  ses/                language.py (parser, validação, referência), engine.py (motor de jogo),
                      world.py, director_tools.py (ferramentas da IA)
  services/           orquestrador Gemini, geração de imagens
  api/routes/         FastAPI: /api/game, /api/ses, /api/orchestrator, cenas, objetos...
frontend/             editor React + Vite
projects/             projetos (O Farol = exemplo em SES; Calixto Island = experimento visual)
docs/                 SES.md (a linguagem), project_format.md; docs/legacy = visão antiga
runtime/, editor/     protótipos antigos (Arcade / PySide6), fora do fluxo atual
```

## Licença

MIT. Veja [LICENSE](LICENSE).
