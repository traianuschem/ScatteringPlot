#!/usr/bin/env python3
"""
TUBAF Scattering Plot Tool - Version 5.1 (Qt)
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
from PySide6.QtCore import Qt
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
from utils.data_loader import load_scattering_data
from utils.user_config import get_user_config


class ScatterPlotApp(QMainWindow):
    """Hauptanwendung (Qt-basiert)"""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("TUBAF Scattering Plot Tool v5.1")
        self.resize(1600, 1000)

        # Config
        self.config = get_user_config()

        # Datenverwaltung
        self.groups = []
        self.unassigned_datasets = []

        # Plot-Einstellungen
        self.plot_type = 'Log-Log'
        self.stack_mode = True
        self.show_grid = True
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
            'major_alpha': 0.3,
            'major_color': '#FFFFFF',
            'minor_enable': False,
            'minor_axis': 'both',
            'minor_linestyle': 'dotted',
            'minor_linewidth': 0.5,
            'minor_alpha': 0.2,
            'minor_color': '#FFFFFF'
        }
        self.font_settings = {
            'title_size': 14,
            'title_bold': True,
            'title_italic': False,
            'labels_size': 12,
            'labels_bold': False,
            'labels_italic': False,
            'ticks_size': 10,
            'legend_size': 10,
            'font_family': 'sans-serif'
        }
        self.export_settings = {
            'format': 'PNG',
            'dpi': 300,
            'width': 10.0,
            'height': 8.0,
            'keep_aspect': True,
            'transparent': False,
            'tight_layout': True,
            'facecolor_white': False
        }

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

        settings_action = QAction("Achsenlimits...", self)
        settings_action.triggered.connect(self.show_plot_settings)
        plot_menu.addAction(settings_action)

        legend_action = QAction("Legenden-Einstellungen...", self)
        legend_action.triggered.connect(self.show_legend_settings)
        plot_menu.addAction(legend_action)

        grid_action = QAction("Grid-Einstellungen...", self)
        grid_action.triggered.connect(self.show_grid_settings)
        plot_menu.addAction(grid_action)

        font_action = QAction("Schriftart-Einstellungen...", self)
        font_action.triggered.connect(self.show_font_settings)
        plot_menu.addAction(font_action)

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

        load_btn = QPushButton("📁 Laden")
        load_btn.clicked.connect(self.load_data_to_unassigned)
        button_layout.addWidget(load_btn)

        delete_btn = QPushButton("🗑 Löschen")
        delete_btn.clicked.connect(self.delete_selected)
        button_layout.addWidget(delete_btn)

        layout.addLayout(button_layout)

        # Tree Widget
        self.tree = QTreeWidget()
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

        # Grid
        options_layout.addWidget(QLabel("Grid:"), 2, 0)
        self.grid_checkbox = QCheckBox("Anzeigen")
        self.grid_checkbox.setChecked(True)
        self.grid_checkbox.stateChanged.connect(self.update_plot)
        options_layout.addWidget(self.grid_checkbox, 2, 1)

        # Farbschema
        options_layout.addWidget(QLabel("Farbschema:"), 3, 0)
        self.color_scheme_combo = QComboBox()
        self.color_scheme_combo.addItems(list(self.config.color_schemes.keys()))
        self.color_scheme_combo.setCurrentText('TUBAF')
        self.color_scheme_combo.currentTextChanged.connect(self.change_color_scheme)
        options_layout.addWidget(self.color_scheme_combo, 3, 1)

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
        # Plot-Einstellungen
        self.stack_mode = self.stack_checkbox.isChecked()
        self.show_grid = self.grid_checkbox.isChecked()

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

        # Farben holen
        color_scheme = self.color_scheme_combo.currentText()
        colors = self.config.color_schemes.get(color_scheme, self.config.color_schemes['TUBAF'])
        color_cycle = iter(colors * 10)  # Genug Farben

        # Plotten
        plot_info = PLOT_TYPES[self.plot_type]
        current_offset = 0

        # Gruppen plotten
        for group in self.groups:
            if not group.visible:
                continue

            # Gruppen-Label für Legende (mit Stack-Faktor)
            if self.stack_mode and len(self.groups) > 1:
                group_label = f"{group.name} (×{group.stack_factor:.1f})"
            else:
                group_label = group.name

            # Plot je Datensatz
            for dataset in group.datasets:
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

                # Stack-Offset
                if self.stack_mode:
                    y = y * group.stack_factor + current_offset

                # Plotten
                plot_style = dataset.get_plot_style()

                if dataset.y_err is not None and self.plot_type == 'Log-Log':
                    # Fehler als transparente Fläche
                    y_err_trans = self.transform_data(dataset.x, dataset.y_err, self.plot_type)[1]
                    if self.stack_mode:
                        y_err_trans = y_err_trans * group.stack_factor
                    self.ax_main.fill_between(x, y - y_err_trans, y + y_err_trans,
                                              alpha=0.2, color=color)

                self.ax_main.plot(x, y, plot_style, color=color, label=dataset.display_label,
                                 linewidth=dataset.line_width, markersize=dataset.marker_size)

            if self.stack_mode:
                current_offset += group.stack_factor

        # Auch nicht zugeordnete Datensätze plotten (ohne Stack-Faktor)
        for dataset in self.unassigned_datasets:
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

            self.ax_main.plot(x, y, plot_style, color=color, label=dataset.display_label,
                             linewidth=dataset.line_width, markersize=dataset.marker_size)

        # Achsen
        self.ax_main.set_xlabel(plot_info['xlabel'], fontsize=self.font_settings['labels_size'],
                               weight='bold' if self.font_settings['labels_bold'] else 'normal',
                               style='italic' if self.font_settings['labels_italic'] else 'normal',
                               fontfamily=self.font_settings['font_family'])
        self.ax_main.set_ylabel(plot_info['ylabel'], fontsize=self.font_settings['labels_size'],
                               weight='bold' if self.font_settings['labels_bold'] else 'normal',
                               style='italic' if self.font_settings['labels_italic'] else 'normal',
                               fontfamily=self.font_settings['font_family'])
        self.ax_main.set_xscale(plot_info['xscale'])
        self.ax_main.set_yscale(plot_info['yscale'])

        # Tick-Schriftgröße
        self.ax_main.tick_params(axis='both', labelsize=self.font_settings['ticks_size'])

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

        # Legende (erweitert in v5.1)
        if any(group.visible and group.datasets for group in self.groups) or self.unassigned_datasets:
            legend = self.ax_main.legend(
                loc=self.legend_settings['position'],
                fontsize=self.legend_settings['fontsize'],
                ncol=self.legend_settings['ncol'],
                frameon=self.legend_settings['frameon'],
                shadow=self.legend_settings['shadow'],
                fancybox=self.legend_settings['fancybox']
            )
            if legend and legend.get_frame():
                legend.get_frame().set_alpha(self.legend_settings['alpha'])

        self.fig.tight_layout()
        self.canvas.draw()

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
        """Löscht ausgewählte Items"""
        items = self.tree.selectedItems()
        if not items:
            return

        for item in items:
            data = item.data(0, Qt.UserRole)
            if data:
                item_type, obj = data
                if item_type == 'group':
                    if obj in self.groups:
                        self.groups.remove(obj)
                elif item_type == 'dataset':
                    # Aus Gruppe oder unassigned entfernen
                    parent_data = item.parent().data(0, Qt.UserRole) if item.parent() else None
                    if parent_data and parent_data[0] == 'group':
                        parent_data[1].remove_dataset(obj)
                    elif obj in self.unassigned_datasets:
                        self.unassigned_datasets.remove(obj)

            # Aus Tree entfernen
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
        """Kontextmenü für Tree"""
        item = self.tree.itemAt(position)
        if not item:
            return

        menu = QMenu()

        data = item.data(0, Qt.UserRole)

        rename_action = menu.addAction("Umbenennen")

        # Farbe zurücksetzen nur für Datensätze (v4.2+)
        reset_color_action = None
        if data and data[0] == 'dataset':
            menu.addSeparator()
            reset_color_action = menu.addAction("Farbe zurücksetzen")

        menu.addSeparator()
        delete_action = menu.addAction("Löschen")

        action = menu.exec(self.tree.viewport().mapToGlobal(position))

        if action == rename_action:
            self.rename_item(item)
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
                         "TUBAF Scattering Plot Tool - Version 5.1 (Qt)\n\n"
                         "Professionelles Tool für Streudaten-Analyse\n\n"
                         "Neue Features in v5.1:\n"
                         "• Erweiterte Legenden-Einstellungen\n"
                         "• Umfassende Grid-Einstellungen (Major/Minor)\n"
                         "• Schriftart-Anpassung für alle Elemente\n"
                         "• Verbesserter Export-Dialog\n\n"
                         "Features:\n"
                         "• Qt6-basierte moderne GUI mit modularer Architektur\n"
                         "• Permanenter Dark Mode\n"
                         "• Verschiedene Plot-Typen\n"
                         "• Stil-Vorlagen und Auto-Erkennung\n"
                         "• Farbschema-Manager\n"
                         "• Drag & Drop\n"
                         "• Session-Verwaltung")

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
                    'show_grid': self.show_grid,
                    'color_scheme': self.color_scheme_combo.currentText(),
                    'axis_limits': self.axis_limits,
                    'legend_settings': self.legend_settings,
                    'grid_settings': self.grid_settings,
                    'font_settings': self.font_settings,
                    'export_settings': self.export_settings
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
                    item = QTreeWidgetItem(self.unassigned_item, [dataset.name, ""])
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(0, Qt.Checked if dataset.show_in_legend else Qt.Unchecked)
                    item.setData(0, Qt.UserRole, ('dataset', dataset))

                # Einstellungen wiederherstellen
                self.plot_type = session.get('plot_type', 'Log-Log')
                self.plot_type_combo.setCurrentText(self.plot_type)

                self.stack_mode = session.get('stack_mode', True)
                self.stack_checkbox.setChecked(self.stack_mode)

                self.show_grid = session.get('show_grid', True)
                self.grid_checkbox.setChecked(self.show_grid)

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
