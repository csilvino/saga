# Visão Geral do Projeto: Saga Engine

Este documento fornece um resumo do estado atual, da visão final e do potencial futuro da Saga Engine.

## 1. O Que a Saga Engine Pode Fazer Hoje

Até o momento, o **Runtime da Engine** já possui um núcleo funcional robusto, capaz de executar a lógica básica de um jogo de aventura. As principais funcionalidades implementadas são:

*   **Carregamento de Projetos:** A engine carrega e valida a estrutura de um jogo a partir de um arquivo `project.json`, utilizando um schema para garantir a integridade dos dados.
*   **Gerenciamento de Cenas:** É possível carregar e exibir cenas com imagens de fundo e personagens/objetos.
*   **Navegação Flexível:** A engine suporta dois modos de navegação distintos:
    *   **`pathfinding` (Estilo Monkey Island):** O personagem se move pela cena ao longo de um caminho calculado (A*) quando o jogador clica no chão.
    *   **`first_person` (Estilo Calixto Island):** A navegação é feita exclusivamente através de cliques em hotspots, sem movimentação de personagem visível.
*   **Sistema de Hotspots e Ações:** Cenas podem conter áreas interativas (hotspots) que, ao serem clicadas, disparam uma variedade de ações, incluindo:
    *   `go_to_scene`: Mudar de uma cena para outra.
    *   `add_item`: Adicionar um item ao inventário do jogador.
    *   `remove_item`: Remover um item do inventário.
    *   `combine_items`: Combinar dois itens para criar um terceiro.
    *   `start_dialog`: Iniciar uma conversa.
*   **Sistema de Inventário:** Um sistema de back-end completo para gerenciar os itens do jogador, incluindo a lógica de adição, remoção e combinação.
*   **Sistema de Diálogo:** A engine pode carregar e executar diálogos em formato de grafo, com suporte para falas de personagens e múltiplos nós de escolha, com uma UI básica para interação.
*   **SagaScript:** Uma linguagem de script simples para orquestrar eventos complexos, como movimentação de personagens, diálogos e manipulação de inventário.
*   **Sistema de Áudio:** Gerenciamento de música de fundo e efeitos sonoros, com a capacidade de reproduzi-los através de ações.
*   **Persistência:** Funcionalidade de salvar e carregar o estado do jogo (cena atual, posição do jogador, inventário) em arquivos JSON.

Em resumo, já temos o esqueleto de um jogo de aventura funcional, com a maioria dos sistemas de runtime implementados.

## 2. A Visão Completa (Versão 1.0)

Quando todas as tarefas do nosso `TODO.md` estiverem concluídas, a Saga Engine será uma suíte de desenvolvimento completa, composta por dois produtos principais:

### Runtime da Engine
O motor final será capaz de rodar jogos complexos com todas as funcionalidades esperadas de um adventure clássico moderno:
*   **Renderização Avançada:** Cenas com múltiplos planos (parallax), animações de personagens e efeitos visuais.
*   **Lógica de Jogo Completa:** Execução de scripts complexos através do **SagaScript** e da lógica visual do **Logic Weaver**.
*   **Sistemas de Jogo Ricos:** Gerenciamento de estado de jogo, sistema de áudio completo e persistência (salvar/carregar).
*   **Diálogos Dinâmicos:** Diálogos que podem ser influenciados pelo estado do jogo e, opcionalmente, enriquecidos por IA (Gemini).

### Editor Visual (IDE)
A ferramenta de criação será uma IDE completa e intuitiva para que desenvolvedores e escritores possam construir seus jogos sem precisar editar arquivos de texto manualmente:
*   **Editor de Cenas WYSIWYG:** Uma interface visual para montar cenas, posicionar personagens, objetos e definir a navegação.
*   **Editor de Hotspots Visual:** Ferramentas para desenhar e configurar hotspots diretamente sobre a imagem da cena.
*   **Editor de Diálogos em Grafo:** Uma poderosa ferramenta de nós para escrever e estruturar conversas complexas de forma visual e intuitiva.
*   **Logic Weaver:** Um sistema de scripting visual (baseado em nós) para criar puzzles e lógicas de jogo sem escrever código.
*   **Gerenciadores Integrados:** Editores para gerenciar o inventário, os personagens e os assets do projeto.
*   **Assistência de IA (Gemini):** Ferramentas integradas para ajudar na escrita de diálogos, na criação de descrições e na geração de ideias.
*   **Exportador de Projeto:** Uma função para empacotar o projeto do editor em um formato otimizado e pronto para ser executado pelo Runtime.

