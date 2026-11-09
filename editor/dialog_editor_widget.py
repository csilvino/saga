"""
Widget para edição de diálogos em grafo no Editor da Saga Engine.
"""
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem, QGraphicsLineItem, QWidget, QVBoxLayout, QMessageBox, QPushButton, QComboBox, QHBoxLayout, QLabel # Import QLabel
from PySide6.QtGui import QColor, QPen, QBrush, QFont, QPainter
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from typing import Optional, List, Dict, Any

# Importa os modelos de dados do runtime
from runtime.data_models import Project, Dialog, DialogNode, DialogChoice

# Importa o AICore
from editor.ai_core import AICore

# --- Classes para os itens gráficos dos nós de diálogo ---

class DialogNodeItem(QGraphicsRectItem):
    """
    Item gráfico que representa um nó de diálogo (fala ou escolha).
    """
    def __init__(self, node_data: DialogNode, parent=None):
        super().__init__(0, 0, 200, 100, parent) # Tamanho inicial do nó
        self.node_data = node_data
        self.setFlags(QGraphicsRectItem.ItemIsMovable | QGraphicsRectItem.ItemIsSelectable | QGraphicsRectItem.ItemSendsGeometryChanges)
        self.setBrush(QBrush(QColor(50, 50, 50))) # Cor de fundo do nó
        self.setPen(QPen(QColor(100, 100, 100), 2))

        # Texto do nó
        self.text_item = QGraphicsTextItem(self._get_node_display_text(), self)
        self.text_item.setDefaultTextColor(Qt.white)
        self.text_item.setTextWidth(self.rect().width() - 10) # Ajusta largura do texto
        self.text_item.setPos(5, 5) # Margem interna

        # Armazena o ID do nó para fácil acesso
        self.setData(0, node_data.id)
        self.setData(1, "dialog_node")

    def _get_node_display_text(self) -> str:
        """Retorna o texto a ser exibido no nó."""
        if self.node_data.type == "line":
            char = f"({self.node_data.character})" if self.node_data.character else ""
            return f"FALA {char}:\n{self.node_data.text or ''}"
        elif self.node_data.type == "choice":
            char = f"({self.node_data.character})" if self.node_data.character else ""
            return f"ESCOLHA {char}:\n{self.node_data.text or ''}\nOpções: {len(self.node_data.choices) if self.node_data.choices else 0}"
        return f"NÓ: {self.node_data.id}"

    def itemChange(self, change, value):
        """
        Captura mudanças nos itens gráficos (ex: movimentação).
        """
        if change == QGraphicsRectItem.ItemPositionChange:
            # Atualiza a posição do nó no modelo de dados (se necessário)
            # Por enquanto, apenas imprime
            print(f"Nó '{self.node_data.id}' movido para: ({value.x()}, {value.y()})")
        return super().itemChange(change, value)


# --- Widget Principal do Editor de Diálogo ---

