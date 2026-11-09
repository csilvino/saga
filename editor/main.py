"""
Saga Engine - Editor Visual (IDE)
"""
import sys
import json
from pathlib import Path
from typing import Optional # Import Optional
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMenuBar, QToolBar, QStatusBar, QFileDialog, QMessageBox, QStackedWidget, QComboBox
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt, QSize

# Importa os módulos do runtime
sys.path.append(str(Path(__file__).parent.parent)) # Adiciona a raiz do projeto ao sys.path
from runtime.project_loader import load_project_data, ProjectLoadError
from runtime.data_models import Project, Hotspot

# Importa os widgets do editor
from editor.scene_editor_widget import SceneEditorWidget
from editor.properties_panel import PropertiesPanel
from editor.dialog_editor_widget import DialogEditorWidget
from editor.logic_editor_widget import LogicEditorWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Saga Engine Editor")
        self.setGeometry(100, 100, 1280, 720)

        self.current_project: Project | None = None

        self._create_menu_bar()
        self._create_tool_bar()
        self._create_status_bar()
        self._create_central_widget()

    def _create_menu_bar(self):
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("&File")

        new_project_action = QAction("&New Project...", self)
        new_project_action.triggered.connect(self.new_project)
        file_menu.addAction(new_project_action)

        open_project_action = QAction("&Open Project...", self)
        open_project_action.triggered.connect(self.open_project)
        file_menu.addAction(open_project_action)

        save_project_action = QAction("&Save Project", self)
        save_project_action.triggered.connect(self.save_project)
        file_menu.addAction(save_project_action)

        file_menu.addSeparator()

        exit_action = QAction("&Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit Menu
        edit_menu = menu_bar.addMenu("&Edit")
        edit_menu.addAction(QAction("Undo", self))
        edit_menu.addAction(QAction("Redo", self))

    def _create_tool_bar(self):
        tool_bar = QToolBar("Main Toolbar")
        tool_bar.setIconSize(QSize(24, 24))
        self.addToolBar(tool_bar)

        open_action = QAction(QIcon.fromTheme("document-open"), "Open Project", self)
        open_action.triggered.connect(self.open_project)
        tool_bar.addAction(open_action)

        save_action = QAction(QIcon.fromTheme("document-save"), "Save Project", self)
        save_action.triggered.connect(self.save_project)
        tool_bar.addAction(save_action)

        tool_bar.addSeparator()

        # Ação para ativar o modo de desenho de hotspot
        draw_hotspot_action = QAction(QIcon.fromTheme("draw-polygon"), "Draw Hotspot", self)
        draw_hotspot_action.setCheckable(True)
        draw_hotspot_action.triggered.connect(self.toggle_draw_hotspot_mode)
        tool_bar.addAction(draw_hotspot_action)

        tool_bar.addSeparator()

        # Ações para alternar entre editores
        self.scene_editor_action = QAction("Scene Editor", self)
        self.scene_editor_action.triggered.connect(lambda: self.switch_editor("scene"))
        tool_bar.addAction(self.scene_editor_action)

        self.dialog_editor_action = QAction("Dialog Editor", self)
        self.dialog_editor_action.triggered.connect(lambda: self.switch_editor("dialog"))
        tool_bar.addAction(self.dialog_editor_action)

        self.logic_editor_action = QAction("Logic Editor", self)
        self.logic_editor_action.triggered.connect(lambda: self.switch_editor("logic"))
        tool_bar.addAction(self.logic_editor_action)

        tool_bar.addSeparator()

        # ComboBox para selecionar diálogos/lógicas
        self.dialog_selector = QComboBox(self)
        self.dialog_selector.setMinimumWidth(150)
        self.dialog_selector.currentIndexChanged.connect(self.load_selected_dialog_or_logic)
        tool_bar.addWidget(self.dialog_selector)


    def _create_status_bar(self):
        self.statusBar().showMessage("Ready")

    def _create_central_widget(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        self.stacked_editor_widgets = QStackedWidget(self)
        
        self.scene_editor = SceneEditorWidget(self)
        self.stacked_editor_widgets.addWidget(self.scene_editor) # Index 0

        self.dialog_editor = DialogEditorWidget(self)
        self.stacked_editor_widgets.addWidget(self.dialog_editor) # Index 1

        self.logic_editor = LogicEditorWidget(self)
        self.stacked_editor_widgets.addWidget(self.logic_editor) # Index 2

        main_layout.addWidget(self.stacked_editor_widgets, 3) # Ocupa 3/4 do espaço

        self.properties_panel = PropertiesPanel(self)
        main_layout.addWidget(self.properties_panel, 1) # Ocupa 1/4 do espaço

        # Conectar sinais
        self.scene_editor.hotspot_selected.connect(self.properties_panel.set_hotspot)
        self.properties_panel.hotspot_properties_changed.connect(self.update_hotspot_in_project)
        self.dialog_editor.dialog_changed.connect(self.mark_project_as_modified)
        self.logic_editor.logic_graph_changed.connect(self.mark_project_as_modified)


    # --- Slots para ações do menu/toolbar ---
    def new_project(self):
        QMessageBox.information(self, "New Project", "New project functionality not yet implemented.")
        # Implementar lógica para criar novo projeto

    def open_project(self):
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.Directory)
        file_dialog.setWindowTitle("Open Saga Engine Project Folder")
        
        if file_dialog.exec():
            selected_directory = file_dialog.selectedFiles()[0]
            project_path = Path(selected_directory)
            
            try:
                project_data_dict = load_project_data(str(project_path))
                self.current_project = Project.from_dict(project_data_dict, str(project_path))
                self.setWindowTitle(f"Saga Engine Editor - {self.current_project.name}")
                self.statusBar().showMessage(f"Project '{self.current_project.name}' opened from: {project_path}")
                
                self.scene_editor.set_project(self.current_project)
                self.scene_editor.load_scene(self.current_project.start_scene)
                self.dialog_editor.set_project(self.current_project)
                self.logic_editor.set_project(self.current_project)
                self.properties_panel.set_project(self.current_project) # Passa o projeto para o painel de propriedades
                self.properties_panel.clear_panel() # Limpa o painel de propriedades ao carregar novo projeto
                self._populate_dialog_logic_selector() # Popula o ComboBox

            except ProjectLoadError as e:
                QMessageBox.critical(self, "Error Opening Project", f"Failed to load project: {e}")
                self.statusBar().showMessage("Error opening project.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")
                self.statusBar().showMessage("Error opening project.")

    def save_project(self):
        if not self.current_project:
            QMessageBox.warning(self, "Save Project", "No project is currently open to save.")
            return

        project_file_path = Path(self.current_project.project_path) / "project.json"
        try:
            # Salva o diálogo e a lógica antes de salvar o projeto completo
            if self.stacked_editor_widgets.currentWidget() == self.dialog_editor:
                self.dialog_editor.save_dialog_to_project()
            elif self.stacked_editor_widgets.currentWidget() == self.logic_editor:
                self.logic_editor.save_logic_graph_to_project()

            project_data_to_save = self.current_project.to_dict()
            with open(project_file_path, "w", encoding="utf-8") as f:
                json.dump(project_data_to_save, f, indent=2)
            self.statusBar().showMessage(f"Project '{self.current_project.name}' saved successfully.")
            QMessageBox.information(self, "Save Project", "Project saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error Saving Project", f"Failed to save project: {e}")
            self.statusBar().showMessage("Error saving project.")

    def toggle_draw_hotspot_mode(self, checked: bool):
        """Ativa/desativa o modo de desenho de hotspot no editor de cena."""
        if not self.current_project:
            QMessageBox.warning(self, "Draw Hotspot", "Please open a project first.")
            self.sender().setChecked(False) # Desmarca o botão
            return
        self.scene_editor.set_drawing_hotspot_mode(checked)
        self.statusBar().showMessage(f"Draw Hotspot Mode: {'ON' if checked else 'OFF'}")

    def update_hotspot_in_project(self, hotspot_id: str, updated_hotspot: Hotspot):
        """
        Atualiza o hotspot no modelo do projeto quando suas propriedades são alteradas no painel.
        """
        if not self.current_project or not self.scene_editor.current_scene_data:
            return

        scene_id = self.scene_editor.current_scene_data.id
        for i, hotspot in enumerate(self.current_project.scenes[scene_id].hotspots):
            if hotspot.id == hotspot_id:
                self.current_project.scenes[scene_id].hotspots[i] = updated_hotspot
                print(f"Hotspot '{hotspot_id}' atualizado no modelo do projeto.")
                # Opcional: Recarregar a cena ou apenas o item gráfico para refletir mudanças visuais
                break

    def switch_editor(self, editor_type: str):
        """Alterna entre os diferentes editores (cena, diálogo, lógica)."""
        if editor_type == "scene":
            self.stacked_editor_widgets.setCurrentWidget(self.scene_editor)
            self.statusBar().showMessage("Scene Editor Active.")
            self._populate_dialog_logic_selector(editor_type)
        elif editor_type == "dialog":
            self.stacked_editor_widgets.setCurrentWidget(self.dialog_editor)
            self.statusBar().showMessage("Dialog Editor Active.")
            self._populate_dialog_logic_selector(editor_type)
        elif editor_type == "logic":
            self.stacked_editor_widgets.setCurrentWidget(self.logic_editor)
            self.statusBar().showMessage("Logic Editor Active.")
            self._populate_dialog_logic_selector(editor_type)

    def _populate_dialog_logic_selector(self, editor_type: Optional[str] = None):
        """Popula o ComboBox com IDs de diálogos ou grafos de lógica."""
        self.dialog_selector.clear()
        if not self.current_project:
            return

        if editor_type == "dialog":
            if self.current_project.dialogs:
                self.dialog_selector.addItems(sorted(self.current_project.dialogs.keys()))
            else:
                self.dialog_selector.addItem("Nenhum diálogo")
        elif editor_type == "logic":
            # Por enquanto, usamos scripts como placeholder para logic_graphs
            if self.current_project.scripts:
                self.dialog_selector.addItems(sorted(self.current_project.scripts.keys()))
            else:
                self.dialog_selector.addItem("Nenhuma lógica")
        else: # Default para editor de cena ou nenhum editor específico
            self.dialog_selector.addItem("N/A")

    def load_selected_dialog_or_logic(self):
        """Carrega o diálogo ou grafo de lógica selecionado no editor ativo."""
        selected_id = self.dialog_selector.currentText()
        if not selected_id or selected_id == "Nenhum diálogo" or selected_id == "Nenhuma lógica" or selected_id == "N/A":
            return

        current_editor = self.stacked_editor_widgets.currentWidget()
        if current_editor == self.dialog_editor:
            self.dialog_editor.load_dialog(selected_id)
        elif current_editor == self.logic_editor:
            self.logic_editor.load_logic_graph(selected_id)

    def mark_project_as_modified(self):
        """Sinaliza que o projeto foi modificado e precisa ser salvo."""
        self.statusBar().showMessage("Project modified. Save required.")
        # Futuramente, podemos adicionar um asterisco ao título da janela

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
