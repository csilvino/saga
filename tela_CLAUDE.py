import React, { useState, useEffect, useRef } from 'react';
import { Play, X, Package, MapPin, Volume2, VolumeX, Maximize2, Minimize2, Send } from 'lucide-react';

const GamePlayer = () => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [command, setCommand] = useState('');
  const [textLog, setTextLog] = useState([]);
  const [inventory, setInventory] = useState([]);
  const [currentScene, setCurrentScene] = useState({
    name: 'Escritório do Professor Lagarto',
    description: 'Você está em um escritório empoeirado. Raios de luz atravessam uma janela suja, iluminando pilhas de livros antigos e papéis espalhados.',
    image: 'https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?w=1200&h=800&fit=crop',
    objects: [
      { name: 'escrivaninha', x: 65, y: 45 },
      { name: 'tapete', x: 50, y: 75 },
      { name: 'escada', x: 20, y: 30 },
    ],
    exits: ['norte', 'sul'],
  });
  
  const inputRef = useRef(null);
  const logRef = useRef(null);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [textLog]);

  useEffect(() => {
    if (isPlaying && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isPlaying]);

  const addToLog = (text, type = 'normal') => {
    setTextLog(prev => [...prev, { text, type, timestamp: Date.now() }]);
  };

  const startGame = () => {
    setIsPlaying(true);
    setTextLog([]);
    setInventory([]);
    
    setTimeout(() => {
      addToLog('═══════════════════════════════════════════════════════', 'system');
      addToLog('      CALIXTO ISLAND - Uma Aventura de Mistério', 'title');
      addToLog('═══════════════════════════════════════════════════════', 'system');
      addToLog('');
      addToLog('Você é um detetive renomado convocado para investigar', 'story');
      addToLog('o desaparecimento misterioso do Professor Lagarto.', 'story');
      addToLog('');
      addToLog('Digite OLHAR para examinar o ambiente.', 'hint');
      addToLog('Digite AJUDA para ver os comandos disponíveis.', 'hint');
      addToLog('');
      describeScene();
    }, 500);
  };

  const describeScene = () => {
    addToLog('─────────────────────────────────────', 'separator');
    addToLog(`📍 ${currentScene.name.toUpperCase()}`, 'location');
    addToLog('─────────────────────────────────────', 'separator');
    addToLog('');
    addToLog(currentScene.description, 'description');
    addToLog('');
    
    if (currentScene.objects.length > 0) {
      addToLog(`Objetos visíveis: ${currentScene.objects.map(o => o.name).join(', ')}`, 'objects');
    }
    
    if (currentScene.exits.length > 0) {
      addToLog(`Saídas: ${currentScene.exits.map(e => e.toUpperCase()).join(', ')}`, 'exits');
    }
    addToLog('');
  };

  const processCommand = (cmd) => {
    const input = cmd.toLowerCase().trim();
    addToLog(`> ${cmd}`, 'command');

    if (input === 'ajuda' || input === 'help') {
      addToLog('');
      addToLog('🧭 NAVEGAÇÃO: NORTE (N) | SUL (S) | LESTE (L) | OESTE (O)', 'help');
      addToLog('👁️  OBSERVAÇÃO: OLHAR | EXAMINAR [objeto]', 'help');
      addToLog('🤲 INTERAÇÃO: PEGAR [objeto] | USAR [objeto] | ABRIR [objeto]', 'help');
      addToLog('🎒 INVENTÁRIO: INVENTARIO (I)', 'help');
      addToLog('');
      return;
    }

    if (input === 'olhar' || input === 'look' || input === 'l') {
      describeScene();
      return;
    }

    if (input === 'inventario' || input === 'i' || input === 'inv') {
      addToLog('');
      if (inventory.length === 0) {
        addToLog('📦 Seu inventário está vazio.', 'info');
      } else {
        addToLog('📦 INVENTÁRIO:', 'category');
        inventory.forEach(item => addToLog(`  • ${item.name}`, 'item'));
      }
      addToLog('');
      return;
    }

    if (['norte', 'n', 'sul', 's', 'leste', 'l', 'oeste', 'o'].includes(input)) {
      const dirMap = { n: 'norte', s: 'sul', l: 'leste', o: 'oeste' };
      const fullDir = dirMap[input] || input;

      if (currentScene.exits.includes(fullDir)) {
        addToLog(`Você vai para ${fullDir.toUpperCase()}...`, 'action');
        addToLog('');
        setTimeout(() => {
          if (fullDir === 'norte') {
            setCurrentScene({
              name: 'Biblioteca',
              description: 'Uma vasta biblioteca com estantes que vão do chão ao teto. O silêncio é absoluto.',
              image: 'https://images.unsplash.com/photo-1507842217343-583bb7270b66?w=1200&h=800&fit=crop',
              objects: [
                { name: 'livro antigo', x: 40, y: 50 },
                { name: 'globo', x: 70, y: 60 },
                { name: 'escada de mão', x: 85, y: 40 },
              ],
              exits: ['sul'],
            });
            describeScene();
          } else {
            addToLog('Você volta ao escritório.', 'action');
            describeScene();
          }
        }, 800);
      } else {
        addToLog('Você não pode ir nessa direção.', 'error');
      }
      return;
    }

    const actionMatch = input.match(/^(pegar|usar|abrir|examinar) (.+)$/);
    if (actionMatch) {
      const [, action, object] = actionMatch;
      const objectExists = currentScene.objects.find(o => o.name === object);
      
      if (!objectExists) {
        addToLog(`Não há nenhum(a) ${object} aqui.`, 'error');
        return;
      }

      switch (action) {
        case 'examinar':
          addToLog('');
          if (object === 'escrivaninha') {
            addToLog('Uma escrivaninha antiga de mogno. Há várias gavetas com papéis amarelados.', 'description');
          } else if (object === 'tapete') {
            addToLog('Um tapete persa desgastado. Há algo estranho embaixo dele...', 'description');
          } else {
            addToLog(`O(a) ${object} não parece ter nada de especial.`, 'description');
          }
          break;

        case 'pegar':
          if (['escrivaninha', 'escada'].includes(object)) {
            addToLog('Isso é muito pesado para carregar!', 'error');
          } else {
            setInventory(prev => [...prev, { name: object, id: Date.now() }]);
            addToLog(`Você pegou: ${object}`, 'success');
            setCurrentScene(prev => ({
              ...prev,
              objects: prev.objects.filter(o => o.name !== object)
            }));
          }
          break;

        case 'abrir':
          if (object === 'escrivaninha') {
            addToLog('Você encontra uma CHAVE ENFERRUJADA na gaveta!', 'discovery');
            setInventory(prev => [...prev, { name: 'chave enferrujada', id: Date.now() }]);
          } else {
            addToLog(`Você não consegue abrir ${object}.`, 'error');
          }
          break;

        default:
          addToLog(`Você não pode fazer isso com ${object}.`, 'error');
      }
      addToLog('');
      return;
    }

    addToLog('Comando não reconhecido. Digite AJUDA para ver os comandos.', 'error');
  };

  const handleSubmit = () => {
    if (command.trim()) {
      processCommand(command);
      setCommand('');
    }
  };

  const getLogColor = (type) => {
    const colors = {
      system: 'text-cyan-400',
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

  if (!isPlaying) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
        <div className="text-center space-y-8 p-8">
          <div className="space-y-4">
            <h1 className="text-6xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-600">
              SAGA ENGINE
            </h1>
            <p className="text-2xl text-gray-400">Game Player</p>
          </div>
          
          <div className="w-64 h-1 bg-gradient-to-r from-transparent via-cyan-500 to-transparent mx-auto"></div>
          
          <div className="space-y-6">
            <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-6 border border-gray-700">
              <h2 className="text-xl font-bold text-yellow-400 mb-4">Calixto Island</h2>
              <p className="text-gray-300 text-sm leading-relaxed">
                Uma aventura de texto clássica onde você investiga<br/>
                o misterioso desaparecimento do Professor Lagarto.
              </p>
            </div>
            
            <button
              onClick={startGame}
              className="group relative px-8 py-4 bg-gradient-to-r from-cyan-600 to-blue-600 text-white rounded-lg font-bold text-lg hover:from-cyan-500 hover:to-blue-500 transition-all transform hover:scale-105 shadow-lg hover:shadow-cyan-500/50"
            >
              <div className="flex items-center gap-3">
                <Play className="w-6 h-6" />
                INICIAR JOGO
              </div>
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex flex-col ${isFullscreen ? 'fixed inset-0 z-50' : 'h-screen'} bg-gray-900`}>
      
      {/* Header */}
      <div className="bg-gray-950 border-b border-gray-800 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Play className="w-5 h-5 text-cyan-400" />
            <span className="font-bold text-white">SAGA PLAYER</span>
          </div>
          <div className="h-6 w-px bg-gray-700"></div>
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-cyan-400" />
            <span className="text-sm text-gray-400">{currentScene.name}</span>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
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
            onClick={() => setIsPlaying(false)}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* CENA PRINCIPAL (Maior) */}
        <div className="flex-1 flex flex-col">
          
          {/* Canvas da Cena com Objetos */}
          <div className="flex-1 relative bg-black overflow-hidden">
            <img 
              src={currentScene.image}
              alt={currentScene.name}
              className="w-full h-full object-cover"
            />
            
            {/* Objetos Clicáveis na Cena */}
            {currentScene.objects.map((obj, index) => (
              <button
                key={index}
                onClick={() => processCommand(`examinar ${obj.name}`)}
                className="absolute w-16 h-16 bg-cyan-400/20 hover:bg-cyan-400/40 border-2 border-cyan-400 rounded-full flex items-center justify-center transition-all hover:scale-110 group"
                style={{ left: `${obj.x}%`, top: `${obj.y}%`, transform: 'translate(-50%, -50%)' }}
                title={obj.name}
              >
                <div className="text-white text-xs font-bold opacity-0 group-hover:opacity-100 transition-opacity absolute -bottom-8 whitespace-nowrap bg-gray-900 px-2 py-1 rounded">
                  {obj.name}
                </div>
              </button>
            ))}

            {/* Overlay com Info da Cena */}
            <div className="absolute inset-0 bg-gradient-to-t from-gray-900 via-transparent to-transparent pointer-events-none"></div>
            
            {/* Saídas Disponíveis */}
            <div className="absolute bottom-6 left-6 flex gap-2">
              {currentScene.exits.map(exit => (
                <button
                  key={exit}
                  onClick={() => processCommand(exit)}
                  className="px-4 py-2 bg-purple-600/90 hover:bg-purple-600 text-white rounded-lg font-bold text-sm transition-colors flex items-center gap-2 backdrop-blur-sm"
                >
                  {exit === 'norte' && '⬆️'}
                  {exit === 'sul' && '⬇️'}
                  {exit === 'leste' && '➡️'}
                  {exit === 'oeste' && '⬅️'}
                  {exit.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          {/* Input de Comando */}
          <div className="bg-gray-950 border-t border-gray-800 p-4">
            <div className="flex items-center gap-3">
              <span className="text-cyan-400 font-mono text-lg font-bold">{'>'}</span>
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
                placeholder="Digite um comando (ex: examinar mesa, pegar livro, norte)..."
                className="flex-1 bg-gray-800 text-white px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 font-mono"
                autoComplete="off"
                spellCheck="false"
              />
              <button
                onClick={handleSubmit}
                className="px-6 py-3 bg-cyan-600 hover:bg-cyan-700 text-white rounded-lg font-bold transition-colors flex items-center gap-2"
              >
                <Send className="w-4 h-4" />
                Enviar
              </button>
            </div>
            
            <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
              <span>💡 Dica: Clique nos pontos azuis na cena para interagir</span>
              <span>•</span>
              <span>Digite AJUDA para ver todos os comandos</span>
            </div>
          </div>
        </div>

        {/* PAINEL LATERAL DIREITO */}
        <div className="w-80 bg-gray-950 border-l border-gray-800 flex flex-col">
          
          {/* Log de Texto */}
          <div className="flex-1 flex flex-col overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-800 flex items-center gap-2">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              <span className="text-sm font-bold text-white">LOG DO JOGO</span>
            </div>
            
            <div 
              ref={logRef}
              className="flex-1 overflow-y-auto p-4 font-mono text-xs leading-relaxed space-y-1"
              style={{ scrollBehavior: 'smooth' }}
            >
              {textLog.map((entry, index) => (
                <div key={index} className={getLogColor(entry.type)}>
                  {entry.text}
                </div>
              ))}
            </div>
          </div>

          {/* Inventário */}
          <div className="border-t border-gray-800 p-4">
            <div className="flex items-center gap-2 mb-3">
              <Package className="w-5 h-5 text-yellow-400" />
              <h3 className="font-bold text-white">INVENTÁRIO</h3>
              <span className="text-xs text-gray-500">({inventory.length})</span>
            </div>
            
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {inventory.length === 0 ? (
                <div className="text-center py-6 text-gray-600 text-xs">
                  <Package className="w-8 h-8 mx-auto mb-2 opacity-30" />
                  <p>Vazio</p>
                </div>
              ) : (
                inventory.map((item) => (
                  <div
                    key={item.id}
                    className="bg-gray-800/50 hover:bg-gray-800 border border-gray-700 rounded-lg p-2 cursor-pointer transition-colors"
                    onClick={() => processCommand(`examinar ${item.name}`)}
                  >
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 bg-gray-700 rounded flex items-center justify-center">
                        <Package className="w-4 h-4 text-yellow-400" />
                      </div>
                      <div className="flex-1 text-xs">
                        <div className="font-medium text-white">{item.name}</div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GamePlayer;