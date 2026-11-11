// GamePlayer Component - Saga Engine
import React, { useState, useEffect, useRef } from 'react';
import { Play, X, Package, MapPin, Volume2, VolumeX, Maximize2, Minimize2, Send, Type, Notebook } from 'lucide-react';
import { useGameAudio, type ObjectSound } from './useGameAudio';
import type { Project, GameObject } from '../types';
import api, { getAssetUrl, isPlaceholderSprite } from '../services/api';
import { useResizable, useRightResizable } from '../hooks';
import { ResizeHandle } from './ui';
import GameLauncher from './GameLauncher';
import RetroStage from './RetroStage';

interface GamePlayerProps {
  project: Project;
  initialSceneId: string;
  onClose: () => void;
}

// Componente para renderizar objetos animados ou estáticos
const AnimatedObject = ({ obj, projectName, onClick, invisible = false }: { obj: GameObject, projectName: string, onClick: () => void, invisible?: boolean }) => {
  const [currentFrame, setCurrentFrame] = useState(0);
  // painted = the object is part of the background picture: only a clickable area on top of it
  // invisible: drawn elsewhere (the retro canvas); only the clickable area stays
  const painted = !!obj.properties?.painted || invisible;
  const spriteUrl = painted ? null : getAssetUrl(projectName, obj.sprite);
  const placeholder = painted ? '' : isPlaceholderSprite(obj.sprite) ? obj.sprite : (spriteUrl ? '' : '📦');

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
    backgroundImage: spriteUrl ? `url("${spriteUrl}")` : undefined,
    backgroundRepeat: 'no-repeat',
  };
  if (placeholder) {
    style.display = 'flex';
    style.alignItems = 'center';
    style.justifyContent = 'center';
    style.fontSize = '2.5rem';
  }

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
      className={painted
        ? "group rounded-md hover:outline hover:outline-2 hover:outline-cyan-300/60"
        : "hover:scale-105 transition-transform duration-200 group"}
    >
      {placeholder}
      {/* Tooltip opcional */}
      <div className="text-white text-xs font-bold opacity-0 group-hover:opacity-100 transition-opacity absolute -bottom-6 left-1/2 transform -translate-x-1/2 whitespace-nowrap bg-gray-900 px-2 py-1 rounded z-10 pointer-events-none">
        {obj.name}
      </div>
    </div>
  );
};

interface GameView {
  scene_id: string;
  scene_name: string;
  objects: { id: string; name: string }[];
  inventory: { id: string; name: string }[];
  exits: Record<string, string>;
  background?: string | null;   // state variant (e.g. door open), else the scene background
  ambient?: string | null;      // the scene's background sound for this state
  object_sounds?: ObjectSound[];
  ended: string | null;
}

// Colors the engine's messages by what they are
const messageType = (text: string) => {
  if (text.startsWith('== ') || text.startsWith('📍')) return 'location';
  if (text.startsWith('Você vê:') || text.startsWith('Vejo:')) return 'objects';
  if (text.startsWith('Saídas:')) return 'exits';
  if (text.startsWith('[')) return 'error';
  return 'normal';
};

// Autosave: the engine is stateless, so the whole game is {state, view, log}; kept per project
// in this browser so a reload (or closing the player) continues where you were.
const saveKey = (projectName: string) => `saga_autosave:${projectName}`;
const loadSave = (projectName: string): any => {
  try { return JSON.parse(localStorage.getItem(saveKey(projectName)) || 'null'); } catch { return null; }
};

