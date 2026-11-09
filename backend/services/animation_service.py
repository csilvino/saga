import logging
from PIL import Image
import io
import uuid
from pathlib import Path
from google import genai
from google.genai import types

from backend.config.user_settings import get_gemini_key, get_image_model
from backend.services.project_service import project_service

logger = logging.getLogger(__name__)

class AnimationService:
    def __init__(self):
        pass

    def generate_animation_sheet(self, project_name: str, object_id: str, animation_description: str, frame_count: int = 3) -> dict:
        """
        Gera um sprite sheet animado para um objeto existente usando o Gemini.
        """
        api_key = get_gemini_key()
        if not api_key:
            raise ValueError("Chave da API Gemini não configurada.")

        # 1. Carregar o objeto e seu sprite original
        project = project_service.load_project(project_name)
        
        target_obj = None
        scene_id = None
        
        # Busca o objeto em todas as cenas
        for s_id, scene in project.get("scenes", {}).items():
            for obj in scene.get("objects", []):
                if obj["id"] == object_id:
                    target_obj = obj
                    scene_id = s_id
                    break
            if target_obj: break
        
        if not target_obj:
            raise ValueError(f"Objeto {object_id} não encontrado.")
            
        sprite_path = target_obj.get("sprite")
        if not sprite_path:
            raise ValueError(f"O objeto {target_obj['name']} não tem um sprite base para animar.")

        full_sprite_path = project_service.load_project_path(project_name) / sprite_path
        if not full_sprite_path.exists():
             raise ValueError(f"Arquivo de sprite não encontrado: {sprite_path}")

        original_image = Image.open(full_sprite_path)

        # 2. Preparar o Prompt para o Gemini
        prompt = f"""
        You are a game asset generator.
        I will provide an image of a game object.
        Create a sprite sheet containing exactly {frame_count} frames of this object animated horizontally.
        
        Animation Description: {animation_description}
        
        Requirements:
        1. The output image must contain {frame_count} variations of the object side-by-side.
        2. Maintain the EXACT same art style, colors, and proportions as the original image.
        3. The background must be transparent (or solid white if transparency is not possible).
        4. The frames should be evenly spaced.
        5. Do not add any text or grid lines. Just the objects.
        
        Input Image: Attached.
        """

        client = genai.Client(api_key=api_key)
        model_id = get_image_model()

        logger.info(f"Gerando animação '{animation_description}' para {target_obj['name']} com {frame_count} frames...")

        try:
            # CORREÇÃO: Removido response_mime_type="image/png" pois causa erro 400 no modelo multimodal
            response = client.models.generate_content(
                model=model_id,
                contents=[prompt, original_image]
            )
            
            generated_image = None
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.data:
                        generated_image = Image.open(io.BytesIO(part.inline_data.data))
                        break
            
            if not generated_image:
                raise RuntimeError("O Gemini não retornou uma imagem válida.")

            # 3. Processamento (SEMPRE remover fundo para garantir transparência)
            if generated_image.mode != 'RGBA':
                generated_image = generated_image.convert('RGBA')
            
            from rembg import remove
            logger.info("Removendo fundo do sprite sheet gerado...")
            generated_image = remove(generated_image)

            # 4. Fatiar a Imagem em Frames e Salvar como WebP Animado
            total_width, total_height = generated_image.size
            frame_width = total_width // frame_count
            
            frames = []
            for i in range(frame_count):
                # crop(left, upper, right, lower)
                box = (i * frame_width, 0, (i + 1) * frame_width, total_height)
                frame = generated_image.crop(box)
                frames.append(frame)
                
            sprites_dir = project_service.load_project_path(project_name) / "sprites"
            filename = f"{target_obj['name']}_anim_{uuid.uuid4().hex[:6]}.webp"
            save_path = sprites_dir / filename
            
            # Cálculo de duração do frame (ms). Base padrão: 4 fps = 250ms por frame
            # Se a IA sugerir algo rápido no prompt, nós poderíamos adaptar, mas manteremos o padrão FPS do WebP
            fps = 8 # Padrão mais suave para gifs
            duration_ms = int(1000 / fps)
            
            # Se 'loop' estiver na descrição, a animação não para
            is_loop = False
            if "loop" in animation_description.lower() or "ciclo" in animation_description.lower() or "balanç" in animation_description.lower():
                is_loop = True
            
            # Salvar como WebP animado
            frames[0].save(
                save_path,
                format="WEBP",
                save_all=True,
                append_images=frames[1:],
                duration=duration_ms,
                loop=0 if is_loop else 1,
                background=(0, 0, 0, 0)
            )
            
            relative_path = f"sprites/{filename}"

            # 5. Atualizar o Objeto no Projeto
            target_obj["sprite"] = relative_path
            
            # Como é um WebP, o tamanho físico do sprite agora é exatamente o tamanho de UM frame
            target_obj["size"] = {
                "width": frame_width,
                "height": total_height
            }
            
            # Sinaliza pro Frontend que ele não precisa mais fatiar isso no CSS
            target_obj["animation"] = {
                "type": "animated_webp",
                "frameCount": frame_count,
                "fps": fps,
                "loop": is_loop
            }

            project_service.save_project_data(project_name, project)

            return {
                "success": True,
                "message": f"Animação criada com sucesso para {target_obj['name']}.",
                "sprite_path": relative_path,
                "animation_config": target_obj["animation"]
            }

        except Exception as e:
            logger.error(f"Erro ao gerar animação: {e}", exc_info=True)
            raise

animation_service = AnimationService()
