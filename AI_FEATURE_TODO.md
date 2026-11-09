# Projeto: Criação de Cena Assistida por IA

**Objetivo:** Permitir que um usuário descreva uma cena em texto, receba um background gerado por IA e, em seguida, extraia objetos interativos e suas variações (estados/animações) diretamente da imagem.

---

### SPRINT 1: Geração do Background da Cena (A Fundação)
**(Meta: O usuário descreve uma cena e a vê aparecer no editor com um background gerado por IA.)**

- [ ] **Tarefa 1.1: Interface de Geração (Frontend)**
  - [ ] Na aba "IA" do painel direito, criar uma nova seção "Criador de Cenas".
  - [ ] Adicionar um campo de texto (`<textarea>`) para o usuário descrever a cena.
  - [ ] Adicionar um botão "Gerar Cena".

- [ ] **Tarefa 1.2: Novo Endpoint de Geração (Backend)**
  - [ ] Criar endpoint: `POST /api/ai/generate-scene`.
  - [ ] Receber o prompt de texto.
  - [ ] Construir um "mega-prompt" para a API de imagem do Gemini.
  - [ ] Chamar a API do Gemini para gerar a imagem.
  - [ ] Salvar a imagem em `/assets/backgrounds/`.
  - [ ] Retornar o caminho do novo arquivo.

- [ ] **Tarefa 1.3: Integração e Criação da Cena (Frontend)**
  - [ ] Ao receber a resposta do backend:
    1. Criar uma nova estrutura de cena no JSON do projeto.
    2. Atribuir a imagem gerada como `background`.
    3. Adicionar a nova cena à lista no `Sidebar`.
    4. Mudar a `activeView` para a cena recém-criada.

---

### SPRINT 2: Extração de Objetos da Cena (A Mágica)
**(Meta: Transformar partes da imagem em objetos independentes.)**

- [ ] **Tarefa 2.1: Ferramenta de Extração (Frontend)**
  - [ ] Adicionar botão "Extrair Objeto" na toolbar do `CentralPanel`.
  - [ ] Ativar modo de desenho de retângulo (bounding box).

- [ ] **Tarefa 2.2: Modal de Nomenclatura (Frontend)**
  - [ ] Ao soltar o mouse, um modal pede o nome do objeto.

- [ ] **Tarefa 2.3: Novo Endpoint de Extração (Backend)**
  - [ ] Criar endpoint: `POST /api/ai/extract-object`.
  - [ ] Receber: imagem de fundo, `bounding box`, nome do objeto.
  - [ ] **Chamada 1 (Inpainting):** Preencher a área do objeto no background.
  - [ ] **Chamada 2 (Outpainting):** Criar o sprite do objeto com fundo transparente.
  - [ ] Salvar as duas novas imagens.
  - [ ] Criar o `object.json` básico.

- [ ] **Tarefa 2.4: Integração do Objeto (Frontend)**
  - [ ] Atualizar o `background` da cena com a imagem "limpa".
  - [ ] Adicionar o novo objeto à lista de `objects` da cena.
  - [ ] Renderizar o novo `DraggableObject` sobre o background.

---

### SPRINT 3: Geração de Estados e Animações (O Diferencial)
**(Meta: Dar vida aos objetos extraídos.)**

- [ ] **Tarefa 3.1: Interface de Variação (Frontend)**
  - [ ] No `HotspotEditor` (ou um novo painel), ao selecionar um objeto, mostrar a opção "Gerar Variação/Animação".
  - [ ] Permitir escolher entre "Novo Estado" ou "Animação".
  - [ ] Campo de texto para descrever a variação (ex: "baú aberto").

- [ ] **Tarefa 3.2: Endpoint de Variação (Backend)**
  - [ ] Criar endpoint: `POST /api/ai/generate-object-variation`.
  - [ ] Receber: sprite original e o prompt de variação.
  - [ ] Chamar a API do Gemini para gerar o novo sprite (ou frames de animação).
  - [ ] Salvar o novo asset.

- [ ] **Tarefa 3.3: Integração de Estados (Frontend)**
  - [ ] Receber o novo sprite.
  - [ ] Atualizar o JSON do objeto para incluir o novo estado em `states`.
  - [ ] Permitir ao usuário testar a troca de estados no editor.
