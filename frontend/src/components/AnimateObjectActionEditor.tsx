import React from 'react';
import { ToyBrick } from 'lucide-react';
import type { Action } from '../types';

const AnimateObjectActionEditor = ({ action, onUpdateAction, sceneObjects }) => {
  const handleUpdate = (field, value) => {
    onUpdateAction(action.id, {
      ...action,
      payload: { ...action.payload, [field]: value },
    });
  };

  return (
    <div className="p-3 bg-gray-800 rounded-lg space-y-2 border border-gray-700">
      <div className="flex items-center gap-2">
        <ToyBrick className="w-4 h-4 text-purple-400" />
        <span className="text-sm font-semibold text-gray-300">Animar Objeto</span>
      </div>
      <div>
        <label className="block text-xs text-gray-400 mb-1">Objeto Alvo</label>
        <select
          value={action.payload?.objectId || ''}
          onChange={(e) => handleUpdate('objectId', e.target.value)}
          className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded-md text-sm focus:outline-none focus:border-purple-500"
        >
          <option value="">Selecione um objeto...</option>
          {sceneObjects.map(obj => (
            <option key={obj.id} value={obj.id}>{obj.name}</option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-xs text-gray-400 mb-1">Propriedade</label>
        <select
          value={action.payload?.property || 'rotation'}
          onChange={(e) => handleUpdate('property', e.target.value)}
          className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded-md text-sm focus:outline-none focus:border-purple-500"
        >
          <option value="rotation">Rotação</option>
          <option value="position.x">Posição X</option>
          <option value="position.y">Posição Y</option>
          <option value="scale.x">Escala X</option>
          <option value="scale.y">Escala Y</option>
        </select>
      </div>
      <div>
        <label className="block text-xs text-gray-400 mb-1">Tipo de Animação</label>
        <select
          value={action.payload?.animationType || 'swing'}
          onChange={(e) => handleUpdate('animationType', e.target.value)}
          className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded-md text-sm focus:outline-none focus:border-purple-500"
        >
          <option value="swing">Balanço (Pêndulo)</option>
          <option value="linear">Linear</option>
        </select>
      </div>
      <div className="flex gap-2">
        <div className="flex-1">
          <label className="block text-xs text-gray-400 mb-1">Duração (ms)</label>
          <input
            type="number"
            value={action.payload?.duration || 1000}
            onChange={(e) => handleUpdate('duration', parseInt(e.target.value, 10))}
            className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded-md text-sm"
          />
        </div>
        <div className="flex-1">
          <label className="block text-xs text-gray-400 mb-1">De (valor)</label>
          <input
            type="number"
            value={action.payload?.from || -30}
            onChange={(e) => handleUpdate('from', parseFloat(e.target.value))}
            className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded-md text-sm"
          />
        </div>
        <div className="flex-1">
          <label className="block text-xs text-gray-400 mb-1">Até (valor)</label>
          <input
            type="number"
            value={action.payload?.to || 30}
            onChange={(e) => handleUpdate('to', parseFloat(e.target.value))}
            className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded-md text-sm"
          />
        </div>
      </div>
    </div>
  );
};

export default AnimateObjectActionEditor;
