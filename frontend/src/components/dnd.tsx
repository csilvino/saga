import React, { useState, useEffect } from 'react';
import { useDraggable, useDroppable } from '@dnd-kit/core';
import { Image as ImageIcon, Trash2, Music, FileAudio } from 'lucide-react';
import { toast } from 'react-hot-toast';
import type { GameObject, Hotspot, Project } from '../types';
import { getAssetUrl } from '../services/api';

export const DraggableAsset = ({ projectName, filePath, onSetBackground, onDeleteAsset, currentSceneId }) => {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({
    id: `asset-${filePath}`,
    data: { filePath, type: 'asset' },
  });

  const style = transform ? {
    transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`,
  } : undefined;

  const assetUrl = getAssetUrl(projectName, filePath);

  return (
    <div ref={setNodeRef} style={style} {...listeners} {...attributes} className="group relative aspect-square bg-gray-800 rounded-lg overflow-hidden border-2 border-transparent hover:border-purple-500 cursor-grab">
      {assetUrl && <img src={assetUrl} alt={filePath} className="w-full h-full object-cover pointer-events-none" />}
      <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
        <button
          onClick={(e) => {
            e.stopPropagation();
            if (!currentSceneId) {
              toast.error("Abra uma cena primeiro para definir o fundo!");
              return;
            }
            onSetBackground(filePath, currentSceneId);
          }}
          className="p-2 rounded-full bg-black/50 hover:bg-purple-500 text-white transition-colors"
          title="Definir como Fundo"
        >
          <ImageIcon className="w-4 h-4" />
        </button>
        <button onClick={(e) => { e.stopPropagation(); onDeleteAsset(filePath); }} className="p-2 rounded-full bg-black/50 hover:bg-red-500 text-white transition-colors" title="Deletar Asset">
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

export const DraggableObject = ({ obj, project, selected, onClick }: { obj: GameObject, project: Project, selected: boolean, onClick: (id: string) => void }) => {
  const { attributes, listeners, setNodeRef, transform: dragTransform, isDragging } = useDraggable({
    id: `object-${obj.id}`,
    data: { objectId: obj.id, type: 'object' },
  });

  const [currentFrame, setCurrentFrame] = useState(0);
  const [animatedValue, setAnimatedValue] = useState(0);

  useEffect(() => {
    // Pausa animações durante o arrasto para melhorar performance
    if (isDragging) return;

    if (obj.animation?.type === 'sprite_sheet') {
      const { fps, frameCount, loop } = obj.animation;
      const interval = setInterval(() => {
        setCurrentFrame(prevFrame => {
          const nextFrame = prevFrame + 1;
          if (nextFrame >= frameCount) {
            return loop ? 0 : prevFrame;
          }
          return nextFrame;
        });
      }, 1000 / fps);
      return () => clearInterval(interval);
    } else if (obj.animation?.type === 'transform') {
      const { min, max, duration } = obj.animation;
      let start: number | null = null;
      let frameHandle: number;

      const animate = (time: number) => {
        if (!start) start = time;
        const elapsed = (time - start) / 1000;
        const cycle = (elapsed % (duration * 2)) / duration;
        const t = cycle > 1 ? 2 - cycle : cycle;

        // Easing simples (senoidal para suavizar as pontas)
        const easedT = (1 - Math.cos(t * Math.PI)) / 2;
        const value = min + (max - min) * easedT;

        setAnimatedValue(value);
        frameHandle = requestAnimationFrame(animate);
      };

      frameHandle = requestAnimationFrame(animate);
      return () => cancelAnimationFrame(frameHandle);
    }
  }, [obj.animation, isDragging]);

  const isAnimatedSprite = obj.animation?.type === 'sprite_sheet';

  // Fallback para posição
  const position = obj.position || { x: 0, y: 0 };

  const baseStyle: React.CSSProperties = {
    left: `${position.x}px`,
    top: `${position.y}px`,
    width: `${obj.size?.width || 100}px`,
    height: `${obj.size?.height || 100}px`,
    zIndex: obj.zIndex || 10,
    position: 'absolute',
    cursor: isDragging ? 'grabbing' : 'grab',
    // Remove transições durante o arrasto para evitar lag visual
    transition: isDragging ? 'none' : 'all 0.1s ease-out',
  };

  // Combine static rotation/scale with animated ones
  let finalRotation = obj.rotation || 0;
  let scaleX = obj.scale?.x || 1;
  let scaleY = obj.scale?.y || 1;

  if (obj.animation?.type === 'transform' && !isDragging) {
    const anim = obj.animation;
    if (anim.property === 'rotation') {
      finalRotation += animatedValue;
    } else if (anim.property === 'scale') {
      const factor = 1 + animatedValue / 100;
      if (!anim.subProperty || anim.subProperty === 'x') scaleX *= factor;
      if (!anim.subProperty || anim.subProperty === 'y') scaleY *= factor;
    }
  }

  const anchor = obj.anchor || { x: 0.5, y: 0.5 };
  const anchorX = anchor.x * 100;
  const anchorY = anchor.y * 100;

  const transformStyle: React.CSSProperties = {
    transformOrigin: `${anchorX}% ${anchorY}%`,
    transform: dragTransform
      ? `translate3d(${dragTransform.x}px, ${dragTransform.y}px, 0) translate(${-anchorX}%, ${-anchorY}%) rotate(${finalRotation}deg) scale(${scaleX}, ${scaleY})`
      : `translate(${-anchorX}%, ${-anchorY}%) rotate(${finalRotation}deg) scale(${scaleX}, ${scaleY})`
  };

  const spriteUrl = getAssetUrl(project.name, obj.sprite);

  if (!spriteUrl || obj.type === 'music' || obj.type === 'sound') {
    return (
      <div
        ref={setNodeRef}
        style={{ ...baseStyle, ...transformStyle }}
        {...listeners}
        {...attributes}
        onClick={(e) => { e.stopPropagation(); onClick(obj.id); }}
        className={`flex items-center justify-center rounded-lg shadow-lg border-2 p-2 ${selected ? 'bg-purple-600/40 border-purple-500 ring-2 ring-purple-500/50' : 'bg-gray-800/60 border-gray-700/50 hover:bg-gray-700/80 hover:border-purple-500/50'} ${obj.type === 'music' || obj.type === 'sound' ? 'backdrop-blur-sm' : 'border-dashed'}`}
      >
        <div className="flex flex-col items-center gap-1 overflow-hidden">
          {obj.type === 'music' && <Music size={24} className="text-purple-400" />}
          {obj.type === 'sound' && <FileAudio size={24} className="text-blue-400" />}
          {!obj.type || (obj.type !== 'music' && obj.type !== 'sound') && <ImageIcon size={24} className="text-gray-500" />}
          <span className="text-[10px] font-medium text-gray-300 truncate max-w-full px-1">{obj.name}</span>
        </div>
      </div>
    );
  }

  if (obj.animation?.type === 'sprite_sheet') {
    const anim = obj.animation;
    const { frameWidth, frameHeight } = anim;
    const backgroundPositionX = -(currentFrame * frameWidth);

    const animationStyle: React.CSSProperties = {
      ...baseStyle,
      ...transformStyle,
      backgroundImage: `url("${spriteUrl}")`,
      backgroundSize: `${anim.frameCount * 100}% 100%`,
      backgroundPosition: anim.frameCount > 1 ? `${(currentFrame / (anim.frameCount - 1)) * 100}% 0%` : '0% 0%',
      backgroundRepeat: 'no-repeat',
    };

    return (
      <div
        ref={setNodeRef}
        style={animationStyle}
        {...listeners}
        {...attributes}
        onClick={(e) => { e.stopPropagation(); onClick(obj.id); }}
        className={`${selected ? 'outline outline-4 outline-purple-500' : ''}`}
      />
    );
  }

  return (
    <div
      ref={setNodeRef}
      style={{ ...baseStyle, ...transformStyle }}
      {...listeners}
      {...attributes}
      onClick={(e) => { e.stopPropagation(); onClick(obj.id); }}
      className={`${selected ? 'outline outline-4 outline-purple-500' : ''}`}
    >
      <img
        src={spriteUrl}
        alt={obj.name}
        className="pointer-events-none w-full h-full"
      />
    </div>
  );
};


export const DraggableInventoryItem = ({ item, project }: { item: any, project: Project }) => {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({
    id: `inventory-item-${item.id}`,
    data: { itemId: item.id, type: 'inventory-item', icon: item.icon },
  });

  const style = transform ? {
    transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`,
    zIndex: 1000,
    opacity: 0,
  } : undefined;

  const iconUrl = getAssetUrl(project.name, item.icon);

  return (
    <div ref={setNodeRef} style={style} {...listeners} {...attributes} className="w-12 h-12 bg-gray-800 rounded-lg border border-gray-700 flex items-center justify-center hover:border-purple-500 transition-colors cursor-grab active:cursor-grabbing group relative">
      {iconUrl ? (
        <img src={iconUrl} alt={item.name} className="w-8 h-8 object-contain pointer-events-none" />
      ) : (
        <span className="text-xs text-gray-500">{item ? item.name[0] : '?'}</span>
      )}
      {item && (
        <div className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 bg-black/80 text-white text-xs px-2 py-1 rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
          {item.name}
        </div>
      )}
    </div>
  );
};

