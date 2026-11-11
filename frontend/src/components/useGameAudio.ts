// The game's sound, from what the engine says (view.ambient, view.object_sounds, result.sounds):
// - the scene's background sound loops and crossfades when it changes (another scene, a variant);
// - objects here sound in a loop (a clock) or now and then (a crow), and stop when they leave;
// - the 'play "..."' of a turn sound once.
// Everything goes through one master gain (mute) and, in RETRO mode, a crude 8-bit filter.
import { useCallback, useEffect, useRef } from 'react';
import { getAssetUrl } from '../services/api';

export interface ObjectSound { id: string; file: string; mode: 'loop' | 'random'; every: [number, number] }

const VOLUME = { ambient: 0.45, object: 0.35, random: 0.6, event: 0.9 };
const FADE = 1.5;   // seconds

interface Loop { url: string; src: AudioBufferSourceNode; gain: GainNode }
interface ObjectVoice { key: string; loop?: Loop; timer?: number }

export function useGameAudio(projectName: string, ambient: string | null | undefined,
                             objectSounds: ObjectSound[] | undefined, muted: boolean, retro: boolean) {
  const ctxRef = useRef<AudioContext | null>(null);
  const masterRef = useRef<GainNode | null>(null);
  const retroRef = useRef<{ shaper: WaveShaperNode; filter: BiquadFilterNode } | null>(null);
  const buffers = useRef(new Map<string, Promise<AudioBuffer | null>>());
  const ambientRef = useRef<Loop | null>(null);
  const voices = useRef(new Map<string, ObjectVoice>());

  const url = (file: string) => getAssetUrl(projectName, file) || '';
  const opts = useRef({ muted, retro });
  opts.current = { muted, retro };

  // master -> (RETRO: fewer levels and a dull top end, like an 8-bit machine) -> speakers
  const route = useCallback(() => {
    const c = ctxRef.current, m = masterRef.current;
    if (!c || !m) return;
    m.gain.setTargetAtTime(opts.current.muted ? 0 : 1, c.currentTime, 0.05);
    m.disconnect();
    if (!opts.current.retro) {
      m.connect(c.destination);
      return;
    }
    if (!retroRef.current) {
      const shaper = c.createWaveShaper();
      const steps = 32, n = 2048, curve = new Float32Array(n);
      for (let i = 0; i < n; i++) curve[i] = Math.round(((i / (n - 1)) * 2 - 1) * steps) / steps;
      shaper.curve = curve;
      const filter = c.createBiquadFilter();
      filter.type = 'lowpass';
      filter.frequency.value = 3800;
      shaper.connect(filter).connect(c.destination);
      retroRef.current = { shaper, filter };
    }
    m.connect(retroRef.current.shaper);
  }, []);

  const ctx = useCallback((): AudioContext | null => {
    if (!ctxRef.current) {
      const AC = window.AudioContext || (window as any).webkitAudioContext;
      if (!AC) return null;
      const c: AudioContext = new AC();
      ctxRef.current = c;
      masterRef.current = c.createGain();
      route();
    }
    if (ctxRef.current.state === 'suspended') ctxRef.current.resume().catch(() => { /* needs a gesture */ });
    return ctxRef.current;
  }, []);

  const load = useCallback((u: string): Promise<AudioBuffer | null> => {
    let p = buffers.current.get(u);
    if (!p) {
      p = fetch(u).then(r => (r.ok ? r.arrayBuffer() : Promise.reject(r.status)))
        .then(data => ctx()!.decodeAudioData(data))
        .catch(() => null);                       // a missing sound is silence, never an error
      buffers.current.set(u, p);
    }
    return p;
  }, [ctx]);

  const start = useCallback(async (u: string, volume: number, loop: boolean): Promise<Loop | null> => {
    const c = ctx();
    const buf = await load(u);
    if (!c || !buf || !masterRef.current) return null;
    const src = c.createBufferSource();
    src.buffer = buf;
    src.loop = loop;
    const gain = c.createGain();
    gain.gain.setValueAtTime(loop ? 0 : volume, c.currentTime);
    if (loop) gain.gain.linearRampToValueAtTime(volume, c.currentTime + FADE);
    src.connect(gain).connect(masterRef.current);
    src.start();
    return { url: u, src, gain };
  }, [ctx, load]);

  const stop = (l: Loop | null | undefined) => {
    const c = ctxRef.current;
    if (!l || !c) return;
    l.gain.gain.cancelScheduledValues(c.currentTime);
    l.gain.gain.setValueAtTime(l.gain.gain.value, c.currentTime);
    l.gain.gain.linearRampToValueAtTime(0, c.currentTime + FADE);
    try { l.src.stop(c.currentTime + FADE + 0.05); } catch { /* already stopped */ }
  };

  // the scene's background sound: crossfade when it changes
  useEffect(() => {
    const u = ambient ? url(ambient) : '';
    if ((ambientRef.current?.url || '') === u) return;
    stop(ambientRef.current);
    ambientRef.current = null;
    if (!u) return;
    let cancelled = false;
    start(u, VOLUME.ambient, true).then(l => {
      if (cancelled) stop(l); else ambientRef.current = l;
    });
    return () => { cancelled = true; };
  }, [ambient, projectName]);

  // the objects' sounds: start what came, stop what left
  useEffect(() => {
    const want = new Map((objectSounds || []).map(s => [s.id, s]));
    voices.current.forEach((v, id) => {
      const s = want.get(id);
      if (!s || `${s.file}|${s.mode}` !== v.key) {
        stop(v.loop);
        if (v.timer) window.clearTimeout(v.timer);
        voices.current.delete(id);
      }
    });
    want.forEach((s, id) => {
      if (voices.current.has(id)) return;
      const voice: ObjectVoice = { key: `${s.file}|${s.mode}` };
      voices.current.set(id, voice);
      const u = url(s.file);
      if (s.mode === 'loop') {
        start(u, VOLUME.object, true).then(l => {
          if (voices.current.get(id) === voice) voice.loop = l ?? undefined; else stop(l);
        });
      } else {
        const [lo, hi] = s.every || [20, 60];
        const next = () => {
          voice.timer = window.setTimeout(() => {
            if (voices.current.get(id) !== voice) return;
            start(u, VOLUME.random, false);
            next();
          }, (lo + Math.random() * Math.max(0, hi - lo)) * 1000);
        };
        next();
      }
    });
  }, [JSON.stringify(objectSounds || []), projectName]);

  // mute / RETRO changed
  useEffect(() => { route(); }, [muted, retro, route]);

  // leaving the player: silence and free the audio device
  useEffect(() => () => {
    voices.current.forEach(v => v.timer && window.clearTimeout(v.timer));
    voices.current.clear();
    ctxRef.current?.close().catch(() => { /* already closed */ });
    ctxRef.current = null;
  }, []);

  // the 'play "..."' of a turn
  const playEvents = useCallback((files: (string | null | undefined)[]) => {
    files.filter(Boolean).forEach(f => start(url(f!), VOLUME.event, false));
  }, [start, projectName]);

  return { playEvents };
}
