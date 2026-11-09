// D:/PythonProject/saga/frontend/src/AuthCallback.tsx
import React, { useEffect, useState } from 'react';
import api from './services/api';
import { Sparkles } from 'lucide-react';

const AuthCallback = () => {
  const [status, setStatus] = useState('Autenticando com o Google...');
  const [error, setError] = useState('');

  useEffect(() => {
    const processAuth = async () => {
      try {
        console.log("AuthCallback montado. URL:", window.location.href);
        const params = new URLSearchParams(window.location.search);
        const code = params.get('code');
        const state = params.get('state');
        const errorParam = params.get('error');

        console.log("Params:", { code, state, error: errorParam });

        if (errorParam) {
            setError(`Erro retornado pelo Google: ${errorParam}`);
            setStatus('Falha na autenticação.');
            return;
        }

        if (!code) {
          setError('Código de autenticação não encontrado na URL.');
          setStatus('Falha na autenticação.');
          return;
        }

        setStatus('Validando credenciais com o servidor...');
        // O state é opcional aqui, mas se vier, passamos para o backend
        const payload = { code, state: state || undefined };
        const response = await api.post('/api/auth/google/callback', payload);

        const { session_token, user } = response.data;

        if (!session_token) {
          setError('O servidor não retornou um token de sessão.');
          setStatus('Falha na autenticação.');
          return;
        }

        // Envia mensagem para a janela pai (App.tsx)
        if (window.opener) {
            window.opener.postMessage({
                type: 'auth_success',
                token: session_token,
                user: user
            }, window.location.origin); // Restringe a origem para segurança
        }

        setStatus('Login realizado com sucesso! Esta janela será fechada em breve.');

        setTimeout(() => {
          window.close();
        }, 1500);

      } catch (err) {
        console.error('Erro durante o callback de autenticação:', err);

        let errorDetail = 'Ocorreu um erro desconhecido.';
        if (err.response && err.response.data && err.response.data.detail) {
            if (typeof err.response.data.detail === 'object') {
                errorDetail = JSON.stringify(err.response.data.detail);
            } else {
                errorDetail = err.response.data.detail;
            }
        }

        setError(`Falha na comunicação com o servidor: ${errorDetail}`);
        setStatus('Falha na autenticação.');
      }
    };

    processAuth();
  }, []);

  return (
    <div className="w-full h-screen bg-gray-950 text-white flex items-center justify-center">
      <div className="text-center p-8">
        <Sparkles className="w-12 h-12 text-purple-400 mx-auto mb-6 animate-pulse" />
        <h1 className="text-2xl font-bold text-gray-200 mb-2">{status}</h1>
        {error && <p className="text-red-400 max-w-md break-all">{error}</p>}
        <p className="text-gray-500 mt-4">Por favor, aguarde. Você será redirecionado em breve.</p>
      </div>
    </div>
  );
};

export default AuthCallback;
