import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Toaster, toast } from 'react-hot-toast';
import { Folder, Bot, PlusCircle, Loader2 } from 'lucide-react';
import { v4 as uuidv4 } from 'uuid';
import {
  DndContext,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent
} from '@dnd-kit/core';

import type { Project, Scene, GameObject } from './types';
import api, { getAssetUrl } from './services/api';
import { Sidebar } from './components/structure/Sidebar';
import { SceneCanvas } from './components/structure/SceneCanvas';
import { AIPanel } from './components/ai/AIPanel';
import { Header } from './components/structure/Header';
import { ConfirmModal } from './components/ui';
import SettingsPanel from './components/settings/SettingsPanel';
import GamePlayer from './components/GamePlayer'; // Importado
import { useResizable, useRightResizable } from './hooks';

const LAST_PROJECT_KEY = 'saga_last_open_project';

const WelcomeScreen = ({ onOpenProject, onCreateProject, projects, onLogin, onOpenSettings, isOpeningProject }) => (
  <div className="w-full h-screen bg-gray-950 text-white flex flex-col">
    <Header projectName={null} onSave={() => { }} onOpen={() => { }} isLoggedIn={false} onLogin={onLogin} onLogout={() => { }} onOpenSettings={onOpenSettings} />
    <div className="flex-1 flex flex-col items-center justify-center p-4">
      <div className="text-center mb-12">
        <Bot size={64} className="mx-auto text-purple-400 mb-4 animate-pulse" />
        <h1 className="text-5xl font-bold mb-2 tracking-tight">Saga Engine</h1>
        <p className="text-xl text-gray-400 font-medium tracking-wide">Criação de Jogos Assistida por IA</p>
      </div>
      <div className="w-full max-w-md">
        <h2 className="text-xs font-black uppercase tracking-[0.2em] text-purple-400/80 mb-4 text-center">Abrir Projeto Existente</h2>
        <div className="bg-gray-900/50 border border-white/5 rounded-xl p-2 space-y-1 max-h-60 overflow-y-auto custom-scrollbar">
          {projects.length > 0 ? projects.map(p => (
            <button
              key={p}
              disabled={!!isOpeningProject}
              onClick={() => onOpenProject(p)}
              className="group w-full text-left flex items-center justify-between p-3 hover:bg-white/5 rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <div className="flex items-center gap-3">
                <Folder size={18} className="text-purple-400 group-hover:text-purple-300 transition-colors" />
                <span className="font-medium group-hover:translate-x-0.5 transition-transform">{p}</span>
              </div>
              {isOpeningProject === p ? (
                <Loader2 size={16} className="animate-spin text-purple-400" />
              ) : (
                <span className="text-[10px] font-bold text-gray-600 group-hover:text-purple-400 transition-colors">ABRIR</span>
              )}
            </button>
          )) : (
            <p className="py-8 text-center text-gray-500 italic">Nenhum projeto encontrado.</p>
          )}
        </div>
        <div className="mt-8 text-center">
          <button
            onClick={onCreateProject}
            disabled={!!isOpeningProject}
            className="group inline-flex items-center gap-2 px-8 py-4 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl transition-all duration-300 font-bold shadow-lg shadow-purple-900/20 active:scale-95"
          >
            <PlusCircle size={20} className="group-hover:rotate-90 transition-transform duration-300" />
            Criar Novo Projeto
          </button>
        </div>
      </div>
    </div>
  </div>
);

