"""
Painel de Propriedades para edição de Hotspots e outros elementos.
"""
import json
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QFormLayout
from PySide6.QtCore import Qt, Signal
from typing import Optional, Any, Dict, List

# Importa os modelos de dados do runtime
from runtime.data_models import Hotspot, Action, Shape, Project

class PropertiesPanel(QWidget):
    # Sinal emitido quando as propriedades de um hotspot são alteradas
    hotspot_properties_changed = Signal(str, Hotspot) # hotspot_id, updated_hotspot

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.current_hotspot: Optional[Hotspot] = None
        self.current_project: Optional[Project] = None # Adiciona referência ao projeto
        self.current_hotspot_id: Optional[str] = None

        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)

        self.title_label = QLabel("Propriedades do Hotspot")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.layout.addWidget(self.title_label)

        self.form_layout = QFormLayout()
        self.layout.addLayout(self.form_layout)

        # Campos de edição
        self.id_input = QLineEdit()
        self.id_input.setReadOnly(True) # ID geralmente não é editável diretamente
        self.form_layout.addRow("ID:", self.id_input)

        self.name_input = QLineEdit()
        self.form_layout.addRow("Nome:", self.name_input)

        self.visible_checkbox = QComboBox()
        self.visible_checkbox.addItems(["True", "False"])
        self.form_layout.addRow("Visível:", self.visible_checkbox)

        self.enabled_checkbox = QComboBox()
        self.enabled_checkbox.addItems(["True", "False"])
        self.form_layout.addRow("Habilitado:", self.enabled_checkbox)

        # Seção de Ação
        self.action_type_combo = QComboBox()
        self.action_type_combo.addItems(["go_to_scene", "add_item", "remove_item", "combine_items", "start_dialog", "run_script", "play_music", "play_sound", "stop_music"])
        self.action_type_combo.currentTextChanged.connect(self._on_action_type_changed)
        self.form_layout.addRow("Ação Tipo:", self.action_type_combo)

        self.action_params_layout = QVBoxLayout() # Layout para parâmetros dinâmicos
        self.form_layout.addRow("Parâmetros:", self.action_params_layout)
        
        # Campos de parâmetros específicos (inicialmente ocultos)
        self.param_scene_id_input = QLineEdit()
        self.param_item_id_input = QLineEdit()
        self.param_item1_id_input = QLineEdit()
        self.param_item2_id_input = QLineEdit()
        self.param_result_item_id_input = QLineEdit()
        self.param_dialog_id_input = QLineEdit()
        self.param_script_id_combo = QComboBox() # Para selecionar scripts
        self.param_music_id_input = QLineEdit()
        self.param_sound_id_input = QLineEdit()
        self.param_slot_input = QLineEdit() # Para save/load game

        self.param_widgets: Dict[str, QWidget] = {} # Mapeia o nome do parâmetro para o widget
        self._setup_param_widgets()

        # Botão de Salvar
        self.save_button = QPushButton("Aplicar Alterações")
        self.save_button.clicked.connect(self._apply_changes)
        self.layout.addWidget(self.save_button)

        self.clear_panel() # Inicializa o painel vazio

    def _setup_param_widgets(self):
        """Configura os widgets para os parâmetros das ações."""
        self.param_widgets = {
            "scene": self.param_scene_id_input,
            "item_id": self.param_item_id_input,
            "item1_id": self.param_item1_id_input,
            "item2_id": self.param_item2_id_input,
            "result_item_id": self.param_result_item_id_input,
            "dialog_id": self.param_dialog_id_input,
            "script_id": self.param_script_id_combo,
            "music_id": self.param_music_id_input,
            "sound_id": self.param_sound_id_input,
            "slot": self.param_slot_input
        }
        # Adiciona todos os widgets de parâmetro ao layout, mas os esconde
        for param_name, widget in self.param_widgets.items():
            self.action_params_layout.addWidget(QLabel(f"{param_name.replace('_', ' ').title()}:"))
            self.action_params_layout.addWidget(widget)
            widget.hide() # Esconde por padrão

    def _on_action_type_changed(self, action_type: str):
        """
        Atualiza os campos de parâmetro visíveis com base no tipo de ação selecionado.
        """
        for widget in self.param_widgets.values():
            widget.hide() # Esconde todos os parâmetros

        if action_type == "go_to_scene":
            self.param_widgets["scene"].show()
        elif action_type == "add_item" or action_type == "remove_item":
            self.param_widgets["item_id"].show()
        elif action_type == "combine_items":
            self.param_widgets["item1_id"].show()
            self.param_widgets["item2_id"].show()
            self.param_widgets["result_item_id"].show()
        elif action_type == "start_dialog":
            self.param_widgets["dialog_id"].show()
        elif action_type == "run_script":
            self.param_widgets["script_id"].show()
            self._populate_script_combo()
        elif action_type == "play_music":
            self.param_widgets["music_id"].show()
        elif action_type == "play_sound":
            self.param_widgets["sound_id"].show()
        elif action_type == "save_game" or action_type == "load_game":
            self.param_widgets["slot"].show()

    def _populate_script_combo(self):
        """Preenche o QComboBox de scripts com os IDs de scripts do projeto."""
        self.param_script_id_combo.clear()
        if self.current_project and self.current_project.scripts:
            self.param_script_id_combo.addItems(sorted(self.current_project.scripts.keys()))
        else:
            self.param_script_id_combo.addItem("Nenhum script disponível")

    def set_project(self, project: Project):
        """Define o projeto atual para o painel de propriedades."""
        self.current_project = project
        self._populate_script_combo() # Atualiza a lista de scripts

    def clear_panel(self):
        """Limpa todos os campos do painel."""
        self.current_hotspot = None
        self.current_hotspot_id = None
        self.title_label.setText("Nenhum Hotspot Selecionado")
        self.id_input.clear()
        self.name_input.clear()
        self.visible_checkbox.setCurrentIndex(0)
        self.enabled_checkbox.setCurrentIndex(0)
        self.action_type_combo.setCurrentIndex(0)
        for widget in self.param_widgets.values():
            if isinstance(widget, QLineEdit):
                widget.clear()
            elif isinstance(widget, QComboBox):
                widget.clear()
        self.save_button.setEnabled(False)

    def set_hotspot(self, hotspot: Hotspot):
        """
        Define o hotspot cujas propriedades serão exibidas e editadas.
        """
        self.current_hotspot = hotspot
        self.current_hotspot_id = hotspot.id
        self.title_label.setText(f"Propriedades: {hotspot.name or hotspot.id}")
        self.id_input.setText(hotspot.id)
        self.name_input.setText(hotspot.name or "")
        self.visible_checkbox.setCurrentText(str(hotspot.visible))
        self.enabled_checkbox.setCurrentText(str(hotspot.enabled))
        
        # Define o tipo de ação e atualiza os parâmetros visíveis
        self.action_type_combo.setCurrentText(hotspot.action.type)
        self._on_action_type_changed(hotspot.action.type) # Garante que os campos corretos apareçam

        # Preenche os campos de parâmetro
        for param_name, param_value in hotspot.action.params.items():
            widget = self.param_widgets.get(param_name)
            if widget:
                if isinstance(widget, QLineEdit):
                    widget.setText(str(param_value))
                elif isinstance(widget, QComboBox):
                    widget.setCurrentText(str(param_value))

        self.save_button.setEnabled(True)

    def _apply_changes(self):
        """
        Aplica as alterações dos campos de volta ao objeto Hotspot e emite um sinal.
        """
        if not self.current_hotspot:
            return

        try:
            # Atualiza o modelo de dados do hotspot
            self.current_hotspot.name = self.name_input.text()
            self.current_hotspot.visible = self.visible_checkbox.currentText() == "True"
            self.current_hotspot.enabled = self.enabled_checkbox.currentText() == "True"
            
            # Atualiza a ação
            action_type = self.action_type_combo.currentText()
            new_params: Dict[str, Any] = {}
            # Coleta os parâmetros visíveis
            if action_type == "go_to_scene":
                new_params["scene"] = self.param_scene_id_input.text()
            elif action_type == "add_item" or action_type == "remove_item":
                new_params["item_id"] = self.param_item_id_input.text()
            elif action_type == "combine_items":
                new_params["item1_id"] = self.param_item1_id_input.text()
                new_params["item2_id"] = self.param_item2_id_input.text()
                new_params["result_item_id"] = self.param_result_item_id_input.text()
            elif action_type == "start_dialog":
                new_params["dialog_id"] = self.param_dialog_id_input.text()
            elif action_type == "run_script":
                new_params["script_id"] = self.param_script_id_combo.currentText()
            elif action_type == "play_music":
                new_params["music_id"] = self.param_music_id_input.text()
            elif action_type == "play_sound":
                new_params["sound_id"] = self.param_sound_id_input.text()
            elif action_type == "save_game" or action_type == "load_game":
                new_params["slot"] = int(self.param_slot_input.text()) # Assume que é um int

            self.current_hotspot.action = Action(type=action_type, params=new_params)

            print(f"Propriedades do hotspot '{self.current_hotspot.id}' atualizadas.")
            self.hotspot_properties_changed.emit(self.current_hotspot.id, self.current_hotspot)
        except ValueError:
            print("Erro: Parâmetro 'slot' deve ser um número inteiro.")
        except Exception as e:
            print(f"Erro ao aplicar alterações: {e}")
