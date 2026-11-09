// GamePlayer Component - Saga Engine
import React, { useState, useEffect, useRef } from 'react';
import { Play, X, Package, MapPin, Volume2, VolumeX, Maximize2, Minimize2, Send, Type, Notebook } from 'lucide-react';
import type { Project, Scene, GameObject } from '../types';
import api, { getAssetUrl } from '../services/api';
import { useResizable, useRightResizable } from '../hooks';
import { ResizeHandle } from './ui';
import GameLauncher from './GameLauncher';

interface GamePlayerProps {
  project: Project;
  initialSceneId: string;
  onClose: () => void;
}

// Componente para renderizar objetos animados ou estáticos
const AnimatedObject = ({ obj, projectName, onClick }: { obj: GameObject, projectName: string, onClick: () => void }) => {
  const [currentFrame, setCurrentFrame] = useState(0);
  const spriteUrl = getAssetUrl(projectName, obj.sprite);

  useEffect(() => {
    if (obj.animation?.type === 'sprite_sheet') {
      const { fps, frameCount, loop } = obj.animation;
      // Only set up interval if there's an animation to play
      if (frameCount > 1) {
        const interval = setInterval(() => {
          setCurrentFrame(prev => {
            const next = prev + 1;
            if (next >= frameCount) return loop ? 0 : prev;
            return next;
          });
        }, 1000 / fps);
        return () => clearInterval(interval);
      }
    }
  }, [obj.animation]);

  // Correctly calculate position based on the object's center
  const width = (obj.size.width / 1920) * 100;
  const height = (obj.size.height / 1080) * 100;
  const left = ((obj.position.x - obj.size.width / 2) / 1920) * 100;
  const top = ((obj.position.y - obj.size.height / 2) / 1080) * 100;

  // Estilo base
  const style: React.CSSProperties = {
    left: `${left}%`,
    top: `${top}%`,
    width: `${width}%`,
    height: `${height}%`,
    position: 'absolute',
    cursor: 'pointer',
    backgroundImage: `url("${spriteUrl}")`,
    backgroundRepeat: 'no-repeat',
  };

  // Ajuste para Sprite Sheet
  if (obj.animation?.type === 'sprite_sheet') {
    const { frameCount } = obj.animation;
    // O tamanho da imagem de fundo é X vezes maior que a div
    style.backgroundSize = `${frameCount * 100}% 100%`;

    // Avoid division by zero if frameCount is 1
    if (frameCount > 1) {
      style.backgroundPosition = `${(currentFrame / (frameCount - 1)) * 100}% 0%`;
    } else {
      style.backgroundPosition = '0% 0%';
    }
  } else {
    style.backgroundSize = 'contain';
    style.backgroundPosition = 'center';
  }

  return (
    <div
      style={style}
      onClick={onClick}
      title={obj.name}
      className="hover:scale-105 transition-transform duration-200 group"
    >
      {/* Tooltip opcional */}
      <div className="text-white text-xs font-bold opacity-0 group-hover:opacity-100 transition-opacity absolute -bottom-6 left-1/2 transform -translate-x-1/2 whitespace-nowrap bg-gray-900 px-2 py-1 rounded z-10 pointer-events-none">
        {obj.name}
      </div>
    </div>
  );
};

