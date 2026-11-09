from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import urllib.parse
import json
import httpx
from fastapi.responses import JSONResponse

from backend.config import google_oauth, user_settings

# Define o prefixo completo da API diretamente no roteador
router = APIRouter(prefix="/api/auth", tags=["auth"])

class ApiKey(BaseModel):
    key: str

class AuthCode(BaseModel):
    code: str
    state: str = None

@router.get("/has-key")
async def check_has_key():
    """Verifica se a chave da API do Gemini já está configurada."""
    has_key = bool(user_settings.get_gemini_key())
    return {"has_key": has_key}

@router.get("/google/url")
async def get_google_auth_url():
    params = {
        "client_id": google_oauth.CLIENT_ID,
        "redirect_uri": "http://localhost:5174/auth/callback",
        "response_type": "code",
        "scope": " ".join(google_oauth.SCOPES),
        "access_type": "offline",
        "prompt": "consent"
    }
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return {"url": auth_url}

@router.post("/google/callback")
async def google_auth_callback(auth_data: AuthCode):
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": auth_data.code,
        "client_id": google_oauth.CLIENT_ID,
        "client_secret": google_oauth.CLIENT_SECRET,
        "redirect_uri": "http://localhost:5174/auth/callback",
        "grant_type": "authorization_code"
    }

    async with httpx.AsyncClient() as client:
        # 1. Trocar o código pelo token de acesso
        token_response = await client.post(token_url, data=data)
        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Falha ao obter token do Google: {token_response.text}")
        
        tokens = token_response.json()
        access_token = tokens.get("access_token")

        # 2. Obter informações do usuário
        user_info_url = "https://www.googleapis.com/oauth2/v1/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}
        user_response = await client.get(user_info_url, headers=headers)
        
        if user_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Falha ao obter dados do usuário do Google")
            
        user_info = user_response.json()

    # 3. Montar os dados do usuário para o frontend
    session_token = access_token 
    
    user_data = {
        "name": user_info.get("name"),
        "email": user_info.get("email"),
        "avatar": user_info.get("picture"),
        "has_gemini_key": bool(user_settings.get_gemini_key())
    }
    
    return JSONResponse(content={
        "session_token": session_token,
        "user": user_data
    })

@router.post("/key")
async def save_api_key(api_key: ApiKey):
    try:
        user_settings.save_gemini_key(api_key.key)
        return {"status": "success", "message": "Chave de API salva com sucesso."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Não foi possível salvar a chave: {e}")
