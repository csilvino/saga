import React from 'react';
import { Sparkles, Save, FolderOpen, Settings, LogIn, LogOut, Bot, XCircle, Play } from 'lucide-react';

interface HeaderProps {
  projectName: string | null;
  onSave: () => void;
  onClose?: () => void;
  onOpen?: () => void;
  onPlay?: () => void; // Adicionado
  onOpenSettings: () => void;
  isLoggedIn: boolean;
  onLogin: () => void;
  onLogout: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  projectName,
  onSave,
  onClose,
  onOpen,
  onPlay, // Adicionado
  onOpenSettings,
  isLoggedIn,
  onLogin,
  onLogout,
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
        {isLoggedIn ? (
          <button onClick={onLogout} className="px-3 py-2 text-sm bg-red-800 hover:bg-red-700 rounded-lg flex items-center gap-2 transition-colors" title="Fazer Logout da IA">
            <LogOut size={16} />
            Logout IA
          </button>
        ) : (
          <button onClick={onLogin} className="px-3 py-2 text-sm bg-blue-800 hover:bg-blue-700 rounded-lg flex items-center gap-2 transition-colors" title="Fazer Login com a IA">
            <LogIn size={16} />
            Login IA
          </button>
        )}
      </div>
    </div>
  );
};
