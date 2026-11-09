# Recuperação de Contexto do Projeto SAGA ENGINE

**Data da Última Atualização:** (Data Atual)
**Status:** Arquitetura "IA-First" definida. Backend robusto com ferramentas de IA. Frontend em refatoração, com instabilidade.

## 🚀 A Grande Virada: A Visão "IA-First" e o SAGA ENGINE SCRIPT (SES)

O projeto passou por uma mudança fundamental de filosofia, proposta e liderada pelo usuário. Abandonamos o modelo de uma UI com botões e campos manuais em favor de uma interface **IA-First**, onde a principal forma de interação é através de comandos em linguagem natural em um painel de chat.

### 1. Manifesto: SAGA ENGINE SCRIPT (SES)
- **Documento Criado:** `SAGA_ENGINE_SCRIPT_SES.md` foi criado na raiz do projeto. Ele serve como a "Bíblia" e a visão de longo prazo para a nossa linguagem de script.
- **Filosofia:** O SES foca na **intenção narrativa** em vez da implementação técnica. O objetivo é que tanto humanos quanto a IA possam escrever código de forma intuitiva (ex: `on click on Porta, if player.has("chave"), goToScene("sala2")`).
- **Arquitetura:** O manifesto detalha uma linguagem completa com tipos, sistema de eventos, declarações de alto nível (cenas, objetos, personagens) e um pipeline de compilação para múltiplos alvos (Web, Unity, Godot).

### 2. Arquitetura do Agente de IA (Backend)
Para suportar a visão IA-First, o backend foi reestruturado para funcionar como um **Agente de IA Orquestrador**.
- **Orquestrador (`gemini_orchestrator.py`):** O cérebro do sistema. Usa a técnica de **Function Calling** da API Gemini para interpretar os prompts do usuário e decidir quais "ferramentas" executar.
- **Caixa de Ferramentas (`tools.py`):** Um conjunto robusto de rotas de API foi criado para servir como as "ferramentas" que o orquestrador pode chamar. Inclui funcionalidades para:
  - Criar Sprite Sheets
  - Recortar, redimensionar e aplicar filtros em imagens
  - Listar assets e analisar imagens
  - Atualizar o `project.json`
- **Rotas de Suporte:**
  - `genai_edit.py`: Implementa a remoção de objetos de imagens (inpainting) usando a API do Gemini.
  - `orchestrator.py`: Expõe o orquestrador através de um endpoint `/api/orchestrator/command`.

### 3. Refatoração da Interface (Frontend)
A interface do usuário foi completamente redesenhada para se alinhar à nova visão.
- **Estrutura de 3 Painéis:** O `App.tsx` foi simplificado para orquestrar três componentes principais:
  1. `Sidebar`: Painel esquerdo, agora contextual.
  2. `SceneCanvas`: Painel central, focado em preview.
  3. `AIPanel`: Painel direito, o centro de comando da IA.
- **`Sidebar` Contextual (A Visão Correta):**
  - **Modo Explorer:** Por padrão, mostra a hierarquia do projeto (Cenas > Objetos).
  - **Modo Editor (SES):** Ao selecionar um objeto, o `Sidebar` se transforma em um `PropertiesEditor`, mostrando o código SES daquele objeto para edição.
- **`AIPanel` (Centro de Comando):**
  - **Chat:** A aba principal, conectada ao orquestrador do backend.
  - **Diretor (Workflows):** Uma aba secundária que funciona como uma "biblioteca de prompts", ajudando o usuário a descobrir as capacidades da IA.

## ⚠️ ESTADO ATUAL E PRÓXIMO PASSO IMEDIATO ⚠️

**O Desafio:** Durante a implementação da nova interface, ocorreram várias regressões e erros graves, incluindo a quebra total da aplicação (tela de "Carregando..."). O usuário reverteu o `App.tsx` para uma versão estável, mas a implementação do `Sidebar` contextual ainda não está funcional.

**O Erro:** Minhas tentativas de implementar o `Sidebar` contextual modificando o `App.tsx` foram desastrosas. A abordagem correta, definida pelo usuário, é manter o `App.tsx` estável e colocar toda a lógica de alternância de visão (Explorer vs. Editor) **dentro do componente `Sidebar`**.

**Próxima Ação Imediata e Única:**
1.  **Corrigir o `Sidebar.tsx`:**
    - O componente receberá a prop `selectedObjectId` do `App.tsx`.
    - Ele terá uma lógica interna:
      - **SE** `selectedObjectId` tiver um valor, ele encontrará o objeto correspondente no `project` e renderizará o `PropertiesEditor` para esse objeto.
      - **SE** `selectedObjectId` for `null`, ele renderizará a visão normal do `Explorer`.
    - O botão "Fechar" no editor chamará a função `onSelectObject(null)`, que já é passada pelo `App.tsx`, fazendo o `Sidebar` voltar ao modo `Explorer`.
2.  **NÃO TOCAR NO `App.tsx`:** Nenhuma alteração deve ser feita no `App.tsx` até que o `Sidebar` esteja funcionando perfeitamente com a lógica contextual interna.

Após esta correção, o próximo passo será implementar o **upload de assets de dentro do `PropertiesEditor`**.
