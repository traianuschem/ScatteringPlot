"""
Axes Settings Dialog

This dialog allows users to configure axis labels and titles.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QDialogButtonBox, QCheckBox, QPushButton, QMessageBox, QHBoxLayout,
    QSpinBox, QDoubleSpinBox, QFontComboBox, QComboBox
)
from utils.mathtext_formatter import get_syntax_help_text, preprocess_mathtext
from i18n import tr


class AxesSettingsDialog(QDialog):
    """Dialog für Achsen-Einstellungen"""

    def __init__(self, parent, current_xlabel=None, current_ylabel=None, plot_type='Log-Log', axis_limits=None,
                 font_settings=None, subplot_kind=None, sub_axis_limits=None, sub_default_ylabel=''):
        super().__init__(parent)
        self.setWindowTitle(tr("axes.title"))
        self.resize(650, 900)

        # Font settings initialisieren
        if font_settings is None:
            font_settings = {}
        self.font_settings = font_settings

        self.plot_type = plot_type

        # v7.7: Subplot-Achse (PDDF P(r) / ASAXS-Cross-Term / Significance)
        # 'PDDF', 'ASAXS', 'Significance' oder None (aktueller Plot-Typ hat keinen Subplot)
        self.subplot_kind = subplot_kind
        if sub_axis_limits is None:
            sub_axis_limits = {'xlabel': None, 'ylabel': None,
                                'xmin': None, 'xmax': None, 'ymin': None, 'ymax': None,
                                'auto': True, 'yscale': None}
        # Unveränderte Kopie: wird zurückgegeben, wenn kein Subplot aktiv ist (die
        # zugehörigen Widgets werden dann gar nicht erst in die UI eingebaut).
        self._sub_axis_limits_original = dict(sub_axis_limits)
        self.sub_default_ylabel = sub_default_ylabel

        layout = QVBoxLayout(self)

        # Info
        info_label = QLabel(tr("axes.info"))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Achsentitel-Gruppe
        titles_group = QGroupBox(tr("axes.axis_titles.title"))
        titles_layout = QGridLayout()

        # X-Achsentitel
        titles_layout.addWidget(QLabel(tr("axes.axis_titles.x_title")), 0, 0)
        self.xlabel_edit = QLineEdit()
        self.xlabel_edit.setPlaceholderText(tr("axes.axis_titles.auto_based_on", plot_type=plot_type))
        if current_xlabel:
            self.xlabel_edit.setText(current_xlabel)
        titles_layout.addWidget(self.xlabel_edit, 0, 1)

        # Y-Achsentitel
        titles_layout.addWidget(QLabel(tr("axes.axis_titles.y_title")), 1, 0)
        self.ylabel_edit = QLineEdit()
        self.ylabel_edit.setPlaceholderText(tr("axes.axis_titles.auto_based_on", plot_type=plot_type))
        if current_ylabel:
            self.ylabel_edit.setText(current_ylabel)
        titles_layout.addWidget(self.ylabel_edit, 1, 1)

        # Syntax-Hilfe Button (v7.0)
        syntax_help_btn = QPushButton(tr("axes.axis_titles.latex_help"))
        syntax_help_btn.clicked.connect(self.show_syntax_help)
        titles_layout.addWidget(syntax_help_btn, 2, 0, 1, 2)

        # Vorschau (v7.0)
        titles_layout.addWidget(QLabel(tr("axes.axis_titles.preview")), 3, 0)
        self.preview_label = QLabel("")
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet(
            "background-color: #2b2b2b; "
            "padding: 8px; "
            "border: 1px solid #555; "
            "border-radius: 4px; "
            "min-height: 40px;"
        )
        titles_layout.addWidget(self.preview_label, 3, 1)

        # Connect signals AFTER all UI elements are created
        self.xlabel_edit.textChanged.connect(self.update_preview)
        self.ylabel_edit.textChanged.connect(self.update_preview)

        titles_group.setLayout(titles_layout)
        layout.addWidget(titles_group)

        # Achsenlimits-Gruppe
        limits_group = QGroupBox(tr("axes.limits.title"))
        limits_layout = QGridLayout()

        # Info-Label
        limits_info = QLabel(tr("axes.limits.info"))
        limits_info.setWordWrap(True)
        limits_layout.addWidget(limits_info, 0, 0, 1, 2)

        # Initialisiere axis_limits falls nicht vorhanden
        if axis_limits is None:
            axis_limits = {'xmin': None, 'xmax': None, 'ymin': None, 'ymax': None, 'auto': True}

        # X-Limits
        limits_layout.addWidget(QLabel(tr("axes.limits.x_min")), 1, 0)
        self.xmin_edit = QLineEdit()
        self.xmin_edit.setPlaceholderText(tr("axes.limits.placeholder", value="0.001"))
        if axis_limits.get('xmin') is not None:
            self.xmin_edit.setText(str(axis_limits['xmin']))
        limits_layout.addWidget(self.xmin_edit, 1, 1)

        limits_layout.addWidget(QLabel(tr("axes.limits.x_max")), 2, 0)
        self.xmax_edit = QLineEdit()
        self.xmax_edit.setPlaceholderText(tr("axes.limits.placeholder", value="10.0"))
        if axis_limits.get('xmax') is not None:
            self.xmax_edit.setText(str(axis_limits['xmax']))
        limits_layout.addWidget(self.xmax_edit, 2, 1)

        # Y-Limits
        limits_layout.addWidget(QLabel(tr("axes.limits.y_min")), 3, 0)
        self.ymin_edit = QLineEdit()
        self.ymin_edit.setPlaceholderText(tr("axes.limits.placeholder", value="0.001"))
        if axis_limits.get('ymin') is not None:
            self.ymin_edit.setText(str(axis_limits['ymin']))
        limits_layout.addWidget(self.ymin_edit, 3, 1)

        limits_layout.addWidget(QLabel(tr("axes.limits.y_max")), 4, 0)
        self.ymax_edit = QLineEdit()
        self.ymax_edit.setPlaceholderText(tr("axes.limits.placeholder", value="1000.0"))
        if axis_limits.get('ymax') is not None:
            self.ymax_edit.setText(str(axis_limits['ymax']))
        limits_layout.addWidget(self.ymax_edit, 4, 1)

        # Auto-Modus Checkbox
        self.auto_checkbox = QCheckBox(tr("axes.limits.auto_scaling"))
        self.auto_checkbox.setChecked(axis_limits.get('auto', True))
        limits_layout.addWidget(self.auto_checkbox, 5, 0, 1, 2)

        # Y-Scale Override
        limits_layout.addWidget(QLabel(tr("axes.limits.y_scale")), 6, 0)
        self.yscale_combo = QComboBox()
        self.yscale_combo.addItem(tr("axes.limits.y_scale_auto"), userData=None)
        self.yscale_combo.addItem(tr("axes.limits.y_scale_linear"), userData='linear')
        self.yscale_combo.addItem(tr("axes.limits.y_scale_log"), userData='log')
        self.yscale_combo.addItem(tr("axes.limits.y_scale_symlog"), userData='symlog')
        # Pre-select from axis_limits
        yscale_val = axis_limits.get('yscale', None)
        if yscale_val == 'linear':
            self.yscale_combo.setCurrentIndex(1)
        elif yscale_val == 'log':
            self.yscale_combo.setCurrentIndex(2)
        elif yscale_val == 'symlog':
            self.yscale_combo.setCurrentIndex(3)
        else:
            self.yscale_combo.setCurrentIndex(0)
        limits_layout.addWidget(self.yscale_combo, 6, 1)

        # Symlog-Feinsteuerung (nur relevant und sichtbar, wenn Y-Skala = Symlog)
        self.symlog_decades_label = QLabel(tr("axes.limits.symlog_decades"))
        limits_layout.addWidget(self.symlog_decades_label, 7, 0)
        self.symlog_decades_spin = QSpinBox()
        self.symlog_decades_spin.setRange(1, 15)
        self.symlog_decades_spin.setValue(axis_limits.get('symlog_decades', 4) or 4)
        self.symlog_decades_spin.setToolTip(tr("axes.limits.symlog_decades_tooltip"))
        limits_layout.addWidget(self.symlog_decades_spin, 7, 1)

        self.symlog_linscale_label = QLabel(tr("axes.limits.symlog_linscale"))
        limits_layout.addWidget(self.symlog_linscale_label, 8, 0)
        self.symlog_linscale_spin = QDoubleSpinBox()
        self.symlog_linscale_spin.setRange(0.1, 10.0)
        self.symlog_linscale_spin.setSingleStep(0.1)
        self.symlog_linscale_spin.setValue(axis_limits.get('symlog_linscale', 1.0) or 1.0)
        self.symlog_linscale_spin.setToolTip(tr("axes.limits.symlog_linscale_tooltip"))
        limits_layout.addWidget(self.symlog_linscale_spin, 8, 1)

        self.yscale_combo.currentIndexChanged.connect(self._update_symlog_controls_visibility)
        self._update_symlog_controls_visibility()

        # Reset Limits Button
        reset_limits_btn = QPushButton(tr("axes.limits.reset"))
        reset_limits_btn.clicked.connect(self.reset_limits)
        limits_layout.addWidget(reset_limits_btn, 9, 0, 1, 2)

        limits_group.setLayout(limits_layout)
        layout.addWidget(limits_group)

        # Subplot-Achse (v7.7): PDDF P(r)-Plot, ASAXS-Cross-Term oder Significance
        subplot_group = QGroupBox(tr("axes.subplot.title"))
        subplot_layout = QGridLayout()
        row = 0

        # Immer anlegen (auch wenn versteckt), damit get_sub_axis_limits() konsistent bleibt
        self.sub_ylabel_edit = QLineEdit()
        self.sub_xlabel_edit = QLineEdit()
        self.sub_xmin_edit = QLineEdit()
        self.sub_xmax_edit = QLineEdit()
        self.sub_ymin_edit = QLineEdit()
        self.sub_ymax_edit = QLineEdit()
        self.sub_auto_checkbox = QCheckBox(tr("axes.subplot.auto_scaling"))
        self.sub_yscale_combo = QComboBox()

        if self.subplot_kind is None:
            no_subplot_label = QLabel(tr("axes.subplot.no_subplot"))
            no_subplot_label.setWordWrap(True)
            subplot_layout.addWidget(no_subplot_label, row, 0, 1, 2)
            row += 1
        else:
            info_key = 'info_pddf' if self.subplot_kind == 'PDDF' else 'info_shared_x'
            subplot_info = QLabel(tr(f"axes.subplot.{info_key}"))
            subplot_info.setWordWrap(True)
            subplot_layout.addWidget(subplot_info, row, 0, 1, 2)
            row += 1

            # Y-Achsentitel-Override
            subplot_layout.addWidget(QLabel(tr("axes.subplot.y_title")), row, 0)
            self.sub_ylabel_edit.setPlaceholderText(
                tr("axes.subplot.auto_based_on_default", default=self.sub_default_ylabel))
            if sub_axis_limits.get('ylabel'):
                self.sub_ylabel_edit.setText(sub_axis_limits['ylabel'])
            subplot_layout.addWidget(self.sub_ylabel_edit, row, 1)
            row += 1

            if self.subplot_kind == 'PDDF':
                # Unabhängige r-Achse: eigener Titel + eigene Limits möglich
                subplot_layout.addWidget(QLabel(tr("axes.subplot.x_title")), row, 0)
                self.sub_xlabel_edit.setPlaceholderText(
                    tr("axes.subplot.auto_based_on_default", default='r / nm'))
                if sub_axis_limits.get('xlabel'):
                    self.sub_xlabel_edit.setText(sub_axis_limits['xlabel'])
                subplot_layout.addWidget(self.sub_xlabel_edit, row, 1)
                row += 1

                subplot_layout.addWidget(QLabel(tr("axes.subplot.x_min")), row, 0)
                if sub_axis_limits.get('xmin') is not None:
                    self.sub_xmin_edit.setText(str(sub_axis_limits['xmin']))
                subplot_layout.addWidget(self.sub_xmin_edit, row, 1)
                row += 1

                subplot_layout.addWidget(QLabel(tr("axes.subplot.x_max")), row, 0)
                if sub_axis_limits.get('xmax') is not None:
                    self.sub_xmax_edit.setText(str(sub_axis_limits['xmax']))
                subplot_layout.addWidget(self.sub_xmax_edit, row, 1)
                row += 1

            # Y-Limits
            subplot_layout.addWidget(QLabel(tr("axes.subplot.y_min")), row, 0)
            if sub_axis_limits.get('ymin') is not None:
                self.sub_ymin_edit.setText(str(sub_axis_limits['ymin']))
            subplot_layout.addWidget(self.sub_ymin_edit, row, 1)
            row += 1

            subplot_layout.addWidget(QLabel(tr("axes.subplot.y_max")), row, 0)
            if sub_axis_limits.get('ymax') is not None:
                self.sub_ymax_edit.setText(str(sub_axis_limits['ymax']))
            subplot_layout.addWidget(self.sub_ymax_edit, row, 1)
            row += 1

            self.sub_auto_checkbox.setChecked(sub_axis_limits.get('auto', True))
            subplot_layout.addWidget(self.sub_auto_checkbox, row, 0, 1, 2)
            row += 1

            subplot_layout.addWidget(QLabel(tr("axes.subplot.y_scale")), row, 0)
            self.sub_yscale_combo.addItem(tr("axes.subplot.y_scale_auto"), userData=None)
            self.sub_yscale_combo.addItem(tr("axes.subplot.y_scale_linear"), userData='linear')
            self.sub_yscale_combo.addItem(tr("axes.subplot.y_scale_log"), userData='log')
            sub_yscale_val = sub_axis_limits.get('yscale', None)
            if sub_yscale_val == 'linear':
                self.sub_yscale_combo.setCurrentIndex(1)
            elif sub_yscale_val == 'log':
                self.sub_yscale_combo.setCurrentIndex(2)
            else:
                self.sub_yscale_combo.setCurrentIndex(0)
            subplot_layout.addWidget(self.sub_yscale_combo, row, 1)
            row += 1

            reset_sub_limits_btn = QPushButton(tr("axes.subplot.reset"))
            reset_sub_limits_btn.clicked.connect(self.reset_sub_limits)
            subplot_layout.addWidget(reset_sub_limits_btn, row, 0, 1, 2)
            row += 1

        subplot_group.setLayout(subplot_layout)
        layout.addWidget(subplot_group)

        # Schriftart-Einstellungen für Achsenbeschriftungen
        labels_font_group = QGroupBox(tr("axes.font_labels.title"))
        labels_font_layout = QGridLayout()

        # Font Family
        labels_font_layout.addWidget(QLabel(tr("axes.font_labels.family")), 0, 0)
        self.labels_font_combo = QFontComboBox()
        current_labels_font = self.font_settings.get('labels_font_family', 'Arial')
        index = self.labels_font_combo.findText(current_labels_font)
        if index >= 0:
            self.labels_font_combo.setCurrentIndex(index)
        labels_font_layout.addWidget(self.labels_font_combo, 0, 1)

        # Font Size
        labels_font_layout.addWidget(QLabel(tr("axes.font_labels.size")), 1, 0)
        self.labels_size_spin = QSpinBox()
        self.labels_size_spin.setRange(6, 32)
        self.labels_size_spin.setValue(self.font_settings.get('labels_size', 12))
        self.labels_size_spin.setSuffix(" pt")
        labels_font_layout.addWidget(self.labels_size_spin, 1, 1)

        # Bold & Italic
        self.labels_bold = QCheckBox(tr("axes.font_labels.bold"))
        self.labels_bold.setChecked(self.font_settings.get('labels_bold', False))
        labels_font_layout.addWidget(self.labels_bold, 2, 0)

        self.labels_italic = QCheckBox(tr("axes.font_labels.italic"))
        self.labels_italic.setChecked(self.font_settings.get('labels_italic', False))
        labels_font_layout.addWidget(self.labels_italic, 2, 1)

        labels_font_group.setLayout(labels_font_layout)
        layout.addWidget(labels_font_group)

        # Schriftart-Einstellungen für Ticks
        ticks_font_group = QGroupBox(tr("axes.font_ticks.title"))
        ticks_font_layout = QGridLayout()

        # Font Family
        ticks_font_layout.addWidget(QLabel(tr("axes.font_labels.family")), 0, 0)
        self.ticks_font_combo = QFontComboBox()
        current_ticks_font = self.font_settings.get('ticks_font_family', 'Arial')
        index = self.ticks_font_combo.findText(current_ticks_font)
        if index >= 0:
            self.ticks_font_combo.setCurrentIndex(index)
        ticks_font_layout.addWidget(self.ticks_font_combo, 0, 1)

        # Font Size
        ticks_font_layout.addWidget(QLabel(tr("axes.font_labels.size")), 1, 0)
        self.ticks_size_spin = QSpinBox()
        self.ticks_size_spin.setRange(6, 24)
        self.ticks_size_spin.setValue(self.font_settings.get('ticks_size', 10))
        self.ticks_size_spin.setSuffix(" pt")
        ticks_font_layout.addWidget(self.ticks_size_spin, 1, 1)

        # Bold & Italic
        self.ticks_bold = QCheckBox(tr("axes.font_labels.bold"))
        self.ticks_bold.setChecked(self.font_settings.get('ticks_bold', False))
        ticks_font_layout.addWidget(self.ticks_bold, 2, 0)

        self.ticks_italic = QCheckBox(tr("axes.font_labels.italic"))
        self.ticks_italic.setChecked(self.font_settings.get('ticks_italic', False))
        ticks_font_layout.addWidget(self.ticks_italic, 2, 1)

        ticks_font_group.setLayout(ticks_font_layout)
        layout.addWidget(ticks_font_group)

        # Reset-Button
        reset_layout = QHBoxLayout()
        reset_btn = QPushButton(tr("axes.reset_default"))
        reset_btn.clicked.connect(self.reset_labels)
        reset_layout.addStretch()
        reset_layout.addWidget(reset_btn)
        layout.addLayout(reset_layout)

        # Initial preview update
        self.update_preview()

        layout.addStretch()

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def reset_labels(self):
        """Setzt Labels auf Standard zurück"""
        self.xlabel_edit.clear()
        self.ylabel_edit.clear()

    def reset_limits(self):
        """Setzt Achsenlimits zurück"""
        self.xmin_edit.clear()
        self.xmax_edit.clear()
        self.ymin_edit.clear()
        self.ymax_edit.clear()
        self.auto_checkbox.setChecked(True)
        self.yscale_combo.setCurrentIndex(0)
        self.symlog_decades_spin.setValue(4)
        self.symlog_linscale_spin.setValue(1.0)

    def reset_sub_limits(self):
        """Setzt die Subplot-Achseneinstellungen zurück (v7.7)"""
        self.sub_ylabel_edit.clear()
        self.sub_xlabel_edit.clear()
        self.sub_xmin_edit.clear()
        self.sub_xmax_edit.clear()
        self.sub_ymin_edit.clear()
        self.sub_ymax_edit.clear()
        self.sub_auto_checkbox.setChecked(True)
        self.sub_yscale_combo.setCurrentIndex(0)

    def _update_symlog_controls_visibility(self):
        """Zeigt die Symlog-Feinsteuerung nur, wenn Symlog als Y-Skala gewählt ist"""
        is_symlog = self.yscale_combo.currentData() == 'symlog'
        self.symlog_decades_label.setVisible(is_symlog)
        self.symlog_decades_spin.setVisible(is_symlog)
        self.symlog_linscale_label.setVisible(is_symlog)
        self.symlog_linscale_spin.setVisible(is_symlog)

    def get_labels(self):
        """Gibt die Achsenbeschriftungen zurück"""
        xlabel = self.xlabel_edit.text().strip() if self.xlabel_edit.text().strip() else None
        ylabel = self.ylabel_edit.text().strip() if self.ylabel_edit.text().strip() else None
        return xlabel, ylabel

    def get_axis_limits(self):
        """Gibt die Achsenlimits zurück"""
        try:
            xmin = float(self.xmin_edit.text()) if self.xmin_edit.text() else None
        except ValueError:
            xmin = None

        try:
            xmax = float(self.xmax_edit.text()) if self.xmax_edit.text() else None
        except ValueError:
            xmax = None

        try:
            ymin = float(self.ymin_edit.text()) if self.ymin_edit.text() else None
        except ValueError:
            ymin = None

        try:
            ymax = float(self.ymax_edit.text()) if self.ymax_edit.text() else None
        except ValueError:
            ymax = None

        return {
            'xmin': xmin,
            'xmax': xmax,
            'ymin': ymin,
            'ymax': ymax,
            'auto': self.auto_checkbox.isChecked(),
            'yscale': self.yscale_combo.currentData(),
            'symlog_decades': self.symlog_decades_spin.value(),
            'symlog_linscale': self.symlog_linscale_spin.value()
        }

    def get_sub_axis_limits(self):
        """Gibt die Subplot-Achseneinstellungen zurück (v7.7: PDDF/ASAXS/Significance)"""
        if self.subplot_kind is None:
            # Kein Subplot beim aktuellen Plot-Typ -> Widgets existieren nicht in der UI,
            # unveränderte Ausgangswerte zurückgeben
            return dict(self._sub_axis_limits_original)

        def _to_float(edit):
            try:
                return float(edit.text()) if edit.text() else None
            except ValueError:
                return None

        xlabel = self.sub_xlabel_edit.text().strip() or None
        ylabel = self.sub_ylabel_edit.text().strip() or None

        return {
            'xlabel': xlabel,
            'ylabel': ylabel,
            'xmin': _to_float(self.sub_xmin_edit),
            'xmax': _to_float(self.sub_xmax_edit),
            'ymin': _to_float(self.sub_ymin_edit),
            'ymax': _to_float(self.sub_ymax_edit),
            'auto': self.sub_auto_checkbox.isChecked(),
            'yscale': self.sub_yscale_combo.currentData(),
        }

    def get_font_settings(self):
        """Gibt die Schriftart-Einstellungen zurück"""
        return {
            'labels_font_family': self.labels_font_combo.currentText(),
            'labels_size': self.labels_size_spin.value(),
            'labels_bold': self.labels_bold.isChecked(),
            'labels_italic': self.labels_italic.isChecked(),
            'ticks_font_family': self.ticks_font_combo.currentText(),
            'ticks_size': self.ticks_size_spin.value(),
            'ticks_bold': self.ticks_bold.isChecked(),
            'ticks_italic': self.ticks_italic.isChecked()
        }

    def update_preview(self):
        """Aktualisiert die Vorschau der formatierten Achsenbeschriftungen (v7.0)"""
        xlabel = self.xlabel_edit.text()
        ylabel = self.ylabel_edit.text()

        if not xlabel and not ylabel:
            self.preview_label.setText(f"<i>{tr('axes.axis_titles.preview_placeholder')}</i>")
            return

        # MathText preprocessing
        preview_parts = []
        if xlabel:
            processed_x = preprocess_mathtext(xlabel)
            preview_x_html = self._create_preview_html(processed_x)
            preview_parts.append(f"<b>X:</b> {preview_x_html}")

        if ylabel:
            processed_y = preprocess_mathtext(ylabel)
            preview_y_html = self._create_preview_html(processed_y)
            preview_parts.append(f"<b>Y:</b> {preview_y_html}")

        self.preview_label.setText(" | ".join(preview_parts))

    def _create_preview_html(self, text):
        """
        Erstellt eine HTML-Vorschau für den MathText.
        Dies ist eine Approximation - das tatsächliche Rendering erfolgt durch Matplotlib.
        """
        # Einfache Ersetzungen für häufige MathText-Befehle
        replacements = {
            r'$\alpha$': 'α', r'$\beta$': 'β', r'$\gamma$': 'γ',
            r'$\delta$': 'δ', r'$\theta$': 'θ', r'$\lambda$': 'λ',
            r'$\mu$': 'µ', r'$\pi$': 'π', r'$\sigma$': 'σ',
            r'$\pm$': '±', r'$\times$': '×', r'$\cdot$': '·',
            r'$\AA$': 'Å', r'\AA': 'Å',
        }

        preview = text
        for mathtext, symbol in replacements.items():
            preview = preview.replace(mathtext, symbol)

        # Ersetze \mathbf{...} und \mathit{...} mit HTML
        import re
        preview = re.sub(r'\$\\mathbf\{([^}]+)\}\$', r'<b>\1</b>', preview)
        preview = re.sub(r'\$\\mathit\{([^}]+)\}\$', r'<i>\1</i>', preview)

        # Verschachtelte Formatierung
        preview = re.sub(r'\\mathbf\{\\mathit\{([^}]+)\}\}', r'<b><i>\1</i></b>', preview)

        # Hochstellung und Tiefstellung (verbessert für {}-Syntax)
        # ^{...} und ^x
        preview = re.sub(r'\^{([^}]+)}', r'<sup>\1</sup>', preview)
        preview = re.sub(r'\^(\w)', r'<sup>\1</sup>', preview)

        # _{...} und _x
        preview = re.sub(r'_{([^}]+)}', r'<sub>\1</sub>', preview)
        preview = re.sub(r'_(\w)', r'<sub>\1</sub>', preview)

        # Entferne übrig gebliebene $ und \
        preview = preview.replace('$', '')
        preview = preview.replace('\\', '')

        return preview

    def show_syntax_help(self):
        """Zeigt Syntax-Hilfe für LaTeX/MathText an (v7.0)"""
        msg = QMessageBox(self)
        msg.setWindowTitle("LaTeX/MathText Syntax-Hilfe")
        msg.setIcon(QMessageBox.Information)
        msg.setText(get_syntax_help_text())
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setMinimumWidth(500)
        msg.exec()
