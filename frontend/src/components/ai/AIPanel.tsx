import React, { useState, useEffect, useRef } from 'react';
import { Sparkles, Send, Trash2, Bot, Terminal, BookOpen, Palette, Box, Wand2, Image as ImageIcon, ChevronRight, ChevronLeft } from 'lucide-react';
import { toast } from 'react-hot-toast';
import api from '../../services/api';
import type { Project, Scene } from '../../types';
import { ResizeHandle } from '../ui';

const WORKFLOWS = {
  diretor: { icon: Sparkles, title: 'Diretor', description: 'Crie cenas e objetos seguindo o estilo atual.', template: 'Como Diretor, crie uma nova cena baseada no estilo visual da cena "[ID_REF]" e nomeie-a como "[NOME]". Inclua lógica SES.' },
  scripting: { icon: Terminal, title: 'SES Expert', description: 'Crie lógica de interação e narrativa.', template: 'Escreva um script SES para o objeto "[NOME]" com uma descrição rica em "on examine" e uma interação com outro objeto em "on use with".' },
  narrativa: { icon: BookOpen, title: 'Narrador', description: 'Gere descrições imersivas para o log.', template: 'Descreva a cena atual de forma poética e detalhada para o jogador, focando na atmosfera Calixto Island.' },
  imageMaker: { icon: Palette, title: 'Visual', description: 'Gere backgrounds e sprites.', template: 'Gere uma imagem de fundo para a cena [NOME] que seja [DESCRIÇÃO].' }
};

const CHAT_HISTORY_KEY = 'saga_ai_chat_history';
const defaultWelcomeMessage = { sender: 'ai', text: 'Olá! Sou o Diretor. Peça um adventure ("crie um jogo de mistério numa mansão com 4 salas") ou uma mudança ("a porta só abre com a chave"). Eu construo, testo jogando e conto como vencer.' };

interface AIPanelProps {
  project: Project;
  activeScene: Scene | null;
  selectedObjectId: string | null;
  onProjectUpdate: () => void;
  resizable: {
    width: number;
    isResizing: boolean;
    handleMouseDown: (e: React.MouseEvent) => void;
  };
  onStartExtraction?: (prompt: string) => void;
}