## 3. Potencial Futuro (Enriquecimento Pós-1.0)

Após a conclusão da versão 1.0, a Saga Engine pode ser expandida com funcionalidades que a tornariam ainda mais rica e competitiva:

*   **Sistema de Animação Avançado:** Implementar um editor de state machine para gerenciar animações complexas dos personagens (andar, falar, usar itens, animações ociosas).
*   **Suporte à Localização (Tradução):** Ferramentas no editor para facilitar a exportação e importação de textos, permitindo que os jogos sejam traduzidos para múltiplos idiomas.
*   **Editor de Cutscenes (Timeline):** Uma interface baseada em linha do tempo para criar cutscenes complexas, controlando movimentos de câmera, animações de personagens e eventos sincronizados.
*   **Sistema de Plugins e Módulos:** Permitir que a comunidade de desenvolvedores crie e compartilhe seus próprios módulos para estender as funcionalidades tanto do Editor quanto do Runtime.
*   **Exportação para Múltiplas Plataformas:** Utilizar ferramentas como PyInstaller ou Nuitka para empacotar os jogos em executáveis para Windows, macOS e Linux, e explorar a possibilidade de exportação para Web (via Pyodide/WebAssembly).
*   **Integração com Shaders:** Permitir o uso de shaders para efeitos de pós-processamento, como correção de cor, iluminação dinâmica, chuva, etc., dando mais atmosfera aos jogos.
*   **Ferramentas de Debug Visual:** Adicionar ao editor a capacidade de visualizar em tempo real as "walkable areas" do pathfinding, os polígonos dos hotspots e outras informações de debug sobrepostas à cena.

---

## 4. A Experiência Saga Engine: Do Conceito ao Jogo em Minutos (Visão Detalhada)

A Saga Engine é construída com uma filosofia central: **capacitar criadores de histórias a transformar suas visões em jogos de aventura 2D, com fluidez, rapidez e o poder da Inteligência Artificial, sem a complexidade das engines de propósito geral.**

Nosso objetivo é que, independentemente de você querer um mistério imersivo em primeira pessoa (estilo *Calixto Island*) ou uma comédia pirata em terceira pessoa com um personagem andando pela tela (estilo *Monkey Island*), a Saga Engine seja a ferramenta mais intuitiva e eficiente para isso.

### 🎬 ONBOARDING: O Início da Aventura

Ao abrir a Saga Engine pela primeira vez, o usuário é recebido por uma tela de boas-vindas inteligente:

```
┌─────────────────────────────────────────────────────────┐
│  🎮 BEM-VINDO À SAGA ENGINE                              │
│                                                          │
│  Vamos criar seu jogo de aventura juntos!               │
│                                                          │
│  [✨ Criar Novo Projeto com IA]  ← DESTAQUE             │
│  [📁 Abrir Projeto Existente]                           │
│  [📚 Explorar Templates]                                │
│  [🎓 Tutoriais Interativos]                             │
└─────────────────────────────────────────────────────────┘
```

A opção **"Criar Novo Projeto com IA"** é o caminho preferencial, pois demonstra imediatamente o poder da engine.

### O Assistente Criativo (IA)

Ao clicar em "Criar Novo Projeto com IA", um chat conversacional se abre:

```
┌─────────────────────────────────────────────────────────┐
│ 🤖 Assistente Saga                                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ Olá! Sou seu assistente criativo. Me conta:            │
│                                                          │
│ • Qual é a sua ideia de jogo? (Ex: "Um detetive em uma  │
│   ilha tropical investiga um mistério antigo.")         │
│ • Qual estilo de jogo você prefere?                     │
│   [🏝️ Calixto Island (1ª Pessoa, Hotspots)]             │
│   [🏴‍☠️ Monkey Island (3ª Pessoa, Personagem Andando)]   │
│ • Qual o tom da narrativa? (Ex: "Sério", "Cômico", "Noir")│
│                                                          │
│ Ou escolha um template para começar rápido:            │
│ [Template: Mistério em Ilha] [Template: Aventura Pirata]│
│                                                          │
│ [___________________________________________] Enviar    │
└─────────────────────────────────────────────────────────┘
```

