from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from google import genai
from PIL import Image
from pathlib import Path
import json
import uuid
import re

from backend.services.project_service import project_service, get_project_path
from backend.config.user_settings import get_gemini_key, get_gemini_model
from backend.services.image_processing import process_extraction
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai"])

class ChatContext(BaseModel):
    scene_id: Optional[str] = None
    background_path: Optional[str] = None

class ChatMessage(BaseModel):
    message: str
    context: Optional[ChatContext] = None

class DetectRequest(BaseModel):
    project_name: str
    image_path: str

class ExtractRequest(BaseModel):
    project_name: str
    image_path: str
    object_name: str
    bbox: dict # {ymin, xmin, ymax, xmax}

def clean_json_string(json_str: str) -> str:
    """Limpa a string retornada pela LLM para tentar extrair um JSON válido."""
    json_str = re.sub(r'```json\s*', '', json_str)
    json_str = re.sub(r'```\s*', '', json_str)
    start = json_str.find('[')
    end = json_str.rfind(']')
    if start != -1 and end != -1:
        json_str = json_str[start:end+1]
    return json_str.strip()

@router.post("/chat")
async def ai_chat(chat_message: ChatMessage):
    api_key = get_gemini_key()
    if not api_key:
        raise HTTPException(status_code=400, detail="Chave da API do Gemini não configurada.")

    try:
        client = genai.Client(api_key=api_key)
        contents = []
        
        if chat_message.context and chat_message.context.background_path and project_service.project_path:
            project_path = project_service.project_path
            image_path = (project_path / chat_message.context.background_path).resolve()
            if image_path.exists():
                try:
                    img = Image.open(image_path)
                    contents.append("Analise a seguinte imagem de uma cena de jogo e depois responda à pergunta do usuário: ")
                    contents.append(img)
                except Exception as e:
                    print(f"AVISO: Não foi possível carregar a imagem de contexto: {e}")
        
        contents.append(chat_message.message)
        response = client.models.generate_content(model=get_gemini_model(), contents=contents)
        return {"reply": response.text}
    except Exception as e:
        print(f"ERRO API Gemini: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na IA: {e}")

@router.post("/detect-objects")
async def detect_objects(request: DetectRequest):
    api_key = get_gemini_key()
    if not api_key:
        raise HTTPException(status_code=400, detail="Chave Gemini necessária.")

    try:
        project_path = project_service.load_project_path(request.project_name)
        clean_path = request.image_path.lstrip("/")
        image_path = (project_path / clean_path).resolve()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao carregar projeto ou caminho da imagem: {e}")

    if not image_path.exists():
        raise HTTPException(status_code=404, detail=f"Imagem não encontrada no servidor: {request.image_path}")

    try:
        client = genai.Client(api_key=api_key)
        img = Image.open(image_path)
        
        prompt = """
        Analise esta imagem de cena de jogo. Identifique os objetos principais que poderiam ser interativos (ex: móveis, itens, portas).
        Para cada objeto, forneça o nome e a bounding box (caixa delimitadora) com coordenadas normalizadas (0.0 a 1.0).
        
        IMPORTANTE: Retorne APENAS um JSON válido. Não use markdown. Não use aspas simples.
        Formato esperado:
        [
            {"name": "Relogio", "bbox": {"ymin": 0.1, "xmin": 0.2, "ymax": 0.3, "xmax": 0.4}},
            {"name": "Mesa", "bbox": {"ymin": 0.5, "xmin": 0.1, "ymax": 0.8, "xmax": 0.9}}
        ]
        """
        
        response = client.models.generate_content(model=get_gemini_model(), contents=[prompt, img])
        cleaned_json = clean_json_string(response.text)
        objects = json.loads(cleaned_json)
        return {"objects": objects}
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"A IA retornou um formato inválido: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao detectar objetos: {e}")

