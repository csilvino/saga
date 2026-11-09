from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import uuid
import traceback
from PIL import Image
from backend.services.project_service import project_service
from backend.services.gemini_imagen import GeminiImagenExtractor
from backend.services.animation_service import animation_service # Importado
from backend.config.user_settings import get_gemini_key, get_generation_source

router = APIRouter(prefix="/api/genai", tags=["genai"])

class HighQualityExtractRequest(BaseModel):
    project_name: str
    scene_id: str
    object_name: str
    bbox: list # [x1, y1, x2, y2]

class GenerateVariationRequest(BaseModel):
    project_name: str
    sprite_path: str
    prompt: str

class AnimateObjectRequest(BaseModel):
    project_name: str
    object_id: str
    description: str
    frame_count: int = 3

@router.post("/animate-object")
async def animate_object(request: AnimateObjectRequest):
    """
    Gera um sprite sheet animado para um objeto existente.
    """
    try:
        result = animation_service.generate_animation_sheet(
            project_name=request.project_name,
            object_id=request.object_id,
            animation_description=request.description,
            frame_count=request.frame_count
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Erro ao animar objeto: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro interno ao animar objeto: {str(e)}")

@router.post("/extract-high-quality")
async def extract_high_quality(request: HighQualityExtractRequest):
    api_key = get_gemini_key()
    if not api_key:
        raise HTTPException(status_code=400, detail="Chave Gemini não configurada.")
    
    try:
        # 1. Carregar dados do projeto e da cena
        project_data = project_service.load_project(request.project_name)
        project_path = project_service.load_project_path(request.project_name)

        scene = project_data.get("scenes", {}).get(request.scene_id)
        if not scene:
            raise HTTPException(status_code=404, detail=f"Cena '{request.scene_id}' não encontrada.")

        background_filename = scene.get("background")
        if not background_filename:
            raise HTTPException(status_code=400, detail="A cena não tem imagem de fundo.")

        # Limpa o nome do arquivo de parâmetros (ex: ?v=123)
        background_path_str = background_filename.split('?')[0]

        # Constrói o caminho absoluto para a imagem
        scene_path = (project_path / background_path_str).resolve()

        if not scene_path.exists():
            raise HTTPException(status_code=404, detail=f"Arquivo de imagem '{background_path_str}' não encontrado.")
        
        scene_image = Image.open(scene_path)
        
        # 2. Inicializar Extrator
        try:
            extractor = GeminiImagenExtractor(api_key)
        except Exception as e:
            print(f"Erro ao inicializar GeminiImagenExtractor: {e}")
            raise HTTPException(status_code=500, detail=f"Erro ao inicializar IA: {str(e)}")

        # 3. Executar Pipeline
        final_sprite = extractor.extract_sprite(
            scene_image,
            request.bbox,
            request.object_name
        )

        if not final_sprite:
            raise HTTPException(status_code=500, detail="A IA não conseguiu gerar o sprite. Verifique os logs do servidor.")
        
        # 4. Salvar
        sprites_dir = project_path / "sprites"
        sprites_dir.mkdir(exist_ok=True)
        
        safe_name = "".join(c for c in request.object_name if c.isalnum() or c in " _-").rstrip()
        filename = f"{safe_name}_hq_{uuid.uuid4().hex[:6]}.png"
        save_path = sprites_dir / filename
        
        final_sprite.save(save_path, format="PNG")
        
        source = get_generation_source()
        method_name = "SANA (Local GPU)" if source == 'local' else "Gemini 2.5 + Imagen 3"

        return {
            "success": True,
            "sprite_url": f"sprites/{filename}",
            "method": method_name
        }
        
    except HTTPException as e:
        # Re-raise HTTP exceptions para que o FastAPI as manipule
        raise e
    except Exception as e:
        print(f"Erro GenAI não tratado: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro interno no servidor: {str(e)}")

@router.post("/generate-variation")
async def generate_variation(request: GenerateVariationRequest):
    api_key = get_gemini_key()
    if not api_key:
        raise HTTPException(status_code=400, detail="Chave Gemini não configurada.")

    try:
        project_path = project_service.load_project_path(request.project_name)
        # Remove potential leading slashes or 'sprites/' prefix if duplicated
        clean_sprite_path = request.sprite_path.lstrip('/')
        sprite_full_path = (project_path / clean_sprite_path).resolve()

        if not sprite_full_path.exists():
            # Try prepending 'sprites/' if not found
            sprite_full_path = (project_path / "sprites" / clean_sprite_path).resolve()

        if not sprite_full_path.exists():
            raise HTTPException(status_code=404, detail=f"Sprite original não encontrado: {request.sprite_path}")

        original_sprite = Image.open(sprite_full_path)

        extractor = GeminiImagenExtractor(api_key)

        # 1. Analisar o sprite original para obter uma descrição base
        description_obj = extractor._analyze_with_gemini(original_sprite, "o objeto na imagem")
        if not description_obj:
            raise HTTPException(status_code=500, detail="Falha ao analisar o sprite original com Gemini.")

        # 2. Modificar o prompt com a instrução do usuário
        # Adicionamos a modificação do usuário ao prompt detalhado
        description_obj["detailed_prompt"] += f". MODIFICATION: {request.prompt}. Ensure the object maintains its original style and perspective."

        # 3. Gerar a nova imagem (usando o método simulado ou real se disponível)
        # Nota: Como o método _generate_with_gemini atual é um placeholder que retorna None ou usa RemBG,
        # precisamos garantir que ele tente gerar algo novo.
        # Se o método _generate_with_gemini retornar None (porque Imagen 3 não está disponível),
        # não temos como gerar a variação.

        # Tentar gerar
        new_sprite_raw = extractor._generate_with_gemini(description_obj, original_sprite)

        if not new_sprite_raw:
             # Se o método padrão falhar (ex: API não disponível), não podemos fazer nada por enquanto
             # a menos que implementemos um fallback de edição de imagem real.
             raise HTTPException(status_code=501, detail="A geração de variações requer acesso à API Imagen 3, que não está disponível nesta configuração.")

        # 4. Remover fundo (garantir transparência)
        final_sprite = extractor._convert_to_transparent(new_sprite_raw)

        # 5. Salvar o novo sprite
        sprites_dir = project_path / "sprites"
        sprites_dir.mkdir(exist_ok=True)

        base_name = os.path.splitext(os.path.basename(request.sprite_path))[0]
        # Limpar o prompt para usar no nome do arquivo
        safe_prompt = "".join(c for c in request.prompt if c.isalnum()).lower()[:15]
        filename = f"{base_name}_var_{safe_prompt}_{uuid.uuid4().hex[:4]}.png"
        save_path = sprites_dir / filename

        final_sprite.save(save_path, format="PNG")

        return {
            "success": True,
            "sprite_url": f"sprites/{filename}",
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Erro na geração de variação: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro interno ao gerar variação: {str(e)}")
