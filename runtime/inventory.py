"""
Módulo de Inventário para a Saga Engine.
"""
from __future__ import annotations
import arcade
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class Item:
    """
    Representa um item no inventário.
    """
    id: str
    name: str
    description: str
    texture: arcade.Texture = field(repr=False, compare=False)

class Inventory:
    """
    Gerencia o inventário do jogador.
    """
    def __init__(self):
        self.items: Dict[str, Item] = {}

    def add_item(self, item: Item):
        """
        Adiciona um item ao inventário.
        """
        if item.id in self.items:
            print(f"Aviso: Item '{item.id}' já existe no inventário.")
            return
        self.items[item.id] = item
        print(f"Item '{item.name}' adicionado ao inventário.")

    def remove_item(self, item_id: str):
        """
        Remove um item do inventário.
        """
        if item_id in self.items:
            removed_item = self.items.pop(item_id)
            print(f"Item '{removed_item.name}' removido do inventário.")
        else:
            print(f"Aviso: Tentativa de remover item inexistente '{item_id}'.")

    def has_item(self, item_id: str) -> bool:
        """
        Verifica se um item está no inventário.
        """
        return item_id in self.items

    def get_item(self, item_id: str) -> Optional[Item]:
        """
        Retorna um item do inventário, se existir.
        """
        return self.items.get(item_id)

    def get_all_items(self) -> List[Item]:
        """
        Retorna uma lista de todos os itens no inventário.
        """
        return list(self.items.values())

if __name__ == '__main__':
    # Exemplo de uso
    inv = Inventory()
    # A textura seria carregada de um arquivo na implementação real
    fake_texture = arcade.Texture.create_empty("fake", (64, 64))
    
    key = Item(id="key_01", name="Chave Dourada", description="Uma chave antiga e ornamentada.", texture=fake_texture)
    
    inv.add_item(key)
    print(f"Tem a chave? {inv.has_item('key_01')}")
    inv.remove_item('key_01')
    print(f"Tem a chave? {inv.has_item('key_01')}")
