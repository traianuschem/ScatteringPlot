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
from dialogs.dialog_utils import fit_to_screen, scrollable_layout


class AxesSettingsDialog(QDialog):
    """Dialog für Achsen-Einstellungen"""

    def __init__(self, parent, current_xlabel=None, current_ylabel=None, plot_type='Log-Log', axis_limits=None,
                 font_settings=None, panels=None):
        super().__init__(parent)
        self.setWindowTitle(tr("axes.title"))
        fit_to_screen(self, 650, 900)

        # Font settings initialisieren
        if font_settings is None:
            font_settings = {}
        self.font_settings = font_settings

        self.plot_type = plot_type

        # v8.1: Achsen der weiteren Panels (alle außer dem Hauptpanel). Jeder Eintrag:
        # {'id', 'name', 'type', 'axis' (dict), 'default_xlabel', 'default_ylabel', 'shared_x'}
        self.panels = [dict(p, axis=dict(p['axis'])) for p in (panels or [])]
        self._current_panel_index = None

        layout, outer_layout = scrollable_layout(self)

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

        # Weitere Panels (v8.1): Achsentitel, Limits und Skalen je Panel
        panel_group = QGroupBox(tr("axes.panels.title"))
        panel_layout = QGridLayout()
        row = 0

        self.panel_combo = QComboBox()
        self.panel_info_label = QLabel()
        self.panel_info_label.setWordWrap(True)
        self.sub_xlabel_edit = QLineEdit()
        self.sub_ylabel_edit = QLineEdit()
        self.sub_xmin_edit = QLineEdit()
        self.sub_xmax_edit = QLineEdit()
        self.sub_ymin_edit = QLineEdit()
        self.sub_ymax_edit = QLineEdit()
        self.sub_auto_checkbox = QCheckBox(tr("axes.panels.auto_scaling"))
        self.sub_xscale_combo = QComboBox()
        self.sub_yscale_combo = QComboBox()
        for combo in (self.sub_xscale_combo, self.sub_yscale_combo):
            combo.addItem(tr("axes.panels.scale_auto"), userData=None)
            combo.addItem(tr("axes.panels.scale_linear"), userData='linear')
            combo.addItem(tr("axes.panels.scale_log"), userData='log')
        self.sub_yscale_combo.addItem(tr("axes.panels.scale_symlog"), userData='symlog')

        if not self.panels:
            no_panel_label = QLabel(tr("axes.panels.no_panels"))
            no_panel_label.setWordWrap(True)
            panel_layout.addWidget(no_panel_label, row, 0, 1, 2)
        else:
            panel_layout.addWidget(QLabel(tr("axes.panels.panel")), row, 0)
            for p in self.panels:
                self.panel_combo.addItem(f"{p['name']} ({p['type']})", userData=p['id'])
            panel_layout.addWidget(self.panel_combo, row, 1)
            row += 1
            panel_layout.addWidget(self.panel_info_label, row, 0, 1, 2)
            row += 1
            for label_key, widget in (("x_title", self.sub_xlabel_edit), ("y_title", self.sub_ylabel_edit),
                                      ("x_min", self.sub_xmin_edit), ("x_max", self.sub_xmax_edit),
                                      ("y_min", self.sub_ymin_edit), ("y_max", self.sub_ymax_edit)):
                panel_layout.addWidget(QLabel(tr(f"axes.panels.{label_key}")), row, 0)
                panel_layout.addWidget(widget, row, 1)
                row += 1
            panel_layout.addWidget(self.sub_auto_checkbox, row, 0, 1, 2)
            row += 1
            panel_layout.addWidget(QLabel(tr("axes.panels.x_scale")), row, 0)
            panel_layout.addWidget(self.sub_xscale_combo, row, 1)
            row += 1
            panel_layout.addWidget(QLabel(tr("axes.panels.y_scale")), row, 0)
            panel_layout.addWidget(self.sub_yscale_combo, row, 1)
            row += 1
            reset_sub_limits_btn = QPushButton(tr("axes.panels.reset"))
            reset_sub_limits_btn.clicked.connect(self.reset_sub_limits)
            panel_layout.addWidget(reset_sub_limits_btn, row, 0, 1, 2)

            self.panel_combo.currentIndexChanged.connect(self._on_panel_changed)
            self._on_panel_changed(0)

        panel_group.setLayout(panel_layout)
        layout.addWidget(panel_group)

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

        # Buttons (außerhalb des Scrollbereichs)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer_layout.addWidget(buttons)

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
        """Setzt die Achseneinstellungen des gewählten Panels zurück (v8.1)"""
        for edit in (self.sub_xlabel_edit, self.sub_ylabel_edit, self.sub_xmin_edit,
                     self.sub_xmax_edit, self.sub_ymin_edit, self.sub_ymax_edit):
            edit.clear()
        self.sub_auto_checkbox.setChecked(True)
        self.sub_xscale_combo.setCurrentIndex(0)
        self.sub_yscale_combo.setCurrentIndex(0)

    @staticmethod
    def _set_combo_data(combo, value):
        index = combo.findData(value)
        combo.setCurrentIndex(index if index >= 0 else 0)

    def _store_current_panel(self):
        """Übernimmt die Eingaben in die Arbeitskopie des aktuell gewählten Panels."""
        if self._current_panel_index is None:
            return

        def _to_float(edit):
            try:
                return float(edit.text()) if edit.text() else None
            except ValueError:
                return None

        axis = self.panels[self._current_panel_index]['axis']
        axis.update({
            'xlabel': self.sub_xlabel_edit.text().strip() or None,
            'ylabel': self.sub_ylabel_edit.text().strip() or None,
            'xmin': _to_float(self.sub_xmin_edit),
            'xmax': _to_float(self.sub_xmax_edit),
            'ymin': _to_float(self.sub_ymin_edit),
            'ymax': _to_float(self.sub_ymax_edit),
            'auto': self.sub_auto_checkbox.isChecked(),
            'xscale': self.sub_xscale_combo.currentData(),
            'yscale': self.sub_yscale_combo.currentData(),
        })

    def _on_panel_changed(self, index):
        """Lädt die Achseneinstellungen des gewählten Panels in die Eingabefelder."""
        self._store_current_panel()
        if index < 0 or index >= len(self.panels):
            return
        self._current_panel_index = index
        p = self.panels[index]
        axis = p['axis']
        self.sub_xlabel_edit.setPlaceholderText(
            tr("axes.panels.auto_based_on_default", default=p.get('default_xlabel', '')))
        self.sub_ylabel_edit.setPlaceholderText(
            tr("axes.panels.auto_based_on_default", default=p.get('default_ylabel', '')))
        self.sub_xlabel_edit.setText(axis.get('xlabel') or '')
        self.sub_ylabel_edit.setText(axis.get('ylabel') or '')
        for edit, key in ((self.sub_xmin_edit, 'xmin'), (self.sub_xmax_edit, 'xmax'),
                          (self.sub_ymin_edit, 'ymin'), (self.sub_ymax_edit, 'ymax')):
            edit.setText('' if axis.get(key) is None else str(axis[key]))
        self.sub_auto_checkbox.setChecked(axis.get('auto', True))
        self._set_combo_data(self.sub_xscale_combo, axis.get('xscale'))
        self._set_combo_data(self.sub_yscale_combo, axis.get('yscale'))

        # Gekoppelte X-Achse: X-Limits/-Skala kommen vom Kopplungsziel
        shared = p.get('shared_x', False)
        for widget in (self.sub_xmin_edit, self.sub_xmax_edit, self.sub_xscale_combo):
            widget.setEnabled(not shared)
        self.panel_info_label.setText(tr("axes.panels.info_shared_x") if shared
                                      else tr("axes.panels.info_independent"))

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

    def get_panel_axes(self):
        """Gibt die Achseneinstellungen der weiteren Panels zurück (v8.1): {panel_id: axis}"""
        self._store_current_panel()
        return {p['id']: p['axis'] for p in self.panels}

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
