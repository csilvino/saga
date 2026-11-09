import React, { useState, useEffect, useRef } from 'react';
import { Settings, Key, Image as ImageIcon, Layout, Zap, Code, Globe, Palette, Save, X, Eye, EyeOff, RefreshCw, HardDrive, Cloud, Cpu, CheckCircle, XCircle, Music, Volume2 } from 'lucide-react';
import { saveApiKey, checkApiKey, uploadSprite, getAssetUrl } from '../../services/api';
import { toast } from 'react-hot-toast';

const SettingsPanel = ({
  onClose,
  project = null,
  onSaveProject
}: {
  onClose: () => void,
  project?: any,
  onSaveProject?: (p: any) => Promise<void>
}) => {
  const [activeTab, setActiveTab] = useState(project ? 'project' : 'api');
  const [showApiKey, setShowApiKey] = useState(false);
  const [apiKeyStatus, setApiKeyStatus] = useState<'idle' | 'checking' | 'valid' | 'invalid'>('idle');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const musicInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);

  // Estado local para o Launcher (inicializado do projeto se existir)
  const [launcherSettings, setLauncherSettings] = useState({
    title: project?.launcher?.title || project?.name || '',
    description: project?.launcher?.description || '',
    flyer_image: project?.launcher?.flyer_image || '',
    launcher_music: project?.launcher?.launcher_music || '',
    version: project?.launcher?.version || '1.0.0'
  });

  const [settings, setSettings] = useState({
    // API Keys
    geminiApiKey: '',
    openaiApiKey: '',

    // Image Generation
    imageProvider: 'sana', // sana, gemini, openai
    imageResolution: '1024x1024',
    imageQuality: 'standard',
    inferenceSteps: 20,
    guidanceScale: 7.5,

    // Performance
    useGPU: true,
    deviceType: 'cuda', // cuda, cpu
    batchSize: 1,
    cacheEnabled: true,

    // Editor
    canvasResolution: '1920x1080',
    gridSize: 16,
    snapToGrid: true,
    showGrid: false,
    autoSave: true,
    autoSaveInterval: 300, // seconds

    // Export
    exportFormat: 'html',
    compressionLevel: 'medium',
    includeAssets: true,

    // Language & Region
    language: 'pt-BR',
    timezone: 'America/Sao_Paulo',

    // Theme
    theme: 'dark',
    accentColor: '#3b82f6',

    // Advanced
    debugMode: false,
    telemetry: true,
    betaFeatures: false,
  });

  const placeholderKey = '••••••••••••••••••••••••••••••';

  useEffect(() => {
    const fetchKeyStatus = async () => {
      setApiKeyStatus('checking');
      try {
        const response = await checkApiKey();
        if (response.configured) {
          setApiKeyStatus('valid');
          updateSetting('geminiApiKey', placeholderKey);
        } else {
          setApiKeyStatus('idle');
        }
      } catch (error) {
        console.error("Failed to check API key status", error);
        setApiKeyStatus('invalid');
      }
    };
    fetchKeyStatus();
  }, []);

  const handleTestConnection = async () => {
    setApiKeyStatus('checking');
    try {
      const keyToTest = (settings.geminiApiKey && settings.geminiApiKey !== placeholderKey)
        ? settings.geminiApiKey
        : null;

      if (keyToTest) {
        await saveApiKey(keyToTest);
      }

      const response = await checkApiKey();
      if (response.configured) {
        setApiKeyStatus('valid');
        if (keyToTest) updateSetting('geminiApiKey', placeholderKey);
      } else {
        setApiKeyStatus('invalid');
      }
    } catch (error) {
      setApiKeyStatus('invalid');
    }
  };

  const handleSaveAndClose = async () => {
    if (settings.geminiApiKey && settings.geminiApiKey !== placeholderKey) {
      setApiKeyStatus('checking');
      try {
        await saveApiKey(settings.geminiApiKey);
        setApiKeyStatus('valid');
      } catch (error) {
        console.error("Failed to save API key", error);
        setApiKeyStatus('invalid');
        return;
      }
    }

    // Salvando configurações do Launcher no projeto
    if (project && onSaveProject) {
      const updatedProject = {
        ...project,
        launcher: {
          ...launcherSettings
        }
      };
      await onSaveProject(updatedProject);
    }

    onClose(); // Chama a função do pai para fechar
  };

  const updateSetting = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !project?.name) return;

    setIsUploading(true);
    try {
      const result = await uploadSprite(file, project.name);
      if (result.success) {
        setLauncherSettings(prev => ({ ...prev, flyer_image: result.asset_path }));
        toast.success("Flyer atualizado!");
      }
    } catch (error) {
      console.error("Upload failed", error);
      toast.error("Erro ao enviar imagem.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleAudioUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !project?.name) return;

    setIsUploading(true);
    try {
      const result = await uploadSprite(file, project.name);
      if (result.success) {
        setLauncherSettings(prev => ({ ...prev, launcher_music: result.asset_path }));
        toast.success("Música de fundo carregada!");
      }
    } catch (error) {
      console.error("Audio upload failed", error);
      toast.error("Erro ao enviar áudio.");
    } finally {
      setIsUploading(false);
    }
  };

  const tabs = [
    { id: 'project', label: 'Project Settings', icon: Layout, show: !!project },
    { id: 'api', label: 'API Keys', icon: Key, show: true },
    { id: 'generation', label: 'Image Generation', icon: ImageIcon, show: true },
    { id: 'performance', label: 'Performance', icon: Zap, show: true },
    { id: 'editor', label: 'Editor', icon: Code, show: true },
    { id: 'export', label: 'Export', icon: HardDrive, show: true },
    { id: 'general', label: 'General', icon: Globe, show: true },
    { id: 'advanced', label: 'Advanced', icon: Cpu, show: true },
  ];

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-lg shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col">

        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-800">
          <div className="flex items-center gap-3">
            <Settings className="w-6 h-6 text-blue-400" />
            <h2 className="text-2xl font-bold text-white">Settings</h2>
          </div>
          <button
            onClick={onClose} // Usa a função onClose do pai
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        <div className="flex flex-1 overflow-hidden">

          {/* Sidebar */}
          <div className="w-64 bg-gray-950 p-4 border-r border-gray-800 overflow-y-auto">
            <nav className="space-y-1">
              {tabs.filter(t => t.show).map(tab => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${activeTab === tab.id
                      ? 'bg-purple-600 text-white shadow-lg shadow-purple-900/20'
                      : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                      }`}
                  >
                    <Icon className="w-5 h-5" />
                    <span className="font-medium text-sm tracking-wide">{tab.label}</span>
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Content */}
          <div className="flex-1 p-6 overflow-y-auto">

            {/* PROJECT SETTINGS */}
            {activeTab === 'project' && project && (
              <div className="space-y-8 animate-in fade-in slide-in-from-left-4 duration-300">
                <div>
                  <h3 className="text-xl font-bold text-white mb-2 flex items-center gap-2">
                    <Layout className="w-5 h-5 text-purple-400" />
                    Launcher Customization
                  </h3>
                  <p className="text-sm text-gray-400 mb-6">
                    Configure how your game appears to players in the opening screen.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  {/* Left Side: Inputs */}
                  <div className="space-y-6">
                    <div className="space-y-2">
                      <label className="block text-xs font-black uppercase tracking-widest text-gray-500">
                        Game Title
                      </label>
                      <input
                        type="text"
                        value={launcherSettings.title}
                        onChange={(e) => setLauncherSettings(prev => ({ ...prev, title: e.target.value }))}
                        className="w-full bg-gray-800/50 border border-gray-700 rounded-xl px-4 py-3 text-white focus:border-purple-500 focus:outline-none transition-all"
                        placeholder="My Saga Game"
                      />
                    </div>

                    <div className="space-y-2">
                      <label className="block text-xs font-black uppercase tracking-widest text-gray-500">
                        Version
                      </label>
                      <input
                        type="text"
                        value={launcherSettings.version}
                        onChange={(e) => setLauncherSettings(prev => ({ ...prev, version: e.target.value }))}
                        className="w-full bg-gray-800/50 border border-gray-700 rounded-xl px-4 py-3 text-white focus:border-purple-500 focus:outline-none transition-all"
                        placeholder="1.0.0"
                      />
                    </div>

                    <div className="space-y-2">
                      <label className="block text-xs font-black uppercase tracking-widest text-gray-500">
                        Short Description
                      </label>
                      <textarea
                        rows={4}
                        value={launcherSettings.description}
                        onChange={(e) => setLauncherSettings(prev => ({ ...prev, description: e.target.value }))}
                        className="w-full bg-gray-800/50 border border-gray-700 rounded-xl px-4 py-3 text-white focus:border-purple-500 focus:outline-none transition-all resize-none"
                        placeholder="Describe your epic journey..."
                      />
                    </div>

                    <div className="space-y-2">
                      <label className="block text-xs font-black uppercase tracking-widest text-gray-500">
                        Flyer Image Path
                      </label>
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={launcherSettings.flyer_image}
                          onChange={(e) => setLauncherSettings(prev => ({ ...prev, flyer_image: e.target.value }))}
                          className="flex-1 bg-gray-800/50 border border-gray-700 rounded-xl px-4 py-3 text-white focus:border-purple-500 focus:outline-none transition-all"
                          placeholder="/flyer_calixto.png"
                        />
                        <input
                          type="file"
                          ref={fileInputRef}
                          onChange={handleFileUpload}
                          className="hidden"
                          accept="image/*"
                        />
                        <button
                          onClick={() => fileInputRef.current?.click()}
                          disabled={isUploading}
                          className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-xl text-gray-400 hover:text-white hover:border-gray-500 transition-all disabled:opacity-50"
                        >
                          {isUploading ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'Browse'}
                        </button>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <label className="block text-xs font-black uppercase tracking-widest text-gray-500">
                        Launcher Music (Loop)
                      </label>
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={launcherSettings.launcher_music}
                          onChange={(e) => setLauncherSettings(prev => ({ ...prev, launcher_music: e.target.value }))}
                          className="flex-1 bg-gray-800/50 border border-gray-700 rounded-xl px-4 py-3 text-white focus:border-purple-500 focus:outline-none transition-all"
                          placeholder="/audio/theme.mp3"
                        />
                        <input
                          type="file"
                          ref={musicInputRef}
                          onChange={handleAudioUpload}
                          className="hidden"
                          accept="audio/*"
                        />
                        <button
                          onClick={() => musicInputRef.current?.click()}
                          disabled={isUploading}
                          className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-xl text-gray-400 hover:text-white hover:border-gray-500 transition-all disabled:opacity-50"
                        >
                          {isUploading ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'Browse'}
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Right Side: Preview */}
                  <div className="space-y-4">
                    <label className="block text-xs font-black uppercase tracking-widest text-gray-500">
                      Live Preview
                    </label>
                    <div className="aspect-[16/10] bg-black rounded-2xl border border-white/5 overflow-hidden shadow-2xl relative group">
                      {/* Background Flyer Mock */}
                      <div className="absolute inset-0">
                        {launcherSettings.flyer_image ? (
                          <img
                            src={launcherSettings.flyer_image.startsWith('http') ? launcherSettings.flyer_image : getAssetUrl(project?.name, launcherSettings.flyer_image) || ''}
                            alt="Preview"
                            className="w-full h-full object-cover opacity-60"
                          />
                        ) : (
                          <div className="w-full h-full bg-gradient-to-br from-purple-900/20 to-black flex items-center justify-center">
                            <ImageIcon className="w-12 h-12 text-gray-800" />
                          </div>
                        )}
                        <div className="absolute inset-0 bg-gradient-to-t from-black via-black/40 to-transparent"></div>
                      </div>

                      {/* Info Mock */}
                      < div className="absolute inset-x-6 bottom-6 text-left" >
                        <div className="mb-2 px-2 py-0.5 bg-purple-600/20 border border-purple-500/30 rounded text-[8px] font-black text-purple-400 w-fit uppercase tracking-widest">
                          Saga Adventure
                        </div>
                        <h4 className="text-xl font-black text-white italic uppercase tracking-tighter mb-1 truncate">
                          {launcherSettings.title || 'Game Title'}
                        </h4>
                        <p className="text-[10px] text-gray-400 line-clamp-2 max-w-[80%]">
                          {launcherSettings.description || 'No description provided.'}
                        </p>
                      </div >

                      <div className="absolute top-4 right-4 text-[8px] font-black text-white/30 tracking-widest">
                        PREVIEW ONLY
                      </div>
                    </div >
                    <p className="text-[10px] text-gray-500 text-center italic">
                      This is a simplified preview. Launch the game to see full effects.
                    </p>
                  </div >
                </div >
              </div >
            )}

            {/* API KEYS */}
            {
              activeTab === 'api' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-4">API Configuration</h3>
                    <p className="text-sm text-gray-400 mb-6">
                      Configure your API keys for AI services. Keys are stored locally and never shared.
                    </p>
                  </div>

                  {/* Gemini API */}
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-300">
                      Google Gemini API Key
                    </label>
                    <div className="relative">
                      <input
                        type={showApiKey ? 'text' : 'password'}
                        value={settings.geminiApiKey}
                        onChange={(e) => {
                          updateSetting('geminiApiKey', e.target.value);
                          if (apiKeyStatus === 'valid' && e.target.value !== placeholderKey) {
                            setApiKeyStatus('idle');
                          }
                        }}
                        placeholder="AIzaSy..."
                        className="w-full bg-gray-800 text-white px-4 py-3 pr-20 rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
                      />
                      <button
                        onClick={() => setShowApiKey(!showApiKey)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:bg-gray-700 rounded"
                      >
                        {showApiKey ? <EyeOff className="w-4 h-4 text-gray-400" /> : <Eye className="w-4 h-4 text-gray-400" />}
                      </button>
                    </div>
                    <p className="text-xs text-gray-500">
                      Get your key at <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">Google AI Studio</a>
                    </p>
                  </div>

                  {/* OpenAI API (opcional) */}
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-300">
                      OpenAI API Key <span className="text-gray-500">(Optional)</span>
                    </label>
                    <input
                      type={showApiKey ? 'text' : 'password'}
                      value={settings.openaiApiKey}
                      onChange={(e) => updateSetting('openaiApiKey', e.target.value)}
                      placeholder="sk-..."
                      className="w-full bg-gray-800 text-white px-4 py-3 rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
                    />
                    <p className="text-xs text-gray-500">
                      For GPT-4 Vision features (experimental)
                    </p>
                  </div>

                  <div className="flex items-center gap-4">
                    {/* Test Connection */}
                    <button
                      onClick={handleTestConnection}
                      disabled={apiKeyStatus === 'checking'}
                      className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:bg-gray-500"
                    >
                      <RefreshCw className="w-4 h-4" />
                      Test Connection
                    </button>
                    {/* Status Indicator */}
                    <div className="flex items-center gap-2">
                      {apiKeyStatus === 'checking' && <div className="w-4 h-4 border-2 border-t-blue-400 border-gray-600 rounded-full animate-spin"></div>}
                      {apiKeyStatus === 'valid' && <CheckCircle className="w-5 h-5 text-green-500" />}
                      {apiKeyStatus === 'invalid' && <XCircle className="w-5 h-5 text-red-500" />}
                      <span className={`text-sm ${apiKeyStatus === 'valid' ? 'text-green-400' :
                        apiKeyStatus === 'invalid' ? 'text-red-400' : 'text-gray-400'
                        }`}>
                        {apiKeyStatus === 'valid' && 'Key is configured'}
                        {apiKeyStatus === 'invalid' && 'Key not found or invalid'}
                        {apiKeyStatus === 'checking' && 'Checking...'}
                      </span>
                    </div>
                  </div>
                </div>
              )
            }

            {/* IMAGE GENERATION */}
            {
              activeTab === 'generation' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-4">Image Generation Settings</h3>
                  </div>

                  {/* Provider */}
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-300">
                      Image Provider
                    </label>
                    <select
                      value={settings.imageProvider}
                      onChange={(e) => updateSetting('imageProvider', e.target.value)}
                      className="w-full bg-gray-800 text-white px-4 py-3 rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
                    >
                      <option value="sana">SANA Local (Free, GPU required)</option>
                      <option value="gemini">Google Gemini Imagen (Cloud, 50 free/day)</option>
                      <option value="openai">OpenAI DALL-E 3 (Cloud, paid)</option>
                    </select>
                  </div>

                  {/* Resolution */}
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-300">
                      Default Resolution
                    </label>
                    <select
                      value={settings.imageResolution}
                      onChange={(e) => updateSetting('imageResolution', e.target.value)}
                      className="w-full bg-gray-800 text-white px-4 py-3 rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
                    >
                      <option value="512x512">512x512 (Fast)</option>
                      <option value="768x768">768x768 (Balanced)</option>
                      <option value="1024x1024">1024x1024 (Recommended)</option>
                      <option value="1536x1536">1536x1536 (High Quality)</option>
                      <option value="2048x2048">2048x2048 (Maximum)</option>
                    </select>
                  </div>

                  {/* Quality */}
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-300">
                      Image Quality
                    </label>
                    <select
                      value={settings.imageQuality}
                      onChange={(e) => updateSetting('imageQuality', e.target.value)}
                      className="w-full bg-gray-800 text-white px-4 py-3 rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
                    >
                      <option value="draft">Draft (Faster)</option>
                      <option value="standard">Standard</option>
                      <option value="high">High Quality (Slower)</option>
                    </select>
                  </div>

                  {/* Advanced - só aparece se SANA */}
                  {settings.imageProvider === 'sana' && (
                    <>
                      <div className="space-y-2">
                        <label className="block text-sm font-medium text-gray-300">
                          Inference Steps: {settings.inferenceSteps}
                        </label>
                        <input
                          type="range"
                          min="10"
                          max="50"
                          value={settings.inferenceSteps}
                          onChange={(e) => updateSetting('inferenceSteps', parseInt(e.target.value))}
                          className="w-full"
                        />
                        <p className="text-xs text-gray-500">
                          More steps = better quality but slower. Recommended: 20-30
                        </p>
                      </div>

                      <div className="space-y-2">
                        <label className="block text-sm font-medium text-gray-300">
                          Guidance Scale: {settings.guidanceScale}
                        </label>
                        <input
                          type="range"
                          min="1"
                          max="15"
                          step="0.5"
                          value={settings.guidanceScale}
                          onChange={(e) => updateSetting('guidanceScale', parseFloat(e.target.value))}
                          className="w-full"
                        />
                        <p className="text-xs text-gray-500">
                          How closely to follow the prompt. Recommended: 7-9
                        </p>
                      </div>
                    </>
                  )}
                </div>
              )
            }

            {/* PERFORMANCE */}
            {
              activeTab === 'performance' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-4">Performance Settings</h3>
                  </div>

                  {/* GPU Usage */}
                  <div className="flex items-center justify-between p-4 bg-gray-800 rounded-lg">
                    <div>
                      <div className="font-medium text-white">Use GPU Acceleration</div>
                      <div className="text-sm text-gray-400">Requires CUDA-compatible GPU</div>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.useGPU}
                        onChange={(e) => updateSetting('useGPU', e.target.checked)}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-700 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>

                  {/* Device Type */}
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-300">
                      Compute Device
                    </label>
                    <select
                      value={settings.deviceType}
                      onChange={(e) => updateSetting('deviceType', e.target.value)}
                      className="w-full bg-gray-800 text-white px-4 py-3 rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
                      disabled={!settings.useGPU}
                    >
                      <option value="cuda">CUDA (NVIDIA GPU)</option>
                      <option value="cpu">CPU Only</option>
                      <option value="mps">MPS (Apple Silicon)</option>
                    </select>
                  </div>

                  {/* Cache */}
                  <div className="flex items-center justify-between p-4 bg-gray-800 rounded-lg">
                    <div>
                      <div className="font-medium text-white">Enable Model Caching</div>
                      <div className="text-sm text-gray-400">Faster loading, uses more disk space</div>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.cacheEnabled}
                        onChange={(e) => updateSetting('cacheEnabled', e.target.checked)}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-700 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>

                  {/* Telemetry */}
                  <div className="flex items-center justify-between p-4 bg-gray-800 rounded-lg">
                    <div>
                      <div className="font-medium text-white">Usage Analytics</div>
                      <div className="text-sm text-gray-400">Help improve Saga Engine</div>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.telemetry}
                        onChange={(e) => updateSetting('telemetry', e.target.checked)}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-700 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>

                  {/* Beta Features */}
                  <div className="flex items-center justify-between p-4 bg-gray-800 rounded-lg">
                    <div>
                      <div className="font-medium text-white">Beta Features</div>
                      <div className="text-sm text-gray-400">Enable experimental features</div>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.betaFeatures}
                        onChange={(e) => updateSetting('betaFeatures', e.target.checked)}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-700 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>

                  {/* Clear Cache */}
                  <div className="space-y-3">
                    <label className="block text-sm font-medium text-gray-300">
                      Storage Management
                    </label>
                    <button className="w-full px-4 py-3 bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition-colors text-left">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-medium">Clear Model Cache</div>
                          <div className="text-sm text-gray-400">Frees ~10GB disk space</div>
                        </div>
                        <HardDrive className="w-5 h-5 text-gray-400" />
                      </div>
                    </button>
                    <button className="w-full px-4 py-3 bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition-colors text-left">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-medium">Clear Project Cache</div>
                          <div className="text-sm text-gray-400">Frees ~500MB disk space</div>
                        </div>
                        <HardDrive className="w-5 h-5 text-gray-400" />
                      </div>
                    </button>
                  </div>

                  {/* Reset Settings */}
                  <div className="pt-4 border-t border-gray-700">
                    <button className="w-full px-4 py-3 bg-red-600/10 hover:bg-red-600/20 text-red-400 rounded-lg transition-colors font-medium">
                      Reset All Settings to Default
                    </button>
                  </div>
                </div>
              )
            }

            {/* EDITOR */}
            {
              activeTab === 'editor' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-4">Editor Preferences</h3>
                  </div>

                  {/* Canvas Resolution */}
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-300">
                      Canvas Resolution
                    </label>
                    <select
                      value={settings.canvasResolution}
                      onChange={(e) => updateSetting('canvasResolution', e.target.value)}
                      className="w-full bg-gray-800 text-white px-4 py-3 rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
                    >
                      <option value="1280x720">1280x720 (HD)</option>
                      <option value="1920x1080">1920x1080 (Full HD)</option>
                      <option value="2560x1440">2560x1440 (2K)</option>
                      <option value="3840x2160">3840x2160 (4K)</option>
                    </select>
                  </div>

                  {/* Grid Size */}
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-300">
                      Grid Size: {settings.gridSize}px
                    </label>
                    <input
                      type="range"
                      min="8"
                      max="64"
                      step="8"
                      value={settings.gridSize}
                      onChange={(e) => updateSetting('gridSize', parseInt(e.target.value))}
                      className="w-full"
                    />
                  </div>

                  {/* Snap to Grid */}
                  <div className="flex items-center justify-between p-4 bg-gray-800 rounded-lg">
                    <div>
                      <div className="font-medium text-white">Snap to Grid</div>
                      <div className="text-sm text-gray-400">Auto-align objects to grid</div>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.snapToGrid}
                        onChange={(e) => updateSetting('snapToGrid', e.target.checked)}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-700 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>

                  {/* Show Grid */}
                  <div className="flex items-center justify-between p-4 bg-gray-800 rounded-lg">
                    <div>
                      <div className="font-medium text-white">Show Grid</div>
                      <div className="text-sm text-gray-400">Display grid lines on canvas</div>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.showGrid}
                        onChange={(e) => updateSetting('showGrid', e.target.checked)}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-700 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>

                  {/* Auto Save */}
                  <div className="flex items-center justify-between p-4 bg-gray-800 rounded-lg">
                    <div>
                      <div className="font-medium text-white">Auto Save</div>
                      <div className="text-sm text-gray-400">Automatically save changes</div>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.autoSave}
                        onChange={(e) => updateSetting('autoSave', e.target.checked)}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-700 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>

                  {settings.autoSave && (
                    <div className="space-y-2">
                      <label className="block text-sm font-medium text-gray-300">
                        Auto Save Interval: {settings.autoSaveInterval}s
                      </label>
                      <input
                        type="range"
                        min="60"
                        max="600"
                        step="60"
                        value={settings.autoSaveInterval}
                        onChange={(e) => updateSetting('autoSaveInterval', parseInt(e.target.value))}
                        className="w-full"
                      />
                    </div>
                  )}
                </div>
              )
            }

            {/* EXPORT */}
            {
              activeTab === 'export' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-4">Export Settings</h3>
                  </div>

                  {/* Format */}
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-300">
                      Export Format
                    </label>
                    <select
                      value={settings.exportFormat}
                      onChange={(e) => updateSetting('exportFormat', e.target.value)}
                      className="w-full bg-gray-800 text-white px-4 py-3 rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
                    >
                      <option value="html">HTML5 (Web)</option>
                      <option value="electron">Electron (Desktop App)</option>
                      <option value="cordova">Cordova (Mobile App)</option>
                      <option value="scorm">SCORM (LMS Compatible)</option>
                      <option value="json">JSON (Data Only)</option>
                    </select>
                  </div>

                  {/* Compression */}
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-300">
                      Asset Compression
                    </label>
                    <select
                      value={settings.compressionLevel}
                      onChange={(e) => updateSetting('compressionLevel', e.target.value)}
                      className="w-full bg-gray-800 text-white px-4 py-3 rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
                    >
                      <option value="none">None (Larger file, best quality)</option>
                      <option value="low">Low (Balanced)</option>
                      <option value="medium">Medium (Recommended)</option>
                      <option value="high">High (Smaller file)</option>
                    </select>
                  </div>

                  {/* Include Assets */}
                  <div className="flex items-center justify-between p-4 bg-gray-800 rounded-lg">
                    <div>
                      <div className="font-medium text-white">Include All Assets</div>
                      <div className="text-sm text-gray-400">Embed images/audio in export</div>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.includeAssets}
                        onChange={(e) => updateSetting('includeAssets', e.target.checked)}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-700 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>
                </div>
              )
            }

            {/* GENERAL */}
            {
              activeTab === 'general' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-4">General Settings</h3>
                  </div>

                  {/* Language */}
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-300">
                      Language
                    </label>
                    <select
                      value={settings.language}
                      onChange={(e) => updateSetting('language', e.target.value)}
                      className="w-full bg-gray-800 text-white px-4 py-3 rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
                    >
                      <option value="en-US">English (US)</option>
                      <option value="pt-BR">Português (Brasil)</option>
                      <option value="es-ES">Español</option>
                      <option value="fr-FR">Français</option>
                      <option value="de-DE">Deutsch</option>
                    </select>
                  </div>

                  {/* Timezone */}
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-300">
                      Timezone
                    </label>
                    <select
                      value={settings.timezone}
                      onChange={(e) => updateSetting('timezone', e.target.value)}
                      className="w-full bg-gray-800 text-white px-4 py-3 rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
                    >
                      <option value="America/Sao_Paulo">São Paulo (GMT-3)</option>
                      <option value="America/New_York">New York (GMT-5)</option>
                      <option value="Europe/London">London (GMT+0)</option>
                      <option value="Asia/Tokyo">Tokyo (GMT+9)</option>
                    </select>
                  </div>

                  {/* Theme */}
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-300">
                      Theme
                    </label>
                    <div className="grid grid-cols-3 gap-3">
                      {['dark', 'light', 'auto'].map(theme => (
                        <button
                          key={theme}
                          onClick={() => updateSetting('theme', theme)}
                          className={`p-3 rounded-lg border-2 transition-colors capitalize ${settings.theme === theme
                            ? 'border-blue-500 bg-blue-500/10'
                            : 'border-gray-700 hover:border-gray-600'
                            }`}
                        >
                          <Palette className="w-5 h-5 mx-auto mb-1 text-gray-400" />
                          <div className="text-sm text-gray-300">{theme}</div>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Accent Color */}
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-300">
                      Accent Color
                    </label>
                    <div className="flex gap-3">
                      <input
                        type="color"
                        value={settings.accentColor}
                        onChange={(e) => updateSetting('accentColor', e.target.value)}
                        className="h-12 w-20 rounded-lg cursor-pointer"
                      />
                      <input
                        type="text"
                        value={settings.accentColor}
                        onChange={(e) => updateSetting('accentColor', e.target.value)}
                        className="flex-1 bg-gray-800 text-white px-4 py-3 rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
                      />
                    </div>
                  </div>
                </div>
              )
            }

            {/* ADVANCED */}
            {
              activeTab === 'advanced' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-4">Advanced Settings</h3>
                    <p className="text-sm text-yellow-400">
                      ⚠️ Only change these if you know what you're doing
                    </p>
                  </div>

                  {/* Debug Mode */}
                  <div className="flex items-center justify-between p-4 bg-gray-800 rounded-lg">
                    <div>
                      <div className="font-medium text-white">Debug Mode</div>
                      <div className="text-sm text-gray-400">Show console logs and errors</div>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.debugMode}
                        onChange={(e) => updateSetting('debugMode', e.target.checked)}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-700 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                  </div>
                </div>
              )
            }

          </div >
        </div >

        {/* Footer */}
        < div className="flex items-center justify-between p-6 border-t border-gray-800" >
          <div className="text-sm text-gray-400">
            Changes are saved automatically
          </div>
          <div className="flex gap-3">
            <button
              onClick={onClose} // Usa a função onClose do pai
              className="px-6 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSaveAndClose}
              className="flex items-center gap-2 px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              <Save className="w-4 h-4" />
              Save Changes
            </button>
          </div>
        </div >

      </div >
    </div >
  );
};

export default SettingsPanel;