export const DroppableHotspot = ({ hotspot, isPlayMode, selectedHotspotId, onSelectHotspot, onExecuteActions, onHotspotContextMenu }) => {
  const { setNodeRef, isOver } = useDroppable({
    id: `hotspot-${hotspot.id}`,
    data: { hotspotId: hotspot.id, type: 'hotspot' },
    disabled: !isPlayMode,
  });

  return (
    <div
      ref={setNodeRef}
      key={hotspot.id}
      className={`absolute cursor-pointer transition-all ${isPlayMode ? '' : 'pointer-events-auto'} ${!isPlayMode && selectedHotspotId === hotspot.id ? 'bg-yellow-500/40 border-2 border-solid border-yellow-400' : 'bg-purple-500/30 hover:bg-purple-500/50 border-2 border-dashed border-purple-400'} ${isOver && isPlayMode ? 'bg-green-500/40 border-2 border-solid border-green-400' : ''}`}
      style={{ clipPath: `polygon(${hotspot.shape.points.map(p => `${(p[0] / 1920) * 100}% ${(p[1] / 1080) * 100}%`).join(', ')})`, width: '100%', height: '100%' }}
      onClick={(e) => {
        e.stopPropagation();
        if (isPlayMode) {
          onExecuteActions(hotspot.actions);
        } else {
          onSelectHotspot(hotspot.id);
        }
      }}
      onContextMenu={(e) => !isPlayMode && onHotspotContextMenu(e, hotspot)}
    >
      {!isPlayMode && <span className="text-white text-xs font-bold absolute p-1 bg-black/50 rounded" style={{ left: `${(hotspot.shape.points[0][0] / 1920) * 100}%`, top: `${(hotspot.shape.points[0][1] / 1080) * 100}%` }}>{hotspot.name}</span>}
    </div>
  );
};