const AIPanelComponent: React.FC<AIPanelProps> = ({ project, activeScene, selectedObjectId, onProjectUpdate, resizable, onStartExtraction }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [activeTab, setActiveTab] = useState('chat');
  const [messages, setMessages] = useState(() => {
    try {
      const saved = localStorage.getItem(CHAT_HISTORY_KEY);
      return saved ? JSON.parse(saved) : [defaultWelcomeMessage];
    } catch {
      return [defaultWelcomeMessage];
    }
  });
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    localStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(messages));
  }, [messages]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const newMessage = { sender: 'user', text: input };
    setMessages(prev => [...prev, newMessage]);
    setInput('');
    setIsLoading(true);

    // Constrói o contexto para enviar ao backend
    const context = {
      project_name: project.name,
      active_scene: activeScene,
      selected_object_id: selectedObjectId,
    };

    try {
      const response = await api.post('/api/orchestrator/command', {
        prompt: input,
        context: context,
      });
      const { text_response } = response.data;

      if (text_response) setMessages(prev => [...prev, { sender: 'ai', text: text_response }]);

      const tool_responses = response.data.tool_responses || [];

      if (tool_responses.length > 0) {
        // one summary line per answer ("🔧 12 ações: create_scene ×3, ..."), with the details folded
        const counts: Record<string, number> = {};
        tool_responses.forEach((tr: any) => { counts[tr.tool] = (counts[tr.tool] || 0) + 1; });
        const failed = tool_responses.filter((tr: any) => tr.result?.error).length;
        const summary = Object.entries(counts).map(([t, n]) => n > 1 ? `${t} ×${n}` : t).join(', ');
        const details = tool_responses.map((tr: any) =>
          `${tr.result?.error ? '✖' : '✔'} ${tr.tool} ${JSON.stringify(tr.args || {})}\n   → ${JSON.stringify(tr.result)}`).join('\n');
        setMessages(prev => [...prev, {
          sender: 'system',
          text: `🔧 ${tool_responses.length} ações: ${summary}${failed ? ` (${failed} com erro, corrigidas pela IA)` : ''}`,
          details,
        }]);
      }
      if (response.data.project_changed || tool_responses.length > 0) {
        onProjectUpdate();
      }
    } catch (error) {
      const errorText = error.response?.data?.detail || "Ocorreu um erro.";
      setMessages(prev => [...prev, { sender: 'ai', text: `Desculpe, falhei. ${errorText}` }]);
      toast.error("Erro no comando com a IA.");
    } finally {
      setIsLoading(false);
    }
  };

  // Starts a new conversation: the director forgets what was said (the project stays as it is)
  const handleNewConversation = async () => {
    try {
      await api.post('/api/orchestrator/reset', { project_name: project.name });
    } catch { /* the next message starts a new chat anyway */ }
    setMessages([defaultWelcomeMessage]);
  };

  const handleWorkflowClick = (template: string) => {
    setInput(template);
    setActiveTab('chat');
  };

  if (isCollapsed) {
    return <button onClick={() => setIsCollapsed(false)} className="w-12 h-full bg-gray-950 border-l border-gray-800 flex items-center justify-center"><ChevronLeft className="w-6 h-6 text-purple-400" /></button>;
  }

  const renderContent = () => {
    if (activeTab === 'director') {
      return (
        <div className="flex-1 overflow-auto p-4">
          <h3 className="text-lg font-bold mb-4">Workflows do Diretor</h3>
          <div className="space-y-3">
            {Object.entries(WORKFLOWS).map(([key, wf]) => {
              const Icon = wf.icon;
              return (
                <button key={key} onClick={() => handleWorkflowClick(wf.template)} className="w-full p-4 rounded-lg border border-purple-500/20 bg-purple-500/5 hover:bg-purple-500/10 transition-all text-left group">
                  <div className="flex items-center gap-4">
                    <Icon className={`w-8 h-8 text-purple-400`} />
                    <div>
                      <h4 className="font-semibold">{wf.title}</h4>
                      <p className="text-xs text-gray-400">{wf.description}</p>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      );
    }
    // Padrão é o chat
    return (
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex gap-3 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.sender === 'ai' && <Sparkles className="w-5 h-5 text-purple-400 flex-shrink-0 mt-1" />}
              {msg.sender === 'system' && <Terminal className="w-5 h-5 text-green-400 flex-shrink-0 mt-1" />}
              <div className={`max-w-[90%] rounded-lg p-3 ${msg.sender === 'user' ? 'bg-purple-600 text-white' : 'bg-gray-800 text-gray-300'}`}>
                <p className="text-sm whitespace-pre-wrap">{msg.text}</p>
                {msg.details && <details className="mt-2"><summary className="text-xs text-gray-500 cursor-pointer">detalhes</summary><pre className="mt-1 p-2 bg-gray-900 rounded-lg text-xs text-green-300 overflow-x-auto whitespace-pre-wrap"><code>{msg.details}</code></pre></details>}
              </div>
            </div>
          ))}
          {isLoading && <div className="flex justify-start"><div className="p-3 bg-gray-800 rounded-lg">...</div></div>}
          <div ref={chatEndRef} />
        </div>
        <div className="p-4 border-t border-gray-800">
          <form onSubmit={handleSendMessage} className="flex gap-2">
            <input type="text" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Descreva o que precisa..." className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-purple-500" />
            <button type="submit" className="p-2 bg-purple-600 hover:bg-purple-500 rounded-lg"><Send className="w-5 h-5" /></button>
          </form>
        </div>
      </div>
    );
  };

  return (
    <>
      <ResizeHandle onMouseDown={resizable.handleMouseDown} isResizing={resizable.isResizing} />
      <div style={{ width: `${resizable.width}px` }} className="bg-gray-900 border-l border-gray-800 flex flex-col relative overflow-hidden">
        <button onClick={() => setIsCollapsed(true)} className="absolute -left-8 top-1/2 -translate-y-1/2 w-8 h-16 bg-gray-900 border border-gray-800 rounded-l-lg flex items-center justify-center hover:bg-gray-800 z-10"><ChevronRight className="w-5 h-5" /></button>

        <div className="flex border-b border-gray-800">
          <button onClick={() => setActiveTab('chat')} className={`flex-1 py-3 text-sm font-semibold ${activeTab === 'chat' ? 'text-purple-400 border-b-2 border-purple-400' : 'text-gray-500 hover:text-gray-300'}`}>💬 Chat</button>
          <button onClick={() => setActiveTab('director')} className={`flex-1 py-3 text-sm font-semibold ${activeTab === 'director' ? 'text-purple-400 border-b-2 border-purple-400' : 'text-gray-500 hover:text-gray-300'}`}>🎬 Diretor</button>
          <button onClick={handleNewConversation} title="Nova conversa (a IA esquece o histórico)" className="px-3 text-gray-500 hover:text-red-400"><Trash2 className="w-4 h-4" /></button>
        </div>

        {renderContent()}
      </div>
    </>
  );
};

export const AIPanel = React.memo(AIPanelComponent);
