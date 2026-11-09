"""
Diálogo para geração de ideias (nomes, itens, pistas) usando IA.
"""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QTextEdit, QFormLayout, QMessageBox
from PySide6.QtCore import Qt
from typing import Optional

from editor.ai_core import AICore
from runtime.data_models import Project

class IdeaGeneratorDialog(QDialog):
    def __init__(self, ai_core: AICore, current_project: Optional[Project] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Generate Idea with AI")
        self.setMinimumWidth(500)

        self.ai_core = ai_core
        self.current_project = current_project

        self._create_widgets()

    def _create_widgets(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # --- Tipo de Ideia ---
        self.idea_type_label = QLabel("Type of Idea:")
        self.idea_type_selector = QComboBox()
        self.idea_type_selector.addItems(["Item", "Character Name", "Location Name", "Plot Twist", "Puzzle Idea"])
        form_layout.addRow(self.idea_type_label, self.idea_type_selector)

        # --- Contexto/Prompt ---
        self.context_label = QLabel("Context/Prompt:")
        self.context_input = QTextEdit()
        self.context_input.setPlaceholderText("e.g., 'A magical artifact found in a pirate's treasure chest', 'A mysterious character in a haunted mansion'")
        form_layout.addRow(self.context_label, self.context_input)

        main_layout.addLayout(form_layout)

        # --- Botão Gerar ---
        self.generate_button = QPushButton("Generate Idea")
        self.generate_button.clicked.connect(self._generate_idea)
        main_layout.addWidget(self.generate_button)

        # --- Resultado ---
        self.result_label = QLabel("Generated Idea:")
        self.result_output = QTextEdit()
        self.result_output.setReadOnly(True)
        main_layout.addWidget(self.result_label)
        main_layout.addWidget(self.result_output)

        # --- Botões de Ação ---
        button_layout = QHBoxLayout()
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.reject)
        button_layout.addWidget(self.close_button)

        main_layout.addLayout(button_layout)

    def _generate_idea(self):
        """
        Gera uma ideia usando a IA com base no tipo e contexto fornecidos.
        """
        if not self.ai_core.is_provider_configured("gemini"):
            QMessageBox.warning(self, "Generate Idea", "Gemini API is not configured. Please configure it in Editor Settings.")
            return

        idea_type = self.idea_type_selector.currentText()
        context = self.context_input.toPlainText().strip()

        if not context:
            QMessageBox.warning(self, "Generate Idea", "Please provide some context or a prompt for the AI.")
            return

        # Constrói o prompt para a IA
        project_context = ""
        if self.current_project:
            project_context = (f"The game project is named '{self.current_project.name}' "
                               f"and its description is '{self.current_project.metadata.description}'.")

        prompt = (f"Generate a {idea_type} idea for a point-and-click adventure game. "
                  f"Context: '{context}'. "
                  f"{project_context} "
                  f"Be concise and creative. Provide only the idea itself, no conversational filler.")
        
        QMessageBox.information(self, "Generate Idea", "Gerando ideia com IA... Isso pode levar alguns segundos.")
        
        generated_text = self.ai_core.generate_text(prompt)

        if generated_text:
            self.result_output.setPlainText(generated_text)
        else:
            QMessageBox.warning(self, "Generate Idea", "Não foi possível gerar uma ideia. Verifique sua conexão ou a configuração da API.")

