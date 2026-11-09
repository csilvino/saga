"""
Módulo central para gerenciamento e orquestração de diferentes provedores de IA.
"""
from typing import Dict, Optional, Any
from editor.ai_providers.gemini_provider import GeminiProvider

class AICore:
    """
    Gerencia a configuração e o uso de diferentes provedores de IA.
    """
    def __init__(self):
        self.providers: Dict[str, Any] = {
            "gemini": GeminiProvider()
            # Outros provedores (DALL-E, MusicGen, etc.) seriam adicionados aqui
        }
        self.configured_providers: Dict[str, bool] = {
            "gemini": False
        }

    def configure_provider(self, provider_name: str, api_key: str):
        """
        Configura um provedor de IA específico com sua chave de API.
        """
        provider = self.providers.get(provider_name)
        if provider:
            try:
                provider.configure(api_key)
                self.configured_providers[provider_name] = True
                print(f"Provedor '{provider_name}' configurado com sucesso.")
            except ValueError as e:
                print(f"Erro ao configurar provedor '{provider_name}': {e}")
            except Exception as e:
                print(f"Erro inesperado ao configurar provedor '{provider_name}': {e}")
        else:
            print(f"Aviso: Provedor de IA '{provider_name}' não encontrado.")

    def is_provider_configured(self, provider_name: str) -> bool:
        """Verifica se um provedor específico está configurado."""
        return self.configured_providers.get(provider_name, False)

    def generate_text(self, prompt: str, provider_name: str = "gemini") -> Optional[str]:
        """
        Gera texto usando o provedor especificado.
        """
        provider = self.providers.get(provider_name)
        if not provider:
            print(f"Erro: Provedor '{provider_name}' não encontrado para geração de texto.")
            return None
        if not self.is_provider_configured(provider_name):
            print(f"Erro: Provedor '{provider_name}' não configurado para geração de texto.")
            return None
        
        # Assumimos que o provedor tem um método generate_text
        if hasattr(provider, 'generate_text'):
            return provider.generate_text(prompt)
        else:
            print(f"Erro: Provedor '{provider_name}' não suporta geração de texto.")
            return None

    # Métodos futuros para generate_image, generate_audio, etc.
    # def generate_image(self, prompt: str, provider_name: str = "dalle") -> Optional[Any]:
    #     pass

# Exemplo de uso
if __name__ == '__main__':
    ai_core = AICore()
    
    # Simula a configuração da chave Gemini
    gemini_key = os.getenv("GEMINI_API_KEY") # Chave real viria de um local seguro
    if gemini_key:
        ai_core.configure_provider("gemini", gemini_key)
        
        if ai_core.is_provider_configured("gemini"):
            test_prompt = "Crie uma frase de abertura para um jogo de aventura."
            generated_text = ai_core.generate_text(test_prompt)
            if generated_text:
                print(f"\nResposta do AI Core (Gemini):\n{generated_text}")
        else:
            print("\nGemini não configurado, pulando teste de geração de texto.")
    else:
        print("\nVariável de ambiente GEMINI_API_KEY não definida. Não é possível testar o AI Core com Gemini.")
