import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import uuid
from pathlib import Path
import logging
from PIL import Image

from backend.services.local_image_generator import LocalWorkerUnavailable, local_image_service
from backend.services.project_service import project_service
from backend.services.gemini_imagen import GeminiImagenExtractor
from backend.config.user_settings import get_gemini_key, get_generation_source

router = APIRouter(prefix="/api/genai", tags=["genai-image"])
logger = logging.getLogger(__name__)

class GenerateImageRequest(BaseModel):
    project_name: str
    prompt: str
    negative_prompt: str = None # Mantido para compatibilidade, mas não usado por Gemini Multimodal
    output_type: str = "sprites"
    width: int = 1024
    height: int = 1024
    reference_image_path: str = None # Novo campo para imagem de referência

class AnalyzeImageRequest(BaseModel):
    project_name: str
    image_path: str
    prompt: str = "Descreva esta imagem em detalhes, focando no estilo artístico, cores e elementos principais."

class AnalyzeSceneRequest(BaseModel):
    project_name: str
    scene_id: str

@router.post("/generate-image")
async def generate_image_route(request: GenerateImageRequest):
    """
    Gera uma imagem usando o gerador configurado (Cloud ou Local) e a salva na pasta do projeto.
    """
    try:
        source = get_generation_source()
        image = None
        
        # Resolve o caminho absoluto da imagem de referência, se fornecido
        full_reference_image_path = None
        if request.reference_image_path:
            project_path = project_service.load_project_path(request.project_name)
            full_reference_image_path = str(project_path / request.reference_image_path)
            if not Path(full_reference_image_path).exists():
                raise HTTPException(status_code=404, detail=f"Imagem de referência não encontrada: {request.reference_image_path}")

        if source == 'cloud':
            api_key = get_gemini_key()
            if not api_key:
                raise HTTPException(status_code=400, detail="Chave da API Gemini não configurada para geração Cloud.")
            
            extractor = GeminiImagenExtractor(api_key)
            image = extractor.generate_image(
                prompt=request.prompt,
                negative_prompt=request.negative_prompt, # Será ignorado por Gemini Multimodal
                width=request.width,
                height=request.height,
                reference_image_path=full_reference_image_path # Passa a imagem de referência
            )
            filename_prefix = "Cloud_Gemini"
        else:
            # Local: FLUX.1 Kontext on the user's GPU (local_image_worker), with style reference
            try:
                image = await asyncio.to_thread(
                    local_image_service.generate_image,
                    prompt=request.prompt,
                    width=request.width,
                    height=request.height,
                    reference_image_path=full_reference_image_path,
                )
            except LocalWorkerUnavailable as e:
                raise HTTPException(status_code=503, detail=str(e))
            filename_prefix = "Local_FLUX"
        
        project_path = project_service.load_project_path(request.project_name)
        
        if request.output_type not in ["sprites", "backgrounds", "items"]:
            raise HTTPException(status_code=400, detail="Tipo de saída inválido.")
            
        output_dir = project_path / request.output_type
        output_dir.mkdir(exist_ok=True)
        
        filename = f"{filename_prefix}_{uuid.uuid4().hex[:8]}.png"
        save_path = output_dir / filename
        image.save(save_path, "PNG")
        
        relative_path = f"{request.output_type}/{filename}"
        
        return {
            "success": True,
            "message": "Imagem gerada com sucesso!",
            "image_path": relative_path,
            "source": source
        }
        
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Projeto '{request.project_name}' não encontrado.")
    except Exception as e:
        logger.error(f"Erro ao gerar imagem ({get_generation_source()}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno ao gerar imagem: {str(e)}")

@router.post("/analyze-image")
async def analyze_image_route(request: AnalyzeImageRequest):
    """
    Analisa uma imagem existente no projeto usando o Gemini Vision.
    """
    try:
        api_key = get_gemini_key()
        if not api_key:
            raise HTTPException(status_code=400, detail="Chave da API Gemini não configurada.")

        project_path = project_service.load_project_path(request.project_name)
        full_path = project_path / request.image_path

        if not full_path.exists():
            raise HTTPException(status_code=404, detail=f"Imagem não encontrada: {request.image_path}")

        # Carrega a imagem
        image = Image.open(full_path)

        # Usa o extrator (que já tem a lógica de visão)
        extractor = GeminiImagenExtractor(api_key)
        description = extractor.analyze_image(image, request.prompt)

        return {
            "success": True,
            "description": description
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Projeto '{request.project_name}' não encontrado.")
    except Exception as e:
        logger.error(f"Erro ao analisar imagem: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno ao analisar imagem: {str(e)}")

@router.post("/analyze-scene")
async def analyze_scene_route(request: AnalyzeSceneRequest):
    """
    Analisa o background de uma cena específica.
    """
    try:
        api_key = get_gemini_key()
        if not api_key:
            raise HTTPException(status_code=400, detail="Chave da API Gemini não configurada.")

        project = project_service.load_project(request.project_name)
        
        if request.scene_id not in project.get("scenes", {}):
            raise HTTPException(status_code=404, detail=f"Cena {request.scene_id} não encontrada.")
            
        scene = project["scenes"][request.scene_id]
        
        # Lógica melhorada para encontrar o background
        background_path = scene.get("background")
        
        # Se não estiver na raiz, procura nos objetos
        if not background_path:
            for obj in scene.get("objects", []):
                if obj.get("type") == "background":
                    background_path = obj.get("sprite")
                    break
        
        if not background_path:
            return {
                "success": False,
                "message": "Esta cena não possui uma imagem de fundo definida."
            }
            
        # Remove query params (ex: ?t=123) se houver
        if "?" in background_path:
            background_path = background_path.split("?")[0]

        project_path = project_service.load_project_path(request.project_name)
        full_path = project_path / background_path
        
        if not full_path.exists():
            raise HTTPException(status_code=404, detail=f"Arquivo de background não encontrado: {background_path}")

        image = Image.open(full_path)
        extractor = GeminiImagenExtractor(api_key)
        description = extractor.analyze_image(image, "Descreva o estilo visual, a iluminação, as cores e os elementos principais desta cena de jogo.")

        return {
            "success": True,
            "description": description
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Projeto '{request.project_name}' não encontrado.")
    except Exception as e:
        logger.error(f"Erro ao analisar cena: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno ao analisar cena: {str(e)}")
