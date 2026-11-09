import React, { useState } from 'react';
import { Image as ImageIcon, Film, Trash2, ToyBrick, Plus, PanelLeftClose, PanelLeftOpen, X, Star, Music, FileAudio, Layout, Box } from 'lucide-react';
import type { Project, GameObject, Scene } from '../../types';
import { ResizeHandle, TreeItem } from '../ui';
import { PropertiesEditor } from '../editor/PropertiesEditor';

interface SidebarProps {
  project: Project;
  activeSceneId: string | null;
  selectedObjectId: string | null;
  onSelectScene: (sceneId: string) => void;
  onSelectObject: (objectId: string | null) => void;
  onCreateScene: () => void;
  onDeleteScene: (sceneId: string) => void;
  onRenameScene: (sceneId: string, newName: string) => void;
  onCreateObject: (sceneId: string, type?: GameObject['type']) => void;
  onDeleteObject: (sceneId: string, objectId: string) => void;
  onSaveProperties: (itemType: 'scene' | 'object', itemId: string, updates: any) => void;
  onSetSceneBackground: (sceneId: string, backgroundPath: string) => void;
  onMagicPartAnimate: (parentObjectId: string, result: any) => void;
  onStartExtraction?: (prompt: string) => void;
  resizable: {
    width: number;
    isResizing: boolean;
    handleMouseDown: (e: React.MouseEvent) => void;
  };
}

const ExplorerView: React.FC<Omit<SidebarProps, 'onSaveProperties' | 'resizable' | 'onSetSceneBackground'>> = (props) => {
  const {
    project,
    activeSceneId,
    selectedObjectId,
    onSelectScene,
    onSelectObject,
    onCreateScene,
    onDeleteScene,
    onRenameScene,
    onCreateObject,
    onDeleteObject,
    onStartExtraction,
  } = props;
  const [editingId, setEditingId] = useState<string | null>(null);
  const [tempName, setTempName] = useState('');

  const handleStartEditing = (id: string, currentName: string) => {
    setEditingId(id);
    setTempName(currentName);
  };

  const handleFinishEditing = () => {
    if (editingId && tempName.trim()) {
      onRenameScene(editingId, tempName.trim());
    }
    setEditingId(null);
    setTempName('');
  };

  return (
    <div className="flex-1 overflow-y-auto p-3 space-y-2 scrollbar-thin scrollbar-thumb-purple-500/20 scrollbar-track-transparent">
      <div className="text-sm text-gray-300 mb-4 px-2">{project.name}</div>

      <TreeItem icon={Film} label="Cenas" count={Object.keys(project.scenes).length} defaultOpen onAddClick={onCreateScene}>
        {Object.values(project.scenes).map(scene => (
          <div key={scene.id} className="group relative pr-8">
            {editingId === scene.id ? (
              <input type="text" value={tempName} onChange={(e) => setTempName(e.target.value)} onBlur={handleFinishEditing} onKeyDown={(e) => e.key === 'Enter' && handleFinishEditing()} className="bg-gray-700 text-white w-full my-1 px-2 py-1 rounded" autoFocus />
            ) : (
              <TreeItem
                icon={ImageIcon}
                label={
                  <span className="flex items-center gap-1">
                    {scene.name}
                    {project.start_scene === scene.id && <Star size={10} className="fill-yellow-500 text-yellow-500" title="Cena Inicial" />}
                  </span>
                }
                count={scene.objects.length}
                isActive={activeSceneId === scene.id && !selectedObjectId}
                onClick={() => onSelectScene(scene.id)}
                onDoubleClick={() => handleStartEditing(scene.id, scene.name)}
              >
                <div className="pl-4 mt-1 space-y-1">
                  {scene.objects.map((obj: GameObject) => (
                    <div key={obj.id} onClick={(e) => { e.stopPropagation(); onSelectObject(obj.id); }} className={`group flex items-center justify-between py-1 text-sm rounded-md px-2 cursor-pointer ${selectedObjectId === obj.id ? 'bg-purple-600/40 text-white' : 'text-gray-400 hover:bg-purple-500/10'}`}>
                      <span className="flex items-center gap-2">
                        {obj.type === 'sprite' && <ToyBrick size={14} />}
                        {obj.type === 'background' && <Layout size={14} />}
                        {obj.type === 'music' && <Music size={14} />}
                        {obj.type === 'sound' && <FileAudio size={14} />}
                        {obj.type === 'item' && <Box size={14} />}
                        {obj.name}
                      </span>
                      <button onClick={(e) => { e.stopPropagation(); onDeleteObject(scene.id, obj.id); }} className="p-1 hover:bg-red-600/20 rounded"><Trash2 className="w-3 h-3 text-red-500" /></button>
                    </div>
                  ))}

                  <div className="grid grid-cols-2 gap-1 mt-2">
                    <button onClick={() => activeSceneId && onCreateObject(activeSceneId, 'sprite')} className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-purple-400 p-1 hover:bg-purple-500/5 rounded transition-colors" title="Novo Sprite">
                      <ToyBrick size={12} /> Sprite
                    </button>
                    <button onClick={() => activeSceneId && onCreateObject(activeSceneId, 'background')} className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-blue-400 p-1 hover:bg-blue-500/5 rounded transition-colors" title="Novo Background">
                      <Layout size={12} /> BG
                    </button>
                    <button onClick={() => activeSceneId && onCreateObject(activeSceneId, 'item')} className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-yellow-400 p-1 hover:bg-yellow-500/5 rounded transition-colors" title="Novo Item">
                      <Box size={12} /> Item
                    </button>
                    <button onClick={() => activeSceneId && onCreateObject(activeSceneId, 'music')} className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-green-400 p-1 hover:bg-green-500/5 rounded transition-colors" title="Nova Música">
                      <Music size={12} /> Música
                    </button>
                  </div>
                </div>
              </TreeItem>
            )}
            <button onClick={(e) => { e.stopPropagation(); onDeleteScene(scene.id); }} className="absolute right-1 top-2 p-1 hover:bg-red-600/20 rounded">
              <Trash2 className="w-4 h-4 text-red-500" />
            </button>
          </div>
        ))}
      </TreeItem>
    </div>
  );
};

