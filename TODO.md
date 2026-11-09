# Saga Engine: Plano de Recuperação e Desenvolvimento

Este documento foca exclusivamente nas funcionalidades básicas de edição de cena, seguindo a ordem lógica de dependência.

## 1. Gerenciamento de Backgrounds (PRIORIDADE MÁXIMA 🔴)
O objetivo é permitir que o usuário altere ou remova a imagem de fundo da cena (o "quadrado cinza").

- [ ] **Trocar Background**
    - [ ] No `AssetBrowser`, ao clicar com botão direito em uma imagem, mostrar opção "Definir como Fundo".
    - [ ] Ao clicar, atualizar o `project.scenes[id].background` e salvar.
    - [ ] A imagem na cena deve atualizar imediatamente.
- [ ] **Remover Background**
    - [ ] Adicionar um botão ou opção "Remover Fundo" na barra de ferramentas da cena.
    - [ ] Isso deve definir o background como `null` ou uma cor sólida padrão.

## 2. Inserção de Objetos (Sprites) 🟠
O objetivo é permitir popular a cena com personagens e itens.

- [ ] **Drag-and-Drop Estável**
    - [ ] Reimplementar `dnd-kit` focando apenas em arrastar da Galeria -> Cena.
    - [ ] Garantir que o objeto seja criado na posição exata do mouse.
- [ ] **Manipulação de Objetos**
    - [ ] Garantir que a seleção e deleção (que já funcionam) continuem funcionando após adicionar novos itens.

## 3. Gerenciamento de Cenas (CRUD) 🟡
O objetivo é permitir criar novas salas/cenas e apagar as existentes.

- [ ] **Criar Cena**
    - [ ] Adicionar botão "+" na seção de Cenas da Sidebar.
    - [ ] Backend: Criar endpoint `POST /api/scenes/create`.
    - [ ] Frontend: Solicitar nome da nova cena e atualizar a lista.
- [ ] **Deletar Cena**
    - [ ] Adicionar botão de lixeira ao passar o mouse sobre uma cena na Sidebar.
    - [ ] Backend: Criar endpoint `DELETE /api/scenes/{id}`.
    - [ ] Frontend: Remover da lista e limpar o Painel Central se a cena deletada estiver ativa.

## 4. Organização de Assets 🟢
Melhorar a visualização dos arquivos.

- [ ] **Refatoração do AssetBrowser**
    - [ ] Separar visualmente Backgrounds, Sprites e Áudio.
    - [ ] Implementar preview de áudio (tocar som).
