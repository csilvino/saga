"""
Diálogo de Configurações para o Editor da Saga Engine.
Permite ao usuário gerenciar chaves de API e outras configurações.
"""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFormLayout, QMessageBox
from PySide6.QtCore import Qt
from typing import Optional

from editor.settings_manager import SettingsManager
from editor.ai_core import AICore # Para configurar a API

class SettingsDialog(QDialog):
    def __init__(self, ai_core: AICore, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Editor Settings")
        self.setMinimumWidth(400)

        self.ai_core = ai_core
        self.settings_manager = SettingsManager()

        self._create_widgets()
        self._load_current_settings()

    def _create_widgets(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # --- Gemini API Key ---
        self.gemini_api_key_input = QLineEdit()
        self.gemini_api_key_input.setEchoMode(QLineEdit.Password) # Esconde a chave
        form_layout.addRow("Gemini API Key:", self.gemini_api_key_input)

        # --- Outras configurações futuras ---
        # Ex: self.editor_theme_combo = QComboBox()
        # form_layout.addRow("Editor Theme:", self.editor_theme_combo)

        main_layout.addLayout(form_layout)

        # --- Botões ---
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self._save_settings)
        button_layout.addWidget(self.save_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject) # Fecha o diálogo sem salvar
        button_layout.addWidget(self.cancel_button)

        main_layout.addLayout(button_layout)

    def _load_current_settings(self):
        """
        Carrega as configurações atuais e preenche os campos.
        """
        gemini_key = self.settings_manager.get_api_key("gemini")
        if gemini_key:
            self.gemini_api_key_input.setText(gemini_key)

    def _save_settings(self):
        """
        Salva as configurações inseridas pelo usuário.
        """
        gemini_key = self.gemini_api_key_input.text().strip()
        if gemini_key:
            self.settings_manager.set_api_key("gemini", gemini_key)
            self.ai_core.configure_provider("gemini", gemini_key) # Tenta configurar a API imediatamente
        else:
            # Se a chave for limpa, remove do settings
            api_keys = self.settings_manager.get_setting("api_keys", {})
            if "gemini" in api_keys:
                del api_keys["gemini"]
                self.settings_manager.set_setting("api_keys", api_keys)
                self.ai_core.configured_providers["gemini"] = False # Desconfigura no AICore
            QMessageBox.information(self, "Settings", "Gemini API Key cleared.")

        QMessageBox.information(self, "Settings", "Settings saved successfully!")
        self.accept() # Fecha o diálogo com sucesso