**Exemplo: Usuário descreve "Um detetive em uma ilha tropical investiga um mistério antigo" e escolhe "Calixto Island".**

A IA processa a descrição e o estilo:

```
🤖 Analisando sua ideia...
✓ Modo de Navegação: First-person (hotspot-driven)
✓ Gerando estrutura de 3 cenas iniciais (Praia, Cabana, Templo Antigo)
✓ Criando personagem principal "Detetive Alex" e 2 NPCs
✓ Sugerindo 5 itens de inventário iniciais
✓ Esboçando um diálogo introdutório
✓ Selecionando assets visuais e sonoros compatíveis
```

Em poucos segundos, o projeto é gerado e o usuário é levado à interface principal.

## 🎨 O Coração do Editor: Interface Principal

A interface principal é dividida em áreas claras:

*   **Painel Lateral Esquerdo (Navegação do Projeto):** Árvore de cenas, lista de personagens, diálogos, inventário, lógica visual, assets.
*   **Área Central (Editor Ativo):** Onde a mágica acontece – Editor de Cenas, Editor de Diálogos, Logic Weaver.
*   **Painel Lateral Direito (Propriedades/Contexto):** Exibe as propriedades do item selecionado, sugestões da IA.
*   **Barra Superior (Ferramentas Globais):** Salvar, Abrir, Testar Jogo, Exportar.
*   **Barra Inferior (Status/Dicas da IA):** Mensagens de status, dicas contextuais da IA.

```
┌────────────────────────────────────────────────────────────────────┐
│ Saga Engine - Mistério na Ilha Perdida            [💾🎮▶️]         │
├────────────┬───────────────────────────────────────┬──────────────┤
│            │                                       │              │
│  📁 Projeto│         🖼️ EDITOR DE CENA             │ ⚙️ PROPRIEDADES │
│  ├─ Cenas  │                                       │              │
│  │  ├─ Praia│   ┌──────────────────────────────────┐│  Hotspot: Bote │
│  │  ├─ Cabana│   │                                  ││  ID: bote_praia│
│  │  └─ Templo│   │    [Imagem: Praia tropical]      ││  Nome: Bote    │
│  ├─ Person.│   │                                  ││  Ação: [Examinar ▼]│
│  ├─ Diálogo│   │    [📍 Hotspot: Bote]             ││  Params: {"text": "Um bote velho..."}│
│  ├─ Invent.│   │    [📍 Hotspot: Cabana]           ││              │
│  ├─ Lógica │   │                                  ││  [+ Nova Ação] │
│  ├─ Assets │   └──────────────────────────────────┘│              │
│            │                                       │              │
│  🌐 Cenas: │   🎯 FERRAMENTAS DE CENA:             │ 💡 DICA IA:  │
│  • Praia   │   [➕ Objeto] [➕ Hotspot] [✏️ Caminho] │ "Que tal um  │
│  • Cabana  │                                       │  hotspot no  │
│  • Templo  │                                       │  coqueiro?"  │
│ [+ Nova]   │                                       │              │
└────────────┴───────────────────────────────────────┴──────────────┘
```

## 🎨 Módulo: Editor de Cenas (Visual e Inteligente)

### Criação de Cenas:
*   **"Gerar com IA":** Descreva a cena ("Interior de uma cabana abandonada na praia com uma mesa e uma porta para o porão"). A IA gera o background, posiciona objetos básicos e sugere hotspots.
*   **"Usar Imagem Existente":** Faça upload de seu próprio background. A IA pode analisar a imagem e sugerir hotspots e objetos.
*   **"Biblioteca de Assets":** Acesse uma vasta biblioteca de backgrounds e sprites (gratuitos e premium) da comunidade.

