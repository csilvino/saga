"""
Módulo de Gerenciamento de Áudio para a Saga Engine.
"""
from __future__ import annotations
import arcade
from pathlib import Path
from typing import Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from runtime.data_models import Project

class AudioManager:
    """
    Gerencia o carregamento e a reprodução de áudio (músicas e efeitos sonoros).
    """
    def __init__(self, project: Project):
        self.project = project
        self.project_path = Path(project.project_path)
        self.sounds: Dict[str, arcade.Sound] = {}
        self.music_player: Optional[arcade.MediaPlayer] = None
        self.current_music: Optional[arcade.Sound] = None

        self._load_audio_assets()

    def _load_audio_assets(self):
        """
        Carrega todos os assets de áudio definidos no projeto.
        """
        print("Carregando assets de áudio...")
        for audio_id, audio_asset in self.project.assets.audio.items():
            audio_path = self.project_path / audio_asset.path
            if audio_path.exists():
                try:
                    # Reverting to use arcade.load_sound for all audio assets
                    sound = arcade.load_sound(str(audio_path))
                    self.sounds[audio_id] = sound
                    print(f"  - Áudio '{audio_id}' carregado de '{audio_path}'")
                except Exception as e:
                    print(f"Erro ao carregar áudio '{audio_id}': {e}")
            else:
                print(f"Aviso: Arquivo de áudio não encontrado em '{audio_path}'")

    def play_sound(self, sound_id: str):
        """
        Reproduz um efeito sonoro.
        """
        sound = self.sounds.get(sound_id)
        if sound:
            arcade.play_sound(sound)
        else:
            print(f"Aviso: Efeito sonoro '{sound_id}' não encontrado.")

    def play_music(self, music_id: str, loop: bool = True):
        """
        Reproduz uma música de fundo. Para a música anterior se estiver tocando.
        """
        music = self.sounds.get(music_id)
        if not music:
            print(f"Aviso: Música '{music_id}' não encontrada.")
            return

        if self.current_music == music:
            print(f"Música '{music_id}' já está tocando.")
            return

        if self.music_player:
            self.stop_music()

        print(f"Tocando música: {music_id}")
        self.current_music = music
        self.music_player = self.current_music.play(loop=loop)

    def stop_music(self):
        """
        Para a música que está tocando.
        """
        if self.music_player:
            print("Parando música.")
            self.current_music.stop(self.music_player)
            self.music_player = None
            self.current_music = None
