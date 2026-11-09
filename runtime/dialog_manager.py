"""
Módulo de Diálogo para a Saga Engine.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from runtime.data_models import Dialog, DialogNode

class DialogManager:
    """
    Gerencia o estado e o fluxo de um diálogo.
    """
    def __init__(self):
        self.active_dialog: Optional[Dialog] = None
        self.current_node: Optional[DialogNode] = None
        self.is_active = False

    def start_dialog(self, dialog: Dialog):
        """
        Inicia um novo diálogo.
        """
        self.active_dialog = dialog
        self.current_node = self.active_dialog.nodes.get(self.active_dialog.start_node)
        self.is_active = True
        print(f"Diálogo iniciado. Nó atual: {self.current_node.id if self.current_node else 'Nenhum'}")

    def advance_dialog(self, choice_index: Optional[int] = None):
        """
        Avança o diálogo para o próximo nó.
        """
        if not self.is_active or not self.current_node:
            return

        next_node_id = None
        if self.current_node.type == "line":
            next_node_id = self.current_node.next
        elif self.current_node.type == "choice" and choice_index is not None:
            if self.current_node.choices and 0 <= choice_index < len(self.current_node.choices):
                next_node_id = self.current_node.choices[choice_index].next

        if next_node_id:
            self.current_node = self.active_dialog.nodes.get(next_node_id)
            print(f"Avançando para o nó: {self.current_node.id if self.current_node else 'Fim do diálogo'}")
        else:
            self.end_dialog()

    def end_dialog(self):
        """
        Encerra o diálogo atual.
        """
        self.is_active = False
        self.current_node = None
        self.active_dialog = None
        print("Diálogo encerrado.")

if __name__ == '__main__':
    # Exemplo de uso
    from runtime.data_models import Dialog, DialogNode, DialogChoice

    # Cria um diálogo de exemplo
    dialog_data = Dialog(
        start_node="node_1",
        nodes={
            "node_1": DialogNode(id="node_1", type="line", text="Olá!", next="node_2"),
            "node_2": DialogNode(
                id="node_2",
                type="choice",
                choices=[
                    DialogChoice(text="Como vai?", next="node_3"),
                    DialogChoice(text="Adeus.", next="node_4"),
                ],
            ),
            "node_3": DialogNode(id="node_3", type="line", text="Estou bem, obrigado!", next=None),
            "node_4": DialogNode(id="node_4", type="line", text="Até mais!", next=None),
        },
    )

    dialog_manager = DialogManager()
    dialog_manager.start_dialog(dialog_data)
    
    # Simula a escolha do jogador
    if dialog_manager.current_node and dialog_manager.current_node.type == "choice":
        print("Escolhas:", [choice.text for choice in dialog_manager.current_node.choices])
        dialog_manager.advance_dialog(0) # Escolhe a primeira opção
    
    dialog_manager.advance_dialog() # Avança após a linha de texto
    dialog_manager.advance_dialog() # Tenta avançar novamente (deve encerrar)
