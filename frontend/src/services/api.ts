import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8070',
});


/**
 * Constructs the full URL for a given project asset.
 * This URL is intended to be used directly in `src` attributes of images, etc.
 * @param projectName The name of the project.
 * @param assetPath The relative path of the asset within the project's asset folder.
 * @returns The full, accessible URL for the asset, or null if the path is invalid.
 */
/** A sprite that is not a file: an emoji or text placeholder put there when the object was created. */
export const isPlaceholderSprite = (sprite: string | null | undefined): boolean =>
  !!sprite && !sprite.startsWith('http') && !/\.[a-z0-9]{2,5}(\?.*)?$/i.test(sprite);

export const getAssetUrl = (projectName: string, assetPath: string | null | undefined): string | null => {
  if (!projectName || !assetPath || isPlaceholderSprite(assetPath)) {
    return null;
  }
  // The backend route is /api/assets/{project_name}/{asset_path}
  // The axios baseURL is http://localhost:8000
  // So we construct the path part of the URL.
  const cleanedAssetPath = assetPath.startsWith('/') ? assetPath.substring(1) : assetPath;
  return `${api.defaults.baseURL}/api/assets/${encodeURIComponent(projectName)}/${cleanedAssetPath}`;
};


/**
 * Função para fazer upload de um arquivo de sprite.
 * @param file O arquivo a ser enviado.
 * @param projectName O nome do projeto para contextualizar o upload.
 * @returns A resposta da API, que deve conter o caminho do novo asset.
 */
export const uploadSprite = async (file: File, projectName: string) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('project_name', projectName);
  // O backend espera o 'asset_type' para saber em qual pasta salvar.
  // Vamos derivar isso do tipo de arquivo.
  const assetType = file.type.startsWith('image/') ? 'sprites' : 'audio';
  formData.append('asset_type', assetType);

  const response = await api.post('/api/assets/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

/**
 * Salva a chave da API do Gemini no backend.
 * @param apiKey A chave da API a ser salva.
 * @returns A resposta da API.
 */
export const saveApiKey = async (apiKey: string) => {
  const response = await api.post('/api/tools/save-api-key', { api_key: apiKey });
  return response.data;
};

/**
 * Verifica se a chave da API do Gemini já está configurada no backend.
 * @returns A resposta da API, contendo { configured: boolean }.
 */
export const checkApiKey = async (validate: boolean = false) => {
  const response = await api.get('/api/tools/check-api-key', { params: { validate } });
  return response.data as { configured: boolean; valid?: boolean; error?: string };
};

export type ModelInfo = { name: string; label: string };
export type ModelsResponse = { text_model: string; image_model: string; text: ModelInfo[]; image: ModelInfo[]; error?: string };

/** Modelos Gemini disponíveis para a chave do usuário, e os escolhidos agora. */
export const listModels = async () => {
  const response = await api.get('/api/tools/models');
  return response.data as ModelsResponse;
};

/** Salva os modelos escolhidos (texto/orquestração e imagem). */
export const saveModels = async (textModel?: string, imageModel?: string) => {
  const response = await api.post('/api/tools/models', { text_model: textModel, image_model: imageModel });
  return response.data;
};

export interface SesProblem { line: number; col: number; message: string; }
export interface SesValidation { ok: boolean; errors: SesProblem[]; warnings: SesProblem[]; }

/** Valida um script SES (sintaxe e referências a objetos/cenas do projeto). */
export const validateSes = async (script: string, projectName?: string, ownerKind: 'object' | 'scene' = 'object'): Promise<SesValidation> => {
  const response = await api.post('/api/ses/validate', { script, project_name: projectName, owner_kind: ownerKind });
  return response.data;
};

/** Remove a chave da API do Gemini das configurações do usuário. */
export const deleteApiKey = async () => {
  const response = await api.delete('/api/tools/api-key');
  return response.data;
};


/**
 * Solicita à IA parâmetros de animação para um objeto.
 * @param objectName Nome do objeto.
 * @param hint Dica opcional sobre a animação desejada.
 * @returns Sugestão de animação da IA.
 */
export const suggestAnimation = async (objectName: string, hint: string = "") => {
  const response = await api.post('/api/ai/suggest-animation', {
    object_name: objectName,
    hint: hint
  });
  return response.data;
};

export const magicPartAnimate = async (projectName: string, imagePath: string, objectName: string) => {
  const response = await api.post('/api/ai/magic-part-animate', {
    project_name: projectName,
    image_path: imagePath,
    object_name: objectName
  });
  return response.data;
};

/**
 * Solicita à IA a geração de um sprite sheet animado para o objeto.
 * @param projectName Nome do projeto.
 * @param objectId ID do objeto.
 * @param description O que a animação deve fazer.
 * @param frameCount Quantidade de frames desejados.
 */
export const animateObjectWithAI = async (projectName: string, objectId: string, description: string, frameCount: number = 3) => {
  const response = await api.post('/api/genai/animate-object', {
    project_name: projectName,
    object_id: objectId,
    description: description,
    frame_count: frameCount
  });
  return response.data;
};

export default api;
