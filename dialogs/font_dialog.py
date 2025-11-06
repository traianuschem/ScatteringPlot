"""
Font Settings Dialog

This dialog allows users to configure fonts for plot elements.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QGroupBox,
    QLabel, QSpinBox, QFontComboBox, QCheckBox,
    QDialogButtonBox
)


class FontSettingsDialog(QDialog):
    """Dialog für Schriftart-Einstellungen"""

    def __init__(self, parent, font_settings):
        super().__init__(parent)
        self.setWindowTitle("Schriftart-Einstellungen")
        self.font_settings = font_settings.copy()

        layout = QVBoxLayout(self)

        # Titel-Gruppe
        title_group = QGroupBox("Titel")
        title_layout = QGridLayout()

        title_layout.addWidget(QLabel("Schriftgröße:"), 0, 0)
        self.title_size_spin = QSpinBox()
        self.title_size_spin.setRange(6, 48)
        self.title_size_spin.setValue(font_settings.get('title_size', 14))
        self.title_size_spin.setSuffix(" pt")
        title_layout.addWidget(self.title_size_spin, 0, 1)

        self.title_bold = QCheckBox("Fett")
        self.title_bold.setChecked(font_settings.get('title_bold', True))
        title_layout.addWidget(self.title_bold, 1, 0)

        self.title_italic = QCheckBox("Kursiv")
        self.title_italic.setChecked(font_settings.get('title_italic', False))
        title_layout.addWidget(self.title_italic, 1, 1)

        self.title_underline = QCheckBox("Unterstrichen")
        self.title_underline.setChecked(font_settings.get('title_underline', False))
        title_layout.addWidget(self.title_underline, 2, 0)

        title_group.setLayout(title_layout)
        layout.addWidget(title_group)

        # Achsenbeschriftung-Gruppe
        labels_group = QGroupBox("Achsenbeschriftungen")
        labels_layout = QGridLayout()

        labels_layout.addWidget(QLabel("Schriftgröße:"), 0, 0)
        self.labels_size_spin = QSpinBox()
        self.labels_size_spin.setRange(6, 32)
        self.labels_size_spin.setValue(font_settings.get('labels_size', 12))
        self.labels_size_spin.setSuffix(" pt")
        labels_layout.addWidget(self.labels_size_spin, 0, 1)

        self.labels_bold = QCheckBox("Fett")
        self.labels_bold.setChecked(font_settings.get('labels_bold', False))
        labels_layout.addWidget(self.labels_bold, 1, 0)

        self.labels_italic = QCheckBox("Kursiv")
        self.labels_italic.setChecked(font_settings.get('labels_italic', False))
        labels_layout.addWidget(self.labels_italic, 1, 1)

        self.labels_underline = QCheckBox("Unterstrichen")
        self.labels_underline.setChecked(font_settings.get('labels_underline', False))
        labels_layout.addWidget(self.labels_underline, 2, 0)

        labels_group.setLayout(labels_layout)
        layout.addWidget(labels_group)

        # Tick-Labels-Gruppe
        ticks_group = QGroupBox("Achsen-Werte (Ticks)")
        ticks_layout = QGridLayout()

        ticks_layout.addWidget(QLabel("Schriftgröße:"), 0, 0)
        self.ticks_size_spin = QSpinBox()
        self.ticks_size_spin.setRange(6, 24)
        self.ticks_size_spin.setValue(font_settings.get('ticks_size', 10))
        self.ticks_size_spin.setSuffix(" pt")
        ticks_layout.addWidget(self.ticks_size_spin, 0, 1)

        self.ticks_bold = QCheckBox("Fett")
        self.ticks_bold.setChecked(font_settings.get('ticks_bold', False))
        ticks_layout.addWidget(self.ticks_bold, 1, 0)

        self.ticks_italic = QCheckBox("Kursiv")
        self.ticks_italic.setChecked(font_settings.get('ticks_italic', False))
        ticks_layout.addWidget(self.ticks_italic, 1, 1)

        self.ticks_underline = QCheckBox("Unterstrichen")
        self.ticks_underline.setChecked(font_settings.get('ticks_underline', False))
        ticks_layout.addWidget(self.ticks_underline, 2, 0)

        ticks_group.setLayout(ticks_layout)
        layout.addWidget(ticks_group)

        # Legenden-Gruppe
        legend_group = QGroupBox("Legende")
        legend_layout = QGridLayout()

        legend_layout.addWidget(QLabel("Schriftgröße:"), 0, 0)
        self.legend_size_spin = QSpinBox()
        self.legend_size_spin.setRange(6, 24)
        self.legend_size_spin.setValue(font_settings.get('legend_size', 10))
        self.legend_size_spin.setSuffix(" pt")
        legend_layout.addWidget(self.legend_size_spin, 0, 1)

        self.legend_bold = QCheckBox("Fett")
        self.legend_bold.setChecked(font_settings.get('legend_bold', False))
        legend_layout.addWidget(self.legend_bold, 1, 0)

        self.legend_italic = QCheckBox("Kursiv")
        self.legend_italic.setChecked(font_settings.get('legend_italic', False))
        legend_layout.addWidget(self.legend_italic, 1, 1)

        self.legend_underline = QCheckBox("Unterstrichen")
        self.legend_underline.setChecked(font_settings.get('legend_underline', False))
        legend_layout.addWidget(self.legend_underline, 2, 0)

        legend_group.setLayout(legend_layout)
        layout.addWidget(legend_group)

        # Schriftart-Gruppe
        font_group = QGroupBox("Schriftart")
        font_layout = QGridLayout()

        font_layout.addWidget(QLabel("Familie:"), 0, 0)
        self.font_family_combo = QFontComboBox()
        current_font = font_settings.get('font_family', 'sans-serif')
        # Versuche die gespeicherte Schriftart zu setzen
        index = self.font_family_combo.findText(current_font)
        if index >= 0:
            self.font_family_combo.setCurrentIndex(index)
        font_layout.addWidget(self.font_family_combo, 0, 1)

        font_group.setLayout(font_layout)
        layout.addWidget(font_group)

        # Math Text Gruppe (Version 5.2)
        math_group = QGroupBox("Wissenschaftliche Notation")
        math_layout = QGridLayout()

        self.use_math_text = QCheckBox("Math Text für Exponenten verwenden")
        self.use_math_text.setChecked(font_settings.get('use_math_text', False))
        math_layout.addWidget(self.use_math_text, 0, 0, 1, 2)

        hint_label = QLabel("Konvertiert: nm⁻¹ → nm$^{-1}$ für bessere Darstellung")
        hint_label.setStyleSheet("color: #888; font-style: italic; font-size: 9pt;")
        hint_label.setWordWrap(True)
        math_layout.addWidget(hint_label, 1, 0, 1, 2)

        math_group.setLayout(math_layout)
        layout.addWidget(math_group)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_settings(self):
        """Gibt Einstellungen zurück"""
        return {
            'title_size': self.title_size_spin.value(),
            'title_bold': self.title_bold.isChecked(),
            'title_italic': self.title_italic.isChecked(),
            'title_underline': self.title_underline.isChecked(),
            'labels_size': self.labels_size_spin.value(),
            'labels_bold': self.labels_bold.isChecked(),
            'labels_italic': self.labels_italic.isChecked(),
            'labels_underline': self.labels_underline.isChecked(),
            'ticks_size': self.ticks_size_spin.value(),
            'ticks_bold': self.ticks_bold.isChecked(),
            'ticks_italic': self.ticks_italic.isChecked(),
            'ticks_underline': self.ticks_underline.isChecked(),
            'legend_size': self.legend_size_spin.value(),
            'legend_bold': self.legend_bold.isChecked(),
            'legend_italic': self.legend_italic.isChecked(),
            'legend_underline': self.legend_underline.isChecked(),
            'font_family': self.font_family_combo.currentText(),
            'use_math_text': self.use_math_text.isChecked()
        }
