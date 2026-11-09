from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from PIL import Image
from pathlib import Path
import io
import uuid
import logging
from typing import Optional
from google import genai
from google.genai import types
import numpy as np
import cv2

from backend.services.project_service import project_service
from backend.services.gemini_imagen import GeminiImagenExtractor
from backend.services.image_processing import process_extraction
from backend.config.user_settings import get_gemini_key, get_image_model, get_generation_source

# Importação condicional para não quebrar se as libs não estiverem instaladas
try:
    from backend.services.sana_generator import sana_service
except ImportError:
    sana_service = None

router = APIRouter(prefix="/api/genai/edit", tags=["genai-edit"])

class RemoveObjectRequest(BaseModel):
    project_name: str
    background_path: str
    object_name: str
    bbox: list

class GenerateContextualImageRequest(BaseModel):
    project_name: str
    prompt: str
    base_image_path: Optional[str] = None
    output_type: str = "sprites" # sprites, backgrounds, items

@router.post("/remove-object")
async def remove_object_from_image(request: RemoveObjectRequest):
    """
    Remove um objeto de uma imagem de fundo usando IA (inpainting).
    """
    api_key = get_gemini_key()
    if not api_key:
        raise HTTPException(status_code=400, detail="A chave da API do Gemini não está configurada.")

    try:
        # Carrega a imagem de fundo original
        project_path = project_service.load_project_path(request.project_name)
        original_image_path = (project_path / request.background_path).resolve()
        if not original_image_path.is_file():
            raise HTTPException(status_code=404, detail="Imagem de fundo não encontrada.")
        
        image_pil = Image.open(original_image_path)

        # Inicializa o extrator e remove o objeto
        extractor = GeminiImagenExtractor(api_key=api_key)
        new_image_pil = extractor.remove_object(
            image_pil=image_pil,
            object_name=request.object_name,
            bbox=request.bbox
        )

        if not new_image_pil:
            raise HTTPException(status_code=500, detail="A IA não conseguiu remover o objeto da imagem.")

        # Salva a nova imagem
        output_dir = project_path / "backgrounds"
        output_dir.mkdir(exist_ok=True)
        
        original_stem = Path(request.background_path).stem
        new_filename = f"{original_stem}_inpainted_{uuid.uuid4().hex[:6]}.png"
        output_path = output_dir / new_filename
        
        new_image_pil.save(output_path, "PNG")
        
        new_asset_path = f"backgrounds/{new_filename}"
        
        return {"new_background_path": new_asset_path}

    except Exception as e:
        logging.error(f"Erro ao remover objeto da imagem: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")

@router.post("/generate-contextual-image")
async def generate_contextual_image(request: GenerateContextualImageRequest):
    """
    Gera uma imagem contextual.
    Usa SANA (Local) ou Gemini (Cloud) dependendo da configuração.
    """
    source = get_generation_source()
    logging.info(f"Solicitação de geração de imagem. Fonte configurada: {source}")

    try:
        generated_image = None

        if source == 'local':
            if not sana_service:
                raise HTTPException(status_code=500, detail="Serviço SANA não disponível. Instale as dependências locais.")
            
            # SANA não suporta image-to-image nativamente da mesma forma que o Gemini Inpainting
            # Por enquanto, usamos apenas o prompt de texto para geração local
            # Futuro: Implementar img2img com SANA
            generated_image = sana_service.generate_image(prompt=request.prompt)

        else: # Cloud (Gemini)
            api_key = get_gemini_key()
            if not api_key:
                raise HTTPException(status_code=400, detail="A chave da API do Gemini não está configurada.")
            
            client = genai.Client(api_key=api_key)
            contents = [request.prompt]
            
            # Se houver imagem base, carrega e adiciona ao prompt (apenas para Cloud por enquanto)
            if request.base_image_path:
                project_path = project_service.load_project_path(request.project_name)
                base_image_full_path = (project_path / request.base_image_path).resolve()
                
                if base_image_full_path.is_file():
                    base_image = Image.open(base_image_full_path)
                    contents.append(base_image)
                else:
                    logging.warning(f"Imagem base não encontrada: {base_image_full_path}")

            image_model_name = get_image_model()
            logging.info(f"Gerando imagem na nuvem com o modelo: {image_model_name}")

            response = client.models.generate_content(
                model=image_model_name,
                contents=contents,
            )

            for part in response.parts:
                if part.inline_data:
                    generated_image = part.as_image()
                    break
        
        if not generated_image:
             raise HTTPException(status_code=500, detail="A IA não retornou nenhuma imagem.")

        # Salva a imagem gerada
        project_path = project_service.load_project_path(request.project_name)
        output_dir = project_path / request.output_type
        output_dir.mkdir(exist_ok=True)
        
        filename = f"gen_{uuid.uuid4().hex[:8]}.png"
        output_path = output_dir / filename
        
        generated_image.save(output_path, "PNG")
        
        asset_path = f"{request.output_type}/{filename}"
        
        return {
            "success": True,
            "message": f"Imagem gerada com sucesso ({source}).",
            "asset_path": asset_path
        }

    except Exception as e:
        logging.error(f"Erro ao gerar imagem: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro na geração de imagem: {str(e)}")