export const Sidebar: React.FC<SidebarProps> = (props) => {
  const { resizable, project, activeSceneId, selectedObjectId, onSelectObject, onSaveProperties, onSetSceneBackground, onMagicPartAnimate, onStartExtraction } = props;
  const [isCollapsed, setIsCollapsed] = useState(false);

  const handleToggleCollapse = () => setIsCollapsed(!isCollapsed);

  let selectedObject: GameObject | undefined;
  if (selectedObjectId) {
    for (const scene of Object.values(project.scenes)) {
      const found = scene.objects.find(o => o.id === selectedObjectId);
      if (found) {
        selectedObject = found;
        break;
      }
    }
  }

  const activeScene = activeSceneId ? project.scenes[activeSceneId] : null;

  if (isCollapsed) {
    return (
      <div className="w-14 bg-gray-950 border-r border-gray-800 flex flex-col items-center py-4 gap-4 flex-shrink-0">
        <button onClick={handleToggleCollapse} className="p-2 hover:bg-gray-700 rounded-lg transition-all">
          <PanelLeftOpen className="w-5 h-5 text-purple-400" />
        </button>
      </div>
    );
  }

  return (
    <>
      <div style={{ width: `${resizable.width}px` }} className="flex-shrink-0 bg-gradient-to-b from-gray-950 to-gray-900 h-full flex flex-col overflow-hidden">
        <div className="h-14 border-b border-gray-800 flex items-center justify-between px-4 bg-gray-950/50 flex-shrink-0">
          <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">
            {selectedObject ? 'Propriedades do Objeto' : 'Explorer'}
          </span>
          {selectedObject ? (
            <button onClick={() => onSelectObject(null)} className="p-1.5 hover:bg-gray-700 rounded-lg transition-all" title="Voltar para o Explorer">
              <X className="w-4 h-4 text-gray-400" />
            </button>
          ) : (
            <button onClick={handleToggleCollapse} className="p-1.5 hover:bg-gray-700 rounded-lg transition-all">
              <PanelLeftClose className="w-4 h-4 text-purple-400" />
            </button>
          )}
        </div>

        <div className="flex-1 overflow-hidden flex flex-col min-h-0">
          {selectedObject && activeScene ? (
            <div className="flex-1 flex flex-col overflow-hidden">
              <PropertiesEditor
                key={`obj-${selectedObject.id}`}
                project={project}
                selectedItem={selectedObject}
                activeScene={activeScene}
                onSave={(updates) => onSaveProperties('object', selectedObject.id, updates)}
                onClose={() => onSelectObject(null)}
                onSetSceneBackground={(backgroundPath) => onSetSceneBackground(activeScene.id, backgroundPath)}
                onMagicPartAnimate={onMagicPartAnimate}
                onStartExtraction={onStartExtraction}
              />
            </div>
          ) : activeSceneId && activeScene && !selectedObject ? (
            <div className="flex-1 flex flex-col overflow-hidden">
              <ExplorerView {...props} />
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-gray-600">
              <p className="text-xs">Selecione uma cena para começar</p>
            </div>
          )}
        </div>
      </div>
      <ResizeHandle onMouseDown={resizable.handleMouseDown} isResizing={resizable.isResizing} />
    </>
  );
};
