# CHANGELOG

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

Formato:
- Versões seguem SemVer
- Seção "Unreleased" mantém mudanças que ainda não foram lançadas

## [Unreleased] - 2026-03-09 (Current Dev)

### 🚀 Major Features (IA & Orquestração)
- **Novo Orquestrador Gemini (v2.0):**
  - Migração completa para a nova SDK `google-genai`.
  - Implementação de `system_instruction` robusto com a "BIBLIOTECA SES COMPLETA v2.0".
  - Adição de ferramentas de IA: `create_scene`, `create_object_in_scene`, `set_scene_background`, `generate_image`, `delete_scene`.
  - Mecanismo de **Debounce** para evitar chamadas duplicadas da IA.
  - Otimização automática de prompts: A IA reescreve prompts de usuário para melhor performance em modelos de difusão.

- **Geração de Imagem Local (SSD-1B):**
  - Implementação do `local_image_generator.py` usando `StableDiffusionXLPipeline`.
  - Modelo padrão definido para **`segmind/SSD-1B`** (rápido, público e alta qualidade).
  - Tratamento de imagem com `numpy` para evitar artefatos e imagens pretas.
  - Suporte a prompts positivos e negativos.

- **Criação Inteligente de Objetos:**
  - Novo serviço `object_generation_service.py`.
  - Geração automática de placeholders (emojis) para sprites.
  - Geração automática de scripts SES básicos (`on examine`, `on click`).
  - Cálculo de posição inteligente para evitar sobreposição de objetos na cena.

### 🛠️ Backend Improvements
- **Rotas de API:**
  - `POST /api/scenes/create`: Adicionada verificação `check_if_exists` para evitar duplicatas (retorna sucesso com ID existente).
  - `DELETE /api/scenes/`: Nova rota para deleção de cenas.
  - `POST /api/objects/create`: Atualizada para usar o gerador inteligente de objetos.
  - `POST /api/genai/generate-image`: Nova rota para geração de imagens via IA local.
- **Project Service:**
  - Unificação dos métodos de salvamento em `save_project_data`.

### 🐛 Bug Fixes
- Correção do loop de criação de cenas duplicadas pela IA.
- Correção de erros de `async/await` no orquestrador Gemini.
- Correção de erros de autenticação com modelos Hugging Face (mudança para modelo público).
- Correção do estado do `SettingsPanel` no frontend (abrir/fechar).

### 📝 Documentation
- Atualização do CHANGELOG com o progresso recente.

## [0.1.0] - YYYY-MM-DD
### Added
- Inicialização do repositório e estrutura do projeto.
