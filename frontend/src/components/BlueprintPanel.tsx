// BlueprintPanel - the game's ficha (ficha.yaml): one text with the whole adventure. VERIFICAR
// checks it (logic holes, the solution, each death, an automatic player), MONTAR builds the project
// from it keeping the art already made, GERAR ARTE / GERAR SONS make the missing pictures / sounds
// in the background.
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { X, CheckCircle2, AlertTriangle, XCircle, Hammer, SearchCheck, Image as ImageIcon, Loader2, Music } from 'lucide-react';
import api from '../services/api';
import SceneArtList from './SceneArtList';
import type { SceneArt } from './SceneArtList';

interface Problem { nivel: 'erro' | 'aviso'; msg: string; onde?: string }
interface TestResult { teste: string; ok: boolean; comandos: number; fim: string; motivo?: string; comandos_recusados?: string[] }
interface Report {
  ok: boolean;
  salvo?: boolean;
  numeros?: Record<string, number>;
  problemas: Problem[];
  testes?: TestResult[];
  explorador?: { venceu: boolean; confirmado?: boolean; caminho: string[]; comandos_testados: number; estados: number;
                 cenas_nao_visitadas: string[]; finais: { texto: string; comandos: number }[]; esgotou: boolean };
  arte?: { cenas_sem_arte: string[]; variantes_sem_arte: string[]; pronta: boolean; arte_revisar?: string[] };
}
interface ArtStatus { running: boolean; log: string[]; cenas_sem_arte: string[]; variantes_sem_arte: string[]; pronta: boolean; arte_revisar?: string[];
                    na_web?: string[]; cenas?: SceneArt[] }
interface SoundStatus { running: boolean; log: string[]; sons_sem_arquivo: string[]; sons: number; som_pronto: boolean; result?: { falhas?: string[] } | null }

