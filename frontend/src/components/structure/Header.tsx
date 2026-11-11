import React from 'react';
import { Save, FolderOpen, Settings, KeyRound, Bot, XCircle, Play, ScrollText } from 'lucide-react';

interface HeaderProps {
  projectName: string | null;
  onSave: () => void;
  onClose?: () => void;
  onOpen?: () => void;
  onPlay?: () => void; // Adicionado
  onBlueprint?: () => void;   // abre a ficha do jogo
  onOpenSettings: () => void;
  hasAiKey: boolean;          // a chave do Gemini está cadastrada
  onOpenApiKey: () => void;   // abre Configurações → API Keys
}

export const Header: React.FC<HeaderProps> = ({
  projectName,
  onSave,
  onClose,
  onOpen,
  onPlay, // Adicionado
  onBlueprint,
  onOpenSettings,
  hasAiKey,
  onOpenApiKey,
}) => {
  return (
    <div className="h-14 bg-gray-900 border-b border-gray-800 flex items-center justify-between px-4 flex-shrink-0">
      <div className="flex items-center gap-3">
        <Bot size={28} className="text-purple-400" />
        <h1 className="text-lg font-bold text-white">Saga Engine</h1>
        {projectName && (
          <>
            <span className="text-gray-600">/</span>
            <span className="text-sm font-semibold text-gray-300">{projectName}</span>
          </>
        )}
      </div>
      <div className="flex items-center gap-3">
        {projectName ? (
          <>
            <button onClick={onPlay} className="px-4 py-2 text-sm bg-green-700 hover:bg-green-600 text-white font-bold rounded-lg flex items-center gap-2 transition-colors shadow-lg shadow-green-900/20">
              <Play size={16} fill="currentColor" />
              JOGAR
            </button>
            {onBlueprint && (
              <button onClick={onBlueprint} title="A ficha do jogo: o adventure inteiro num arquivo, verificado e montado de uma vez"
                      className="px-3 py-2 text-sm bg-gray-800 hover:bg-gray-700 rounded-lg flex items-center gap-2 transition-colors">
                <ScrollText size={16} />
                Ficha
              </button>
            )}
            <div className="w-px h-6 bg-gray-700 mx-1" />
            <button onClick={onSave} className="px-3 py-2 text-sm bg-gray-800 hover:bg-gray-700 rounded-lg flex items-center gap-2 transition-colors">
              <Save size={16} />
              Salvar
            </button>
            <button onClick={onOpen} className="px-3 py-2 text-sm bg-gray-800 hover:bg-gray-700 rounded-lg flex items-center gap-2 transition-colors">
              <FolderOpen size={16} />
              Abrir Outro
            </button>
            <button onClick={onClose} className="px-3 py-2 text-sm bg-gray-800 hover:bg-gray-700 rounded-lg flex items-center gap-2 transition-colors" title="Fechar Projeto">
                <XCircle size={16} />
                Fechar
            </button>
          </>
        ) : (
          <button onClick={onOpen} className="px-3 py-2 text-sm bg-gray-800 hover:bg-gray-700 rounded-lg flex items-center gap-2 transition-colors">
            <FolderOpen size={16} />
            Abrir Projeto
          </button>
        )}
        <button onClick={onOpenSettings} className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors" title="Configurações">
          <Settings size={16} />
        </button>
        <div className="w-px h-6 bg-gray-700" />
        <button
          onClick={onOpenApiKey}
          className={`px-3 py-2 text-sm rounded-lg flex items-center gap-2 transition-colors ${hasAiKey ? 'bg-gray-800 hover:bg-gray-700' : 'bg-amber-700 hover:bg-amber-600'}`}
          title={hasAiKey ? 'Chave da IA cadastrada (Configurações → API Keys)' : 'Cadastre sua chave do Gemini para usar a IA'}
        >
          <KeyRound size={16} />
          {hasAiKey ? 'Chave IA' : 'Configurar IA'}
          <span className={`w-2 h-2 rounded-full ${hasAiKey ? 'bg-green-400' : 'bg-amber-300'}`} />
        </button>
      </div>
    </div>
  );
};