class ExtractObjectRequest(BaseModel):
    project_name: str
    scene_id: str
    image_path: str # Caminho relativo do background
    selection_points: list[dict] # [{x: 10, y: 10}, ...]

@router.post("/extract-object")
async def extract_object_from_image(request: ExtractObjectRequest):
    """
    1. Cria uma máscara a partir dos pontos.
    2. Recorta o objeto (Sprite).
    3. Remove o objeto do fundo (Inpaint).
    4. Retorna os caminhos dos novos assets.
    """
    try:
        project_path = project_service.load_project_path(request.project_name)
        # Strip query strings if present (e.g. backgrounds/img.png?t=123)
        clean_image_path = request.image_path.split('?')[0]
        full_image_path = (project_path / clean_image_path).resolve()
        
        if not full_image_path.is_file():
            raise HTTPException(status_code=404, detail=f"Imagem não encontrada: {clean_image_path}")

        image_pil = Image.open(full_image_path).convert("RGBA")
        width, height = image_pil.size

        # 2 e 3. RECORTAR OBJETO E INPAINT USANDO O SERVICE UNIFICADO
        sprite_cropped, inpainted_image, real_bbox = process_extraction(
            str(full_image_path), 
            points=request.selection_points
        )
        
        # Salvar Sprite
        sprites_dir = project_path / "sprites"
        sprites_dir.mkdir(exist_ok=True)
        sprite_filename = f"extracted_{uuid.uuid4().hex[:6]}.png"
        sprite_path = sprites_dir / sprite_filename
        sprite_cropped.save(sprite_path, "PNG")
        logging.info(f"Sprite salvo em: {sprite_path}")

        # Salvar Background Inpainted
        bg_dir = project_path / "backgrounds"
        bg_stem = Path(clean_image_path).stem
        new_bg_filename = f"{bg_stem}_clean_{uuid.uuid4().hex[:6]}.png"
        new_bg_path = bg_dir / new_bg_filename
        inpainted_image.save(new_bg_path, "PNG")
        logging.info(f"Background salvo em: {new_bg_path}")
        
        # Obter o bbox para retorno da posição
        bbox = sprite_cropped.getbbox() # Isso não é bem o bbox na imagem original
        # Precisamos do bbox original da seleção para posicionar no frontend
        pts = np.array([(int(p['x']), int(p['y'])) for p in request.selection_points], np.int32)
        xmin, ymin, w, h = cv2.boundingRect(pts)

        return {
            "success": True,
            "new_background_path": f"backgrounds/{new_bg_filename}",
            "new_sprite_path": f"sprites/{sprite_filename}",
            "position": {"x": real_bbox["left"], "y": real_bbox["top"]},
            "real_bbox_pixels": real_bbox,
            "message": "Extração realizada com inpainting real"
        }

    except Exception as e:
        logging.error(f"Erro na extração: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro na extração: {str(e)}")
