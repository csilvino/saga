import json
from pathlib import Path

# Caminho para o arquivo de configurações do usuário
USER_SETTINGS_PATH = Path.home() / ".saga_engine_settings.json"

# --- CONFIGURAÇÃO DE GERAÇÃO ---

# Fonte de Geração de Imagem: 'cloud' (Gemini) ou 'local' (SANA)
GENERATION_SOURCE = 'cloud'

# Defina como True para usar modelos de maior qualidade (e maior custo, se em nuvem).
USE_PRO_MODELS = False

# --- MODELOS ---

# Modelo de Texto/Orquestração (Rápido e Econômico)
# Padrões; cada usuário escolhe os seus em Configurações → API Keys (gemini_model / gemini_image_model)
DEFAULT_GEMINI_MODEL = 'models/gemini-3.5-flash-lite'

# Modelos de Imagem (Cloud)
# Usando o modelo multimodal correto conforme instrução do usuário
IMAGE_GENERATION_MODEL = 'models/gemini-2.5-flash-image'

# Imagem local: FLUX.1 Kontext no gerador local_image_worker (veja local_image_worker/README.md)

# Modelo de Vídeo (Futuro)
VIDEO_GENERATION_MODEL = 'models/veo-3.1-fast-generate-preview'

# --- CONFIGURAÇÕES DE CRIAÇÃO DE OBJETOS ---
AUTO_GENERATE_SPRITES = False  # True quando imagens funcionarem
PLACEHOLDER_MODE = "emoji"  # ou "icon" ou "text"


def get_user_settings() -> dict:
    """Lê as configurações do usuário do arquivo JSON."""
    if not USER_SETTINGS_PATH.exists():
        return {}
    with open(USER_SETTINGS_PATH, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_user_settings(settings: dict):
    """Salva as configurações no arquivo JSON do usuário."""
    with open(USER_SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=2)

def get_gemini_key() -> str | None:
    """Obtém a chave da API do Gemini das configurações."""
    settings = get_user_settings()
    return settings.get("gemini_api_key")

def save_gemini_key(api_key: str):
    """Salva a chave da API do Gemini nas configurações."""
    settings = get_user_settings()
    settings["gemini_api_key"] = api_key
    save_user_settings(settings)

def get_gemini_model() -> str:
    """Obtém o nome do modelo de texto Gemini das configurações."""
    settings = get_user_settings()
    return settings.get("gemini_model", DEFAULT_GEMINI_MODEL)

def save_models(text_model: str | None = None, image_model: str | None = None,
                image_source: str | None = None):
    """Salva os modelos escolhidos pelo usuário (None mantém o atual).
    image_source: 'cloud' (Gemini) ou 'local' (FLUX na GPU, via local_image_worker)."""
    settings = get_user_settings()
    if text_model:
        settings["gemini_model"] = text_model
    if image_model:
        settings["gemini_image_model"] = image_model
    if image_source in ("cloud", "local"):
        settings["generation_source"] = image_source
    save_user_settings(settings)

def get_image_model() -> str:
    """Obtém o nome do modelo de imagem Gemini das configurações."""
    settings = get_user_settings()
    return settings.get("gemini_image_model", IMAGE_GENERATION_MODEL)

def get_generation_source() -> str:
    """Retorna 'cloud' ou 'local'."""
    settings = get_user_settings()
    return settings.get("generation_source", GENERATION_SOURCE)
