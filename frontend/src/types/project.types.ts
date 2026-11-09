export interface Project {
  name: string;
  version: string;
  start_scene: string;
  navigation_mode: 'pathfinding' | 'first_person';
  metadata: {
    author: string;
    description: string;
  };
  scenes: Record<string, Scene>;
  assets: {
    sprites: Record<string, any>;
    audio: Record<string, any>;
    fonts: Record<string, any>;
    items: Record<string, any>;
  };
  dialogs: Record<string, any>;
  scripts: Record<string, any>;
}

export interface Scene {
  id: string;
  name: string;
  description?: string;
  size: { width: number; height: number };
  hotspots: Hotspot[];
  objects: GameObject[];
  ses?: string;
}

export interface Hotspot {
  id: string;
  name: string;
  shape: { type: string; points: number[][] };
  action: { type: string; params: any };
  visible: boolean;
  enabled: boolean;
}

export interface SpriteSheetAnimation {
  type: 'sprite_sheet';
  frameCount: number;       // Total de frames na animação
  frameWidth: number;       // Largura de um único frame
  frameHeight: number;      // Altura de um único frame
  fps: number;              // Frames por segundo
  loop: boolean;            // A animação repete?
}

export type Animation = SpriteSheetAnimation; // Futuramente podemos ter | RotateAnimation | etc.

export interface GameObject {
  id: string;
  type: string;
  sprite: string; // Agora pode ser um sprite sheet
  position: { x: number; y: number };
  animation?: Animation;
}
