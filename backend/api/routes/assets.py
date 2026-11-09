from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from pathlib import Path
import shutil
import os
import logging
import io
from PIL import Image

from backend.services.project_service import project_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assets", tags=["assets"])

MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "audio/mpeg", "audio/wav", "audio/ogg"}

class DeleteAssetRequest(BaseModel):
    project_name: str
    asset_path: str

@router.get("/list")
async def list_assets(project_name: str):
    project_path = project_service.load_project_path(project_name)
    asset_dirs = ["sprites", "backgrounds", "audio", "items", "fonts"]
    all_assets = {}
    for asset_dir in asset_dirs:
        full_dir_path = project_path / asset_dir
        if full_dir_path.is_dir():
            assets_in_dir = [str(item.relative_to(project_path)).replace("\\", "/") for item in sorted(full_dir_path.iterdir()) if item.is_file()]
            all_assets[asset_dir] = assets_in_dir
    return all_assets

@router.post("/upload")
async def upload_asset(project_name: str = Form(...), asset_type: str = Form(...), file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid file type: {file.content_type}.")
    
    project_path = project_service.load_project_path(project_name)
    upload_dir = project_path / asset_type
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename
    
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Retorna o caminho relativo do asset para que o frontend possa salvá-lo
    asset_path = f"{asset_type}/{file.filename}"
        
    return {
        "success": True, 
        "message": f"Asset '{file.filename}' uploaded.",
        "asset_path": asset_path
    }

@router.delete("/")
async def delete_asset(request: DeleteAssetRequest):
    project = project_service.load_project(request.project_name)
    project_path = project_service.project_path
    asset_path_normalized = request.asset_path.replace("\\", "/")

    for scene in project.get("scenes", {}).values():
        if scene.get("background", "").split('?')[0] == asset_path_normalized:
            raise HTTPException(status_code=400, detail=f"Asset in use as background in scene '{scene['name']}'")
        for obj in scene.get("objects", []):
            if obj.get("sprite", "").split('?')[0] == asset_path_normalized:
                raise HTTPException(status_code=400, detail=f"Asset in use by object '{obj['name']}' in scene '{scene['name']}'")

    full_asset_path = (project_path / asset_path_normalized).resolve()
    if not full_asset_path.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")

    try:
        os.remove(full_asset_path)
        return {"success": True, "message": f"Asset '{asset_path_normalized}' deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting asset: {e}")

# Rota de Thumbnail (DEVE VIR ANTES da rota genérica de assets)
@router.get("/thumbnail/{project_name}/{asset_path:path}")
async def get_asset_thumbnail(project_name: str, asset_path: str):
    try:
        project_path = project_service.load_project_path(project_name)
        clean_asset_path = asset_path.split('?')[0]
        full_asset_path = (project_path / clean_asset_path).resolve()

        if not full_asset_path.is_file():
            raise HTTPException(status_code=404, detail="Asset not found")

        img = Image.open(full_asset_path)
        img.thumbnail((128, 128))
        
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)

        return StreamingResponse(img_byte_arr, media_type="image/png")
    except Exception as e:
        logger.error(f"Erro ao gerar thumbnail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro ao gerar thumbnail.")

# Rota Genérica de Assets (DEVE VIR DEPOIS da de thumbnail)
@router.get("/{project_name}/{asset_path:path}")
async def get_asset(project_name: str, asset_path: str):
    try:
        # Se o asset_path for um emoji ou placeholder, retorna 404 imediatamente
        if not asset_path.isascii():
            raise HTTPException(status_code=404, detail="Placeholder emoji cannot be served as file")

        project_path = project_service.load_project_path(project_name)
        clean_asset_path = asset_path.split('?')[0]
        full_asset_path = (project_path / clean_asset_path).resolve()
        
        if not full_asset_path.is_file() or not full_asset_path.is_relative_to(project_path.resolve()):
            raise HTTPException(status_code=404, detail="Asset not found or access denied")
            
        return FileResponse(full_asset_path)
    except HTTPException:
        # Re-raise HTTPExceptions para manter o status code correto (404, 400, etc)
        raise
    except Exception as e:
        logger.error(f"Error serving asset '{asset_path}' for project '{project_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error serving asset: {e}")
