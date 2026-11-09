export interface Point {
  x: number;
  y: number;
}

export interface GameObject {
  id: string;
  name: string;
  type: string;
  sprite: string;
  position: Point;
  size?: { width: number; height: number };
  origin?: Point;
  scale: Point;
  rotation: number;
  anchor?: Point;
  zIndex: number;
  states?: { [key: string]: string };
  state?: string;
  visible?: boolean;
  properties?: { [key: string]: any };
  actions?: any[];
  ses?: string;
  animation?: Animation;
}

export type Animation = SpriteSheetAnimation | TransformAnimation;

export interface SpriteSheetAnimation {
  type: 'sprite_sheet';
  frameWidth: number;
  frameHeight: number;
  frameCount: number;
  fps: number;
  loop: boolean;
}

export interface TransformAnimation {
  type: 'transform';
  property: 'rotation' | 'scale' | 'position';
  subProperty?: 'x' | 'y';
  min: number;
  max: number;
  duration: number; // in seconds
  easing: 'linear' | 'easeInOut' | 'step';
}

export interface Hotspot {
  id: string;
  name: string;
  shape: {
    type: 'polygon';
    points: Array<[number, number]>;
  };
  actions: Action[];
}

export interface Action {
  id: string;
  type: string;
  payload: any;
}

export interface Scene {
  id: string;
  name: string;
  // background: string; // Removido
  objects: GameObject[];
  hotspots: Hotspot[];
}

export interface Project {
  id: string;
  name: string;
  start_scene: string;
  scenes: { [id: string]: Scene };
  assets: {
    sprites: { [key: string]: { path: string } };
    items: { [key: string]: { id: string; name: string; icon: string } };
    audio: any; // Define better if needed
  };
  dialogs: { [key: string]: any }; // Define better if needed
  inventory?: string[];
  launcher?: {
    title: string;
    description: string;
    flyer_image: string;
    launcher_music?: string;
    version: string;
  };
}
