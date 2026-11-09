"""
Modelos de dados (dataclasses) para o Logic Weaver da Saga Engine.

Estas classes representam a estrutura de um grafo de lógica visual,
incluindo nós de eventos, ações e condições.
"""
from dataclasses import dataclass, field, asdict # Import asdict
from typing import List, Dict, Any, Optional, Tuple

@dataclass(kw_only=True) # Adicionado kw_only=True para lidar com herança de dataclasses
class LogicNode:
    """Base para todos os nós do Logic Weaver."""
    id: str
    type: str
    position: Tuple[int, int] = field(default=(0, 0)) # Posição no editor visual
    
    # Propriedades genéricas para serem usadas por subtipos de nós
    properties: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EventNode(LogicNode):
    """Nó que representa um evento (gatilho)."""
    event_type: str # Ex: "on_hotspot_click", "on_scene_load"
    target_id: Optional[str] = None # Ex: hotspot_id, scene_id

@dataclass
class ActionNode(LogicNode):
    """Nó que representa uma ação a ser executada."""
    action_type: str # Ex: "set_variable", "play_sound", "run_script"
    action_params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ConditionNode(LogicNode):
    """Nó que representa uma condição a ser verificada."""
    condition_type: str # Ex: "has_item", "variable_equals"
    condition_params: Dict[str, Any] = field(default_factory=dict)
    
    # IDs dos nós para onde ir se a condição for verdadeira ou falsa
    on_true: Optional[str] = None
    on_false: Optional[str] = None

@dataclass
class LogicConnection:
    """Representa uma conexão entre dois nós."""
    source_node_id: str
    target_node_id: str
    # Pode ter um "port" de origem/destino se os nós tiverem múltiplos pontos de conexão
    source_port: Optional[str] = None
    target_port: Optional[str] = None

@dataclass
class LogicGraph:
    """Representa um grafo completo de lógica visual."""
    id: str
    name: str
    nodes: Dict[str, LogicNode] = field(default_factory=dict)
    connections: List[LogicConnection] = field(default_factory=list)
    start_node_id: Optional[str] = None # O nó inicial do grafo

    def to_dict(self):
        """Converte o grafo de lógica para um dicionário serializável."""
        nodes_dict = {}
        for node_id, node in self.nodes.items():
            node_data = asdict(node)
            # Remove o campo 'type' da base LogicNode se for um subtipo
            if isinstance(node, EventNode):
                node_data['type'] = 'event'
            elif isinstance(node, ActionNode):
                node_data['type'] = 'action'
            elif isinstance(node, ConditionNode):
                node_data['type'] = 'condition'
            nodes_dict[node_id] = node_data
        
        connections_list = [asdict(conn) for conn in self.connections]

        return {
            "id": self.id,
            "name": self.name,
            "start_node_id": self.start_node_id,
            "nodes": nodes_dict,
            "connections": connections_list
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogicGraph':
        """Cria uma instância de LogicGraph a partir de um dicionário."""
        nodes = {}
        for node_id, node_data in data.get('nodes', {}).items():
            node_type = node_data.pop('type') # Remove 'type' para evitar conflito com dataclass
            
            # Garante que os argumentos são passados como keyword arguments
            common_args = {
                'id': node_data.pop('id'),
                'type': node_type,
                'position': node_data.pop('position', (0, 0)),
                'properties': node_data.pop('properties', {})
            }

            if node_type == 'event':
                nodes[node_id] = EventNode(**common_args, **node_data)
            elif node_type == 'action':
                nodes[node_id] = ActionNode(**common_args, **node_data)
            elif node_type == 'condition':
                nodes[node_id] = ConditionNode(**common_args, **node_data)
            else:
                nodes[node_id] = LogicNode(**common_args, **node_data) # Fallback para tipo genérico

        connections = [LogicConnection(**conn_data) for conn_data in data.get('connections', [])]

        return cls(
            id=data['id'],
            name=data['name'],
            start_node_id=data.get('start_node_id'),
            nodes=nodes,
            connections=connections
        )
