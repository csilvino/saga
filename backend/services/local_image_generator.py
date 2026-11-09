import torch
import logging
from PIL import Image
from backend.config.user_settings import get_local_model_id

logger = logging.getLogger(__name__)

class LocalImageGenerator:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LocalImageGenerator, cls).__new__(cls)
            cls._instance.pipe = None
            cls._instance.device = "cuda" if torch.cuda.is_available() else "cpu"
        return cls._instance

    def _load_model(self):
        if self.pipe is not None:
            return

        try:
            from diffusers import StableDiffusionXLPipeline
            
            model_id = get_local_model_id()
            logger.info(f"Carregando modelo local SSD-1B ({model_id}) no dispositivo: {self.device}...")

            dtype = torch.float16 if self.device == "cuda" else torch.float32
            
            self.pipe = StableDiffusionXLPipeline.from_pretrained(
                model_id,
                torch_dtype=dtype,
                use_safetensors=True
            )
            
            if self.device == "cuda":
                # Otimizações críticas para VRAM limitada (já que o usuário roda LLM 14B)
                self.pipe.enable_model_cpu_offload()
                self.pipe.enable_vae_slicing()
                self.pipe.enable_vae_tiling()
            else:
                self.pipe.to("cpu")
                
            logger.info("Modelo local carregado com sucesso.")
            
        except Exception as e:
            logger.error(f"Erro fatal ao carregar modelo local: {e}")
            self.pipe = None
            raise

    def generate_image(self, prompt: str, negative_prompt: str = "", width: int = 1024, height: int = 1024) -> Image.Image:
        """
        Gera uma imagem usando o modelo local (SSD-1B).
        """
        self._load_model()
        
        if self.pipe is None:
            raise RuntimeError("Modelo de imagem local não pôde ser carregado.")

        logger.info(f"Gerando imagem localmente... Prompt: {prompt[:50]}...")
        
        # Parâmetros otimizados para velocidade/qualidade
        steps = 20
        guidance = 7.0
        
        try:
            result = self.pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                height=height,
                width=width,
                num_inference_steps=steps,
                guidance_scale=guidance
            ).images[0]
            
            return result
            
        except Exception as e:
            logger.error(f"Erro durante inferência local: {e}")
            raise

# Singleton para uso global
local_image_service = LocalImageGenerator()
