from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from PIL import Image, ImageDraw, ImageFilter
from pathlib import Path
import logging
import json
import shutil

from backend.services.project_service import project_service
from backend.config.user_settings import save_gemini_key, get_gemini_key # Adicionado

router = APIRouter(prefix="/api/tools", tags=["tools"])
logger = logging.getLogger(__name__)

# ==================== MODELS ====================

class SpriteSheetRequest(BaseModel):
    project_name: str
    image_paths: List[str]
    output_filename: str
    columns: Optional[int] = None
    spacing: int = 0

class ImageCropRequest(BaseModel):
    project_name: str
    image_path: str
    bbox: Dict[str, int]  # {x, y, width, height}
    output_filename: str

class ImageResizeRequest(BaseModel):
    project_name: str
    image_path: str
    width: int
    height: int
    output_filename: str
    maintain_aspect: bool = True

class ImageFilterRequest(BaseModel):
    project_name: str
    image_path: str
    filter_type: str  # blur, sharpen, edge_enhance, grayscale
    output_filename: str
    intensity: Optional[float] = 1.0

class ProjectAssetListRequest(BaseModel):
    project_name: str
    asset_type: Optional[str] = None  # images, sprites, backgrounds, all

class ImageAnalysisRequest(BaseModel):
    project_name: str
    image_path: str

class MaskCreationRequest(BaseModel):
    project_name: str
    image_path: str
    bbox: Dict[str, int]
    output_filename: str
    mask_type: str = "rectangle"  # rectangle, ellipse

class BatchOperationRequest(BaseModel):
    project_name: str
    operation: str  # resize, convert, rename
    source_pattern: str  # glob pattern
    params: Dict[str, Any]

class ProjectConfigUpdateRequest(BaseModel):
    project_name: str
    updates: Dict[str, Any]

class SaveApiKeyRequest(BaseModel): # Adicionado
    api_key: str

# ==================== API KEY MANAGEMENT ==================== # Adicionado
@router.post("/save-api-key") # Adicionado
async def save_api_key_tool(request: SaveApiKeyRequest): # Adicionado
    """
    🔑 Salva a chave da API do Gemini nas configurações do usuário.
    """
    try:
        if not request.api_key or len(request.api_key) < 10:
            raise HTTPException(status_code=400, detail="Chave de API inválida.")
        
        save_gemini_key(request.api_key)
        logger.info("Chave da API Gemini salva com sucesso.")
        return {"success": True, "message": "Chave da API salva com sucesso."}
    except Exception as e:
        logger.error(f"Erro ao salvar chave da API: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao salvar chave: {str(e)}")

@router.get("/check-api-key")
async def check_api_key_tool(validate: bool = False):
    """
    🔑 Verifica se a chave da API do Gemini está configurada.
    validate=true: faz uma chamada mínima ao Gemini (uma palavra) para confirmar que a chave
    funciona de verdade (chave inválida, revogada ou sem créditos aparecem aqui).
    """
    key = get_gemini_key()
    configured = bool(key)
    if not validate or not configured:
        return {"configured": configured}
    try:
        from google import genai
        from backend.config.user_settings import get_gemini_model
        client = genai.Client(api_key=key)
        await client.aio.models.generate_content(model=get_gemini_model(), contents="ok")
        return {"configured": True, "valid": True}
    except Exception as e:
        message = str(e)
        if "RESOURCE_EXHAUSTED" in message or "402" in message:
            reason = "A chave funciona, mas os créditos da conta acabaram (Google AI Studio → Billing)."
        elif "API_KEY_INVALID" in message or "API key not valid" in message or "PERMISSION_DENIED" in message:
            reason = "Chave inválida ou revogada."
        else:
            reason = message[:200]
        logger.warning(f"Teste da chave Gemini falhou: {reason}")
        return {"configured": True, "valid": False, "error": reason}


@router.delete("/api-key")
async def delete_api_key_tool():
    """🔑 Remove a chave da API do Gemini das configurações do usuário."""
    from backend.config.user_settings import get_user_settings, save_user_settings
    settings = get_user_settings()
    for k in ("gemini_api_key", "geminiApiKey"):
        settings.pop(k, None)
    save_user_settings(settings)
    return {"success": True}

# ==================== SPRITE SHEET ====================

