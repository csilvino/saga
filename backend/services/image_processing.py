"""
image_processing.py - SAGA ENGINE
Versão Cloud-First: Usa Gemini para Inpainting (Remoção de Objeto) e RemBG para recorte.
"""

import cv2
import numpy as np
from PIL import Image
import io
import logging
from rembg import remove

from backend.services.gemini_imagen import GeminiImagenExtractor
from backend.config.user_settings import get_gemini_key, get_image_model

logger = logging.getLogger(__name__)

def inpaint_with_gemini(image_pil: Image.Image, mask_pil: Image.Image) -> Image.Image:
    """
    Usa a API do Gemini para remover o objeto mascarado e restaurar o fundo.
    """
    api_key = get_gemini_key()
    if not api_key:
        logger.warning("Chave Gemini não configurada. Usando fallback OpenCV.")
        return inpaint_opencv_improved(image_pil, mask_pil)

    try:
        # 1. Criar uma versão da imagem com a área a ser removida destacada (ex: contorno vermelho)
        img_np = np.array(image_pil.convert("RGB"))
        mask_np = np.array(mask_pil)
        if len(mask_np.shape) == 3: mask_np = mask_np[:,:,0]
        
        # Encontrar contornos da máscara
        contours, _ = cv2.findContours(mask_np, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Desenhar contorno na imagem guia
        guide_img_np = img_np.copy()
        cv2.drawContours(guide_img_np, contours, -1, (255, 0, 0), 2) # Contorno Vermelho
        guide_image = Image.fromarray(guide_img_np)
        
        # Prompt refinado para preservar o contexto (mesa, chão, etc.)
        prompt = (
            "Edit this image: Remove ONLY the object outlined in red. "
            "Do NOT remove the surface underneath it (like a table, floor, or shelf). "
            "Reconstruct the surface texture realistically where the object was standing. "
            "Return ONLY the cleaned image without the red outline."
        )
        
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=api_key)
        model_id = get_image_model()
        
        # CORREÇÃO: Removido response_mime_type="image/png" pois causa erro 400 no modelo multimodal
        response = client.models.generate_content(
            model=model_id,
            contents=[prompt, guide_image]
        )
        
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    logger.info("Inpainting com Gemini realizado com sucesso.")
                    return Image.open(io.BytesIO(part.inline_data.data))
        
        logger.warning("Gemini não retornou imagem editada. Usando fallback.")
        return inpaint_opencv_improved(image_pil, mask_pil)

    except Exception as e:
        logger.error(f"Erro no inpainting Cloud (Gemini): {e}")
        return inpaint_opencv_improved(image_pil, mask_pil)

def inpaint_opencv_improved(image_pil: Image.Image, mask_pil: Image.Image) -> Image.Image:
    """
    Versão melhorada do OpenCV inpaint (Telea).
    Rápido, leve e não requer download de modelos.
    """
    img = np.array(image_pil.convert("RGB"))
    mask = np.array(mask_pil)
    
    if len(mask.shape) == 3:
        mask = mask[:, :, 0]
    
    _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
    
    # Dilatar a máscara para garantir que cobrimos as bordas do objeto
    kernel = np.ones((7, 7), np.uint8)
    mask_dilated = cv2.dilate(mask, kernel, iterations=4)
    
    # Inpainting
    result = cv2.inpaint(img, mask_dilated, inpaintRadius=25, flags=cv2.INPAINT_TELEA)
    
    # Suavização para disfarçar as bordas do inpainting
    blurred = cv2.GaussianBlur(result, (15, 15), 0)
    mask_feathered = cv2.GaussianBlur(mask_dilated.astype(float), (31, 31), 0) / 255.0
    mask_feathered = mask_feathered[:, :, np.newaxis]
    
    result_blended = (result.astype(float) * (1 - mask_feathered * 0.3) +
                      blurred.astype(float) * (mask_feathered * 0.3)).astype(np.uint8)
    
    return Image.fromarray(result_blended)

