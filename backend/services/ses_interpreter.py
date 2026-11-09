import re
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class SESInterpreter:
    """
    Interpretador para a linguagem SES (Saga Engine Script).
    Foca na execução de blocos 'on trigger { ... }'.
    """

    def __init__(self):
        # Mapeamento de comandos SES para ações internas
        self.commands = {
            "narrate": "NARRATE",
            "goToScene": "NAVIGATE",
            "navigate": "NAVIGATE",
            "add_to_inventory": "PICKUP",
            "take": "PICKUP",
            "destroy": "DESTROY",
            "set_state": "SET_STATE",
            "playSound": "PLAY_SOUND",
        }

    def execute_block(self, script: str, trigger_type: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Busca e executa blocos correspondentes ao tipo de trigger.
        Aliases:
        - examine: 'examine', 'look', 'look at'
        - interact: 'interact', 'click', 'use', 'pickup', 'take'
        """
        if not script:
            return []

        # Mapeia trigger_type para possíveis nomes de blocos no SES
        trigger_map = {
            "examine": ["examine", "look", "look at"],
            "interact": ["interact", "click", "use", "pickup", "take", "on", "subir", "descer", "entrar", "sair", "sentar"]
        }
        
        possible_triggers = trigger_map.get(trigger_type, [trigger_type])
        
        # Procura por qualquer um dos gatilhos possíveis
        for trigger in possible_triggers:
            block_pattern = rf"on\s+{trigger}\s*\{{(.*?)\}}"
            match = re.search(block_pattern, script, re.DOTALL | re.IGNORECASE)
            if match:
                block_content = match.group(1)
                return self._parse_lines(block_content, context)

        # Fallback por compatibilidade se não houver blocos estruturados
        if trigger_type == "examine" and "on " not in script:
            return self._parse_lines(script, context)

        return []

    def _parse_lines(self, block_content: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Processa as linhas de um bloco de código.
        """
        effects = []
        # Limpa o conteúdo e divide em instruções (terminadas por ; ou \n)
        instructions = re.split(r'[;\n]', block_content)
        instructions = [i.strip() for i in instructions if i.strip()]
        
        game_state = context.get("game_state", {})
        
        i = 0
        while i < len(instructions):
            instr = instructions[i]
            
            # 1. Detectar IF básico
            # Ex: if get_state('key') { ... }
            if instr.startswith("if"):
                # Procura a condição entre parênteses
                cond_match = re.search(r"if\s*\((.*?)\)\s*\{", instr)
                if cond_match:
                    condition = cond_match.group(1).strip()
                    
                    # Avalia a condição (simplificado)
                    res = self._evaluate_condition(condition, context)
                    
                    # Se verdadeiro, executa o conteúdo do bloco
                    # Se falso, pula até encontrar o correspondente }
                    if res:
                        # Para fins de simplificação v1, vamos processar o que estiver entre { e }
                        # Se estiver na mesma linha: if (..) { narrate(..) }
                        inner_match = re.search(r"\{(.*?)\}", instr)
                        if inner_match:
                            effects.extend(self._parse_lines(inner_match.group(1), context))
                        else:
                            # Se o bloco continuar em outras linhas (mais complexo)
                            pass
                    else:
                        # Pula (TODO: lógica de rular bloco multi-linha)
                        pass
                i += 1
                continue

            # 2. Detectar comandos simples: cmd(arg)
            cmd_match = re.match(r"(\w+)\s*\((.*?)\)", instr)
            if cmd_match:
                cmd_name = cmd_match.group(1)
                cmd_args_raw = cmd_match.group(2)
                
                # Executa get_state se estiver dentro de outro comando? 
                # Não, vamos manter simples: args são literais ou variáveis
                
                # Limpa argumentos (remove aspas)
                args = [arg.strip().strip("'").strip('"') for arg in cmd_args_raw.split(',')]
                
                action = self.commands.get(cmd_name)
                if action:
                    effect = self._generate_effect(action, args, context)
                    if effect:
                        effects.append(effect)
            
            i += 1

        return effects

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """
        Avalia uma condição SES simples.
        Suporta:
        - get_state('key')
        - get_state('key') == 'value'
        - !get_state('key')
        """
        game_state = context.get("game_state", {})
        
        # get_state('key')
        gs_match = re.search(r"get_state\(['\"](.+?)['\"]\)", condition)
        if gs_match:
            key = gs_match.group(1)
            val = game_state.get(key)
            
            # if get_state('k') == 'v'
            if "==" in condition:
                parts = condition.split("==")
                right = parts[1].strip().strip("'").strip('"')
                return str(val).lower() == right.lower()
                
            # if !get_state('k')
            if condition.strip().startswith("!"):
                return not val
                
            return bool(val)
            
        # has_item('id')
        hi_match = re.search(r"has_item\(['\"](.+?)['\"]\)", condition)
        if hi_match:
            item_id = hi_match.group(1)
            inventory = context.get("inventory", [])
            return any(item.get("id") == item_id for item in inventory)
            
        return True # Default true if unknown condition

    def _generate_effect(self, action: str, args: List[str], context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Transforma um comando parseado em um efeito colateral estruturado.
        """
        if action == "NARRATE":
            return {"type": "MESSAGE", "content": args[0]}
        
        if action == "NAVIGATE":
            return {"type": "NAVIGATE", "target_id": args[0]}
        
        if action == "PICKUP":
            target_id = args[0]
            if target_id in ["self", "self.id"]:
                target_id = context.get("target_id")
            return {"type": "PICKUP", "target_id": target_id}
            
        if action == "DESTROY":
            target_id = args[0]
            if target_id in ["self", "self.id"]:
                target_id = context.get("target_id")
            return {"type": "DESTROY", "target_id": target_id}
            
        if action == "SET_STATE":
            if len(args) >= 2:
                # Normaliza booleanos de texto para booleano real se necessário
                val = args[1]
                if val.lower() == "true": val = True
                elif val.lower() == "false": val = False
                
                return {"type": "STATE_CHANGE", "key": args[0], "value": val, "target_id": context.get("target_id")}
                
        if action == "PLAY_SOUND":
            return {"type": "AUDIO", "file": args[0]}

        return None

# Singleton
ses_runtime = SESInterpreter()
