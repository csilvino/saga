import React, { useEffect, useState } from 'react';
import { Play, Settings, X, Volume2, VolumeX } from 'lucide-react';
import type { Project } from '../types';
import { getAssetUrl } from '../services/api';

interface GameLauncherProps {
  project: Project;
  onStartGame: () => void;
  onClose: () => void;
}

const GameLauncher: React.FC<GameLauncherProps> = ({ project, onStartGame, onClose }) => {
  const [isMuted, setIsMuted] = useState(false);
  const [audio, setAudio] = useState<HTMLAudioElement | null>(null);

  const launcherConfig = project.launcher || {
    title: project.name,
    description: "Um jogo criado com Saga Engine",
    flyer_image: "",
    launcher_music: "",
    version: "1.0.0"
  };

  const flyerUrl = launcherConfig.flyer_image ? getAssetUrl(project.name, launcherConfig.flyer_image) : null;
  const musicUrl = launcherConfig.launcher_music ? getAssetUrl(project.name, launcherConfig.launcher_music) : null;

  useEffect(() => {
    if (musicUrl) {
      const newAudio = new Audio(musicUrl);
      newAudio.loop = true;
      newAudio.volume = 0.5;
      newAudio.play().catch(e => console.log("Autoplay blocked:", e));
      setAudio(newAudio);

      return () => {
        newAudio.pause();
        newAudio.src = "";
      };
    }
  }, [musicUrl]);

  useEffect(() => {
    if (audio) {
      audio.muted = isMuted;
    }
  }, [isMuted, audio]);

  return (
    <div className="fixed inset-0 z-50 bg-black flex items-center justify-center overflow-hidden">
      {/* Background Image / Flyer */}
      {flyerUrl && (
        <div
          className="absolute inset-0 bg-cover bg-center opacity-40"
          style={{ backgroundImage: `url("${flyerUrl}")` }}
        ></div>
      )}

      {/* Overlay Gradient */}
      <div className="absolute inset-0 bg-gradient-to-t from-black via-black/60 to-transparent"></div>

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center justify-center h-full max-w-4xl px-8 text-center animate-fade-in">

        {/* Title */}
        <h1 className="text-6xl md:text-8xl font-black text-transparent bg-clip-text bg-gradient-to-b from-yellow-300 to-yellow-600 mb-4 drop-shadow-lg tracking-tight"
            style={{ fontFamily: 'serif' }}>
          {launcherConfig.title || project.name}
        </h1>

        {/* Version */}
        <div className="text-gray-500 text-sm mb-8 font-mono tracking-widest">
          VERSION {launcherConfig.version || "1.0.0"}
        </div>

        {/* Description */}
        <p className="text-xl text-gray-300 max-w-2xl mb-12 leading-relaxed font-light">
          {launcherConfig.description}
        </p>

        {/* Menu Buttons */}
        <div className="flex flex-col gap-4 w-full max-w-xs">
          <button
            onClick={onStartGame}
            className="group relative px-8 py-4 bg-gradient-to-r from-yellow-600 to-yellow-500 hover:from-yellow-500 hover:to-yellow-400 text-black font-bold text-lg rounded shadow-lg hover:shadow-yellow-500/20 transition-all transform hover:scale-105 active:scale-95 flex items-center justify-center gap-3"
          >
            <Play className="w-6 h-6 fill-black" />
            NOVO JOGO
          </button>

          <button
            disabled
            className="px-8 py-4 bg-gray-800/50 text-gray-500 font-bold text-lg rounded border border-gray-700 cursor-not-allowed flex items-center justify-center gap-3"
          >
            CARREGAR JOGO
          </button>

          <button
            onClick={onClose}
            className="px-8 py-4 bg-transparent hover:bg-white/10 text-white font-bold text-lg rounded border border-white/20 transition-colors flex items-center justify-center gap-3"
          >
            <X className="w-6 h-6" />
            SAIR
          </button>
        </div>
      </div>

      {/* Footer Controls */}
      <div className="absolute bottom-8 right-8 flex gap-4">
        <button
          onClick={() => setIsMuted(!isMuted)}
          className="p-3 bg-black/50 hover:bg-black/80 text-white rounded-full backdrop-blur-sm transition-colors"
        >
          {isMuted ? <VolumeX className="w-6 h-6" /> : <Volume2 className="w-6 h-6" />}
        </button>
      </div>
    </div>
  );
};

export default GameLauncher;