class DialogEditorWidget(QGraphicsView):
    dialog_node_selected = Signal(DialogNode) # Sinal emitido quando um nó de diálogo é selecionado
    dialog_changed = Signal() # Sinal emitido quando o diálogo é modificado e precisa ser salvo

    def __init__(self, ai_core: AICore, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.project: Optional[Project] = None
        self.current_dialog: Optional[Dialog] = None
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.ai_core = ai_core # Referência ao AICore

        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)

        self.scene.selectionChanged.connect(self._on_selection_changed)

        # Controles de IA (adicionados em um layout para melhor organização)
        ai_controls_widget = QWidget(self)
        ai_controls_layout = QHBoxLayout(ai_controls_widget)
        ai_controls_layout.setContentsMargins(5, 5, 5, 5)

        ai_controls_layout.addWidget(QLabel("Tom da Fala:"))
        self.tone_selector = QComboBox()
        self.tone_selector.addItems(["Neutro", "Cômico", "Sério", "Irônico", "Triste", "Raivoso"])
        ai_controls_layout.addWidget(self.tone_selector)

        self.suggest_speech_button = QPushButton("Sugerir Fala (IA)")
        self.suggest_speech_button.clicked.connect(self._suggest_speech_with_ai)
        ai_controls_layout.addWidget(self.suggest_speech_button)
        
        ai_controls_widget.setLayout(ai_controls_layout)
        ai_controls_widget.setGeometry(10, 10, ai_controls_widget.sizeHint().width(), ai_controls_widget.sizeHint().height())
        ai_controls_widget.hide() # Esconde por padrão
        self.ai_controls_widget = ai_controls_widget


    def _on_selection_changed(self):
        """Chamado quando a seleção de itens na cena muda."""
        selected_items = self.scene.selectedItems()
        if selected_items and isinstance(selected_items[0], DialogNodeItem):
            self.dialog_node_selected.emit(selected_items[0].node_data)
            self.ai_controls_widget.show() # Mostra os controles de IA se um nó de diálogo for selecionado
        else:
            self.dialog_node_selected.emit(None) # Nenhum nó de diálogo selecionado
            self.ai_controls_widget.hide() # Esconde os controles de IA

    def set_project(self, project: Project):
        """Define o projeto atual para o editor de diálogo."""
        self.project = project
        self.scene.clear()
        self.current_dialog = None
        self.scene.setSceneRect(QRectF(0, 0, 2000, 1500)) # Área de trabalho grande para o grafo

    def load_dialog(self, dialog_id: str):
        """
        Carrega e exibe um diálogo específico do projeto.
        """
        if not self.project:
            print("No project loaded.")
            return

        dialog_data = self.project.dialogs.get(dialog_id)
        if not dialog_data:
            print(f"Dialog '{dialog_id}' not found.")
            return

        self.current_dialog = dialog_data
        self.scene.clear() # Limpa a cena anterior

        # Cria os itens gráficos para cada nó
        node_items: Dict[str, DialogNodeItem] = {}
        x_offset = 50
        y_offset = 50
        for node_id, node_data in dialog_data.nodes.items():
            node_item = DialogNodeItem(node_data)
            # Posição inicial simples para visualização
            node_item.setPos(x_offset, y_offset)
            x_offset += 250
            if x_offset > 1500: # Quebra de linha
                x_offset = 50
                y_offset += 150
            self.scene.addItem(node_item)
            node_items[node_id] = node_item

        # Desenha as conexões entre os nós
        for node_id, node_item in node_items.items():
            node_data = node_item.node_data
            if node_data.type == "line" and node_data.next:
                if node_data.next in node_items:
                    target_item = node_items[node_data.next]
                    line = QGraphicsLineItem(node_item.pos().x() + node_item.rect().width(),
                                             node_item.pos().y() + node_item.rect().height()/2,
                                             target_item.pos().x(),
                                             target_item.pos().y() + target_item.rect().height()/2)
                    line.setPen(QPen(Qt.white, 2))
                    self.scene.addItem(line)
            elif node_data.type == "choice" and node_data.choices:
                for choice in node_data.choices:
                    if choice.next and choice.next in node_items:
                        target_item = node_items[choice.next]
                        line = QGraphicsLineItem(node_item.pos().x() + node_item.rect().width(),
                                                 node_item.pos().y() + node_item.rect().height()/2,
                                                 target_item.pos().x(),
                                                 target_item.pos().y() + target_item.rect().height()/2)
                        line.setPen(QPen(Qt.yellow, 1, Qt.DotLine))
                        self.scene.addItem(line)
        
        self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio) # Ajusta a cena na visualização

    def _suggest_speech_with_ai(self):
        """
        Sugere uma fala para o nó de diálogo selecionado usando a IA, considerando o tom.
        """
        selected_items = self.scene.selectedItems()
        if not selected_items or not isinstance(selected_items[0], DialogNodeItem):
            QMessageBox.warning(self, "Sugestão de Fala", "Nenhum nó de diálogo selecionado.")
            return

        node_item = selected_items[0]
        node_data = node_item.node_data

        if node_data.type != "line":
            QMessageBox.warning(self, "Sugestão de Fala", "Apenas nós de 'fala' podem ter falas sugeridas pela IA.")
            return

        if not self.ai_core.is_provider_configured("gemini"):
            QMessageBox.warning(self, "Sugestão de Fala", "A API do Gemini não está configurada. Por favor, configure-a nas Settings.")
            return

        selected_tone = self.tone_selector.currentText()
        
        # Constrói o prompt para a IA, incluindo o tom
        prompt = (f"Gere uma variação curta para a seguinte fala de personagem em um jogo de aventura. "
                  f"Personagem: {node_data.character or 'Desconhecido'}. "
                  f"Fala atual: '{node_data.text or ''}'. "
                  f"Contexto do jogo: {self.project.name}. "
                  f"Tom do jogo: {self.project.metadata.description}. "
                  f"O tom da nova fala deve ser: '{selected_tone}'. "
                  f"Apenas a nova fala, sem introdução.")
        
        QMessageBox.information(self, "Sugestão de Fala", "Gerando sugestão de fala com IA... Isso pode levar alguns segundos.")
        
        generated_text = self.ai_core.generate_text(prompt)

        if generated_text:
            response = QMessageBox.question(self, "Sugestão de Fala da IA", 
                                            f"Sugestão:\n\n'{generated_text}'\n\nDeseja usar esta fala?",
                                            QMessageBox.Yes | QMessageBox.No)
            if response == QMessageBox.Yes:
                node_data.text = generated_text
                node_item.text_item.setPlainText(node_item._get_node_display_text()) # Atualiza o texto no item gráfico
                self.dialog_changed.emit() # Sinaliza que o diálogo foi modificado
                QMessageBox.information(self, "Sugestão de Fala", "Fala atualizada com a sugestão da IA.")
        else:
            QMessageBox.warning(self, "Sugestão de Fala", "Não foi possível gerar uma sugestão de fala. Verifique sua conexão ou a configuração da API.")


    def save_dialog_to_project(self):
        """
        Salva o estado atual do diálogo de volta para o modelo do projeto.
        """
        if not self.current_dialog or not self.project:
            print("Nenhum diálogo ou projeto carregado para salvar.")
            return

        updated_nodes: Dict[str, DialogNode] = {}
        for item in self.scene.items():
            if isinstance(item, DialogNodeItem):
                node_id = item.node_data.id
                # Atualiza a posição do nó no modelo de dados
                # item.node_data.position = {"x": int(item.pos().x()), "y": int(item.pos().y())}
                # Para salvar a posição, precisamos adicionar um campo 'position' ao DialogNode
                # Por enquanto, apenas atualizamos o nó existente
                updated_nodes[node_id] = item.node_data
        
        # Atualiza o dicionário de nós do diálogo atual
        self.current_dialog.nodes = updated_nodes
        
        # Atualiza o diálogo no projeto principal
        self.project.dialogs[self.current_dialog.start_node] = self.current_dialog # Assumindo que start_node é o ID do diálogo
        
        print(f"Diálogo '{self.current_dialog.start_node}' salvo no modelo do projeto.")
        self.dialog_changed.emit() # Sinaliza que o projeto precisa ser salvo

    def wheelEvent(self, event):
        """
        Implementa zoom com a roda do mouse.
        """
        zoom_factor = 1.15
        if event.angleDelta().y() > 0:
            self.scale(zoom_factor, zoom_factor)
        else:
            self.scale(1 / zoom_factor, 1 / zoom_factor)

    def itemChange(self, change, value):
        if change == QGraphicsRectItem.ItemPositionChange:
            item = self.sender()
            if isinstance(item, DialogNodeItem) and self.current_dialog:
                node_id = item.data(0)
                if node_id:
                    for node_id, node in self.current_dialog.nodes.items():
                        if node.id == item.node_data.id:
                            print(f"Node {node.id} moved to {value}")
                            break
        return super().itemChange(change, value)
