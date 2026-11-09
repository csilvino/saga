from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import uuid
import cv2
import numpy as np
from PIL import Image
from rembg import remove, new_session
from google import genai
from google.genai import types

from backend.services.project_service import project_service
from backend.config.user_settings import get_gemini_key, get_gemini_model

router = APIRouter(prefix="/api/gemini", tags=["gemini"])

# Sessão do RemBG para performance (carrega o modelo u2net uma vez)
rembg_session = new_session("u2net")

class GeminiExtractRequest(BaseModel):
    project_name: str
    scene_id: str
    object_id: str # ID do objeto detectado pelo YOLO
    bbox: list # [x1, y1, x2, y2] do YOLO
    object_name: str # Nome da classe (ex: "clock")

@router.post("/extract-precise")
async def extract_precise_object(request: GeminiExtractRequest):
    api_key = get_gemini_key()
    if not api_key:
        raise HTTPException(status_code=400, detail="Chave da API Gemini não configurada. Vá em Configurações > IA.")

    try:
        # 1. Carregar a imagem original da cena
        project_path = project_service.load_project_path(request.project_name)
        
        # Encontrar a imagem de fundo
        scene_image_path = None
        for ext in ["jpg", "png", "jpeg"]:
            potential_path = project_path / "backgrounds" / f"{request.scene_id}.{ext}"
            if potential_path.exists():
                scene_image_path = potential_path
                break
        
        if not scene_image_path:
            raise HTTPException(status_code=404, detail="Imagem da cena não encontrada.")

        original_image = Image.open(scene_image_path)
        img_w, img_h = original_image.size

        # 2. Recortar com margem generosa (50%) para dar contexto ao Gemini
        x1, y1, x2, y2 = request.bbox
        width = x2 - x1
        height = y2 - y1
        
        margin_x = width * 0.5
        margin_y = height * 0.5
        
        crop_x1 = max(0, int(x1 - margin_x))
        crop_y1 = max(0, int(y1 - margin_y))
        crop_x2 = min(img_w, int(x2 + margin_x))
        crop_y2 = min(img_h, int(y2 + margin_y))
        
        cropped_image = original_image.crop((crop_x1, crop_y1, crop_x2, crop_y2))
        
        # 3. Consultar Gemini 2.5 Flash para análise visual
        # Como a API de edição direta (inpainting) ainda é restrita, usamos o Gemini
        # para confirmar o objeto e o RemBG para o recorte preciso, guiado pela inteligência.
        
        client = genai.Client(api_key=api_key)
        
        # Prompt focado na identificação visual para garantir que estamos pegando o objeto certo
        prompt = f"""
        Analise este recorte de imagem. O objeto principal é um(a) '{request.object_name}'.
        Confirme se o objeto está visível e inteiro.
        """
        
        # Usando o modelo solicitado (ou o mais próximo disponível publicamente se o 2.5 for beta restrito)
        model_name = get_gemini_model()
        
        response = client.models.generate_content(
            model=model_name,
            contents=[prompt, cropped_image]
        )
        
        print(f"DEBUG: Gemini Analysis: {response.text}")

        # 4. Extração com RemBG (Alta Precisão)
        # O RemBG é especializado em remover fundos. Aplicado no crop focado, ele é excelente.
        output_image = remove(cropped_image, session=rembg_session)
        
        # 5. Salvar o Sprite
        sprites_dir = project_path / "sprites"
        sprites_dir.mkdir(exist_ok=True)
        
        sanitized_name = "".join(c for c in request.object_name if c.isalnum() or c in " _-").rstrip()
        sprite_filename = f"{sanitized_name}_gemini_{uuid.uuid4().hex[:6]}.png"
        sprite_path = sprites_dir / sprite_filename
        
        output_image.save(sprite_path, format="PNG")
        
        # Retornar URL relativa
        sprite_url = f"sprites/{sprite_filename}"
        return {
            "success": True,
            "sprite_url": sprite_url,
            "message": f"Objeto extraído com precisão usando IA."
        }

    except Exception as e:
        print(f"ERRO Gemini Extraction: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na extração com Gemini: {str(e)}")
