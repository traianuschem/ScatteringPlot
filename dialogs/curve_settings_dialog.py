"""
Curve Settings Dialog

Umfassender Dialog zur Bearbeitung aller Kurveneinstellungen:
- Farbe (Picker + Schnellauswahl aus aktueller Palette)
- Marker (Stil, Größe)
- Linie (Stil, Breite)
- Fehlerbalken (Anzeige, Stil, Transparenz)
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QDialogButtonBox, QCheckBox, QPushButton,
    QComboBox, QSpinBox, QDoubleSpinBox, QColorDialog, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from i18n import tr


class CurveSettingsDialog(QDialog):
    """Dialog zur umfassenden Bearbeitung von Kurveneinstellungen"""

    # Verfügbare Marker und Linien-Stile (diese werden dynamisch übersetzt)
    @staticmethod
    def get_marker_styles():
        return {
            tr("curve_settings.marker.none"): '',
            tr("curve_settings.marker.circle"): 'o',
            tr("curve_settings.marker.square"): 's',
            tr("curve_settings.marker.triangle_up"): '^',
            tr("curve_settings.marker.triangle_down"): 'v',
            tr("curve_settings.marker.triangle_left"): '<',
            tr("curve_settings.marker.triangle_right"): '>',
            tr("curve_settings.marker.diamond"): 'D',
            tr("curve_settings.marker.star"): '*',
            tr("curve_settings.marker.plus"): '+',
            tr("curve_settings.marker.cross"): 'x',
            tr("curve_settings.marker.dot"): '.',
            tr("curve_settings.marker.pixel"): ',',
        }

    @staticmethod
    def get_line_styles():
        return {
            tr("curve_settings.line.none"): '',
            tr("curve_settings.line.solid"): '-',
            tr("curve_settings.line.dashed"): '--',
            tr("curve_settings.line.dashdot"): '-.',
            tr("curve_settings.line.dotted"): ':',
        }

    def __init__(self, parent, dataset, current_color_scheme=None, color_schemes=None):
        """
        Args:
            parent: Parent Widget
            dataset: DataSet-Objekt
            current_color_scheme: Name der aktuellen Farbpalette
            color_schemes: Dict mit allen verfügbaren Farbpaletten
        """
        super().__init__(parent)
        self.dataset = dataset
        self.current_color_scheme = current_color_scheme
        self.color_schemes = color_schemes or {}
        self.selected_color = dataset.color

        self.setWindowTitle(tr("curve_settings.title", dataset=dataset.name))
        self.resize(600, 700)

        layout = QVBoxLayout(self)

        # Info-Label
        info_label = QLabel(tr("curve_settings.info"))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # === FARBE ===
        color_group = QGroupBox(tr("curve_settings.color.title"))
        color_layout = QVBoxLayout()

        # Aktuelle Farbe anzeigen
        color_display_layout = QHBoxLayout()
        color_display_layout.addWidget(QLabel(tr("curve_settings.color.current")))

        self.color_preview = QFrame()
        self.color_preview.setFixedSize(100, 30)
        self.color_preview.setFrameShape(QFrame.Box)
        self.update_color_preview()
        color_display_layout.addWidget(self.color_preview)

        self.color_picker_btn = QPushButton(tr("curve_settings.color.picker"))
        self.color_picker_btn.clicked.connect(self.open_color_picker)
        color_display_layout.addWidget(self.color_picker_btn)

        color_display_layout.addStretch()
        color_layout.addLayout(color_display_layout)

        # Schnellfarben aus aktueller Palette
        if current_color_scheme and current_color_scheme in self.color_schemes:
            palette_colors = self.color_schemes[current_color_scheme]

            color_layout.addWidget(QLabel(tr("curve_settings.color.quick_selection", scheme=current_color_scheme)))

            # Farb-Buttons in Grid
            quick_colors_layout = QGridLayout()
            for i, color in enumerate(palette_colors[:10]):  # Max 10 Farben
                btn = QPushButton()
                btn.setFixedSize(40, 30)
                btn.setStyleSheet(f"background-color: {color}; border: 2px solid #888;")
                btn.clicked.connect(lambda checked, c=color: self.set_quick_color(c))
                quick_colors_layout.addWidget(btn, i // 5, i % 5)

            color_layout.addLayout(quick_colors_layout)

        # Reset-Button für Farbe
        reset_color_btn = QPushButton(tr("curve_settings.color.reset"))
        reset_color_btn.clicked.connect(self.reset_color)
        color_layout.addWidget(reset_color_btn)

        color_group.setLayout(color_layout)
        layout.addWidget(color_group)

        # === MARKER ===
        marker_group = QGroupBox(tr("curve_settings.marker.title"))
        marker_layout = QGridLayout()

        marker_layout.addWidget(QLabel(tr("curve_settings.marker.style")), 0, 0)
        self.marker_combo = QComboBox()
        marker_styles = self.get_marker_styles()
        for name, style in marker_styles.items():
            self.marker_combo.addItem(name, style)
        # Aktuellen Marker setzen
        current_marker = dataset.marker_style or ''
        for i, (name, style) in enumerate(marker_styles.items()):
            if style == current_marker:
                self.marker_combo.setCurrentIndex(i)
                break
        marker_layout.addWidget(self.marker_combo, 1, 1)

        marker_layout.addWidget(QLabel(tr("curve_settings.marker.size")), 1, 0)
        self.marker_size_spin = QDoubleSpinBox()
        self.marker_size_spin.setRange(0, 20)
        self.marker_size_spin.setSingleStep(0.5)
        self.marker_size_spin.setValue(dataset.marker_size)
        marker_layout.addWidget(self.marker_size_spin, 2, 1)

        marker_group.setLayout(marker_layout)
        layout.addWidget(marker_group)

        # === LINIE ===
        line_group = QGroupBox(tr("curve_settings.line.title"))
        line_layout = QGridLayout()

        line_layout.addWidget(QLabel(tr("curve_settings.line.style")), 0, 0)
        self.line_combo = QComboBox()
        line_styles = self.get_line_styles()
        for name, style in line_styles.items():
            self.line_combo.addItem(name, style)
        # Aktuelle Linie setzen
        current_line = dataset.line_style or ''
        for i, (name, style) in enumerate(line_styles.items()):
            if style == current_line:
                self.line_combo.setCurrentIndex(i)
                break
        line_layout.addWidget(self.line_combo, 0, 1)

        line_layout.addWidget(QLabel(tr("curve_settings.line.width")), 1, 0)
        self.line_width_spin = QDoubleSpinBox()
        self.line_width_spin.setRange(0, 10)
        self.line_width_spin.setSingleStep(0.5)
        self.line_width_spin.setValue(dataset.line_width)
        line_layout.addWidget(self.line_width_spin, 1, 1)

        line_group.setLayout(line_layout)
        layout.addWidget(line_group)

        # === FEHLERBALKEN ===
        error_group = QGroupBox(tr("curve_settings.error_bars.title"))
        error_layout = QGridLayout()

        # Checkbox zum Aktivieren/Deaktivieren
        self.show_errorbars_check = QCheckBox(tr("curve_settings.error_bars.show"))
        self.show_errorbars_check.setChecked(getattr(dataset, 'show_errorbars', True))
        self.show_errorbars_check.stateChanged.connect(self.toggle_errorbar_settings)
        error_layout.addWidget(self.show_errorbars_check, 0, 0, 1, 2)

        # Info ob Fehler vorhanden sind
        has_errors = dataset.y_err is not None
        self.error_info = QLabel()
        if has_errors:
            error_info.setText(tr("curve_settings.error_bars.available"))
            error_info.setStyleSheet("color: green;")
        else:
            error_info.setText(tr("curve_settings.error_bars.not_available"))
            error_info.setStyleSheet("color: #888;")
            self.show_errorbars_check.setEnabled(False)
        error_layout.addWidget(error_info, 1, 0, 1, 2)

        # Fehlerbalken-Stil (v6.0)
        error_layout.addWidget(QLabel(tr("curve_settings.error_bars.representation")), 2, 0)
        self.errorbar_style_combo = QComboBox()
        self.errorbar_style_combo.addItem(tr("curve_settings.error_bars.fill"), "fill")
        self.errorbar_style_combo.addItem(tr("curve_settings.error_bars.bars"), "bars")
        # Aktuellen Stil setzen
        current_style = getattr(dataset, 'errorbar_style', 'fill')
        if current_style == 'bars':
            self.errorbar_style_combo.setCurrentIndex(1)
        elif current_style == 'stem':
            self.errorbar_style_combo.setCurrentIndex(2)
        else:
            self.errorbar_style_combo.setCurrentIndex(0)
        self.errorbar_style_combo.currentIndexChanged.connect(self.update_errorbar_ui)
        error_layout.addWidget(self.errorbar_style_combo, 2, 1)

        # Info-Text für gewählten Stil
        self.errorbar_info_label = QLabel()
        self.errorbar_info_label.setWordWrap(True)
        self.errorbar_info_label.setStyleSheet("color: #888; font-style: italic;")
        error_layout.addWidget(self.errorbar_info_label, 3, 0, 1, 2)

        # Capsize (Breite der Endkappen) - nur für 'bars'
        self.errorbar_capsize_label = QLabel(tr("curve_settings.error_bars.cap_size"))
        error_layout.addWidget(self.errorbar_capsize_label, 3, 0)
        self.errorbar_capsize_spin = QDoubleSpinBox()
        self.errorbar_capsize_spin.setRange(0, 10)
        self.errorbar_capsize_spin.setSingleStep(0.5)
        self.errorbar_capsize_spin.setValue(getattr(dataset, 'errorbar_capsize', 3))
        error_layout.addWidget(self.errorbar_capsize_spin, 3, 1)

        # Transparenz
        self.errorbar_alpha_label = QLabel(tr("curve_settings.error_bars.transparency"))
        error_layout.addWidget(self.errorbar_alpha_label, 4, 0)
        self.errorbar_alpha_spin = QDoubleSpinBox()
        self.errorbar_alpha_spin.setRange(0, 1)
        self.errorbar_alpha_spin.setSingleStep(0.1)
        self.errorbar_alpha_spin.setValue(getattr(dataset, 'errorbar_alpha', 0.3))
        error_layout.addWidget(self.errorbar_alpha_spin, 4, 1)

        # Linienbreite der Fehlerbalken - nur für 'bars'
        self.errorbar_linewidth_label = QLabel(tr("curve_settings.error_bars.line_width"))
        error_layout.addWidget(self.errorbar_linewidth_label, 5, 0)
        self.errorbar_linewidth_spin = QDoubleSpinBox()
        self.errorbar_linewidth_spin.setRange(0.1, 5)
        self.errorbar_linewidth_spin.setSingleStep(0.1)
        self.errorbar_linewidth_spin.setValue(getattr(dataset, 'errorbar_linewidth', 1.0))
        error_layout.addWidget(self.errorbar_linewidth_spin, 5, 1)

        # Transparenz
        self.errorbar_alpha_label = QLabel("Transparenz:")
        error_layout.addWidget(self.errorbar_alpha_label, 6, 0)
        self.errorbar_alpha_spin = QDoubleSpinBox()
        self.errorbar_alpha_spin.setRange(0, 1)
        self.errorbar_alpha_spin.setSingleStep(0.1)
        self.errorbar_alpha_spin.setValue(getattr(dataset, 'errorbar_alpha', 0.3))
        error_layout.addWidget(self.errorbar_alpha_spin, 6, 1)

        error_group.setLayout(error_layout)
        layout.addWidget(error_group)

        # Initial errorbar settings aktivieren/deaktivieren
        self.toggle_errorbar_settings()

        # === BUTTONS ===
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def update_color_preview(self):
        """Aktualisiert die Farbvorschau"""
        if self.selected_color:
            self.color_preview.setStyleSheet(
                f"background-color: {self.selected_color}; border: 2px solid #888;"
            )
        else:
            self.color_preview.setStyleSheet(
                "background-color: #CCCCCC; border: 2px solid #888;"
            )

    def open_color_picker(self):
        """Öffnet den Farbwähler-Dialog"""
        initial_color = QColor(self.selected_color) if self.selected_color else QColor(Qt.blue)
        color = QColorDialog.getColor(initial_color, self, "Farbe wählen")

        if color.isValid():
            self.selected_color = color.name()
            self.update_color_preview()

    def set_quick_color(self, color):
        """Setzt eine Schnellfarbe aus der Palette"""
        self.selected_color = color
        self.update_color_preview()

    def reset_color(self):
        """Setzt die Farbe auf Auto (None) zurück"""
        self.selected_color = None
        self.update_color_preview()

    def toggle_errorbar_settings(self):
        """Aktiviert/Deaktiviert Errorbar-Settings basierend auf Checkbox"""
        enabled = self.show_errorbars_check.isChecked()

        # Checkbox bei fehlenden Fehlerdaten nur für stem-Plot aktivieren
        style = self.errorbar_style_combo.currentData()
        has_errors = self.dataset.y_err is not None
        if not has_errors and style != 'stem':
            self.show_errorbars_check.setEnabled(False)
        else:
            self.show_errorbars_check.setEnabled(True)

        self.errorbar_style_combo.setEnabled(enabled)
        self.errorbar_capsize_spin.setEnabled(enabled)
        self.errorbar_alpha_spin.setEnabled(enabled)
        self.errorbar_linewidth_spin.setEnabled(enabled)
        # UI für den gewählten Stil aktualisieren
        if enabled:
            self.update_errorbar_ui()
        self.update_marker_info()

    def update_errorbar_ui(self):
        """Aktualisiert UI basierend auf gewähltem Fehlerbalken-Stil"""
        style = self.errorbar_style_combo.currentData()

        # Info-Text je nach Stil
        if style == 'fill':
            self.errorbar_info_label.setText(
                "Zeigt Fehler als transparente Fläche um die Kurve. Ideal für kontinuierliche Messungen. "
                "Benötigt Fehlerdaten in der Datei."
            )
        elif style == 'bars':
            self.errorbar_info_label.setText(
                "Zeigt Fehler als Balken mit Endkappen. Klassische Darstellung für diskrete Messpunkte. "
                "Benötigt Fehlerdaten in der Datei."
            )
        elif style == 'stem':
            self.errorbar_info_label.setText(
                "Zeigt jeden Datenpunkt als vertikale Linie (Ankerlinie) von der x-Achse. "
                "Ideal für XRD-Reflexmuster aus PDF-Datenbanken. Benötigt keine Fehlerdaten."
            )

        is_bars = (style == 'bars')
        is_stem = (style == 'stem')
        is_fill = (style == 'fill')

        # Cap-Größe nur bei 'bars' relevant
        self.errorbar_capsize_label.setVisible(is_bars)
        self.errorbar_capsize_spin.setVisible(is_bars)

        # Linienbreite bei 'bars' und 'stem' relevant
        self.errorbar_linewidth_label.setVisible(is_bars or is_stem)
        self.errorbar_linewidth_spin.setVisible(is_bars or is_stem)

        # Beschriftung für Linienbreite anpassen
        if is_stem:
            self.errorbar_linewidth_label.setText("Ankerlinien-Breite:")
        else:
            self.errorbar_linewidth_label.setText("Linienbreite:")

        # Transparenz immer sichtbar, aber Beschriftung anpassen
        if is_bars:
            self.errorbar_alpha_label.setText("Transparenz (Balken):")
        elif is_stem:
            self.errorbar_alpha_label.setText("Transparenz (Linien):")
        else:  # fill
            self.errorbar_alpha_label.setText("Transparenz (Fläche):")

        # Marker-Hinweis aktualisieren
        self.update_marker_info()

    def update_marker_info(self):
        """Zeigt Hinweis für Marker-Einstellungen bei stem-Plots und passt Checkbox-Text an"""
        if not self.show_errorbars_check.isChecked():
            self.marker_info_label.setVisible(False)
            return

        style = self.errorbar_style_combo.currentData()

        # Checkbox-Beschriftung anpassen
        if style == 'stem':
            self.show_errorbars_check.setText("Ankerlinien-Darstellung aktivieren")
            self.marker_info_label.setText(
                "💡 Hinweis: Bei Ankerlinien sind die Marker-Einstellungen besonders wichtig!"
            )
            self.marker_info_label.setVisible(True)
        elif style == 'fill' or style == 'bars':
            self.show_errorbars_check.setText("Fehlerbalken anzeigen")
            self.marker_info_label.setVisible(False)
        else:
            self.show_errorbars_check.setText("Spezielle Darstellung verwenden")
            self.marker_info_label.setVisible(False)

    def get_settings(self):
        """Gibt alle Einstellungen als Dictionary zurück"""
        return {
            'color': self.selected_color,
            'marker_style': self.marker_combo.currentData(),
            'marker_size': self.marker_size_spin.value(),
            'line_style': self.line_combo.currentData(),
            'line_width': self.line_width_spin.value(),
            'show_errorbars': self.show_errorbars_check.isChecked(),
            'errorbar_style': self.errorbar_style_combo.currentData(),
            'errorbar_capsize': self.errorbar_capsize_spin.value(),
            'errorbar_alpha': self.errorbar_alpha_spin.value(),
            'errorbar_linewidth': self.errorbar_linewidth_spin.value(),
        }