const BlueprintPanel: React.FC<{ projectName: string; onClose: () => void; onBuilt: () => void }> = ({ projectName, onClose, onBuilt }) => {
  const [text, setText] = useState('');
  const [exported, setExported] = useState(false);
  const [busy, setBusy] = useState<'' | 'check' | 'build'>('');
  const [report, setReport] = useState<Report | null>(null);
  const [art, setArt] = useState<ArtStatus | null>(null);
  const [sound, setSound] = useState<SoundStatus | null>(null);
  const soundTimer = useRef<number | null>(null);
  const [error, setError] = useState('');
  const timer = useRef<number | null>(null);

  useEffect(() => {
    api.get(`/api/blueprint/${encodeURIComponent(projectName)}`)
      .then(r => { setText(r.data.text); setExported(r.data.exported); })
      .catch(e => setError(e.response?.data?.detail || String(e)));
  }, [projectName]);

  const pollArt = useCallback(async () => {
    try {
      const r = await api.get(`/api/blueprint/art/${encodeURIComponent(projectName)}`);
      setArt(r.data);
      if (timer.current) window.clearTimeout(timer.current);
      if (r.data.running) timer.current = window.setTimeout(pollArt, 5000);
    } catch { /* the backend restarted: the panel keeps what it showed */ }
  }, [projectName]);

  useEffect(() => { pollArt(); return () => { if (timer.current) window.clearTimeout(timer.current); }; }, [pollArt]);

  const pollSound = useCallback(async () => {
    try {
      const r = await api.get(`/api/blueprint/sound/${encodeURIComponent(projectName)}`);
      setSound(r.data);
      if (soundTimer.current) window.clearTimeout(soundTimer.current);
      if (r.data.running) soundTimer.current = window.setTimeout(pollSound, 5000);
    } catch { /* the backend restarted: the panel keeps what it showed */ }
  }, [projectName]);

  useEffect(() => { pollSound(); return () => { if (soundTimer.current) window.clearTimeout(soundTimer.current); }; }, [pollSound]);

  const startSound = async () => {
    setError('');
    try { await api.post(`/api/blueprint/sound/${encodeURIComponent(projectName)}`); pollSound(); }
    catch (e: any) { setError(e.response?.data?.detail || String(e)); }
  };

  const run = async (kind: 'check' | 'build') => {
    setBusy(kind); setError('');
    try {
      const r = await api.post(`/api/blueprint/${kind}`, { project_name: projectName, text });
      setReport(r.data);
      if (kind === 'build' && r.data.salvo) { setExported(false); onBuilt(); pollArt(); pollSound(); }
    } catch (e: any) {
      setError(e.response?.data?.detail || String(e));
    } finally {
      setBusy('');
    }
  };

  const startArt = async () => {
    setError('');
    try { await api.post(`/api/blueprint/art/${encodeURIComponent(projectName)}`); pollArt(); }
    catch (e: any) { setError(e.response?.data?.detail || String(e)); }
  };

  const errors = report?.problemas.filter(p => p.nivel === 'erro') || [];
  const warnings = report?.problemas.filter(p => p.nivel === 'aviso') || [];
  const ex = report?.explorador;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-7xl h-full max-h-[92vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
          <div>
            <h2 className="font-bold text-white">Ficha do jogo</h2>
            <p className="text-xs text-gray-400">
              O jogo inteiro num arquivo: mapa, objetos, scripts, arte e a solução. Verifique, monte e gere a arte.
              {exported && ' Este projeto ainda não tinha ficha: este é um rascunho tirado do projeto atual.'}
            </p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-800 rounded-lg" title="Fechar"><X size={18} /></button>
        </div>

        <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
          <textarea
            value={text}
            onChange={e => setText(e.target.value)}
            spellCheck={false}
            className="flex-1 min-h-[200px] bg-gray-950 text-gray-200 font-mono text-xs p-3 outline-none resize-none border-r border-gray-800"
          />
          <div className="md:w-[420px] flex flex-col overflow-hidden">
            <div className="flex flex-wrap gap-2 p-3 border-b border-gray-800">
              <button onClick={() => run('check')} disabled={!!busy}
                      className="px-3 py-2 text-sm bg-gray-800 hover:bg-gray-700 disabled:opacity-50 rounded-lg flex items-center gap-2">
                {busy === 'check' ? <Loader2 size={16} className="animate-spin" /> : <SearchCheck size={16} />} Verificar
              </button>
              <button onClick={() => run('build')} disabled={!!busy || art?.running || sound?.running}
                      title={art?.running || sound?.running ? 'Espere a arte e os sons terminarem' : 'Verifica e, sem erros, monta o projeto (a arte e os sons já feitos são mantidos)'}
                      className="px-3 py-2 text-sm bg-purple-700 hover:bg-purple-600 disabled:opacity-50 rounded-lg flex items-center gap-2">
                {busy === 'build' ? <Loader2 size={16} className="animate-spin" /> : <Hammer size={16} />} Montar o jogo
              </button>
              <button onClick={startArt} disabled={!!busy || art?.running || art?.pronta}
                      title="Gera as cenas e variantes que faltam, em segundo plano (horas); as cenas marcadas 'Web' ficam com você"
                      className="px-3 py-2 text-sm bg-gray-800 hover:bg-gray-700 disabled:opacity-50 rounded-lg flex items-center gap-2">
                {art?.running ? <Loader2 size={16} className="animate-spin" /> : <ImageIcon size={16} />} Gerar arte
              </button>
              <button onClick={startSound} disabled={!!busy || sound?.running || !sound?.sons || sound?.som_pronto}
                      title={!sound?.sons ? 'A ficha não tem sons (som: nas cenas e objetos, play "..." nos scripts)'
                        : 'Gera o som ambiente, os sons dos objetos e os play dos scripts que faltam (minutos)'}
                      className="px-3 py-2 text-sm bg-gray-800 hover:bg-gray-700 disabled:opacity-50 rounded-lg flex items-center gap-2">
                {sound?.running ? <Loader2 size={16} className="animate-spin" /> : <Music size={16} />} Gerar sons
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-3 text-sm space-y-3">
              {error && <div className="text-red-400">{error}</div>}
              {report && (
                <div className={`flex items-center gap-2 font-bold ${report.ok ? 'text-green-400' : 'text-red-400'}`}>
                  {report.ok ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
                  {report.ok ? (report.salvo ? 'Sem erros: jogo montado.' : 'Sem erros.') : `${errors.length} erro(s): corrija antes de montar.`}
                </div>
              )}
              {report?.numeros && (
                <div className="text-xs text-gray-400">
                  {Object.entries(report.numeros).map(([k, v]) => `${v} ${k}`).join(' · ')}
                </div>
              )}
              {[...errors, ...warnings].map((p, i) => (
                <div key={i} className={`flex gap-2 ${p.nivel === 'erro' ? 'text-red-300' : 'text-amber-300'}`}>
                  {p.nivel === 'erro' ? <XCircle size={14} className="mt-1 shrink-0" /> : <AlertTriangle size={14} className="mt-1 shrink-0" />}
                  <span>{p.msg}{p.onde && <span className="text-gray-500"> ({p.onde})</span>}</span>
                </div>
              ))}
              {report?.testes && report.testes.length > 0 && (
                <div>
                  <div className="text-gray-400 text-xs uppercase mb-1">Testes</div>
                  {report.testes.map((t, i) => (
                    <div key={i} className={t.ok ? 'text-green-300' : 'text-red-300'}>
                      {t.ok ? '✔' : '✘'} {t.teste} <span className="text-gray-500">({t.comandos} comandos)</span>
                      {t.motivo && <div className="text-xs text-gray-400 ml-4">{t.motivo}</div>}
                      {t.comandos_recusados && <div className="text-xs text-gray-500 ml-4">recusados: {t.comandos_recusados.join(', ')}</div>}
                    </div>
                  ))}
                </div>
              )}
              {ex && (
                <div>
                  <div className="text-gray-400 text-xs uppercase mb-1">Jogador automático</div>
                  <div className={ex.venceu ? 'text-green-300' : 'text-amber-300'}>
                    {ex.venceu ? `Venceu sozinho em ${ex.caminho.length} comandos.` : 'Não venceu sozinho.'}
                    <span className="text-gray-500"> {ex.comandos_testados} comandos testados, {ex.estados} estados.</span>
                  </div>
                  {ex.finais.length > 0 && (
                    <div className="text-xs text-gray-400 mt-1">Finais que encontrou: {ex.finais.map(f => `"${f.texto.slice(0, 60)}…"`).join(' · ')}</div>
                  )}
                </div>
              )}
              {art && (
                <div>
                  <div className="text-gray-400 text-xs uppercase mb-1">Arte</div>
                  <div className={art.pronta ? 'text-green-300' : 'text-gray-300'}>
                    {art.pronta ? 'Todas as cenas e variantes têm imagem.'
                      : `Faltam ${art.cenas_sem_arte.length} cena(s) e ${art.variantes_sem_arte.length} variante(s).`}
                    {art.running && ' Gerando…'}
                  </div>
                  {(art.na_web?.length ?? 0) > 0 && (
                    <div className="text-cyan-300 text-xs mt-1">Esperando imagens da web: {art.na_web!.join(', ')}.</div>
                  )}
                  {(art.cenas?.length ?? 0) > 0 && (
                    <details className="mt-2" open={(art.na_web?.length ?? 0) > 0}>
                      <summary className="cursor-pointer text-gray-400 text-xs">
                        Fonte da arte por cena (GPU local, API Gemini ou Web)
                      </summary>
                      <div className="mt-1">
                        <SceneArtList projectName={projectName} scenes={art.cenas!} busy={!!art.running} onChanged={pollArt} />
                      </div>
                    </details>
                  )}
                  {(art.arte_revisar?.length ?? 0) > 0 && (
                    <div className="mt-1">
                      <div className="text-amber-300">A revisão ainda vê {art.arte_revisar!.length} problema(s) na arte:</div>
                      {art.arte_revisar!.map((p, i) => (
                        <div key={i} className="flex gap-2 text-amber-200 text-xs">
                          <AlertTriangle size={12} className="mt-0.5 shrink-0" /><span>{p}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {art.log.length > 0 && (
                    <pre className="mt-1 text-[11px] text-gray-500 whitespace-pre-wrap max-h-48 overflow-y-auto">{art.log.slice(-12).join('\n')}</pre>
                  )}
                </div>
              )}
              {sound && sound.sons > 0 && (
                <div>
                  <div className="text-gray-400 text-xs uppercase mb-1">Som</div>
                  <div className={sound.som_pronto ? 'text-green-300' : 'text-gray-300'}>
                    {sound.som_pronto ? `Os ${sound.sons} sons estão prontos.`
                      : `Faltam ${sound.sons_sem_arquivo.length} de ${sound.sons} sons.`}
                    {sound.running && ' Gerando…'}
                  </div>
                  {(sound.result?.falhas?.length ?? 0) > 0 && (
                    <div className="text-xs text-red-300 mt-1">{sound.result!.falhas!.slice(0, 3).join(' · ')}</div>
                  )}
                  {sound.log.length > 0 && (
                    <pre className="mt-1 text-[11px] text-gray-500 whitespace-pre-wrap max-h-32 overflow-y-auto">{sound.log.slice(-8).join('\n')}</pre>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BlueprintPanel;
