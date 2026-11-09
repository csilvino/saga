import React, { useState } from 'react';
import { ChevronRight, GripVertical, AlertTriangle } from 'lucide-react';

interface TreeItemProps {
  icon: React.ElementType;
  label: string;
  count?: number;
  defaultOpen?: boolean;
  children: React.ReactNode;
  onAddClick?: () => void;
  onClick?: () => void;
  onDoubleClick?: () => void;
  isActive?: boolean;
}

export const TreeItem: React.FC<TreeItemProps> = ({ icon: Icon, label, count, defaultOpen = false, children, onAddClick, onClick, onDoubleClick, isActive }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  const handleHeaderClick = () => {
    if (onClick) {
      onClick();
    }
    setIsOpen(!isOpen);
  };

  return (
    <div className={`rounded-lg ${isActive ? 'bg-purple-600/20' : ''}`}>
      <div
        className="flex items-center justify-between px-2 py-1.5 rounded-md hover:bg-gray-800 cursor-pointer"
        onClick={handleHeaderClick}
        onDoubleClick={onDoubleClick}
      >
        <div className="flex items-center gap-2">
          <ChevronRight size={16} className={`transition-transform ${isOpen ? 'rotate-90' : ''}`} />
          <Icon size={16} className="text-purple-400" />
          <span className="text-sm font-semibold">{label}</span>
          {count !== undefined && <span className="text-xs text-gray-500">({count})</span>}
        </div>
        {onAddClick && (
          <button onClick={(e) => { e.stopPropagation(); onAddClick(); }} className="text-xs text-gray-400 hover:text-white p-1 rounded hover:bg-purple-500/20">+</button>
        )}
      </div>
      {isOpen && <div className="pl-4 border-l border-gray-800 ml-4">{children}</div>}
    </div>
  );
};

interface ResizeHandleProps {
  onMouseDown: (e: React.MouseEvent) => void;
  isResizing: boolean;
}

export const ResizeHandle: React.FC<ResizeHandleProps> = ({ onMouseDown, isResizing }) => (
  <div
    onMouseDown={onMouseDown}
    className={`w-1.5 h-full bg-gray-800 hover:bg-purple-600 cursor-col-resize flex items-center justify-center transition-colors ${
      isResizing ? 'bg-purple-600' : ''
    }`}
  >
    <GripVertical className="w-3 h-3 text-gray-600" />
  </div>
);

interface ConfirmModalProps {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: () => void;
    title: string;
    message: string;
}

export const ConfirmModal: React.FC<ConfirmModalProps> = ({ isOpen, onClose, onConfirm, title, message }) => {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={onClose}>
            <div className="bg-gray-800 rounded-lg shadow-2xl p-6 w-full max-w-md border border-yellow-500/30" onClick={e => e.stopPropagation()}>
                <div className="flex items-center gap-4 mb-4">
                    <div className="w-12 h-12 rounded-full bg-yellow-500/10 flex items-center justify-center">
                        <AlertTriangle className="w-6 h-6 text-yellow-400" />
                    </div>
                    <h2 className="text-xl font-bold text-white">{title}</h2>
                </div>
                <p className="text-gray-400 mb-6">{message}</p>
                <div className="flex justify-end gap-4">
                    <button onClick={onClose} className="px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-white transition-colors">
                        Cancelar
                    </button>
                    <button
                        onClick={() => {
                            onConfirm();
                            onClose();
                        }}
                        className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white font-semibold transition-colors"
                    >
                        Confirmar Exclusão
                    </button>
                </div>
            </div>
        </div>
    );
};
