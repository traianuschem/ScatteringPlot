#!/usr/bin/env python3
"""
ScatterForge Plot

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
    QMenu, QDoubleSpinBox, QListWidget, QListWidgetItem
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
from core.models import DataSet, DataGroup, Dataset2D
from core.panel_types import PANEL_TYPE_ORDER
from core.plot_layout import (PlotLayout, MAIN_ID, PRESET_NAMES, LEGACY_PLOT_TYPES,
                              default_axis_settings, migrate_legacy_session)
from core.version import __version__, get_version_string
from dialogs.settings_dialog import PlotSettingsDialog
from dialogs.group_dialog import CreateGroupDialog
from dialogs.design_manager import DesignManagerDialog
from dialogs.legend_editor_dialog import LegendEditorDialog
from dialogs.title_editor_dialog import TitleEditorDialog
from dialogs.grid_dialog import GridSettingsDialog
from dialogs.font_dialog import FontSettingsDialog
from dialogs.export_dialog import ExportSettingsDialog
from dialogs.annotations_dialog import AnnotationsDialog
from dialogs.reference_lines_dialog import ReferenceLinesDialog
from dialogs.plot_limits_dialog import PlotLimitsDialog
from dialogs.axes_dialog import AxesSettingsDialog
from dialogs.plot2d_dialog import Plot2DDialog
from dialogs.gift_dialog import GiftDialog
from utils.data_loader import load_scattering_data
from analysis.significance import significance as compute_significance, rolling_median
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


def _looks_pddf_related(ds):
    """Erkennt P(r)-Kurven sowie ihre q-Raum-Fit-Kurven ("..._fit-PDDF" o.ä.)."""
    if ds.is_pofr():
        return True
    return 'pddf' in ds.filepath.stem.lower() and ds.is_fit_curve()


def split_pddf_bundle(datasets):
    """Trennt eine Dataset-Auswahl in eine gemeinsame PDDF-Gruppe und den Rest.

    Alle P(r)-Datensätze sowie ihre PDDF-Fit-Kurven (Dateiname enthält "pddf", z.B.
    "..._fit-PDDF") werden zusammen in EINE Gruppe gebündelt — auch über mehrere
    Proben hinweg, falls die Auswahl mehrere GIFT/GNOM-Ergebnisse enthält. Die
    zugehörige Rohdaten-Datei (z.B. "..._IA.dat") hat i.d.R. keinen im Dateinamen
    erkennbaren Bezug zu den PDDF-Exportdateien (frei gewählter GIFT/GNOM-
    Exportname) und kann daher nicht zuverlässig automatisch zugeordnet werden —
    sie muss weiterhin manuell in die entstandene Gruppe gezogen werden.

    Returns:
        (pddf_bundle, remaining): Liste der zu bündelnden Datasets (Auswahl-Reihenfolge),
        Liste der übrigen Datasets.
    """
    bundle = [ds for ds in datasets if _looks_pddf_related(ds)]
    if not bundle:
        return [], list(datasets)
    remaining = [ds for ds in datasets if ds not in bundle]
    return bundle, remaining


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


class _Curve:
    """Eine zu zeichnende Kurve: Datensatz + Gruppe (None = nicht zugeordnet),
    zugewiesene Farbe und Stack-Faktor."""
    __slots__ = ('dataset', 'group', 'color', 'stack_factor')

    def __init__(self, dataset, group, color, stack_factor):
        self.dataset = dataset
        self.group = group
        self.color = color
        self.stack_factor = stack_factor


class ScatterPlotApp(QMainWindow):
    """Hauptanwendung (Qt-basiert)"""

    # ------------------------------------------------------------------
    # v8.1: Plot-Typ, Achsenlimits und Achsentitel gehören dem Hauptpanel.
    # Die Properties halten die bisherigen Attribute für Dialoge, Designs
    # und Standard-Einstellungen kompatibel.
    # ------------------------------------------------------------------

    @property
    def plot_type(self):
        return self.plot_layout.main.panel_type

    @plot_type.setter
    def plot_type(self, value):
        self.plot_layout.main.set_type(value)

    @property
    def axis_limits(self):
        return self.plot_layout.main.axis

    @axis_limits.setter
    def axis_limits(self, value):
        axis = self.plot_layout.main.axis
        new = dict(value or {})
        labels = {k: axis.get(k) for k in ('xlabel', 'ylabel')}
        axis.clear()
        axis.update(default_axis_settings())
        axis.update(new)
        axis.update(labels)  # Achsentitel werden über custom_xlabel/custom_ylabel gesetzt

    @property
    def custom_xlabel(self):
        return self.plot_layout.main.axis.get('xlabel')

    @custom_xlabel.setter
    def custom_xlabel(self, value):
        self.plot_layout.main.axis['xlabel'] = value

    @property
    def custom_ylabel(self):
        return self.plot_layout.main.axis.get('ylabel')

    @custom_ylabel.setter
    def custom_ylabel(self, value):
        self.plot_layout.main.axis['ylabel'] = value

    def __init__(self):
        super().__init__()

        # Logger initialisieren (v5.6)
        self.logger = setup_logger('ScatterForge')
        self.logger.info("=" * 60)
        self.logger.info(f"{get_version_string()} gestartet")
        self.logger.info("=" * 60)

        self.setWindowTitle(get_version_string())
        self.resize(1600, 1000)

        # Config
        self.logger.debug("Lade User-Config...")
        self.config = get_user_config()
        self.logger.info("User-Config geladen")

        # User Metadata Manager initialisieren (v7.0+)
        from utils.user_metadata import get_user_metadata_manager
        self.user_metadata = get_user_metadata_manager()
        self.logger.info("User-Metadata-Manager geladen")

        # i18n initialisieren (v6.2+)
        self.i18n = get_i18n()
        saved_lang = self.config.get_language()
        self.i18n.set_language(saved_lang)
        self.logger.info(f"Sprache initialisiert: {saved_lang}")

        # Datenverwaltung
        self.groups = []
        self.unassigned_datasets = []
        self.datasets_2d = []  # 2D SAXS datasets (NeXus/HDF5)

        # Plot-Einstellungen
        # v8.1: Panel-Layout (freies Grid); Hauptpanel trägt Plot-Typ und Achsenlimits
        self.plot_layout = PlotLayout()
        self.panel_axes = {}
        self.stack_mode = True
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

        # Default Plot-Settings aus Config laden (v5.4, erweitert v7.0.3)
        self.logger.debug("Prüfe auf gespeicherte Standard-Plot-Einstellungen...")
        default_settings = self.config.get_default_plot_settings()
        if default_settings:
            self.logger.info("Lade gespeicherte Standard-Plot-Einstellungen")
            self.logger.debug(f"  - Legend Settings: {list(default_settings.get('legend_settings', {}).keys())}")
            self.logger.debug(f"  - Grid Settings: {list(default_settings.get('grid_settings', {}).keys())}")
            self.logger.debug(f"  - Font Settings: {list(default_settings.get('font_settings', {}).keys())}")
            self.logger.debug(f"  - Plot Design: {default_settings.get('current_plot_design', 'Standard')}")
            self.logger.debug(f"  - Custom X-Label: {default_settings.get('custom_xlabel', None)}")
            self.logger.debug(f"  - Custom Y-Label: {default_settings.get('custom_ylabel', None)}")

            self.legend_settings = default_settings.get('legend_settings', self.legend_settings)
            self.grid_settings = default_settings.get('grid_settings', self.grid_settings)
            self.font_settings = default_settings.get('font_settings', self.font_settings)
            self.current_plot_design = default_settings.get('current_plot_design', 'Standard')
            self.custom_xlabel = default_settings.get('custom_xlabel', None)
            self.custom_ylabel = default_settings.get('custom_ylabel', None)
            if default_settings.get('axis_limits'):
                self.axis_limits = default_settings.get('axis_limits')
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

        # v7.0: Benutzer-Config Management
        load_user_config_action = QAction(tr("menu.file.load_user_config"), self)
        load_user_config_action.triggered.connect(self.load_user_config)
        file_menu.addAction(load_user_config_action)

        save_user_config_action = QAction(tr("menu.file.save_user_config_as"), self)
        save_user_config_action.triggered.connect(self.save_user_config_as)
        file_menu.addAction(save_user_config_action)

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

        # Analyse-Menü (v7.8): IFT/GIFT
        analysis_menu = menubar.addMenu(tr("menu.analysis.title"))

        gift_action = QAction(tr("menu.analysis.gift"), self)
        gift_action.setShortcut(QKeySequence("Ctrl+Shift+G"))
        gift_action.triggered.connect(lambda: self.show_gift_dialog())
        analysis_menu.addAction(gift_action)

        verify_action = QAction(tr("menu.analysis.verify_sidecar"), self)
        verify_action.triggered.connect(self.verify_gift_sidecar)
        analysis_menu.addAction(verify_action)

        # ASAXS-Auswertung (v8.1): I_A/I_N, I_cross/I_N, Korrelation
        analysis_menu.addSeparator()
        asaxs_action = QAction(tr("menu.analysis.asaxs"), self)
        asaxs_action.triggered.connect(lambda: self.show_asaxs_dialog())
        analysis_menu.addAction(asaxs_action)

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

        # v7.0: Benutzer-Metadaten Editor
        user_metadata_action = QAction(tr("menu.settings.user_metadata"), self)
        user_metadata_action.triggered.connect(self.edit_user_metadata)
        settings_menu.addAction(user_metadata_action)

        settings_menu.addSeparator()

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
        # Plot-Typ-Shortcuts (Ctrl+Shift+1-8)
        plot_types = ['Log-Log', 'Porod', 'Kratky', 'Guinier',
                      'Bragg Spacing', '2-Theta', 'PDDF', 'Azimuthal Profile']
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
        """Ändert den Plot-Typ via Shortcut (v7.0; v8.1: 'PDDF' → Vorlage Hauptplot + P(r))"""
        if plot_type in LEGACY_PLOT_TYPES:
            self.apply_legacy_plot_type(plot_type)
            return
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

        # 2D Load button on its own row
        load2d_layout = QHBoxLayout()
        load2d_btn = QPushButton(tr("2d.load_button"))
        load2d_btn.clicked.connect(self.load_2d_data)
        load2d_layout.addWidget(load2d_btn)
        layout.addLayout(load2d_layout)

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
        self.unassigned_item = QTreeWidgetItem(self.tree, [tr("tree.unassigned"), ""])
        self.unassigned_item.setExpanded(True)

        # 2D Datasets Section
        self.datasets_2d_item = QTreeWidgetItem(self.tree, [tr("tree.section_2d"), ""])
        self.datasets_2d_item.setExpanded(True)

        # Annotations & Referenzlinien Section (Version 5.3)
        self.annotations_item = QTreeWidgetItem(self.tree, [tr("tree.annotations"), ""])
        self.annotations_item.setExpanded(True)

        layout.addWidget(self.tree)

        # Optionen
        options_group = QGroupBox(tr("options.title"))
        options_layout = QGridLayout()

        # Plot-Typ
        options_layout.addWidget(QLabel(tr("options.plot_type")), 0, 0)
        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems(PANEL_TYPE_ORDER)
        self.plot_type_combo.setToolTip(tr("panels.main_type_tooltip"))
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

        # Panels (v8.1): Liste der Plot-Panels im Grid, jedes ein-/ausschaltbar
        layout.addWidget(self._create_panels_box())

        # Update Button
        update_btn = QPushButton(tr("options.update_plot"))
        update_btn.clicked.connect(self.update_plot)
        layout.addWidget(update_btn)

        return widget

    # ------------------------------------------------------------------
    # Panels (v8.1)
    # ------------------------------------------------------------------

    def _create_panels_box(self):
        """Box mit der Panel-Liste: Checkbox je Panel (an/aus), Hinzufügen,
        Entfernen, Layout-Dialog und Vorlagen."""
        box = QGroupBox(tr("panels.title"))
        box_layout = QVBoxLayout(box)

        self.panel_list = QListWidget()
        self.panel_list.setMaximumHeight(110)
        self.panel_list.setToolTip(tr("panels.list_tooltip"))
        self.panel_list.itemChanged.connect(self._on_panel_item_changed)
        self.panel_list.itemDoubleClicked.connect(
            lambda item: self.show_layout_dialog(item.data(Qt.UserRole)))
        box_layout.addWidget(self.panel_list)

        buttons = QHBoxLayout()
        add_btn = QPushButton("+")
        add_btn.setToolTip(tr("panels.add_tooltip"))
        add_menu = QMenu(add_btn)
        for panel_type in PANEL_TYPE_ORDER:
            add_menu.addAction(panel_type, lambda pt=panel_type: self.add_panel(pt))
        add_btn.setMenu(add_menu)
        buttons.addWidget(add_btn)

        remove_btn = QPushButton("−")
        remove_btn.setToolTip(tr("panels.remove_tooltip"))
        remove_btn.clicked.connect(self.remove_selected_panel)
        buttons.addWidget(remove_btn)

        layout_btn = QPushButton(tr("panels.layout_button"))
        layout_btn.setToolTip(tr("panels.layout_tooltip"))
        layout_btn.clicked.connect(lambda: self.show_layout_dialog(self._selected_panel_id()))
        buttons.addWidget(layout_btn)

        self.panel_preset_combo = QComboBox()
        self.panel_preset_combo.addItem(tr("panels.preset_placeholder"), None)
        for name in PRESET_NAMES:
            self.panel_preset_combo.addItem(tr(f"panels.preset.{name}"), name)
        self.panel_preset_combo.setToolTip(tr("panels.preset_tooltip"))
        self.panel_preset_combo.activated.connect(self._on_panel_preset_chosen)
        buttons.addWidget(self.panel_preset_combo, 1)

        box_layout.addLayout(buttons)
        self.refresh_panel_list()
        return box

    def refresh_panel_list(self):
        """Synchronisiert die Panel-Liste und die Plot-Typ-Combo mit dem Layout."""
        if not hasattr(self, 'panel_list'):
            return
        self.panel_list.blockSignals(True)
        self.panel_list.clear()
        for panel in self.plot_layout.panels:
            text = panel.name if panel.name == panel.panel_type else f"{panel.name} ({panel.panel_type})"
            if panel.is_main:
                text = f"{text} — {tr('panels.main')}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, panel.id)
            if panel.is_main:
                # Hauptpanel ist immer aktiv: Häkchen sichtbar, aber nicht umschaltbar
                item.setFlags(item.flags() & ~Qt.ItemIsUserCheckable)
            else:
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if (panel.enabled or panel.is_main) else Qt.Unchecked)
            item.setToolTip(tr("panels.item_tooltip", row=panel.row + 1, col=panel.col + 1,
                               type=panel.panel_type))
            self.panel_list.addItem(item)
        self.panel_list.blockSignals(False)

        if hasattr(self, 'plot_type_combo') and self.plot_type_combo.currentText() != self.plot_type:
            self.plot_type_combo.blockSignals(True)
            self.plot_type_combo.setCurrentText(self.plot_type)
            self.plot_type_combo.blockSignals(False)

    def _selected_panel_id(self):
        item = self.panel_list.currentItem() if hasattr(self, 'panel_list') else None
        return item.data(Qt.UserRole) if item else None

    def _on_panel_item_changed(self, item):
        panel = self.plot_layout.get(item.data(Qt.UserRole))
        if panel is None or panel.is_main:
            return
        panel.enabled = item.checkState() == Qt.Checked
        errors = self.plot_layout.validate()
        if errors:
            # z. B. Überlappung mit einem anderen aktiven Panel → Änderung zurücknehmen
            panel.enabled = not panel.enabled
            QMessageBox.warning(self, tr("panels.title"), "\n".join(errors))
            self.refresh_panel_list()
            return
        self.logger.info(f"Panel '{panel.name}' {'aktiviert' if panel.enabled else 'deaktiviert'}")
        self.update_plot()

    def add_panel(self, panel_type):
        """Hängt ein neues Panel des gewählten Typs an (erste freie Zelle bzw. neue Zeile).
        q-Raum-Panels unter dem Hauptpanel teilen dessen X-Achse."""
        layout = self.plot_layout
        panel = layout.add_panel(panel_type)
        main = layout.main
        if (panel.type_info.x_domain == main.type_info.x_domain
                and panel.col == main.col and panel.row == main.row + main.rowspan):
            panel.share_x_with = MAIN_ID
        self.logger.info(f"Panel '{panel.name}' hinzugefügt (Zeile {panel.row + 1}, Spalte {panel.col + 1})")
        self.refresh_panel_list()
        self.update_plot()
        return panel

    def ensure_panel(self, panel_type):
        """Sorgt dafür, dass ein aktives Panel des Typs existiert (aktiviert ein
        vorhandenes oder legt eines an). Gibt das Panel zurück."""
        if self.plot_type == panel_type:
            return self.plot_layout.main
        for panel in self.plot_layout.panels:
            if panel.panel_type == panel_type:
                if not panel.enabled:
                    panel.enabled = True
                    if self.plot_layout.validate():
                        panel.enabled = False
                        continue
                    self.refresh_panel_list()
                    self.update_plot()
                return panel
        return self.add_panel(panel_type)

    def remove_selected_panel(self):
        panel_id = self._selected_panel_id()
        if panel_id is None:
            return
        if panel_id == MAIN_ID:
            QMessageBox.information(self, tr("panels.title"), tr("panels.cannot_remove_main"))
            return
        panel = self.plot_layout.get(panel_id)
        self.plot_layout.remove_panel(panel_id)
        self.plot_layout.compact()
        # Gruppen-Zuordnungen auf das entfernte Panel lösen
        for group in self.groups:
            if group.panel_ids is not None and panel_id in group.panel_ids:
                group.panel_ids = [pid for pid in group.panel_ids if pid != panel_id] or None
        for item in self.annotations + self.reference_lines:
            if item.get('panel_id') == panel_id:
                item['panel_id'] = MAIN_ID
        self.logger.info(f"Panel '{panel.name}' entfernt")
        self.refresh_panel_list()
        self.rebuild_tree()
        self.update_plot()

    def _on_panel_preset_chosen(self, index):
        name = self.panel_preset_combo.itemData(index)
        self.panel_preset_combo.setCurrentIndex(0)
        if name:
            self.apply_layout_preset(name)

    def apply_layout_preset(self, name):
        """Ersetzt das Layout durch eine Vorlage; Hauptpanel-Typ und -Achsen bleiben."""
        main = self.plot_layout.main
        self.plot_layout = PlotLayout.preset(name, main.panel_type, dict(main.axis))
        self.plot_layout.main.title = main.title
        self._drop_stale_panel_refs()
        self.logger.info(f"Panel-Vorlage '{name}' angewendet")
        self.refresh_panel_list()
        self.rebuild_tree()
        self.update_plot()

    def apply_legacy_plot_type(self, name):
        """Früherer Plot-Typ (z. B. Shortcut oder Skript): 'PDDF', 'Significance',
        'ASAXS' und 'ASAXS+sub' werden auf Panel-Vorlagen abgebildet."""
        with_sub = name.endswith('+sub')
        name = name.replace('+sub', '')
        if name in LEGACY_PLOT_TYPES:
            main_type, preset, enabled = LEGACY_PLOT_TYPES[name]
            self.plot_type = main_type
            self.apply_layout_preset(preset)
            sub = self.plot_layout.get('sub')
            if sub is not None:
                sub.enabled = enabled or with_sub
            self.refresh_panel_list()
            self.update_plot()
        else:
            self.plot_type_combo.setCurrentText(name)

    def _drop_stale_panel_refs(self):
        """Entfernt Verweise auf nicht mehr existierende Panels (Gruppen, Annotationen)."""
        ids = {p.id for p in self.plot_layout.panels}
        for group in self.groups:
            if group.panel_ids is not None:
                group.panel_ids = [pid for pid in group.panel_ids if pid in ids] or None
        for item in self.annotations + self.reference_lines:
            if item.get('panel_id') not in (None, *ids):
                item['panel_id'] = MAIN_ID

    def show_layout_dialog(self, panel_id=None):
        """Öffnet den Layout-Dialog (Grid, Panel-Typen, Kopplung, Optionen)."""
        from dialogs.plot_layout_dialog import PlotLayoutDialog
        dialog = PlotLayoutDialog(self, self.plot_layout, select_panel_id=panel_id)
        if dialog.exec():
            self.plot_layout = dialog.get_layout()
            self._drop_stale_panel_refs()
            self.logger.info(f"Panel-Layout aktualisiert: {self.plot_layout.rows}×{self.plot_layout.cols}, "
                             f"{len(self.plot_layout.enabled_panels())} aktive Panels")
            self.refresh_panel_list()
            self.rebuild_tree()
            self.update_plot()

    def panel_label(self, panel_id):
        """Anzeigename eines Panels (für Tree-Tooltips und Menüs)."""
        panel = self.plot_layout.get(panel_id)
        return panel.name if panel else panel_id

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
        """Aktualisiert den Plot (v8.1: flexibles Panel-Grid, siehe core/plot_layout.py)"""
        self.stack_mode = self.stack_checkbox.isChecked()
        self.logger.debug(f"Plot-Update: Stack={self.stack_mode}, Gruppen={len(self.groups)}, Unassigned={len(self.unassigned_datasets)}")

        # v7.0: Tree-Reihenfolge für Plot und Legende verwenden
        ordered_groups, ordered_unassigned = self.get_tree_order()
        self.logger.debug(f"  Tree-Order: {len(ordered_groups)} Gruppen, {len(ordered_unassigned)} unassigned")

        # Figure leeren (Warnung bei log-Skala unterdrücken)
        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='.*non-positive.*')
            self.fig.clear()

        layout = self.plot_layout
        layout_errors = layout.validate()
        if layout_errors:
            # Ungültiges Layout (sollte der Layout-Dialog verhindern): nur Hauptpanel zeichnen
            self.logger.warning(f"Ungültiges Panel-Layout, zeichne nur Hauptpanel: {layout_errors}")
            panels = [layout.main]
        else:
            panels = layout.enabled_panels()

        self.panel_axes = self._build_axes(layout, panels)
        self.ax_main = self.panel_axes[MAIN_ID]

        # Kurven sammeln (Farbe einmal pro Datensatz) und auf Panels verteilen
        curves = self._collect_curves(ordered_groups, ordered_unassigned)
        routed = {panel.id: [] for panel in panels}
        for curve in curves:
            for panel in self._route_curve(curve, panels):
                routed[panel.id].append(curve)

        for panel in panels:
            self._render_panel(panel, self.panel_axes[panel.id], routed[panel.id])
        self._hide_shared_x_labels(panels)

        # Legenden (v8.1: pro Panel 'all' | 'own' | 'off')
        for panel in panels:
            if panel.legend == 'off':
                continue
            only = None
            if panel.legend == 'own':
                only = {id(c.dataset) for c in routed[panel.id]}
            self._render_legend(self.panel_axes[panel.id], ordered_groups, ordered_unassigned, only)

        self._render_reference_lines()
        self._render_annotations()
        has_multi = len(panels) > 1
        title_active = self._render_titles(panels, has_multi)

        # tight_layout() mit Fehlerbehandlung für ungültiges MathText (v6.2)
        # und stem plots (die manchmal tight_layout stören).
        # Mit mehreren Panels + Titel: Platz für suptitle; ohne Titel: kleiner Top-Rand
        if has_multi and title_active:
            _tl_rect = [0, 0, 1, 0.93]
        elif has_multi:
            _tl_rect = [0, 0, 1, 0.98]
        else:
            _tl_rect = None
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', message='.*tight_layout.*')
                if _tl_rect:
                    self.fig.tight_layout(rect=_tl_rect)
                else:
                    self.fig.tight_layout()
        except ValueError as e:
            # MathText-Parsing-Fehler (z.B. nicht geschlossene Klammern in LaTeX)
            error_msg = str(e)
            if "ParseException" in error_msg or "Expected end of text" in error_msg:
                self.logger.warning(f"MathText-Fehler in Legende ignoriert: {error_msg[:100]}...")
            else:
                raise
        except Exception as e:
            # Andere Fehler loggen aber nicht abstürzen (z.B. stem plots)
            self.logger.debug(f"tight_layout fehlgeschlagen: {e}")

        self.canvas.draw()

    # ------------------------------------------------------------------
    # Panel-Rendering (v8.1)
    # ------------------------------------------------------------------

    def _build_axes(self, layout, panels):
        """Legt für jedes aktive Panel eine Achse im GridSpec an. Panels, deren
        X-Achse gekoppelt ist, werden nach ihrem Kopplungsziel erzeugt (sharex)."""
        gs = GridSpec(layout.rows, layout.cols, figure=self.fig,
                      height_ratios=layout.row_ratios, width_ratios=layout.col_ratios,
                      hspace=layout.hspace, wspace=layout.wspace)
        axes = {}
        for panel in layout.creation_order(panels):
            share = axes.get(panel.share_x_with) if panel.share_x_with else None
            cell = gs[panel.row:panel.row + panel.rowspan, panel.col:panel.col + panel.colspan]
            axes[panel.id] = self.fig.add_subplot(cell, sharex=share)
        return axes

    def _collect_curves(self, ordered_groups, ordered_unassigned):
        """Sichtbare Kurven in Tree-Reihenfolge. Farben werden hier – unabhängig von
        der Anzahl der Panels – genau einmal pro Datensatz vergeben."""
        color_scheme = self.color_scheme_combo.currentText()
        colors = self.config.color_schemes.get(color_scheme, self.config.color_schemes['TUBAF'])
        color_cycle = iter(colors * 10)  # Genug Farben

        def usable(dataset):
            # Checkbox steuert Sichtbarkeit komplett
            if not dataset.show_in_legend:
                return False
            # Überspringe Datasets ohne geladene Daten (z.B. fehlende Dateien)
            if not dataset.data_loaded:
                self.logger.warning(f"  Dataset '{dataset.name}' übersprungen (Daten nicht geladen)")
                return False
            return True

        def color_for(dataset, cycle):
            if not dataset.color:
                dataset.color = next(cycle)
            return dataset.color

        curves = []
        for group, datasets_in_order in ordered_groups:
            if not group.visible:
                continue
            # Stack-Faktor direkt von der Gruppe verwenden (NICHT kumulativ!)
            stack_factor = group.stack_factor if self.stack_mode else 1.0
            # Gruppenspezifische Farbpalette (v5.4)
            if group.color_scheme:
                group_colors = self.config.color_schemes.get(group.color_scheme, colors)
                group_cycle = iter(group_colors * 10)
            else:
                group_cycle = color_cycle
            for dataset in datasets_in_order:
                if usable(dataset):
                    curves.append(_Curve(dataset, group, color_for(dataset, group_cycle), stack_factor))

        # Nicht zugeordnete Datensätze (ohne Stack-Faktor)
        for dataset in ordered_unassigned:
            if usable(dataset):
                curves.append(_Curve(dataset, None, color_for(dataset, color_cycle), 1.0))
        return curves

    def _route_curve(self, curve, panels):
        """Bestimmt die Panels, in denen eine Kurve gezeichnet wird.

        - Gruppe ohne feste Zuordnung (panel_ids=None) und nicht zugeordnete Datensätze:
          alle aktiven Panels, deren Typ den Datensatz akzeptiert (z. B. P(r)-Daten nur
          im P(r)-Panel); akzeptiert keines, landet er im Hauptpanel.
        - Feste Zuordnung: davon die akzeptierenden Panels; akzeptiert keines, wird die
          Zuordnung erzwungen (wie früher 'main'/'sub' bei PDDF). Sind alle zugeordneten
          Panels deaktiviert, wird im Hauptpanel gezeichnet.
        """
        main = next(p for p in panels if p.id == MAIN_ID)
        panel_ids = curve.group.panel_ids if curve.group is not None else None
        if panel_ids is None:
            candidates, explicit = panels, False
        else:
            candidates = [p for p in panels if p.id in panel_ids]
            explicit = True
            if not candidates:
                return [main]
        accepted = [p for p in candidates if p.type_info.accepts(curve.dataset)]
        if accepted:
            return accepted
        return candidates if explicit else [main]

    def _prepare_xy(self, dataset):
        """Kopie der Daten, gefiltert mit den individuellen Plotgrenzen (v5.7)."""
        x = dataset.x.copy()
        y = dataset.y.copy()
        y_err = dataset.y_err.copy() if dataset.y_err is not None else None
        mask = np.ones(len(x), dtype=bool)
        if dataset.x_min is not None:
            mask &= (x >= dataset.x_min)
        if dataset.x_max is not None:
            mask &= (x <= dataset.x_max)
        if dataset.y_min is not None:
            mask &= (y >= dataset.y_min)
        if dataset.y_max is not None:
            mask &= (y <= dataset.y_max)
        return x[mask], y[mask], (y_err[mask] if y_err is not None else None)

    def _panel_scales(self, panel):
        """Effektive (xscale, yscale) eines Panels: Override aus dem Achsen-Dialog
        oder Standard des Panel-Typs."""
        info = panel.type_info
        return (panel.axis.get('xscale') or info.xscale,
                panel.axis.get('yscale') or info.yscale)

    def _render_panel(self, panel, ax, curves):
        """Zeichnet alle Kurven eines Panels und formatiert dessen Achsen."""
        info = panel.type_info
        xscale, yscale = self._panel_scales(panel)
        ctx = {'wavelength': self.wavelength, 'options': panel.options}
        symlog_abs_vals = []  # sammelt |y| für die linthresh-Bestimmung bei symlog

        if info.zero_line:
            ax.axhline(0, color='gray', lw=0.8, ls='--', zorder=0)
        if info.renderer == 'significance':
            for level in self._get_significance_thresholds(panel):
                ax.axhline(level, color='gray', lw=0.8, ls='--', zorder=0)
                ax.text(0.01, level, f'{level:g}σ', transform=ax.get_yaxis_transform(),
                        fontsize=8, color='gray', va='bottom', ha='left')

        for curve in curves:
            dataset, color = curve.dataset, curve.color
            x, y, y_err = self._prepare_xy(dataset)
            x, y, y_err = info.transform(x, y, y_err, ctx)
            if not info.show_errors:
                y_err = None
            stack = curve.stack_factor if panel.apply_stack else 1.0
            y = y * stack
            if y_err is not None:
                y_err = y_err * stack

            if info.renderer == 'significance':
                self._render_significance(ax, x, y, y_err, dataset, color, panel)
                continue

            # ASAXS Cross-Term: bei log-Skala nur positive Werte (symlog und linear
            # zeigen auch die negativen Werte)
            if getattr(dataset, 'data_term', '') == 'cross' and yscale == 'log':
                pos = y > 0
                if not np.any(pos):
                    continue
                x, y = x[pos], y[pos]
                if y_err is not None:
                    y_err = y_err[pos]

            if yscale == 'symlog':
                nonzero = y[y != 0]
                if nonzero.size:
                    symlog_abs_vals.append(np.abs(nonzero))

            self._render_curve(ax, x, y, y_err, dataset, color, yscale)

        self._style_axes(panel, ax, xscale, yscale, symlog_abs_vals)

    def _render_curve(self, ax, x, y, y_err, dataset, color, yscale, label=None):
        """Zeichnet einen Datensatz (SNR-Marker, Stem, Fehlerfläche/-balken oder Linie)."""
        if label is None:
            label = dataset.display_label
        plot_style = dataset.get_plot_style()
        errorbar_style = getattr(dataset, 'errorbar_style', 'fill')
        line_alpha = getattr(dataset, 'line_alpha', 1.0)

        # SNR-Qualitätsmarker (wenn aktiviert und Fehlerdaten vorhanden)
        if getattr(dataset, 'snr_visualization', False) and y_err is not None and len(x) > 0:
            self._render_snr_markers(ax, x, y, y_err, dataset, color, yscale, label=label)
        # Spezialfall: stem plot für XRD-Referenz
        elif errorbar_style == 'stem':
            markerline, stemlines, baseline = ax.stem(
                x, y,
                linefmt=color,
                markerfmt=dataset.marker_style if dataset.marker_style else 'o',
                basefmt=' '
            )
            markerline.set_markerfacecolor(color)
            markerline.set_markeredgecolor(color)
            markerline.set_markersize(dataset.marker_size)
            stemlines.set_linewidth(dataset.line_width)
            stemlines.set_alpha(dataset.errorbar_alpha)
            markerline.set_alpha(line_alpha)
            ax.plot([], [], color=color, marker=dataset.marker_style if dataset.marker_style else 'o',
                    markersize=dataset.marker_size, linestyle='', label=label, alpha=line_alpha)
        # Fehlerbalken plotten wenn vorhanden und aktiviert (v6.0)
        elif y_err is not None and dataset.show_errorbars:
            if errorbar_style == 'fill':
                ax.fill_between(x, y - y_err, y + y_err, alpha=dataset.errorbar_alpha, color=color)
                ax.plot(x, y, plot_style, color=color, label=label, alpha=line_alpha,
                        linewidth=dataset.line_width, markersize=dataset.marker_size)
            else:  # 'bars'
                container = ax.errorbar(
                    x, y, yerr=np.abs(y_err),
                    fmt=plot_style,
                    color=color,
                    label=label,
                    linewidth=dataset.line_width,
                    markersize=dataset.marker_size,
                    capsize=dataset.errorbar_capsize,
                    elinewidth=dataset.errorbar_linewidth,
                    alpha=line_alpha,
                    ecolor=color,
                    capthick=dataset.errorbar_linewidth
                )
                # Fehlerbalken/Caps behalten ihre eigene Transparenz
                for artist in list(container.lines[1]) + list(container.lines[2]):
                    artist.set_alpha(dataset.errorbar_alpha)
        else:
            ax.plot(x, y, plot_style, color=color, label=label, alpha=line_alpha,
                    linewidth=dataset.line_width, markersize=dataset.marker_size)

    def _axis_label(self, override, default):
        """Achsentitel: Override (MathText) oder formatierter Standard des Panel-Typs."""
        if override:
            return preprocess_mathtext(override)
        return self.convert_to_mathtext(self.format_axis_label(default))

    def _style_axes(self, panel, ax, xscale, yscale, symlog_abs_vals):
        """Achsentitel, Skalen, Ticks, Grid und Limits eines Panels (für alle Panels gleich)."""
        info = panel.type_info
        xlabel = self._axis_label(panel.axis.get('xlabel'), info.xlabel)
        ylabel = self._axis_label(panel.axis.get('ylabel'), info.default_ylabel(panel.options))

        # Achsenbeschriftungen mit erweiterten Font-Optionen (v5.3)
        label_weight = 'bold' if self.font_settings.get('labels_bold', False) else 'normal'
        label_style = 'italic' if self.font_settings.get('labels_italic', False) else 'normal'

        # Unterstrichen wird via LaTeX unterstützt (falls aktiviert)
        if self.font_settings.get('labels_underline', False):
            xlabel = r'$\underline{' + xlabel.replace('$', '') + r'}$'
            ylabel = r'$\underline{' + ylabel.replace('$', '') + r'}$'

        font_kwargs = dict(
            fontsize=self.font_settings.get('labels_size', 12),
            weight=label_weight, style=label_style,
            fontfamily=self.font_settings.get('labels_font_family',
                                              self.font_settings.get('font_family', 'sans-serif')),
        )
        ax.set_xlabel(xlabel, **font_kwargs)
        ax.set_ylabel(ylabel, **font_kwargs)

        # Skalen (X nur setzen, wenn die Achse nicht von einem anderen Panel geerbt wird)
        if not panel.share_x_with:
            ax.set_xscale(xscale)
        if yscale == 'symlog':
            linthresh = self._compute_symlog_linthresh(
                symlog_abs_vals, decades=panel.axis.get('symlog_decades', 4))
            linscale = panel.axis.get('symlog_linscale') or 1.0
            ax.set_yscale('symlog', linthresh=linthresh, linscale=linscale)
        else:
            ax.set_yscale(yscale)

        # X-Limits: Plot-Typ-spezifische Defaults (z. B. Azimutalprofil → −180 … 180)
        if panel.axis.get('auto', True) and info.xlim and not panel.share_x_with:
            ax.set_xlim(*info.xlim)

        # Tick-Einstellungen (v5.7: Erweitert um Länge, Breite, Richtung)
        tick_weight = 'bold' if self.font_settings.get('ticks_bold', False) else 'normal'
        tick_style = 'italic' if self.font_settings.get('ticks_italic', False) else 'normal'
        tick_labelsize = self.grid_settings.get('tick_labelsize', self.font_settings.get('ticks_size', 10))

        ax.tick_params(
            axis='both', which='major',
            direction=self.grid_settings.get('major_tick_direction', 'in'),
            length=self.grid_settings.get('major_tick_length', 6.0),
            width=self.grid_settings.get('major_tick_width', 1.0),
            labelsize=tick_labelsize
        )
        if self.grid_settings.get('minor_ticks_enable', True):
            ax.tick_params(
                axis='both', which='minor',
                direction=self.grid_settings.get('minor_tick_direction', 'in'),
                length=self.grid_settings.get('minor_tick_length', 3.0),
                width=self.grid_settings.get('minor_tick_width', 0.5)
            )

        # Font-Eigenschaften für Tick-Labels anwenden
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontweight(tick_weight)
            label.set_fontstyle(tick_style)
            label.set_fontfamily(self.font_settings.get('ticks_font_family',
                                                        self.font_settings.get('font_family', 'sans-serif')))

        # Tick-Label-Rotation (v5.7)
        x_rotation = self.grid_settings.get('x_tick_rotation', 0)
        y_rotation = self.grid_settings.get('y_tick_rotation', 0)
        if x_rotation != 0:
            ax.tick_params(axis='x', rotation=x_rotation)
        if y_rotation != 0:
            ax.tick_params(axis='y', rotation=y_rotation)

        # Grid-Einstellungen (erweitert in v5.1)
        if self.grid_settings['major_enable']:
            ax.grid(True, which='major',
                    axis=self.grid_settings['major_axis'],
                    linestyle=self.grid_settings['major_linestyle'],
                    linewidth=self.grid_settings['major_linewidth'],
                    color=self.grid_settings['major_color'],
                    alpha=self.grid_settings['major_alpha'])
        if self.grid_settings['minor_enable']:
            ax.minorticks_on()
            ax.grid(True, which='minor',
                    axis=self.grid_settings['minor_axis'],
                    linestyle=self.grid_settings['minor_linestyle'],
                    linewidth=self.grid_settings['minor_linewidth'],
                    color=self.grid_settings['minor_color'],
                    alpha=self.grid_settings['minor_alpha'])

        # Achsenlimits (X nur bei unabhängiger X-Achse)
        if not panel.axis.get('auto', True):
            if not panel.share_x_with:
                if panel.axis.get('xmin') is not None:
                    ax.set_xlim(left=panel.axis['xmin'])
                if panel.axis.get('xmax') is not None:
                    ax.set_xlim(right=panel.axis['xmax'])
            if panel.axis.get('ymin') is not None:
                ax.set_ylim(bottom=panel.axis['ymin'])
            if panel.axis.get('ymax') is not None:
                ax.set_ylim(top=panel.axis['ymax'])

    def _hide_shared_x_labels(self, panels):
        """Bei gekoppelter X-Achse: X-Titel und Tick-Beschriftung eines Panels
        ausblenden, wenn direkt darunter (gleiche Spalten) ein Panel derselben
        Kopplungsgruppe liegt – wie bei den früheren ASAXS-/Significance-Subplots."""
        def root(p):
            seen = set()
            while p.share_x_with and p.id not in seen:
                seen.add(p.id)
                nxt = self.plot_layout.get(p.share_x_with)
                if nxt is None:
                    break
                p = nxt
            return p.id

        for upper in panels:
            for lower in panels:
                if lower is upper or root(lower) != root(upper):
                    continue
                if lower.row != upper.row + upper.rowspan:
                    continue
                cols_upper = set(range(upper.col, upper.col + upper.colspan))
                cols_lower = set(range(lower.col, lower.col + lower.colspan))
                if cols_upper & cols_lower:
                    ax = self.panel_axes[upper.id]
                    ax.set_xlabel('')
                    ax.tick_params(axis='x', labelbottom=False)
                    break

    def _render_legend(self, ax, ordered_groups, ordered_unassigned, only=None):
        """Legende (v5.1/v5.3/v5.7/v7.0: Tree-Order, individuelle Formatierung).

        `only`: Menge von id(dataset) – nur diese Datensätze (Legenden-Modus 'own');
        None = alle sichtbaren Datensätze (Modus 'all').
        """
        from matplotlib.lines import Line2D

        def include(dataset):
            return (dataset.show_in_legend and getattr(dataset, 'legend_visible', True)
                    and dataset.data_loaded and (only is None or id(dataset) in only))

        def dataset_handle(dataset):
            marker = dataset.marker_style if dataset.marker_style else 'o'
            linestyle = dataset.line_style if dataset.line_style else ''
            # Wenn kein expliziter Stil, dann aus dem Auto-Stil ableiten
            if not dataset.marker_style and not dataset.line_style:
                if dataset.is_fit_curve():
                    linestyle, marker = '-', ''
                else:
                    marker, linestyle = 'o', ''
            return Line2D([0], [0], color=dataset.color, marker=marker, linestyle=linestyle,
                          linewidth=dataset.line_width, markersize=dataset.marker_size,
                          alpha=getattr(dataset, 'line_alpha', 1.0))

        handles, labels = [], []
        # Globale Legenden-Schrift (Fett/Kursiv) gilt zusätzlich zur Formatierung je Eintrag
        all_bold = self.font_settings.get('legend_bold', False)
        all_italic = self.font_settings.get('legend_italic', False)

        def add(handle, text, bold, italic):
            handles.append(handle)
            labels.append(format_legend_text(text, bold or all_bold, italic or all_italic))

        for group, datasets_in_order in ordered_groups:
            if not group.visible or not datasets_in_order:
                continue
            members = [ds for ds in datasets_in_order if include(ds)]
            if only is not None and not members:
                continue
            # Gruppe als Label hinzufügen, falls gewünscht (unsichtbares Dummy-Handle)
            if getattr(group, 'show_in_legend', True):
                add(Line2D([0], [0], color='none', marker='', linestyle=''),
                    getattr(group, 'display_label', group.name),
                    getattr(group, 'legend_bold', False), getattr(group, 'legend_italic', False))
            for dataset in members:
                add(dataset_handle(dataset), dataset.display_label,
                    getattr(dataset, 'legend_bold', False), getattr(dataset, 'legend_italic', False))

        for dataset in ordered_unassigned:
            if include(dataset):
                add(dataset_handle(dataset), dataset.display_label,
                    getattr(dataset, 'legend_bold', False), getattr(dataset, 'legend_italic', False))

        if not handles:
            return

        # v7.0: Reihenfolge invertieren falls gewünscht (für gestackte Kurven)
        if self.legend_settings.get('reverse_order', False):
            handles, labels = handles[::-1], labels[::-1]

        legend = ax.legend(
            handles, labels,
            loc=self.legend_settings['position'],
            fontsize=self.font_settings.get('legend_size', self.legend_settings.get('fontsize', 10)),
            ncol=self.legend_settings['ncol'],
            frameon=self.legend_settings['frameon'],
            shadow=self.legend_settings['shadow'],
            fancybox=self.legend_settings['fancybox']
        )
        if legend:
            if legend.get_frame():
                legend.get_frame().set_alpha(self.legend_settings['alpha'])
            # v7.0: Formatierung erfolgt über MathText, nur noch Font-Familie setzen
            for text in legend.get_texts():
                text.set_fontfamily(self.font_settings.get('font_family', 'sans-serif'))

    def _axes_for_panel_id(self, panel_id):
        """Achse eines Panels; Fallback Hauptpanel (z. B. wenn das Panel deaktiviert ist)."""
        return self.panel_axes.get(panel_id or MAIN_ID, self.ax_main)

    def _render_reference_lines(self):
        """Referenzlinien (v5.2; v8.1: pro Panel über 'panel_id')."""
        for ref_line in self.reference_lines:
            ax = self._axes_for_panel_id(ref_line.get('panel_id'))
            if ref_line['type'] == 'vertical':
                ax.axvline(x=ref_line['value'], linestyle=ref_line['linestyle'],
                           linewidth=ref_line['linewidth'], color=ref_line['color'],
                           alpha=ref_line['alpha'])
                if ref_line['label']:
                    # Label oben rechts an der Linie
                    ylim = ax.get_ylim()
                    ax.text(ref_line['value'], ylim[1] * 0.95, ref_line['label'],
                            rotation=90, va='top', ha='right',
                            fontsize=10, color=ref_line['color'])
            else:  # horizontal
                ax.axhline(y=ref_line['value'], linestyle=ref_line['linestyle'],
                           linewidth=ref_line['linewidth'], color=ref_line['color'],
                           alpha=ref_line['alpha'])
                if ref_line['label']:
                    # Label rechts an der Linie
                    xlim = ax.get_xlim()
                    ax.text(xlim[1] * 0.95, ref_line['value'], ref_line['label'],
                            ha='right', va='bottom', fontsize=10, color=ref_line['color'])

    def _render_annotations(self):
        """Annotations (v5.2, 5.3: draggable, v7.0: MathText, v8.1: pro Panel)."""
        self.annotation_texts = []  # Text-Objekte speichern für draggable
        for idx, annotation in enumerate(self.annotations):
            ax = self._axes_for_panel_id(annotation.get('panel_id'))
            text_obj = ax.text(
                annotation['x'], annotation['y'],
                preprocess_mathtext(annotation['text']),
                fontsize=annotation['fontsize'],
                color=annotation['color'],
                rotation=annotation['rotation'],
                ha='left', va='bottom',
                picker=True,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.1, edgecolor='none')
            )
            text_obj.set_picker(5)  # Pickable mit Toleranz von 5 Pixeln
            text_obj._annotation_idx = idx
            self.annotation_texts.append(text_obj)

    def _render_titles(self, panels, has_multi):
        """Figurentitel und Panel-Titel. Bei mehreren Panels läuft der Haupttitel als
        fig.suptitle() über dem ganzen Grid, damit tight_layout ihn nicht abschneidet.

        Returns:
            True, wenn ein Haupttitel gezeichnet wurde.
        """
        title_active = bool(self.title_settings.get('enabled', False) and self.title_settings.get('text'))
        title_weight = 'bold' if self.title_settings.get('bold', True) else 'normal'
        title_style = 'italic' if self.title_settings.get('italic', False) else 'normal'
        title_color = self.title_settings.get('color', '#000000')
        title_size = self.title_settings.get('size', 14)

        if title_active:
            if has_multi:
                title_obj = self.fig.suptitle(
                    self.title_settings['text'],
                    fontsize=title_size, fontweight=title_weight, fontstyle=title_style,
                    color=title_color,
                    x={'left': 0.05, 'right': 0.95}.get(self.title_settings.get('position', 'center'), 0.5),
                    ha=self.title_settings.get('position', 'center'),
                )
            else:
                title_obj = self.ax_main.set_title(
                    self.title_settings['text'],
                    fontsize=title_size, fontweight=title_weight, fontstyle=title_style,
                    color=title_color, loc=self.title_settings.get('position', 'center'),
                )
            # Hintergrund (falls aktiviert)
            if self.title_settings.get('background_color'):
                title_obj.set_bbox(dict(
                    boxstyle='round,pad=0.5',
                    facecolor=self.title_settings['background_color'],
                    alpha=self.title_settings.get('background_alpha', 0.8),
                    edgecolor='none'
                ))

        # Panel-Titel (nur bei mehreren Panels; Schrift wie Haupttitel, etwas kleiner)
        if has_multi:
            for panel in panels:
                if panel.title:
                    self.panel_axes[panel.id].set_title(
                        preprocess_mathtext(panel.title),
                        fontsize=max(title_size - 2, 6), fontweight=title_weight,
                        fontstyle=title_style, color=title_color,
                    )
        return title_active

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

    def _render_snr_markers(self, ax, x, y, y_err, dataset, color, yscale, label=None):
        """Rendert Datenpunkte mit SNR-basierten Qualitätsmarkern.

        Gute Punkte (SNR ≥ Schwellenwert): konfigurierbarer gefüllter Marker.
        Schlechte Punkte (SNR < Schwellenwert): konfigurierbarer offener Marker, gedimmt.
        Einstellungen stammen aus den dataset.snr_* Attributen.
        """
        threshold = getattr(dataset, 'snr_threshold', 1.0)
        good_marker = getattr(dataset, 'snr_good_marker', 'o') or 'o'
        poor_marker = getattr(dataset, 'snr_poor_marker', '^') or '^'
        poor_alpha = getattr(dataset, 'snr_poor_alpha', 0.3)
        show_eb = getattr(dataset, 'snr_show_errorbars', True)

        with np.errstate(invalid='ignore', divide='ignore'):
            snr = np.abs(y) / np.abs(y_err)

        mask_good = (snr >= threshold) & np.isfinite(snr)
        mask_poor = (snr < threshold) & np.isfinite(snr)

        # Bei log-Skala nur positive y-Werte
        if yscale == 'log':
            pos = y > 0
            mask_good &= pos
            mask_poor &= pos

        if label is None:
            label = dataset.display_label

        marker_s = max(float(dataset.marker_size), 2.0) ** 2 * 3.5
        label_shown = False

        if np.any(mask_good):
            ax.scatter(x[mask_good], y[mask_good],
                       marker=good_marker, s=marker_s, color=color, zorder=3,
                       label=label, alpha=getattr(dataset, 'line_alpha', 1.0))
            label_shown = True

        if np.any(mask_poor):
            ax.scatter(x[mask_poor], y[mask_poor],
                       marker=poor_marker, s=marker_s * 0.85,
                       facecolors='none', edgecolors=color, alpha=poor_alpha, zorder=3)

        if not label_shown:
            ax.plot([], [], color=color, marker=good_marker, linestyle='',
                    markersize=dataset.marker_size, label=label)

        # Optionale Fehlerbalken auf alle sichtbaren Punkte
        if show_eb:
            all_vis = mask_good | mask_poor
            if np.any(all_vis):
                ax.errorbar(x[all_vis], y[all_vis], yerr=y_err[all_vis],
                            fmt='none', ecolor=color, elinewidth=0.8,
                            capsize=2, capthick=0.8, alpha=0.3, zorder=2)

    def _get_significance_thresholds(self, panel):
        """σ-Schwellenwerte für die gestrichelten Referenzlinien eines Significance-Panels
        (Panel-Option 'thresholds', Fallback: 3, 2, 1)."""
        values = []
        for v in panel.options.get('thresholds') or []:
            try:
                values.append(float(v))
            except (TypeError, ValueError):
                continue
        return values if values else [3.0, 2.0, 1.0]

    def _significance_window(self):
        """Glättungsfenster des ersten Significance-Panels (Default 9), z. B. für GIFT."""
        for panel in self.plot_layout.panels:
            if panel.panel_type == 'Significance':
                return int(panel.options.get('window', 9))
        return 9

    def _render_significance(self, ax, x, y, y_err, dataset, color, panel):
        """Rendert die punktweise Signifikanz |I(q)/σ(q)|:
        dünn = Rohdaten, dick = über ein gleitendes Median-Fenster geglättet
        (robust gegen einzelne Ausreißer-Rauschspitzen)."""
        if y_err is None or len(x) == 0:
            return
        significance = compute_significance(y, y_err)
        ax.plot(x, significance, '-', color=color,
                linewidth=max(dataset.line_width * 0.6, 0.5), alpha=0.4)
        smoothed = self._rolling_median(significance, int(panel.options.get('window', 9)))
        ax.plot(x, smoothed, '-', color=color, linewidth=dataset.line_width * 1.8)

    @staticmethod
    def _rolling_median(arr, window):
        """Zentrierter gleitender Median (siehe analysis.significance.rolling_median)."""
        return rolling_median(arr, window)

    def _compute_symlog_linthresh(self, abs_val_arrays, decades=4):
        """Bestimmt linthresh für die symlog-Skala aus der Anzahl gewünschter Dekaden.

        `decades` gibt an, über wie viele Zehnerpotenzen unterhalb des größten
        angezeigten |y|-Werts noch logarithmisch skaliert wird, bevor die Skala
        in den linearen Bereich um Null übergeht. Ein kleinerer Wert komprimiert
        den Plot (weniger Dekaden bis Null), ein größerer Wert dehnt ihn.
        Statt vom kleinsten Datenwert auszugehen (der z. B. bei verrauschten
        ASAXS-Cross-Term-Daten nahe Null liegen und den Plot unnötig
        auseinanderziehen kann), wird vom größten Wert abwärts gerechnet.
        """
        decades = max(1, int(decades))
        if abs_val_arrays:
            combined = np.concatenate(abs_val_arrays)
            combined = combined[np.isfinite(combined) & (combined > 0)]
            if combined.size:
                max_val = np.max(combined)
                return float(10 ** (np.floor(np.log10(max_val)) - decades))
        return 1e-3

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
        q_types = {'Log-Log', 'Porod', 'Kratky', 'PDDF', 'ASAXS', 'dlnI/dlnq', 'Significance', 'I linear'}

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
        if event.inaxes is None:
            return

        # Prüfen, ob ein Text-Objekt angeklickt wurde (v8.1: in jedem Panel)
        for text_obj in getattr(self, 'annotation_texts', []):
            if text_obj.axes is not event.inaxes:
                continue
            contains, _ = text_obj.contains(event)
            if contains:
                self._dragged_annotation = text_obj
                self._drag_start_pos = (event.xdata, event.ydata)
                break

    def on_annotation_motion(self, event):
        """Maus-Motion für Annotation-Drag (Version 5.3)"""
        if not hasattr(self, '_dragged_annotation') or self._dragged_annotation is None:
            return
        if event.inaxes is not self._dragged_annotation.axes:
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
            group_item.setFlags(group_item.flags() | Qt.ItemIsUserCheckable)
            group_item.setCheckState(0, Qt.Checked if group.visible else Qt.Unchecked)
            group_item.setData(0, Qt.UserRole, ('group', group))

            QMessageBox.information(self, tr("messages.success"), tr("messages.group_created", name=name))
        else:
            self.logger.debug("Gruppen-Dialog abgebrochen")

    def auto_group_by_magnitude(self):
        """
        Automatische Gruppierung (v5.4, PDDF-Bündelung)

        PDDF-Datensätze (P(r) sowie ihre q-Raum-Geschwister Rohdaten/Fit, erkannt am
        gemeinsamen Dateinamen-Präfix) werden zusammen in EINE Gruppe gebündelt, damit
        die PDDF-Subplot-Zuordnung (Haupt-/Subplot pro Datensatz) funktioniert. Alle
        übrigen Datasets erhalten weiterhin je eine eigene Gruppe mit automatischen
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

        created_groups = []

        # PDDF-Datensätze (P(r) + q-Raum-Geschwister) in EINE gemeinsame Gruppe bündeln
        pddf_bundle, remaining_datasets = split_pddf_bundle(selected_datasets)
        if pddf_bundle:
            existing_names = {g.name for g in self.groups}
            base_name = tr("messages.auto_pddf_group_name")
            group_name = base_name
            suffix = 2
            while group_name in existing_names:
                group_name = f"{base_name} ({suffix})"
                suffix += 1

            group = DataGroup(group_name, 1.0)
            for dataset in pddf_bundle:
                group.add_dataset(dataset)
                if dataset in self.unassigned_datasets:
                    self.unassigned_datasets.remove(dataset)
            group.display_label = group_name
            self.groups.append(group)
            created_groups.append((group_name, 1.0))
            self.logger.debug(
                f"  PDDF-Gruppe '{group_name}' erstellt ({len(pddf_bundle)} Datasets: "
                f"{', '.join(ds.name for ds in pddf_bundle)})"
            )

        # Für jedes übrige Dataset eine eigene Gruppe erstellen
        for idx, dataset in enumerate(remaining_datasets):
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

    def load_2d_data(self):
        """Lädt ein 2D SAXS Dataset (NeXus/HDF5)"""
        self.logger.debug("Öffne 2D-Datei-Dialog...")
        files, _ = QFileDialog.getOpenFileNames(
            self, tr("2d.load_button"),
            self.config.get_last_directory(),
            "HDF5 / NeXus (*.h5 *.h5z);;Alle Dateien (*)"
        )
        if not files:
            self.logger.debug("2D-Datei-Dialog abgebrochen")
            return

        self.config.set_last_directory(str(Path(files[0]).parent))
        for filepath in files:
            try:
                ds2d = Dataset2D(filepath)
                ds2d.load_data(raise_on_error=True)
                self.datasets_2d.append(ds2d)
                self.logger.info(f"2D Dataset geladen: {ds2d.name} ({ds2d.metadata.get('n_pixels_valid', '?')} Pixel)")

                if not hasattr(self, 'datasets_2d_item') or self.datasets_2d_item is None:
                    self.rebuild_tree()
                    return

                item = QTreeWidgetItem(self.datasets_2d_item, [ds2d.display_label, "2D"])
                item.setData(0, Qt.UserRole, ('dataset_2d', ds2d))
                self.datasets_2d_item.setExpanded(True)
            except Exception as e:
                self.logger.error(f"Fehler beim Laden von {Path(filepath).name}: {e}")
                QMessageBox.warning(self, tr("messages.error"),
                                    tr("2d.error_loading", error=str(e)))

    def open_2d_dialog(self, dataset_2d):
        """Öffnet den 2D-Analyse-Dialog für ein Dataset2D (nicht-modal)"""
        dlg = Plot2DDialog(dataset_2d, parent=self)
        dlg.projection_ready.connect(self.add_projection_to_tree)
        dlg.show()

    def add_projection_to_tree(self, dataset):
        """Übernimmt eine 1D-Projektion aus dem 2D-Dialog in den 1D-Tree"""
        self.unassigned_datasets.append(dataset)
        item = QTreeWidgetItem(self.unassigned_item, [dataset.display_label, ""])
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(0, Qt.Checked)
        item.setData(0, Qt.UserRole, ('dataset', dataset))
        self.update_plot()
        self.logger.info(f"1D-Projektion hinzugefügt: {dataset.name}")

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
                elif item_type == 'dataset_2d':
                    obj = data[1]
                    if obj in self.datasets_2d:
                        self.datasets_2d.remove(obj)
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
            # Flexibles Entpacken: data kann 2 oder 3 Elemente haben
            # Format: (item_type, obj) oder (item_type, idx, obj)
            if len(data) == 2:
                item_type, obj = data
            elif len(data) == 3:
                item_type, idx, obj = data
            else:
                return  # Unbekanntes Format

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
            elif item_type == 'dataset_2d':
                self.open_2d_dialog(obj)
            elif item_type == 'annotation' or item_type == 'reference_line':
                # Annotations/Referenzlinien werden per Kontextmenü bearbeitet
                # Doppelklick hier bewusst nichts tun
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
        elif data and data[0] == 'group':
            group = data[1]
            # Checkbox-Status mit group.visible synchronisieren (blendet die
            # gesamte Gruppe im Plot ein/aus, unabhängig von den einzelnen Kurven)
            group.visible = (item.checkState(0) == Qt.Checked)
            self.update_plot()

    def show_context_menu(self, position):
        """Kontextmenü für Tree (erweitert v5.3 für Annotations/Referenzlinien, v5.4 für Gruppen-Farbpaletten, v6.0 für Kurven-Editor)"""
        item = self.tree.itemAt(position)
        if not item:
            return

        menu = QMenu()

        data = item.data(0, Qt.UserRole)

        # 2D Dataset: open analysis dialog
        open_2d_action = None
        if data and data[0] == 'dataset_2d':
            open_2d_action = menu.addAction(tr("2d.open_dialog"))
            menu.addSeparator()

        # Bearbeiten für Annotations/Referenzlinien (v5.3)
        edit_action = None
        if data and data[0] in ['annotation', 'reference_line']:
            edit_action = menu.addAction(tr("context_menu.edit"))

        # Kurve bearbeiten für Datensätze (v6.0)
        edit_curve_action = None
        gift_action = None
        if data and data[0] == 'dataset':
            edit_curve_action = menu.addAction(tr("context_menu.edit_curve"))
            # IFT/GIFT (v7.8)
            gift_action = menu.addAction(tr("context_menu.gift"))

        # ASAXS-Auswertung (v8.1): für Datensätze/Gruppen mit ASAXS-Termen
        asaxs_action = None
        if data and data[0] in ('dataset', 'group'):
            members = [data[1]] if data[0] == 'dataset' else data[1].datasets
            if any(getattr(ds, 'data_term', '') in ('normal', 'anomalous', 'cross') for ds in members):
                asaxs_action = menu.addAction(tr("context_menu.asaxs"))

        # Gruppe bearbeiten (v6.2)
        edit_group_action = None
        if data and data[0] == 'group':
            edit_group_action = menu.addAction(tr("context_menu.edit_group"))

        # Panel-Zuordnung (v8.1): Untermenü 'Anzeigen in' mit checkbaren Panels
        panel_menu = None
        panel_actions = {}
        panel_auto_action = None
        if data and data[0] == 'group' and len(self.plot_layout.panels) > 1:
            group_ids = data[1].panel_ids
            panel_menu = menu.addMenu(tr("context_menu.show_in_panels"))
            panel_auto_action = panel_menu.addAction(tr("context_menu.panels_auto"))
            panel_auto_action.setCheckable(True)
            panel_auto_action.setChecked(group_ids is None)
            panel_menu.addSeparator()
            for panel in self.plot_layout.panels:
                act = panel_menu.addAction(panel.name if panel.enabled or panel.is_main
                                           else f"{panel.name} ({tr('panels.disabled')})")
                act.setCheckable(True)
                act.setChecked(group_ids is not None and panel.id in group_ids)
                panel_actions[act] = panel.id

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

        # Dateipfad aktualisieren für Datensätze (v7.0.4)
        update_filepath_action = None
        if data and data[0] == 'dataset':
            update_filepath_action = menu.addAction(tr("context_menu.update_filepath"))

        menu.addSeparator()
        delete_action = menu.addAction(tr("context_menu.delete"))

        action = menu.exec(self.tree.viewport().mapToGlobal(position))

        if action == open_2d_action and open_2d_action:
            self.open_2d_dialog(data[1])
        elif action == edit_action and edit_action:
            self.edit_annotation_or_refline(item)
        elif action == edit_curve_action and edit_curve_action:
            # Kurve bearbeiten (v6.0)
            self.edit_curve_settings(item)
        elif action == gift_action and gift_action:
            # IFT/GIFT (v7.8)
            self.show_gift_dialog(data[1])
        elif action == asaxs_action and asaxs_action:
            # ASAXS-Auswertung (v8.1)
            self.show_asaxs_dialog([data[1]] if data[0] == 'dataset' else list(data[1].datasets))
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
        elif panel_menu and action == panel_auto_action:
            data[1].panel_ids = None
            self.rebuild_tree()
            self.update_plot()
        elif panel_menu and action in panel_actions:
            # Panel in der festen Zuordnung ein-/ausschalten (aus 'Automatisch' heraus:
            # Start mit genau diesem Panel)
            group = data[1]
            panel_id = panel_actions[action]
            ids = list(group.panel_ids) if group.panel_ids is not None else []
            if panel_id in ids:
                ids.remove(panel_id)
            else:
                ids.append(panel_id)
            group.panel_ids = ids or None
            self.rebuild_tree()
            self.update_plot()
        elif action == reset_color_action and reset_color_action:
            self.reset_dataset_color(item)
        elif action == set_limits_action and set_limits_action:
            # Plotgrenzen für Dataset setzen (v5.7)
            self.set_dataset_plot_limits(item)
        elif action == update_filepath_action and update_filepath_action:
            # Dateipfad aktualisieren (v7.0.4)
            self.update_dataset_filepath(item)
        elif action == delete_action:
            self.tree.setCurrentItem(item)
            self.delete_selected()

    def rename_item(self, item):
        """Benennt Item um"""
        data = item.data(0, Qt.UserRole)
        if data:
            item_type, obj = data
            old_name = obj.name if item_type in ['group', 'dataset', 'dataset_2d'] else item.text(0)
            new_name, ok = QInputDialog.getText(self, "Umbenennen", "Neuer Name:", text=old_name)
            if ok and new_name:
                if item_type in ['group', 'dataset', 'dataset_2d']:
                    obj.name = new_name
                    obj.display_label = new_name
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

    def update_dataset_filepath(self, item):
        """Aktualisiert den Dateipfad eines Datensatzes (v7.0.4)"""
        data = item.data(0, Qt.UserRole)
        if not data or data[0] != 'dataset':
            return

        dataset = data[1]

        # Zeige aktuellen Pfad
        current_path = str(dataset.filepath)
        file_exists = dataset.filepath.exists() if hasattr(dataset.filepath, 'exists') else False

        # Info-Text erstellen
        if file_exists:
            info_text = tr("messages.current_filepath_exists", filepath=current_path)
        else:
            info_text = tr("messages.current_filepath_missing", filepath=current_path)

        # File-Dialog öffnen
        filename, _ = QFileDialog.getOpenFileName(
            self,
            tr("context_menu.update_filepath"),
            str(dataset.filepath.parent) if hasattr(dataset.filepath, 'parent') else self.config.get_last_directory(),
            "Data Files (*.dat *.txt *.csv *.xy);;All Files (*.*)"
        )

        if filename:
            old_filepath = dataset.filepath
            old_name = dataset.name

            # Neuen Pfad setzen
            dataset.filepath = Path(filename)

            # Optional: Namen aktualisieren wenn er vom alten Dateinamen abgeleitet war
            if dataset.name == old_filepath.stem:
                dataset.name = dataset.filepath.stem
                dataset.display_label = dataset.name

            # Versuche Daten neu zu laden
            try:
                dataset.load_data(raise_on_error=True)
                dataset.data_loaded = True

                # Tree-Item aktualisieren
                item.setText(0, dataset.display_label)

                # Plot aktualisieren
                self.update_plot()

                self.logger.info(f"Dateipfad für '{dataset.name}' aktualisiert: {filename}")
                QMessageBox.information(
                    self,
                    tr("messages.success"),
                    tr("messages.filepath_updated", name=dataset.display_label, filepath=filename)
                )
            except Exception as e:
                # Bei Fehler: Rollback
                dataset.filepath = old_filepath
                dataset.name = old_name
                dataset.data_loaded = False

                self.logger.error(f"Fehler beim Laden der neuen Datei: {e}")
                QMessageBox.critical(
                    self,
                    tr("messages.error"),
                    tr("messages.filepath_update_error", error=str(e))
                )

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
            dataset.line_alpha = settings['line_alpha']
            dataset.show_errorbars = settings['show_errorbars']
            dataset.errorbar_style = settings['errorbar_style']
            dataset.errorbar_capsize = settings['errorbar_capsize']
            dataset.errorbar_alpha = settings['errorbar_alpha']
            dataset.errorbar_linewidth = settings['errorbar_linewidth']
            dataset.snr_visualization = settings.get('snr_visualization', False)
            dataset.snr_threshold = settings.get('snr_threshold', 1.0)
            dataset.snr_good_marker = settings.get('snr_good_marker', 'o')
            dataset.snr_poor_marker = settings.get('snr_poor_marker', '^')
            dataset.snr_poor_alpha = settings.get('snr_poor_alpha', 0.3)
            dataset.snr_show_errorbars = settings.get('snr_show_errorbars', True)
            if settings.get('data_term') is not None:
                dataset.data_term = settings['data_term']
            if settings.get('pddf_role') is not None:
                dataset.set_pddf_role(settings['pddf_role'])

            if 'col_x' in settings:
                new_mapping = (settings['col_x'], settings['col_y'], settings['col_err'])
                old_mapping = (dataset.col_x, dataset.col_y, dataset.col_err)
                if new_mapping != old_mapping:
                    try:
                        dataset.set_column_mapping(*new_mapping)
                    except ValueError as e:
                        QMessageBox.warning(
                            self,
                            tr("messages.error"),
                            tr("curve_settings.columns.selection_error", error=str(e))
                        )

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

        # Dialog öffnen mit Template-Dataset und Gruppenreferenz
        dialog = CurveSettingsDialog(
            self,
            template_dataset,
            current_color_scheme=active_palette_name,
            color_schemes=self.config.color_schemes,
            group=group,
            plot_type=self.plot_type,
            panels=[(p.id, p.name) for p in self.plot_layout.panels],
        )
        dialog.setWindowTitle(f"Gruppeneinstellungen für '{group.name}' ({len(group.datasets)} Kurven)")

        if dialog.exec():
            settings = dialog.get_settings()

            # Gruppenspezifische Einstellungen direkt am Group-Objekt setzen
            if 'panel_ids' in settings:
                group.panel_ids = settings['panel_ids']

            # Palette ändern: Kurvenfarben neu aus der Palette vergeben.
            # Ohne Änderung bleiben die vorhandenen Einzelfarben erhalten.
            scheme = settings.get('group_color_scheme')
            if scheme is not None:
                group.color_scheme = scheme or None
                for dataset in group.datasets:
                    dataset.color = None

            # Kurveneinstellungen auf ALLE Datasets in der Gruppe anwenden
            for dataset in group.datasets:
                dataset.marker_style = settings['marker_style']
                dataset.marker_size = settings['marker_size']
                dataset.line_style = settings['line_style']
                dataset.line_width = settings['line_width']
                dataset.line_alpha = settings['line_alpha']
                dataset.show_errorbars = settings['show_errorbars']
                dataset.errorbar_style = settings['errorbar_style']
                dataset.errorbar_capsize = settings['errorbar_capsize']
                dataset.errorbar_alpha = settings['errorbar_alpha']
                dataset.errorbar_linewidth = settings['errorbar_linewidth']
                dataset.snr_visualization = settings.get('snr_visualization', False)
                dataset.snr_threshold = settings.get('snr_threshold', 1.0)
                dataset.snr_good_marker = settings.get('snr_good_marker', 'o')
                dataset.snr_poor_marker = settings.get('snr_poor_marker', '^')
                dataset.snr_poor_alpha = settings.get('snr_poor_alpha', 0.3)
                dataset.snr_show_errorbars = settings.get('snr_show_errorbars', True)
                if settings.get('data_term') is not None:
                    dataset.data_term = settings['data_term']

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
        """Setzt Farbe für Datasets ohne Farbe in einer Gruppe (v5.7, fix v7.3.1).

        Nur Datasets ohne gesetzte Farbe (color=None) werden angepasst.
        Bereits manuell gesetzte Einzelfarben bleiben erhalten.
        """
        if not group.datasets:
            return

        # Nur unkolorierte Datasets behandeln
        uncolored = [ds for ds in group.datasets if not ds.color]
        if not uncolored:
            return  # Alle haben bereits eine Farbe — nichts tun

        # Referenzfarbe: erste gesetzte Farbe in der Gruppe
        reference_color = None
        for dataset in group.datasets:
            if dataset.color:
                reference_color = dataset.color
                break

        # Wenn keine Farbe in der Gruppe gesetzt ist, aus der Palette holen
        if not reference_color:
            if group.color_scheme and group.color_scheme in self.config.color_schemes:
                colors = self.config.color_schemes[group.color_scheme]
            else:
                scheme_name = self.color_scheme_combo.currentText()
                colors = self.config.color_schemes.get(scheme_name, ['#1f77b4'])
            from itertools import cycle
            reference_color = next(cycle(colors))

        # Nur die Datasets ohne Farbe anpassen
        for dataset in uncolored:
            dataset.color = reference_color

        self.logger.debug(
            f"Farbe für {len(uncolored)} neue Dataset(s) in '{group.name}' gesetzt: {reference_color}"
        )

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

        self.logger.debug(f"Dataset '{dataset.name}' zu Gruppe '{target_group.name}' verschoben")

    def sync_data_from_tree(self):
        """Synchronisiert Datenstrukturen nach Drag & Drop im Tree"""
        self.logger.debug("Synchronisiere Datenstrukturen nach Drag & Drop...")

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
        self.logger.debug(f"Synchronisation abgeschlossen: {len(self.groups)} Gruppen, {len(self.unassigned_datasets)} unassigned")

    # ------------------------------------------------------------------
    # IFT/GIFT (v7.8)
    # ------------------------------------------------------------------

    def _selected_dataset(self):
        """Erster ausgewählter 1D-Datensatz im Tree (oder None)."""
        for item in self.tree.selectedItems():
            data = item.data(0, Qt.UserRole)
            if data and data[0] == 'dataset':
                return data[1]
        return None

    def show_gift_dialog(self, dataset=None):
        """Öffnet den IFT/GIFT-Dialog für einen Datensatz (nicht-modal)."""
        dataset = dataset or self._selected_dataset()
        if dataset is None:
            QMessageBox.information(self, tr("menu.analysis.gift"),
                                    tr("messages.gift_select_dataset"))
            return
        if not getattr(dataset, 'data_loaded', False):
            QMessageBox.warning(self, tr("messages.error"),
                                tr("messages.gift_not_loaded", name=dataset.name))
            return
        window = self._significance_window()
        try:
            dlg = GiftDialog(dataset, parent=self, significance_window=window,
                             datasets=self._loaded_datasets)
        except (ValueError, IndexError) as e:
            QMessageBox.critical(self, tr("messages.error"), str(e))
            return
        dlg.results_applied.connect(self.add_gift_results)
        self._gift_dialogs = [d for d in getattr(self, '_gift_dialogs', []) if d.isVisible()]
        self._gift_dialogs.append(dlg)
        dlg.show()

    def _loaded_datasets(self):
        """Alle geladenen Datensätze (Gruppen + nicht zugeordnet), z. B. für die GIFT-Serie."""
        out = [ds for g in self.groups for ds in g.datasets] + list(self.unassigned_datasets)
        return [ds for ds in out if getattr(ds, 'data_loaded', False)]

    def add_gift_results(self, info):
        """Legt aus den GIFT-Ergebnisdateien eine PDDF-Gruppe an (Rohdaten + Fit + p(r))."""
        source = info['dataset']
        paths = info['paths']
        name = source.display_label
        try:
            if 'data' in paths:
                # q wurde für die Analyse umgerechnet (z. B. Å⁻¹ → nm⁻¹)
                ds_data = DataSet(paths['data'], name=name)
            else:
                ds_data = DataSet(source.filepath, name=name)
                if getattr(source, '_columns_configured', False):
                    ds_data.set_column_mapping(source.col_x, source.col_y, source.col_err)
            ds_data.set_pddf_role('data')

            ds_fit = DataSet(paths['fit'])
            ds_fit.set_pddf_role('fit')
            ds_fit.display_label = tr("gift.label_fit", name=name)

            ds_pr = DataSet(paths['pr'], filter_nonpositive=False)
            ds_pr.set_pddf_role('pofr')
            ds_pr.display_label = tr("gift.label_pr", name=name)
        except ValueError as e:
            QMessageBox.critical(self, tr("messages.error"), str(e))
            return

        existing = {g.name for g in self.groups}
        group_name = tr("gift.group_name", name=name)
        base, i = group_name, 2
        while group_name in existing:
            group_name = f"{base} ({i})"
            i += 1
        group = DataGroup(group_name)
        group.provenance_record_id = info.get('record_id')
        for ds in (ds_data, ds_fit, ds_pr):
            group.add_dataset(ds)
        self.groups.append(group)
        self.logger.info(f"GIFT-Ergebnisse als Gruppe '{group_name}' übernommen "
                         f"(record_id {group.provenance_record_id})")

        # v8.1: P(r)-Panel aktivieren bzw. anlegen (früher: Plot-Typ 'PDDF')
        self.ensure_panel('P(r)')
        self.rebuild_tree()
        self.update_plot()

    # ------------------------------------------------------------------
    # ASAXS-Auswertung (v8.1)
    # ------------------------------------------------------------------

    def show_asaxs_dialog(self, preselect=None):
        """Öffnet den ASAXS-Dialog (nicht-modal) für I_A/I_N, I_cross/I_N und Korrelation."""
        from dialogs.asaxs_dialog import AsaxsDialog
        dlg = AsaxsDialog(self._loaded_datasets, parent=self, preselect=preselect)
        dlg.datasets_ready.connect(self.add_derived_datasets)
        self._asaxs_dialogs = [d for d in getattr(self, '_asaxs_dialogs', []) if d.isVisible()]
        self._asaxs_dialogs.append(dlg)
        dlg.show()

    def add_derived_datasets(self, info):
        """Übernimmt abgeleitete Datensätze (z. B. aus dem ASAXS-Dialog) als neue Gruppe
        und zeigt sie in einem Ratio-Panel (wird bei Bedarf angelegt)."""
        datasets = info.get('datasets') or []
        if not datasets:
            return
        existing = {g.name for g in self.groups}
        group_name = base = info.get('group_name') or tr("asaxs.title")
        i = 2
        while group_name in existing:
            group_name = f"{base} ({i})"
            i += 1
        group = DataGroup(group_name)
        for ds in datasets:
            group.add_dataset(ds)
        self.groups.append(group)
        self.logger.info(f"{len(datasets)} abgeleitete Datensätze als Gruppe '{group_name}' übernommen")

        if any(getattr(ds, 'data_term', '') == 'ratio' for ds in datasets):
            panel = self.ensure_panel('Ratio')
            if info.get('ylabel') and not panel.axis.get('ylabel'):
                panel.axis['ylabel'] = info['ylabel']
        self.rebuild_tree()
        self.update_plot()

    def verify_gift_sidecar(self):
        """Prüft die SHA-256 aller Dateien eines Provenance-Sidecars gegen die Platte."""
        from analysis.gift.provenance import ProvenanceRecord
        path, _ = QFileDialog.getOpenFileName(self, tr("menu.analysis.verify_sidecar"), "",
                                              "Provenance (*_prov.json *.json)")
        if not path:
            return
        try:
            record = ProvenanceRecord.load(path)
        except (OSError, ValueError) as e:
            QMessageBox.critical(self, tr("messages.error"), str(e))
            return
        symbols = {'ok': '✔', 'modified': '✖', 'missing': '?', 'no_hash': '–'}
        lines = [tr("messages.gift_verify_inputs")]
        results = record.verify_inputs() + [None] + record.verify_outputs()
        for r in results:
            if r is None:
                lines.append("")
                lines.append(tr("messages.gift_verify_outputs"))
                continue
            name = r.get('filename') or r.get('label')
            lines.append(f"  {symbols.get(r['status'], r['status'])} {name}  "
                         f"({tr('messages.gift_status_' + r['status'])})")
        all_ok = all(r['status'] == 'ok' for r in results if r is not None)
        header = tr("messages.gift_verify_ok" if all_ok else "messages.gift_verify_failed",
                    record_id=record.record_id)
        box = QMessageBox.information if all_ok else QMessageBox.warning
        box(self, tr("menu.analysis.verify_sidecar"), header + "\n\n" + "\n".join(lines))

    def rebuild_tree(self):
        """Baut Tree komplett neu auf"""
        self.tree.clear()

        self.tree.headerItem().setText(1, "×")

        # "Nicht zugeordnet" Sektion
        self.unassigned_item = QTreeWidgetItem(self.tree, [tr("tree.unassigned"), ""])
        self.unassigned_item.setExpanded(True)

        for dataset in self.unassigned_datasets:
            item = QTreeWidgetItem(self.unassigned_item, [dataset.display_label, ""])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(0, Qt.Checked if dataset.show_in_legend else Qt.Unchecked)
            item.setData(0, Qt.UserRole, ('dataset', dataset))

        # Gruppen
        for group in self.groups:
            col2 = format_stack_factor(group.stack_factor)
            group_item = QTreeWidgetItem(self.tree, [group.name, col2])
            # v8.1: Panel-Zuordnung als Tooltip der Faktor-Spalte
            if group.panel_ids is None:
                panels_text = tr("tree.panels_auto")
            else:
                panels_text = ", ".join(self.panel_label(pid) for pid in group.panel_ids)
            group_item.setToolTip(1, tr("tree.panels_tooltip", panels=panels_text))
            group_item.setExpanded(not group.collapsed)
            group_item.setFlags(group_item.flags() | Qt.ItemIsUserCheckable)
            group_item.setCheckState(0, Qt.Checked if group.visible else Qt.Unchecked)
            group_item.setData(0, Qt.UserRole, ('group', group))
            record_id = getattr(group, 'provenance_record_id', None)
            if record_id:
                group_item.setToolTip(0, tr("tree.provenance_tooltip", record_id=record_id))

            for dataset in group.datasets:
                item = QTreeWidgetItem(group_item, [dataset.display_label, ""])
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(0, Qt.Checked if dataset.show_in_legend else Qt.Unchecked)
                item.setData(0, Qt.UserRole, ('dataset', dataset))

        # 2D Datasets section
        self.datasets_2d_item = QTreeWidgetItem(self.tree, [tr("tree.section_2d"), ""])
        self.datasets_2d_item.setExpanded(True)
        for ds2d in self.datasets_2d:
            item = QTreeWidgetItem(self.datasets_2d_item, [ds2d.display_label, "2D"])
            item.setData(0, Qt.UserRole, ('dataset_2d', ds2d))

        # Annotations & Referenzlinien (v5.3)
        self.annotations_item = QTreeWidgetItem(self.tree, [tr("tree.annotations"), ""])
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

        # v8.1: Panels, deren X-Achse mit dem Hauptpanel gekoppelt ist, verlieren die
        # Kopplung, wenn der neue Typ eine andere X-Größe hat (z. B. q → 2θ)
        main_domain = self.plot_layout.main.type_info.x_domain
        for panel in self.plot_layout.panels:
            share = self.plot_layout.get(panel.share_x_with) if panel.share_x_with else None
            if share is not None and share.type_info.x_domain != panel.type_info.x_domain:
                panel.share_x_with = None
                self.logger.info(f"X-Kopplung von Panel '{panel.name}' gelöst "
                                 f"(Hauptpanel-X ist jetzt '{main_domain}')")

        self.refresh_panel_list()
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

    def show_legend_editor(self):
        """Legenden-Editor (v7.0; v8.1.1: Änderungen erst bei OK, nichts geht verloren)"""
        dialog = LegendEditorDialog(
            self,
            self.groups,
            self.unassigned_datasets,
            self.legend_settings,
            self.font_settings
        )
        if dialog.exec():
            dialog.apply_entry_changes()
            self.apply_legend_order(*dialog.get_order())
            self.legend_settings.update(dialog.get_legend_settings())
            self.font_settings.update(dialog.get_font_settings())
            self.update_plot()
            self.rebuild_tree()

    def show_title_editor(self):
        """Zeigt Titel-Editor Dialog (v7.0, v8.1: mit Titel je Panel)"""
        dialog = TitleEditorDialog(
            self,
            self.title_settings,
            panels=[(p.id, p.name, p.title) for p in self.plot_layout.panels]
        )
        if dialog.exec():
            self.title_settings = dialog.get_settings()
            for panel_id, text in dialog.get_panel_titles().items():
                panel = self.plot_layout.get(panel_id)
                if panel is not None:
                    panel.title = text
            self.update_plot()

    def apply_legend_order(self, group_order, dataset_orders, unassigned_order):
        """Übernimmt die Reihenfolge aus dem Legenden-Editor (v8.1.1).

        Sortiert nur um – Gruppen/Datensätze, die nicht in den Listen vorkommen,
        bleiben in ihrer bisherigen Reihenfolge am Ende erhalten.

        Args:
            group_order: Gruppen in neuer Reihenfolge
            dataset_orders: dict id(group) → Datensätze der Gruppe in neuer Reihenfolge
            unassigned_order: nicht zugeordnete Datensätze in neuer Reihenfolge
        """
        def reordered(current, wanted):
            ids = {id(o) for o in current}
            head = [o for o in wanted if id(o) in ids]
            head_ids = {id(o) for o in head}
            return head + [o for o in current if id(o) not in head_ids]

        self.groups = reordered(self.groups, group_order)
        for group in self.groups:
            if id(group) in dataset_orders:
                group.datasets[:] = reordered(group.datasets, dataset_orders[id(group)])
        self.unassigned_datasets[:] = reordered(self.unassigned_datasets, unassigned_order)

    def show_grid_settings(self):
        """Zeigt Grid- und Tick-Einstellungen Dialog"""
        dialog = GridSettingsDialog(self, self.grid_settings)
        if dialog.exec():
            self.grid_settings = dialog.get_settings()
            self.update_plot()

    def show_axes_settings(self):
        """Zeigt Achsen und Limits Dialog (v7.0 - jetzt mit Schriftart-Einstellungen,
        v8.1 - Achsen aller weiteren Panels)"""
        panels = []
        for panel in self.plot_layout.panels:
            if panel.is_main:
                continue
            info = panel.type_info
            panels.append({
                'id': panel.id, 'name': panel.name, 'type': panel.panel_type,
                'axis': panel.axis,
                'default_xlabel': info.xlabel,
                'default_ylabel': info.default_ylabel(panel.options),
                'shared_x': bool(panel.share_x_with),
            })
        dialog = AxesSettingsDialog(
            self,
            self.custom_xlabel,
            self.custom_ylabel,
            self.plot_type,
            self.axis_limits,
            self.font_settings,
            panels=panels,
        )
        if dialog.exec():
            self.custom_xlabel, self.custom_ylabel = dialog.get_labels()
            self.axis_limits = dialog.get_axis_limits()
            for panel_id, axis in dialog.get_panel_axes().items():
                panel = self.plot_layout.get(panel_id)
                if panel is not None:
                    panel.axis.update(axis)
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

    def _attach_panel_selector(self, dialog, current_id=MAIN_ID):
        """Fügt einem Annotations-/Referenzlinien-Dialog eine Panel-Auswahl hinzu
        (v8.1, nur bei mehreren Panels). Gibt die Combo zurück (oder None)."""
        if len(self.plot_layout.panels) < 2:
            return None
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("panels.target_panel")))
        combo = QComboBox()
        for panel in self.plot_layout.panels:
            combo.addItem(panel.name, panel.id)
        combo.setCurrentIndex(max(0, combo.findData(current_id or MAIN_ID)))
        row.addWidget(combo, 1)
        box = dialog.layout()
        box.insertLayout(max(0, box.count() - 1), row)  # vor den OK/Abbrechen-Buttons
        return combo

    @staticmethod
    def _selected_panel_of(combo):
        return combo.currentData() if combo is not None else MAIN_ID

    def add_annotation(self):
        """Fügt Annotation hinzu (Version 5.2, erweitert 5.3, v8.1: Ziel-Panel)"""
        dialog = AnnotationsDialog(self)
        panel_combo = self._attach_panel_selector(dialog)
        if dialog.exec():
            annotation = dialog.get_annotation()
            annotation['panel_id'] = self._selected_panel_of(panel_combo)
            self.annotations.append(annotation)
            self.update_annotations_tree()
            self.update_plot()

    def add_reference_line(self):
        """Fügt Referenzlinie hinzu (Version 5.2, erweitert 5.3)"""
        dialog = ReferenceLinesDialog(self)
        panel_combo = self._attach_panel_selector(dialog)
        if dialog.exec():
            ref_line = dialog.get_reference_line()
            ref_line['panel_id'] = self._selected_panel_of(panel_combo)

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
            panel_combo = self._attach_panel_selector(dialog, obj.get('panel_id'))

            if dialog.exec():
                updated = dialog.get_annotation()
                updated['panel_id'] = self._selected_panel_of(panel_combo)
                self.annotations[idx] = updated
                self.update_annotations_tree()
                self.update_plot()

        elif item_type == 'reference_line':
            # Referenzlinien-Dialog mit vorausgefüllten Werten
            from dialogs.reference_lines_dialog import ReferenceLinesDialog
            dialog = ReferenceLinesDialog(self)
            dialog.type_combo.setCurrentIndex(0 if obj['type'] == 'vertical' else 1)
            dialog.value_spin.setValue(obj['value'])
            dialog.label_edit.setText(obj.get('label', ''))
            dialog.linestyle_combo.setCurrentText(obj['linestyle'])
            dialog.linewidth_spin.setValue(obj['linewidth'])
            dialog.color = obj['color']
            dialog.color_button.setStyleSheet(f"background-color: {obj['color']}; border: 1px solid #555;")
            dialog.color_button.setText(obj['color'])
            dialog.alpha_spin.setValue(obj['alpha'])
            panel_combo = self._attach_panel_selector(dialog, obj.get('panel_id'))

            if dialog.exec():
                updated = dialog.get_reference_line()
                updated['panel_id'] = self._selected_panel_of(panel_combo)
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
        elif format_ext == 'tiff':
            filter_str = "TIFF Dateien (*.tiff *.tif)"
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

                elif format_ext == 'tiff':
                    # TIFF-Optionen
                    save_kwargs['transparent'] = settings.get('transparent', False)
                    if not settings.get('transparent', False):
                        save_kwargs['facecolor'] = settings.get('bg_color', 'white')

                    # TIFF-Kompression
                    tiff_comp = settings.get('tiff_compression', 'tiff_deflate')
                    pil_kwargs = {}

                    if tiff_comp == 'tiff_lzw':
                        pil_kwargs['compression'] = 'tiff_lzw'
                    elif tiff_comp == 'tiff_jpeg':
                        pil_kwargs['compression'] = 'tiff_jpeg'
                        pil_kwargs['quality'] = settings.get('tiff_quality', 95)
                    elif tiff_comp == 'tiff_deflate':
                        pil_kwargs['compression'] = 'tiff_deflate'
                    # else: no compression (None)

                    if pil_kwargs:
                        save_kwargs['pil_kwargs'] = pil_kwargs

                elif format_ext == 'pdf':
                    # PDF-Metadaten (v7.0: erweitert mit allen Infos in Subject)
                    metadata = self._build_export_metadata(settings, format_type='pdf')

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

                    # SVG-Metadaten (v7.0: nur matplotlib-unterstützte Keys)
                    # matplotlib's SVG backend unterstützt nur: Title, Date, Creator
                    svg_metadata = {}
                    if settings.get('meta_title'):
                        svg_metadata['Title'] = settings['meta_title']
                    if settings.get('meta_author'):
                        svg_metadata['Creator'] = settings['meta_author']  # Author → Creator für SVG

                    # Date im ISO-Format
                    if settings.get('meta_auto_timestamp', True):
                        from datetime import datetime, timezone
                        svg_metadata['Date'] = datetime.now(timezone.utc).isoformat()

                    if svg_metadata:
                        save_kwargs['metadata'] = svg_metadata

                # Speichern
                self.fig.savefig(filename, **save_kwargs)

                # v7.0: Post-Export Metadaten-Handling
                if format_ext in ['png', 'tiff', 'tif']:
                    # XMP-Metadaten für PNG/TIFF einbetten
                    try:
                        from utils.metadata_export import add_metadata_to_export
                        full_metadata = self._build_export_metadata(settings, include_all=True)
                        add_metadata_to_export(Path(filename), full_metadata, format_ext.upper())
                        self.logger.info(f"XMP-Metadaten in {format_ext.upper()} eingebettet")
                    except Exception as e:
                        self.logger.warning(f"XMP-Metadaten konnten nicht eingebettet werden: {e}")
                        # Nicht kritisch - Datei ist trotzdem gespeichert

                elif format_ext in ['svg', 'pdf', 'eps']:
                    # XMP-Sidecar-Datei für SVG/PDF/EPS erstellen
                    # PDF: Zusätzlich zu embedded Metadaten (doppelt hält besser)
                    # SVG/EPS: Einzige vollständige Metadaten-Option
                    try:
                        from utils.metadata_export import create_xmp_sidecar
                        full_metadata = self._build_export_metadata(settings, include_all=True)
                        if create_xmp_sidecar(Path(filename), full_metadata):
                            self.logger.info(f"XMP-Sidecar erstellt: {filename}.xmp")
                    except Exception as e:
                        self.logger.warning(f"XMP-Sidecar konnte nicht erstellt werden: {e}")
                        # Nicht kritisch - Haupt-Datei ist trotzdem gespeichert

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

    def _build_export_metadata(self, settings: dict, include_all: bool = False, format_type: str = None) -> dict:
        """
        Erstellt vollständige Metadaten für Export (v7.0+)

        Args:
            settings: Export-Settings Dictionary
            include_all: Wenn True, werden alle erweiterten Metadaten inkludiert
                        (für XMP). Wenn False, nur matplotlib-kompatible Felder
                        (für PDF/SVG savefig).
            format_type: 'pdf', 'svg', oder None - für format-spezifische Anpassungen

        Returns:
            dict: Metadaten-Dictionary
        """
        from datetime import datetime, timezone
        from core.version import get_metadata_provenance
        import uuid

        metadata = {}

        # Basic metadata (immer dabei)
        if settings.get('meta_title'):
            metadata['Title'] = settings['meta_title']

        if settings.get('meta_author'):
            metadata['Author'] = settings['meta_author']

        if settings.get('meta_subject'):
            metadata['Subject'] = settings['meta_subject']

        if settings.get('meta_keywords'):
            metadata['Keywords'] = settings['meta_keywords']

        # Für matplotlib savefig (PDF/SVG): erweiterte Metadaten sammeln
        if not include_all:
            # Erweiterte Metadaten temporär sammeln für PDF-Subject-Erweiterung
            extended_meta = {}

            # ORCID
            if settings.get('meta_orcid'):
                orcid = settings['meta_orcid'].strip()
                if orcid:
                    if not orcid.startswith('http'):
                        extended_meta['Creator_ORCID'] = f"https://orcid.org/{orcid}"
                    else:
                        extended_meta['Creator_ORCID'] = orcid

            # Affiliation
            if settings.get('meta_affiliation'):
                extended_meta['Affiliation'] = settings['meta_affiliation']

            # License
            if settings.get('meta_license'):
                extended_meta['License'] = settings['meta_license']

            # Timestamp
            if settings.get('meta_auto_timestamp', True):
                now = datetime.now(timezone.utc)
                extended_meta['CreationDate'] = now.isoformat()
                extended_meta['CreationDate_Unix'] = int(now.timestamp())

            # Provenance
            if settings.get('meta_auto_provenance', True):
                prov = get_metadata_provenance()
                extended_meta['Creator_Tool'] = f"{prov['software']} v{prov['version']}"
                extended_meta['Creator_Tool_Version'] = prov['version']
                extended_meta['Python_Version'] = prov['python_version']
                extended_meta['Matplotlib_Version'] = prov['matplotlib_version']

            # UUID
            if settings.get('meta_generate_uuid', False):
                extended_meta['Image_UUID'] = str(uuid.uuid4())

            # Experiment metadata
            if settings.get('meta_experiment_id'):
                extended_meta['Experiment_ID'] = settings['meta_experiment_id']
            if settings.get('meta_measurement_date'):
                extended_meta['Measurement_Date'] = settings['meta_measurement_date']
            if settings.get('meta_sample_id'):
                extended_meta['Sample_ID'] = settings['meta_sample_id']

            # Für PDF: Alle erweiterten Metadaten in Subject-Feld packen
            if format_type == 'pdf':
                from utils.metadata_export import format_metadata_as_text

                # Kombiniere basis metadata mit erweiterten
                full_meta = {**metadata, **extended_meta}

                # Formatiere als kompakten Text
                extended_text = format_metadata_as_text(full_meta, format='plain')

                # Überschreibe Subject mit erweitertem Text
                metadata['Subject'] = extended_text

            return metadata

        # Erweiterte Metadaten (nur für XMP/PNG/TIFF)

        # ORCID
        if settings.get('meta_orcid'):
            orcid = settings['meta_orcid'].strip()
            if orcid:
                if not orcid.startswith('http'):
                    metadata['Creator_ORCID'] = f"https://orcid.org/{orcid}"
                else:
                    metadata['Creator_ORCID'] = orcid

        # Affiliation
        if settings.get('meta_affiliation'):
            metadata['Affiliation'] = settings['meta_affiliation']

        # License
        if settings.get('meta_license'):
            metadata['License'] = settings['meta_license']

            # License URL für bekannte CC-Lizenzen
            license_urls = {
                'CC-BY-4.0': 'https://creativecommons.org/licenses/by/4.0/',
                'CC-BY-SA-4.0': 'https://creativecommons.org/licenses/by-sa/4.0/',
                'CC-BY-NC-4.0': 'https://creativecommons.org/licenses/by-nc/4.0/',
                'CC-BY-NC-SA-4.0': 'https://creativecommons.org/licenses/by-nc-sa/4.0/',
                'CC0-1.0': 'https://creativecommons.org/publicdomain/zero/1.0/',
            }
            if settings['meta_license'] in license_urls:
                metadata['License_URL'] = license_urls[settings['meta_license']]

        # Automatische Metadaten

        # Timestamp (wenn aktiviert)
        if settings.get('meta_auto_timestamp', True):
            now = datetime.now(timezone.utc)
            metadata['CreationDate'] = now.isoformat()
            metadata['CreationDate_Unix'] = int(now.timestamp())

        # Software-Provenienz (wenn aktiviert)
        if settings.get('meta_auto_provenance', True):
            prov = get_metadata_provenance()
            metadata['Creator_Tool'] = f"{prov['software']} v{prov['version']}"
            metadata['Creator_Tool_Version'] = prov['version']
            metadata['Python_Version'] = prov['python_version']
            metadata['Matplotlib_Version'] = prov['matplotlib_version']

        # UUID (wenn aktiviert)
        if settings.get('meta_generate_uuid', False):
            metadata['Image_UUID'] = str(uuid.uuid4())

        # Experiment metadata (optional)
        if settings.get('meta_experiment_id'):
            metadata['Experiment_ID'] = settings['meta_experiment_id']

        if settings.get('meta_measurement_date'):
            metadata['Measurement_Date'] = settings['meta_measurement_date']

        if settings.get('meta_sample_id'):
            metadata['Sample_ID'] = settings['meta_sample_id']

        return metadata

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

    def edit_user_metadata(self):
        """
        Öffnet Editor für Benutzer-Metadaten (v7.0+)
        """
        from dialogs.user_metadata_dialog import UserMetadataDialog

        self.logger.debug("Öffne Benutzer-Metadaten-Editor...")
        dialog = UserMetadataDialog(self.user_metadata, self)
        dialog.exec()

    def load_user_config(self):
        """
        Lädt Benutzer-Config von einer Datei (v7.0+)
        """
        self.logger.debug("Öffne Benutzer-Config-Laden-Dialog...")

        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Benutzer-Config laden",
            str(Path.home()),
            "JSON Files (*.json)"
        )

        if filepath:
            try:
                self.user_metadata.load_from_file(filepath)
                self.logger.info(f"Benutzer-Config geladen: {filepath}")

                QMessageBox.information(
                    self,
                    "Erfolg",
                    f"Benutzer-Config wurde erfolgreich geladen:\n\n{filepath}"
                )

                # In Haupt-Config merken
                self.config.config['last_user_metadata_file'] = filepath
                self.config.save_config()

            except Exception as e:
                self.logger.error(f"Fehler beim Laden der Benutzer-Config: {e}")
                QMessageBox.critical(
                    self,
                    "Fehler",
                    f"Fehler beim Laden der Benutzer-Config:\n\n{str(e)}"
                )

    def save_user_config_as(self):
        """
        Speichert Benutzer-Config unter einem neuen Namen (v7.0+)
        """
        self.logger.debug("Öffne Benutzer-Config-Speichern-Dialog...")

        # Default-Pfad
        if self.user_metadata.current_file:
            default_path = str(self.user_metadata.current_file)
        else:
            default_path = str(Path.home() / ".scatterforge" / "user_metadata.json")

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Benutzer-Config speichern unter",
            default_path,
            "JSON Files (*.json)"
        )

        if filepath:
            try:
                self.user_metadata.save(Path(filepath))
                self.logger.info(f"Benutzer-Config gespeichert: {filepath}")

                QMessageBox.information(
                    self,
                    "Erfolg",
                    f"Benutzer-Config wurde erfolgreich gespeichert:\n\n{filepath}"
                )

                # In Haupt-Config merken
                self.config.config['last_user_metadata_file'] = filepath
                self.config.save_config()

            except Exception as e:
                self.logger.error(f"Fehler beim Speichern der Benutzer-Config: {e}")
                QMessageBox.critical(
                    self,
                    "Fehler",
                    f"Fehler beim Speichern der Benutzer-Config:\n\n{str(e)}"
                )

    def show_about(self):
        """Zeigt Über-Dialog"""
        QMessageBox.about(self, "Über ScatterForge Plot",
                         f"{get_version_string()}\n\n"
                         "Professionelles Tool für Streudaten-Analyse\n\n"
                         "Neue Features in v7.0:\n"
                         "• Erweiterte Metadaten für Export (FAIR-Prinzipien)\n"
                         "• Benutzer-Metadaten-Manager (ORCID, Affiliation)\n"
                         "• XMP-Support für PNG/TIFF\n"
                         "• Automatische Zeitstempel & Software-Provenienz\n"
                         "• Lizenz-Management für wissenschaftliche Publikationen\n\n"
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
                    'datasets_2d': [ds.to_dict() for ds in self.datasets_2d],
                    'plot_type': self.plot_type,  # Typ des Hauptpanels
                    'plot_layout': self.plot_layout.to_dict(),  # v8.1: Panel-Grid
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
                # v8.1: Sessions ≤ v8.0 (Plot-Typ mit festem Subplot) in ein Panel-Layout übersetzen
                migrate_legacy_session(session)

                # Tree leeren
                self.tree.clear()
                self.unassigned_item = QTreeWidgetItem(self.tree, [tr("tree.unassigned"), ""])
                self.unassigned_item.setExpanded(True)

                # Annotations & Referenzlinien Section neu erstellen (v5.3)
                self.annotations_item = QTreeWidgetItem(self.tree, [tr("tree.annotations"), ""])
                self.annotations_item.setExpanded(True)

                # Daten laden
                self.groups = [DataGroup.from_dict(g) for g in session.get('groups', [])]
                self.unassigned_datasets = [DataSet.from_dict(ds) for ds in session.get('unassigned', [])]
                self.datasets_2d = [Dataset2D.from_dict(d) for d in session.get('datasets_2d', [])]
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
                    group_item.setFlags(group_item.flags() | Qt.ItemIsUserCheckable)
                    group_item.setCheckState(0, Qt.Checked if group.visible else Qt.Unchecked)
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

                # 2D Datasets in Tree einfügen
                self.datasets_2d_item = QTreeWidgetItem(self.tree, [tr("tree.section_2d"), ""])
                self.datasets_2d_item.setExpanded(True)
                for ds2d in self.datasets_2d:
                    item = QTreeWidgetItem(self.datasets_2d_item, [ds2d.display_label, "2D"])
                    item.setData(0, Qt.UserRole, ('dataset_2d', ds2d))

                # Einstellungen wiederherstellen
                # v8.1: Panel-Layout (enthält Plot-Typ, Achsen und Titel aller Panels)
                self.plot_layout = PlotLayout.from_dict(session['plot_layout'])
                self._drop_stale_panel_refs()
                self.refresh_panel_list()

                self.stack_mode = session.get('stack_mode', True)
                self.stack_checkbox.setChecked(self.stack_mode)

                color_scheme = session.get('color_scheme', 'TUBAF')
                self.color_scheme_combo.setCurrentText(color_scheme)


                # Version 6.2: Wellenlänge für 2-Theta Plot
                if 'wavelength' in session:
                    self.wavelength = session['wavelength']
                    self.wavelength_edit.setText(str(self.wavelength))

                # Erweiterte Einstellungen (v5.1)
                if 'legend_settings' in session:
                    self.legend_settings = session['legend_settings']
                if 'title_settings' in session:  # v7.0
                    self.title_settings = session['title_settings']
                    # v7.7-Subplot-Titel steckt nach der Migration im Panel 'sub'
                    self.title_settings.pop('subplot_text', None)
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

                # Version 5.7: Custom Achsenbeschriftungen (v8.1: Teil von plot_layout)
                if 'unit_format' in session:
                    self.unit_format = session['unit_format']

                # Tree neu aufbauen (v8.1: inkl. Panel-Zuordnung als Tooltip)
                self.rebuild_tree()

                # Zähle fehlende Datensätze
                missing_count = 0
                for group in self.groups:
                    missing_count += sum(1 for ds in group.datasets if not ds.data_loaded)
                missing_count += sum(1 for ds in self.unassigned_datasets if not ds.data_loaded)

                self.logger.info("Session erfolgreich geladen")
                self.update_plot()

                # Zeige Erfolgsmeldung mit optionaler Warnung für fehlende Dateien
                if missing_count > 0:
                    self.logger.warning(f"{missing_count} Datensätze konnten nicht geladen werden (Dateien nicht gefunden)")
                    QMessageBox.warning(
                        self,
                        tr("messages.success"),
                        tr("messages.session_loaded") + f"\n\n⚠️ Hinweis: {missing_count} Datensätze konnten nicht geladen werden, da die Dateien nicht gefunden wurden."
                    )
                else:
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
    app.setApplicationName("ScatterForge Plot")
    app.setOrganizationName("TU Bergakademie Freiberg")
    app.setApplicationVersion(__version__)

    # Hauptfenster
    window = ScatterPlotApp()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
