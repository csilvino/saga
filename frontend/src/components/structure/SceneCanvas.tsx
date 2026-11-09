import React, { useRef, useEffect, useState } from 'react';
import type { Project, Scene } from '../../types';
import { getAssetUrl } from '../../services/api';
import { DraggableObject } from '../dnd';
import { Image as ImageIcon } from 'lucide-react';

interface SelectionPoint {
  x: number;
  y: number;
}

interface SceneCanvasProps {
  project: Project;
  scene: Scene | null;
  selectedObjectId: string | null;
  onSelectObject: (objectId: string | null) => void;
  selectionMode?: boolean;
  onSelectionComplete?: (points: SelectionPoint[]) => void;
  onScaleChange?: (scale: number) => void;
}

const BASE_WIDTH = 1920;
const BASE_HEIGHT = 1080;

const SceneCanvasComponent: React.FC<SceneCanvasProps> = ({
  project, scene, selectedObjectId, onSelectObject,
  selectionMode = false, onSelectionComplete, onScaleChange
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);

  // Selection State
  const [selectionPoints, setSelectionPoints] = useState<SelectionPoint[]>([]);
  const [mousePos, setMousePos] = useState<SelectionPoint | null>(null);

  useEffect(() => {
    const updateScale = () => {
      if (containerRef.current) {
        const { width, height } = containerRef.current.getBoundingClientRect();
        const scaleX = width / BASE_WIDTH;
        setScale(scaleX);
        if (onScaleChange) onScaleChange(scaleX);
      }
    };

    const resizeObserver = new ResizeObserver(updateScale);
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }
    updateScale();
    return () => resizeObserver.disconnect();
  }, []);

  // Reset selection when mode changes
  useEffect(() => {
    if (!selectionMode) {
      setSelectionPoints([]);
      setMousePos(null);
    }
  }, [selectionMode]);

  if (!scene) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-900 text-gray-600">
        <p>Selecione uma cena no Explorer ou peça para a IA criar uma.</p>
      </div>
    );
  }

  const bgObj = scene.objects.find(o => o.type === 'background' || o.name === 'Background');
  const backgroundUrl = bgObj?.sprite ? getAssetUrl(project.name, bgObj.sprite) : null;

  const handleCanvasClick = (e: React.MouseEvent) => {
    if (!selectionMode) {
      if (e.target === e.currentTarget) {
        onSelectObject(null);
      }
      return;
    }

    // Lasso Logic
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      // Since the inner div is scaled, we need to map the click to the logical 1920x1080 space
      // The click e.clientX is global. rect.left is global.
      // offsetX relative to the container *before* scale?
      // Let's use standard calculation:

      // Calculate click position relative to the container's top-left
      const rawX = e.clientX - rect.left;
      const rawY = e.clientY - rect.top;

      // Apply inverse scale to get logical coordinates
      const x = rawX / scale;
      const y = rawY / scale;

      // Clamping
      const finalX = Math.max(0, Math.min(BASE_WIDTH, x));
      const finalY = Math.max(0, Math.min(BASE_HEIGHT, y));

      setSelectionPoints(prev => [...prev, { x: finalX, y: finalY }]);
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (selectionMode && containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const rawX = e.clientX - rect.left;
      const rawY = e.clientY - rect.top;
      const x = Math.max(0, Math.min(BASE_WIDTH, rawX / scale));
      const y = Math.max(0, Math.min(BASE_HEIGHT, rawY / scale));
      setMousePos({ x, y });
    }
  };

  const handleRightClick = (e: React.MouseEvent) => {
    if (selectionMode) {
      e.preventDefault();
      if (selectionPoints.length > 2 && onSelectionComplete) {
        onSelectionComplete(selectionPoints);
        setSelectionPoints([]); // Ou manter até confirmar? Vamos limpar por enquanto.
      }
    }
  };

  return (
    <div className="flex-1 flex items-center justify-center p-8 bg-gradient-to-br from-gray-900 to-gray-950 overflow-hidden"
      onClick={handleCanvasClick}
      onMouseMove={handleMouseMove}
      onContextMenu={handleRightClick}
      style={{ cursor: selectionMode ? 'crosshair' : 'default' }}
    >
      <div ref={containerRef} className="relative w-full max-w-6xl aspect-video bg-gray-800 rounded-lg border-2 border-purple-500/30 shadow-2xl shadow-purple-500/20 overflow-hidden">

        {/* Camada Lógica (1920x1080) Scaled */}
        <div style={{
          width: `${BASE_WIDTH}px`,
          height: `${BASE_HEIGHT}px`,
          transform: `scale(${scale})`,
          transformOrigin: 'top left',
          backgroundImage: backgroundUrl ? `url("${backgroundUrl}")` : 'none',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
        }}
          className="relative"
        >
          {!backgroundUrl && (
            <div className="w-full h-full flex flex-col items-center justify-center text-purple-400/30">
              <ImageIcon size={128} />
              <p className="mt-4 text-2xl">Cena sem background</p>
            </div>
          )}

          {/* Objects (Disabled pointer events during selection to avoid selecting them) */}
          <div style={{ pointerEvents: selectionMode ? 'none' : 'auto' }}>
            {scene.objects.map(obj => (
              <DraggableObject
                key={obj.id}
                obj={obj}
                project={project}
                selected={!selectionMode && selectedObjectId === obj.id}
                onClick={() => !selectionMode && onSelectObject(obj.id)}
              />
            ))}
          </div>

          {/* Selection Overlay */}
          {selectionMode && (
            <svg className="absolute top-0 left-0 w-full h-full pointer-events-none" style={{ zIndex: 999 }}>
              {/* Lines to previous points */}
              <polyline
                points={selectionPoints.map(p => `${p.x},${p.y}`).join(' ')}
                fill="none"
                stroke="#a855f7"
                strokeWidth="4"
                strokeDasharray="10 5"
              />

              {/* Closing line preview */}
              {selectionPoints.length > 0 && mousePos && (
                <line
                  x1={selectionPoints[selectionPoints.length - 1].x}
                  y1={selectionPoints[selectionPoints.length - 1].y}
                  x2={mousePos.x}
                  y2={mousePos.y}
                  stroke="#a855f7"
                  strokeWidth="2"
                  opacity="0.5"
                />
              )}

              {/* Points */}
              {selectionPoints.map((p, i) => (
                <circle key={i} cx={p.x} cy={p.y} r="6" fill="#d8b4fe" stroke="#581c87" strokeWidth="2" />
              ))}

              {/* Start Point Highlight (Close Loop hint) */}
              {selectionPoints.length > 2 && (
                <circle cx={selectionPoints[0].x} cy={selectionPoints[0].y} r="10" fill="none" stroke="#22c55e" strokeWidth="3" opacity="0.8" />
              )}
            </svg>
          )}

          {selectionMode && (
            <div className="absolute top-4 left-4 bg-black/80 text-white p-4 rounded-lg backdrop-blur-md border border-purple-500/50 pointer-events-none">
              <h3 className="font-bold text-purple-300">Modo de Seleção (Lasso)</h3>
              <p className="text-sm text-gray-300">1. Clique para marcar pontos ao redor do objeto.</p>
              <p className="text-sm text-gray-300">2. Botão Direito para <b>Finalizar</b>.</p>
              <p className="text-sm text-gray-400 mt-2">Pontos: {selectionPoints.length}</p>
            </div>
          )}

        </div>
      </div>
    </div>
  );
};

export const SceneCanvas = React.memo(SceneCanvasComponent);
