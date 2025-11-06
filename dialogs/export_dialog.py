"""
Export Settings Dialog

This dialog allows users to configure export settings for plots.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QGroupBox,
    QLabel, QSpinBox, QDoubleSpinBox, QComboBox,
    QCheckBox, QDialogButtonBox, QLineEdit
)


class ExportSettingsDialog(QDialog):
    """Dialog für Export-Einstellungen"""

    def __init__(self, parent, export_settings):
        super().__init__(parent)
        self.setWindowTitle("Export-Einstellungen")
        self.export_settings = export_settings.copy()

        layout = QVBoxLayout(self)

        # Format-Gruppe
        format_group = QGroupBox("Format")
        format_layout = QGridLayout()

        format_layout.addWidget(QLabel("Dateiformat:"), 0, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(['PNG', 'SVG', 'PDF', 'EPS'])
        current_format = export_settings.get('format', 'PNG')
        index = self.format_combo.findText(current_format)
        if index >= 0:
            self.format_combo.setCurrentIndex(index)
        format_layout.addWidget(self.format_combo, 0, 1)

        format_group.setLayout(format_layout)
        layout.addWidget(format_group)

        # Auflösung-Gruppe
        resolution_group = QGroupBox("Auflösung")
        resolution_layout = QGridLayout()

        resolution_layout.addWidget(QLabel("DPI:"), 0, 0)
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 1200)
        self.dpi_spin.setSingleStep(50)
        self.dpi_spin.setValue(export_settings.get('dpi', 300))
        resolution_layout.addWidget(self.dpi_spin, 0, 1)

        resolution_group.setLayout(resolution_layout)
        layout.addWidget(resolution_group)

        # Größe-Gruppe (in cm statt inch)
        size_group = QGroupBox("Größe")
        size_layout = QGridLayout()

        size_layout.addWidget(QLabel("Breite:"), 0, 0)
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(2.5, 127.0)  # 1-50 inch = 2.5-127 cm
        self.width_spin.setSingleStep(1.0)
        # Konvertiere von inch (gespeichert) zu cm (angezeigt)
        self.width_spin.setValue(export_settings.get('width', 10.0) * 2.54)
        self.width_spin.setSuffix(" cm")
        self.width_spin.setDecimals(1)
        size_layout.addWidget(self.width_spin, 0, 1)

        size_layout.addWidget(QLabel("Höhe:"), 1, 0)
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(2.5, 127.0)  # 1-50 inch = 2.5-127 cm
        self.height_spin.setSingleStep(1.0)
        # Konvertiere von inch (gespeichert) zu cm (angezeigt)
        self.height_spin.setValue(export_settings.get('height', 8.0) * 2.54)
        self.height_spin.setSuffix(" cm")
        self.height_spin.setDecimals(1)
        size_layout.addWidget(self.height_spin, 1, 1)

        self.keep_aspect = QCheckBox("Seitenverhältnis beibehalten")
        self.keep_aspect.setChecked(export_settings.get('keep_aspect', True))
        size_layout.addWidget(self.keep_aspect, 2, 0, 1, 2)

        size_group.setLayout(size_layout)
        layout.addWidget(size_group)

        # Optionen-Gruppe
        options_group = QGroupBox("Optionen")
        options_layout = QGridLayout()

        self.transparent_bg = QCheckBox("Transparenter Hintergrund")
        self.transparent_bg.setChecked(export_settings.get('transparent', False))
        options_layout.addWidget(self.transparent_bg, 0, 0, 1, 2)

        self.tight_layout = QCheckBox("Tight Layout (weniger Rand)")
        self.tight_layout.setChecked(export_settings.get('tight_layout', True))
        options_layout.addWidget(self.tight_layout, 1, 0, 1, 2)

        self.facecolor_white = QCheckBox("Weißer Hintergrund (bei PNG)")
        self.facecolor_white.setChecked(export_settings.get('facecolor_white', False))
        options_layout.addWidget(self.facecolor_white, 2, 0, 1, 2)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Hinweis
        hint_label = QLabel("Hinweis: PNG eignet sich für Präsentationen, SVG/PDF für Publikationen.")
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(hint_label)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_settings(self):
        """Gibt Einstellungen zurück (Größe von cm in inch konvertiert)"""
        return {
            'format': self.format_combo.currentText(),
            'dpi': self.dpi_spin.value(),
            'width': self.width_spin.value() / 2.54,  # cm → inch
            'height': self.height_spin.value() / 2.54,  # cm → inch
            'keep_aspect': self.keep_aspect.isChecked(),
            'transparent': self.transparent_bg.isChecked(),
            'tight_layout': self.tight_layout.isChecked(),
            'facecolor_white': self.facecolor_white.isChecked()
        }