@router.post("/create-sprite-sheet")
async def create_sprite_sheet_tool(request: SpriteSheetRequest):
    """
    🎨 Cria um sprite sheet a partir de múltiplas imagens.
    """
    project_path = project_service.load_project_path(request.project_name)
    
    if not request.image_paths:
        raise HTTPException(status_code=400, detail="Nenhuma imagem fornecida")

    frames = []
    for img_path in request.image_paths:
        full_path = (project_path / img_path).resolve()
        if not full_path.is_file():
            raise HTTPException(status_code=404, detail=f"Imagem não encontrada: {img_path}")
        frames.append(Image.open(full_path).convert('RGBA'))

    frame_width, frame_height = frames[0].size
    num_frames = len(frames)
    columns = request.columns if request.columns is not None else num_frames
    rows = (num_frames + columns - 1) // columns

    total_width = columns * frame_width + (columns - 1) * request.spacing
    total_height = rows * frame_height + (rows - 1) * request.spacing

    sprite_sheet = Image.new('RGBA', (total_width, total_height), (0, 0, 0, 0))

    for idx, frame in enumerate(frames):
        row = idx // columns
        col = idx % columns
        x = col * (frame_width + request.spacing)
        y = row * (frame_height + request.spacing)
        sprite_sheet.paste(frame, (x, y))

    output_dir = project_path / "sprites"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / request.output_filename
    sprite_sheet.save(output_path)

    return {
        "success": True,
        "sprite_sheet_path": f"sprites/{request.output_filename}",
        "frame_width": frame_width,
        "frame_height": frame_height,
        "columns": columns,
        "rows": rows,
        "frame_count": num_frames
    }

# ==================== IMAGE MANIPULATION ====================

@router.post("/crop-image")
async def crop_image_tool(request: ImageCropRequest):
    """
    ✂️ Recorta uma região específica de uma imagem.
    """
    project_path = project_service.load_project_path(request.project_name)
    full_path = (project_path / request.image_path).resolve()
    
    if not full_path.is_file():
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    
    img = Image.open(full_path)
    bbox = request.bbox
    cropped = img.crop((
        bbox['x'],
        bbox['y'],
        bbox['x'] + bbox['width'],
        bbox['y'] + bbox['height']
    ))
    
    output_dir = project_path / "cropped"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / request.output_filename
    cropped.save(output_path)
    
    return {
        "success": True,
        "cropped_image_path": f"cropped/{request.output_filename}",
        "width": bbox['width'],
        "height": bbox['height']
    }

@router.post("/resize-image")
async def resize_image_tool(request: ImageResizeRequest):
    """
    📏 Redimensiona uma imagem.
    """
    project_path = project_service.load_project_path(request.project_name)
    full_path = (project_path / request.image_path).resolve()
    
    if not full_path.is_file():
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    
    img = Image.open(full_path)
    
    if request.maintain_aspect:
        img.thumbnail((request.width, request.height), Image.Resampling.LANCZOS)
        new_size = img.size
    else:
        img = img.resize((request.width, request.height), Image.Resampling.LANCZOS)
        new_size = (request.width, request.height)
    
    output_dir = project_path / "resized"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / request.output_filename
    img.save(output_path)
    
    return {
        "success": True,
        "resized_image_path": f"resized/{request.output_filename}",
        "new_width": new_size[0],
        "new_height": new_size[1]
    }

@router.post("/apply-filter")
async def apply_filter_tool(request: ImageFilterRequest):
    """
    🎭 Aplica filtros em uma imagem.
    """
    project_path = project_service.load_project_path(request.project_name)
    full_path = (project_path / request.image_path).resolve()
    
    if not full_path.is_file():
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    
    img = Image.open(full_path)
    
    if request.filter_type == "blur":
        img = img.filter(ImageFilter.GaussianBlur(radius=request.intensity * 5))
    elif request.filter_type == "sharpen":
        img = img.filter(ImageFilter.SHARPEN)
    elif request.filter_type == "edge_enhance":
        img = img.filter(ImageFilter.EDGE_ENHANCE)
    elif request.filter_type == "grayscale":
        img = img.convert('L').convert('RGBA')
    else:
        raise HTTPException(status_code=400, detail="Filtro não suportado")
    
    output_dir = project_path / "filtered"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / request.output_filename
    img.save(output_path)
    
    return {
        "success": True,
        "filtered_image_path": f"filtered/{request.output_filename}",
        "filter_applied": request.filter_type
    }

# ==================== MASK CREATION ====================