const GamePlayer: React.FC<GamePlayerProps> = ({ project, initialSceneId, onClose }) => {
  const [showLauncher, setShowLauncher] = useState(() => !loadSave(project.name));
  const [gameState, setGameState] = useState<any>(null);
  const [view, setView] = useState<GameView | null>(null);
  const [busy, setBusy] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [command, setCommand] = useState('');
  const [textLog, setTextLog] = useState<{ text: string; type: string; timestamp: number }[]>([]);
  const [fontSize, setFontSize] = useState(14);

  // Presentation: the author's default (project.presentation) and the player's own choice
  // (kept in this browser). 'classico' = picture on top, text below, like the 8-bit adventures.
  const presKey = `saga_presentation:${project.name}`;
  const [pres, setPres] = useState<{ layout: string; retro: boolean }>(() => {
    const def = { layout: (project as any).presentation?.layout || 'paineis', retro: !!(project as any).presentation?.retro };
    try { return { ...def, ...JSON.parse(localStorage.getItem(presKey) || '{}') }; } catch { return def; }
  });
  const updatePres = (change: Partial<{ layout: string; retro: boolean }>) => {
    const next = { ...pres, ...change };
    setPres(next);
    try { localStorage.setItem(presKey, JSON.stringify(next)); } catch { /* storage blocked */ }
  };
  const classic = pres.layout === 'classico';

  // Hooks de redimensionamento
  const leftPanel = useResizable(320, 200, 500);
  const rightPanel = useRightResizable(384, 250, 600);

  const audio = useGameAudio(project.name, view?.ambient, view?.object_sounds, isMuted, pres.retro);

  const inputRef = useRef<HTMLInputElement>(null);
  const logRef = useRef<HTMLDivElement>(null);
  const initialized = useRef(false);

  // every object of the project by id (objects can move between scenes during play)
  const allObjects: Record<string, GameObject> = {};
  Object.values(project.scenes).forEach(s => s.objects.forEach(o => { allObjects[o.id] = o; }));

  const currentScene = project.scenes[view?.scene_id || initialSceneId] || Object.values(project.scenes)[0];
  const inventory = (view?.inventory || []).map(i => ({ ...i, icon: allObjects[i.id]?.sprite }));
  const visibleIds = new Set((view?.objects || []).map(o => o.id));

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [textLog, fontSize]);

  useEffect(() => {
    if (!showLauncher && inputRef.current) {
      inputRef.current.focus();
    }
  }, [showLauncher, busy]);

  const addToLog = (text: string, type = 'normal') => {
    setTextLog(prev => [...prev, { text, type, timestamp: Date.now() }]);
  };

  const showResult = (data: any) => {
    setGameState(data.state);
    setView(data.view);
    audio.playEvents((data.sounds || []).map((s: { file?: string | null }) => s.file));
    (data.messages || []).forEach((m: string) => addToLog(m, messageType(m)));
    if (data.view?.ended) addToLog('— FIM — digite RECOMEÇAR para jogar de novo.', 'system');
    addToLog('');
  };

  // save after every change of state (the log goes too, so the screen comes back as it was)
  useEffect(() => {
    if (!gameState) return;
    try {
      localStorage.setItem(saveKey(project.name),
        JSON.stringify({ state: gameState, view, log: textLog.slice(-300), savedAt: Date.now() }));
    } catch { /* storage full or blocked: playing still works */ }
  }, [gameState, view, textLog, project.name]);

  const resumeGame = (save: any) => {
    setGameState(save.state);
    setView(save.view);
    setTextLog([...(save.log || []),
      { text: '— jogo salvo: continuando de onde parou (digite RECOMEÇAR para um jogo novo) —', type: 'system', timestamp: Date.now() },
      { text: '', type: 'normal', timestamp: Date.now() }]);
  };

  const startGame = async () => {
    setTextLog([]);
    addToLog('═══════════════════════════════════════════════════════', 'system');
    addToLog(`      ${project.name.toUpperCase()}`, 'title');
    addToLog('═══════════════════════════════════════════════════════', 'system');
    addToLog('');
    try {
      const response = await api.post('/api/game/start', { project_name: project.name });
      showResult(response.data);
    } catch (error: any) {
      addToLog(`Não foi possível iniciar o jogo: ${error.response?.data?.detail || error.message}`, 'error');
    }
  };

  useEffect(() => {
    if (showLauncher || initialized.current) return;
    initialized.current = true;
    const save = loadSave(project.name);
    if (save?.state) resumeGame(save);
    else startGame();
  }, [showLauncher]);

  const processCommand = async (cmd: string) => {
    const input = cmd.trim();
    if (!input || busy) return;

    addToLog(`> ${input}`, 'command');
    const lower = input.toLowerCase();

    if (lower === 'sair do jogo' || lower === 'exit') {
      onClose();
      return;
    }
    if (lower === 'limpar' || lower === 'cls') {
      setTextLog([]);
      return;
    }
    if (lower === 'recomeçar' || lower === 'recomecar' || lower === 'restart') {
      try { localStorage.removeItem(saveKey(project.name)); } catch { /* storage blocked */ }
      startGame();
      return;
    }

    setBusy(true);
    try {
      const response = await api.post('/api/game/command', {
        project_name: project.name,
        command: input,
        state: gameState,
      });
      showResult(response.data);
    } catch (error: any) {
      console.error(error);
      addToLog(`Erro ao processar comando: ${error.response?.data?.detail || error.message}`, 'error');
    } finally {
      setBusy(false);
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

  const backgroundObj = currentScene?.objects.find(o => o.type === 'background' || o.name === 'Background');
  const backgroundUrl = getAssetUrl(project.name, view?.background || backgroundObj?.sprite || '') || '';

  const visibleObjs = Object.values(allObjects).filter(o => visibleIds.has(o.id));
  const spriteOf = (o: GameObject) => (o.properties?.painted ? null : getAssetUrl(project.name, o.sprite));
  const retroSprites = pres.retro
    ? visibleObjs.filter(o => spriteOf(o)).sort((a, b) => (a.zIndex || 0) - (b.zIndex || 0)).map(o => ({
        url: spriteOf(o)!, x: o.position.x - o.size.width / 2, y: o.position.y - o.size.height / 2,
        w: o.size.width, h: o.size.height }))
    : [];

  // 16:9 stage: background and objects share the same 1920x1080 coordinates
  const stage = (
    <div className="relative" style={{ width: 'min(100cqw, calc(100cqh * 16 / 9))', aspectRatio: '16 / 9' }}>
      {backgroundUrl && (pres.retro
        ? <RetroStage background={backgroundUrl} sprites={retroSprites} />
        : <img src={backgroundUrl} alt={view?.scene_name || ''} className="absolute inset-0 w-full h-full object-cover" />)}
      {visibleObjs.map((obj) => (
        <AnimatedObject
          key={obj.id}
          obj={obj}
          projectName={project.name}
          invisible={pres.retro && !!spriteOf(obj)}
          onClick={() => processCommand(`examinar ${obj.name}`)}
        />
      ))}
    </div>
  );

  const header = (
      <div className="bg-gray-950 border-b border-gray-800 px-6 py-3 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Play className="w-5 h-5 text-cyan-400" />
            <span className="font-bold text-white">SAGA PLAYER</span>
          </div>
          <div className="h-6 w-px bg-gray-700"></div>
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-cyan-400" />
            <span className="text-sm text-gray-400 font-medium" style={{ fontSize: `${fontSize}px` }}>{view?.scene_name || currentScene?.name}</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Apresentação: clássico (imagem em cima, texto embaixo) ou painéis; ilustração retrô */}
          <div className="flex items-center bg-gray-800 rounded-lg mr-2 border border-gray-700 text-xs font-bold">
            <button onClick={() => updatePres({ layout: classic ? 'paineis' : 'classico' })}
              className="px-3 py-2 rounded-l-lg text-gray-300 hover:bg-gray-700 hover:text-white"
              title="Clássico: imagem em cima e texto embaixo, como nos adventures de 8 bits">
              {classic ? 'CLÁSSICO' : 'PAINÉIS'}
            </button>
            <div className="w-px h-4 bg-gray-700"></div>
            <button onClick={() => updatePres({ retro: !pres.retro })}
              className={`px-3 py-2 rounded-r-lg hover:bg-gray-700 ${pres.retro ? 'text-amber-300' : 'text-gray-500'}`}
              title="Ilustração retrô: baixa resolução e poucas cores">
              RETRÔ
            </button>
          </div>

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
  );

  const commandInput = (className: string, style: React.CSSProperties = {}) => (
    <input
      ref={inputRef}
      type="text"
      value={command}
      onChange={(e) => setCommand(e.target.value)}
      onKeyDown={(e) => { if (e.key === 'Enter') handleSubmit(); }}
      className={className}
      style={style}
      placeholder={classic ? '' : 'Digite um comando...'}
      autoComplete="off"
      spellCheck="false"
    />
  );

  // CLÁSSICO: like the 8-bit illustrated adventures: the picture on top, the text below, one input line
  if (classic) {
    const retroFont = "'VT323', ui-monospace, monospace";
    return (
      <div className={`flex flex-col ${isFullscreen ? 'fixed inset-0 z-50' : 'h-screen'} bg-black`}>
        {header}
        <div className="relative bg-black overflow-hidden flex items-center justify-center flex-shrink-0 border-b-4 border-gray-800"
             style={{ containerType: 'size', height: '58%' }}>
          {stage}
        </div>
        <div ref={logRef} className="flex-1 overflow-y-auto px-6 py-3 leading-snug"
             style={{ fontFamily: retroFont, scrollBehavior: 'smooth' }}>
          {textLog.map((entry, index) => (
            <div key={index} className={getLogColor(entry.type)} style={{ fontSize: `${fontSize + 8}px` }}>
              {entry.text || ' '}
            </div>
          ))}
        </div>
        <div className="flex items-center gap-2 px-6 py-3 border-t border-gray-800 bg-black"
             style={{ fontFamily: retroFont, fontSize: `${fontSize + 10}px` }}>
          <span className="text-green-400">{'>'}</span>
          {commandInput('flex-1 bg-transparent text-green-300 uppercase focus:outline-none caret-green-300',
                        { fontFamily: retroFont, fontSize: `${fontSize + 10}px` })}
        </div>
      </div>
    );
  }

  return (
    <div className={`flex flex-col ${isFullscreen ? 'fixed inset-0 z-50' : 'h-screen'} bg-gray-900`}>

      {header}

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
                      {getAssetUrl(project.name, item.icon) ? <img src={getAssetUrl(project.name, item.icon)!} className="w-full h-full object-contain" /> : <Package className="w-4 h-4 text-yellow-400" />}
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
          <div className="flex-1 relative bg-black overflow-hidden flex items-center justify-center"
               style={{ containerType: 'size' }}>
            {stage}

            {/* Overlay com Info da Cena */}
            <div className="absolute inset-0 bg-gradient-to-t from-gray-900 via-transparent to-transparent pointer-events-none"></div>
          </div>

          {/* Input de Comando */}
          <div className="bg-gray-950 border-t border-gray-800 p-4">
            <div className="flex items-center gap-3">
              <span className="text-cyan-400 font-mono font-bold" style={{ fontSize: `${fontSize + 4}px` }}>{'>'}</span>
              {commandInput('flex-1 bg-gray-800 text-white px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 font-mono',
                            { fontSize: `${fontSize}px` })}
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
              <span>💡 Clique num objeto para examiná-lo</span>
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
