// SceneArtList - where each scene's pictures come from, chosen per scene:
//   GPU local  - the local worker (FLUX on this PC)
//   API Gemini - the Gemini image model, with the creator's key (paid per image)
//   Web        - the creator makes them on a web AI (Gemini, ChatGPT...) with his own account:
//                this list gives the prompts to copy and takes the pictures back. The Saga crops
//                them, finds the objects, cuts out the loose objects and puts everything in place.
import React, { useState } from 'react';
import { Copy, Upload, Loader2, Globe, CheckCircle2, Circle, ExternalLink } from 'lucide-react';
import api, { getAssetUrl } from '../services/api';

export interface SceneArt {
  id: string; name: string; source: 'local' | 'gemini' | 'web'; background: string | null;
  sprites: number; sprites_done: number; variants: number; variants_done: number;
}
interface WebPrompts {
  scene: string; background: string | null; style_reference: string | null;
  background_prompt: string; sprites: string[]; sprites_prompt: string;
  variants: { index: number; when: string; done: boolean; prompt: string }[];
}

const SOURCES: { id: SceneArt['source']; label: string; title: string }[] = [
  { id: 'local', label: 'GPU local', title: 'Gerado no gerador local (FLUX, na placa de vídeo deste PC)' },
  { id: 'gemini', label: 'API Gemini', title: 'Gerado pela API de imagem da Gemini, com a sua chave (pago por imagem)' },
  { id: 'web', label: 'Web', title: 'Você gera numa IA da web (Gemini, ChatGPT...) com a sua conta e envia a imagem' },
];

const enc = encodeURIComponent;

