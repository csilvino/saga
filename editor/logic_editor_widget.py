"""
Widget para edição de lógica visual (Logic Weaver) no Editor da Saga Engine.
"""
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem, QGraphicsLineItem, QWidget, QVBoxLayout, QMessageBox
from PySide6.QtGui import QColor, QPen, QBrush, QFont, QPainter # Import QPainter
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from typing import Optional, List, Dict, Any

# Importa os modelos de dados do runtime
from runtime.data_models import Project
from runtime.logic_models import LogicGraph, LogicNode, EventNode, ActionNode, ConditionNode, LogicConnection

# --- Classes para os itens gráficos dos nós de lógica ---

class LogicNodeItem(QGraphicsRectItem):
    """
    Item gráfico base que representa um nó de lógica.
    """
    def __init__(self, node_data: LogicNode, parent=None):
        super().__init__(0, 0, 200, 100, parent) # Tamanho inicial do nó
        self.node_data = node_data
        self.setFlags(QGraphicsRectItem.ItemIsMovable | QGraphicsRectItem.ItemIsSelectable | QGraphicsRectItem.ItemSendsGeometryChanges)
        self.setBrush(QBrush(QColor(70, 70, 70))) # Cor de fundo padrão
        self.setPen(QPen(QColor(120, 120, 120), 2))

        # Texto do nó
        self.text_item = QGraphicsTextItem(self._get_node_display_text(), self)
        self.text_item.setDefaultTextColor(Qt.white)
        self.text_item.setTextWidth(self.rect().width() - 10) # Ajusta largura do texto
        self.text_item.setPos(5, 5) # Margem interna

        # Armazena o ID do nó para fácil acesso
        self.setData(0, node_data.id)
        self.setData(1, "logic_node")

        # Define a posição inicial se já estiver no modelo
        if node_data.position:
            self.setPos(node_data.position[0], node_data.position[1])

    def _get_node_display_text(self) -> str:
        """Retorna o texto a ser exibido no nó."""
        if isinstance(self.node_data, EventNode):
            return f"EVENTO: {self.node_data.event_type}\nID: {self.node_data.target_id or 'Nenhum'}"
        elif isinstance(self.node_data, ActionNode):
            return f"AÇÃO: {self.node_data.action_type}\nParams: {self.node_data.action_params}"
        elif isinstance(self.node_data, ConditionNode):
            return f"CONDIÇÃO: {self.node_data.condition_type}\nParams: {self.node_data.condition_params}"
        return f"NÓ: {self.node_data.id} ({self.node_data.type})"

    def itemChange(self, change, value):
        """
        Captura mudanças nos itens gráficos (ex: movimentação).
        """
        if change == QGraphicsRectItem.ItemPositionChange:
            # Atualiza a posição do nó no modelo de dados
            self.node_data.position = (int(value.x()), int(value.y()))
            # print(f"Nó '{self.node_data.id}' movido para: {self.node_data.position}")
        return super().itemChange(change, value)


# --- Widget Principal do Editor de Lógica Visual ---

