"""
Provedor de IA para a API do Google Gemini.
"""
import os
from typing import Optional
import google.generativeai as genai

class GeminiProvider:
    """
    Provedor específico para a API do Google Gemini.
    """
    def __init__(self):
        self._api_key: Optional[str] = None
        self._model = None

    def configure(self, api_key: str):
        """
        Configura a API do Gemini com a chave fornecida.
        """
        if not api_key:
            raise ValueError("A chave da API do Gemini não pode ser vazia.")
        self._api_key = api_key
        genai.configure(api_key=self._api_key)
        self._model = genai.GenerativeModel('gemini-pro')
        print("API do Gemini configurada com sucesso.")

    def generate_text(self, prompt: str) -> Optional[str]:
        """
        Gera conteúdo textual usando o modelo Gemini.
        """
        if not self._model:
            print("Erro: Provedor Gemini não configurado. Chame 'configure()' primeiro.")
            return None
        
        try:
            response = self._model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Erro ao gerar conteúdo com o provedor Gemini: {e}")
            return None

# Exemplo de uso (apenas para teste)
if __name__ == '__main__':
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Por favor, defina a variável de ambiente GEMINI_API_KEY para testar.")
    else:
        gemini_provider = GeminiProvider()
        gemini_provider.configure(api_key)
        
        test_prompt = "Escreva uma breve descrição para um item de jogo chamado 'Espada Flamejante'."
        print(f"\nPrompt: {test_prompt}")
        generated_text = gemini_provider.generate_text(test_prompt)
        if generated_text:
            print(f"Resposta da IA:\n{generated_text}")