export default function App() {
  const [project, setProject] = useState<Project | null>(null);
  const [projects, setProjects] = useState<string[]>([]);
  const [activeSceneId, setActiveSceneId] = useState<string | null>(null);
  const [selectedObjectId, setSelectedObjectId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [deletionTarget, setDeletionTarget] = useState<{ type: string; id: string; sceneId?: string } | null>(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false); // Estado para controlar o modo de jogo
  const [isOpening, setIsOpening] = useState<string | null>(null);

  // Extraction Mode State
  const [isExtractionMode, setIsExtractionMode] = useState(false);
  const [extractionPrompt, setExtractionPrompt] = useState<string | null>(null);

  const leftSidebar = useResizable(280, 200, 500);
  const rightAIPanel = useRightResizable(450, 350, 800);
  const [canvasScale, setCanvasScale] = useState(1);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 5,
      },
    })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, delta } = event;
    if (!active.data.current) return;

    const { type, objectId, filePath } = active.data.current as any;

    if (type === 'object' && objectId) {
      // Mover objeto existente
      setProject(prev => {
        if (!prev) return prev;
        const newProject = { ...prev };

        // Find the object in all scenes (though usually it's the active one)
        for (const sId in newProject.scenes) {
          const scene = newProject.scenes[sId];
          const objIndex = scene.objects.findIndex(o => o.id === objectId);
          if (objIndex !== -1) {
            const obj = scene.objects[objIndex];

            // Correção de Escala: Garante que scale não seja zero
            const safeScale = canvasScale || 1;

            // Arredonda para evitar sub-pixels
            const scaledDeltaX = Math.round(delta.x / safeScale);
            const scaledDeltaY = Math.round(delta.y / safeScale);

            const updatedObject = {
              ...obj,
              position: {
                x: Math.round(obj.position.x + scaledDeltaX),
                y: Math.round(obj.position.y + scaledDeltaY),
              }
            };
            const newObjects = [...scene.objects];
            newObjects[objIndex] = updatedObject;
            newProject.scenes[sId] = { ...scene, objects: newObjects };

            handleSaveProject(newProject);
            break;
          }
        }
        return newProject;
      });
    } else if (type === 'asset' && filePath) {
      // Arrastar novo asset para a cena (placeholder por enquanto ou implementar drop)
      // O drop real precisaria de um Droppable que capturasse a posição do mouse no SceneCanvas
      // Vamos focar no movimento do objeto existente primeiro.
    }
  };

  const loadProjectList = useCallback(async () => {
    try {
      const projResponse = await api.get('/api/projects/list');
      setProjects(projResponse.data);
      return projResponse.data;
    } catch (error) {
      toast.error("Falha ao listar projetos.");
      return [];
    }
  }, []);

  const openProject = useCallback(async (projectName: string) => {
    setIsOpening(projectName);
    try {
      const projectResponse = await api.post('/api/projects/load', { name: projectName });
      const loadedProject = projectResponse.data.project;
      setProject(loadedProject);

      if (loadedProject.start_scene && loadedProject.scenes[loadedProject.start_scene]) {
        setActiveSceneId(loadedProject.start_scene);
      } else if (Object.keys(loadedProject.scenes).length > 0) {
        setActiveSceneId(Object.keys(loadedProject.scenes)[0]);
      }
      setSelectedObjectId(null);

      localStorage.setItem(LAST_PROJECT_KEY, projectName);
      toast.success(`Projeto "${projectName}" carregado!`);
    } catch (error) {
      console.error("DEBUG: Erro ao abrir projeto:", error);
      if (axios.isAxiosError(error)) {
        console.error("DEBUG: Detalhes do erro:", {
          message: error.message,
          code: error.code,
          config: error.config,
          response: error.response
        });
      }
      toast.error(`Falha ao abrir o projeto '${projectName}'. Verifique se o backend está rodando.`);
      localStorage.removeItem(LAST_PROJECT_KEY);
    } finally {
      setIsOpening(null);
    }
  }, []);

  const handleCreateProject = async () => {
    const projectName = prompt("Digite o nome do novo projeto:");
    if (!projectName || projectName.trim() === "") {
      toast.error("Nome de projeto inválido.");
      return;
    }
    try {
      await api.post('/api/projects/create', { name: projectName });
      toast.success(`Projeto "${projectName}" criado!`);
      await loadProjectList();
      await openProject(projectName);
    } catch (error) {
      toast.error(`Falha ao criar o projeto '${projectName}'.`);
    }
  };

  const handleCloseProject = () => {
    setProject(null);
    setActiveSceneId(null);
    setSelectedObjectId(null);
    localStorage.removeItem(LAST_PROJECT_KEY);
    loadProjectList();
  };

  const refreshProjectState = useCallback(async () => {
    if (!project) return;
    await openProject(project.name);
  }, [project, openProject]);

  const handleSaveProject = useCallback(async (projectToSave?: Project) => {
    const dataToSave = projectToSave || project;
    if (!dataToSave) return;
    try {
      await api.post('/api/projects/save', { project: dataToSave });
      if (projectToSave) {
        setProject(projectToSave);
      }
    } catch (error) {
      toast.error('Erro ao salvar o projeto.');
    }
  }, [project]);

  const handleSelectScene = (sceneId: string) => {
    setActiveSceneId(sceneId);
    setSelectedObjectId(null);
  };

  const handleCreateScene = async () => {
    setProject(prev => {
      if (!prev) return prev;
      const newSceneId = `scene_${uuidv4()}`;
      const backgroundObjectId = `background_${uuidv4()}`;

      // Cria a cena com um objeto de background padrão
      const newScene: Scene = {
        id: newSceneId,
        name: `Nova Cena ${Object.keys(prev.scenes).length + 1}`,
        objects: [
          {
            id: backgroundObjectId,
            name: "Background",
            type: 'background',
            sprite: '',
            position: { x: 960, y: 540 },
            origin: { x: 960, y: 540 },
            size: { width: 1920, height: 1080 },
            scale: { x: 1, y: 1 },
            rotation: 0,
            zIndex: 0,
            actions: [],
            ses: "// Script para o Background\n"
          }
        ],
        hotspots: [],
        actions: [],
      } as any; // Cast temporário pois removemos 'background' da interface

      const newProject = {
        ...prev,
        start_scene: prev.start_scene || newSceneId,
        scenes: {
          ...prev.scenes,
          [newSceneId]: newScene,
        }
      };

      handleSaveProject(newProject);
      setActiveSceneId(newSceneId);
      toast.success("Nova cena criada!");

      return newProject;
    });
  };

  const handleCreateObject = async (sceneId: string, type: GameObject['type'] = 'sprite') => {
    setProject(prev => {
      if (!prev) return prev;
      const scene = prev.scenes[sceneId];
      if (!scene) return prev;

      const newObjectId = `${type}_${uuidv4()}`;

      // Default dimensions based on type
      let width = 100;
      let height = 100;
      let zIndex = 10;

      if (type === 'background') {
        width = 1920;
        height = 1080;
        zIndex = 0;
      } else if (type === 'sound' || type === 'music') {
        width = 50;
        height = 50;
      }

      const newObject: GameObject = {
        id: newObjectId,
        name: `Novo ${type.charAt(0).toUpperCase() + type.slice(1)} ${scene.objects.length + 1}`,
        type: type,
        sprite: '',
        position: { x: 960, y: 540 },
        origin: { x: 960, y: 540 },
        size: { width, height },
        scale: { x: 1, y: 1 },
        rotation: 0,
        zIndex: zIndex,
        properties: {
          volume: type === 'sound' || type === 'music' ? 1.0 : undefined,
          loop: type === 'music' ? true : undefined
        },
        actions: [],
        ses: `// Script para ${type} ${scene.objects.length + 1}\n\non click {\n  // Adicione sua lógica aqui\n}\n`
      };

      const newProject = {
        ...prev,
        scenes: {
          ...prev.scenes,
          [sceneId]: {
            ...scene,
            objects: [...scene.objects, newObject],
          },
        },
      };

      handleSaveProject(newProject);
      setSelectedObjectId(newObjectId);
      toast.success(`Novo ${type} criado e selecionado!`);

      return newProject;
    });
  };

  const handleSaveProperties = useCallback(async (itemType: 'scene' | 'object', itemId: string, updates: Partial<GameObject> | Partial<Scene>) => {
    setProject(prev => {
      if (!prev) return prev;
      let newProject = { ...prev };

      if (itemType === 'object') {
        for (const sceneId in newProject.scenes) {
          const scene = newProject.scenes[sceneId];
          const objectIndex = scene.objects.findIndex(o => o.id === itemId);
          if (objectIndex !== -1) {
            const updatedObject = { ...scene.objects[objectIndex], ...updates };
            const newObjects = [...scene.objects];
            newObjects[objectIndex] = updatedObject;
            newProject.scenes[sceneId] = { ...scene, objects: newObjects };
            break;
          }
        }
      } else if (itemType === 'scene') {
        if (newProject.scenes[itemId]) {
          newProject.scenes[itemId] = { ...newProject.scenes[itemId], ...updates };
        }
      }

      handleSaveProject(newProject);
      return newProject;
    });
  }, [handleSaveProject]);

  const handleSetSceneBackground = useCallback(async (sceneId: string, backgroundPath: string) => {
    setProject(prev => {
      const scene = prev.scenes[sceneId];
      if (!scene) return prev;

      // Update strictly the background object
      const updatedObjects = (scene.objects || []).map(obj => {
        if (obj.type === 'background' || obj.name === 'Background') {
          return { ...obj, sprite: backgroundPath };
        }
        return obj;
      });

      const newProject = {
        ...prev,
        scenes: {
          ...prev.scenes,
          [sceneId]: {
            ...scene,
            objects: updatedObjects
          },
        },
      };

      handleSaveProject(newProject);
      return newProject;
    });
  }, [handleSaveProject]);

  const handleMagicAnimatePart = useCallback(async (parentObjectId: string, result: any) => {
    setProject(prev => {
      if (!prev) return prev;

      const { new_part, updated_parent_sprite } = result;
      let targetSceneId = '';
      let parentObj: GameObject | null = null;

      // Encontrar o pai e sua cena
      for (const sId in prev.scenes) {
        const pObj = prev.scenes[sId].objects.find(o => o.id === parentObjectId);
        if (pObj) {
          targetSceneId = sId;
          parentObj = pObj;
          break;
        }
      }
      if (!parentObj || !targetSceneId) return prev;

      // Usar dimensões reais do backend para evitar loading demorado
      const newPartId = `obj_${uuidv4().slice(0, 8)}`;
      const realBbox = new_part.real_bbox_pixels;
      const anchorX = new_part.animation.anchor_x;
      const anchorY = new_part.animation.anchor_y;

      // Precisamos carregar a imagem para saber a proporção real
      // (Poderíamos usar async/await aqui, mas como estamos dentro do setProject, 
      // o ideal seria ter carregado antes. Mas para simplicidade agora vamos assumir 
      // que o size.width/height do pai reflete a proporção da imagem).

      // TODO: No futuro, passar parent_image_size do backend para evitar este load.

      const widthRatio = (parentObj.size?.width || 0) / (realBbox.parent_width || parentObj.size?.width || 1);
      const heightRatio = (parentObj.size?.height || 0) / (realBbox.parent_height || parentObj.size?.height || 1);

      const canvasPartWidth = realBbox.width * widthRatio;
      const canvasPartHeight = realBbox.height * heightRatio;

      const parentCanvasLeft = parentObj.position.x - ((parentObj.size?.width || 0) / 2);
      const parentCanvasTop = parentObj.position.y - ((parentObj.size?.height || 0) / 2);

      // A posição do objeto no SAGA deve ser o seu ponto de ancoragem (pivot)
      const partCanvasAnchorX = parentCanvasLeft + (realBbox.left * widthRatio) + (canvasPartWidth * anchorX);
      const partCanvasAnchorY = parentCanvasTop + (realBbox.top * heightRatio) + (canvasPartHeight * anchorY);

      const newPart: GameObject = {
        id: newPartId,
        name: new_part.name,
        sprite: new_part.sprite,
        type: 'sprite',
        position: { x: partCanvasAnchorX, y: partCanvasAnchorY },
        size: { width: canvasPartWidth, height: canvasPartHeight },
        scale: { x: 1, y: 1 },
        rotation: 0,
        zIndex: parentObj.zIndex + 1,
        anchor: { x: anchorX, y: anchorY },
        animation: {
          type: 'transform',
          property: new_part.animation.type === 'rotate' ? 'rotation' : (new_part.animation.type === 'scale' ? 'scale' : 'position'),
          min: new_part.animation.min_value,
          max: new_part.animation.max_value,
          duration: new_part.animation.duration,
          easing: 'easeInOut'
        },
        ses: `// Automatizado: Parte do objeto ${parentObj.name}`
      };

      // Atualizar o pai (trocar sprite)
      const updatedObjects = prev.scenes[targetSceneId].objects.map(o => {
        if (o.id === parentObjectId) {
          return { ...o, sprite: updated_parent_sprite };
        }
        return o;
      });

      const newProject = {
        ...prev,
        scenes: {
          ...prev.scenes,
          [targetSceneId]: {
            ...prev.scenes[targetSceneId],
            objects: [...updatedObjects, newPart]
          }
        }
      };

      handleSaveProject(newProject);
      setSelectedObjectId(newPartId);
      toast.success(`Parte "${new_part.name}" extraída e animada!`);
      return newProject;
    });
  }, [handleSaveProject]);

  const handleRenameScene = async (sceneId: string, newName: string) => {
    await handleSaveProperties('scene', sceneId, { name: newName });
  };

  const handleConfirmDelete = async () => {
    if (!deletionTarget) return;
    const { type, id, sceneId } = deletionTarget;

    setProject(prev => {
      if (!prev) return prev;

      if (type === 'scene') {
        const newProject = { ...prev };
        delete newProject.scenes[id];

        // Se a cena deletada era a inicial, pega a próxima disponível ou deixa vazio
        if (id === prev.start_scene) {
          const remainingScenes = Object.keys(newProject.scenes);
          newProject.start_scene = remainingScenes.length > 0 ? remainingScenes[0] : '';
        }

        handleSaveProject(newProject);

        if (activeSceneId === id) {
          setActiveSceneId(newProject.start_scene || null);
        }
        toast.success("Cena deletada.");
        return newProject;
      } else if (type === 'object' && sceneId) {
        const scene = prev.scenes[sceneId];
        if (!scene) return prev;
        const objectToDelete = scene.objects.find(obj => obj.id === id);
        const isBackground = objectToDelete?.type === 'background';
        const newObjects = scene.objects.filter(obj => obj.id !== id);
        const newProject = {
          ...prev,
          scenes: {
            ...prev.scenes,
            [sceneId]: {
              ...scene,
              objects: newObjects,
            },
          },
        };

        handleSaveProject(newProject);

        if (selectedObjectId === id) {
          setSelectedObjectId(null);
        }
        toast.success("Objeto removido da cena.");
        return newProject;
      }
      return prev;
    });
    setDeletionTarget(null);
  };

  const handleLogin = async () => {
    try {
      const response = await api.get('/api/auth/google/url');
      const { url } = response.data;
      const width = 600, height = 700;
      const left = (window.innerWidth / 2) - (width / 2);
      const top = (window.innerHeight / 2) - (height / 2);
      window.open(url, 'SagaLogin', `width=${width},height=${height},top=${top},left=${left}`);
    } catch (error) {
      toast.error("Não foi possível iniciar o login.");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('gemini_token');
    localStorage.removeItem('gemini_user');
    setIsLoggedIn(false);
    toast.success("Logout da IA realizado com sucesso!");
  };

  useEffect(() => {
    const handleAuthSuccess = () => {
      setIsLoggedIn(true);
    };
    window.addEventListener('authSuccess', handleAuthSuccess);
    return () => window.removeEventListener('authSuccess', handleAuthSuccess);
  }, []);

  useEffect(() => {
    const initialize = async () => {
      setIsLoading(true);
      try {
        const projectList = await loadProjectList();
        const lastProject = localStorage.getItem(LAST_PROJECT_KEY);
        // if (lastProject && projectList.includes(lastProject)) {
        //   await openProject(lastProject);
        // }
      } catch (error) {
        toast.error("Falha ao conectar com o backend.");
      } finally {
        setIsLoading(false);
      }
    };
    initialize();
  }, [loadProjectList, openProject]);

  if (isLoading) {
    return <div className="w-full h-screen bg-gray-950 flex items-center justify-center text-purple-400"><p>Carregando Saga Engine...</p></div>;
  }

  if (!project) {
    return (
      <div className="h-screen bg-gray-950 text-white font-sans flex flex-col">
        <Toaster position="bottom-right" toastOptions={{ style: { background: '#2a2a2a', color: '#e5e5e5', border: '1px solid rgba(255,255,255,0.1)' } }} />

        <WelcomeScreen
          onOpenProject={openProject}
          onCreateProject={handleCreateProject}
          projects={projects}
          onLogin={handleLogin}
          onOpenSettings={() => setIsSettingsOpen(true)}
          isOpeningProject={isOpening}
        />

        {isSettingsOpen && (
          <SettingsPanel
            onClose={() => setIsSettingsOpen(false)}
            project={null}
          />
        )}

        <ConfirmModal
          isOpen={!!deletionTarget}
          onClose={() => setDeletionTarget(null)}
          onConfirm={handleConfirmDelete}
          title={`Confirmar Exclusão`}
          message={`Você tem certeza que deseja deletar este ${deletionTarget?.type}? Esta ação não pode ser desfeita.`}
        />
      </div>
    );
  }

  // RENDERIZAÇÃO CONDICIONAL: JOGO OU EDITOR
  if (isPlaying) {
    return (
      <GamePlayer
        project={project}
        initialSceneId={activeSceneId || project.start_scene}
        onClose={() => setIsPlaying(false)}
      />
    );
  }

  const activeScene = project.scenes[activeSceneId] || null;

  // Extraction Mode Handlers
  const handleSelectionComplete = async (points: { x: number, y: number }[]) => {
    if (!activeScene || !project) {
      toast.error("Nenhuma cena ativa!");
      setIsExtractionMode(false);
      return;
    }

    const toastId = toast.loading("Extraindo objeto...");

    try {
      // Find the source background image from the background object
      const bgObj = activeScene.objects.find(o => o.type === 'background' || o.name === 'Background');
      const sourceImage = bgObj?.sprite;

      if (!sourceImage) {
        toast.error("Nenhum objeto de fundo encontrado na cena!");
        setIsExtractionMode(false);
        return;
      }

      // Load background image to get real dimensions
      const bgUrl = getAssetUrl(project.name, sourceImage);
      const img = new Image();

      await new Promise((resolve, reject) => {
        img.onload = resolve;
        img.onerror = reject;
        img.src = bgUrl;
      });

      const realWidth = img.width;
      const realHeight = img.height;
      const canvasWidth = 1920; // BASE_WIDTH from SceneCanvas
      const canvasHeight = 1080; // BASE_HEIGHT from SceneCanvas

      console.log(`Canvas: ${canvasWidth}x${canvasHeight}, Real Image: ${realWidth}x${realHeight}`);

      // Convert coordinates from canvas space to real image space
      const convertedPoints = points.map(p => ({
        x: Math.round((p.x / canvasWidth) * realWidth),
        y: Math.round((p.y / canvasHeight) * realHeight)
      }));

      console.log("Original points:", points);
      console.log("Converted points:", convertedPoints);

      const response = await api.post('/api/genai/edit/extract-object', {
        project_name: project.name,
        scene_id: activeSceneId,
        image_path: sourceImage,
        selection_points: convertedPoints
      });

      const { new_background_path, new_sprite_path, real_bbox_pixels } = response.data;

      // Criar um novo objeto com o sprite extraído
      // Calcular dimensões no canvas baseadas nos pixels reais retornados
      const spriteCanvasWidth = Math.round((real_bbox_pixels.width / realWidth) * canvasWidth);
      const spriteCanvasHeight = Math.round((real_bbox_pixels.height / realHeight) * canvasHeight);

      // Calcular posição no canvas (SAGA usa o centro do objeto)
      const canvasPosition = {
        x: Math.round(((real_bbox_pixels.left + real_bbox_pixels.width / 2) / realWidth) * canvasWidth),
        y: Math.round(((real_bbox_pixels.top + real_bbox_pixels.height / 2) / realHeight) * canvasHeight)
      };

      const newObjectId = `extracted_${uuidv4().slice(0, 8)}`;
      const newObject: GameObject = {
        id: newObjectId,
        name: "Objeto Extraído",
        type: 'sprite',
        sprite: new_sprite_path,
        position: canvasPosition,
        origin: canvasPosition,
        size: { width: spriteCanvasWidth, height: spriteCanvasHeight },
        scale: { x: 1, y: 1 },
        rotation: 0,
        zIndex: 10,
        properties: {},
        actions: [],
        ses: ""
      };

      // Create the updated project state ATOMICALLY
      setProject(prev => {
        if (!prev) return prev;

        const currentScene = prev.scenes[activeSceneId];
        const newBackgroundPath = `${new_background_path}?t=${Date.now()}`;

        // Find or Create background object
        let bgFound = false;
        const updatedObjects = (currentScene.objects || []).map(obj => {
          if (obj.type === 'background' || obj.name === 'Background') {
            bgFound = true;
            return { ...obj, sprite: newBackgroundPath };
          }
          return obj;
        });

        const backgroundObjects = bgFound ? updatedObjects : [
          ...updatedObjects,
          {
            id: `background_${uuidv4().slice(0, 8)}`,
            name: "Background",
            type: 'background' as const,
            sprite: newBackgroundPath,
            position: { x: 960, y: 540 },
            origin: { x: 960, y: 540 },
            size: { width: 1920, height: 1080 },
            scale: { x: 1, y: 1 },
            rotation: 0,
            zIndex: 0,
            properties: {},
            actions: [],
            ses: ""
          }
        ];

        const { background, ...sceneWithoutOldBg } = currentScene as any;

        const newProject = {
          ...prev,
          scenes: {
            ...prev.scenes,
            [activeSceneId]: {
              ...sceneWithoutOldBg,
              objects: [...backgroundObjects, newObject]
            }
          }
        };

        handleSaveProject(newProject);
        return newProject;
      });

      toast.success("Objeto extraído com sucesso!", { id: toastId });
      setSelectedObjectId(newObjectId);

    } catch (error: any) {
      console.error("Erro na extração:", error);
      toast.error(error.response?.data?.detail || "Erro ao extrair objeto", { id: toastId });
    } finally {
      setIsExtractionMode(false);
    }
  };

  // Expor essa função para o AIPanel ou Sidebar usar
  const startExtraction = (prompt: string) => {
    setExtractionPrompt(prompt);
    setIsExtractionMode(true);
    toast("Modo de Seleção Ativado! Circule o objeto.", { icon: '✂️' });
  };

  return (
    <div className="h-screen bg-gray-950 text-white font-sans flex flex-col">
      <Toaster position="bottom-right" toastOptions={{ style: { background: '#2a2a2a', color: '#e5e5e5' } }} />

      <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
        <Header
          projectName={project.name}
          onSave={() => handleSaveProject(project)}
          onClose={handleCloseProject}
          onOpenSettings={() => setIsSettingsOpen(true)}
          onPlay={() => setIsPlaying(true)} // Conectado
          isLoggedIn={isLoggedIn}
          onLogin={handleLogin}
          onLogout={handleLogout}
        />

        {isSettingsOpen && (
          <SettingsPanel
            onClose={() => setIsSettingsOpen(false)}
            project={project}
            onSaveProject={handleSaveProject}
          />
        )}

        <div className="flex-1 flex overflow-hidden">
          <Sidebar
            project={project}
            activeSceneId={activeSceneId}
            selectedObjectId={selectedObjectId}
            onSelectScene={handleSelectScene}
            onSelectObject={setSelectedObjectId}
            onDeleteScene={(sceneId) => setDeletionTarget({ type: 'scene', id: sceneId })}
            onDeleteObject={(sceneId, objectId) => setDeletionTarget({ type: 'object', id: objectId, sceneId })}
            onCreateScene={handleCreateScene}
            onCreateObject={handleCreateObject}
            onRenameScene={handleRenameScene}
            onSaveProperties={handleSaveProperties}
            onSetSceneBackground={handleSetSceneBackground}
            onMagicPartAnimate={handleMagicAnimatePart}
            onStartExtraction={startExtraction}
            resizable={leftSidebar}
          />

          <SceneCanvas
            key={activeSceneId}
            project={project}
            scene={activeScene}
            selectedObjectId={selectedObjectId}
            onSelectObject={setSelectedObjectId}
            selectionMode={isExtractionMode}
            onSelectionComplete={handleSelectionComplete}
            onScaleChange={setCanvasScale}
          />

          <AIPanel
            project={project}
            activeScene={activeScene}
            selectedObjectId={selectedObjectId}
            onProjectUpdate={() => openProject(project.name)}
            resizable={rightAIPanel}
            onStartExtraction={startExtraction}
          />
        </div>
      </DndContext>

      <ConfirmModal
        isOpen={!!deletionTarget}
        onClose={() => setDeletionTarget(null)}
        onConfirm={handleConfirmDelete}
        title={`Confirmar Exclusão`}
        message={`Você tem certeza que deseja deletar este ${deletionTarget?.type}? Esta ação não pode ser desfeita.`}
      />
    </div >
  );
}
