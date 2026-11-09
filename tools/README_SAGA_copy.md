# README_SAGA

Arquivo mestre de controle de tarefas para o projeto Saga Engine. Este arquivo centraliza a lista de tarefas hierárquica, sequencial e atualizável. Atualize os itens marcando [x] quando concluídos e use os campos de status (TODO / IN PROGRESS / BLOCKED / DONE) nas notas de cada seção.

Última atualização: 2025-12-17

---

## Visão
Saga Engine — engine para jogos 2D point-and-click. Estrutura: /editor, /runtime, /shared, /projects.

---

## Lista Mestre de Tarefas (Checklist)

1. Fundação do Projeto
[x] 1.1 Criar repositório principal e estrutura de pastas  - STATUS: DONE
    [x] 1.1.1 Inicializar Git no caminho c:\CURSO PYTHON\SAGA_ENGINE  - STATUS: DONE
    [x] 1.1.2 Criar árvore de pastas: /editor, /runtime, /shared, /projects, /docs, /tools, /tests  - STATUS: DONE
    [x] 1.1.3 Adicionar .gitignore, README.md inicial e LICENSE  - STATUS: DONE
    Critério: repositório com estrutura criada e README com visão geral.

[ ] 1.2 Definir padrões e convenções
    [ ] 1.2.1 Guia de estilo Python (PEP8 + convenções do projeto)
    [ ] 1.2.2 Convenção de versionamento semântica (SemVer)
    [ ] 1.2.3 Formato de arquivos de projeto (JSON schema inicial em /shared)
    Critério: documentos de convenção no /docs.

[ ] 1.3 Configuração de ambiente de desenvolvimento
    [ ] 1.3.1 Definir e documentar versão mínima do Python (>=3.10)
    [ ] 1.3.2 Arquivos requirements-dev.txt e requirements.txt
    [ ] 1.3.3 Instruções para setup em Windows (virtualenv, VS Code settings)
    Critério: dev pode rodar ambiente seguindo docs.

[ ] 1.4 CI/CD e qualidade
    [ ] 1.4.1 Pipeline básico (GitHub Actions) para lint, tests e build de pacotes
    [ ] 1.4.2 Configurar linters (flake8/ruff) e formatter (black/isort)
    Critério: PR aceita somente se pipeline verde.

---

2. Runtime da Engine
[ ] 2.1 Arquitetura do runtime
    [ ] 2.1.1 Documento de arquitetura (módulos, responsabilidades, comunicação)
    [ ] 2.1.2 Definir API pública entre /runtime e /shared (formats JSON)
    Critério: documento aprovado e exemplos de uso.

[ ] 2.2 Loader de projeto e assets
    [ ] 2.2.1 Implementar carregador de projeto JSON
    [ ] 2.2.2 Gerenciar paths de assets (sprites, tiles, áudio)
    Critério: projeto de exemplo carrega sem erro.

[ ] 2.3 Sistema de renderização com Arcade
    [ ] 2.3.1 Janela principal, loop e camadas de render
    [ ] 2.3.2 Render de sprites, backgrounds e camadas parallax
    Critério: cena de demo renderiza corretamente.

[ ] 2.4 Hotspots e detecção de interação
    [ ] 2.4.1 Estrutura de hotspots (formas, tags, estados)
    [ ] 2.4.2 Detecção de mouse (over, click, drag)
    Critério: hotspots detectados e eventos acionam handlers.

[ ] 2.5 Inventário e objetos
    [ ] 2.5.1 Modelo de itens, stack e combinações
    [ ] 2.5.2 UI de inventário básica
    Critério: adicionar/remover item e combinar implementado.

[ ] 2.6 Sistema de diálogos
    [ ] 2.6.1 Execução de árvores de diálogo a partir de JSON
    [ ] 2.6.2 Variáveis de diálogo, condições e ramos
    Critério: diálogo ramificado funciona.

[ ] 2.7 Logic Weaver (lógica visual runtime)
    [ ] 2.7.1 Executor de nodes (interpretação de JSON do editor)
    [ ] 2.7.2 Nós essenciais: condicional, ação, temporizador, mover, animar, alterar inventário
    Critério: lógica visual simples executa efeitos.

[ ] 2.8 Sistema de scripts SagaScript
    [ ] 2.8.1 Esboço da sintaxe mínima e parser/executor seguro
    [ ] 2.8.2 Integração com runtime para modificar estado do jogo
    Critério: scripts de exemplo modificam variáveis e ações.

