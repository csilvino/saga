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
  description?: string;      // what the player reads on "examinar"
  animation?: Animation;
  effect?: Effect;           // a looping effect from the ficha's 'animacao' (backend/ses/animation.py)
  parts?: ObjectPart[];      // moving parts drawn on top of the object (a clock's pendulum)
}

// swing/sway: amount in degrees; bob: scene pixels; flicker/pulse: glow strength 0-1
export interface Effect {
  type: 'swing' | 'sway' | 'bob' | 'flicker' | 'pulse';
  amount: number;
  period: number;            // seconds per cycle
  color?: string;
}

export interface ObjectPart {
  name: string;
  description: string;
  effect?: Effect | null;
  at: Point;                 // where it hangs from, fractions of the object's picture
  height: number;
  sprite?: string;
  rect?: { x: number; y: number; w: number; h: number };   // fractions of the object's picture
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
  description?: string;            // what the player reads on entering
  exits?: Record<string, string>;  // direction -> scene id
  ses?: string;
  effect?: Effect;                 // the whole picture: bob = rocks (at sea), flicker/pulse = light
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