def process_extraction(image_path: str, bbox: dict = None, points: list[dict] = None) -> tuple[Image.Image, Image.Image, dict]:
    """
    Extrai um objeto de uma imagem e restaura o fundo.
    1. Recorta o objeto (RemBG).
    2. Restaura o fundo (Gemini Cloud Inpaint).
    """
    # 1. Carregar imagem original
    original_img = Image.open(image_path).convert("RGBA")
    width, height = original_img.size
    
    # 2. Definir região de interesse (Crop) e Máscara Inicial
    if points:
        pts = np.array([(int(p['x']), int(p['y'])) for p in points], np.int32)
        xmin, ymin, w, h = cv2.boundingRect(pts)
        xmax, ymax = xmin + w, ymin + h
        mask_points = np.zeros((height, width), dtype=np.uint8)
        cv2.fillPoly(mask_points, [pts], 255)
    elif bbox:
        xmin_norm = max(0.0, min(1.0, bbox['xmin']))
        ymin_norm = max(0.0, min(1.0, bbox['ymin']))
        xmax_norm = max(0.0, min(1.0, bbox['xmax']))
        ymax_norm = max(0.0, min(1.0, bbox['ymax']))
        xmin, ymin = int(xmin_norm * width), int(ymin_norm * height)
        xmax, ymax = int(xmax_norm * width), int(ymax_norm * height)
        mask_points = None
    else:
        raise ValueError("É necessário fornecer 'bbox' ou 'points'.")

    padding = 25
    left = max(0, xmin - padding)
    top = max(0, ymin - padding)
    right = min(width, xmax + padding)
    bottom = min(height, ymax + padding)
    
    if right <= left or bottom <= top:
        raise ValueError(f"Bbox/Points resultaram em área nula.")

    # 3. Recortar o objeto (Crop)
    crop = original_img.crop((left, top, right, bottom))
    
    # 4. Remover o fundo do recorte (Criar Sprite)
    if mask_points is not None:
        mask_crop = mask_points[top:bottom, left:right]
        mask_pil = Image.fromarray(mask_crop)
        temp_sprite = Image.new("RGBA", crop.size, (0,0,0,0))
        temp_sprite.paste(crop, (0,0), mask=mask_pil)
        crop = temp_sprite

    img_byte_arr = io.BytesIO()
    crop.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    
    # post_process_mask helps clean up edges and dark backgrounds
    sprite_bytes = remove(img_byte_arr, post_process_mask=True)
    sprite_img = Image.open(io.BytesIO(sprite_bytes)).convert("RGBA")
    
    # 5. Preparar Máscara para Inpainting do Fundo
    mask_inpaint = np.zeros((height, width), dtype=np.uint8)
    sprite_np = np.array(sprite_img)
    alpha_mask = sprite_np[:, :, 3]
    h_sprite, w_sprite = alpha_mask.shape
    h_paste = min(h_sprite, height - top)
    w_paste = min(w_sprite, width - left)
    
    object_mask = (alpha_mask[:h_paste, :w_paste] > 10).astype(np.uint8) * 255
    mask_inpaint[top:top+h_paste, left:left+w_paste] = object_mask

    mask_pil_final = Image.fromarray(mask_inpaint)

    # 6. Executar Inpainting do Fundo (Gemini Cloud)
    logger.info("Iniciando inpainting do fundo com Gemini Cloud...")
    # Tenta usar Gemini, se falhar cai para OpenCV
    background_restored_rgb = inpaint_with_gemini(original_img.convert("RGB"), mask_pil_final)

    # CORREÇÃO: Gemini pode retornar imagem com dimensões diferentes.
    # Redimensionar para o tamanho original antes de compor o canal alpha.
    if background_restored_rgb.size != (width, height):
        logger.warning(
            f"Inpainted image size {background_restored_rgb.size} differs from original {(width, height)}. Resizing."
        )
        background_restored_rgb = background_restored_rgb.resize((width, height), Image.LANCZOS)

    # Restaurar Alpha original
    if original_img.mode == 'RGBA':
        original_alpha = np.array(original_img.split()[-1])
        # Onde houve inpainting, o alpha deve ser 255 (opaco)
        final_alpha = np.where(mask_inpaint > 0, 255, original_alpha).astype(np.uint8)
        final_img_np = np.dstack((np.array(background_restored_rgb), final_alpha))
        background_restored = Image.fromarray(final_img_np, "RGBA")
    else:
        background_restored = background_restored_rgb.convert("RGBA")

    # 7. Calcular Bbox Real
    trim_bbox = sprite_img.getbbox()
    if trim_bbox:
        final_sprite = sprite_img.crop(trim_bbox)
        real_bbox_pixels = {
            "left": left + trim_bbox[0],
            "top": top + trim_bbox[1],
            "width": trim_bbox[2] - trim_bbox[0],
            "height": trim_bbox[3] - trim_bbox[1],
            "parent_width": width,
            "parent_height": height
        }
    else:
        final_sprite = sprite_img
        real_bbox_pixels = {
            "left": left, 
            "top": top, 
            "width": right-left, 
            "height": bottom-top,
            "parent_width": width,
            "parent_height": height
        }

    return final_sprite, background_restored, real_bbox_pixels
