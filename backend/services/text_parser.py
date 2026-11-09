import logging
import re
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

class TextParser:
    def __init__(self):
        # Dicionário de Verbos (Sinônimo -> Ação Canônica)
        self.verbs = {
            # Movimento
            "IR": "GO", "ANDAR": "GO", "CAMINHAR": "GO", "CORRER": "GO", "ENTRAR": "ENTER", "GO": "GO", "WALK": "GO",
            "SUBIR": "MOVE_UP", "DESCER": "MOVE_DOWN", "SAIR": "EXIT", "VOLTAR": "GO_BACK",
            "NORTE": "GO_N", "SUL": "GO_S", "LESTE": "GO_E", "OESTE": "GO_W", "CIMA": "GO_U", "BAIXO": "GO_D",
            "N": "GO_N", "S": "GO_S", "L": "GO_E", "O": "GO_W", "E": "GO_E", "W": "GO_W", "U": "GO_U", "D": "GO_D",
            
            # Manipulação
            "PEGAR": "PICKUP", "APANHAR": "PICKUP", "COLHER": "PICKUP", "GET": "PICKUP", "TAKE": "PICKUP",
            "SOLTAR": "DROP", "LARGAR": "DROP", "DEIXAR": "DROP", "DROP": "DROP",
            "ABRIR": "OPEN", "DESTRLANCAR": "OPEN", "OPEN": "OPEN",
            "FECHAR": "CLOSE", "TRANCAR": "CLOSE", "CLOSE": "CLOSE", "SHUT": "CLOSE",
            "EMPURRAR": "PUSH", "MOVER": "PUSH", "PUSH": "PUSH", "MOVE": "PUSH",
            "PUXAR": "PULL", "PULL": "PULL",
            "USAR": "USE", "UTILIZAR": "USE", "USE": "USE",
            "ACENDER": "ON", "LIGAR": "ON", "LIGHT": "ON", "TURNON": "ON",
            "APAGAR": "OFF", "DESLIGAR": "OFF", "EXTINGUISH": "OFF", "TURNOFF": "OFF",
            "SENTAR": "SIT", "SIT": "SIT",
            
            # Observação
            "OLHAR": "LOOK", "EXAMINAR": "LOOK", "VER": "LOOK", "LER": "LOOK", "LOOK": "LOOK", "EXAMINE": "LOOK", "X": "LOOK",
            "INVENTARIO": "INVENTORY", "INV": "INVENTORY", "I": "INVENTORY", "ITENS": "INVENTORY",
            
            # Interação
            "FALAR": "TALK", "CONVERSAR": "TALK", "TALK": "TALK", "SPEAK": "TALK",
            "DAR": "GIVE", "ENTREGAR": "GIVE", "OFERECER": "GIVE", "GIVE": "GIVE",
            
            # Atalhos Calixto
            "N": "GO_N", "S": "GO_S", "L": "GO_E", "O": "GO_W",
            "NORTE": "GO_N", "SUL": "GO_S", "LESTE": "GO_E", "OESTE": "GO_W",
            "NORTH": "GO_N", "SOUTH": "GO_S", "EAST": "GO_E", "WEST": "GO_W"
        }

        # Palavras para ignorar (Stopwords)
        self.stopwords = {
            "O", "A", "OS", "AS", "UM", "UMA", "UNS", "UMAS", 
            "NO", "NA", "NOS", "NAS", "DO", "DA", "DOS", "DAS", 
            "DE", "EM", "COM", "PARA", "POR", "THE", "A", "AN", "IN", "ON", "AT", "TO", "WITH"
        }

    def normalize_input(self, text: str) -> List[str]:
        """
        Limpa o texto, remove pontuação e stopwords, retorna lista de tokens.
        """
        # Remove pontuação e converte para maiúsculas
        clean_text = re.sub(r'[^\w\s]', '', text).upper()
        tokens = clean_text.split()
        
        # Remove stopwords
        filtered_tokens = [t for t in tokens if t not in self.stopwords]
        return filtered_tokens

    def parse_command(self, text: str, context_objects: List[Dict]) -> Dict[str, Any]:
        """
        Processa o comando de texto e retorna a intenção estruturada.
        
        Args:
            text: O comando digitado pelo usuário (ex: "Abrir a porta")
            context_objects: Lista de objetos presentes na cena e no inventário para validação.
                             Cada dict deve ter {'name': 'Porta', 'id': '...'}
        
        Returns:
            Dict com:
            - action: O verbo canônico (ex: OPEN)
            - target: O ID do objeto alvo (se encontrado) ou o nome (se não)
            - message: Mensagem de feedback (ex: "Não vejo nenhuma porta aqui.")
        """
        tokens = self.normalize_input(text)
        
        if not tokens:
            return {"action": "NONE", "message": "Eu não entendi."}

        # 1. Identificar o Verbo
        verb_token = tokens[0]
        # Tenta match exato ou regra das 4 letras
        action = self.verbs.get(verb_token)
        if not action:
            # Tenta regra das 4 letras se a palavra for longa
            if len(verb_token) >= 4:
                short_verb = verb_token[:4]
                # Procura no dicionário chaves que comecem com essas 4 letras
                for key, val in self.verbs.items():
                    if key.startswith(short_verb):
                        action = val
                        break
        
        if not action:
            return {"action": "UNKNOWN", "message": f"Eu não sei como '{verb_token}'."}

        # Comandos sem alvo (ex: OLHAR, INVENTARIO, NORTE)
        if len(tokens) == 1:
            return {"action": action, "target": None, "message": None}

        # 2. Identificar o Objeto Alvo (Substantivo)
        # O resto da frase é considerado o nome do objeto (ex: "LANTERNA DE OLEO")
        target_name_tokens = tokens[1:]
        target_name_str = " ".join(target_name_tokens)
        
        found_object = None
        
        # Busca exata ou parcial nos objetos do contexto
        for obj in context_objects:
            obj_name = obj.get("name", "").upper()
            # Verifica se o nome do objeto contém as palavras digitadas
            # Ex: Objeto "Lanterna Velha", usuário digita "Lanterna" -> Match
            if target_name_str in obj_name:
                found_object = obj
                break
            # Regra das 4 letras para objetos também? Pode ser útil.
        
        if found_object:
            return {
                "action": action,
                "target_id": found_object.get("id"),
                "target_name": found_object.get("name"),
                "message": f"Comando aceito: {action} {found_object.get('name')}"
            }
        else:
            return {
                "action": action,
                "target_id": None,
                "target_name": target_name_str,
                "message": f"Eu não vejo '{target_name_str}' aqui."
            }

# Singleton
text_parser = TextParser()
