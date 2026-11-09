import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Save, UploadCloud, Image as ImageIcon, Music, FileAudio, Crosshair, Maximize, RotateCcw, Sparkles, Box } from 'lucide-react';
import { toast } from 'react-hot-toast';
import type { GameObject, Scene } from '../../types';
import { uploadSprite, getAssetUrl, suggestAnimation, magicPartAnimate, animateObjectWithAI } from '../../services/api';

interface PropertiesEditorProps {
  project: { name: string };
  selectedItem: GameObject | (Scene & { type?: 'scene' }); // Flexível para ambos
  activeScene: Scene;
  onSave: (updates: any) => void;
  onClose: () => void;
  onSetSceneBackground: (backgroundPath: string) => void;
  onMagicPartAnimate: (parentObjectId: string, result: any) => void;
  onStartExtraction?: (prompt: string) => void;
  resizable?: boolean;
}

export const PropertiesEditor: React.FC<PropertiesEditorProps> = ({
  project,
  selectedItem,
  activeScene,
  onSave,
  onClose,
  onSetSceneBackground,
  onMagicPartAnimate,
  onStartExtraction,
}) => {
  const [draft, setDraft] = useState<any>(selectedItem);
  const [localPreview, setLocalPreview] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isSuggesting, setIsSuggesting] = useState(false);
  const [isMagicProcessing, setIsMagicProcessing] = useState(false);
  const [showAnimationModal, setShowAnimationModal] = useState(false);
  const [animationPrompt, setAnimationPrompt] = useState('');
  const [animationFrames, setAnimationFrames] = useState(3);
  const [isAnimating, setIsAnimating] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isScene = !('type' in draft) || draft.type === 'scene';

  // Sincroniza draft quando o item selecionado mudar
  useEffect(() => {
    setDraft(selectedItem);

    // Limpa preview local ao trocar de item
    if (localPreview) {
      URL.revokeObjectURL(localPreview);
      setLocalPreview(null);
    }
  }, [selectedItem.id]);

  // Cleanup do preview ao desmontar
  useEffect(() => {
    return () => {
      if (localPreview) {
        URL.revokeObjectURL(localPreview);
      }
    };
  }, [localPreview]);

  const handleFieldChange = (field: keyof GameObject, value: any) => {
    setDraft(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = () => {
    onSave(draft);
    toast.success(`"${draft.name}" salvo!`);
  };

  const handleCenterObject = () => {
    // Centraliza baseado na resolução base de 1920x1080
    const centeredPosition = { x: 960, y: 540 };

    setDraft(prev => {
      const updated = { ...prev, position: centeredPosition };
      onSave(updated); // Salva imediatamente
      return updated;
    });

    toast.success('Objeto centralizado!');
  };

  const handleFitToScreen = () => {
    // Ajusta para o tamanho total da cena (1920x1080) e centraliza
    const fullScreenSize = { width: 1920, height: 1080 };
    const centeredPosition = { x: 960, y: 540 };

    setDraft(prev => {
      const updated = {
        ...prev,
        size: fullScreenSize,
        position: centeredPosition
      };
      onSave(updated); // Salva imediatamente
      return updated;
    });

    toast.success('Objeto ajustado à tela!');
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validação de tipo de arquivo
    const isImage = file.type.startsWith('image/');
    const isAudio = file.type.startsWith('audio/');

    if (!isImage && !isAudio) {
      toast.error('Apenas imagens ou áudio são permitidos.');
      return;
    }

    // Preview apenas para imagens
    let newPreviewUrl: string | null = null;
    if (isImage) {
      newPreviewUrl = URL.createObjectURL(file);
      setLocalPreview(newPreviewUrl);
    }

    setIsUploading(true);
    const toastId = toast.loading('Enviando asset...');

    try {
      const response = await uploadSprite(file, project.name);
      const newAssetPath = response.asset_path;

      // Atualiza o draft com o caminho permanente
      // Atualiza o draft
      setDraft(prev => {
        const field = isScene ? 'background' : 'sprite';
        const updated = { ...prev, [field]: newAssetPath };

        // Se for cena, não removemos o field 'background' aqui para não quebrar o componente ainda
        // mas o onSave tratará as cenas conforme a nova interface
        onSave(updated);

        return updated;
      });

      toast.success('Asset enviado com sucesso!', { id: toastId });

      // Verifica se deve definir como background
      const checkbox = document.getElementById('is-background-checkbox') as HTMLInputElement;
      if (checkbox?.checked) {
        onSetSceneBackground(newAssetPath);
      }
    } catch (error) {
      console.error("Erro no upload:", error);
      toast.error('Falha ao enviar asset.', { id: toastId });

      // Limpa preview em caso de erro
      if (newPreviewUrl) {
        URL.revokeObjectURL(newPreviewUrl);
        setLocalPreview(null);
      }
    } finally {
      setIsUploading(false);
    }
  };

  const handleSuggestAnimation = async () => {
    setIsSuggesting(true);
    const toastId = toast.loading('IA analisando objeto...');

    try {
      const suggestion = await suggestAnimation(draft.name, draft.type);
      console.log("IA Sugestão:", suggestion);

      const getProperty = (type: string) => {
        if (type === 'rotate') return 'rotation';
        if (type === 'scale') return 'scale';
        if (type === 'translate') return 'position';
        return 'rotation';
      };

      const newAnimation = {
        type: 'transform' as const,
        property: getProperty(suggestion.type),
        min: suggestion.min_value,
        max: suggestion.max_value,
        duration: suggestion.duration,
        easing: 'easeInOut' as const
      };

      if (suggestion.anchor_x !== undefined && suggestion.anchor_y !== undefined) {
        handleFieldChange('anchor', { x: suggestion.anchor_x, y: suggestion.anchor_y });
      }

      handleFieldChange('animation', newAnimation);
      toast.success('IA sugeriu uma animação e ajuste de âncora!', { id: toastId });
    } catch (error) {
      console.error("Erro na sugestão IA:", error);
      toast.error('IA falhou ao sugerir animação.', { id: toastId });
    } finally {
      setIsSuggesting(false);
    }
  };

  const handleMagicAnimatePart = async () => {
    if (!draft.sprite || isScene) return;

    setIsMagicProcessing(true);
    const toastId = toast.loading('IA detectando e extraindo partes do objeto...');

    try {
      const result = await magicPartAnimate(project.name, draft.sprite, draft.name);

      if (!result.new_part) {
        toast.error("Nenhuma parte animável detectada.", { id: toastId });
        return;
      }

      onMagicPartAnimate(draft.id, result);
      toast.success('Objeto "Explodido" com sucesso! Parte animada criada.', { id: toastId });
    } catch (error) {
      console.error("Erro no Magic Animate:", error);
      toast.error('IA falhou na automação mágica.', { id: toastId });
    } finally {
      setIsMagicProcessing(false);
    }
  };

  const handleGenerateAnimation = async () => {
    if (!draft.id || !animationPrompt) return;

    setIsAnimating(true);
    const toastId = toast.loading('IA gerando frames de animação...');

    try {
      const result = await animateObjectWithAI(project.name, draft.id, animationPrompt, animationFrames);

      if (result.success && result.sprite_path) {
        setDraft(prev => {
          const updated = {
            ...prev,
            sprite: result.sprite_path,
            animation: result.animation_config
          };

          // Adjust size to match the new single frame width from the backend
          if (prev.size && result.animation_config?.frameWidth) {
            updated.size = {
              ...prev.size,
              width: result.animation_config.frameWidth
            };
          }

          onSave(updated);
          return updated;
        });
        setShowAnimationModal(false);
        setAnimationPrompt('');
        toast.success('Animação gerada com sucesso!', { id: toastId });
      } else {
        toast.error('A IA processou o pedido mas não retornou os dados esperados.', { id: toastId });
      }
    } catch (error) {
      console.error("Erro ao gerar animação:", error);
      toast.error('Falha ao gerar animação.', { id: toastId });
    } finally {
      setIsAnimating(false);
    }
  };

  // URLs e estados derivados
  const finalAssetUrl = useMemo(() => {
    if (localPreview) return localPreview;
    const sprite = isScene ? (draft as any).background : draft.sprite;
    if (sprite) return getAssetUrl(project.name, sprite);
    return null;
  }, [localPreview, project.name, draft.sprite, (draft as any).background, isScene]);

  const canBeSetAsBackground = useMemo(() => {
    if (isScene) return false;
    return !!draft.sprite && (draft.type === 'sprite' || draft.type === 'background');
  }, [draft.sprite, draft.type, isScene]);

  const isSceneBackground = useMemo(() => {
    if (isScene) return true;
    if (!draft.sprite) return false;

    const bgObj = activeScene.objects.find(o => o.type === 'background' || o.name === 'Background');
    if (!bgObj) return false;

    return draft.sprite === bgObj.sprite;
  }, [activeScene.objects, draft.sprite, isScene]);

  const getAssetSectionLabel = () => {
    if (isScene) return 'Background da Cena';
    const labels: Record<string, string> = {
      background: 'Imagem de Fundo',
      sound: 'Arquivo de Som',
      music: 'Arquivo de Música',
      character: 'Sprite do Personagem',
      item: 'Sprite do Item'
    };
    return labels[draft.type || ''] || 'Sprite';
  };

  const getAssetIcon = () => {
    // Mostra preview de imagem
    if (finalAssetUrl && ['sprite', 'background', 'item', 'character'].includes(draft.type)) {
      return (
        <img
          src={finalAssetUrl}
          alt={draft.name}
          className="max-w-full max-h-full object-contain"
          onError={(e) => {
            // Fallback se imagem não carregar
            (e.target as HTMLImageElement).style.display = 'none';
          }}
        />
      );
    }

    // Ícones para áudio
    if (draft.type === 'music') return <Music className="w-8 h-8 text-gray-600" />;
    if (draft.type === 'sound') return <FileAudio className="w-8 h-8 text-gray-600" />;

    // Ícone padrão
    return <ImageIcon className="w-8 h-8 text-gray-600" />;
  };

  const getAcceptedFileTypes = () => {
    if (draft.type === 'music' || draft.type === 'sound') {
      return "audio/*";
    }
    return "image/*";
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-gray-950/40 relative group/editor overflow-hidden">
      {/* Header com botões de ação */}
      <div className="h-12 border-b border-gray-800/50 flex items-center justify-between px-3 bg-gray-950/20 backdrop-blur-md sticky top-0 z-10 flex-shrink-0">
        <div className="flex items-center gap-2 overflow-hidden">
          <div className="p-1.5 bg-purple-500/10 rounded-lg">
            {isScene ? <ImageIcon size={14} className="text-purple-400" /> : <Box size={14} className="text-purple-400" />}
          </div>
          <span className="text-sm font-medium text-gray-200 truncate pr-4">
            {isScene ? "Cena: " : ""}{draft.name}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleSave}
            title="Salvar Alterações"
            className="p-1.5 hover:bg-green-500/10 text-gray-400 hover:text-green-400 rounded-lg transition-all"
          >
            <Save size={16} />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto overflow-x-hidden scrollbar-thin scrollbar-thumb-purple-500/20 scrollbar-track-transparent">
        <div className="p-4 space-y-6">
          {/* Section: Basic Info */}
          <div className="space-y-3">
            <h3 className="text-[10px] font-bold text-gray-500 uppercase tracking-widest pl-1">Identidade</h3>
            <div className="space-y-2">
              <label className="block">
                <span className="text-[10px] text-gray-500 ml-1">Nome</span>
                <input
                  type="text"
                  value={draft.name}
                  onChange={(e) => handleFieldChange('name', e.target.value)}
                  className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-purple-500/50 transition-colors"
                />
              </label>
            </div>
          </div>

          {/* Section: Transform */}
          {!isScene && draft.type !== 'music' && draft.type !== 'sound' && (
            <div className="space-y-3 pt-2 border-t border-gray-800/50">
              <div className="flex items-center justify-between mb-1">
                <h3 className="text-[10px] font-bold text-gray-500 uppercase tracking-widest pl-1">Transform</h3>
                <div className="flex gap-1">
                  <button onClick={handleCenterObject} title="Centralizar" className="p-1 hover:bg-gray-800 rounded text-gray-500 hover:text-purple-400 transition-colors"><Crosshair size={12} /></button>
                  <button onClick={handleFitToScreen} title="Ajustar à Tela" className="p-1 hover:bg-gray-800 rounded text-gray-500 hover:text-blue-400 transition-colors"><Maximize size={12} /></button>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <label className="block">
                    <span className="text-[10px] text-gray-500 ml-1">Posição X</span>
                    <input
                      type="number"
                      value={draft.position?.x || 0}
                      onChange={(e) => handleFieldChange('position', { ...draft.position, x: Number(e.target.value) })}
                      className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-purple-500/50"
                    />
                  </label>
                  <label className="block">
                    <span className="text-[10px] text-gray-500 ml-1">Posição Y</span>
                    <input
                      type="number"
                      value={draft.position?.y || 0}
                      onChange={(e) => handleFieldChange('position', { ...draft.position, y: Number(e.target.value) })}
                      className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-purple-500/50"
                    />
                  </label>
                </div>
                <div className="space-y-2">
                  <label className="block">
                    <span className="text-[10px] text-gray-500 ml-1">Largura</span>
                    <input
                      type="number"
                      value={draft.size?.width || 0}
                      onChange={(e) => handleFieldChange('size', { ...draft.size, width: Number(e.target.value) })}
                      className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-purple-500/50"
                    />
                  </label>
                  <label className="block">
                    <span className="text-[10px] text-gray-500 ml-1">Altura</span>
                    <input
                      type="number"
                      value={draft.size?.height || 0}
                      onChange={(e) => handleFieldChange('size', { ...draft.size, height: Number(e.target.value) })}
                      className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-purple-500/50"
                    />
                  </label>
                </div>
              </div>
              <div className="space-y-2">
                <label className="block">
                  <span className="text-[10px] text-gray-500 ml-1">Z-Index</span>
                  <input
                    type="number"
                    value={draft.zIndex ?? 10}
                    onChange={(e) => handleFieldChange('zIndex', Number(e.target.value))}
                    className="w-full bg-gray-900 border border-gray-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-purple-500/50"
                  />
                </label>
              </div>
            </div>
          )}

          {/* Section: Asset Upload */}
          {!isScene && (
            <div className="space-y-3 pt-2 border-t border-gray-800/50">
              <h3 className="text-[10px] font-bold text-gray-500 uppercase tracking-widest pl-1">{getAssetSectionLabel()}</h3>

              <div className="space-y-4">
                <div className="w-full aspect-video bg-gray-900 border border-gray-800 rounded-xl flex items-center justify-center overflow-hidden group/asset relative">
                  {getAssetIcon()}
                  <div onClick={handleUploadClick} className="absolute inset-0 bg-gray-950/60 opacity-0 group-hover/asset:opacity-100 transition-opacity flex flex-col items-center justify-center cursor-pointer gap-2 backdrop-blur-sm">
                    <UploadCloud size={24} className="text-purple-400" />
                    <span className="text-xs font-medium text-white">Alterar Asset</span>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex gap-2">
                    <button
                      onClick={handleUploadClick}
                      className="flex-1 flex items-center justify-center gap-2 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-xs font-medium border border-gray-700 transition-colors"
                    >
                      <UploadCloud size={14} /> Upload
                    </button>
                    {onStartExtraction && (draft.type === 'sprite' || draft.type === 'item' || draft.type === 'background') && (
                      <button
                        onClick={() => onStartExtraction(`Extração Contextual: ${draft.name}`)}
                        className="flex-1 flex items-center justify-center gap-2 py-2 bg-green-950/30 hover:bg-green-900/40 text-green-400 rounded-lg text-xs font-medium border border-green-900/30 transition-colors"
                        title="Capturar objeto da cena usando o laço"
                      >
                        <span>✂️</span> Capturar
                      </button>
                    )}
                  </div>

                  <p className="text-[10px] text-gray-500 break-all px-1">
                    {draft.sprite || 'Nenhum asset selecionado'}
                  </p>
                  <input type="file" ref={fileInputRef} onChange={handleFileChange} accept={getAcceptedFileTypes()} className="hidden" />

                  {canBeSetAsBackground && (
                    <label className="flex items-center gap-2 cursor-pointer p-1.5 hover:bg-gray-800/50 rounded-lg transition-colors">
                      <input
                        id="is-background-checkbox"
                        type="checkbox"
                        checked={isSceneBackground}
                        onChange={(e) => e.target.checked && draft.sprite && onSetSceneBackground(draft.sprite)}
                        className="w-4 h-4 rounded border-gray-800 bg-gray-900 text-purple-500 focus:ring-purple-500/20"
                      />
                      <span className="text-[11px] text-gray-400">Usar como background desta cena</span>
                    </label>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Section: Audio Controls */}
          {!isScene && (draft.type === 'sound' || draft.type === 'music') && (
            <div className="space-y-3 pt-2 border-t border-gray-800/50">
              <h3 className="text-[10px] font-bold text-gray-500 uppercase tracking-widest pl-1">Áudio</h3>
              <div className="space-y-4 px-1">
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-[10px] text-gray-500">Volume</span>
                    <span className="text-[10px] font-mono text-purple-400">{Math.round((draft.properties?.volume ?? 1) * 100)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    value={draft.properties?.volume ?? 1}
                    onChange={(e) => handleFieldChange('properties', { ...draft.properties, volume: Number(e.target.value) })}
                    className="w-full h-1 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-purple-500"
                  />
                </div>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={draft.properties?.loop ?? (draft.type === 'music')}
                    onChange={(e) => handleFieldChange('properties', { ...draft.properties, loop: e.target.checked })}
                    className="w-4 h-4 rounded border-gray-800 bg-gray-900 text-purple-500 focus:ring-purple-500/20"
                  />
                  <span className="text-[11px] text-gray-400">Repetir áudio</span>
                </label>
              </div>
            </div>
          )}

          {/* Section: Animation IA */}
          {!isScene && (draft.type === 'sprite' || draft.type === 'character') && (
            <div className="space-y-4 pt-4 border-t border-gray-800/50">
              <div className="space-y-2">
                <button
                  onClick={() => setShowAnimationModal(true)}
                  disabled={isAnimating || !draft.sprite}
                  className="w-full flex items-center justify-center gap-2 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-purple-500/20 transition-all active:scale-[0.98] disabled:opacity-50"
                >
                  <Sparkles size={14} className={isAnimating ? 'animate-pulse' : ''} />
                  {isAnimating ? 'Gerando Animação...' : 'Gerar Animação (IA)'}
                </button>

                <button
                  onClick={handleSuggestAnimation}
                  disabled={isSuggesting || !draft.sprite}
                  className="w-full flex items-center justify-center gap-2 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700/50 rounded-xl text-[11px] transition-all active:scale-[0.98] disabled:opacity-50"
                >
                  <Maximize size={12} className={isSuggesting ? 'animate-pulse' : ''} />
                  {isSuggesting ? 'Analisando Movimento...' : 'Sugerir Movimento'}
                </button>

                <button
                  onClick={handleMagicAnimatePart}
                  disabled={isMagicProcessing || !draft.sprite}
                  className="w-full flex items-center justify-center gap-2 py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700/50 rounded-xl text-xs font-bold transition-all active:scale-[0.98] disabled:opacity-50"
                >
                  <Sparkles size={14} className={isMagicProcessing ? 'animate-spin' : ''} />
                  {isMagicProcessing ? 'Processando...' : 'Explodir Partes (SAM)'}
                </button>
              </div>

              {draft.animation && (
                <div className="p-3 bg-gray-950/50 rounded-xl border border-gray-800 space-y-2">
                  <div className="flex justify-between items-center text-[10px]">
                    <span className="text-gray-500 uppercase font-bold">Animação Ativa</span>
                    <button onClick={() => handleFieldChange('animation', undefined)} className="text-red-500 hover:underline">Remover</button>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <span className="text-[10px] text-gray-500 block">Tipo</span>
                      <span className="text-xs text-white capitalize">{draft.animation.property || 'Transform'}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-gray-500 block">Duração</span>
                      <span className="text-xs text-white">{draft.animation.duration}s</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Section: Script SES */}
          <div className="space-y-3 pt-2 border-t border-gray-800/50">
            <h3 className="text-[10px] font-bold text-gray-500 uppercase tracking-widest pl-1">Script (SES)</h3>
            <div className="h-64 w-full bg-gray-900 border border-gray-800 rounded-xl overflow-hidden focus-within:border-purple-500/50 transition-colors">
              <textarea
                value={draft.ses || ''}
                onChange={(e) => handleFieldChange('ses', e.target.value)}
                className="w-full h-full bg-transparent p-3 font-mono text-[11px] resize-none focus:outline-none text-gray-300 scrollbar-thin scrollbar-thumb-purple-500/20"
                spellCheck="false"
                placeholder={isScene ? "// Scripts para o início da cena..." : "// Scripts de interação com este objeto..."}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
