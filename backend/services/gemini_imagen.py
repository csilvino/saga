# Corrigindo o padrão de uso para 'google.genai' conforme o exemplo do usuário.
from google import genai
from google.genai import types
from PIL import Image
import numpy as np
import json
import re
import os
import time
import uuid
import io
import logging

# Importa a configuração centralizada do modelo
from backend.config.user_settings import get_gemini_model, get_generation_source, get_image_model
from backend.services.local_image_generator import local_image_service

class GeminiImagenExtractor:
    """
    Extrator de sprites de alta fidelidade, editor de imagens e gerador usando a API google.genai.
    """
    
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API Key do Gemini é obrigatória")
        
        try:
            self.client = genai.Client(api_key=api_key)
            self.model_name = get_gemini_model()
            # O modelo de edição de imagem pode ser diferente, vamos usar o recomendado.
            self.edit_model_name = get_image_model()
            logging.info(f"GeminiImagenExtractor inicializado. Modelo de análise: {self.model_name}, Modelo de edição: {self.edit_model_name}.")

        except Exception as e:
            logging.error(f"Erro inesperado ao inicializar o GeminiImagenExtractor com genai.Client: {e}", exc_info=True)
            raise

    def generate_image(self, prompt: str, negative_prompt: str = None, width: int = 1024, height: int = 1024, reference_image_path: str = None) -> Image.Image:
        """
        Gera uma imagem completa.
        Suporta 'Image Prompting' se reference_image_path for fornecido (apenas para modelos Gemini Multimodais).
        """
        try:
            model_id = get_image_model()
            logging.info(f"Iniciando geração de imagem Cloud. Modelo: {model_id}")
            logging.info(f"Prompt: {prompt[:100]}...")
            
            reference_image = None
            if reference_image_path:
                if os.path.exists(reference_image_path):
                    logging.info(f"Carregando imagem de referência: {reference_image_path}")
                    reference_image = Image.open(reference_image_path)
                else:
                    logging.warning(f"Imagem de referência não encontrada: {reference_image_path}")

            # Lógica de decisão baseada no nome do modelo
            if "imagen" in model_id.lower():
                # Imagen não suporta image prompt da mesma forma que o Gemini Multimodal (ainda)
                if reference_image:
                    logging.warning("Modelo Imagen detectado. A imagem de referência será ignorada (suporte apenas no Gemini Multimodal).")
                return self._generate_with_imagen_endpoint(model_id, prompt, width, height)
            else:
                return self._generate_with_gemini_multimodal(model_id, prompt, width, height, reference_image)

        except Exception as e:
            logging.error(f"Erro na geração de imagem Cloud: {e}", exc_info=True)
            raise

    def _generate_with_imagen_endpoint(self, model_id, prompt, width, height):
        """Usa o endpoint dedicado para modelos Imagen."""
        logging.info("Usando endpoint 'generate_images' (Imagen).")
        
        # Mapeamento de aspect ratio
        ratio = width / height
        if 0.9 <= ratio <= 1.1: aspect_ratio = "1:1"
        elif ratio > 1.5: aspect_ratio = "16:9"
        elif ratio < 0.6: aspect_ratio = "9:16"
        else: aspect_ratio = "4:3" if width >= height else "3:4"

        response = self.client.models.generate_images(
            model=model_id,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=aspect_ratio
            )
        )
        
        if response.generated_images:
            image_bytes = response.generated_images[0].image.image_bytes
            return Image.open(io.BytesIO(image_bytes))
        
        raise Exception("API Imagen retornou sucesso mas sem imagens.")

    def _generate_with_gemini_multimodal(self, model_id, prompt, width, height, reference_image=None):
        """Usa o endpoint 'generate_content' para modelos Gemini Multimodais (ex: gemini-2.5-flash-image)."""
        logging.info("Usando endpoint 'generate_content' (Gemini Multimodal).")
        
        contents = [prompt]
        
        if reference_image:
            logging.info("Anexando imagem de referência ao prompt.")
            contents.append(reference_image)
            # Reforça o prompt para usar a imagem
            contents[0] = f"Generate a new image based on the visual style of the attached reference image. Description of the new scene: {prompt}"
        else:
            contents[0] = f"Generate an image based on this description: {prompt}"
        
        # CORREÇÃO: Removido response_mime_type, pois não é suportado para output de imagem em generate_content.
        # O modelo multimodal deve retornar a imagem diretamente nas partes do conteúdo.
        response = self.client.models.generate_content(
            model=model_id,
            contents=contents
        )
        
        # Procura por partes de imagem na resposta
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    logging.info("Imagem encontrada em inline_data.")
                    return Image.open(io.BytesIO(part.inline_data.data))

        raise Exception("O modelo Gemini não retornou dados de imagem válidos na resposta.")

    def analyze_image(self, image_pil: Image.Image, prompt: str) -> str:
        """
        Analisa uma imagem usando o Gemini Vision e retorna uma descrição textual.
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt, image_pil]
            )
            return response.text
        except Exception as e:
            logging.error(f"Erro ao analisar imagem com Gemini: {e}", exc_info=True)
            return f"Erro na análise da imagem: {str(e)}"

    def remove_object(self, image_pil: Image.Image, object_name: str, bbox: list) -> Image.Image | None:
        """
        Remove um objeto de uma imagem usando a funcionalidade de inpainting do Gemini.
        """
        prompt = f"Da imagem fornecida, remova apenas o objeto '{object_name}' localizado na área aproximada da bounding box. Preencha o fundo de forma realista, mantendo o estilo e a iluminação do restante da cena. Não altere nada fora da área do objeto."
        
        try:
            # A API de edição de imagem espera o prompt e a imagem como 'contents'
            response = self.client.models.generate_content(
                model=self.edit_model_name,
                contents=[prompt, image_pil]
            )
            
            # A imagem gerada vem em 'response.parts'
            for part in response.parts:
                if part.inline_data:
                    # Retorna a primeira imagem encontrada
                    return part.as_image()
            
            logging.warning("A resposta da API de edição de imagem não continha uma imagem.")
            return None

        except Exception as e:
            logging.error(f"Erro na remoção de objeto com Gemini: {e}", exc_info=True)
            return None

    def extract_sprite(self, scene_image_pil, bbox, object_name):
        """
        Pipeline principal: Crop -> Describe -> Generate -> Remove Background
        """
        cropped = self._crop_object(scene_image_pil, bbox)
        description = self._analyze_with_gemini(cropped, object_name)
        
        if not description:
            logging.warning("Falha na análise do Gemini.")
            raise Exception("A análise do Gemini não retornou uma descrição válida.")
        
        generated_sprite = self._generate_with_gemini(description, cropped)
        
        if not generated_sprite:
            logging.warning("Falha na geração do Gemini.")
            raise Exception("A geração da imagem com Gemini falhou.")
        
        final_sprite = self._convert_to_transparent(generated_sprite)
        return final_sprite
    
    def _crop_object(self, image_pil, bbox):
        """Recorta objeto com margem de 30% para dar contexto à IA"""
        if isinstance(bbox, dict):
            x1, y1, x2, y2 = bbox['xmin'], bbox['ymin'], bbox['xmax'], bbox['ymax']
        elif isinstance(bbox, list):
            x1, y1, x2, y2 = bbox
        else:
            return image_pil

        width, height = x2 - x1, y2 - y1
        margin_x, margin_y = width * 0.3, height * 0.3
        
        crop_box = (max(0, int(x1 - margin_x)), max(0, int(y1 - margin_y)), min(image_pil.width, int(x2 + margin_x)), min(image_pil.height, int(y2 + margin_y)))
        return image_pil.crop(crop_box)
    
    def _analyze_with_gemini(self, cropped_image, object_name):
        """
        Usa o modelo Gemini configurado para criar um prompt perfeito para a geração
        """
        prompt = f"""
        Atue como um especialista em Prompt Engineering para IA generativa de imagens.
        Analise este recorte de imagem que contém um(a) "{object_name}".
        Sua tarefa é criar uma descrição visual EXTREMAMENTE DETALHADA para recriar este objeto.
        Foque em:
        1. Estilo artístico exato (cartoon, realista, pixel art, etc).
        2. Materiais, texturas e iluminação.
        3. Cores exatas.
        4. Detalhes únicos (arranhões, padrões, ornamentos).
        5. Perspectiva (frontal, isométrica, etc).
        Retorne APENAS um JSON com este formato:
        {{
            "style": "estilo artístico",
            "detailed_prompt": "descrição completa e densa para o gerador de imagem"
        }}
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt, cropped_image]
            )
            text = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(text)
        except Exception as e:
            logging.error(f"Erro Gemini (Análise) com o novo client: {e}")
            return None
    
    def _generate_with_gemini(self, description, original_crop):
        """
        Usa Gemini ou SANA (Local) para gerar o sprite isolado.
        """
        source = get_generation_source()

        if source == 'local':
            logging.info("Usando gerador local SANA.")
            try:
                # Combina o estilo e o prompt detalhado
                full_prompt = f"{description['style']}, {description['detailed_prompt']}, white background, high quality, 4k"
                # CORREÇÃO: Chamada atualizada para o novo serviço
                generated_image = local_image_service.generate_image(full_prompt)
                return generated_image
            except Exception as e:
                logging.error(f"Erro ao gerar com SANA: {e}")
                # Fallback para RemBG se falhar
                logging.info("Fallback para RemBG após erro no SANA.")
                from rembg import remove
                return remove(original_crop)
        else:
            # Se estiver em Cloud, tentamos usar o Imagen 3 para gerar o sprite
            logging.info("Usando Imagen 3 (Cloud) para gerar sprite.")
            try:
                full_prompt = f"{description['style']}, {description['detailed_prompt']}, white background, isolated object"
                return self.generate_image(full_prompt, width=1024, height=1024)
            except Exception as e:
                logging.error(f"Erro ao gerar com Imagen 3: {e}")
                logging.info("Fallback para RemBG.")
                from rembg import remove
                return remove(original_crop)
    
    def _convert_to_transparent(self, image_pil):
        """
        Garante que a imagem esteja em RGBA e remove bordas vazias.
        Se a imagem gerada não for transparente (ex: SANA gera fundo branco/preto), remove o fundo.
        """
        if image_pil is None:
            return None

        img_rgba = image_pil.convert('RGBA')

        # Se a imagem não tiver transparência (ex: gerada pelo SANA), removemos o fundo agora
        # Verificamos se há pixels transparentes. Se alpha channel for todo 255, precisa remover fundo.
        extrema = img_rgba.getextrema()
        if extrema[3][0] == 255: # Canal Alpha mínimo é 255 (opaco)
             logging.info("Imagem gerada é opaca. Removendo fundo com RemBG...")
             from rembg import remove
             img_rgba = remove(img_rgba)

        # Autocrop (remove espaço vazio transparente)
        bbox = img_rgba.getbbox()
        if bbox:
            return img_rgba.crop(bbox)
        return img_rgba