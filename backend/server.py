import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Adiciona o diretório raiz do projeto ao sys.path para importações corretas
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

# Importa os roteadores da API
from backend.api.routes import projects, scenes, assets, auth, ai, yolo_detection, genai_sprites, genai_edit, tools, orchestrator

# --- Configuração da Aplicação FastAPI ---
app = FastAPI(
    title="Saga Engine API",
    description="API para gerenciar projetos, cenas e assets do Saga Engine.",
    version="0.1.0"
)

# --- Configuração do CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Monta o diretório de projetos para servir arquivos estáticos
app.mount("/projects", StaticFiles(directory=ROOT_DIR / "projects"), name="projects")

# --- Inclusão dos Roteadores da API ---
app.include_router(projects.router)
app.include_router(scenes.router)
app.include_router(assets.router)
app.include_router(auth.router)
app.include_router(ai.router)
app.include_router(yolo_detection.router)
app.include_router(genai_sprites.router)
app.include_router(genai_edit.router)
app.include_router(tools.router)
app.include_router(orchestrator.router) # Rota do Orquestrador adicionada

# --- Endpoint Raiz ---
@app.get("/", tags=["Root"])
def read_root():
    """Verifica o status do servidor."""
    return {"status": "Saga Engine server is running"}

# --- Inicialização (para debug) ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8070, reload=True)