[ ] 2.9 Áudio
    [ ] 2.9.1 Integração com áudio do Arcade (música, SFX, canais)
    [ ] 2.9.2 Sistema de mixagem e persistência de volume
    Critério: SFX e música reproduzem e controlam volume.

[ ] 2.10 Save / Load
    [ ] 2.10.1 Serializar estado do jogo em JSON (save slots)
    [ ] 2.10.2 Restaurar cena, inventário, variáveis de jogo
    Critério: salvar/carregar restaura estado corretamente.

[ ] 2.11 Ferramentas de debugging no runtime
    [ ] 2.11.1 Console de variáveis e logs em tela
    [ ] 2.11.2 Modo de edição rápido (hot-reload de assets)
    Critério: debug utilities disponíveis em builds dev.

---

3. Editor Visual (IDE)
[ ] 3.1 Arquitetura do editor
    [ ] 3.1.1 Documento de arquitetura do Editor
    [ ] 3.1.2 Definir comunicação editor <-> runtime (export JSON)
    Critério: arquitetura aprovada e fluxo de export definido.

[ ] 3.2 Setup PySide6 e projeto base
    [ ] 3.2.1 Janela principal, dock widgets e layout
    [ ] 3.2.2 Sistema de perfis de usuário e preferências
    Critério: editor inicia com UI base.

[ ] 3.3 Editor de cenas (viewport)
    [ ] 3.3.1 Canvas com QGraphicsView + manipulação (pan/zoom)
    [ ] 3.3.2 Camadas, grid, snapping e preview (export)
    Critério: cena pode ser montada visualmente e salva em JSON.

[ ] 3.4 Editor de hotspots
    [ ] 3.4.1 Ferramentas de criação/edição de polígonos e retângulos
    [ ] 3.4.2 Atributos: nome, ação, tags, condições
    Critério: hotspots exportáveis e testáveis no runtime.

[ ] 3.5 Editor de diálogos em grafo
    [ ] 3.5.1 Node editor para diálogos com nós de falas, escolhas e condições
    [ ] 3.5.2 Import/Export para JSON do runtime
    Critério: diálogo criado no editor roda no runtime.

[ ] 3.6 Logic Weaver (Editor de lógica visual)
    [ ] 3.6.1 Node editor para lógica (QGraphicsScene based)
    [ ] 3.6.2 Biblioteca de nós e sistema de extensão
    Critério: grafo exportado interpretável pelo runtime.

[ ] 3.7 Editor de inventário e personagens
    [ ] 3.7.1 CRUD de itens, sprites, descrições e combinações
    [ ] 3.7.2 Definição de personagens e falas padrão
    Critério: dados do editor refletidos no runtime.

[ ] 3.8 Exportador de projeto
    [ ] 3.8.1 Validador de projeto (checks de consistência)
    [ ] 3.8.2 Export para pasta + jsons compatíveis com runtime
    Critério: runtime carrega export sem erros.

[ ] 3.9 Integração básica com IA (no editor)
    [ ] 3.9.1 Painel para request ao Gemini (prompt templates)
    [ ] 3.9.2 Histórico de respostas e auditoria
    Critério: escritor utiliza Gemini para gerar variantes de diálogo.

---

4. Sistemas de Adventure (mecânicas)
[ ] 4.1 Sistema de verbos / interações (Look, Use, Talk, Give)
    [ ] 4.1.1 Definir API de verbos e handlers
    [ ] 4.1.2 UI de seleção de verbo no runtime
    Critério: ações executáveis via verbos no runtime.

[ ] 4.2 Inventário avançado
    [ ] 4.2.1 Pistas, itens combináveis, estados condicionalmente ocultos
    [ ] 4.2.2 Sistema de descrição dinâmica (dependendo do contexto)
    Critério: inventário com regras avançadas funciona.

[ ] 4.3 Sistema de pistas e objetivos
    [ ] 4.3.1 Tracker de objetivos e progressão
    [ ] 4.3.2 Sistema de dicas (triggerável)
    Critério: objetivos atualizam e dicas são acionadas.

[ ] 4.4 Pathfinding A* para NPCs e arrastar personagens
    [ ] 4.4.1 Implementar A* grid/waypoint no /shared
    [ ] 4.4.2 Integração com movimento e colisões
    Critério: NPCs se movem usando pathfinding.

[ ] 4.5 Sistema de animação e estados
    [ ] 4.5.1 Estados de personagem e blend básico de animações
    Critério: animações trocam conforme ações.

---

5. Integração com IA (Gemini)
[ ] 5.1 Design de integração
    [ ] 5.1.1 Definir casos de uso (diálogo, naming, brainstorming)
    [ ] 5.1.2 Especificar limites (tokens, custos, privacidade)
    Critério: política de uso definida.

