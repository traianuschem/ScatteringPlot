#!/usr/bin/env python3
"""
TUBAF Scattering Plot Tool - Version 5.2 (Qt)
==============================================

Professionelles Tool für Streudaten-Analyse mit:
- Qt6-basierte moderne GUI mit modularer Architektur
- Permanenter Dark Mode
- Verschiedene Plot-Typen (Log-Log, Porod, Kratky, Guinier, PDDF)
- Stil-Vorlagen und Auto-Erkennung
- Farbschema-Manager
- Drag & Drop
- Session-Verwaltung
- Erweiterte Legenden-, Grid- und Font-Einstellungen
- Verbesserter Export-Dialog
- Plot-Designs für konsistente Visualisierung
- Annotations und Referenzlinien
- Math Text für wissenschaftliche Notation
"""

import sys
from pathlib import Path
import json
import numpy as np

# Qt6 imports
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTreeWidget, QTreeWidgetItem, QPushButton, QLabel,
    QCheckBox, QComboBox, QLineEdit, QFileDialog, QMessageBox,
    QInputDialog, QDialog, QDialogButtonBox, QGroupBox, QGridLayout,
    QMenu, QDoubleSpinBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QColor, QPalette

# Matplotlib mit Qt Backend
import matplotlib
matplotlib.use('QtAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec

# Eigene Module
from core.models import DataSet, DataGroup
from core.constants import PLOT_TYPES
from dialogs.settings_dialog import PlotSettingsDialog
from dialogs.group_dialog import CreateGroupDialog
from dialogs.design_manager import DesignManagerDialog
from dialogs.legend_dialog import LegendSettingsDialog
from dialogs.grid_dialog import GridSettingsDialog
from dialogs.font_dialog import FontSettingsDialog
from dialogs.export_dialog import ExportSettingsDialog
from dialogs.annotations_dialog import AnnotationsDialog
from dialogs.reference_lines_dialog import ReferenceLinesDialog
from utils.data_loader import load_scattering_data
from utils.user_config import get_user_config


class DataTreeWidget(QTreeWidget):
    """Custom Tree Widget mit Drag & Drop Support"""

    items_dropped = Signal()  # Signal wenn Items verschoben wurden

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_app = None  # Wird später gesetzt

    def dropEvent(self, event):
        """Überschreibt dropEvent um Datenstrukturen zu synchronisieren"""
        # Standard Drop durchführen (visuell)
        super().dropEvent(event)

        # Nach Drop die Datenstrukturen synchronisieren
        if self.main_app:
            self.main_app.sync_data_from_tree()


class ScatterPlotApp(QMainWindow):
    """Hauptanwendung (Qt-basiert)"""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("TUBAF Scattering Plot Tool v5.2")
        self.resize(1600, 1000)

        # Config
        self.config = get_user_config()

        # Datenverwaltung
        self.groups = []
        self.unassigned_datasets = []

        # Plot-Einstellungen
        self.plot_type = 'Log-Log'
        self.stack_mode = True
        self.axis_limits = {'xmin': None, 'xmax': None, 'ymin': None, 'ymax': None, 'auto': True}

        # Erweiterte Einstellungen (Version 5.1)
        self.legend_settings = {
            'position': 'best',
            'fontsize': 10,
            'ncol': 1,
            'alpha': 0.9,
            'frameon': True,
            'shadow': False,
            'fancybox': True
        }
        self.grid_settings = {
            'major_enable': True,
            'major_axis': 'both',
            'major_linestyle': 'solid',
            'major_linewidth': 0.8,
            'major_alpha': 0.5,
            'major_color': '#CCCCCC',  # Hellgrau für hellen Plot-Hintergrund
            'minor_enable': True,
            'minor_axis': 'both',
            'minor_linestyle': 'dotted',
            'minor_linewidth': 0.5,
            'minor_alpha': 0.3,
            'minor_color': '#E0E0E0'  # Sehr hellgrau für Minor-Grid
        }
        self.font_settings = {
            'title_size': 14,
            'title_bold': True,
            'title_italic': False,
            'title_underline': False,
            'labels_size': 12,
            'labels_bold': False,
            'labels_italic': False,
            'labels_underline': False,
            'ticks_size': 10,
            'ticks_bold': False,
            'ticks_italic': False,
            'ticks_underline': False,
            'legend_size': 10,
            'legend_bold': False,
            'legend_italic': False,
            'legend_underline': False,
            'font_family': 'sans-serif',
            'use_math_text': False
        }
        self.export_settings = {
            'format': 'PNG',
            'dpi': 300,
            'width': 10.0,  # 10 inch = 25.4 cm
            'height': 6.25,  # 6.25 inch = 15.875 cm (16:10 Format)
            'keep_aspect': True,
            'transparent': False,
            'tight_layout': True,
            'facecolor_white': False
        }

        # Version 5.2 Features
        self.use_math_text = False  # Math Text für Exponenten
        self.annotations = []  # Liste von Annotations
        self.reference_lines = []  # Liste von Referenzlinien
        self.current_plot_design = 'Standard'  # Aktuelles Plot-Design

        # GUI erstellen
        self.create_menu()
        self.create_main_widget()

        # Dark Mode anwenden
        self.apply_theme()

        # Initial Plot
        self.update_plot()

    def create_menu(self):
        """Erstellt die Menüleiste"""
        menubar = self.menuBar()

        # Datei-Menü
        file_menu = menubar.addMenu("Datei")

        load_action = QAction("Daten laden...", self)
        load_action.triggered.connect(self.load_data_to_unassigned)
        file_menu.addAction(load_action)

        file_menu.addSeparator()

        save_session_action = QAction("Session speichern", self)
        save_session_action.triggered.connect(self.save_session)
        file_menu.addAction(save_session_action)

        load_session_action = QAction("Session laden", self)
        load_session_action.triggered.connect(self.load_session)
        file_menu.addAction(load_session_action)

        file_menu.addSeparator()

        export_action = QAction("Exportieren...", self)
        export_action.triggered.connect(self.show_export_dialog)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        quit_action = QAction("Beenden", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # Plot-Menü
        plot_menu = menubar.addMenu("Plot")

        update_action = QAction("Aktualisieren", self)
        update_action.triggered.connect(self.update_plot)
        plot_menu.addAction(update_action)

        plot_menu.addSeparator()

        legend_action = QAction("Legenden-Einstellungen...", self)
        legend_action.triggered.connect(self.show_legend_settings)
        plot_menu.addAction(legend_action)

        grid_action = QAction("Grid-Einstellungen...", self)
        grid_action.triggered.connect(self.show_grid_settings)
        plot_menu.addAction(grid_action)

        font_action = QAction("Schriftart-Einstellungen...", self)
        font_action.triggered.connect(self.show_font_settings)
        plot_menu.addAction(font_action)

        plot_menu.addSeparator()

        annotation_action = QAction("Annotation hinzufügen...", self)
        annotation_action.triggered.connect(self.add_annotation)
        plot_menu.addAction(annotation_action)

        refline_action = QAction("Referenzlinie hinzufügen...", self)
        refline_action.triggered.connect(self.add_reference_line)
        plot_menu.addAction(refline_action)

        # Design-Menü
        design_menu = menubar.addMenu("Design")

        manager_action = QAction("Design-Manager...", self)
        manager_action.triggered.connect(self.show_design_manager)
        design_menu.addAction(manager_action)

        design_menu.addSeparator()

        # Schnell-Stile
        for preset_name in self.config.style_presets.keys():
            action = QAction(f"Stil '{preset_name}' anwenden", self)
            action.triggered.connect(lambda checked, p=preset_name: self.apply_style_to_selected(p))
            design_menu.addAction(action)

        # Hilfe-Menü
        help_menu = menubar.addMenu("Hilfe")

        about_action = QAction("Über", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_main_widget(self):
        """Erstellt das Haupt-Widget"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        # Splitter für flexible Größenanpassung
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Linke Seite: Kontrollen
        left_widget = self.create_left_panel()
        splitter.addWidget(left_widget)

        # Rechte Seite: Plot
        right_widget = self.create_right_panel()
        splitter.addWidget(right_widget)

        # Proportionen setzen
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

    def create_left_panel(self):
        """Erstellt linkes Panel mit Kontrollen"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Buttons
        button_layout = QHBoxLayout()

        add_group_btn = QPushButton("➕ Gruppe")
        add_group_btn.clicked.connect(self.create_group)
        button_layout.addWidget(add_group_btn)

        auto_group_btn = QPushButton("🔢 Auto-Gruppieren")
        auto_group_btn.clicked.connect(self.auto_group_by_magnitude)
        auto_group_btn.setToolTip("Automatische Gruppierung nach Größenordnung mit Stack-Faktoren")
        button_layout.addWidget(auto_group_btn)

        load_btn = QPushButton("📁 Laden")
        load_btn.clicked.connect(self.load_data_to_unassigned)
        button_layout.addWidget(load_btn)

        delete_btn = QPushButton("🗑 Löschen")
        delete_btn.clicked.connect(self.delete_selected)
        button_layout.addWidget(delete_btn)

        layout.addLayout(button_layout)

        # Tree Widget mit Drag & Drop Support
        self.tree = DataTreeWidget()
        self.tree.main_app = self  # Referenz für Drag & Drop
        self.tree.setHeaderLabels(["Name", "Info"])
        self.tree.setColumnWidth(0, 250)
        self.tree.setDragDropMode(QTreeWidget.InternalMove)
        self.tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.tree.itemDoubleClicked.connect(self.on_tree_double_click)
        self.tree.itemChanged.connect(self.on_tree_item_changed)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)

        # Unassigned Section
        self.unassigned_item = QTreeWidgetItem(self.tree, ["▼ Nicht zugeordnet", ""])
        self.unassigned_item.setExpanded(True)

        # Annotations & Referenzlinien Section (Version 5.3)
        self.annotations_item = QTreeWidgetItem(self.tree, ["▼ Annotations & Referenzlinien", ""])
        self.annotations_item.setExpanded(True)

        layout.addWidget(self.tree)

        # Optionen
        options_group = QGroupBox("Optionen")
        options_layout = QGridLayout()

        # Plot-Typ
        options_layout.addWidget(QLabel("Plot-Typ:"), 0, 0)
        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems(list(PLOT_TYPES.keys()))
        self.plot_type_combo.currentTextChanged.connect(self.change_plot_type)
        options_layout.addWidget(self.plot_type_combo, 0, 1)

        # Stack-Modus
        options_layout.addWidget(QLabel("Stack:"), 1, 0)
        self.stack_checkbox = QCheckBox("Aktiviert")
        self.stack_checkbox.setChecked(True)
        self.stack_checkbox.stateChanged.connect(self.update_plot)
        options_layout.addWidget(self.stack_checkbox, 1, 1)

        # Farbschema
        options_layout.addWidget(QLabel("Farbschema:"), 2, 0)
        self.color_scheme_combo = QComboBox()
        self.color_scheme_combo.addItems(list(self.config.color_schemes.keys()))
        self.color_scheme_combo.setCurrentText('TUBAF')
        self.color_scheme_combo.currentTextChanged.connect(self.change_color_scheme)
        options_layout.addWidget(self.color_scheme_combo, 2, 1)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Update Button
        update_btn = QPushButton("🔄 Plot aktualisieren")
        update_btn.clicked.connect(self.update_plot)
        layout.addWidget(update_btn)

        return widget

    def create_right_panel(self):
        """Erstellt rechtes Panel mit Plot"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Matplotlib Figure
        self.fig = Figure(figsize=(12, 9), dpi=100)
        self.canvas = FigureCanvasQTAgg(self.fig)

        # Mouse-Events für Drag-and-Drop (v5.3) - NUR EINMAL registrieren!
        self.canvas.mpl_connect('button_press_event', self.on_annotation_press)
        self.canvas.mpl_connect('button_release_event', self.on_annotation_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_annotation_motion)

        # Toolbar
        self.toolbar = NavigationToolbar2QT(self.canvas, widget)

        layout.addWidget(self.canvas)
        layout.addWidget(self.toolbar)

        return widget

    def apply_theme(self):
        """Wendet permanentes Dark Theme an (v5.0: Dark Mode ist Standard)"""
        # Fusion Style mit Dark Palette (permanent)
        QApplication.setStyle('Fusion')

        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(43, 43, 43))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(60, 60, 60))
        dark_palette.setColor(QPalette.AlternateBase, QColor(50, 50, 50))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(64, 64, 64))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)

        QApplication.setPalette(dark_palette)

        # Plot bleibt im Light Mode (für bessere Lesbarkeit)
        plt.style.use('default')

    def update_plot(self):
        """Aktualisiert den Plot"""
        # Debug-Log kompakt in Konsole ausgeben (v5.3)
        from datetime import datetime

        def log(msg):
            """Gibt Debug-Info in Konsole aus"""
            print(msg)

        # Plot-Einstellungen
        self.stack_mode = self.stack_checkbox.isChecked()
        log(f"📊 Plot-Update: Stack={self.stack_mode}, Gruppen={len(self.groups)}, Unassigned={len(self.unassigned_datasets)}")

        # Figure leeren
        self.fig.clear()

        # PDDF hat Subplot
        if self.plot_type == 'PDDF':
            gs = GridSpec(2, 1, height_ratios=[3, 1], hspace=0.05, figure=self.fig)
            self.ax_main = self.fig.add_subplot(gs[0])
            self.ax_pddf = self.fig.add_subplot(gs[1], sharex=self.ax_main)
        else:
            self.ax_main = self.fig.add_subplot(111)
            self.ax_pddf = None

        # Farben holen (global)
        color_scheme = self.color_scheme_combo.currentText()
        colors = self.config.color_schemes.get(color_scheme, self.config.color_schemes['TUBAF'])
        color_cycle = iter(colors * 10)  # Genug Farben

        # Plotten
        plot_info = PLOT_TYPES[self.plot_type]

        # Gruppen plotten
        for group in self.groups:
            if not group.visible:
                continue

            # Stack-Faktor direkt von der Gruppe verwenden (NICHT kumulativ!)
            stack_factor = group.stack_factor if self.stack_mode else 1.0

            # Gruppen-Label für Legende (mit Stack-Faktor)
            if self.stack_mode and group.stack_factor != 1.0:
                group_label = f"{group.name} (×{stack_factor:.1f})"
            else:
                group_label = group.name

            # Dummy-Plot für Gruppen-Header in Legende
            has_visible_datasets = any(ds.show_in_legend for ds in group.datasets)
            if has_visible_datasets:
                self.ax_main.plot([], [], color='none', linestyle='', label=group_label)
                log(f"  📁 Gruppe '{group.name}': {len(group.datasets)} Datasets, Stack-Faktor=×{stack_factor:.1f}")

            # Gruppenspezifische Farbpalette (v5.4)
            if group.color_scheme:
                group_colors = self.config.color_schemes.get(group.color_scheme, colors)
                group_color_cycle = iter(group_colors * 10)
                log(f"    🎨 Farbpalette: {group.color_scheme}")
            else:
                group_color_cycle = color_cycle

            # Plot je Datensatz
            for dataset in group.datasets:
                # Checkbox steuert Sichtbarkeit komplett
                if not dataset.show_in_legend:
                    continue

                # Farbe
                if dataset.color:
                    color = dataset.color
                else:
                    color = next(group_color_cycle)
                    dataset.color = color

                # Daten transformieren
                x, y = self.transform_data(dataset.x, dataset.y, self.plot_type)

                # Stack-Multiplikation mit eigenem Gruppen-Faktor
                y = y * stack_factor

                # Plotten
                plot_style = dataset.get_plot_style()

                if dataset.y_err is not None and self.plot_type == 'Log-Log':
                    # Fehler als transparente Fläche
                    y_err_trans = self.transform_data(dataset.x, dataset.y_err, self.plot_type)[1]
                    y_err_trans = y_err_trans * stack_factor
                    self.ax_main.fill_between(x, y - y_err_trans, y + y_err_trans,
                                              alpha=0.2, color=color)

                # Dataset plotten (immer mit Label, da show_in_legend bereits geprüft)
                self.ax_main.plot(x, y, plot_style, color=color, label=dataset.display_label,
                                 linewidth=dataset.line_width, markersize=dataset.marker_size)

        # Auch nicht zugeordnete Datensätze plotten (ohne Stack-Faktor)
        unassigned_count = sum(1 for ds in self.unassigned_datasets if ds.show_in_legend)
        if unassigned_count > 0:
            log(f"  📄 Unassigned: {unassigned_count} Datasets (ohne Stacking)")

        for dataset in self.unassigned_datasets:
            # Checkbox steuert Sichtbarkeit komplett
            if not dataset.show_in_legend:
                continue

            # Farbe
            if dataset.color:
                color = dataset.color
            else:
                color = next(color_cycle)
                dataset.color = color

            # Daten transformieren
            x, y = self.transform_data(dataset.x, dataset.y, self.plot_type)

            # Plotten
            plot_style = dataset.get_plot_style()

            if dataset.y_err is not None and self.plot_type == 'Log-Log':
                # Fehler als transparente Fläche
                y_err_trans = self.transform_data(dataset.x, dataset.y_err, self.plot_type)[1]
                self.ax_main.fill_between(x, y - y_err_trans, y + y_err_trans,
                                          alpha=0.2, color=color)

            # Dataset plotten (immer mit Label, da show_in_legend bereits geprüft)
            self.ax_main.plot(x, y, plot_style, color=color, label=dataset.display_label,
                             linewidth=dataset.line_width, markersize=dataset.marker_size)

        # Achsen (mit Math Text Support in v5.2)
        xlabel = self.convert_to_mathtext(plot_info['xlabel'])
        ylabel = self.convert_to_mathtext(plot_info['ylabel'])

        # Achsenbeschriftungen mit erweiterten Font-Optionen (v5.3)
        label_weight = 'bold' if self.font_settings.get('labels_bold', False) else 'normal'
        label_style = 'italic' if self.font_settings.get('labels_italic', False) else 'normal'

        # Unterstrichen wird via LaTeX unterstützt (falls aktiviert)
        if self.font_settings.get('labels_underline', False):
            xlabel = r'$\underline{' + xlabel.replace('$', '') + r'}$'
            ylabel = r'$\underline{' + ylabel.replace('$', '') + r'}$'

        self.ax_main.set_xlabel(xlabel, fontsize=self.font_settings.get('labels_size', 12),
                               weight=label_weight, style=label_style,
                               fontfamily=self.font_settings.get('font_family', 'sans-serif'))
        self.ax_main.set_ylabel(ylabel, fontsize=self.font_settings.get('labels_size', 12),
                               weight=label_weight, style=label_style,
                               fontfamily=self.font_settings.get('font_family', 'sans-serif'))
        self.ax_main.set_xscale(plot_info['xscale'])
        self.ax_main.set_yscale(plot_info['yscale'])

        # Tick-Labels mit erweiterten Font-Optionen (v5.3)
        tick_weight = 'bold' if self.font_settings.get('ticks_bold', False) else 'normal'
        tick_style = 'italic' if self.font_settings.get('ticks_italic', False) else 'normal'

        self.ax_main.tick_params(axis='both', labelsize=self.font_settings.get('ticks_size', 10))

        # Font-Eigenschaften für Tick-Labels anwenden
        for label in self.ax_main.get_xticklabels() + self.ax_main.get_yticklabels():
            label.set_fontweight(tick_weight)
            label.set_fontstyle(tick_style)
            label.set_fontfamily(self.font_settings.get('font_family', 'sans-serif'))

        # Grid-Einstellungen (erweitert in v5.1)
        if self.grid_settings['major_enable']:
            self.ax_main.grid(True, which='major',
                            axis=self.grid_settings['major_axis'],
                            linestyle=self.grid_settings['major_linestyle'],
                            linewidth=self.grid_settings['major_linewidth'],
                            color=self.grid_settings['major_color'],
                            alpha=self.grid_settings['major_alpha'])

        if self.grid_settings['minor_enable']:
            self.ax_main.minorticks_on()
            self.ax_main.grid(True, which='minor',
                            axis=self.grid_settings['minor_axis'],
                            linestyle=self.grid_settings['minor_linestyle'],
                            linewidth=self.grid_settings['minor_linewidth'],
                            color=self.grid_settings['minor_color'],
                            alpha=self.grid_settings['minor_alpha'])

        # Achsenlimits
        if not self.axis_limits['auto']:
            if self.axis_limits['xmin'] is not None:
                self.ax_main.set_xlim(left=self.axis_limits['xmin'])
            if self.axis_limits['xmax'] is not None:
                self.ax_main.set_xlim(right=self.axis_limits['xmax'])
            if self.axis_limits['ymin'] is not None:
                self.ax_main.set_ylim(bottom=self.axis_limits['ymin'])
            if self.axis_limits['ymax'] is not None:
                self.ax_main.set_ylim(top=self.axis_limits['ymax'])

        # Legende (erweitert in v5.1, v5.3: Font-Optionen)
        if any(group.visible and group.datasets for group in self.groups) or self.unassigned_datasets:
            legend = self.ax_main.legend(
                loc=self.legend_settings['position'],
                fontsize=self.font_settings.get('legend_size', self.legend_settings.get('fontsize', 10)),
                ncol=self.legend_settings['ncol'],
                frameon=self.legend_settings['frameon'],
                shadow=self.legend_settings['shadow'],
                fancybox=self.legend_settings['fancybox']
            )
            if legend and legend.get_frame():
                legend.get_frame().set_alpha(self.legend_settings['alpha'])

            # v5.3: Font-Eigenschaften für Legenden-Texte anwenden
            if legend:
                legend_weight = 'bold' if self.font_settings.get('legend_bold', False) else 'normal'
                legend_style = 'italic' if self.font_settings.get('legend_italic', False) else 'normal'

                for text in legend.get_texts():
                    text.set_fontweight(legend_weight)
                    text.set_fontstyle(legend_style)
                    text.set_fontfamily(self.font_settings.get('font_family', 'sans-serif'))

        # Referenzlinien (Version 5.2)
        for ref_line in self.reference_lines:
            if ref_line['type'] == 'vertical':
                self.ax_main.axvline(
                    x=ref_line['value'],
                    linestyle=ref_line['linestyle'],
                    linewidth=ref_line['linewidth'],
                    color=ref_line['color'],
                    alpha=ref_line['alpha']
                )
                if ref_line['label']:
                    # Label oben rechts an der Linie
                    ylim = self.ax_main.get_ylim()
                    self.ax_main.text(ref_line['value'], ylim[1] * 0.95, ref_line['label'],
                                     rotation=90, va='top', ha='right',
                                     fontsize=10, color=ref_line['color'])
            else:  # horizontal
                self.ax_main.axhline(
                    y=ref_line['value'],
                    linestyle=ref_line['linestyle'],
                    linewidth=ref_line['linewidth'],
                    color=ref_line['color'],
                    alpha=ref_line['alpha']
                )
                if ref_line['label']:
                    # Label rechts an der Linie
                    xlim = self.ax_main.get_xlim()
                    self.ax_main.text(xlim[1] * 0.95, ref_line['value'], ref_line['label'],
                                     ha='right', va='bottom',
                                     fontsize=10, color=ref_line['color'])

        # Annotations (Version 5.2, erweitert 5.3: draggable)
        self.annotation_texts = []  # Text-Objekte speichern für draggable
        for idx, annotation in enumerate(self.annotations):
            text_obj = self.ax_main.text(
                annotation['x'],
                annotation['y'],
                annotation['text'],
                fontsize=annotation['fontsize'],
                color=annotation['color'],
                rotation=annotation['rotation'],
                ha='left',
                va='bottom',
                picker=True,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.1, edgecolor='none')
            )
            # Text verschiebbar machen (v5.3)
            text_obj.set_picker(5)  # Pickable mit Toleranz von 5 Pixeln
            text_obj._annotation_idx = idx  # Index speichern
            self.annotation_texts.append(text_obj)

        self.fig.tight_layout()
        self.canvas.draw()

    def convert_to_mathtext(self, text):
        """Konvertiert Unicode-Exponenten in Math Text (Version 5.2)"""
        if not self.font_settings.get('use_math_text', False):
            return text

        # Mapping von Unicode-Zeichen zu Math Text
        conversions = {
            '⁰': '$^{0}$',
            '¹': '$^{1}$',
            '²': '$^{2}$',
            '³': '$^{3}$',
            '⁴': '$^{4}$',
            '⁵': '$^{5}$',
            '⁶': '$^{6}$',
            '⁷': '$^{7}$',
            '⁸': '$^{8}$',
            '⁹': '$^{9}$',
            '⁻': '$^{-}$',
            '⁺': '$^{+}$',
            '₀': '$_{0}$',
            '₁': '$_{1}$',
            '₂': '$_{2}$',
            '₃': '$_{3}$',
            '₄': '$_{4}$',
            '₅': '$_{5}$',
            '₆': '$_{6}$',
            '₇': '$_{7}$',
            '₈': '$_{8}$',
            '₉': '$_{9}$',
        }

        # Spezielle Kombinationen (häufig verwendet)
        text = text.replace('nm⁻¹', r'nm$^{-1}$')
        text = text.replace('q⁴', r'q$^{4}$')
        text = text.replace('q²', r'q$^{2}$')

        # Einzelne Zeichen konvertieren
        for unicode_char, mathtext in conversions.items():
            text = text.replace(unicode_char, mathtext)

        return text

    def transform_data(self, x, y, plot_type):
        """Transformiert Daten je nach Plot-Typ"""
        if plot_type == 'Porod':
            return x, y * (x ** 4)
        elif plot_type == 'Kratky':
            return x, y * (x ** 2)
        elif plot_type == 'Guinier':
            return x ** 2, np.log(y)
        else:
            return x, y

    def on_annotation_press(self, event):
        """Maus-Press für Annotation-Drag (Version 5.3)"""
        if event.inaxes != self.ax_main:
            return

        # Prüfen, ob ein Text-Objekt angeklickt wurde
        for text_obj in getattr(self, 'annotation_texts', []):
            contains, _ = text_obj.contains(event)
            if contains:
                self._dragged_annotation = text_obj
                self._drag_start_pos = (event.xdata, event.ydata)
                break

    def on_annotation_motion(self, event):
        """Maus-Motion für Annotation-Drag (Version 5.3)"""
        if not hasattr(self, '_dragged_annotation') or self._dragged_annotation is None:
            return
        if event.inaxes != self.ax_main:
            return

        # Position aktualisieren
        self._dragged_annotation.set_position((event.xdata, event.ydata))
        self.canvas.draw_idle()

    def on_annotation_release(self, event):
        """Maus-Release für Annotation-Drag (Version 5.3)"""
        if not hasattr(self, '_dragged_annotation') or self._dragged_annotation is None:
            return

        # Finale Position in Datenstruktur speichern
        idx = self._dragged_annotation._annotation_idx
        if 0 <= idx < len(self.annotations):
            pos = self._dragged_annotation.get_position()
            self.annotations[idx]['x'] = pos[0]
            self.annotations[idx]['y'] = pos[1]
            self.update_annotations_tree()

        self._dragged_annotation = None
        self._drag_start_pos = None

    def create_group(self):
        """Erstellt eine neue Gruppe"""
        dialog = CreateGroupDialog(self)
        if dialog.exec():
            name, stack_factor = dialog.get_values()

            group = DataGroup(name, stack_factor)
            self.groups.append(group)

            # In Tree einfügen
            group_item = QTreeWidgetItem(self.tree, [name, f"×{stack_factor:.1f}"])
            group_item.setExpanded(True)
            group_item.setData(0, Qt.UserRole, ('group', group))

            QMessageBox.information(self, "Erfolg", f"Gruppe '{name}' erstellt")

    def auto_group_by_magnitude(self):
        """
        Automatische Gruppierung nach Größenordnung (v5.4)

        Gruppiert alle unassigned Datasets basierend auf ihrer Y-Wert-Größenordnung
        und setzt automatische Stack-Faktoren für optimale Trennung im Log-Log-Plot.
        """
        if not self.unassigned_datasets:
            QMessageBox.information(self, "Info", "Keine nicht zugeordneten Datasets vorhanden.")
            return

        # 1. Größenordnung für jedes Dataset berechnen
        dataset_magnitudes = []
        for dataset in self.unassigned_datasets:
            # Mittelwert der Y-Werte (log10)
            valid_y = dataset.y[dataset.y > 0]  # Nur positive Werte für log
            if len(valid_y) == 0:
                continue  # Skip datasets ohne gültige Werte

            mean_y = np.mean(valid_y)
            magnitude = int(np.round(np.log10(mean_y)))
            dataset_magnitudes.append((dataset, magnitude))

        if not dataset_magnitudes:
            QMessageBox.warning(self, "Fehler", "Keine Datasets mit gültigen Werten gefunden.")
            return

        # 2. Gruppiere nach Größenordnung
        from collections import defaultdict
        magnitude_groups = defaultdict(list)
        for dataset, magnitude in dataset_magnitudes:
            magnitude_groups[magnitude].append(dataset)

        # 3. Sortiere Größenordnungen (kleinste zuerst)
        sorted_magnitudes = sorted(magnitude_groups.keys())

        # 4. Erstelle Gruppen mit automatischen Stack-Faktoren
        created_groups = []
        for idx, magnitude in enumerate(sorted_magnitudes):
            datasets = magnitude_groups[magnitude]

            # Gruppen-Name basierend auf Größenordnung
            if magnitude >= 0:
                group_name = f"10^{magnitude}"
            else:
                group_name = f"10^({magnitude})"

            # Stack-Faktor: Jede Gruppe wird um ihre Position * 1 Dekade verschoben
            # Gruppe 0: 10^0 = 1, Gruppe 1: 10^1 = 10, Gruppe 2: 10^2 = 100, etc.
            stack_factor = 10.0 ** idx

            # Gruppe erstellen
            group = DataGroup(group_name, stack_factor)
            for dataset in datasets:
                group.add_dataset(dataset)

            self.groups.append(group)
            created_groups.append((group_name, len(datasets), stack_factor))

            # Datasets aus unassigned entfernen
            for dataset in datasets:
                if dataset in self.unassigned_datasets:
                    self.unassigned_datasets.remove(dataset)

        # 5. Tree aktualisieren
        self.rebuild_tree()
        self.update_plot()

        # 6. Erfolgs-Meldung
        msg = f"✓ {len(created_groups)} Gruppen erstellt:\n\n"
        for name, count, factor in created_groups:
            msg += f"• {name}: {count} Dataset(s), Stack-Faktor ×{factor:.1f}\n"

        QMessageBox.information(self, "Auto-Gruppierung erfolgreich", msg)

    def load_data_to_unassigned(self):
        """Lädt Daten in Nicht zugeordnet"""
        files, _ = QFileDialog.getOpenFileNames(self, "Daten laden",
                                                self.config.get_last_directory(),
                                                "Datendateien (*.dat *.txt *.csv);;Alle Dateien (*)")
        if files:
            self.config.set_last_directory(str(Path(files[0]).parent))

            for filepath in files:
                try:
                    dataset = DataSet(filepath)
                    self.unassigned_datasets.append(dataset)

                    # In Tree einfügen mit Checkbox (v4.2+)
                    item = QTreeWidgetItem(self.unassigned_item, [dataset.name, ""])
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(0, Qt.Checked if dataset.show_in_legend else Qt.Unchecked)
                    item.setData(0, Qt.UserRole, ('dataset', dataset))

                except Exception as e:
                    QMessageBox.warning(self, "Fehler", f"Fehler beim Laden von {filepath}:\n{e}")

            self.update_plot()

    def delete_selected(self):
        """Löscht ausgewählte Items (erweitert v5.3 für Annotations/Referenzlinien)"""
        items = self.tree.selectedItems()
        if not items:
            return

        for item in items:
            data = item.data(0, Qt.UserRole)
            if data:
                item_type = data[0]
                if item_type == 'group':
                    obj = data[1]
                    if obj in self.groups:
                        self.groups.remove(obj)
                elif item_type == 'dataset':
                    obj = data[1]
                    # Aus Gruppe oder unassigned entfernen
                    parent_data = item.parent().data(0, Qt.UserRole) if item.parent() else None
                    if parent_data and parent_data[0] == 'group':
                        parent_data[1].remove_dataset(obj)
                    elif obj in self.unassigned_datasets:
                        self.unassigned_datasets.remove(obj)
                elif item_type == 'annotation':
                    idx = data[1]
                    if 0 <= idx < len(self.annotations):
                        del self.annotations[idx]
                    self.update_annotations_tree()
                elif item_type == 'reference_line':
                    idx = data[1]
                    if 0 <= idx < len(self.reference_lines):
                        del self.reference_lines[idx]
                    self.update_annotations_tree()

            # Aus Tree entfernen (nicht bei Annotations/Referenzlinien, die werden neu generiert)
            if data and data[0] not in ['annotation', 'reference_line']:
                if item.parent():
                    item.parent().removeChild(item)
                else:
                    index = self.tree.indexOfTopLevelItem(item)
                    if index >= 0:
                        self.tree.takeTopLevelItem(index)

        self.update_plot()

    def on_tree_double_click(self, item, column):
        """Doppelklick auf Tree-Item"""
        # Prüfen, ob Item Daten hat
        if not item:
            return

        data = item.data(0, Qt.UserRole)
        if data:
            item_type, obj = data
            if item_type == 'group':
                # Stack-Faktor ändern mit Dialog
                dialog = QDialog(self)
                dialog.setWindowTitle("Stack-Faktor ändern")
                layout = QVBoxLayout(dialog)

                label_layout = QHBoxLayout()
                label_layout.addWidget(QLabel(f"Neuer Stack-Faktor für '{obj.name}':"))
                layout.addLayout(label_layout)

                spin = QDoubleSpinBox()
                spin.setRange(0.1, 10000.0)
                spin.setValue(obj.stack_factor)
                spin.setDecimals(2)
                spin.setSingleStep(0.1)
                layout.addWidget(spin)

                buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                buttons.accepted.connect(dialog.accept)
                buttons.rejected.connect(dialog.reject)
                layout.addWidget(buttons)

                if dialog.exec():
                    obj.stack_factor = spin.value()
                    item.setText(1, f"×{spin.value():.1f}")
                    self.update_plot()
            elif item_type == 'dataset':
                # Optional: Dataset-Eigenschaften bearbeiten
                pass

    def on_tree_item_changed(self, item, column):
        """Behandelt Änderungen an Tree-Items (v4.2+: Checkbox für Sichtbarkeit)"""
        if column != 0:  # Nur Spalte 0 hat Checkboxen
            return

        data = item.data(0, Qt.UserRole)
        if data and data[0] == 'dataset':
            dataset = data[1]
            # Checkbox-Status mit show_in_legend synchronisieren
            dataset.show_in_legend = (item.checkState(0) == Qt.Checked)
            self.update_plot()

    def show_context_menu(self, position):
        """Kontextmenü für Tree (erweitert v5.3 für Annotations/Referenzlinien, v5.4 für Gruppen-Farbpaletten)"""
        item = self.tree.itemAt(position)
        if not item:
            return

        menu = QMenu()

        data = item.data(0, Qt.UserRole)

        # Bearbeiten für Annotations/Referenzlinien (v5.3)
        edit_action = None
        if data and data[0] in ['annotation', 'reference_line']:
            edit_action = menu.addAction("Bearbeiten...")

        rename_action = menu.addAction("Umbenennen")

        # Farbpalette für Gruppen (v5.4)
        color_scheme_menu = None
        color_scheme_actions = {}
        if data and data[0] == 'group':
            menu.addSeparator()
            color_scheme_menu = menu.addMenu("Farbpalette wählen")
            # Option zum Zurücksetzen (globale Farbpalette verwenden)
            color_scheme_actions[None] = color_scheme_menu.addAction("(Global verwenden)")
            color_scheme_menu.addSeparator()
            # Alle verfügbaren Farbpaletten
            for scheme_name in sorted(self.config.color_schemes.keys()):
                color_scheme_actions[scheme_name] = color_scheme_menu.addAction(scheme_name)

        # Zu Gruppe zuordnen (nur für Datensätze)
        group_menu = None
        group_actions = {}
        if data and data[0] == 'dataset' and self.groups:
            menu.addSeparator()
            group_menu = menu.addMenu("Zu Gruppe zuordnen")
            for group in self.groups:
                group_actions[group] = group_menu.addAction(group.name)

        # Stil anwenden nur für Datensätze (v5.2+)
        style_menu = None
        style_actions = {}
        if data and data[0] == 'dataset':
            menu.addSeparator()
            style_menu = menu.addMenu("Stil anwenden")
            for preset_name in self.config.style_presets.keys():
                style_actions[preset_name] = style_menu.addAction(preset_name)

        # Farbe zurücksetzen nur für Datensätze (v4.2+)
        reset_color_action = None
        if data and data[0] == 'dataset':
            reset_color_action = menu.addAction("Farbe zurücksetzen")

        menu.addSeparator()
        delete_action = menu.addAction("Löschen")

        action = menu.exec(self.tree.viewport().mapToGlobal(position))

        if action == edit_action and edit_action:
            self.edit_annotation_or_refline(item)
        elif action == rename_action:
            self.rename_item(item)
        elif color_scheme_menu and action in color_scheme_actions.values():
            # Farbpalette für Gruppe setzen
            for scheme_name, scheme_action in color_scheme_actions.items():
                if action == scheme_action:
                    self.set_group_color_scheme(item, scheme_name)
                    break
        elif group_menu and action in group_actions.values():
            # Dataset zu Gruppe zuordnen
            for group, group_action in group_actions.items():
                if action == group_action:
                    self.move_dataset_to_group(item, group)
                    break
        elif style_menu and action in style_actions.values():
            # Stil anwenden
            for preset_name, preset_action in style_actions.items():
                if action == preset_action:
                    self.apply_style_to_dataset(item, preset_name)
                    break
        elif action == reset_color_action and reset_color_action:
            self.reset_dataset_color(item)
        elif action == delete_action:
            self.tree.setCurrentItem(item)
            self.delete_selected()

    def rename_item(self, item):
        """Benennt Item um"""
        data = item.data(0, Qt.UserRole)
        if data:
            item_type, obj = data
            old_name = obj.name if item_type in ['group', 'dataset'] else item.text(0)
            new_name, ok = QInputDialog.getText(self, "Umbenennen", "Neuer Name:", text=old_name)
            if ok and new_name:
                if item_type in ['group', 'dataset']:
                    obj.name = new_name
                item.setText(0, new_name)
                self.update_plot()

    def reset_dataset_color(self, item):
        """Setzt Farbe eines Datensatzes zurück (v4.2+)"""
        data = item.data(0, Qt.UserRole)
        if data and data[0] == 'dataset':
            dataset = data[1]
            dataset.color = None
            self.update_plot()

    def set_group_color_scheme(self, item, scheme_name):
        """Setzt Farbpalette für eine Gruppe (v5.4)"""
        data = item.data(0, Qt.UserRole)
        if data and data[0] == 'group':
            group = data[1]
            group.color_scheme = scheme_name
            # Farben aller Datasets in der Gruppe zurücksetzen, damit neue Palette angewendet wird
            for dataset in group.datasets:
                dataset.color = None
            self.update_plot()

    def apply_style_to_dataset(self, item, preset_name):
        """Wendet Stil-Vorlage auf Datensatz an (v5.2+)"""
        data = item.data(0, Qt.UserRole)
        if data and data[0] == 'dataset':
            dataset = data[1]
            dataset.apply_style_preset(preset_name)
            self.update_plot()

    def move_dataset_to_group(self, item, target_group):
        """Verschiebt Dataset zu einer Gruppe"""
        data = item.data(0, Qt.UserRole)
        if not data or data[0] != 'dataset':
            return

        dataset = data[1]

        # Aus unassigned_datasets entfernen
        if dataset in self.unassigned_datasets:
            self.unassigned_datasets.remove(dataset)
        else:
            # Aus anderer Gruppe entfernen
            for group in self.groups:
                if dataset in group.datasets:
                    group.datasets.remove(dataset)
                    break

        # Zu Zielgruppe hinzufügen
        target_group.datasets.append(dataset)

        # Tree neu aufbauen
        self.rebuild_tree()
        self.update_plot()

        print(f"✓ Dataset '{dataset.name}' zu Gruppe '{target_group.name}' verschoben")

    def sync_data_from_tree(self):
        """Synchronisiert Datenstrukturen nach Drag & Drop im Tree"""
        print("🔄 Synchronisiere Datenstrukturen nach Drag & Drop...")

        # Alle Gruppen leeren
        for group in self.groups:
            group.datasets.clear()

        # Unassigned leeren
        self.unassigned_datasets.clear()

        # Tree durchlaufen und Datenstrukturen neu aufbauen
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            parent_item = root.child(i)
            parent_data = parent_item.data(0, Qt.UserRole)

            # Prüfen ob es eine Gruppe ist
            if parent_data and parent_data[0] == 'group':
                group = parent_data[1]
                # Alle Datasets dieser Gruppe sammeln
                for j in range(parent_item.childCount()):
                    child_item = parent_item.child(j)
                    child_data = child_item.data(0, Qt.UserRole)
                    if child_data and child_data[0] == 'dataset':
                        dataset = child_data[1]
                        group.datasets.append(dataset)

            # "Nicht zugeordnet" Items
            elif parent_item == self.unassigned_item:
                for j in range(parent_item.childCount()):
                    child_item = parent_item.child(j)
                    child_data = child_item.data(0, Qt.UserRole)
                    if child_data and child_data[0] == 'dataset':
                        dataset = child_data[1]
                        self.unassigned_datasets.append(dataset)

        # Plot aktualisieren
        self.update_plot()
        print(f"✓ Synchronisation abgeschlossen: {len(self.groups)} Gruppen, {len(self.unassigned_datasets)} unassigned")

    def rebuild_tree(self):
        """Baut Tree komplett neu auf"""
        self.tree.clear()

        # "Nicht zugeordnet" Sektion
        self.unassigned_item = QTreeWidgetItem(self.tree, ["▼ Nicht zugeordnet", ""])
        self.unassigned_item.setExpanded(True)

        for dataset in self.unassigned_datasets:
            item = QTreeWidgetItem(self.unassigned_item, [dataset.display_label, ""])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(0, Qt.Checked if dataset.show_in_legend else Qt.Unchecked)
            item.setData(0, Qt.UserRole, ('dataset', dataset))

        # Gruppen
        for group in self.groups:
            group_item = QTreeWidgetItem(self.tree, [group.name, f"×{group.stack_factor:.1f}"])
            group_item.setExpanded(not group.collapsed)
            group_item.setData(0, Qt.UserRole, ('group', group))

            for dataset in group.datasets:
                item = QTreeWidgetItem(group_item, [dataset.display_label, ""])
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(0, Qt.Checked if dataset.show_in_legend else Qt.Unchecked)
                item.setData(0, Qt.UserRole, ('dataset', dataset))

        # Annotations & Referenzlinien (v5.3)
        self.annotations_item = QTreeWidgetItem(self.tree, ["▼ Annotations & Referenzlinien", ""])
        self.annotations_item.setExpanded(False)
        self.update_annotations_tree()

    def change_plot_type(self):
        """Ändert Plot-Typ"""
        self.plot_type = self.plot_type_combo.currentText()
        self.update_plot()

    def change_color_scheme(self):
        """Ändert Farbschema"""
        # Farben zurücksetzen
        for group in self.groups:
            for dataset in group.datasets:
                dataset.color = None
        for dataset in self.unassigned_datasets:
            dataset.color = None
        self.update_plot()

    def apply_style_to_selected(self, preset_name):
        """Wendet Stil auf ausgewählte Datensätze an"""
        items = self.tree.selectedItems()
        if not items:
            QMessageBox.information(self, "Info", "Bitte wählen Sie Datensätze aus")
            return

        for item in items:
            data = item.data(0, Qt.UserRole)
            if data and data[0] == 'dataset':
                dataset = data[1]
                dataset.apply_style_preset(preset_name)

        self.update_plot()

    def show_plot_settings(self):
        """Zeigt erweiterte Plot-Einstellungen"""
        dialog = PlotSettingsDialog(self, self.axis_limits)
        if dialog.exec():
            self.axis_limits = dialog.get_limits()
            self.update_plot()

    def show_design_manager(self):
        """Zeigt Design-Manager"""
        dialog = DesignManagerDialog(self, self.config)
        dialog.exec()
        # Config neu laden
        self.color_scheme_combo.clear()
        self.color_scheme_combo.addItems(list(self.config.color_schemes.keys()))
        self.update_plot()

    def show_legend_settings(self):
        """Zeigt Legenden-Einstellungen Dialog"""
        dialog = LegendSettingsDialog(self, self.legend_settings)
        if dialog.exec():
            self.legend_settings = dialog.get_settings()
            self.update_plot()

    def show_grid_settings(self):
        """Zeigt Grid-Einstellungen Dialog"""
        dialog = GridSettingsDialog(self, self.grid_settings)
        if dialog.exec():
            self.grid_settings = dialog.get_settings()
            self.update_plot()

    def show_font_settings(self):
        """Zeigt Schriftart-Einstellungen Dialog"""
        dialog = FontSettingsDialog(self, self.font_settings)
        if dialog.exec():
            self.font_settings = dialog.get_settings()
            self.update_plot()

    def update_annotations_tree(self):
        """Aktualisiert Annotations & Referenzlinien im Tree (Version 5.3)"""
        # Alte Items löschen
        while self.annotations_item.childCount() > 0:
            self.annotations_item.takeChild(0)

        # Annotations hinzufügen
        for idx, annotation in enumerate(self.annotations):
            text_preview = annotation['text'][:20] + '...' if len(annotation['text']) > 20 else annotation['text']
            item = QTreeWidgetItem(self.annotations_item,
                                  [f"📝 {text_preview}",
                                   f"({annotation['x']:.2f}, {annotation['y']:.2f})"])
            item.setData(0, Qt.UserRole, ('annotation', idx, annotation))

        # Referenzlinien hinzufügen
        for idx, ref_line in enumerate(self.reference_lines):
            line_type = "Vertikal" if ref_line['type'] == 'vertical' else 'Horizontal'
            label = ref_line.get('label', '')
            label_text = f" '{label}'" if label else ''
            item = QTreeWidgetItem(self.annotations_item,
                                  [f"📏 {line_type}{label_text}",
                                   f"{ref_line['value']:.2f}"])
            item.setData(0, Qt.UserRole, ('reference_line', idx, ref_line))

    def add_annotation(self):
        """Fügt Annotation hinzu (Version 5.2, erweitert 5.3)"""
        dialog = AnnotationsDialog(self)
        if dialog.exec():
            annotation = dialog.get_annotation()
            self.annotations.append(annotation)
            self.update_annotations_tree()
            self.update_plot()

    def add_reference_line(self):
        """Fügt Referenzlinie hinzu (Version 5.2, erweitert 5.3)"""
        dialog = ReferenceLinesDialog(self)
        if dialog.exec():
            ref_line = dialog.get_reference_line()

            # Automatisches Label generieren, falls leer (Version 5.3)
            if not ref_line.get('label'):
                if ref_line['type'] == 'vertical':
                    ref_line['label'] = f"x = {ref_line['value']:.2f}"
                else:
                    ref_line['label'] = f"y = {ref_line['value']:.2f}"

            self.reference_lines.append(ref_line)
            self.update_annotations_tree()
            self.update_plot()

    def edit_annotation_or_refline(self, item):
        """Bearbeitet Annotation oder Referenzlinie (Version 5.3)"""
        data = item.data(0, Qt.UserRole)
        if not data:
            return

        item_type, idx, obj = data

        if item_type == 'annotation':
            # Annotations-Dialog mit vorausgefüllten Werten
            from dialogs.annotations_dialog import AnnotationsDialog
            dialog = AnnotationsDialog(self)
            dialog.text_edit.setText(obj['text'])
            dialog.x_spin.setValue(obj['x'])
            dialog.y_spin.setValue(obj['y'])
            dialog.fontsize_spin.setValue(obj['fontsize'])
            dialog.color = obj['color']
            dialog.color_button.setStyleSheet(f"background-color: {obj['color']}; border: 1px solid #555;")
            dialog.color_button.setText(obj['color'])
            dialog.rotation_spin.setValue(obj['rotation'])

            if dialog.exec():
                updated = dialog.get_annotation()
                self.annotations[idx] = updated
                self.update_annotations_tree()
                self.update_plot()

        elif item_type == 'reference_line':
            # Referenzlinien-Dialog mit vorausgefüllten Werten
            from dialogs.reference_lines_dialog import ReferenceLinesDialog
            dialog = ReferenceLinesDialog(self)
            dialog.type_combo.setCurrentText('Vertikal' if obj['type'] == 'vertical' else 'Horizontal')
            dialog.value_spin.setValue(obj['value'])
            dialog.label_edit.setText(obj.get('label', ''))
            dialog.linestyle_combo.setCurrentText(obj['linestyle'])
            dialog.linewidth_spin.setValue(obj['linewidth'])
            dialog.color = obj['color']
            dialog.color_button.setStyleSheet(f"background-color: {obj['color']}; border: 1px solid #555;")
            dialog.color_button.setText(obj['color'])
            dialog.alpha_spin.setValue(obj['alpha'])

            if dialog.exec():
                updated = dialog.get_reference_line()
                # Automatisches Label generieren, falls leer
                if not updated.get('label'):
                    if updated['type'] == 'vertical':
                        updated['label'] = f"x = {updated['value']:.2f}"
                    else:
                        updated['label'] = f"y = {updated['value']:.2f}"
                self.reference_lines[idx] = updated
                self.update_annotations_tree()
                self.update_plot()

    def show_export_dialog(self):
        """Zeigt Export-Dialog mit erweiterten Optionen"""
        dialog = ExportSettingsDialog(self, self.export_settings)
        if dialog.exec():
            self.export_settings = dialog.get_settings()
            # Nun Export durchführen
            self.export_with_settings()

    def export_with_settings(self):
        """Exportiert Plot mit aktuellen Export-Einstellungen"""
        settings = self.export_settings
        format_ext = settings['format'].lower()

        if format_ext == 'png':
            filter_str = "PNG Dateien (*.png)"
        elif format_ext == 'svg':
            filter_str = "SVG Dateien (*.svg)"
        elif format_ext == 'pdf':
            filter_str = "PDF Dateien (*.pdf)"
        elif format_ext == 'eps':
            filter_str = "EPS Dateien (*.eps)"
        else:
            filter_str = "Alle Dateien (*.*)"

        filename, _ = QFileDialog.getSaveFileName(
            self,
            f"Plot als {settings['format']} exportieren",
            self.config.get_last_directory(),
            filter_str
        )

        if filename:
            try:
                # Sicherstellen, dass die Dateiendung korrekt ist
                if not filename.lower().endswith(f'.{format_ext}'):
                    filename = f"{filename}.{format_ext}"

                # Figure-Größe temporär anpassen
                original_size = self.fig.get_size_inches()
                self.fig.set_size_inches(settings['width'], settings['height'])

                # Export-Parameter
                save_kwargs = {
                    'dpi': settings['dpi'],
                    'bbox_inches': 'tight' if settings['tight_layout'] else None
                }

                if format_ext == 'png':
                    save_kwargs['transparent'] = settings['transparent']
                    if settings['facecolor_white'] and not settings['transparent']:
                        save_kwargs['facecolor'] = 'white'

                # Speichern
                self.fig.savefig(filename, **save_kwargs)

                # Größe zurücksetzen
                self.fig.set_size_inches(original_size)
                self.canvas.draw()

                # Verzeichnis merken
                self.config.set_last_directory(str(Path(filename).parent))

                QMessageBox.information(self, "Export erfolgreich",
                                      f"Plot wurde erfolgreich exportiert:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Export-Fehler",
                                   f"Fehler beim Exportieren:\n{str(e)}")

    def show_about(self):
        """Zeigt Über-Dialog"""
        QMessageBox.about(self, "Über TUBAF Scattering Plot Tool",
                         "TUBAF Scattering Plot Tool - Version 5.2 (Qt)\n\n"
                         "Professionelles Tool für Streudaten-Analyse\n\n"
                         "Neue Features in v5.2:\n"
                         "• Plot-Designs System (5 vordefinierte + eigene)\n"
                         "• Annotations und Referenzlinien\n"
                         "• Math Text für wissenschaftliche Notation\n"
                         "• Kontextmenü: Stil direkt anwenden\n\n"
                         "Features:\n"
                         "• Qt6-basierte moderne GUI mit modularer Architektur\n"
                         "• Erweiterte Legenden-, Grid- und Font-Einstellungen\n"
                         "• Verschiedene Plot-Typen (Log-Log, Porod, Kratky, etc.)\n"
                         "• Stil-Vorlagen und Auto-Erkennung\n"
                         "• Farbschema-Manager\n"
                         "• Drag & Drop\n"
                         "• Verbesserter Export-Dialog")

    def save_session(self):
        """Speichert Session"""
        filename, _ = QFileDialog.getSaveFileName(self, "Session speichern",
                                                  self.config.get_last_directory(),
                                                  "JSON Dateien (*.json)")
        if filename:
            try:
                session = {
                    'groups': [g.to_dict() for g in self.groups],
                    'unassigned': [ds.to_dict() for ds in self.unassigned_datasets],
                    'plot_type': self.plot_type,
                    'stack_mode': self.stack_mode,
                    'color_scheme': self.color_scheme_combo.currentText(),
                    'axis_limits': self.axis_limits,
                    'legend_settings': self.legend_settings,
                    'grid_settings': self.grid_settings,
                    'font_settings': self.font_settings,
                    'export_settings': self.export_settings,
                    'annotations': self.annotations,
                    'reference_lines': self.reference_lines
                }
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(session, f, indent=2)
                QMessageBox.information(self, "Erfolg", "Session gespeichert")
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Fehler beim Speichern:\n{e}")

    def load_session(self):
        """Lädt Session"""
        filename, _ = QFileDialog.getOpenFileName(self, "Session laden",
                                                  self.config.get_last_directory(),
                                                  "JSON Dateien (*.json)")
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    session = json.load(f)

                # Tree leeren
                self.tree.clear()
                self.unassigned_item = QTreeWidgetItem(self.tree, ["▼ Nicht zugeordnet", ""])
                self.unassigned_item.setExpanded(True)

                # Daten laden
                self.groups = [DataGroup.from_dict(g) for g in session.get('groups', [])]
                self.unassigned_datasets = [DataSet.from_dict(ds) for ds in session.get('unassigned', [])]

                # Tree neu aufbauen
                for group in self.groups:
                    group_item = QTreeWidgetItem(self.tree, [group.name, f"×{group.stack_factor:.1f}"])
                    group_item.setExpanded(not group.collapsed)
                    group_item.setData(0, Qt.UserRole, ('group', group))

                    for dataset in group.datasets:
                        item = QTreeWidgetItem(group_item, [dataset.display_label, ""])
                        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                        item.setCheckState(0, Qt.Checked if dataset.show_in_legend else Qt.Unchecked)
                        item.setData(0, Qt.UserRole, ('dataset', dataset))

                for dataset in self.unassigned_datasets:
                    item = QTreeWidgetItem(self.unassigned_item, [dataset.display_label, ""])
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(0, Qt.Checked if dataset.show_in_legend else Qt.Unchecked)
                    item.setData(0, Qt.UserRole, ('dataset', dataset))

                # Einstellungen wiederherstellen
                self.plot_type = session.get('plot_type', 'Log-Log')
                self.plot_type_combo.setCurrentText(self.plot_type)

                self.stack_mode = session.get('stack_mode', True)
                self.stack_checkbox.setChecked(self.stack_mode)

                color_scheme = session.get('color_scheme', 'TUBAF')
                self.color_scheme_combo.setCurrentText(color_scheme)

                self.axis_limits = session.get('axis_limits', {'xmin': None, 'xmax': None,
                                                               'ymin': None, 'ymax': None, 'auto': True})

                # Erweiterte Einstellungen (v5.1)
                if 'legend_settings' in session:
                    self.legend_settings = session['legend_settings']
                if 'grid_settings' in session:
                    self.grid_settings = session['grid_settings']
                if 'font_settings' in session:
                    self.font_settings = session['font_settings']
                if 'export_settings' in session:
                    self.export_settings = session['export_settings']

                # Version 5.2 Features
                if 'annotations' in session:
                    self.annotations = session['annotations']
                if 'reference_lines' in session:
                    self.reference_lines = session['reference_lines']

                # Annotations-Tree aktualisieren (v5.3)
                self.update_annotations_tree()

                self.update_plot()
                QMessageBox.information(self, "Erfolg", "Session geladen")
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Fehler beim Laden:\n{e}")

    def export_png(self):
        """Exportiert als PNG"""
        filename, _ = QFileDialog.getSaveFileName(self, "PNG Export",
                                                  self.config.get_last_directory(),
                                                  "PNG Dateien (*.png)")
        if filename:
            try:
                dpi = self.config.get_export_dpi()
                self.fig.savefig(filename, dpi=dpi, bbox_inches='tight')
                QMessageBox.information(self, "Erfolg", f"PNG exportiert ({dpi} DPI)")
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Export fehlgeschlagen:\n{e}")

    def export_svg(self):
        """Exportiert als SVG"""
        filename, _ = QFileDialog.getSaveFileName(self, "SVG Export",
                                                  self.config.get_last_directory(),
                                                  "SVG Dateien (*.svg)")
        if filename:
            try:
                self.fig.savefig(filename, format='svg', bbox_inches='tight')
                QMessageBox.information(self, "Erfolg", "SVG exportiert")
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Export fehlgeschlagen:\n{e}")


def main():
    """Hauptfunktion"""
    app = QApplication(sys.argv)

    # App-Metadaten
    app.setApplicationName("TUBAF Scattering Plot Tool")
    app.setOrganizationName("TU Bergakademie Freiberg")
    app.setApplicationVersion("5.0")

    # Hauptfenster
    window = ScatterPlotApp()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