const SceneArtList: React.FC<{ projectName: string; scenes: SceneArt[]; busy: boolean; onChanged: () => void }> =
  ({ projectName, scenes, busy, onChanged }) => {
  const [open, setOpen] = useState<string | null>(null);
  const [prompts, setPrompts] = useState<Record<string, WebPrompts>>({});
  const [working, setWorking] = useState('');
  const [msg, setMsg] = useState<{ scene: string; ok: boolean; text: string } | null>(null);

  const say = (scene: string, ok: boolean, text: string) => setMsg({ scene, ok, text });
  const fail = (scene: string, e: any) => say(scene, false, e.response?.data?.detail || String(e));

  const loadPrompts = async (s: SceneArt) => {
    setWorking(`${s.id}:prompts`);
    try {
      const r = await api.get(`/api/blueprint/web-art/${enc(projectName)}/${enc(s.id)}`);
      setPrompts(p => ({ ...p, [s.id]: r.data }));
    } catch (e) { fail(s.id, e); } finally { setWorking(''); }
  };

  const toggle = (s: SceneArt) => {
    const next = open === s.id ? null : s.id;
    setOpen(next);
    setMsg(null);
    if (next && !prompts[s.id]) loadPrompts(s);
  };

  const setSource = async (s: SceneArt, source: SceneArt['source']) => {
    try {
      await api.put(`/api/blueprint/art-source/${enc(projectName)}/${enc(s.id)}`, { source });
      onChanged();
      if (source === 'web' && open !== s.id) toggle({ ...s, source });
    } catch (e) { fail(s.id, e); }
  };

  const copy = async (scene: string, text: string) => {
    try { await navigator.clipboard.writeText(text); say(scene, true, 'Prompt copiado. Cole na IA da web.'); }
    catch { say(scene, false, 'O navegador não deixou copiar; selecione o texto e copie à mão.'); }
  };

  const upload = async (s: SceneArt, kind: string, file: File | undefined) => {
    if (!file) return;
    setWorking(`${s.id}:${kind}`);
    setMsg(null);
    try {
      const form = new FormData();
      form.append('file', file);
      const r = await api.post(`/api/blueprint/web-art/${enc(projectName)}/${enc(s.id)}/${enc(kind)}`, form,
                               { headers: { 'Content-Type': 'multipart/form-data' } });
      const d = r.data;
      const done = kind === 'background' ? `Cenário recebido${d.painted?.length ? `; achei: ${d.painted.join(', ')}` : ''}.`
        : kind === 'sprites' ? `Objetos recortados e encaixados: ${d.sprites.join(', ')}.`
        : `Variante "${d.variant}" recebida.`;
      say(s.id, !(d.problems?.length), [done, ...(d.problems || [])].join(' '));
      onChanged();
      loadPrompts(s);
    } catch (e) { fail(s.id, e); } finally { setWorking(''); }
  };

  const picker = (s: SceneArt, kind: string, label: string, disabled = false) => (
    <label className={`px-2 py-1 rounded flex items-center gap-1 cursor-pointer text-xs
                       ${disabled || busy ? 'bg-gray-800 text-gray-600 pointer-events-none' : 'bg-cyan-800 hover:bg-cyan-700 text-white'}`}>
      {working === `${s.id}:${kind}` ? <Loader2 size={12} className="animate-spin" /> : <Upload size={12} />} {label}
      <input type="file" accept="image/*" className="hidden" disabled={disabled || busy}
             onChange={e => { upload(s, kind, e.target.files?.[0]); e.target.value = ''; }} />
    </label>
  );

  const copyBtn = (scene: string, text: string) => (
    <button onClick={() => copy(scene, text)} className="px-2 py-1 rounded bg-gray-700 hover:bg-gray-600 text-xs flex items-center gap-1">
      <Copy size={12} /> Copiar prompt
    </button>
  );

  const link = (rel: string | null, label: string) => {
    const url = getAssetUrl(projectName, rel);
    return url ? (
      <a href={url} target="_blank" rel="noreferrer" className="text-cyan-400 hover:underline inline-flex items-center gap-0.5">
        {label}<ExternalLink size={10} />
      </a>
    ) : null;
  };

  const mark = (ok: boolean) => ok ? <CheckCircle2 size={12} className="text-green-400 shrink-0" />
                                   : <Circle size={12} className="text-gray-600 shrink-0" />;

  return (
    <div className="space-y-1">
      {scenes.map(s => {
        const p = prompts[s.id];
        const full = !!s.background && s.sprites_done === s.sprites && s.variants_done === s.variants;
        return (
          <div key={s.id} className="border border-gray-800 rounded-lg">
            <div className="flex items-center gap-2 px-2 py-1.5">
              {mark(full)}
              <span className="flex-1 truncate text-gray-200 text-xs" title={s.name}>{s.name}</span>
              <span className="text-[10px] text-gray-500" title="objetos soltos feitos / variantes feitas">
                {s.sprites > 0 && `obj ${s.sprites_done}/${s.sprites}`}{s.sprites > 0 && s.variants > 0 && ' · '}
                {s.variants > 0 && `var ${s.variants_done}/${s.variants}`}
              </span>
              <select value={s.source} disabled={busy} onChange={e => setSource(s, e.target.value as SceneArt['source'])}
                      className="bg-gray-800 text-xs rounded px-1 py-0.5 border border-gray-700"
                      title={SOURCES.find(x => x.id === s.source)?.title}>
                {SOURCES.map(x => <option key={x.id} value={x.id} title={x.title}>{x.label}</option>)}
              </select>
              {s.source === 'web' && (
                <button onClick={() => toggle(s)} title="Prompts para copiar e imagens para enviar"
                        className={`p-1 rounded ${open === s.id ? 'bg-cyan-800' : 'hover:bg-gray-800'}`}>
                  <Globe size={14} />
                </button>
              )}
            </div>

            {open === s.id && s.source === 'web' && (
              <div className="px-2 pb-2 space-y-2 text-xs border-t border-gray-800 pt-2">
                {!p ? (
                  <div className="text-gray-400 flex items-center gap-2"><Loader2 size={12} className="animate-spin" /> escrevendo os prompts…</div>
                ) : (
                  <>
                    <div className="space-y-1">
                      <div className="flex items-center gap-1 text-gray-300 font-bold">{mark(!!s.background)} 1. Cenário</div>
                      <div className="text-gray-500">
                        Cole o prompt numa IA de imagem da web
                        {p.style_reference && <> e anexe {link(p.style_reference, 'esta imagem')} como referência do estilo do jogo</>}.
                        Envie a imagem que ficar boa.
                        {s.background && <> Atual: {link(s.background, 'ver')}.</>}
                      </div>
                      <div className="flex gap-1">{copyBtn(s.id, p.background_prompt)}{picker(s, 'background', 'Enviar cenário')}</div>
                    </div>

                    {p.sprites.length > 0 && (
                      <div className="space-y-1">
                        <div className="flex items-center gap-1 text-gray-300 font-bold">
                          {mark(s.sprites_done === s.sprites)} 2. Objetos soltos ({p.sprites.join(', ')})
                        </div>
                        <div className="text-gray-500">
                          Uma imagem com os {p.sprites.length} objetos lado a lado, nessa ordem, sobre fundo cinza liso.
                          Anexe {s.background ? link(s.background, 'o cenário') : 'o cenário'} para pegar o estilo.
                          O Saga recorta e encaixa cada um.
                        </div>
                        <div className="flex gap-1">
                          {copyBtn(s.id, p.sprites_prompt)}{picker(s, 'sprites', 'Enviar objetos', !s.background)}
                        </div>
                      </div>
                    )}

                    {p.variants.map(v => (
                      <div key={v.index} className="space-y-1">
                        <div className="flex items-center gap-1 text-gray-300 font-bold">{mark(v.done)} Variante: {v.when}</div>
                        <div className="text-gray-500">Anexe {s.background ? link(s.background, 'o cenário') : 'o cenário'} e peça a edição.</div>
                        <div className="flex gap-1">
                          {copyBtn(s.id, v.prompt)}{picker(s, `variant:${v.index}`, 'Enviar variante', !s.background)}
                        </div>
                      </div>
                    ))}
                  </>
                )}
                {msg && msg.scene === s.id && (
                  <div className={msg.ok ? 'text-green-300' : 'text-amber-300'}>{msg.text}</div>
                )}
              </div>
            )}
            {msg && msg.scene === s.id && open !== s.id && (
              <div className="px-2 pb-1 text-xs text-red-300">{msg.text}</div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default SceneArtList;
