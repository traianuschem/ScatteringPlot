"""
Title Editor Dialog

This dialog allows users to configure the plot title with full customization:
- Title text
- Position (left, center, right)
- Colors (text and background)
- Font settings
- Enable/disable checkbox
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QDialogButtonBox, QCheckBox,
    QComboBox, QSpinBox, QPushButton, QColorDialog, QHBoxLayout
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from i18n import tr


class TitleEditorDialog(QDialog):
    """Dialog für Titel-Einstellungen"""

    def __init__(self, parent, title_settings=None):
        super().__init__(parent)
        self.setWindowTitle(tr("title_editor.title"))
        self.resize(550, 500)

        # Title settings initialisieren
        if title_settings is None:
            title_settings = {
                'enabled': False,
                'text': '',
                'position': 'center',
                'color': '#000000',
                'background_color': None,
                'background_alpha': 0.8,
                'size': 14,
                'bold': True,
                'italic': False
            }
        self.title_settings = title_settings

        self.setup_ui()

    def setup_ui(self):
        """UI aufbauen"""
        layout = QVBoxLayout(self)

        # Titel aktivieren/deaktivieren
        self.enabled_check = QCheckBox(tr("title_editor.show_title"))
        self.enabled_check.setChecked(self.title_settings.get('enabled', False))
        self.enabled_check.stateChanged.connect(self.on_enabled_changed)
        layout.addWidget(self.enabled_check)

        # Titel-Text Gruppe
        text_group = QGroupBox(tr("title_editor.text.title"))
        text_layout = QGridLayout()

        text_layout.addWidget(QLabel(tr("title_editor.text.label")), 0, 0)
        self.title_edit = QLineEdit()
        self.title_edit.setText(self.title_settings.get('text', ''))
        self.title_edit.setPlaceholderText(tr("title_editor.text.placeholder"))
        text_layout.addWidget(self.title_edit, 0, 1)

        text_group.setLayout(text_layout)
        layout.addWidget(text_group)

        # Position und Ausrichtung
        position_group = QGroupBox(tr("title_editor.position.title"))
        position_layout = QGridLayout()

        position_layout.addWidget(QLabel(tr("title_editor.position.horizontal")), 0, 0)
        self.position_combo = QComboBox()
        self.position_combo.addItems(['left', 'center', 'right'])
        current_pos = self.title_settings.get('position', 'center')
        index = self.position_combo.findText(current_pos)
        if index >= 0:
            self.position_combo.setCurrentIndex(index)
        position_layout.addWidget(self.position_combo, 0, 1)

        position_group.setLayout(position_layout)
        layout.addWidget(position_group)

        # Farben
        colors_group = QGroupBox(tr("title_editor.colors.title"))
        colors_layout = QGridLayout()

        # Text-Farbe
        colors_layout.addWidget(QLabel(tr("title_editor.colors.text_color")), 0, 0)
        self.text_color_btn = QPushButton()
        self.text_color = self.title_settings.get('color', '#000000')
        self.update_color_button(self.text_color_btn, self.text_color)
        self.text_color_btn.clicked.connect(self.choose_text_color)
        colors_layout.addWidget(self.text_color_btn, 0, 1)

        # Hintergrund-Farbe
        colors_layout.addWidget(QLabel(tr("title_editor.colors.background")), 1, 0)
        bg_layout = QHBoxLayout()

        self.background_check = QCheckBox(tr("title_editor.colors.show_background"))
        bg_color = self.title_settings.get('background_color')
        self.background_check.setChecked(bg_color is not None)
        bg_layout.addWidget(self.background_check)

        self.bg_color_btn = QPushButton()
        self.bg_color = bg_color if bg_color else '#FFFFFF'
        self.update_color_button(self.bg_color_btn, self.bg_color)
        self.bg_color_btn.clicked.connect(self.choose_bg_color)
        self.bg_color_btn.setEnabled(self.background_check.isChecked())
        self.background_check.stateChanged.connect(
            lambda: self.bg_color_btn.setEnabled(self.background_check.isChecked())
        )
        bg_layout.addWidget(self.bg_color_btn)

        colors_layout.addLayout(bg_layout, 1, 1)

        # Hintergrund-Transparenz
        colors_layout.addWidget(QLabel(tr("title_editor.colors.background_alpha")), 2, 0)
        self.bg_alpha_spin = QSpinBox()
        self.bg_alpha_spin.setRange(0, 100)
        self.bg_alpha_spin.setValue(int(self.title_settings.get('background_alpha', 0.8) * 100))
        self.bg_alpha_spin.setSuffix(" %")
        self.bg_alpha_spin.setEnabled(self.background_check.isChecked())
        self.background_check.stateChanged.connect(
            lambda: self.bg_alpha_spin.setEnabled(self.background_check.isChecked())
        )
        colors_layout.addWidget(self.bg_alpha_spin, 2, 1)

        colors_group.setLayout(colors_layout)
        layout.addWidget(colors_group)

        # Schriftart
        font_group = QGroupBox(tr("title_editor.font.title"))
        font_layout = QGridLayout()

        font_layout.addWidget(QLabel(tr("title_editor.font.size")), 0, 0)
        self.size_spin = QSpinBox()
        self.size_spin.setRange(6, 48)
        self.size_spin.setValue(self.title_settings.get('size', 14))
        self.size_spin.setSuffix(" pt")
        font_layout.addWidget(self.size_spin, 0, 1)

        self.bold_check = QCheckBox(tr("title_editor.font.bold"))
        self.bold_check.setChecked(self.title_settings.get('bold', True))
        font_layout.addWidget(self.bold_check, 1, 0)

        self.italic_check = QCheckBox(tr("title_editor.font.italic"))
        self.italic_check.setChecked(self.title_settings.get('italic', False))
        font_layout.addWidget(self.italic_check, 1, 1)

        font_group.setLayout(font_layout)
        layout.addWidget(font_group)

        layout.addStretch()

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Initial state
        self.on_enabled_changed()

    def on_enabled_changed(self):
        """Aktiviert/deaktiviert die Einstellungen basierend auf der Checkbox"""
        enabled = self.enabled_check.isChecked()
        self.title_edit.setEnabled(enabled)
        self.position_combo.setEnabled(enabled)
        self.text_color_btn.setEnabled(enabled)
        self.background_check.setEnabled(enabled)
        self.bg_color_btn.setEnabled(enabled and self.background_check.isChecked())
        self.bg_alpha_spin.setEnabled(enabled and self.background_check.isChecked())
        self.size_spin.setEnabled(enabled)
        self.bold_check.setEnabled(enabled)
        self.italic_check.setEnabled(enabled)

    def update_color_button(self, button, color):
        """Aktualisiert den Farbbutton"""
        button.setStyleSheet(f"background-color: {color}; min-width: 80px; min-height: 25px;")
        button.setText(color)

    def choose_text_color(self):
        """Öffnet Farbauswahl für Text-Farbe"""
        color = QColorDialog.getColor(QColor(self.text_color), self, tr("title_editor.text_color_dialog"))
        if color.isValid():
            self.text_color = color.name()
            self.update_color_button(self.text_color_btn, self.text_color)

    def choose_bg_color(self):
        """Öffnet Farbauswahl für Hintergrund-Farbe"""
        color = QColorDialog.getColor(QColor(self.bg_color), self, tr("title_editor.background_color_dialog"))
        if color.isValid():
            self.bg_color = color.name()
            self.update_color_button(self.bg_color_btn, self.bg_color)

    def get_settings(self):
        """Gibt die Titel-Einstellungen zurück"""
        return {
            'enabled': self.enabled_check.isChecked(),
            'text': self.title_edit.text(),
            'position': self.position_combo.currentText(),
            'color': self.text_color,
            'background_color': self.bg_color if self.background_check.isChecked() else None,
            'background_alpha': self.bg_alpha_spin.value() / 100.0,
            'size': self.size_spin.value(),
            'bold': self.bold_check.isChecked(),
            'italic': self.italic_check.isChecked()
        }