@router.post("/extract-object")
async def extract_object(request: ExtractRequest):
    try:
        project_path = project_service.load_project_path(request.project_name)
        clean_path = request.image_path.lstrip("/")
        image_path = (project_path / clean_path).resolve()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao carregar projeto ou caminho da imagem: {e}")

    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Imagem não encontrada.")

    try:
        sprite_img, background_restored_img, real_bbox = process_extraction(str(image_path), request.bbox)
        
        obj_id = str(uuid.uuid4())[:8]
        safe_name = "".join([c for c in request.object_name if c.isalnum() or c in (' ', '-', '_')]).strip().replace(' ', '_').lower()
        sprite_filename = f"sprites/{safe_name}_{obj_id}.png"
        sprite_full_path = project_path / sprite_filename
        sprite_full_path.parent.mkdir(parents=True, exist_ok=True)
        sprite_img.save(sprite_full_path, format="PNG")
        
        bg_filename = f"backgrounds/bg_edited_{obj_id}.jpg"
        bg_full_path = project_path / bg_filename
        bg_full_path.parent.mkdir(parents=True, exist_ok=True)
        background_restored_img.save(bg_full_path, format="JPEG", quality=95)
        
        return {
            "message": "Objeto extraído com sucesso!",
            "object_sprite_path": sprite_filename,
            "new_background_path": bg_filename,
            "real_bbox_pixels": real_bbox
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao extrair objeto: {e}")

class MagicPartAnimateRequest(BaseModel):
    project_name: str
    image_path: str # Path to the object's CURRENT sprite
    object_name: str

class SuggestAnimationRequest(BaseModel):
    object_name: str
    hint: Optional[str] = None

@router.post("/magic-part-animate")
async def magic_part_animate(request: MagicPartAnimateRequest):
    api_key = get_gemini_key()
    if not api_key:
        raise HTTPException(status_code=400, detail="Chave Gemini não configurada.")

    try:
        project_path = project_service.load_project_path(request.project_name)
        clean_path = request.image_path.lstrip("/")
        image_path = (project_path / clean_path).resolve()
        
        if not image_path.exists():
            raise HTTPException(status_code=404, detail=f"Imagem não encontrada: {request.image_path}")

        from backend.services.ai_choreographer import AIChoreographer
        choreographer = AIChoreographer(api_key=api_key)
        
        # 1. Detectar partes
        parts = choreographer.analyze_parts(request.object_name, str(image_path))
        if not parts:
            return {"message": "Nenhuma parte animável detectada.", "parts": []}
        
        # Para o "Magic", vamos processar a primeira parte detectada (ex: Pêndulo)
        part = parts[0]
        bbox_raw = part['bbox'] # [ymin, xmin, ymax, xmax] 0-1000
        
        bbox_conv = {
            'ymin': bbox_raw[0] / 1000.0,
            'xmin': bbox_raw[1] / 1000.0,
            'ymax': bbox_raw[2] / 1000.0,
            'xmax': bbox_raw[3] / 1000.0
        }
        
        # 2. Extrair a parte do sprite original
        # Note: Aqui o "background_restored" é na verdade o Sprite Original sem a parte
        part_sprite_img, sprite_without_part_img, real_bbox = process_extraction(str(image_path), bbox_conv)
        
        obj_id = str(uuid.uuid4())[:8]
        part_name_safe = "".join([c for c in part['part_name'] if c.isalnum() or c in (' ', '-', '_')]).strip().replace(' ', '_').lower()
        
        # Salvar Novo Sprite (A parte: ex pêndulo)
        part_filename = f"sprites/{part_name_safe}_{obj_id}.png"
        part_full_path = project_path / part_filename
        part_sprite_img.save(part_full_path, format="PNG")
        
        # Salvar Sprite Atualizado (O pai sem a parte: ex relógio sem pêndulo)
        updated_parent_filename = f"sprites/upd_{request.object_name.lower()}_{obj_id}.png"
        updated_parent_path = project_path / updated_parent_filename
        sprite_without_part_img.save(updated_parent_path, format="PNG")
        
        # 3. Sugerir animação para a parte
        animation_suggestion = choreographer.analyze_animation(part['part_name'], part['behavior'])
        
        return {
            "message": "Parte extraída e animada!",
            "new_part": {
                "name": part['part_name'],
                "sprite": part_filename,
                "animation": animation_suggestion,
                "bbox_rel": bbox_conv,
                "real_bbox_pixels": real_bbox
            },
            "updated_parent_sprite": updated_parent_filename
        }

    except Exception as e:
        logger.error(f"Erro no Magic Part Animate: {e}")
        raise HTTPException(status_code=500, detail=f"Falha na automação mágica: {str(e)}")

@router.post("/suggest-animation")
async def suggest_animation(request: SuggestAnimationRequest):
    # ... (existing code, unchanged)
    api_key = get_gemini_key()
    if not api_key:
        raise HTTPException(status_code=400, detail="Chave Gemini não configurada.")
        
    try:
        from backend.services.ai_choreographer import AIChoreographer
        choreographer = AIChoreographer(api_key=api_key)
        
        suggestion = choreographer.analyze_animation(request.object_name, request.hint)
        return suggestion
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao sugerir animação: {str(e)}")
