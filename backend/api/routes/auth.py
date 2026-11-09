"""
Chave da IA: cada pessoa cadastra a sua própria chave do Gemini em Configurações → API Keys.
Não há login: a chave fica no computador do usuário (~/.saga_engine_settings.json), fora do projeto.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import user_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class ApiKey(BaseModel):
    key: str


@router.get("/has-key")
async def check_has_key():
    """Verifica se a chave da API do Gemini já está configurada."""
    return {"has_key": bool(user_settings.get_gemini_key())}


@router.post("/key")
async def save_api_key(api_key: ApiKey):
    try:
        user_settings.save_gemini_key(api_key.key)
        return {"status": "success", "message": "Chave de API salva com sucesso."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Não foi possível salvar a chave: {e}")