class LogicEditorWidget(QGraphicsView):
    logic_node_selected = Signal(LogicNode) # Sinal emitido quando um nó de lógica é selecionado
    logic_graph_changed = Signal() # Sinal emitido quando o grafo é modificado e precisa ser salvo

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.project: Optional[Project] = None
        self.current_logic_graph: Optional[LogicGraph] = None
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.setRenderHint(QPainter.Antialiasing) # Use QPainter.Antialiasing
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)

        self.scene.selectionChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self):
        """Chamado quando a seleção de itens na cena muda."""
        selected_items = self.scene.selectedItems()
        if selected_items and isinstance(selected_items[0], LogicNodeItem):
            self.logic_node_selected.emit(selected_items[0].node_data)
        else:
            self.logic_node_selected.emit(None) # Nenhum nó de lógica selecionado

    def set_project(self, project: Project):
        """Define o projeto atual para o editor de lógica."""
        self.project = project
        self.scene.clear()
        self.current_logic_graph = None
        self.scene.setSceneRect(QRectF(0, 0, 3000, 2000)) # Área de trabalho grande para o grafo

    def load_logic_graph(self, graph_id: str):
        """
        Carrega e exibe um grafo de lógica específico do projeto.
        """
        if not self.project:
            print("No project loaded.")
            return

        # Assumimos que os grafos de lógica são armazenados em project.scripts por enquanto
        # Futuramente, teremos um campo dedicado para logic_graphs no Project
        # Por agora, vamos criar um grafo de exemplo se não existir
        if graph_id not in self.project.scripts: # Usando scripts como placeholder
            print(f"Logic Graph '{graph_id}' not found. Creating a dummy one.")
            # Cria um grafo de lógica de exemplo
            dummy_graph = LogicGraph(id=graph_id, name=f"Logic Graph {graph_id}")
            dummy_graph.nodes["start"] = EventNode(id="start", type="event", event_type="on_scene_load", position=(50, 50))
            dummy_graph.nodes["action1"] = ActionNode(id="action1", type="action", action_type="say", action_params={"character_id": "hero", "text": "Olá do Logic Weaver!"}, position=(300, 50))
            dummy_graph.connections.append(LogicConnection(source_node_id="start", target_node_id="action1"))
            self.project.scripts[graph_id] = dummy_graph # Armazena no projeto (temporário)

        # Carrega o grafo (se já existir ou o dummy que acabamos de criar)
        # Para fins de demonstração, vamos apenas usar o dummy_graph
        # Em uma implementação real, carregaríamos de um formato serializado
        self.current_logic_graph = self.project.scripts.get(graph_id) # Isso precisará ser ajustado

        if not self.current_logic_graph:
            print(f"Erro: Logic Graph '{graph_id}' não pôde ser carregado.")
            return

        self.scene.clear() # Limpa a cena anterior

        # Cria os itens gráficos para cada nó
        node_items: Dict[str, LogicNodeItem] = {}
        for node_id, node_data in self.current_logic_graph.nodes.items():
            node_item = LogicNodeItem(node_data)
            self.scene.addItem(node_item)
            node_items[node_id] = node_item

        # Desenha as conexões entre os nós
        for connection in self.current_logic_graph.connections:
            source_item = node_items.get(connection.source_node_id)
            target_item = node_items.get(connection.target_node_id)
            if source_item and target_item:
                line = QGraphicsLineItem(source_item.pos().x() + source_item.rect().width(),
                                         source_item.pos().y() + source_item.rect().height()/2,
                                         target_item.pos().x(),
                                         target_item.pos().y() + target_item.rect().height()/2)
                line.setPen(QPen(Qt.darkCyan, 2))
                self.scene.addItem(line)
        
        self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio) # Ajusta a cena na visualização

    def save_logic_graph_to_project(self):
        """
        Salva o estado atual do grafo de lógica de volta para o modelo do projeto.
        """
        if not self.current_logic_graph or not self.project:
            print("Nenhum grafo de lógica ou projeto carregado para salvar.")
            return

        # Atualiza as posições dos nós no modelo de dados
        for item in self.scene.items():
            if isinstance(item, LogicNodeItem):
                item.node_data.position = (int(item.pos().x()), int(item.pos().y()))
        
        # Atualiza o grafo de lógica no projeto principal
        # Isso precisará ser ajustado quando tivermos um campo dedicado para logic_graphs
        # Por enquanto, apenas imprimimos que foi salvo
        print(f"Logic Graph '{self.current_logic_graph.id}' salvo no modelo do projeto.")
        self.logic_graph_changed.emit() # Sinaliza que o projeto precisa ser salvo

    def generate_sagascript(self) -> str:
        """
        Gera SagaScript a partir do grafo de lógica visual.
        """
        if not self.current_logic_graph:
            QMessageBox.warning(self, "Gerar SagaScript", "Nenhum grafo de lógica carregado.")
            return ""

        sagascript_lines: List[str] = []
        
        # Implementação simplificada: apenas lista as ações em sequência
        # Uma implementação real precisaria de um algoritmo de travessia do grafo
        # e tratamento de condições/eventos.
        
        sagascript_lines.append(f"# SagaScript gerado para o grafo: {self.current_logic_graph.name}")
        sagascript_lines.append("")

        # Ordena os nós por posição Y para uma ordem mais lógica
        sorted_nodes = sorted(self.current_logic_graph.nodes.values(), key=lambda node: node.position[1])

        for node in sorted_nodes:
            if isinstance(node, ActionNode):
                params_str = " ".join([f'"{v}"' if isinstance(v, str) and " " in v else str(v) for v in node.action_params.values()])
                sagascript_lines.append(f"{node.action_type} {params_str}")
            elif isinstance(node, EventNode):
                sagascript_lines.append(f"# Evento: {node.event_type} (ID: {node.target_id})")
            elif isinstance(node, ConditionNode):
                sagascript_lines.append(f"# Condição: {node.condition_type} (Params: {node.condition_params})")
                sagascript_lines.append(f"#   -> Se Verdadeiro: {node.on_true}")
                sagascript_lines.append(f"#   -> Se Falso: {node.on_false}")
            sagascript_lines.append("") # Linha em branco para legibilidade

        return "\n".join(sagascript_lines)

    def wheelEvent(self, event):
        """
        Implementa zoom com a roda do mouse.
        """
        zoom_factor = 1.15
        if event.angleDelta().y() > 0:
            self.scale(zoom_factor, zoom_factor)
        else:
            self.scale(1 / zoom_factor, 1 / zoom_factor)
