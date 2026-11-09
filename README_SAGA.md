Saga Engine: Roadmap de Desenvolvimento
Status do Projeto: 🏆 MVP Concluído
Última Atualização: 20/12/2024

📋 Índice de Prioridades
🔴 CRÍTICO - Bloqueador, impede uso básico
🟠 ALTA - Funcionalidade core, necessária para MVP
🟡 MÉDIA - Melhoria importante, não urgente
🟢 BAIXA - Refinamento, pode esperar
⚪ FUTURO - Ideias para versões posteriores

---
### 🏆 MVP - Editor Funcional (Fases 1-5) - ✅ CONCLUÍDO
---

🔴 FASE 1: Funcionalidades Críticas (Sprint 1 - 3 dias) - ✅ CONCLUÍDA
1.1 Gerenciamento de Backgrounds ⏱️ 4h - ✅ CONCLUÍDO
- [x] Trocar e salvar background da cena via menu de contexto.

1.2 Inserção de Objetos (Drag & Drop) ⏱️ 6h - ✅ CONCLUÍDO
- [x] Arrastar assets da galeria para a cena.
- [x] Objeto é criado na posição exata do mouse.

1.3 Manipulação de Objetos ⏱️ 4h - ✅ CONCLUÍDO
- [x] Selecionar e deletar objetos.
- [x] Arrastar objetos existentes para movê-los dentro da cena.
- [x] Posição é salva automaticamente ao soltar.

---

🟠 FASE 2: CRUD de Cenas (Sprint 2 - 2 dias) - ✅ CONCLUÍDA
2.1 Criar Nova Cena ⏱️ 3h - ✅ CONCLUÍDO
- [x] Botão "+" na seção "Cenas" do Explorer.
- [x] Modal para inserir nome da cena.
- [x] Adicionar cena na lista e selecionar automaticamente.

2.2 Deletar Cena ⏱️ 2h - ✅ CONCLUÍDO
- [x] Ícone de lixeira ao hover na lista de cenas.
- [x] Confirmação antes de deletar.
- [x] Se cena ativa for deletada, volta para cena inicial.
- [x] Prevenir delete da cena inicial.

2.3 Editar Cena ⏱️ 2h - ✅ CONCLUÍDO
- [x] Renomear cena (double-click no nome).
- [x] Definir como cena inicial (⭐ na lista).
- [ ] Alterar dimensões (modal "Propriedades da Cena") - *adiado*

---

🟡 FASE 3: Organização de Assets (Sprint 3 - 2 dias) - ✅ CONCLUÍDA
3.1 Refatoração do Asset Browser ⏱️ 4h - ✅ CONCLUÍDO
- [x] Separar assets por categoria (TreeView).
- [x] Grid de thumbnails para cada categoria.

3.2 Upload com Validação ⏱️ 2h - ✅ CONCLUÍDO
- [x] Validar formato (MIME type) e tamanho dos arquivos no backend.

3.3 Gerenciamento Avançado ⏱️ 2h - ✅ CONCLUÍDO
- [x] Deletar assets (com verificação de uso).

---

🟢 FASE 4: Melhorias de UX (Sprint 4 - 2 dias) - ✅ CONCLUÍDA
4.1 Atalhos de Teclado ⏱️ 2h - ✅ CONCLUÍDO
- [x] Implementar atalhos (Ctrl+S, F5, Delete).
- [x] Adicionados atalhos para Undo/Redo (Ctrl+Z, Ctrl+Y).

4.2 Sistema de Desfazer/Refazer ⏱️ 4h - ✅ CONCLUÍDO
- [x] Implementado hook `useHistory` para gerenciar o estado do projeto.
- [x] Ações de modificação agora são adicionadas ao histórico.
- [x] Funções `undo` e `redo` funcionam com os atalhos de teclado.

---

⚪ FASE 5: Funcionalidades Avançadas (Pós-MVP)
5.1 Hotspots (Áreas Clicáveis) ⏱️ 8h - ✅ CONCLUÍDO (MVP)
- [x] Desenhar hotspots retangulares na cena.
- [x] Visualização de hotspots com outline pontilhado.
- [x] Definir ação "Ir para Cena" em um hotspot.
- [x] Deletar hotspots.

5.2 Editor de Diálogos Visual ⏱️ 12h
5.3 Sistema de Inventário ⏱️ 6h
5.4 IA Assistant (Gemini + Stable Diffusion) ⏱️ 16h

---
### 🚀 Próximos Passos (Pós-MVP)
O núcleo do editor está funcional. As próximas fases se concentrarão em expandir as capacidades criativas e melhorar o fluxo de trabalho.

- **Editor de Diálogos Visual**: Implementar a interface de nós para criar e gerenciar conversas.
- **Sistema de Inventário**: Permitir a criação e gerenciamento de itens que o jogador pode coletar.
- **Polimento de UX**: Adicionar tooltips, filtros, e outras melhorias de qualidade de vida.
- **Integração com IA**: Conectar o assistente de IA para geração de conteúdo.
---

Parabéns! Chegamos a um marco incrível. O que você gostaria de fazer agora?