@router.post("/create-mask")
async def create_mask_tool(request: MaskCreationRequest):
    """
    🎭 Cria uma máscara para inpainting.
    """
    project_path = project_service.load_project_path(request.project_name)
    full_path = (project_path / request.image_path).resolve()
    
    if not full_path.is_file():
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    
    img = Image.open(full_path)
    mask = Image.new('L', img.size, 0)
    draw = ImageDraw.Draw(mask)
    
    bbox = request.bbox
    x, y, w, h = bbox['x'], bbox['y'], bbox['width'], bbox['height']
    
    if request.mask_type == "rectangle":
        draw.rectangle([x, y, x + w, y + h], fill=255)
    elif request.mask_type == "ellipse":
        draw.ellipse([x, y, x + w, y + h], fill=255)
    
    output_dir = project_path / "masks"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / request.output_filename
    mask.save(output_path)
    
    return {
        "success": True,
        "mask_path": f"masks/{request.output_filename}",
        "mask_type": request.mask_type
    }

# ==================== PROJECT MANAGEMENT ====================

@router.post("/list-assets")
async def list_assets_tool(request: ProjectAssetListRequest):
    """
    📋 Lista todos os assets de um projeto.
    """
    project_path = project_service.load_project_path(request.project_name)
    
    assets = {
        "images": [],
        "sprites": [],
        "backgrounds": [],
        "masks": [],
        "other": []
    }
    
    for file_path in project_path.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif']:
            relative_path = str(file_path.relative_to(project_path))
            
            if "sprite" in relative_path.lower():
                assets["sprites"].append(relative_path)
            elif "background" in relative_path.lower():
                assets["backgrounds"].append(relative_path)
            elif "mask" in relative_path.lower():
                assets["masks"].append(relative_path)
            else:
                assets["images"].append(relative_path)
    
    if request.asset_type and request.asset_type != "all":
        return {
            "success": True,
            "assets": assets.get(request.asset_type, [])
        }
    
    return {
        "success": True,
        "assets": assets,
        "total_count": sum(len(v) for v in assets.values())
    }

@router.post("/analyze-image")
async def analyze_image_tool(request: ImageAnalysisRequest):
    """
    🔍 Analisa propriedades de uma imagem.
    """
    project_path = project_service.load_project_path(request.project_name)
    full_path = (project_path / request.image_path).resolve()
    
    if not full_path.is_file():
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    
    img = Image.open(full_path)
    
    return {
        "success": True,
        "width": img.width,
        "height": img.height,
        "mode": img.mode,
        "format": img.format,
        "has_transparency": img.mode in ('RGBA', 'LA', 'P'),
        "file_size_kb": full_path.stat().st_size / 1024
    }

@router.post("/update-project-config")
async def update_project_config_tool(request: ProjectConfigUpdateRequest):
    """
    ⚙️ Atualiza o project.json.
    """
    project_path = project_service.load_project_path(request.project_name)
    config_path = project_path / "project.json"
    
    if not config_path.exists():
        raise HTTPException(status_code=404, detail="project.json não encontrado")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Atualiza recursivamente
    def deep_update(base_dict, update_dict):
        for key, value in update_dict.items():
            if isinstance(value, dict) and key in base_dict:
                deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    deep_update(config, request.updates)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    return {
        "success": True,
        "message": "Configuração atualizada com sucesso",
        "updates_applied": request.updates
    }

# ==================== BATCH OPERATIONS ====================

@router.post("/batch-operation")
async def batch_operation_tool(request: BatchOperationRequest):
    """
    🔄 Executa operações em lote.
    """
    project_path = project_service.load_project_path(request.project_name)
    files = list(project_path.glob(request.source_pattern))
    
    results = []
    
    for file_path in files:
        if not file_path.is_file():
            continue
            
        try:
            if request.operation == "resize":
                img = Image.open(file_path)
                img.thumbnail((request.params['width'], request.params['height']))
                img.save(file_path)
                results.append({"file": str(file_path.name), "status": "resized"})
                
            elif request.operation == "convert":
                img = Image.open(file_path)
                new_format = request.params['format'].upper()
                new_path = file_path.with_suffix(f".{request.params['format']}")
                img.save(new_path, format=new_format)
                results.append({"file": str(file_path.name), "status": "converted"})
                
        except Exception as e:
            results.append({"file": str(file_path.name), "status": "error", "error": str(e)})
    
    return {
        "success": True,
        "processed_count": len(results),
        "results": results
    }
