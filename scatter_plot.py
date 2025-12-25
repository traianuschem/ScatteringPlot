#!/usr/bin/env python3
"""
ScatterForge Plot - Version 7.0-dev
====================================

Professionelles Tool für Streudaten-Analyse mit:
- Qt6-basierte moderne GUI mit modularer Architektur
- Permanenter Dark Mode
- Verschiedene Plot-Typen (Log-Log, Porod, Kratky, Guinier, PDDF)
- Stil-Vorlagen und Auto-Erkennung
- Farbschema-Manager mit gruppenspezifischen Farbpaletten
- Drag & Drop
- Session-Verwaltung
- Erweiterte Legenden-, Grid- und Font-Einstellungen
- Optimierter Export-Dialog (16:10 Format)
- Plot-Designs für konsistente Visualisierung
- Programmweite Standard-Plot-Einstellungen
- Annotations und Referenzlinien
- Math Text für wissenschaftliche Notation
- Auto-Gruppierung mit Stack-Faktoren
- Umfassendes Logging-System
- Legendeneditor mit individueller Formatierung
- Unbegrenzte Skalierungsfaktoren
- Automatische Farbvereinheitlichung bei Gruppierung
- Umfassender Kurven-Editor mit Fehlerbalken-Support
- Schnellfarben-Menü aus aktueller Farbpalette
- Flexible Fehlerbalken-Darstellung (transparente Fläche oder Balken)
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
from PySide6.QtGui import QAction, QColor, QPalette, QShortcut, QKeySequence

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
from dialogs.legend_editor_dialog import LegendEditorDialog
from dialogs.title_editor_dialog import TitleEditorDialog
from dialogs.grid_dialog import GridSettingsDialog
from dialogs.font_dialog import FontSettingsDialog
from dialogs.export_dialog import ExportSettingsDialog
from dialogs.annotations_dialog import AnnotationsDialog
from dialogs.reference_lines_dialog import ReferenceLinesDialog
from dialogs.plot_limits_dialog import PlotLimitsDialog
from dialogs.axes_dialog import AxesSettingsDialog
from utils.data_loader import load_scattering_data
from utils.user_config import get_user_config
from utils.logger import setup_logger, get_logger
from utils.mathtext_formatter import preprocess_mathtext, format_legend_text
from i18n import get_i18n, tr


def format_stack_factor(factor):
    """
    Formatiert einen Stack-Faktor für die Anzeige.
    Wenn der Faktor eine Potenz von 10 ist, wird er als ($\\cdot 10^{n}$) dargestellt.
    Andernfalls wird er als (×{factor:.1f}) angezeigt.

    Args:
        factor: Der Stack-Faktor (float)

    Returns:
        Formatierter String für die Anzeige
    """
    import math

    # Prüfe ob der Faktor 1.0 ist (keine Formatierung nötig)
    if abs(factor - 1.0) < 1e-10:
        return ""

    # Prüfe ob der Faktor eine Potenz von 10 ist
    if factor > 0:
        log_factor = math.log10(factor)
        # Prüfe ob log_factor nahe an einer ganzen Zahl ist
        if abs(log_factor - round(log_factor)) < 1e-6:
            exponent = int(round(log_factor))
            return f"$(\\cdot 10^{{{exponent}}})$"

    # Fallback: normale Darstellung
    return f"$(\\times {factor:.1f})$"


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

        # Logger initialisieren (v5.6)
        self.logger = setup_logger('ScatterForge')
        self.logger.info("=" * 60)
        self.logger.info("ScatterForge Plot v6.2 gestartet")
        self.logger.info("=" * 60)

        self.setWindowTitle("ScatterForge Plot v6.2")
        self.resize(1600, 1000)

        # Config
        self.logger.debug("Lade User-Config...")
        self.config = get_user_config()
        self.logger.info("User-Config geladen")

        # i18n initialisieren (v6.2+)
        self.i18n = get_i18n()
        saved_lang = self.config.get_language()
        self.i18n.set_language(saved_lang)
        self.logger.info(f"Sprache initialisiert: {saved_lang}")

        # Datenverwaltung
        self.groups = []
        self.unassigned_datasets = []

        # Plot-Einstellungen
        self.plot_type = 'Log-Log'
        self.stack_mode = True
        self.axis_limits = {'xmin': None, 'xmax': None, 'ymin': None, 'ymax': None, 'auto': True}
        self.wavelength = 0.1524  # Standardwellenlänge: Cu K-alpha in nm

        # Erweiterte Einstellungen (Version 5.1)
        self.legend_settings = {
            'position': 'best',
            'fontsize': 10,
            'ncol': 1,
            'alpha': 0.9,
            'frameon': True,
            'shadow': False,
            'fancybox': True,
            'reverse_order': False  # v7.0: Reihenfolge invertieren
        }
        self.title_settings = {
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

        # Version 5.7 Features
        self.custom_xlabel = None  # Custom X-Achsenbeschriftung
        self.custom_ylabel = None  # Custom Y-Achsenbeschriftung
        self.unit_format = 'in'  # Format für Einheiten: 'slash', 'brackets', 'in'

        # Default Plot-Settings aus Config laden (v5.4)
        self.logger.debug("Prüfe auf gespeicherte Standard-Plot-Einstellungen...")
        default_settings = self.config.get_default_plot_settings()
        if default_settings:
            self.logger.info("Lade gespeicherte Standard-Plot-Einstellungen")
            self.logger.debug(f"  - Legend Settings: {list(default_settings.get('legend_settings', {}).keys())}")
            self.logger.debug(f"  - Grid Settings: {list(default_settings.get('grid_settings', {}).keys())}")
            self.logger.debug(f"  - Font Settings: {list(default_settings.get('font_settings', {}).keys())}")
            self.logger.debug(f"  - Plot Design: {default_settings.get('current_plot_design', 'Standard')}")

            self.legend_settings = default_settings.get('legend_settings', self.legend_settings)
            self.grid_settings = default_settings.get('grid_settings', self.grid_settings)
            self.font_settings = default_settings.get('font_settings', self.font_settings)
            self.current_plot_design = default_settings.get('current_plot_design', 'Standard')
            self.logger.info("Standard-Einstellungen erfolgreich angewendet")
        else:
            self.logger.info("Keine gespeicherten Standard-Einstellungen gefunden, verwende Defaults")

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
        file_menu = menubar.addMenu(tr("menu.file.title"))

        load_action = QAction(tr("menu.file.load"), self)
        load_action.triggered.connect(self.load_data_to_unassigned)
        file_menu.addAction(load_action)

        file_menu.addSeparator()

        # v7.0: Shortcuts für Session-Management
        save_session_action = QAction(tr("menu.file.save_session"), self)
        save_session_action.setShortcut(QKeySequence("Ctrl+S"))
        save_session_action.triggered.connect(self.save_session)
        file_menu.addAction(save_session_action)

        load_session_action = QAction(tr("menu.file.load_session"), self)
        load_session_action.setShortcut(QKeySequence("Ctrl+O"))
        load_session_action.triggered.connect(self.load_session)
        file_menu.addAction(load_session_action)

        # v7.0: Alternativer Shortcut für Session laden
        load_session_action2 = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        load_session_action2.activated.connect(self.load_session)

        file_menu.addSeparator()

        export_action = QAction(tr("menu.file.export"), self)
        export_action.setShortcut(QKeySequence("Ctrl+Shift+E"))
        export_action.triggered.connect(self.show_export_dialog)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        quit_action = QAction(tr("menu.file.quit"), self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # Plot-Menü
        plot_menu = menubar.addMenu(tr("menu.plot.title"))

        update_action = QAction(tr("menu.plot.refresh"), self)
        update_action.triggered.connect(self.update_plot)
        plot_menu.addAction(update_action)

        plot_menu.addSeparator()

        # v7.0: Shortcut für Legenden-Editor (konsolidiert alle Legendeneinstellungen)
        legend_editor_action = QAction(tr("menu.plot.legend_editor"), self)
        legend_editor_action.setShortcut(QKeySequence("Ctrl+L"))
        legend_editor_action.triggered.connect(self.show_legend_editor)
        plot_menu.addAction(legend_editor_action)

        title_editor_action = QAction(tr("menu.plot.title_editor"), self)
        title_editor_action.setShortcut(QKeySequence("Ctrl+T"))
        title_editor_action.triggered.connect(self.show_title_editor)
        plot_menu.addAction(title_editor_action)

        axes_action = QAction(tr("menu.plot.axes_limits"), self)
        axes_action.triggered.connect(self.show_axes_settings)
        plot_menu.addAction(axes_action)

        grid_action = QAction(tr("menu.plot.grid_settings"), self)
        grid_action.triggered.connect(self.show_grid_settings)
        plot_menu.addAction(grid_action)

        plot_menu.addSeparator()

        annotation_action = QAction(tr("menu.plot.add_annotation"), self)
        annotation_action.triggered.connect(self.add_annotation)
        plot_menu.addAction(annotation_action)

        refline_action = QAction(tr("menu.plot.add_reference_line"), self)
        refline_action.triggered.connect(self.add_reference_line)
        plot_menu.addAction(refline_action)

        # Design-Menü
        design_menu = menubar.addMenu(tr("menu.design.title"))

        manager_action = QAction(tr("menu.design.manager"), self)
        manager_action.triggered.connect(self.show_design_manager)
        design_menu.addAction(manager_action)

        design_menu.addSeparator()

        # Schnell-Stile
        for preset_name in self.config.style_presets.keys():
            action = QAction(tr("menu.design.apply_style", preset_name=preset_name), self)
            action.triggered.connect(lambda checked, p=preset_name: self.apply_style_to_selected(p))
            design_menu.addAction(action)

        # Einstellungen-Menü (v6.2+)
        settings_menu = menubar.addMenu(tr("menu.settings.title"))

        # Sprach-Untermenü
        language_menu = settings_menu.addMenu(tr("menu.settings.language"))
        available_langs = self.i18n.get_available_languages()
        current_lang = self.i18n.get_language()

        for lang_code, lang_name in available_langs.items():
            lang_action = QAction(lang_name, self)
            lang_action.setCheckable(True)
            lang_action.setChecked(lang_code == current_lang)
            lang_action.triggered.connect(lambda checked, lc=lang_code: self.change_language(lc))
            language_menu.addAction(lang_action)

        # Hilfe-Menü
        help_menu = menubar.addMenu(tr("menu.help.title"))

        about_action = QAction(tr("menu.help.about"), self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        # v7.0: Zusätzliche Shortcuts (nicht im Menü sichtbar)
        self.setup_shortcuts()

    def setup_shortcuts(self):
        """
        Richtet globale Shortcuts ein (v7.0)
        """
        # Plot-Typ-Shortcuts (Ctrl+Shift+1-7)
        plot_types = ['Log-Log', 'Porod', 'Kratky', 'Guinier', 'Bragg Spacing', '2-Theta', 'PDDF']
        for i, plot_type in enumerate(plot_types, start=1):
            shortcut = QShortcut(QKeySequence(f"Ctrl+Shift+{i}"), self)
            shortcut.activated.connect(lambda pt=plot_type: self.change_plot_type_shortcut(pt))

        # Kurven-Editor für ausgewähltes Element (Ctrl+E)
        edit_shortcut = QShortcut(QKeySequence("Ctrl+E"), self)
        edit_shortcut.activated.connect(self.edit_selected_curve)

        # Neue Gruppe erstellen (Ctrl+G)
        group_shortcut = QShortcut(QKeySequence("Ctrl+G"), self)
        group_shortcut.activated.connect(self.create_group)

        # Ausgewähltes Element löschen (Delete)
        delete_shortcut = QShortcut(QKeySequence("Delete"), self)
        delete_shortcut.activated.connect(self.delete_selected)

    def change_plot_type_shortcut(self, plot_type):
        """Ändert den Plot-Typ via Shortcut (v7.0)"""
        index = self.plot_type_combo.findText(plot_type)
        if index >= 0:
            self.plot_type_combo.setCurrentIndex(index)
            self.logger.info(f"Plot-Typ gewechselt zu '{plot_type}' via Shortcut")

    def edit_selected_curve(self):
        """Öffnet Kurven-Editor für ausgewähltes Element (v7.0)"""
        item = self.tree.currentItem()
        if item:
            data = item.data(0, Qt.UserRole)
            if data and data[0] == 'dataset':
                self.edit_curve_settings(item)
            elif data and data[0] == 'group':
                # Für Gruppen: Gruppen-Editor
                self.edit_group_curves(data[1])
            else:
                self.logger.debug("Kein Dataset oder Gruppe ausgewählt für Kurven-Editor")
        else:
            self.logger.debug("Nichts ausgewählt für Kurven-Editor")

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

        add_group_btn = QPushButton(tr("sidebar.add_group"))
        add_group_btn.clicked.connect(self.create_group)
        button_layout.addWidget(add_group_btn)

        auto_group_btn = QPushButton(tr("sidebar.auto_group"))
        auto_group_btn.clicked.connect(self.auto_group_by_magnitude)
        auto_group_btn.setToolTip("Erstellt für jedes ausgewählte Dataset eine eigene Gruppe mit automatischen Stack-Faktoren (10^0, 10^1, ...)")
        button_layout.addWidget(auto_group_btn)

        load_btn = QPushButton(tr("sidebar.load"))
        load_btn.clicked.connect(self.load_data_to_unassigned)
        button_layout.addWidget(load_btn)

        delete_btn = QPushButton(tr("sidebar.delete"))
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
        options_group = QGroupBox(tr("options.title"))
        options_layout = QGridLayout()

        # Plot-Typ
        options_layout.addWidget(QLabel(tr("options.plot_type")), 0, 0)
        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems(list(PLOT_TYPES.keys()))
        self.plot_type_combo.currentTextChanged.connect(self.change_plot_type)
        options_layout.addWidget(self.plot_type_combo, 0, 1)

        # Stack-Modus
        options_layout.addWidget(QLabel(tr("options.stack")), 1, 0)
        self.stack_checkbox = QCheckBox(tr("common.enabled"))
        self.stack_checkbox.setChecked(True)
        self.stack_checkbox.stateChanged.connect(self.update_plot)
        options_layout.addWidget(self.stack_checkbox, 1, 1)

        # Farbschema
        options_layout.addWidget(QLabel(tr("options.color_scheme")), 2, 0)
        self.color_scheme_combo = QComboBox()
        self.color_scheme_combo.addItems(self.config.get_sorted_scheme_names())
        self.color_scheme_combo.setCurrentText('TUBAF')
        self.color_scheme_combo.currentTextChanged.connect(self.change_color_scheme)
        options_layout.addWidget(self.color_scheme_combo, 2, 1)

        # Wellenlänge (für 2-Theta Plot)
        options_layout.addWidget(QLabel(tr("options.wavelength")), 3, 0)
        self.wavelength_edit = QLineEdit()
        self.wavelength_edit.setText(str(self.wavelength))
        self.wavelength_edit.setToolTip("Wellenlänge für 2-Theta Berechnung (Standard: Cu K-alpha = 0.1524 nm)")
        self.wavelength_edit.editingFinished.connect(self.update_wavelength)
        options_layout.addWidget(self.wavelength_edit, 3, 1)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Update Button
        update_btn = QPushButton(tr("options.update_plot"))
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

    def get_tree_order(self):
        """
        Liest die Reihenfolge der Elemente aus dem Tree aus (v7.0)

        Returns:
            tuple: (ordered_groups, ordered_unassigned)
                - ordered_groups: Liste von (group, datasets_in_order)
                - ordered_unassigned: Liste von datasets
        """
        ordered_groups = []
        ordered_unassigned = []

        # Durchlaufe Tree von oben nach unten
        root = self.tree.invisibleRootItem()

        for i in range(root.childCount()):
            item = root.child(i)
            data = item.data(0, Qt.UserRole)

            if not data:
                continue

            if data[0] == 'group':
                group = data[1]
                # Sammle Datasets dieser Gruppe in Tree-Reihenfolge
                datasets_in_order = []
                for j in range(item.childCount()):
                    child_item = item.child(j)
                    child_data = child_item.data(0, Qt.UserRole)
                    if child_data and child_data[0] == 'dataset':
                        datasets_in_order.append(child_data[1])
                ordered_groups.append((group, datasets_in_order))

            elif data[0] == 'dataset':
                # Unassigned dataset
                dataset = data[1]
                ordered_unassigned.append(dataset)

        return ordered_groups, ordered_unassigned

    def update_plot(self):
        """Aktualisiert den Plot"""
        # Plot-Einstellungen
        self.stack_mode = self.stack_checkbox.isChecked()
        self.logger.debug(f"Plot-Update: Stack={self.stack_mode}, Gruppen={len(self.groups)}, Unassigned={len(self.unassigned_datasets)}")

        # v7.0: Tree-Reihenfolge für Plot und Legende verwenden
        ordered_groups, ordered_unassigned = self.get_tree_order()
        self.logger.debug(f"  Tree-Order: {len(ordered_groups)} Gruppen, {len(ordered_unassigned)} unassigned")

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

        # v7.0: Verwende Tree-Order statt self.groups
        # Gruppen plotten in Tree-Reihenfolge
        for group, datasets_in_order in ordered_groups:
            if not group.visible:
                continue

            # Stack-Faktor direkt von der Gruppe verwenden (NICHT kumulativ!)
            stack_factor = group.stack_factor if self.stack_mode else 1.0

            # Gruppen-Label für Legende (v7.0: Verwendet display_label, das bereits den Faktor enthält)
            group_label = group.display_label if hasattr(group, 'display_label') and group.display_label else group.name

            # Dummy-Plot für Gruppen-Header in Legende
            # v7.0: Verwende datasets_in_order (Tree-Order)
            has_visible_datasets = any(ds.show_in_legend for ds in datasets_in_order)
            if has_visible_datasets:
                self.ax_main.plot([], [], color='none', linestyle='', label=group_label)
                self.logger.debug(f"  Gruppe '{group.name}': {len(datasets_in_order)} Datasets (Tree-Order), Stack=×{stack_factor:.1f}")

            # Gruppenspezifische Farbpalette (v5.4)
            if group.color_scheme:
                group_colors = self.config.color_schemes.get(group.color_scheme, colors)
                group_color_cycle = iter(group_colors * 10)
                self.logger.debug(f"  Farbpalette: Gruppe '{group.name}' → {group.color_scheme}")
            else:
                group_color_cycle = color_cycle

            # v7.0: Plot je Datensatz in Tree-Reihenfolge
            for dataset in datasets_in_order:
                # Checkbox steuert Sichtbarkeit komplett
                if not dataset.show_in_legend:
                    continue

                # Farbe
                if dataset.color:
                    color = dataset.color
                else:
                    color = next(group_color_cycle)
                    dataset.color = color

                # Daten mit individuellen Grenzen filtern (v5.7)
                x_data = dataset.x.copy()
                y_data = dataset.y.copy()
                y_err_data = dataset.y_err.copy() if dataset.y_err is not None else None

                # Maske für Grenzen erstellen
                mask = np.ones(len(x_data), dtype=bool)

                if dataset.x_min is not None:
                    mask &= (x_data >= dataset.x_min)
                if dataset.x_max is not None:
                    mask &= (x_data <= dataset.x_max)
                if dataset.y_min is not None:
                    mask &= (y_data >= dataset.y_min)
                if dataset.y_max is not None:
                    mask &= (y_data <= dataset.y_max)

                # Daten filtern
                x_data = x_data[mask]
                y_data = y_data[mask]
                if y_err_data is not None:
                    y_err_data = y_err_data[mask]

                # Daten transformieren
                x, y = self.transform_data(x_data, y_data, self.plot_type)

                # Stack-Multiplikation mit eigenem Gruppen-Faktor
                y = y * stack_factor

                # Plotten
                plot_style = dataset.get_plot_style()
                errorbar_style = getattr(dataset, 'errorbar_style', 'fill')

                # Spezialfall: stem plot für XRD-Referenz
                if errorbar_style == 'stem':
                    # Stem plot: Vertikale Linien von x-Achse zu Datenpunkten
                    markerline, stemlines, baseline = self.ax_main.stem(
                        x, y,
                        linefmt=color,
                        markerfmt=dataset.marker_style if dataset.marker_style else 'o',
                        basefmt=' '  # Keine Basislinie
                    )
                    # Stil anpassen
                    markerline.set_markerfacecolor(color)
                    markerline.set_markeredgecolor(color)
                    markerline.set_markersize(dataset.marker_size)
                    stemlines.set_linewidth(dataset.line_width)
                    stemlines.set_alpha(dataset.errorbar_alpha)
                    # Label für Legende (manuell, da stem keinen label Parameter hat)
                    self.ax_main.plot([], [], color=color, marker=dataset.marker_style if dataset.marker_style else 'o',
                                     markersize=dataset.marker_size, linestyle='',
                                     label=dataset.display_label)
                # Fehlerbalken plotten wenn vorhanden und aktiviert (v6.0)
                elif y_err_data is not None and dataset.show_errorbars:
                    # Fehler transformieren
                    y_err_trans = self.transform_data(x_data, y_err_data, self.plot_type)[1]
                    y_err_trans = y_err_trans * stack_factor

                    if errorbar_style == 'fill':
                        # Transparente Fehlerfläche (klassische Methode)
                        self.ax_main.fill_between(
                            x, y - y_err_trans, y + y_err_trans,
                            alpha=dataset.errorbar_alpha,
                            color=color
                        )
                        # Hauptkurve plotten
                        self.ax_main.plot(x, y, plot_style, color=color, label=dataset.display_label,
                                         linewidth=dataset.line_width, markersize=dataset.marker_size)
                    else:  # 'bars'
                        # Fehlerbalken mit Caps
                        self.ax_main.errorbar(
                            x, y, yerr=y_err_trans,
                            fmt=plot_style,
                            color=color,
                            label=dataset.display_label,
                            linewidth=dataset.line_width,
                            markersize=dataset.marker_size,
                            capsize=dataset.errorbar_capsize,
                            elinewidth=dataset.errorbar_linewidth,
                            alpha=dataset.errorbar_alpha,
                            ecolor=color,
                            capthick=dataset.errorbar_linewidth
                        )
                else:
                    # Ohne Fehlerbalken normal plotten
                    self.ax_main.plot(x, y, plot_style, color=color, label=dataset.display_label,
                                     linewidth=dataset.line_width, markersize=dataset.marker_size)

        # v7.0: Auch nicht zugeordnete Datensätze plotten in Tree-Order (ohne Stack-Faktor)
        unassigned_count = sum(1 for ds in ordered_unassigned if ds.show_in_legend)
        if unassigned_count > 0:
            self.logger.debug(f"  Unassigned: {unassigned_count} Datasets (Tree-Order, ohne Stacking)")

        for dataset in ordered_unassigned:
            # Checkbox steuert Sichtbarkeit komplett
            if not dataset.show_in_legend:
                continue

            # Farbe
            if dataset.color:
                color = dataset.color
            else:
                color = next(color_cycle)
                dataset.color = color

            # Daten mit individuellen Grenzen filtern (v5.7)
            x_data = dataset.x.copy()
            y_data = dataset.y.copy()
            y_err_data = dataset.y_err.copy() if dataset.y_err is not None else None

            # Maske für Grenzen erstellen
            mask = np.ones(len(x_data), dtype=bool)

            if dataset.x_min is not None:
                mask &= (x_data >= dataset.x_min)
            if dataset.x_max is not None:
                mask &= (x_data <= dataset.x_max)
            if dataset.y_min is not None:
                mask &= (y_data >= dataset.y_min)
            if dataset.y_max is not None:
                mask &= (y_data <= dataset.y_max)

            # Daten filtern
            x_data = x_data[mask]
            y_data = y_data[mask]
            if y_err_data is not None:
                y_err_data = y_err_data[mask]

            # Daten transformieren
            x, y = self.transform_data(x_data, y_data, self.plot_type)

            # Plotten
            plot_style = dataset.get_plot_style()
            errorbar_style = getattr(dataset, 'errorbar_style', 'fill')

            # Spezialfall: stem plot für XRD-Referenz
            if errorbar_style == 'stem':
                # Stem plot: Vertikale Linien von x-Achse zu Datenpunkten
                markerline, stemlines, baseline = self.ax_main.stem(
                    x, y,
                    linefmt=color,
                    markerfmt=dataset.marker_style if dataset.marker_style else 'o',
                    basefmt=' '  # Keine Basislinie
                )
                # Stil anpassen
                markerline.set_markerfacecolor(color)
                markerline.set_markeredgecolor(color)
                markerline.set_markersize(dataset.marker_size)
                stemlines.set_linewidth(dataset.line_width)
                stemlines.set_alpha(dataset.errorbar_alpha)
                # Label für Legende (manuell, da stem keinen label Parameter hat)
                self.ax_main.plot([], [], color=color, marker=dataset.marker_style if dataset.marker_style else 'o',
                                 markersize=dataset.marker_size, linestyle='',
                                 label=dataset.display_label)
            # Fehlerbalken plotten wenn vorhanden und aktiviert (v6.0)
            elif y_err_data is not None and dataset.show_errorbars:
                # Fehler transformieren
                y_err_trans = self.transform_data(x_data, y_err_data, self.plot_type)[1]

                if errorbar_style == 'fill':
                    # Transparente Fehlerfläche (klassische Methode)
                    self.ax_main.fill_between(
                        x, y - y_err_trans, y + y_err_trans,
                        alpha=dataset.errorbar_alpha,
                        color=color
                    )
                    # Hauptkurve plotten
                    self.ax_main.plot(x, y, plot_style, color=color, label=dataset.display_label,
                                     linewidth=dataset.line_width, markersize=dataset.marker_size)
                else:  # 'bars'
                    # Fehlerbalken mit Caps
                    self.ax_main.errorbar(
                        x, y, yerr=y_err_trans,
                        fmt=plot_style,
                        color=color,
                        label=dataset.display_label,
                        linewidth=dataset.line_width,
                        markersize=dataset.marker_size,
                        capsize=dataset.errorbar_capsize,
                        elinewidth=dataset.errorbar_linewidth,
                        alpha=dataset.errorbar_alpha,
                        ecolor=color,
                        capthick=dataset.errorbar_linewidth
                    )
            else:
                # Ohne Fehlerbalken normal plotten
                self.ax_main.plot(x, y, plot_style, color=color, label=dataset.display_label,
                                 linewidth=dataset.line_width, markersize=dataset.marker_size)

        # Achsen (mit Math Text Support in v5.2, Custom Labels in v5.7, Unit Format in v5.7, v7.0: MathText)
        if self.custom_xlabel:
            # v7.0: MathText-Formatierung auch für custom labels
            xlabel = preprocess_mathtext(self.custom_xlabel)
        else:
            xlabel = self.format_axis_label(plot_info['xlabel'])
            xlabel = self.convert_to_mathtext(xlabel)

        if self.custom_ylabel:
            # v7.0: MathText-Formatierung auch für custom labels
            ylabel = preprocess_mathtext(self.custom_ylabel)
        else:
            ylabel = self.format_axis_label(plot_info['ylabel'])
            ylabel = self.convert_to_mathtext(ylabel)

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

        # Tick-Einstellungen (v5.7: Erweitert um Länge, Breite, Richtung)
        tick_weight = 'bold' if self.font_settings.get('ticks_bold', False) else 'normal'
        tick_style = 'italic' if self.font_settings.get('ticks_italic', False) else 'normal'

        # Tick-Parameter aus grid_settings
        tick_labelsize = self.grid_settings.get('tick_labelsize', self.font_settings.get('ticks_size', 10))

        # Major Ticks
        self.ax_main.tick_params(
            axis='both',
            which='major',
            direction=self.grid_settings.get('major_tick_direction', 'in'),
            length=self.grid_settings.get('major_tick_length', 6.0),
            width=self.grid_settings.get('major_tick_width', 1.0),
            labelsize=tick_labelsize
        )

        # Minor Ticks
        if self.grid_settings.get('minor_ticks_enable', True):
            self.ax_main.tick_params(
                axis='both',
                which='minor',
                direction=self.grid_settings.get('minor_tick_direction', 'in'),
                length=self.grid_settings.get('minor_tick_length', 3.0),
                width=self.grid_settings.get('minor_tick_width', 0.5)
            )

        # Font-Eigenschaften für Tick-Labels anwenden
        for label in self.ax_main.get_xticklabels() + self.ax_main.get_yticklabels():
            label.set_fontweight(tick_weight)
            label.set_fontstyle(tick_style)
            label.set_fontfamily(self.font_settings.get('font_family', 'sans-serif'))

        # Tick-Label-Rotation (v5.7)
        x_rotation = self.grid_settings.get('x_tick_rotation', 0)
        y_rotation = self.grid_settings.get('y_tick_rotation', 0)
        if x_rotation != 0:
            self.ax_main.tick_params(axis='x', rotation=x_rotation)
        if y_rotation != 0:
            self.ax_main.tick_params(axis='y', rotation=y_rotation)

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

        # Legende (erweitert in v5.1, v5.3: Font-Optionen, v5.7: Individuelle Formatierung, v7.0: Tree-Order)
        if any(group.visible and datasets_in_order for group, datasets_in_order in ordered_groups) or ordered_unassigned:
            from matplotlib.lines import Line2D

            # Map für Formatierungen erstellen (Label -> (bold, italic))
            format_map = {}

            # Gruppen-Labels hinzufügen (wenn show_in_legend=True)
            new_handles = []
            new_labels = []

            # v7.0: Verwende Tree-Order
            for group, datasets_in_order in ordered_groups:
                if group.visible and datasets_in_order:
                    # Gruppe als Label hinzufügen, falls gewünscht
                    if getattr(group, 'show_in_legend', True):
                        # Dummy-Handle für Gruppen-Label (unsichtbare Linie)
                        dummy_handle = Line2D([0], [0], color='none', marker='', linestyle='')
                        new_handles.append(dummy_handle)
                        group_label = getattr(group, 'display_label', group.name)
                        # v7.0: MathText-Formatierung anwenden
                        is_bold = getattr(group, 'legend_bold', False)
                        is_italic = getattr(group, 'legend_italic', False)
                        formatted_label = format_legend_text(group_label, is_bold, is_italic)
                        new_labels.append(formatted_label)
                        # Speichere Original-Label für Mapping
                        format_map[formatted_label] = (group_label, is_bold, is_italic)

                    # v7.0: Datasets der Gruppe in Tree-Reihenfolge
                    for dataset in datasets_in_order:
                        if dataset.show_in_legend:
                            # Handle explizit mit korrekter Farbe und Stil erstellen
                            plot_style = dataset.get_plot_style()
                            marker = dataset.marker_style if dataset.marker_style else 'o'
                            linestyle = dataset.line_style if dataset.line_style else ''

                            # Wenn kein expliziter Stil, dann aus plot_style ableiten
                            if not dataset.marker_style and not dataset.line_style:
                                if 'fit' in dataset.name.lower():
                                    linestyle = '-'
                                    marker = ''
                                else:
                                    marker = 'o'
                                    linestyle = ''

                            handle = Line2D([0], [0],
                                          color=dataset.color,
                                          marker=marker,
                                          linestyle=linestyle,
                                          linewidth=dataset.line_width,
                                          markersize=dataset.marker_size)
                            new_handles.append(handle)
                            # v7.0: MathText-Formatierung anwenden
                            is_bold = getattr(dataset, 'legend_bold', False)
                            is_italic = getattr(dataset, 'legend_italic', False)
                            formatted_label = format_legend_text(dataset.display_label, is_bold, is_italic)
                            new_labels.append(formatted_label)
                            # Speichere Original-Label für Mapping
                            format_map[formatted_label] = (dataset.display_label, is_bold, is_italic)

            # v7.0: Unassigned Datasets in Tree-Order
            for dataset in ordered_unassigned:
                if dataset.show_in_legend:
                    # Handle explizit mit korrekter Farbe und Stil erstellen
                    plot_style = dataset.get_plot_style()
                    marker = dataset.marker_style if dataset.marker_style else 'o'
                    linestyle = dataset.line_style if dataset.line_style else ''

                    # Wenn kein expliziter Stil, dann aus plot_style ableiten
                    if not dataset.marker_style and not dataset.line_style:
                        if 'fit' in dataset.name.lower():
                            linestyle = '-'
                            marker = ''
                        else:
                            marker = 'o'
                            linestyle = ''

                    handle = Line2D([0], [0],
                                  color=dataset.color,
                                  marker=marker,
                                  linestyle=linestyle,
                                  linewidth=dataset.line_width,
                                  markersize=dataset.marker_size)
                    new_handles.append(handle)
                    # v7.0: MathText-Formatierung anwenden
                    is_bold = getattr(dataset, 'legend_bold', False)
                    is_italic = getattr(dataset, 'legend_italic', False)
                    formatted_label = format_legend_text(dataset.display_label, is_bold, is_italic)
                    new_labels.append(formatted_label)
                    # Speichere Original-Label für Mapping
                    format_map[formatted_label] = (dataset.display_label, is_bold, is_italic)

            # v7.0: Reihenfolge invertieren falls gewünscht (für gestackte Kurven)
            if self.legend_settings.get('reverse_order', False):
                new_handles = new_handles[::-1]
                new_labels = new_labels[::-1]
                self.logger.debug("  Legende: Reihenfolge invertiert")

            # Legende erstellen
            legend = self.ax_main.legend(
                new_handles, new_labels,
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
            # v5.7: Individuelle Formatierung pro Eintrag
            # v7.0: Formatierung erfolgt jetzt über MathText, nur noch Font-Familie setzen
            if legend:
                legend_texts = legend.get_texts()
                for text in legend_texts:
                    # Font-Familie für alle Einträge setzen
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

        # Annotations (Version 5.2, erweitert 5.3: draggable, v7.0: MathText)
        self.annotation_texts = []  # Text-Objekte speichern für draggable
        for idx, annotation in enumerate(self.annotations):
            # v7.0: MathText-Formatierung anwenden
            formatted_text = preprocess_mathtext(annotation['text'])

            text_obj = self.ax_main.text(
                annotation['x'],
                annotation['y'],
                formatted_text,
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

        # Titel rendern (v7.0)
        if self.title_settings.get('enabled', False) and self.title_settings.get('text'):
            title_text = self.title_settings['text']
            title_weight = 'bold' if self.title_settings.get('bold', True) else 'normal'
            title_style = 'italic' if self.title_settings.get('italic', False) else 'normal'

            # Titel erstellen
            title_obj = self.ax_main.set_title(
                title_text,
                fontsize=self.title_settings.get('size', 14),
                fontweight=title_weight,
                fontstyle=title_style,
                color=self.title_settings.get('color', '#000000'),
                loc=self.title_settings.get('position', 'center')
            )

            # Hintergrund (falls aktiviert)
            if self.title_settings.get('background_color'):
                title_obj.set_bbox(dict(
                    boxstyle='round,pad=0.5',
                    facecolor=self.title_settings['background_color'],
                    alpha=self.title_settings.get('background_alpha', 0.8),
                    edgecolor='none'
                ))

        # tight_layout() mit Fehlerbehandlung für ungültiges MathText (v6.2)
        try:
            self.fig.tight_layout()
        except ValueError as e:
            # MathText-Parsing-Fehler (z.B. nicht geschlossene Klammern in LaTeX)
            error_msg = str(e)
            if "ParseException" in error_msg or "Expected end of text" in error_msg:
                self.logger.warning(f"MathText-Fehler in Legende ignoriert: {error_msg[:100]}...")
                # Versuche Plot ohne tight_layout zu zeichnen
            else:
                # Andere ValueError durchreichen
                raise
        except Exception as e:
            # Andere Fehler loggen aber nicht abstürzen
            self.logger.error(f"Fehler bei tight_layout(): {e}")

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

    def format_axis_label(self, label):
        """Konvertiert Achsenbeschriftung je nach Unit-Format (Version 5.7)"""
        if '/' not in label or self.unit_format == 'slash':
            return label

        # Trenne Größe und Einheit
        parts = label.split('/')
        if len(parts) != 2:
            return label

        quantity = parts[0].strip()
        unit = parts[1].strip()

        if self.unit_format == 'brackets':
            return f"{quantity} [{unit}]"
        elif self.unit_format == 'in':
            return f"{quantity} in {unit}"

        return label

    def transform_data(self, x, y, plot_type):
        """Transformiert Daten je nach Plot-Typ"""
        if plot_type == 'Porod':
            return x, y * (x ** 4)
        elif plot_type == 'Kratky':
            return x, y * (x ** 2)
        elif plot_type == 'Guinier':
            return x ** 2, np.log(y)
        elif plot_type == 'Bragg Spacing':
            # d = 2*pi/q (q in nm^-1, d in nm)
            d = 2 * np.pi / x
            return d, y
        elif plot_type == '2-Theta':
            # 2theta = 2 * arcsin(lambda * q / (4*pi))
            # lambda in nm, q in nm^-1, result in degrees
            # Nur Werte berechnen, bei denen das Argument von arcsin <= 1 ist
            arg = self.wavelength * x / (4 * np.pi)
            # Warnung wenn Werte außerhalb des gültigen Bereichs liegen
            if np.any(arg > 1):
                valid_mask = arg <= 1
                x_valid = x[valid_mask]
                y_valid = y[valid_mask]
                if len(x_valid) > 0:
                    theta = np.arcsin(self.wavelength * x_valid / (4 * np.pi))
                    two_theta = 2 * theta * 180 / np.pi
                    return two_theta, y_valid
                else:
                    # Alle Werte sind ungültig, gebe leere Arrays zurück
                    return np.array([]), np.array([])
            else:
                theta = np.arcsin(arg)
                two_theta = 2 * theta * 180 / np.pi
                return two_theta, y
        else:
            return x, y

    def convert_reference_line_value(self, value, from_plot_type, to_plot_type):
        """
        Konvertiert einen X-Wert einer Referenzlinie von einem Plottyp zu einem anderen.

        Args:
            value: Der X-Wert im Quell-Plottyp
            from_plot_type: Der ursprüngliche Plottyp
            to_plot_type: Der Ziel-Plottyp

        Returns:
            Der konvertierte X-Wert im Ziel-Plottyp
        """
        # Plottypen, die q verwenden (keine Transformation der X-Achse)
        q_types = {'Log-Log', 'Porod', 'Kratky', 'PDDF'}

        # Zuerst auf q zurückrechnen (Basiseinheit)
        if from_plot_type in q_types:
            q = value
        elif from_plot_type == 'Guinier':
            # Guinier: x-Achse ist q²
            q = np.sqrt(value) if value >= 0 else value
        elif from_plot_type == 'Bragg Spacing':
            # Bragg: x-Achse ist d = 2π/q
            q = 2 * np.pi / value if value != 0 else value
        elif from_plot_type == '2-Theta':
            # 2-Theta: x-Achse ist 2θ in Grad
            # q = 4π·sin(θ)/λ
            theta_rad = value * np.pi / 360  # 2θ/2 in Radiant
            q = 4 * np.pi * np.sin(theta_rad) / self.wavelength
        else:
            q = value

        # Dann in Ziel-Plottyp umrechnen
        if to_plot_type in q_types:
            return q
        elif to_plot_type == 'Guinier':
            # Guinier: x-Achse ist q²
            return q ** 2
        elif to_plot_type == 'Bragg Spacing':
            # Bragg: x-Achse ist d = 2π/q
            return 2 * np.pi / q if q != 0 else q
        elif to_plot_type == '2-Theta':
            # 2-Theta: x-Achse ist 2θ in Grad
            # 2θ = 2·arcsin(λq/(4π))
            arg = self.wavelength * q / (4 * np.pi)
            if arg <= 1:
                theta_rad = np.arcsin(arg)
                return 2 * theta_rad * 180 / np.pi
            else:
                # Ungültiger Bereich, behalte Wert
                return value
        else:
            return q

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
        self.logger.debug("Öffne Gruppen-Dialog...")
        dialog = CreateGroupDialog(self)
        if dialog.exec():
            name, stack_factor = dialog.get_values()

            group = DataGroup(name, stack_factor)

            # Display-Label mit Faktor setzen (v7.0)
            if stack_factor != 1.0:
                factor_display = format_stack_factor(stack_factor)
                group.display_label = f"{name} {factor_display}"
            else:
                group.display_label = name

            self.groups.append(group)
            self.logger.info(f"Gruppe erstellt: '{name}' (Stack-Faktor: ×{stack_factor:.1f})")

            # In Tree einfügen
            factor_display = format_stack_factor(stack_factor)
            group_item = QTreeWidgetItem(self.tree, [name, factor_display])
            group_item.setExpanded(True)
            group_item.setData(0, Qt.UserRole, ('group', group))

            QMessageBox.information(self, tr("messages.success"), tr("messages.group_created", name=name))
        else:
            self.logger.debug("Gruppen-Dialog abgebrochen")

    def auto_group_by_magnitude(self):
        """
        Automatische Gruppierung (v5.4)

        Erstellt für jedes ausgewählte Dataset eine eigene Gruppe mit automatischen
        Stack-Faktoren (10^0, 10^1, 10^2, ...) für optimale Trennung im Log-Log-Plot.
        """
        self.logger.info("Starte Auto-Gruppierung...")
        # Ausgewählte Items holen
        selected_items = self.tree.selectedItems()
        if not selected_items:
            self.logger.warning("Auto-Gruppierung: Keine Datasets ausgewählt")
            QMessageBox.information(self, "Info",
                "Bitte wählen Sie Datasets aus der 'Nicht zugeordnet'-Liste aus.")
            return

        # Nur Datasets aus selected_items extrahieren
        selected_datasets = []
        for item in selected_items:
            data = item.data(0, Qt.UserRole)
            if data and data[0] == 'dataset':
                dataset = data[1]
                # Nur Datasets aus unassigned_datasets
                if dataset in self.unassigned_datasets:
                    selected_datasets.append(dataset)

        if not selected_datasets:
            self.logger.warning("Auto-Gruppierung: Keine gültigen Datasets ausgewählt")
            QMessageBox.information(self, "Info",
                "Bitte wählen Sie Datasets aus der 'Nicht zugeordnet'-Liste aus.")
            return

        self.logger.info(f"Auto-Gruppierung: {len(selected_datasets)} Datasets ausgewählt")

        # Für jedes Dataset eine eigene Gruppe erstellen
        created_groups = []
        for idx, dataset in enumerate(selected_datasets):
            # Gruppen-Name = Dataset-Name
            group_name = dataset.name

            # Stack-Faktor: Jede Gruppe wird um Position * 1 Dekade verschoben
            # Gruppe 0: 10^0 = 1, Gruppe 1: 10^1 = 10, Gruppe 2: 10^2 = 100, etc.
            stack_factor = 10.0 ** idx

            # Gruppe erstellen
            group = DataGroup(group_name, stack_factor)
            group.add_dataset(dataset)

            # Display-Label mit Faktor setzen (v7.0)
            if stack_factor != 1.0:
                factor_display = format_stack_factor(stack_factor)
                group.display_label = f"{group_name} {factor_display}"
            else:
                group.display_label = group_name

            self.groups.append(group)
            created_groups.append((group_name, stack_factor))
            self.logger.debug(f"  Gruppe '{group_name}' erstellt (Stack: ×{stack_factor:.1f})")

            # Dataset aus unassigned entfernen
            if dataset in self.unassigned_datasets:
                self.unassigned_datasets.remove(dataset)

        # Tree aktualisieren
        self.rebuild_tree()
        self.update_plot()

        self.logger.info(f"Auto-Gruppierung erfolgreich: {len(created_groups)} Gruppen erstellt")

        # Erfolgs-Meldung
        msg = f"✓ {len(created_groups)} Gruppen erstellt:\n\n"
        for name, factor in created_groups:
            msg += f"• {name}: Stack-Faktor ×{factor:.1f}\n"

        QMessageBox.information(self, tr("messages.auto_group_success"), msg)

    def load_data_to_unassigned(self):
        """Lädt Daten in Nicht zugeordnet"""
        self.logger.debug("Öffne Datei-Dialog zum Laden...")
        files, _ = QFileDialog.getOpenFileNames(self, "Daten laden",
                                                self.config.get_last_directory(),
                                                "Datendateien (*.dat *.txt *.csv);;Alle Dateien (*)")
        if files:
            self.logger.info(f"Lade {len(files)} Datei(en)...")
            self.config.set_last_directory(str(Path(files[0]).parent))

            loaded_count = 0
            for filepath in files:
                try:
                    dataset = DataSet(filepath)
                    self.unassigned_datasets.append(dataset)
                    loaded_count += 1
                    self.logger.debug(f"  Geladen: {dataset.name} ({len(dataset.x)} Datenpunkte)")

                    # In Tree einfügen mit Checkbox (v4.2+)
                    item = QTreeWidgetItem(self.unassigned_item, [dataset.name, ""])
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(0, Qt.Checked if dataset.show_in_legend else Qt.Unchecked)
                    item.setData(0, Qt.UserRole, ('dataset', dataset))

                except Exception as e:
                    self.logger.error(f"Fehler beim Laden von {Path(filepath).name}: {e}")
                    QMessageBox.warning(self, tr("messages.error"), tr("messages.error_loading_msg", filepath=filepath, error=str(e)))

            self.logger.info(f"Erfolgreich {loaded_count}/{len(files)} Datei(en) geladen")
            self.update_plot()
        else:
            self.logger.debug("Datei-Dialog abgebrochen")

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
                spin.setRange(0.0001, 1e15)  # Praktisch unbegrenzt
                spin.setValue(obj.stack_factor)
                spin.setDecimals(4)
                spin.setSingleStep(0.1)
                layout.addWidget(spin)

                buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                buttons.accepted.connect(dialog.accept)
                buttons.rejected.connect(dialog.reject)
                layout.addWidget(buttons)

                if dialog.exec():
                    new_factor = spin.value()
                    obj.stack_factor = new_factor

                    # Display-Label mit neuem Faktor aktualisieren (v7.0)
                    if new_factor != 1.0:
                        factor_display = format_stack_factor(new_factor)
                        obj.display_label = f"{obj.name} {factor_display}"
                    else:
                        obj.display_label = obj.name

                    # Tree-Anzeige aktualisieren
                    item.setText(1, format_stack_factor(new_factor))
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
        """Kontextmenü für Tree (erweitert v5.3 für Annotations/Referenzlinien, v5.4 für Gruppen-Farbpaletten, v6.0 für Kurven-Editor)"""
        item = self.tree.itemAt(position)
        if not item:
            return

        menu = QMenu()

        data = item.data(0, Qt.UserRole)

        # Bearbeiten für Annotations/Referenzlinien (v5.3)
        edit_action = None
        if data and data[0] in ['annotation', 'reference_line']:
            edit_action = menu.addAction(tr("context_menu.edit"))

        # Kurve bearbeiten für Datensätze (v6.0)
        edit_curve_action = None
        if data and data[0] == 'dataset':
            edit_curve_action = menu.addAction(tr("context_menu.edit_curve"))

        # Gruppe bearbeiten (v6.2)
        edit_group_action = None
        if data and data[0] == 'group':
            edit_group_action = menu.addAction(tr("context_menu.edit_group"))

        rename_action = menu.addAction(tr("context_menu.rename"))

        # Farbpalette für Gruppen (v5.4, v5.7: Erweitert um einheitliche Farbe)
        color_scheme_menu = None
        color_scheme_actions = {}
        set_group_color_action = None
        if data and data[0] == 'group':
            menu.addSeparator()
            color_scheme_menu = menu.addMenu(tr("context_menu.select_palette"))
            # Option zum Zurücksetzen (globale Farbpalette verwenden)
            color_scheme_actions[None] = color_scheme_menu.addAction(tr("context_menu.use_globally"))
            color_scheme_menu.addSeparator()
            # Alle verfügbaren Farbpaletten
            for scheme_name in sorted(self.config.color_schemes.keys()):
                color_scheme_actions[scheme_name] = color_scheme_menu.addAction(scheme_name)

            # Einheitliche Farbe für Gruppe setzen (v5.7)
            set_group_color_action = menu.addAction(tr("context_menu.set_uniform_color"))

            # Schnellfarben für Gruppen (v6.2)
            group_quick_color_menu = menu.addMenu(tr("context_menu.quick_colors"))
            group_quick_color_actions = {}
            # Bestimme welche Farbpalette die Gruppe verwendet
            group_obj = data[1]
            active_palette_name = group_obj.color_scheme if group_obj.color_scheme else self.color_scheme_combo.currentText()

            if active_palette_name in self.config.color_schemes:
                palette_colors = self.config.color_schemes[active_palette_name]
                for i, color in enumerate(palette_colors[:10], 1):  # Max 10 Farben
                    action_text = f"⬤ Farbe {i}"
                    group_quick_color_actions[color] = group_quick_color_menu.addAction(action_text)
        else:
            group_quick_color_menu = None
            group_quick_color_actions = {}

        # Zu Gruppe zuordnen (nur für Datensätze)
        group_menu = None
        group_actions = {}
        if data and data[0] == 'dataset' and self.groups:
            menu.addSeparator()
            group_menu = menu.addMenu(tr("context_menu.assign_to_group"))
            for group in self.groups:
                group_actions[group] = group_menu.addAction(group.name)

        # Stil anwenden nur für Datensätze (v5.2+)
        style_menu = None
        style_actions = {}
        if data and data[0] == 'dataset':
            menu.addSeparator()
            style_menu = menu.addMenu(tr("context_menu.apply_style"))
            for preset_name in self.config.style_presets.keys():
                style_actions[preset_name] = style_menu.addAction(preset_name)

        # Schnellfarben für Datensätze (v6.0)
        quick_color_menu = None
        quick_color_actions = {}
        if data and data[0] == 'dataset':
            # Bestimme welche Farbpalette zu verwenden ist (Gruppe oder global)
            dataset = data[1]
            active_palette_name = self.color_scheme_combo.currentText()

            # Wenn Dataset zu einer Gruppe gehört, verwende Gruppen-Palette wenn vorhanden
            for group in self.groups:
                if dataset in group.datasets and group.color_scheme:
                    active_palette_name = group.color_scheme
                    break

            if active_palette_name in self.config.color_schemes:
                quick_color_menu = menu.addMenu(tr("context_menu.quick_colors"))
                palette_colors = self.config.color_schemes[active_palette_name]

                for i, color in enumerate(palette_colors[:10], 1):  # Max 10 Farben
                    # Einfaches farbiges Quadrat als Icon-Ersatz
                    action_text = f"⬤ Farbe {i}"
                    quick_color_actions[color] = quick_color_menu.addAction(action_text)

        # Farbe zurücksetzen nur für Datensätze (v4.2+)
        reset_color_action = None
        if data and data[0] == 'dataset':
            reset_color_action = menu.addAction(tr("context_menu.reset_color"))

        # Plotgrenzen für Datensätze (v5.7)
        set_limits_action = None
        if data and data[0] == 'dataset':
            set_limits_action = menu.addAction(tr("context_menu.set_plot_limits"))

        menu.addSeparator()
        delete_action = menu.addAction(tr("context_menu.delete"))

        action = menu.exec(self.tree.viewport().mapToGlobal(position))

        if action == edit_action and edit_action:
            self.edit_annotation_or_refline(item)
        elif action == edit_curve_action and edit_curve_action:
            # Kurve bearbeiten (v6.0)
            self.edit_curve_settings(item)
        elif action == edit_group_action and edit_group_action:
            # Gruppe bearbeiten (v6.2)
            self.edit_group_settings(item)
        elif action == rename_action:
            self.rename_item(item)
        elif action == set_group_color_action and set_group_color_action:
            # Einheitliche Farbe für Gruppe setzen (v5.7)
            self.set_unified_group_color(item)
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
        elif quick_color_menu and action in quick_color_actions.values():
            # Schnellfarbe anwenden (v6.0)
            for color, color_action in quick_color_actions.items():
                if action == color_action:
                    self.set_dataset_quick_color(item, color)
                    break
        elif group_quick_color_menu and action in group_quick_color_actions.values():
            # Schnellfarbe für Gruppe anwenden (v6.2)
            for color, color_action in group_quick_color_actions.items():
                if action == color_action:
                    self.set_group_quick_color(item, color)
                    break
        elif action == reset_color_action and reset_color_action:
            self.reset_dataset_color(item)
        elif action == set_limits_action and set_limits_action:
            # Plotgrenzen für Dataset setzen (v5.7)
            self.set_dataset_plot_limits(item)
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

    def set_dataset_plot_limits(self, item):
        """Setzt individuelle Plotgrenzen für einen Datensatz (v5.7)"""
        data = item.data(0, Qt.UserRole)
        if not data or data[0] != 'dataset':
            return

        dataset = data[1]

        # Dialog öffnen
        dialog = PlotLimitsDialog(self, dataset)
        if dialog.exec():
            x_min, x_max, y_min, y_max = dialog.get_limits()

            # Grenzen setzen
            dataset.x_min = x_min
            dataset.x_max = x_max
            dataset.y_min = y_min
            dataset.y_max = y_max

            self.update_plot()
            print(f"✓ Plotgrenzen für '{dataset.name}' aktualisiert: X=[{x_min}, {x_max}], Y=[{y_min}, {y_max}]")

    def edit_curve_settings(self, item):
        """Öffnet den umfassenden Kurven-Editor-Dialog (v6.0)"""
        from dialogs.curve_settings_dialog import CurveSettingsDialog

        data = item.data(0, Qt.UserRole)
        if not data or data[0] != 'dataset':
            return

        dataset = data[1]

        # Bestimme aktive Farbpalette (Gruppe oder global)
        active_palette_name = self.color_scheme_combo.currentText()
        for group in self.groups:
            if dataset in group.datasets and group.color_scheme:
                active_palette_name = group.color_scheme
                break

        # Dialog öffnen
        dialog = CurveSettingsDialog(
            self,
            dataset,
            current_color_scheme=active_palette_name,
            color_schemes=self.config.color_schemes
        )

        if dialog.exec():
            settings = dialog.get_settings()

            # Alle Einstellungen auf Dataset anwenden
            dataset.color = settings['color']
            dataset.marker_style = settings['marker_style']
            dataset.marker_size = settings['marker_size']
            dataset.line_style = settings['line_style']
            dataset.line_width = settings['line_width']
            dataset.show_errorbars = settings['show_errorbars']
            dataset.errorbar_style = settings['errorbar_style']
            dataset.errorbar_capsize = settings['errorbar_capsize']
            dataset.errorbar_alpha = settings['errorbar_alpha']
            dataset.errorbar_linewidth = settings['errorbar_linewidth']

            self.update_plot()
            self.logger.info(f"Kurveneinstellungen für '{dataset.name}' aktualisiert")

    def edit_group_settings(self, item):
        """Öffnet Dialog zum Bearbeiten aller Kurven in einer Gruppe (v6.2)"""
        from dialogs.curve_settings_dialog import CurveSettingsDialog

        data = item.data(0, Qt.UserRole)
        if not data or data[0] != 'group':
            return

        group = data[1]

        if not group.datasets:
            QMessageBox.information(self, tr("messages.info"), tr("messages.empty_group"))
            return

        # Verwende das erste Dataset als Template für die Voreinstellungen
        template_dataset = group.datasets[0]

        # Bestimme aktive Farbpalette (Gruppe oder global)
        active_palette_name = group.color_scheme if group.color_scheme else self.color_scheme_combo.currentText()

        # Dialog öffnen mit Template-Dataset
        dialog = CurveSettingsDialog(
            self,
            template_dataset,
            current_color_scheme=active_palette_name,
            color_schemes=self.config.color_schemes
        )
        dialog.setWindowTitle(f"Gruppeneinstellungen für '{group.name}' ({len(group.datasets)} Kurven)")

        if dialog.exec():
            settings = dialog.get_settings()

            # Einstellungen auf ALLE Datasets in der Gruppe anwenden
            for dataset in group.datasets:
                dataset.color = settings['color']
                dataset.marker_style = settings['marker_style']
                dataset.marker_size = settings['marker_size']
                dataset.line_style = settings['line_style']
                dataset.line_width = settings['line_width']
                dataset.show_errorbars = settings['show_errorbars']
                dataset.errorbar_style = settings['errorbar_style']
                dataset.errorbar_capsize = settings['errorbar_capsize']
                dataset.errorbar_alpha = settings['errorbar_alpha']
                dataset.errorbar_linewidth = settings['errorbar_linewidth']

            self.update_plot()
            self.logger.info(f"Gruppeneinstellungen für '{group.name}' aktualisiert ({len(group.datasets)} Kurven)")

    def set_dataset_quick_color(self, item, color):
        """Setzt Schnellfarbe für einen Datensatz (v6.0)"""
        data = item.data(0, Qt.UserRole)
        if data and data[0] == 'dataset':
            dataset = data[1]
            dataset.color = color
            self.update_plot()
            self.logger.debug(f"Schnellfarbe {color} für '{dataset.name}' gesetzt")

    def set_group_quick_color(self, item, color):
        """Setzt Schnellfarbe für alle Datasets in einer Gruppe (v6.2)"""
        data = item.data(0, Qt.UserRole)
        if data and data[0] == 'group':
            group = data[1]
            # Farbe auf alle Datasets in der Gruppe anwenden
            for dataset in group.datasets:
                dataset.color = color
            self.update_plot()
            self.logger.debug(f"Schnellfarbe {color} für Gruppe '{group.name}' gesetzt ({len(group.datasets)} Kurven)")

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

    def set_unified_group_color(self, item):
        """Setzt eine einheitliche Farbe für alle Datasets in einer Gruppe (v5.7)"""
        from PySide6.QtWidgets import QColorDialog

        data = item.data(0, Qt.UserRole)
        if not data or data[0] != 'group':
            return

        group = data[1]

        # Aktuelle Farbe ermitteln (von erstem Dataset, falls vorhanden)
        initial_color = QColor('#1f77b4')  # Default
        if group.datasets:
            for dataset in group.datasets:
                if dataset.color:
                    initial_color = QColor(dataset.color)
                    break

        # Farbauswahl-Dialog
        color = QColorDialog.getColor(initial_color, self, f"Farbe für Gruppe '{group.name}' wählen")

        if color.isValid():
            # Farbe auf alle Datasets in der Gruppe anwenden
            color_hex = color.name()
            for dataset in group.datasets:
                dataset.color = color_hex

            self.update_plot()
            print(f"✓ Einheitliche Farbe für Gruppe '{group.name}' gesetzt: {color_hex}")

    def unify_group_colors(self, group):
        """Vereinheitlicht die Farben aller Datasets in einer Gruppe (v5.7)"""
        if not group.datasets:
            return

        # Erste verfügbare Farbe finden (von bereits gesetzten Datasets)
        unified_color = None
        for dataset in group.datasets:
            if dataset.color:
                unified_color = dataset.color
                break

        # Wenn keine Farbe gesetzt ist, eine neue aus der Palette holen
        if not unified_color:
            # Farbpalette für diese Gruppe
            if group.color_scheme and group.color_scheme in self.config.color_schemes:
                colors = self.config.color_schemes[group.color_scheme]
            else:
                # Standard-Farbpalette
                scheme_name = self.color_scheme_combo.currentText()
                colors = self.config.color_schemes.get(scheme_name, ['#1f77b4'])

            # Erste Farbe aus der Palette nehmen
            from itertools import cycle
            color_cycle = cycle(colors)
            unified_color = next(color_cycle)

        # Alle Datasets in der Gruppe auf diese Farbe setzen
        for dataset in group.datasets:
            dataset.color = unified_color

        print(f"✓ Farben in Gruppe '{group.name}' vereinheitlicht: {unified_color}")

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

        # Automatische Farbvereinheitlichung (v5.7)
        self.unify_group_colors(target_group)

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

                # Automatische Farbvereinheitlichung nach Drag & Drop (v5.7)
                if group.datasets:
                    self.unify_group_colors(group)

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
            factor_display = format_stack_factor(group.stack_factor)
            group_item = QTreeWidgetItem(self.tree, [group.name, factor_display])
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
        """Ändert Plot-Typ und passt Referenzlinien an"""
        old_plot_type = self.plot_type
        new_plot_type = self.plot_type_combo.currentText()

        # Vertikale Referenzlinien-X-Werte umrechnen
        if old_plot_type != new_plot_type and hasattr(self, 'reference_lines'):
            for ref_line in self.reference_lines:
                if ref_line['type'] == 'vertical':
                    old_value = ref_line['value']
                    new_value = self.convert_reference_line_value(old_value, old_plot_type, new_plot_type)
                    ref_line['value'] = new_value

                    # Label aktualisieren, falls es ein auto-generiertes Label ist
                    if ref_line.get('label') and ref_line['label'].startswith('x = '):
                        ref_line['label'] = f"x = {new_value:.2f}"

            # Annotations-Tree aktualisieren, um neue Werte anzuzeigen
            if hasattr(self, 'update_annotations_tree'):
                self.update_annotations_tree()

        self.plot_type = new_plot_type
        self.update_plot()

    def change_color_scheme(self):
        """Ändert Farbschema (v5.4: setzt auch Gruppen-Farbpaletten zurück)"""
        # Gruppen-Farbpaletten zurücksetzen (v5.4)
        for group in self.groups:
            group.color_scheme = None  # Globale Palette verwenden
            # Farben zurücksetzen
            for dataset in group.datasets:
                dataset.color = None
        for dataset in self.unassigned_datasets:
            dataset.color = None
        self.update_plot()

    def update_wavelength(self):
        """Aktualisiert die Wellenlänge aus dem UI-Eingabefeld"""
        try:
            wavelength = float(self.wavelength_edit.text())
            if wavelength <= 0:
                raise ValueError("Wellenlänge muss positiv sein")
            self.wavelength = wavelength
            # Plot nur aktualisieren wenn 2-Theta aktiv ist
            if self.plot_type == '2-Theta':
                self.update_plot()
        except ValueError as e:
            QMessageBox.warning(self, "Ungültige Eingabe",
                               f"Bitte geben Sie eine gültige positive Zahl ein.\n{str(e)}")
            self.wavelength_edit.setText(str(self.wavelength))

    def apply_style_to_selected(self, preset_name):
        """Wendet Stil auf ausgewählte Datensätze an"""
        items = self.tree.selectedItems()
        if not items:
            QMessageBox.information(self, tr("messages.info"), tr("messages.select_datasets"))
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
        self.color_scheme_combo.addItems(self.config.get_sorted_scheme_names())
        self.update_plot()

    def show_legend_settings(self):
        """Zeigt Legenden-Einstellungen Dialog"""
        dialog = LegendSettingsDialog(self, self.legend_settings)
        if dialog.exec():
            self.legend_settings = dialog.get_settings()
            self.update_plot()

    def show_legend_editor(self):
        """Zeigt erweiterten Legenden-Editor Dialog (v7.0 - konsolidiert alle Legendeneinstellungen)"""
        dialog = LegendEditorDialog(
            self,
            self.groups,
            self.unassigned_datasets,
            self.legend_settings,
            self.font_settings
        )
        if dialog.exec():
            # Die Änderungen wurden direkt an den Objekten vorgenommen
            # Reihenfolge aktualisieren (falls geändert)
            new_order = dialog.get_legend_order()
            self.apply_legend_order(new_order)
            # Legendeneinstellungen aktualisieren
            self.legend_settings.update(dialog.get_legend_settings())
            # Schriftart-Einstellungen aktualisieren
            font_updates = dialog.get_font_settings()
            self.font_settings.update(font_updates)
            self.update_plot()
            self.rebuild_tree()

    def show_title_editor(self):
        """Zeigt Titel-Editor Dialog (v7.0)"""
        dialog = TitleEditorDialog(self, self.title_settings)
        if dialog.exec():
            self.title_settings = dialog.get_settings()
            self.update_plot()

    def apply_legend_order(self, legend_order):
        """Wendet die neue Legendenreihenfolge auf die Datenstrukturen an (v5.7)"""
        # Gruppen und Datasets neu organisieren basierend auf der Legendenreihenfolge
        new_groups = []
        new_unassigned = []

        # Sammle alle Gruppen aus der neuen Reihenfolge
        seen_groups = set()
        seen_datasets = set()

        for item_data in legend_order:
            item_type = item_data[0]
            obj = item_data[1]

            if item_type == 'group':
                if obj not in seen_groups:
                    seen_groups.add(obj)
                    new_groups.append(obj)
            elif item_type == 'dataset':
                # Dataset aus item_data[2] (parent group) oder None
                parent_group = item_data[2] if len(item_data) > 2 else None
                seen_datasets.add(obj)

                if parent_group:
                    # Dataset gehört zu einer Gruppe
                    if parent_group not in seen_groups:
                        seen_groups.add(parent_group)
                        new_groups.append(parent_group)
                else:
                    # Unassigned dataset
                    if obj not in new_unassigned:
                        new_unassigned.append(obj)

        # Jetzt die Gruppen-Inhalte neu ordnen
        for item_data in legend_order:
            item_type = item_data[0]

            if item_type == 'dataset':
                obj = item_data[1]
                parent_group = item_data[2] if len(item_data) > 2 else None

                if parent_group and parent_group in new_groups:
                    # Stelle sicher, dass das Dataset in der richtigen Gruppe ist
                    if obj not in parent_group.datasets:
                        # Dataset aus alter Position entfernen
                        for group in self.groups:
                            if obj in group.datasets:
                                group.datasets.remove(obj)
                        if obj in self.unassigned_datasets:
                            self.unassigned_datasets.remove(obj)

                        # Zu neuer Gruppe hinzufügen
                        parent_group.datasets.append(obj)

        # Aktualisiere die Hauptlisten
        self.groups = new_groups
        self.unassigned_datasets = new_unassigned

        print(f"✓ Legendenreihenfolge angewendet: {len(self.groups)} Gruppen, {len(self.unassigned_datasets)} unassigned")

    def show_grid_settings(self):
        """Zeigt Grid- und Tick-Einstellungen Dialog"""
        dialog = GridSettingsDialog(self, self.grid_settings)
        if dialog.exec():
            self.grid_settings = dialog.get_settings()
            self.update_plot()

    def show_axes_settings(self):
        """Zeigt Achsen und Limits Dialog (v7.0 - jetzt mit Schriftart-Einstellungen)"""
        dialog = AxesSettingsDialog(
            self,
            self.custom_xlabel,
            self.custom_ylabel,
            self.plot_type,
            self.axis_limits,
            self.font_settings
        )
        if dialog.exec():
            self.custom_xlabel, self.custom_ylabel = dialog.get_labels()
            self.axis_limits = dialog.get_axis_limits()
            # Schriftart-Einstellungen aktualisieren
            font_updates = dialog.get_font_settings()
            self.font_settings.update(font_updates)
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
        dialog = ExportSettingsDialog(self, self.export_settings, main_figure=self.fig)
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

                # Format-spezifische Optionen
                if format_ext == 'png':
                    save_kwargs['transparent'] = settings.get('transparent', False)
                    if not settings.get('transparent', False):
                        save_kwargs['facecolor'] = settings.get('bg_color', 'white')
                    # PNG-Kompression
                    if 'png_compression' in settings:
                        save_kwargs['pil_kwargs'] = {'compress_level': settings['png_compression']}

                elif format_ext == 'pdf':
                    # PDF-Metadaten
                    metadata = {}
                    if settings.get('meta_title'):
                        metadata['Title'] = settings['meta_title']
                    if settings.get('meta_author'):
                        metadata['Author'] = settings['meta_author']
                    if settings.get('meta_subject'):
                        metadata['Subject'] = settings['meta_subject']
                    if settings.get('meta_keywords'):
                        metadata['Keywords'] = settings['meta_keywords']
                    if settings.get('meta_copyright'):
                        metadata['Copyright'] = settings['meta_copyright']

                    if metadata:
                        save_kwargs['metadata'] = metadata

                    # PDF-Version
                    if 'pdf_version' in settings:
                        import matplotlib
                        matplotlib.rcParams['pdf.fonttype'] = 42 if settings.get('embed_fonts', True) else 3

                elif format_ext == 'svg':
                    # SVG-Optionen
                    if settings.get('svg_text_as_path', False):
                        import matplotlib
                        matplotlib.rcParams['svg.fonttype'] = 'path'
                    else:
                        import matplotlib
                        matplotlib.rcParams['svg.fonttype'] = 'none'

                    # SVG-Metadaten
                    metadata = {}
                    if settings.get('meta_title'):
                        metadata['Title'] = settings['meta_title']
                    if settings.get('meta_author'):
                        metadata['Author'] = settings['meta_author']
                    if metadata:
                        save_kwargs['metadata'] = metadata

                # Speichern
                self.fig.savefig(filename, **save_kwargs)

                # Größe zurücksetzen
                self.fig.set_size_inches(original_size)
                self.canvas.draw()

                # Verzeichnis merken
                self.config.set_last_directory(str(Path(filename).parent))

                QMessageBox.information(self, tr("messages.export_success"),
                                      tr("messages.export_success_file", filename=filename))
            except Exception as e:
                QMessageBox.critical(self, tr("messages.export_error"),
                                   tr("messages.export_error_msg", error=str(e)))

    def change_language(self, language_code):
        """
        Wechselt die Sprache der Anwendung (v6.2+)

        Args:
            language_code: Sprachcode (z.B. 'de', 'en')
        """
        self.logger.info(f"Sprachwechsel zu: {language_code}")
        self.i18n.set_language(language_code)
        self.config.set_language(language_code)

        # Zeige Info-Dialog, dass Neustart erforderlich ist
        QMessageBox.information(
            self,
            tr("messages.info"),
            tr("messages.language_changed_restart")
        )

    def show_about(self):
        """Zeigt Über-Dialog"""
        QMessageBox.about(self, "Über ScatterForge Plot",
                         "ScatterForge Plot - Version 5.6\n\n"
                         "Professionelles Tool für Streudaten-Analyse\n\n"
                         "Neue Features in v5.6:\n"
                         "• Export-Optimierung (16:10 Standard-Format)\n"
                         "• Gruppenspezifische Farbpaletten\n"
                         "• Auto-Gruppierung mit automatischen Stack-Faktoren\n"
                         "• Programmweite Standard-Plot-Einstellungen\n"
                         "• Umfassendes Logging-System für Debugging\n\n"
                         "Features:\n"
                         "• Qt6-basierte moderne GUI mit modularer Architektur\n"
                         "• Erweiterte Legenden-, Grid- und Font-Einstellungen\n"
                         "• Verschiedene Plot-Typen (Log-Log, Porod, Kratky, etc.)\n"
                         "• Plot-Designs System mit Vorlagen\n"
                         "• Annotations und Referenzlinien\n"
                         "• Stil-Vorlagen und Auto-Erkennung\n"
                         "• Drag & Drop Support\n"
                         "• Session-Verwaltung")

    def save_session(self):
        """Speichert Session"""
        self.logger.debug("Öffne Session-Speicher-Dialog...")
        filename, _ = QFileDialog.getSaveFileName(self, "Session speichern",
                                                  self.config.get_last_directory(),
                                                  "JSON Dateien (*.json)")
        if filename:
            self.logger.info(f"Speichere Session nach: {Path(filename).name}")
            try:
                session = {
                    'groups': [g.to_dict() for g in self.groups],
                    'unassigned': [ds.to_dict() for ds in self.unassigned_datasets],
                    'plot_type': self.plot_type,
                    'stack_mode': self.stack_mode,
                    'color_scheme': self.color_scheme_combo.currentText(),
                    'axis_limits': self.axis_limits,
                    'wavelength': self.wavelength,  # v6.2
                    'legend_settings': self.legend_settings,
                    'title_settings': self.title_settings,  # v7.0
                    'grid_settings': self.grid_settings,
                    'font_settings': self.font_settings,
                    'export_settings': self.export_settings,
                    'annotations': self.annotations,
                    'reference_lines': self.reference_lines,
                    'current_plot_design': self.current_plot_design,  # v5.4
                    'custom_xlabel': self.custom_xlabel,  # v5.7
                    'custom_ylabel': self.custom_ylabel,  # v5.7
                    'unit_format': self.unit_format  # v5.7
                }
                self.logger.debug(f"  Gruppen: {len(self.groups)}, Unassigned: {len(self.unassigned_datasets)}")
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(session, f, indent=2)
                self.logger.info("Session erfolgreich gespeichert")
                QMessageBox.information(self, tr("messages.success"), tr("messages.session_saved"))
            except Exception as e:
                self.logger.error(f"Fehler beim Speichern der Session: {e}")
                QMessageBox.critical(self, tr("messages.error"), tr("messages.session_save_error", error=str(e)))
        else:
            self.logger.debug("Session-Speicher-Dialog abgebrochen")

    def load_session(self):
        """Lädt Session"""
        self.logger.debug("Öffne Session-Lade-Dialog...")
        filename, _ = QFileDialog.getOpenFileName(self, "Session laden",
                                                  self.config.get_last_directory(),
                                                  "JSON Dateien (*.json)")
        if filename:
            self.logger.info(f"Lade Session von: {Path(filename).name}")
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
                self.logger.debug(f"  Gruppen: {len(self.groups)}, Unassigned: {len(self.unassigned_datasets)}")

                # Display-Labels für Gruppen setzen, falls nicht vorhanden (v7.0)
                for group in self.groups:
                    if not hasattr(group, 'display_label') or group.display_label is None:
                        if group.stack_factor != 1.0:
                            factor_display = format_stack_factor(group.stack_factor)
                            group.display_label = f"{group.name} {factor_display}"
                        else:
                            group.display_label = group.name

                # Tree neu aufbauen
                for group in self.groups:
                    factor_display = format_stack_factor(group.stack_factor)
                    group_item = QTreeWidgetItem(self.tree, [group.name, factor_display])
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

                # Version 6.2: Wellenlänge für 2-Theta Plot
                if 'wavelength' in session:
                    self.wavelength = session['wavelength']
                    self.wavelength_edit.setText(str(self.wavelength))

                # Erweiterte Einstellungen (v5.1)
                if 'legend_settings' in session:
                    self.legend_settings = session['legend_settings']
                if 'title_settings' in session:  # v7.0
                    self.title_settings = session['title_settings']
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

                # Version 5.4: Plot Design wiederherstellen
                if 'current_plot_design' in session:
                    self.current_plot_design = session['current_plot_design']
                    self.logger.debug(f"  Plot Design: {self.current_plot_design}")

                # Version 5.7: Custom Achsenbeschriftungen
                if 'custom_xlabel' in session:
                    self.custom_xlabel = session['custom_xlabel']
                if 'custom_ylabel' in session:
                    self.custom_ylabel = session['custom_ylabel']
                if 'unit_format' in session:
                    self.unit_format = session['unit_format']

                # Annotations-Tree aktualisieren (v5.3)
                self.update_annotations_tree()

                self.logger.info("Session erfolgreich geladen")
                self.update_plot()
                QMessageBox.information(self, tr("messages.success"), tr("messages.session_loaded"))
            except Exception as e:
                self.logger.error(f"Fehler beim Laden der Session: {e}")
                QMessageBox.critical(self, tr("messages.error"), tr("messages.session_load_error", error=str(e)))
        else:
            self.logger.debug("Session-Lade-Dialog abgebrochen")

    def export_png(self):
        """Exportiert als PNG"""
        filename, _ = QFileDialog.getSaveFileName(self, "PNG Export",
                                                  self.config.get_last_directory(),
                                                  "PNG Dateien (*.png)")
        if filename:
            try:
                dpi = self.config.get_export_dpi()
                self.fig.savefig(filename, dpi=dpi, bbox_inches='tight')
                QMessageBox.information(self, tr("messages.success"), tr("messages.png_exported", dpi=dpi))
            except Exception as e:
                QMessageBox.critical(self, tr("messages.error"), tr("messages.export_failed", error=str(e)))

    def export_svg(self):
        """Exportiert als SVG"""
        filename, _ = QFileDialog.getSaveFileName(self, "SVG Export",
                                                  self.config.get_last_directory(),
                                                  "SVG Dateien (*.svg)")
        if filename:
            try:
                self.fig.savefig(filename, format='svg', bbox_inches='tight')
                QMessageBox.information(self, tr("messages.success"), tr("messages.svg_exported"))
            except Exception as e:
                QMessageBox.critical(self, tr("messages.error"), tr("messages.export_failed", error=str(e)))


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
