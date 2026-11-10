// RetroStage - the scene drawn like an 8-bit illustrated adventure: low resolution, reduced palette
// with ordered dithering, scaled up with hard pixels. Background and visible sprites are composed
// on one canvas so everything shares the same look; clicks still go to the DOM objects on top.
import React, { useEffect, useRef } from 'react';

export interface RetroSprite { url: string; x: number; y: number; w: number; h: number }   // 1920x1080 units

const W = 384, H = 216;              // 1920x1080 / 5
const LEVELS = 5;                    // per channel: 5^3 = 125 colours
const GAMMA = 0.75;                  // lifts the shadows: AI paintings are often very dark
const BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5].map(v => (v + 0.5) / 16 - 0.5);

const cache = new Map<string, Promise<HTMLImageElement>>();
const load = (url: string) => {
  if (!cache.has(url)) {
    cache.set(url, new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = url;
    }));
  }
  return cache.get(url)!;
};

const RetroStage: React.FC<{ background: string; sprites: RetroSprite[] }> = ({ background, sprites }) => {
  const ref = useRef<HTMLCanvasElement>(null);
  const key = background + '|' + sprites.map(s => `${s.url}@${s.x},${s.y},${s.w},${s.h}`).join('|');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const canvas = ref.current;
      if (!canvas || !background) return;
      try {
        const [bg, ...imgs] = await Promise.all([load(background), ...sprites.map(s => load(s.url))]);
        if (cancelled) return;
        const ctx = canvas.getContext('2d', { willReadFrequently: true })!;
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        ctx.drawImage(bg, 0, 0, W, H);
        sprites.forEach((s, i) => ctx.drawImage(imgs[i], s.x / 5, s.y / 5, s.w / 5, s.h / 5));
        const data = ctx.getImageData(0, 0, W, H);
        const d = data.data, step = 255 / (LEVELS - 1);
        // auto-levels: the 99th percentile of brightness becomes white, so dark scenes keep detail
        const lum: number[] = [];
        for (let i = 0; i < d.length; i += 4) lum.push((d[i] + d[i + 1] + d[i + 2]) / 3);
        lum.sort((a, b) => a - b);
        const hi = Math.max(60, lum[Math.floor(lum.length * 0.99)]);
        const lut = new Float32Array(256);
        for (let v = 0; v < 256; v++) lut[v] = 255 * Math.pow(Math.min(1, v / hi), GAMMA);
        for (let y = 0; y < H; y++) {
          for (let x = 0; x < W; x++) {
            const t = BAYER[(y & 3) * 4 + (x & 3)] * step;
            const i = (y * W + x) * 4;
            for (let c = 0; c < 3; c++) {
              d[i + c] = Math.max(0, Math.min(255, Math.round((lut[d[i + c]] + t) / step) * step));
            }
          }
        }
        ctx.putImageData(data, 0, 0);
      } catch {
        /* an image failed to load: the canvas keeps what it had */
      }
    })();
    return () => { cancelled = true; };
  }, [key]);

  return (
    <canvas ref={ref} width={W} height={H} className="absolute inset-0 w-full h-full"
            style={{ imageRendering: 'pixelated' }} />
  );
};

export default RetroStage;
