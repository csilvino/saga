# Arquitetura SAGA ENGINE v2.0 (IA-Driven)

Este documento descreve a nova arquitetura implementada para transformar o SAGA ENGINE em uma ferramenta dirigida por IA.

## 1. O "Cérebro": Gemini Asset Orchestrator
O coração do sistema é o `GeminiAssetOrchestrator` (`backend/services/gemini_orchestrator.py`).

*   **Função:** Atua como um "Diretor de Jogo". Recebe comandos em linguagem natural e decide quais ferramentas usar.
*   **SDK:** Utiliza a nova SDK `google-genai` (v2.0+).
*   **Conhecimento:** Possui a "BIBLIOTECA SES COMPLETA v2.0" em seu `system_instruction`, permitindo que entenda conceitos de cenas, objetos, scripts e lógica de jogo.
*   **Ferramentas (Tools):**
    *   `create_scene`: Cria cenas (com verificação de duplicatas).
    *   `create_object_in_scene`: Cria objetos completos (com placeholder e SES).
    *   `generate_image_and_set_as_background`: Fluxo completo de geração de arte.
    *   `delete_scene`: Remove cenas.
    *   `update_object_properties`: Modifica objetos existentes.

## 2. O "Artista": Local Image Generator
A geração de imagens é feita localmente para garantir privacidade e custo zero, usando a GPU do usuário.

*   **Serviço:** `LocalImageGenerator` (`backend/services/local_image_generator.py`).
*   **Modelo Atual:** `segmind/SSD-1B`.
    *   **Por que este modelo?** É uma versão destilada do Stable Diffusion XL. É 50% menor e 60% mais rápido que o SDXL original, mantendo alta qualidade visual. É público (não requer token HF).
*   **Pipeline:** `StableDiffusionXLPipeline`.
*   **Otimização:** O orquestrador reescreve os prompts do usuário para incluir palavras-chave de estilo ("stylized 3D game asset", "clean render") e prompts negativos para garantir a estética desejada.

## 3. O "Engenheiro": Object Generation Service
Para agilizar a criação de jogos, a IA não gera sprites finais imediatamente.

*   **Serviço:** `ObjectGenerationService` (`backend/services/object_generation_service.py`).
*   **Fluxo:**
    1.  Usuário pede: "Crie uma mesa".
    2.  Serviço escolhe um **Emoji** relevante como placeholder (🪑).
    3.  Serviço gera um **Script SES** básico (`on examine { narrate(...) }`).
    4.  Serviço calcula uma **Posição Inteligente** na cena para não sobrepor outros objetos.
    5.  O objeto é criado instantaneamente.
    6.  O usuário pode pedir para gerar o sprite final depois.

## 4. Fluxo de Dados

```mermaid
graph TD
    User[Usuário] -->|Comando: 'Crie uma cena...'| API[API /orchestrator/command]
    API --> Orchestrator[Gemini Orchestrator]
    
    Orchestrator -->|Decisão: create_scene| SceneAPI[Scene API]
    Orchestrator -->|Decisão: generate_image| ImageAPI[GenAI Image API]
    Orchestrator -->|Decisão: create_object| ObjectAPI[Object API]
    
    ImageAPI --> LocalGen[Local Image Generator (SSD-1B)]
    ObjectAPI --> ObjGen[Object Generation Service]
    
    LocalGen -->|Imagem PNG| FileSystem
    ObjGen -->|JSON Objeto| ProjectService
    
    ProjectService -->|Salva| ProjectJSON[project.json]
```

## 5. Próximos Passos (Roadmap)
- [ ] Implementar `analyze_scene_background` para permitir que a IA "veja" e descreva cenas existentes.
- [ ] Melhorar a geração de sprites de objetos (recorte automático de fundo).
- [ ] Implementar sistema de animação simples via CSS/SES.
