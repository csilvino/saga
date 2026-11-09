"""
Módulo para gerenciar as configurações do Editor da Saga Engine.
Inclui o gerenciamento seguro de chaves de API.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional

# Caminho para o arquivo de configurações do usuário
SETTINGS_FILE = Path.home() / ".saga_engine" / "editor_settings.json"

class SettingsManager:
    """
    Gerencia as configurações do editor, incluindo chaves de API.
    As configurações são salvas em um arquivo JSON no diretório do usuário.
    """
    def __init__(self):
        self._settings: Dict[str, Any] = {}
        self._load_settings()

    def _load_settings(self):
        """
        Carrega as configurações do arquivo JSON.
        """
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    self._settings = json.load(f)
                print(f"Configurações carregadas de: {SETTINGS_FILE}")
            except json.JSONDecodeError as e:
                print(f"Erro ao decodificar o arquivo de configurações: {e}. Usando configurações padrão.")
                self._settings = {}
            except Exception as e:
                print(f"Erro ao carregar configurações: {e}. Usando configurações padrão.")
                self._settings = {}
        else:
            print("Arquivo de configurações não encontrado. Usando configurações padrão.")

    def _save_settings(self):
        """
        Salva as configurações no arquivo JSON.
        """
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2)
            print(f"Configurações salvas em: {SETTINGS_FILE}")
        except Exception as e:
            print(f"Erro ao salvar configurações: {e}")

    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Retorna o valor de uma configuração.
        """
        return self._settings.get(key, default)

    def set_setting(self, key: str, value: Any):
        """
        Define o valor de uma configuração e salva.
        """
        self._settings[key] = value
        self._save_settings()

    def get_api_key(self, provider_name: str) -> Optional[str]:
        """
        Retorna a chave da API para um provedor específico.
        """
        return self.get_setting(f"api_keys.{provider_name}")

    def set_api_key(self, provider_name: str, api_key: str):
        """
        Define a chave da API para um provedor específico e salva.
        """
        api_keys = self.get_setting("api_keys", {})
        api_keys[provider_name] = api_key
        self.set_setting("api_keys", api_keys)

# Exemplo de uso
if __name__ == '__main__':
    sm = SettingsManager()
    
    # Teste de API Key
    print(f"Chave Gemini (antes): {sm.get_api_key('gemini')}")
    sm.set_api_key("gemini", "sua_chave_secreta_gemini_123")
    print(f"Chave Gemini (depois): {sm.get_api_key('gemini')}")
    
    # Teste de outra configuração
    print(f"Tema (antes): {sm.get_setting('editor.theme', 'dark')}")
    sm.set_setting("editor.theme", "light")
    print(f"Tema (depois): {sm.get_setting('editor.theme')}")
    
    # Limpa a chave para não persistir no teste
    api_keys = sm.get_setting("api_keys", {})
    if "gemini" in api_keys:
        del api_keys["gemini"]
    sm.set_setting("api_keys", api_keys)
    print(f"Chave Gemini (limpa): {sm.get_api_key('gemini')}")
