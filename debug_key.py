from backend.config.user_settings import get_gemini_key
import os

print(f"Tentando ler a chave...")
key = get_gemini_key()
print(f"Chave lida: '{key}'")

if key:
    print("SUCESSO: Chave encontrada.")
else:
    print("FALHA: Chave não encontrada ou vazia.")
