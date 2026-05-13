"""
Curve Settings Dialog

Umfassender Dialog zur Bearbeitung aller Kurveneinstellungen:
- Farbe (Picker + Schnellauswahl aus aktueller Palette)
- Marker (Stil, Größe)
- Linie (Stil, Breite)
- Fehlerbalken (Anzeige, Stil, Transparenz, Caps, Linienbreite)
- Datenqualität (SNR-Qualitätsmarker)
- Plotbereich (Subplot-Routing, nur bei Gruppen)
- ASAXS Term-Typ

Kann auch im 'preset_mode' betrieben werden — dann wird eine Stil-Vorlage
bearbeitet statt eines konkreten Datensatzes:
  - Farb-Abschnitt wird ausgeblendet
  - ASAXS- und Plotbereich-Abschnitte werden ausgeblendet
  - Name + Beschreibung der Vorlage editierbar
  - SNR-Einstellungen immer verfügbar (keine Fehlerdaten-Prüfung)
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QDialogButtonBox, QCheckBox, QPushButton,
    QComboBox, QSpinBox, QDoubleSpinBox, QColorDialog, QFrame, QWidget,
    QScrollArea, QSizePolicy, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from i18n import tr


class CurveSettingsDialog(QDialog):
    """Dialog zur umfassenden Bearbeitung von Kurveneinstellungen.

    Kann auch als Stil-Vorlagen-Editor verwendet werden (preset_mode=True).
    """

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

    def __init__(self, parent, dataset, current_color_scheme=None,
                 color_schemes=None, group=None, preset_mode=False):
        """
        Args:
            parent: Parent Widget
            dataset: DataSet-Objekt (oder SimpleNamespace im preset_mode)
            current_color_scheme: Name der aktuellen Farbpalette
            color_schemes: Dict mit allen verfügbaren Farbpaletten
            group: Optionales DataGroup-Objekt für den 'Plotbereich'-Abschnitt.
            preset_mode: True = Stil-Vorlagen-Modus (kein Farb-/ASAXS-Abschnitt,
                         Name + Beschreibung editierbar, SNR immer verfügbar).
        """
        super().__init__(parent)
        self.dataset = dataset
        self.group = group
        self.preset_mode = preset_mode
        self.current_color_scheme = current_color_scheme
        self.color_schemes = color_schemes or {}
        self.selected_color = getattr(dataset, 'color', None)

        # Fenstertitel
        if preset_mode:
            self.setWindowTitle(tr("curve_settings.preset_title", name=dataset.name))
        else:
            self.setWindowTitle(tr("curve_settings.title", dataset=dataset.name))

        self.resize(600, 700)

        # Scrollbarer Inhalt
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setSpacing(8)

        outer_layout = QVBoxLayout(self)
        outer_layout.addWidget(scroll)

        # Info-Label
        if preset_mode:
            info_text = tr("curve_settings.preset_info")
        else:
            info_text = tr("curve_settings.info")
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #aaa; font-style: italic;")
        layout.addWidget(info_label)

        # ── VORLAGE (nur preset_mode) ──────────────────────────────────────
        if preset_mode:
            meta_group = QGroupBox(tr("curve_settings.preset_meta.title"))
            meta_layout = QGridLayout()

            meta_layout.addWidget(QLabel(tr("curve_settings.preset_meta.name")), 0, 0)
            self.preset_name_edit = QLineEdit(dataset.name)
            meta_layout.addWidget(self.preset_name_edit, 0, 1)

            meta_layout.addWidget(QLabel(tr("curve_settings.preset_meta.description")), 1, 0)
            self.preset_desc_edit = QLineEdit(getattr(dataset, '_description', ''))
            meta_layout.addWidget(self.preset_desc_edit, 1, 1)

            meta_group.setLayout(meta_layout)
            layout.addWidget(meta_group)
        else:
            self.preset_name_edit = None
            self.preset_desc_edit = None

        # ── FARBE (nicht im preset_mode) ──────────────────────────────────
        if not preset_mode:
            color_group = QGroupBox(tr("curve_settings.color.title"))
            color_layout = QVBoxLayout()

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

            if current_color_scheme and current_color_scheme in self.color_schemes:
                palette_colors = self.color_schemes[current_color_scheme]
                color_layout.addWidget(QLabel(
                    tr("curve_settings.color.quick_selection", scheme=current_color_scheme)))
                quick_colors_layout = QGridLayout()
                for i, color in enumerate(palette_colors[:10]):
                    btn = QPushButton()
                    btn.setFixedSize(40, 30)
                    btn.setStyleSheet(f"background-color: {color}; border: 2px solid #888;")
                    btn.clicked.connect(lambda checked, c=color: self.set_quick_color(c))
                    quick_colors_layout.addWidget(btn, i // 5, i % 5)
                color_layout.addLayout(quick_colors_layout)

            reset_color_btn = QPushButton(tr("curve_settings.color.reset"))
            reset_color_btn.clicked.connect(self.reset_color)
            color_layout.addWidget(reset_color_btn)

            color_group.setLayout(color_layout)
            layout.addWidget(color_group)

        # ── MARKER ────────────────────────────────────────────────────────
        marker_group = QGroupBox(tr("curve_settings.marker.title"))
        marker_layout = QGridLayout()

        marker_layout.addWidget(QLabel(tr("curve_settings.marker.style")), 0, 0)
        self.marker_combo = QComboBox()
        marker_styles = self.get_marker_styles()
        for name, style in marker_styles.items():
            self.marker_combo.addItem(name, style)
        current_marker = getattr(dataset, 'marker_style', '') or ''
        for i, (name, style) in enumerate(marker_styles.items()):
            if style == current_marker:
                self.marker_combo.setCurrentIndex(i)
                break
        marker_layout.addWidget(self.marker_combo, 0, 1)

        marker_layout.addWidget(QLabel(tr("curve_settings.marker.size")), 1, 0)
        self.marker_size_spin = QDoubleSpinBox()
        self.marker_size_spin.setRange(0, 20)
        self.marker_size_spin.setSingleStep(0.5)
        self.marker_size_spin.setValue(float(getattr(dataset, 'marker_size', 4)))
        marker_layout.addWidget(self.marker_size_spin, 1, 1)

        self.marker_info_label = QLabel()
        self.marker_info_label.setWordWrap(True)
        self.marker_info_label.setStyleSheet("color: #0066cc; font-style: italic;")
        self.marker_info_label.setVisible(False)
        marker_layout.addWidget(self.marker_info_label, 2, 0, 1, 2)

        marker_group.setLayout(marker_layout)
        layout.addWidget(marker_group)

        # ── LINIE ─────────────────────────────────────────────────────────
        line_group = QGroupBox(tr("curve_settings.line.title"))
        line_layout = QGridLayout()

        line_layout.addWidget(QLabel(tr("curve_settings.line.style")), 0, 0)
        self.line_combo = QComboBox()
        line_styles = self.get_line_styles()
        for name, style in line_styles.items():
            self.line_combo.addItem(name, style)
        current_line = getattr(dataset, 'line_style', '') or ''
        for i, (name, style) in enumerate(line_styles.items()):
            if style == current_line:
                self.line_combo.setCurrentIndex(i)
                break
        line_layout.addWidget(self.line_combo, 0, 1)

        line_layout.addWidget(QLabel(tr("curve_settings.line.width")), 1, 0)
        self.line_width_spin = QDoubleSpinBox()
        self.line_width_spin.setRange(0, 10)
        self.line_width_spin.setSingleStep(0.5)
        self.line_width_spin.setValue(float(getattr(dataset, 'line_width', 2.0)))
        line_layout.addWidget(self.line_width_spin, 1, 1)

        line_group.setLayout(line_layout)
        layout.addWidget(line_group)

        # ── FEHLERBALKEN ──────────────────────────────────────────────────
        has_errors = preset_mode or (getattr(dataset, 'y_err', None) is not None)

        error_group = QGroupBox(tr("curve_settings.error_bars.title"))
        error_layout = QGridLayout()

        self.show_errorbars_check = QCheckBox(tr("curve_settings.error_bars.show"))
        self.show_errorbars_check.setChecked(getattr(dataset, 'show_errorbars', True))
        self.show_errorbars_check.stateChanged.connect(self.toggle_errorbar_settings)
        error_layout.addWidget(self.show_errorbars_check, 0, 0, 1, 2)

        # Verfügbarkeits-Info (nicht im preset_mode)
        if not preset_mode:
            self.error_info = QLabel()
            if has_errors:
                self.error_info.setText(tr("curve_settings.error_bars.available"))
                self.error_info.setStyleSheet("color: green;")
            else:
                self.error_info.setText(tr("curve_settings.error_bars.not_available"))
                self.error_info.setStyleSheet("color: #888;")
                self.show_errorbars_check.setEnabled(False)
            error_layout.addWidget(self.error_info, 1, 0, 1, 2)

        # Fehlerbalken-Stil
        error_layout.addWidget(QLabel(tr("curve_settings.error_bars.representation")), 2, 0)
        self.errorbar_style_combo = QComboBox()
        self.errorbar_style_combo.addItem(tr("curve_settings.error_bars.fill"), "fill")
        self.errorbar_style_combo.addItem(tr("curve_settings.error_bars.bars"), "bars")
        if not preset_mode:
            # Stem nur für echte Datensätze (nicht für Stil-Vorlagen)
            self.errorbar_style_combo.addItem("Stem / Anker", "stem")
        current_style = getattr(dataset, 'errorbar_style', 'fill')
        for i in range(self.errorbar_style_combo.count()):
            if self.errorbar_style_combo.itemData(i) == current_style:
                self.errorbar_style_combo.setCurrentIndex(i)
                break
        self.errorbar_style_combo.currentIndexChanged.connect(self.update_errorbar_ui)
        error_layout.addWidget(self.errorbar_style_combo, 2, 1)

        # Info-Text
        self.errorbar_info_label = QLabel()
        self.errorbar_info_label.setWordWrap(True)
        self.errorbar_info_label.setStyleSheet("color: #888; font-style: italic;")
        error_layout.addWidget(self.errorbar_info_label, 3, 0, 1, 2)

        # Cap-Größe
        self.errorbar_capsize_label = QLabel(tr("curve_settings.error_bars.cap_size"))
        error_layout.addWidget(self.errorbar_capsize_label, 4, 0)
        self.errorbar_capsize_spin = QDoubleSpinBox()
        self.errorbar_capsize_spin.setRange(0, 10)
        self.errorbar_capsize_spin.setSingleStep(0.5)
        self.errorbar_capsize_spin.setValue(float(getattr(dataset, 'errorbar_capsize', 3.0)))
        error_layout.addWidget(self.errorbar_capsize_spin, 4, 1)

        # Linienbreite
        self.errorbar_linewidth_label = QLabel(tr("curve_settings.error_bars.line_width"))
        error_layout.addWidget(self.errorbar_linewidth_label, 5, 0)
        self.errorbar_linewidth_spin = QDoubleSpinBox()
        self.errorbar_linewidth_spin.setRange(0.1, 5)
        self.errorbar_linewidth_spin.setSingleStep(0.1)
        self.errorbar_linewidth_spin.setValue(float(getattr(dataset, 'errorbar_linewidth', 1.0)))
        error_layout.addWidget(self.errorbar_linewidth_spin, 5, 1)

        # Transparenz
        self.errorbar_alpha_label = QLabel(tr("curve_settings.error_bars.transparency"))
        error_layout.addWidget(self.errorbar_alpha_label, 6, 0)
        self.errorbar_alpha_spin = QDoubleSpinBox()
        self.errorbar_alpha_spin.setRange(0, 1)
        self.errorbar_alpha_spin.setSingleStep(0.1)
        self.errorbar_alpha_spin.setDecimals(2)
        self.errorbar_alpha_spin.setValue(float(getattr(dataset, 'errorbar_alpha', 0.3)))
        error_layout.addWidget(self.errorbar_alpha_spin, 6, 1)

        error_group.setLayout(error_layout)
        layout.addWidget(error_group)

        # Initial errorbar settings aktivieren/deaktivieren
        self.toggle_errorbar_settings()

        # ── DATENQUALITÄT (SNR-Visualisierung) ────────────────────────────
        quality_group = QGroupBox(tr("curve_settings.quality.title"))
        quality_layout = QVBoxLayout()

        self.snr_viz_check = QCheckBox(tr("curve_settings.quality.snr_show"))
        self.snr_viz_check.setChecked(getattr(dataset, 'snr_visualization', False))
        if has_errors:
            self.snr_viz_check.setToolTip(tr("curve_settings.quality.snr_tooltip"))
        else:
            self.snr_viz_check.setEnabled(False)
            self.snr_viz_check.setToolTip(tr("curve_settings.quality.snr_tooltip_unavailable"))
        quality_layout.addWidget(self.snr_viz_check)

        # SNR-Untereinstellungen
        self.snr_detail_widget = QWidget()
        snr_detail_layout = QGridLayout(self.snr_detail_widget)
        snr_detail_layout.setContentsMargins(16, 4, 4, 4)

        marker_values = list(marker_styles.values())

        snr_detail_layout.addWidget(QLabel(tr("curve_settings.quality.snr_threshold")), 0, 0)
        self.snr_threshold_spin = QDoubleSpinBox()
        self.snr_threshold_spin.setRange(0.1, 20.0)
        self.snr_threshold_spin.setSingleStep(0.1)
        self.snr_threshold_spin.setDecimals(1)
        self.snr_threshold_spin.setValue(float(getattr(dataset, 'snr_threshold', 1.0)))
        self.snr_threshold_spin.setToolTip(tr("curve_settings.quality.snr_threshold_tooltip"))
        snr_detail_layout.addWidget(self.snr_threshold_spin, 0, 1)

        snr_detail_layout.addWidget(QLabel(tr("curve_settings.quality.snr_good_marker")), 1, 0)
        self.snr_good_marker_combo = QComboBox()
        for n, v in marker_styles.items():
            self.snr_good_marker_combo.addItem(n, v)
        good_val = getattr(dataset, 'snr_good_marker', 'o')
        for i, v in enumerate(marker_values):
            if v == good_val:
                self.snr_good_marker_combo.setCurrentIndex(i)
                break
        snr_detail_layout.addWidget(self.snr_good_marker_combo, 1, 1)

        snr_detail_layout.addWidget(QLabel(tr("curve_settings.quality.snr_poor_marker")), 2, 0)
        self.snr_poor_marker_combo = QComboBox()
        for n, v in marker_styles.items():
            self.snr_poor_marker_combo.addItem(n, v)
        poor_val = getattr(dataset, 'snr_poor_marker', '^')
        for i, v in enumerate(marker_values):
            if v == poor_val:
                self.snr_poor_marker_combo.setCurrentIndex(i)
                break
        snr_detail_layout.addWidget(self.snr_poor_marker_combo, 2, 1)

        snr_detail_layout.addWidget(QLabel(tr("curve_settings.quality.snr_poor_alpha")), 3, 0)
        self.snr_poor_alpha_spin = QDoubleSpinBox()
        self.snr_poor_alpha_spin.setRange(0.0, 1.0)
        self.snr_poor_alpha_spin.setSingleStep(0.05)
        self.snr_poor_alpha_spin.setDecimals(2)
        self.snr_poor_alpha_spin.setValue(float(getattr(dataset, 'snr_poor_alpha', 0.3)))
        snr_detail_layout.addWidget(self.snr_poor_alpha_spin, 3, 1)

        snr_detail_layout.addWidget(QLabel(tr("curve_settings.quality.snr_errorbars")), 4, 0)
        self.snr_errorbars_check = QCheckBox()
        self.snr_errorbars_check.setChecked(getattr(dataset, 'snr_show_errorbars', True))
        self.snr_errorbars_check.setToolTip(tr("curve_settings.quality.snr_errorbars_tooltip"))
        snr_detail_layout.addWidget(self.snr_errorbars_check, 4, 1)

        quality_layout.addWidget(self.snr_detail_widget)
        quality_group.setLayout(quality_layout)
        layout.addWidget(quality_group)

        self.snr_detail_widget.setVisible(self.snr_viz_check.isChecked())
        self.snr_viz_check.toggled.connect(self.snr_detail_widget.setVisible)

        # ── PLOTBEREICH (nur bei Gruppen-Bearbeitung, nicht im preset_mode) ──
        if self.group is not None and not preset_mode:
            subplot_group = QGroupBox(tr("curve_settings.subplot.title"))
            subplot_layout = QGridLayout()

            subplot_layout.addWidget(QLabel(tr("curve_settings.subplot.show_in")), 0, 0)
            self.subplot_target_combo = QComboBox()
            self.subplot_target_combo.addItem(tr("curve_settings.subplot.both"), "both")
            self.subplot_target_combo.addItem(tr("curve_settings.subplot.main"), "main")
            self.subplot_target_combo.addItem(tr("curve_settings.subplot.sub"), "sub")
            current_target = getattr(self.group, 'subplot_target', 'both')
            for i in range(self.subplot_target_combo.count()):
                if self.subplot_target_combo.itemData(i) == current_target:
                    self.subplot_target_combo.setCurrentIndex(i)
                    break
            self.subplot_target_combo.setToolTip(tr("curve_settings.subplot.tooltip"))
            subplot_layout.addWidget(self.subplot_target_combo, 0, 1)

            subplot_group.setLayout(subplot_layout)
            layout.addWidget(subplot_group)
        else:
            self.subplot_target_combo = None

        # ── ASAXS (nicht im preset_mode) ──────────────────────────────────
        if not preset_mode:
            asaxs_group = QGroupBox(tr("curve_settings.asaxs.title"))
            asaxs_layout = QGridLayout()

            asaxs_layout.addWidget(QLabel(tr("curve_settings.asaxs.term_type")), 0, 0)
            self.asaxs_term_combo = QComboBox()
            self.asaxs_term_combo.addItem(tr("curve_settings.asaxs.none"), "")
            self.asaxs_term_combo.addItem(tr("curve_settings.asaxs.normal"), "normal")
            self.asaxs_term_combo.addItem(tr("curve_settings.asaxs.cross"), "cross")
            self.asaxs_term_combo.addItem(tr("curve_settings.asaxs.anomalous"), "anomalous")
            current_term = getattr(dataset, 'data_term', '')
            for i in range(self.asaxs_term_combo.count()):
                if self.asaxs_term_combo.itemData(i) == current_term:
                    self.asaxs_term_combo.setCurrentIndex(i)
                    break
            asaxs_layout.addWidget(self.asaxs_term_combo, 0, 1)

            asaxs_group.setLayout(asaxs_layout)
            layout.addWidget(asaxs_group)
        else:
            self.asaxs_term_combo = None

        # ── BUTTONS ───────────────────────────────────────────────────────
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        outer_layout.addWidget(buttons)

        # Initiale UI-Aktualisierung
        self.update_errorbar_ui()

    # ── Farb-Hilfsmethoden ────────────────────────────────────────────────

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
        color = QColorDialog.getColor(initial_color, self, tr("curve_settings.color.picker"))
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

    # ── Fehlerbalken UI ───────────────────────────────────────────────────

    def toggle_errorbar_settings(self):
        """Aktiviert/Deaktiviert Errorbar-Settings basierend auf Checkbox"""
        enabled = self.show_errorbars_check.isChecked()

        if not self.preset_mode:
            style = self.errorbar_style_combo.currentData()
            has_errors = getattr(self.dataset, 'y_err', None) is not None
            if not has_errors and style != 'stem':
                self.show_errorbars_check.setEnabled(False)
            else:
                self.show_errorbars_check.setEnabled(True)

        self.errorbar_style_combo.setEnabled(enabled)
        self.errorbar_capsize_spin.setEnabled(enabled)
        self.errorbar_alpha_spin.setEnabled(enabled)
        self.errorbar_linewidth_spin.setEnabled(enabled)
        if enabled:
            self.update_errorbar_ui()
        self.update_marker_info()

    def update_errorbar_ui(self):
        """Aktualisiert UI basierend auf gewähltem Fehlerbalken-Stil"""
        style = self.errorbar_style_combo.currentData()

        # Info-Text je nach Stil
        if style == 'fill':
            self.errorbar_info_label.setText(tr("curve_settings.error_bars.info_fill"))
        elif style == 'bars':
            self.errorbar_info_label.setText(tr("curve_settings.error_bars.info_bars"))
        elif style == 'stem':
            self.errorbar_info_label.setText(tr("curve_settings.error_bars.info_stem"))
        else:
            self.errorbar_info_label.setText("")

        is_bars = (style == 'bars')
        is_stem = (style == 'stem')

        # Cap-Größe nur bei 'bars' relevant
        self.errorbar_capsize_label.setVisible(is_bars)
        self.errorbar_capsize_spin.setVisible(is_bars)

        # Linienbreite bei 'bars' und 'stem' relevant
        self.errorbar_linewidth_label.setVisible(is_bars or is_stem)
        self.errorbar_linewidth_spin.setVisible(is_bars or is_stem)

        if is_stem:
            self.errorbar_linewidth_label.setText(tr("curve_settings.error_bars.line_width_stem"))
        else:
            self.errorbar_linewidth_label.setText(tr("curve_settings.error_bars.line_width"))

        # Transparenz-Label je nach Stil
        if is_bars:
            self.errorbar_alpha_label.setText(tr("curve_settings.error_bars.transparency_bars"))
        elif is_stem:
            self.errorbar_alpha_label.setText(tr("curve_settings.error_bars.transparency_stem"))
        else:
            self.errorbar_alpha_label.setText(tr("curve_settings.error_bars.transparency_fill"))

        self.update_marker_info()

    def update_marker_info(self):
        """Zeigt Hinweis für Marker-Einstellungen bei stem-Plots"""
        if not self.show_errorbars_check.isChecked():
            self.marker_info_label.setVisible(False)
            return

        style = self.errorbar_style_combo.currentData()
        if style == 'stem':
            self.show_errorbars_check.setText(tr("curve_settings.error_bars.stem_show"))
            self.marker_info_label.setText(tr("curve_settings.error_bars.stem_hint"))
            self.marker_info_label.setVisible(True)
        else:
            self.show_errorbars_check.setText(tr("curve_settings.error_bars.show"))
            self.marker_info_label.setVisible(False)

    # ── Validierung & Accept ──────────────────────────────────────────────

    def _on_accept(self):
        """Validiert im preset_mode den Namen vor dem Schließen"""
        if self.preset_mode and self.preset_name_edit is not None:
            if not self.preset_name_edit.text().strip():
                QMessageBox.critical(
                    self, "Fehler",
                    tr("curve_settings.preset_meta.name_required")
                )
                return
        self.accept()

    # ── Einstellungen auslesen ────────────────────────────────────────────

    def get_settings(self):
        """Gibt alle Einstellungen als Dictionary zurück"""
        result = {
            'marker_style': self.marker_combo.currentData(),
            'marker_size': self.marker_size_spin.value(),
            'line_style': self.line_combo.currentData(),
            'line_width': self.line_width_spin.value(),
            'show_errorbars': self.show_errorbars_check.isChecked(),
            'errorbar_style': self.errorbar_style_combo.currentData(),
            'errorbar_capsize': self.errorbar_capsize_spin.value(),
            'errorbar_alpha': self.errorbar_alpha_spin.value(),
            'errorbar_linewidth': self.errorbar_linewidth_spin.value(),
            'snr_visualization': self.snr_viz_check.isChecked(),
            'snr_threshold': self.snr_threshold_spin.value(),
            'snr_good_marker': self.snr_good_marker_combo.currentData(),
            'snr_poor_marker': self.snr_poor_marker_combo.currentData(),
            'snr_poor_alpha': self.snr_poor_alpha_spin.value(),
            'snr_show_errorbars': self.snr_errorbars_check.isChecked(),
        }

        if self.preset_mode:
            # Preset-spezifische Felder
            result['preset_name'] = (
                self.preset_name_edit.text().strip()
                if self.preset_name_edit is not None else self.dataset.name
            )
            result['preset_description'] = (
                self.preset_desc_edit.text()
                if self.preset_desc_edit is not None else ''
            )
        else:
            # Datensatz-spezifische Felder
            result['color'] = self.selected_color
            result['data_term'] = (
                self.asaxs_term_combo.currentData()
                if self.asaxs_term_combo is not None else ''
            )
            result['subplot_target'] = (
                self.subplot_target_combo.currentData()
                if self.subplot_target_combo is not None else None
            )

        return result
