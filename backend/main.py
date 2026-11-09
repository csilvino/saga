import logging
import sys
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# --- Configuração de Logging para Debug ---
logging.basicConfig(level=logging.INFO)
logging.getLogger("watchfiles").setLevel(logging.DEBUG)
# --- Fim da Configuração de Logging ---

# Adiciona o diretório raiz ao path
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

from backend.api.routes import projects, scenes, dialogs, ai, assets, auth, orchestrator, genai_sprites, tools, objects, genai_image, genai_edit, game
from backend.services.project_service import project_service # Importa a instância

app = FastAPI(
    title="Saga Engine API",
    description="Backend para o Editor da Saga Engine",
    version="0.1.0"
)

# Configuração de CORS
origins = [
    "http://localhost:5173", # Porta padrão do Vite
    "http://localhost:5174", # Porta alternativa comum
    "http://localhost:5175", # Outra porta alternativa
    "http://localhost:3000", # Porta comum para React dev
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
    "http://127.0.0.1:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", # Porta padrão do Vite
        "http://localhost:5174", # Porta alternativa comum
        "http://localhost:5175", # Outra porta alternativa
        "http://localhost:3000", # Porta comum para React dev
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registra as rotas
app.include_router(projects.router)
app.include_router(scenes.router)
app.include_router(dialogs.router)
app.include_router(ai.router)
app.include_router(assets.router)
app.include_router(auth.router)
app.include_router(orchestrator.router)
app.include_router(genai_sprites.router)
app.include_router(tools.router)
app.include_router(objects.router)
app.include_router(genai_image.router)
app.include_router(genai_edit.router)
app.include_router(game.router)
app.include_router(game.ses_router)

@app.get("/")
async def root():
    return {"message": "Saga Engine API is running!", "status": "ok"}

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app", 
        host="0.0.0.0", 
        port=8070, 
        reload=True,
        reload_dirs=["backend"] # Monitora apenas a pasta 'backend'
    )