### Edição Visual:
*   **Hotspots:** Ferramentas de desenho intuitivas para criar polígonos, retângulos ou círculos. A IA pode sugerir áreas interativas.
*   **Objetos:** Arraste e solte sprites de personagens e props. A IA pode sugerir posições e tamanhos.
*   **Navegação (Monkey Island Style):** Ferramentas para desenhar áreas caminháveis (polígonos verdes) e obstáculos (polígonos vermelhos) para o pathfinding. A IA pode gerar uma malha de navegação inicial.
*   **Navegação (Calixto Island Style):** Foco total nos hotspots, com a IA sugerindo transições lógicas entre cenas.

## 💬 Módulo: Editor de Diálogos (Grafo e Co-criação com IA)

*   **Visualização em Grafo:** Diálogos são representados como nós e conexões, facilitando a visualização do fluxo.
*   **Geração com IA:** Descreva o diálogo ("Conversa cômica com um pirata bêbado sobre um tesouro escondido"). A IA gera o grafo completo, com falas, escolhas e ramificações.
*   **Sugestões Contextuais:** Enquanto você escreve, a IA sugere variações de falas, respostas para escolhas e até mesmo novos nós de diálogo para explorar.
*   **Análise de Tom:** A IA pode analisar o tom do diálogo e sugerir ajustes para torná-lo mais "cômico", "sombrio", etc.
*   **Testes Rápidos:** Simule o diálogo diretamente no editor para verificar o fluxo.

## 🎒 Módulo: Gerenciador de Inventário (Assistência na Criação de Itens)

*   **Criação de Itens com IA:** Descreva o item ("Uma chave antiga e enferrujada"). A IA gera nome, descrição, e pode até sugerir uma imagem (se integrada a um gerador de imagens).
*   **Sugestões de Combinação:** A IA pode analisar os itens existentes e sugerir combinações lógicas ("Galho + Pano = Tocha").
*   **Biblioteca de Itens:** Acesse uma biblioteca de itens pré-fabricados, com descrições e imagens.

## 🔧 Módulo: Logic Weaver (Lógica Visual com IA)

*   **Editor de Nós:** Crie puzzles e eventos complexos arrastando e conectando nós de lógica (condições, ações, eventos).
*   **Geração de Lógica com IA:** Descreva o puzzle ("O jogador precisa encontrar três pedaços de um mapa para combiná-los e revelar a localização de uma chave que abre a porta do porão"). A IA gera o grafo de lógica visual, incluindo flags de jogo, condições e ações.
*   **Tradução para SagaScript:** O Logic Weaver pode gerar automaticamente o SagaScript correspondente à lógica visual, permitindo que usuários avançados revisem ou otimizem o código.

## 🎵 Módulo: Gerenciador de Áudio (Biblioteca e Geração)

*   **Biblioteca Integrada:** Acesse uma vasta biblioteca de músicas e efeitos sonoros (gratuitos e premium).
*   **Sugestões de IA:** A IA pode analisar a cena ou o diálogo e sugerir trilhas sonoras ambientes ou efeitos sonoros apropriados.
*   **Geração de Áudio (Futuro):** Integração com APIs de geração de áudio para criar sons personalizados com base em descrições de texto.

## 🚀 Testando o Jogo: Iteração Rápida

Um botão **"Testar Jogo"** sempre visível no editor lança o Runtime em uma nova janela, permitindo que o criador teste suas alterações instantaneamente.

*   **Modo Debug:** O Runtime em modo de teste pode exibir informações de debug (posição do personagem, hotspots ativos, variáveis de jogo) e um console para monitorar eventos.

## 📦 Biblioteca de Assets e Comunidade

A Saga Engine terá um forte foco na comunidade:

*   **Marketplace Integrado:** Uma loja dentro do editor para baixar e vender assets (visuais, sonoros, templates de diálogo, scripts, Logic Weaver graphs).
*   **IA para Recomendações:** A IA pode analisar o estilo e o conteúdo do seu projeto e recomendar assets compatíveis do marketplace.
*   **Ferramentas de Upload:** Facilite o compartilhamento de assets criados pela comunidade.

---

**Conclusão:**

A Saga Engine não é apenas uma ferramenta, é um **parceiro criativo**. Ao automatizar tarefas repetitivas e oferecer sugestões inteligentes, ela libera o criador para focar no que realmente importa: a história, os personagens e a experiência do jogador. A combinação de uma interface intuitiva, IA poderosa e um ecossistema vibrante fará da Saga Engine a escolha ideal para dar vida a jogos de aventura 2D.
