"""
Widget para edição e visualização de cenas no Editor da Saga Engine.
"""
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem, QWidget, QVBoxLayout, QGraphicsPolygonItem, QGraphicsItem
from PySide6.QtGui import QPixmap, QImage, QColor, QPen, QPolygonF, QPainter # Import QPainter
from PySide6.QtCore import Qt, QSize, QRectF, QPointF, Signal
from PIL import Image
from pathlib import Path
from typing import Optional, List

# Importa os modelos de dados do runtime
from runtime.data_models import Project, Scene as SceneData, GameObject, Hotspot, Shape, Action

class SceneEditorWidget(QGraphicsView):
    hotspot_selected = Signal(Hotspot) # Sinal emitido quando um hotspot é selecionado

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.project: Optional[Project] = None
        self.current_scene_data: Optional[SceneData] = None
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.setRenderHint(QPainter.Antialiasing) # Use QPainter.Antialiasing
        self.setDragMode(QGraphicsView.RubberBandDrag) # Permite seleção de múltiplos itens
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse) # Zoom/pan a partir do mouse
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)

        self.background_item: Optional[QGraphicsPixmapItem] = None
        self.object_items: List[QGraphicsPixmapItem] = [] # Lista para armazenar os itens de objeto

        # Atributos para desenho de hotspot
        self.drawing_hotspot_mode: bool = False
        self.current_hotspot_points: List[QPointF] = []
        self.temp_hotspot_item: Optional[QGraphicsPolygonItem] = None

        # Conecta o sinal de mudança de seleção da cena
        self.scene.selectionChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self):
        """Chamado quando a seleção de itens na cena muda."""
        selected_items = self.scene.selectedItems()
        if selected_items:
            # Verifica se o item selecionado é um hotspot
            if selected_items[0].data(1) == "hotspot" and self.current_scene_data:
                hotspot_id = selected_items[0].data(0)
                for hotspot in self.current_scene_data.hotspots:
                    if hotspot.id == hotspot_id:
                        self.hotspot_selected.emit(hotspot)
                        print(f"Hotspot '{hotspot_id}' selecionado.")
                        return
            # Se não for hotspot ou não tiver ID, limpa o painel de propriedades
            self.hotspot_selected.emit(None) # Emite None para limpar o painel
        else:
            self.hotspot_selected.emit(None) # Nenhum item selecionado, limpa o painel

    def set_project(self, project: Project):
        """Define o projeto atual para o editor de cena."""
        self.project = project
        self.scene.clear()
        self.current_scene_data = None
        self.background_item = None
        self.object_items = []
        self.scene.setSceneRect(QRectF(0, 0, 1280, 720)) # Tamanho padrão, será ajustado pela cena

    def load_scene(self, scene_id: str):
        """
        Carrega e exibe uma cena específica do projeto.
        """
        if not self.project:
            print("No project loaded.")
            return

        scene_data = self.project.scenes.get(scene_id)
        if not scene_data:
            print(f"Scene '{scene_id}' not found.")
            return

        self.current_scene_data = scene_data
        self.scene.clear() # Limpa a cena anterior

        # Ajusta o tamanho da cena para o tamanho da cena do jogo
        self.scene.setSceneRect(QRectF(0, 0, scene_data.size.width, scene_data.size.height))

        # Carregar imagem de fundo usando Pillow
        background_path = Path(self.project.project_path) / scene_data.background
        if background_path.exists():
            try:
                pil_image = Image.open(background_path)
                q_image = QImage(
                    pil_image.tobytes(),
                    pil_image.width,
                    pil_image.height,
                    QImage.Format_RGBA8888 if pil_image.mode == 'RGBA' else QImage.Format_RGB888
                )
                pixmap = QPixmap.fromImage(q_image)
                self.background_item = QGraphicsPixmapItem(pixmap)
                self.background_item.setZValue(-1) # Desenha no fundo
                self.scene.addItem(self.background_item)
                print(f"Background da cena '{scene_data.name}' carregado.")
            except Exception as e:
                print(f"Error loading background '{background_path}': {e}")
        else:
            print(f"Background not found: {background_path}")
            # Desenha um retângulo cinza como placeholder
            placeholder = self.scene.addRect(0, 0, scene_data.size.width, scene_data.size.height, QPen(Qt.NoPen), QColor(50, 50, 50))
            placeholder.setZValue(-1)
            # Adiciona texto de aviso
            text_item = self.scene.addText(f"Background not found: {scene_data.background}")
            text_item.setDefaultTextColor(Qt.white)
            text_item.setPos(10, 10)


        # Carregar objetos da cena
        self.object_items = []
        for obj_data in scene_data.objects:
            sprite_asset = self.project.assets.sprites.get(obj_data.sprite)
            if not sprite_asset:
                print(f"Aviso: Sprite asset '{obj_data.sprite}' não encontrado para o objeto '{obj_data.id}'.")
                continue

            sprite_path = Path(self.project.project_path) / sprite_asset.path
            if sprite_path.exists():
                try:
                    pil_image = Image.open(sprite_path)
                    q_image = QImage(
                        pil_image.tobytes(),
                        pil_image.width,
                        pil_image.height,
                        QImage.Format_RGBA8888 if pil_image.mode == 'RGBA' else QImage.Format_RGB888
                    )
                    pixmap = QPixmap.fromImage(q_image)
                    item = QGraphicsPixmapItem(pixmap)
                    item.setPos(obj_data.position.x - item.boundingRect().width()/2, obj_data.position.y - item.boundingRect().height()/2)
                    item.setFlag(QGraphicsItem.ItemIsMovable)
                    item.setFlag(QGraphicsItem.ItemIsSelectable)
                    item.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
                    item.setData(0, obj_data.id) # Armazena o ID do objeto no item gráfico
                    self.scene.addItem(item)
                    self.object_items.append(item)
                    print(f"Objeto '{obj_data.id}' carregado.")
                except Exception as e:
                    print(f"Erro ao carregar sprite '{sprite_path}' para objeto '{obj_data.id}': {e}")
            else:
                print(f"Sprite not found: {sprite_path} for object '{obj_data.id}'")
                # Desenha um retângulo como placeholder para o objeto
                placeholder = self.scene.addRect(obj_data.position.x - 32, obj_data.position.y - 32, 64, 64, QPen(Qt.black), QColor(255, 0, 0, 150))
                placeholder.setFlag(QGraphicsItem.ItemIsMovable)
                placeholder.setFlag(QGraphicsItem.ItemIsSelectable)
                placeholder.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
                placeholder.setData(0, obj_data.id)
                self.scene.addItem(placeholder)
                self.object_items.append(placeholder)

        # Carregar hotspots existentes
        for hotspot_data in scene_data.hotspots:
            if hotspot_data.shape.type == "poly":
                polygon = QPolygonF([QPointF(p[0], p[1]) for p in hotspot_data.shape.points])
                hotspot_item = self.scene.addPolygon(polygon, QPen(QColor(0, 255, 0, 150), 2), QColor(0, 255, 0, 50))
                hotspot_item.setFlag(QGraphicsItem.ItemIsSelectable)
                hotspot_item.setData(0, hotspot_data.id)
                hotspot_item.setData(1, "hotspot") # Tipo de item
            # Adicionar outros tipos de shape futuramente
        
        self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio) # Ajusta a cena na visualização

    def set_drawing_hotspot_mode(self, enabled: bool):
        """Ativa/desativa o modo de desenho de hotspot."""
        self.drawing_hotspot_mode = enabled
        if enabled:
            self.setDragMode(QGraphicsView.NoDrag) # Desativa arrastar para desenhar
            self.current_hotspot_points = []
            if self.temp_hotspot_item:
                self.scene.removeItem(self.temp_hotspot_item)
                self.temp_hotspot_item = None
            self.setCursor(Qt.CrossCursor)
            print("Modo de desenho de Hotspot ATIVADO. Clique para adicionar pontos, clique direito para finalizar.")
        else:
            self.setDragMode(QGraphicsView.RubberBandDrag) # Reativa arrastar
            if self.temp_hotspot_item:
                self.scene.removeItem(self.temp_hotspot_item)
                self.temp_hotspot_item = None
            self.current_hotspot_points = []
            self.setCursor(Qt.ArrowCursor)
            print("Modo de desenho de Hotspot DESATIVADO.")

    def mousePressEvent(self, event):
        """
        Manipula eventos de clique do mouse.
        """
        if self.drawing_hotspot_mode:
            scene_pos = self.mapToScene(event.pos())
            if event.button() == Qt.LeftButton:
                self.current_hotspot_points.append(scene_pos)
                self._update_temp_hotspot_item()
            elif event.button() == Qt.RightButton:
                if len(self.current_hotspot_points) >= 3: # Polígono precisa de pelo menos 3 pontos
                    self._finalize_hotspot()
                else:
                    print("Hotspot cancelado: poucos pontos.")
                self.set_drawing_hotspot_mode(False) # Sai do modo de desenho
        else:
            super().mousePressEvent(event) # Comportamento padrão (seleção/arrastar)

    def mouseMoveEvent(self, event):
        """
        Manipula eventos de movimento do mouse.
        """
        if self.drawing_hotspot_mode and self.current_hotspot_points:
            self._update_temp_hotspot_item(self.mapToScene(event.pos()))
        super().mouseMoveEvent(event)

    def _update_temp_hotspot_item(self, current_mouse_pos: Optional[QPointF] = None):
        """
        Atualiza a visualização temporária do polígono sendo desenhado.
        """
        if self.temp_hotspot_item:
            self.scene.removeItem(self.temp_hotspot_item)
        
        if not self.current_hotspot_points:
            return

        polygon_points = QPolygonF(self.current_hotspot_points)
        if current_mouse_pos:
            polygon_points.append(current_mouse_pos)
        
        self.temp_hotspot_item = self.scene.addPolygon(polygon_points, QPen(QColor(255, 255, 0, 200), 2, Qt.DotLine))
        self.temp_hotspot_item.setZValue(100) # Garante que seja desenhado por cima

    def _finalize_hotspot(self):
        """
        Finaliza o desenho do hotspot e o adiciona ao modelo do projeto.
        """
        if not self.current_scene_data or len(self.current_hotspot_points) < 3:
            return

        # Converte QPointF para lista de listas [x, y]
        points_list = [[int(p.x()), int(p.y())] for p in self.current_hotspot_points]
        
        # Cria um ID único para o hotspot (simplificado por enquanto)
        new_hotspot_id = f"hotspot_{len(self.current_scene_data.hotspots) + 1}"
        
        # Cria o modelo de dados do hotspot
        new_hotspot = Hotspot(
            id=new_hotspot_id,
            name=f"Novo Hotspot {len(self.current_scene_data.hotspots) + 1}",
            shape=Shape(type="poly", points=points_list),
            action=Action(type="none", params={}), # Ação padrão, será editada no painel de propriedades
            visible=True,
            enabled=True
        )
        self.current_scene_data.hotspots.append(new_hotspot)
        self.project.scenes[self.current_scene_data.id] = self.current_scene_data # Atualiza o projeto

        # Adiciona o item gráfico permanente à cena
        polygon = QPolygonF(self.current_hotspot_points)
        hotspot_item = self.scene.addPolygon(polygon, QPen(QColor(0, 255, 0, 150), 2), QColor(0, 255, 0, 50))
        hotspot_item.setFlag(QGraphicsItem.ItemIsSelectable)
        hotspot_item.setData(0, new_hotspot_id)
        hotspot_item.setData(1, "hotspot") # Tipo de item
        self.scene.addItem(hotspot_item)
        print(f"Hotspot '{new_hotspot_id}' adicionado à cena.")

        self.current_hotspot_points = []
        if self.temp_hotspot_item:
            self.scene.removeItem(self.temp_hotspot_item)
            self.temp_hotspot_item = None

    def itemChange(self, change, value):
        """
        Captura mudanças nos itens gráficos (ex: movimentação).
        """
        if change == QGraphicsItem.ItemPositionChange and self.current_scene_data:
            item = self.sender()
            if item and item.data(0) and item.data(1) != "hotspot": # Apenas para GameObjects
                obj_id = item.data(0)
                # Encontra o GameObject correspondente no modelo
                for obj_data in self.current_scene_data.objects:
                    if obj_data.id == obj_id:
                        # Atualiza a posição no modelo
                        obj_data.position.x = int(value.x() + item.boundingRect().width()/2)
                        obj_data.position.y = int(value.y() + item.boundingRect().height()/2)
                        # print(f"Objeto '{obj_id}' movido para: ({obj_data.position.x}, {obj_data.position.y})")
                        break
        return super().itemChange(change, value)

    def wheelEvent(self, event):
        """
        Implementa zoom com a roda do mouse.
        """
        zoom_factor = 1.15
        if event.angleDelta().y() > 0:
            self.scale(zoom_factor, zoom_factor)
        else:
            self.scale(1 / zoom_factor, 1 / zoom_factor)
