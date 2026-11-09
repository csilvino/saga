"""
Script para gerar arquivos de imagem e áudio de placeholder para o projeto de demonstração.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import os
from typing import Optional

# Importa os módulos de IA do editor
import sys
sys.path.append(str(Path(__file__).parent.parent)) # Adiciona a raiz do projeto ao sys.path
from editor.ai_core import AICore
from editor.settings_manager import SettingsManager

# Define o diretório base do projeto de demonstração
DEMO_PROJECT_PATH = Path(__file__).parent.parent / "projects" / "demo"

def create_placeholder_image(filepath: Path, width: int, height: int, color: str, text: str = ""):
    """Cria uma imagem PNG de placeholder com a cor e texto especificados."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new('RGBA', (width, height), color)
    
    if text:
        try:
            # Tenta carregar uma fonte padrão, ou usa a default
            font_path = "arial.ttf" # Fonte comum no Windows
            font_size = int(min(width, height) / 5)
            try:
                font = ImageFont.truetype(font_path, font_size)
            except IOError:
                font = ImageFont.load_default(font_size) # Fallback para fonte default
            
            draw = ImageDraw.Draw(img)
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            text_x = (width - text_width) / 2
            text_y = (height - text_height) / 2
            draw.text((text_x, text_y), text, font=font, fill=(0, 0, 0, 255)) # Texto preto
        except Exception as e:
            print(f"Aviso: Erro ao adicionar texto à imagem {filepath}: {e}. Imagem criada sem texto.")
    
    img.save(filepath)
    print(f"Criado placeholder: {filepath} ({width}x{height}, {color})")

def create_placeholder_audio(filepath: Path):
    """Cria um arquivo MP3 de placeholder vazio."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Um cabeçalho MP3 mínimo para evitar alguns erros, mas ainda não é um MP3 válido
        with open(filepath, "wb") as f:
            f.write(b'\xFF\xFB\x90\x44\x00\x00\x00\x00') 
        print(f"Criado placeholder de áudio (vazio): {filepath}")
    except Exception as e:
        print(f"Erro ao criar placeholder de áudio: {e}")

def generate_all_placeholders_with_ai_prompts():
    """
    Gera todos os arquivos de placeholder necessários e prompts de IA para assets reais.
    """
    print("Gerando assets de placeholder e prompts de IA para o projeto de demonstração...")

    ai_core = AICore()
    settings_manager = SettingsManager()
    gemini_key = settings_manager.get_api_key("gemini")
    if gemini_key:
        ai_core.configure_provider("gemini", gemini_key)
    
    if not ai_core.is_provider_configured("gemini"):
        print("\nAviso: Gemini API não configurada. Não será possível gerar prompts de IA detalhados.")
        print("Criei apenas placeholders simples. Configure sua chave Gemini nas Settings do Editor.")

    # --- Backgrounds ---
    print("\n--- Backgrounds ---")
    bg_room_path = DEMO_PROJECT_PATH / "bg" / "room.png"
    bg_scene2_path = DEMO_PROJECT_PATH / "bg" / "scene2.png"

    room_prompt = "Crie uma imagem de fundo para uma sala principal de uma mansão antiga, com lareira e janelas grandes. Estilo: pintura a óleo."
    scene2_prompt = "Crie uma imagem de fundo para uma segunda sala, mais escura e misteriosa, com teias de aranha e móveis cobertos. Estilo: gótico."

    if ai_core.is_provider_configured("gemini"):
        print(f"\nPrompt IA para '{bg_room_path.name}':")
        print(ai_core.generate_text(f"Gere um prompt detalhado para uma IA de imagem para: {room_prompt}"))
        print(f"\nPrompt IA para '{bg_scene2_path.name}':")
        print(ai_core.generate_text(f"Gere um prompt detalhado para uma IA de imagem para: {scene2_prompt}"))
    
    create_placeholder_image(bg_room_path, 1280, 720, "lightgray", "Sala Principal")
    create_placeholder_image(bg_scene2_path, 1280, 720, "darkgray", "Segunda Sala")

    # --- Sprites ---
    print("\n--- Sprites ---")
    hero_path = DEMO_PROJECT_PATH / "sprites" / "hero.png"
    hero_prompt = "Crie um sprite de personagem principal para um jogo de aventura, estilo detetive, com chapéu e capa. Estilo: pixel art."

    if ai_core.is_provider_configured("gemini"):
        print(f"\nPrompt IA para '{hero_path.name}':")
        print(ai_core.generate_text(f"Gere um prompt detalhado para uma IA de imagem para: {hero_prompt}"))
    
    create_placeholder_image(hero_path, 64, 64, "red", "Hero")

    # --- Items ---
    print("\n--- Items ---")
    key_path = DEMO_PROJECT_PATH / "items" / "key_01.png"
    galho_path = DEMO_PROJECT_PATH / "items" / "galho.png"
    pano_path = DEMO_PROJECT_PATH / "items" / "pano.png"
    tocha_path = DEMO_PROJECT_PATH / "items" / "tocha.png"

    key_prompt = "Crie um ícone de item para uma chave antiga e enferrujada."
    galho_prompt = "Crie um ícone de item para um galho seco e quebrado."
    pano_prompt = "Crie um ícone de item para um pedaço de pano sujo."
    tocha_prompt = "Crie um ícone de item para uma tocha acesa, feita de galho e pano."

    if ai_core.is_provider_configured("gemini"):
        print(f"\nPrompt IA para '{key_path.name}':")
        print(ai_core.generate_text(f"Gere um prompt detalhado para uma IA de imagem para: {key_prompt}"))
        print(f"\nPrompt IA para '{galho_path.name}':")
        print(ai_core.generate_text(f"Gere um prompt detalhado para uma IA de imagem para: {galho_prompt}"))
        print(f"\nPrompt IA para '{pano_path.name}':")
        print(ai_core.generate_text(f"Gere um prompt detalhado para uma IA de imagem para: {pano_prompt}"))
        print(f"\nPrompt IA para '{tocha_path.name}':")
        print(ai_core.generate_text(f"Gere um prompt detalhado para uma IA de imagem para: {tocha_prompt}"))

    create_placeholder_image(key_path, 32, 32, "yellow", "Key")
    create_placeholder_image(galho_path, 32, 32, "brown", "Branch")
    create_placeholder_image(pano_path, 32, 32, "white", "Cloth")
    create_placeholder_image(tocha_path, 32, 32, "orange", "Torch")

    # --- Audio ---
    print("\n--- Audio ---")
    ambience_path = DEMO_PROJECT_PATH / "audio" / "ambience.mp3"
    ambience_prompt = "Crie um som ambiente de floresta tropical com pássaros e insetos para um jogo de aventura."

    if ai_core.is_provider_configured("gemini"):
        print(f"\nPrompt IA para '{ambience_path.name}':")
        print(ai_core.generate_text(f"Gere um prompt detalhado para uma IA de áudio para: {ambience_prompt}"))
    
    create_placeholder_audio(ambience_path)

    print("\n--- Geração de Assets Concluída ---")
    print("1. Arquivos de placeholder foram criados nos diretórios do projeto de demonstração.")
    print("2. Se a Gemini API estiver configurada, prompts detalhados foram gerados acima.")
    print("3. Use esses prompts em uma IA de geração de imagem/áudio (ex: DALL-E, Midjourney, MusicGen) para criar assets reais.")
    print("4. Salve os assets gerados nos caminhos indicados (substituindo os placeholders).")
    print("5. Depois, você poderá testar o demo no Runtime e no Editor.")

if __name__ == '__main__':
    generate_all_placeholders_with_ai_prompts()