[ ] 5.2 Implementação do cliente Gemini
    [ ] 5.2.1 Camada de comunicação segura (requests/httpx)
    [ ] 5.2.2 Templates de prompt e armazenamento de respostas
    Critério: chamadas funcionais em ambiente de teste.

[ ] 5.3 Ferramentas no Editor
    [ ] 5.3.1 Assistente de diálogo (sugestões, variações)
    [ ] 5.3.2 Geração de descrições e nomes de itens
    Critério: editor recebe e insere respostas com revisão humana.

[ ] 5.4 Auditoria e controle
    [ ] 5.4.1 Histórico de prompts e respostas
    [ ] 5.4.2 Modo offline e políticas de fallback
    Critério: histórico acessível e fallback funciona sem IA.

---

6. Ferramentas e Fluxo de Trabalho
[ ] 6.1 Ferramentas de build/export
    [ ] 6.1.1 Script de export automatizado (Windows)
    [ ] 6.1.2 Empacotamento mínimo para distribuição do runtime
    Critério: export gera pasta pronta para execução.

[ ] 6.2 Integração com Git e branch strategy
    [ ] 6.2.1 Definir gitflow simplificado (main, develop, feature/*)
    Critério: política publicada e aplicada.

[ ] 6.3 Documentação e tutoriais
    [ ] 6.3.1 Docs de uso básico do editor e runtime
    [ ] 6.3.2 Tutorial “Hello World” criar cena simples
    Critério: tutorial completo e testado.

[ ] 6.4 Templates de projeto e assets
    [ ] 6.4.1 Projeto de exemplo minimal e completo (demo)
    Critério: demos executáveis no runtime.

---

7. Testes e Protótipos
[ ] 7.1 Testes unitários e de integração
    [ ] 7.1.1 Estruturar /tests com pytest
    [ ] 7.1.2 Cobertura inicial para /shared e /runtime core
    Critério: pipelines rodando testes automatizados.

[ ] 7.2 Protótipos rápidos
    [ ] 7.2.1 Prototype 1: cena estática com hotspots e diálogo
    [ ] 7.2.2 Prototype 2: inventário + combinação + puzzle simples
    Critério: protótipos validam arquitetura.

[ ] 7.3 Testes de usabilidade do editor
    [ ] 7.3.1 Sessões de teste com 2-3 usuários (interno)
    Critério: feedback coletado e backlog de melhorias.

---

8. Roadmap de versões
[ ] 8.1 Versão 0.1 - MVP Runtime + Editor básico
    [ ] 8.1.1 Runtime: load/render/hotspots/diálogos/inventário básico
    [ ] 8.1.2 Editor: scene editor, hotspots, export simples
    Critério: jogo demo funcional com 1 cena.

[ ] 8.2 Versão 0.5 - Feature complete básica
    [ ] 8.2.1 Logic Weaver, SagaScript, diálogo avançado, save/load
    [ ] 8.2.2 Editor completo para esses recursos
    Critério: editor+runtime compatíveis para pequena aventura.

[ ] 8.3 Versão 1.0 - Estável e documentado
    [ ] 8.3.1 Integração IA, melhorias UX, polimento e testes
    Critério: lançamento formal com docs e exemplos.

[ ] 8.4 Pós-1.0 - Extensões
    [ ] 8.4.1 Plugins, plataformas adicionais, performance tuning

---

9. Governança, prioridades e atualização da lista (processo)
[ ] 9.1 Política de priorização
    [ ] 9.1.1 Priorizar fundamentos e integração editor/runtime
    [ ] 9.1.2 Iterações curtas (sprints de 2 semanas)
    Critério: backlog priorizado ao fim de cada sprint.

[ ] 9.2 Como atualizar esta lista
    [ ] 9.2.1 Uso: marcar [x] para concluído, adicionar subtarefas com referência
    [ ] 9.2.2 Modelo de status: TODO / IN PROGRESS / BLOCKED / DONE
    Critério: changelog de tarefas disponível em /docs/tasks.md

[ ] 9.3 Relatórios de progresso
    [ ] 9.3.1 Template de status semanal (o que foi feito, impedimentos, próximo)
    Critério: entregas semanais registradas.

---

Observações operacionais (regras do projeto)
- Nunca pular etapas sem autorização explícita.
- Sempre atualizar o status das tarefas quando pedir para começar algo novo.
- Quando quiser que eu continue, informe explicitamente qual seção (ex.: "Começar 2.2 Loader de projeto") — eu entã
