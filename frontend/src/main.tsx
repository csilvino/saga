import React from 'react';
import ReactDOM from 'react-dom/client';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import App from './App.tsx';
import AuthCallback from './AuthCallback.tsx'; // Importa o novo componente
import './index.css';

// Configuração do roteador
const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    // TODO: Adicionar uma página de erro elegante
    // errorElement: <ErrorPage />,
  },
  {
    path: "/auth/callback",
    element: <AuthCallback />,
  },
]);

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
);