const GamePlayer: React.FC<GamePlayerProps> = ({ project, initialSceneId, onClose }) => {
  const [showLauncher, setShowLauncher] = useState(true);
  const [currentSceneId, setCurrentSceneId] = useState(initialSceneId);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [command, setCommand] = useState('');
  const [textLog, setTextLog] = useState<{ text: string; type: string; timestamp: number }[]>([]);
  const [inventory, setInventory] = useState<any[]>([]);
  const [fontSize, setFontSize] = useState(14);

  // Hooks de redimensionamento
  const leftPanel = useResizable(320, 200, 500);
  const rightPanel = useRightResizable(384, 250, 600);

  const inputRef = useRef<HTMLInputElement>(null);
  const logRef = useRef<HTMLDivElement>(null);
  const initialized = useRef(false);

  const currentScene = project.scenes[currentSceneId];

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [textLog, fontSize]);

  useEffect(() => {
    if (!showLauncher && inputRef.current) {
      inputRef.current.focus();
    }
  }, [showLauncher]);

  useEffect(() => {
    if (showLauncher) return; // Don't initialize game logic if launcher is showing
    if (initialized.current) return;
    initialized.current = true;

    addToLog('═══════════════════════════════════════════════════════', 'system');
    addToLog(`      ${project.name.toUpperCase()}`, 'title');
    addToLog('═══════════════════════════════════════════════════════', 'system');
    addToLog('');
    describeScene(currentScene);
  }, [showLauncher]); // Depend on showLauncher to trigger when game starts

  const addToLog = (text: string, type = 'normal') => {
    setTextLog(prev => [...prev, { text, type, timestamp: Date.now() }]);
  };

  const describeScene = (scene: Scene) => {
    if (!scene) return;

    if (scene.description) {
      addToLog(scene.description, 'description');
    }

    const visibleObjects = scene.objects.filter(o => o.type !== 'background');
    if (visibleObjects.length > 0) {
      addToLog(`Objetos visíveis: ${visibleObjects.map(o => o.name).join(', ')}`, 'objects');
    }

    const exits = scene.hotspots.filter(h => h.actions.some(a => a.type === 'navigate'));
    if (exits.length > 0) {
      addToLog(`Saídas: ${exits.map(e => e.name).join(', ')}`, 'exits');
    }
    addToLog('');
  };

  const processCommand = async (cmd: string) => {
    const input = cmd.trim();
    if (!input) return;

    addToLog(`> ${input}`, 'command');

    if (input.toLowerCase() === 'sair' || input.toLowerCase() === 'exit') {
      onClose();
      return;
    }

    if (input.toLowerCase() === 'limpar' || input.toLowerCase() === 'cls') {
      setTextLog([]);
      return;
    }

    try {
      const response = await api.post('/api/game/command', {
        project_name: project.name,
        scene_id: currentSceneId,
        command: input,
        inventory: inventory
      });

      const result = response.data;

      if (!result.success) {
        addToLog(result.message, 'error');
        return;
      }

      addToLog(result.message, 'success');

      if (result.action === 'PICKUP' && result.target_id) {
        const targetObj = currentScene.objects.find(o => o.id === result.target_id);
        if (targetObj) {
          setInventory(prev => [...prev, { id: targetObj.id, name: targetObj.name, icon: targetObj.sprite }]);
        }
      }

      if (result.action === 'LOOK' && !result.target_id) {
        describeScene(currentScene);
      }

    } catch (error) {
      console.error(error);
      addToLog("Erro ao processar comando.", 'error');
    }
  };

  const handleSubmit = () => {
    if (command.trim()) {
      processCommand(command);
      setCommand('');
    }
  };

  const getLogColor = (type: string) => {
    const colors: Record<string, string> = {
      system: 'text-cyan-500 font-bold',
      title: 'text-yellow-400 font-bold text-center',
      location: 'text-green-400 font-bold',
      description: 'text-gray-300',
      objects: 'text-blue-400',
      exits: 'text-purple-400',
      command: 'text-white font-bold',
      success: 'text-green-400',
      error: 'text-red-400',
      info: 'text-cyan-400',
      hint: 'text-yellow-400',
      help: 'text-gray-400',
      item: 'text-blue-300',
      action: 'text-cyan-300',
      discovery: 'text-yellow-300 font-bold',
      story: 'text-gray-400 italic',
      separator: 'text-gray-600',
      category: 'text-yellow-400 font-bold',
    };
    return colors[type] || 'text-gray-300';
  };

  if (showLauncher) {
    return (
      <GameLauncher
        project={project}
        onStartGame={() => setShowLauncher(false)}
        onClose={onClose}
      />
    );
  }

  const backgroundObj = currentScene.objects.find(o => o.type === 'background' || o.name === 'Background');
  const backgroundUrl = backgroundObj ? getAssetUrl(project.name, backgroundObj.sprite) : '';

  return (
    <div className={`flex flex-col ${isFullscreen ? 'fixed inset-0 z-50' : 'h-screen'} bg-gray-900`}>

      {/* Header */}
      <div className="bg-gray-950 border-b border-gray-800 px-6 py-3 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Play className="w-5 h-5 text-cyan-400" />
            <span className="font-bold text-white">SAGA PLAYER</span>
          </div>
          <div className="h-6 w-px bg-gray-700"></div>
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-cyan-400" />
            <span className="text-sm text-gray-400 font-medium" style={{ fontSize: `${fontSize}px` }}>{currentScene.name}</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Controles de Fonte */}
          <div className="flex items-center bg-gray-800 rounded-lg mr-2 border border-gray-700">
            <button
              onClick={() => setFontSize(Math.max(10, fontSize - 2))}
              className="p-2 hover:bg-gray-700 rounded-l-lg transition-colors text-gray-400 hover:text-white"
              title="Diminuir Fonte"
            >
              <span className="text-xs font-bold">A-</span>
            </button>
            <div className="w-px h-4 bg-gray-700"></div>
            <button
              onClick={() => setFontSize(Math.min(32, fontSize + 2))}
              className="p-2 hover:bg-gray-700 rounded-r-lg transition-colors text-gray-400 hover:text-white"
              title="Aumentar Fonte"
            >
              <span className="text-sm font-bold">A+</span>
            </button>
          </div>

          <button
            onClick={() => setIsMuted(!isMuted)}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          >
            {isMuted ? <VolumeX className="w-5 h-5 text-gray-400" /> : <Volume2 className="w-5 h-5 text-gray-400" />}
          </button>

          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          >
            {isFullscreen ? <Minimize2 className="w-5 h-5 text-gray-400" /> : <Maximize2 className="w-5 h-5 text-gray-400" />}
          </button>

          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">

        {/* COLUNA 1: INVENTÁRIO (Esquerda) */}
        <div
          className="bg-gray-900 border-r border-gray-800 flex flex-col flex-shrink-0"
          style={{ width: leftPanel.width }}
        >
          <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-center gap-2">
            <Package className="w-5 h-5 text-yellow-400" />
            <span className="font-bold text-white" style={{ fontSize: `${fontSize}px` }}>INVENTÁRIO</span>
            <span className="text-gray-500" style={{ fontSize: `${fontSize - 2}px` }}>({inventory.length})</span>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {inventory.length === 0 ? (
              <div className="text-center py-6 text-gray-600 flex flex-col items-center">
                <Package className="w-8 h-8 mx-auto mb-2 opacity-30" />
                <p style={{ fontSize: `${fontSize - 2}px` }}>Vazio</p>
              </div>
            ) : (
              inventory.map((item) => (
                <div
                  key={item.id}
                  className="bg-gray-800/50 hover:bg-gray-800 border border-gray-700 rounded-lg p-2 cursor-pointer transition-colors"
                  onClick={() => processCommand(`examinar ${item.name}`)}
                >
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 bg-gray-700 rounded flex items-center justify-center overflow-hidden">
                      {item.icon ? <img src={getAssetUrl(project.name, item.icon)} className="w-full h-full object-cover" /> : <Package className="w-4 h-4 text-yellow-400" />}
                    </div>
                    <div className="flex-1">
                      <div className="font-medium text-white" style={{ fontSize: `${fontSize}px` }}>{item.name}</div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Handle de Redimensionamento Esquerdo */}
        <ResizeHandle onMouseDown={leftPanel.handleMouseDown} isResizing={leftPanel.isResizing} />

        {/* COLUNA 2: CENA (Centro) */}
        <div className="flex-1 flex flex-col min-w-0">

          {/* Canvas da Cena com Objetos */}
          <div className="flex-1 relative bg-black overflow-hidden flex items-center justify-center">
            {backgroundUrl && (
              <img
                src={backgroundUrl}
                alt={currentScene.name}
                className="w-full h-full object-contain"
              />
            )}

            {/* Objetos Clicáveis na Cena */}
            {currentScene.objects.filter(o => o.type !== 'background').map((obj) => {
              const isCollected = inventory.some(i => i.id === obj.id);
              if (isCollected) return null;

              return (
                <AnimatedObject
                  key={obj.id}
                  obj={obj}
                  projectName={project.name}
                  onClick={() => processCommand(`examinar ${obj.name}`)}
                />
              );
            })}

            {/* Overlay com Info da Cena */}
            <div className="absolute inset-0 bg-gradient-to-t from-gray-900 via-transparent to-transparent pointer-events-none"></div>
          </div>

          {/* Input de Comando */}
          <div className="bg-gray-950 border-t border-gray-800 p-4">
            <div className="flex items-center gap-3">
              <span className="text-cyan-400 font-mono font-bold" style={{ fontSize: `${fontSize + 4}px` }}>{'>'}</span>
              <input
                ref={inputRef}
                type="text"
                value={command}
                onChange={(e) => setCommand(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleSubmit();
                  }
                }}
                placeholder="Digite um comando..."
                className="flex-1 bg-gray-800 text-white px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 font-mono"
                style={{ fontSize: `${fontSize}px` }}
                autoComplete="off"
                spellCheck="false"
              />
              <button
                onClick={handleSubmit}
                className="px-6 py-3 bg-cyan-600 hover:bg-cyan-700 text-white rounded-lg font-bold transition-colors flex items-center gap-2"
                style={{ fontSize: `${fontSize}px` }}
              >
                <Send className="w-4 h-4" />
                Enviar
              </button>
            </div>

            <div className="mt-2 flex items-center gap-4 text-gray-500" style={{ fontSize: `${fontSize - 2}px` }}>
              <span>💡 Dica: Clique nos objetos na cena para interagir</span>
              <span>•</span>
              <span>Digite AJUDA para ver todos os comandos</span>
            </div>
          </div>
        </div>

        {/* Handle de Redimensionamento Direito */}
        <ResizeHandle onMouseDown={rightPanel.handleMouseDown} isResizing={rightPanel.isResizing} />

        {/* COLUNA 3: LOG DE TEXTO (Direita) */}
        <div
          className="bg-gray-950 border-l border-gray-800 flex flex-col flex-shrink-0"
          style={{ width: rightPanel.width }}
        >
          <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-center gap-2">
            <Notebook className="w-5 h-5 text-yellow-400" />
            <span className="font-bold text-white" style={{ fontSize: `${fontSize}px` }}>DESCRIÇÃO DO LOCAL</span>
          </div>

          <div
            ref={logRef}
            className="flex-1 overflow-y-auto p-4 font-mono leading-relaxed space-y-1"
            style={{ scrollBehavior: 'smooth' }}
          >
            {textLog.map((entry, index) => (
              <div key={index} className={getLogColor(entry.type)} style={{ fontSize: `${fontSize}px` }}>
                {entry.text}
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
};

export default GamePlayer;
