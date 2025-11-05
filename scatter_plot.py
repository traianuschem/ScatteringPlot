#!/usr/bin/env python3
"""
TUBAF Scattering Plot Tool - Version 4.0 (Qt)
==============================================

Professionelles Tool für Streudaten-Analyse mit:
- Qt6-basierte moderne GUI
- Native Dark Mode Support
- Verschiedene Plot-Typen (Log-Log, Porod, Kratky, Guinier, PDDF)
- Stil-Vorlagen und Auto-Erkennung
- Farbschema-Manager
- Drag & Drop
- Session-Verwaltung
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
    QColorDialog, QListWidget, QTextEdit, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QAction, QColor, QPalette, QIcon

# Matplotlib mit Qt Backend
import matplotlib
matplotlib.use('QtAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec

# Eigene Module
from data_loader import load_scattering_data
from user_config import get_user_config

# Plot-Typen
PLOT_TYPES = {
    'Log-Log': {'xlabel': 'q / nm⁻¹', 'ylabel': 'I / a.u.', 'xscale': 'log', 'yscale': 'log'},
    'Porod': {'xlabel': 'q / nm⁻¹', 'ylabel': 'I·q⁴ / a.u.·nm⁻⁴', 'xscale': 'log', 'yscale': 'log'},
    'Kratky': {'xlabel': 'q / nm⁻¹', 'ylabel': 'I·q² / a.u.·nm⁻²', 'xscale': 'linear', 'yscale': 'linear'},
    'Guinier': {'xlabel': 'q² / nm⁻²', 'ylabel': 'ln(I)', 'xscale': 'linear', 'yscale': 'linear'},
    'PDDF': {'xlabel': 'q / nm⁻¹', 'ylabel': 'I / a.u.', 'xscale': 'log', 'yscale': 'log'}
}


class DataSet:
    """Datensatz mit Stil-Informationen"""
    def __init__(self, filepath, name=None, apply_auto_style=True):
        self.filepath = Path(filepath)
        self.name = name or self.filepath.stem
        self.display_label = self.name
        self.data = None
        self.x = None
        self.y = None
        self.y_err = None

        # Stil
        self.line_style = None
        self.marker_style = None
        self.color = None
        self.line_width = 2
        self.marker_size = 4
        self.show_in_legend = True

        self.load_data()

        # Auto-Stil anwenden
        if apply_auto_style:
            self.apply_auto_style()

    def load_data(self):
        """Lädt Daten"""
        try:
            self.data = load_scattering_data(self.filepath)
            self.x = self.data[:, 0]
            self.y = self.data[:, 1]
            if self.data.shape[1] > 2:
                self.y_err = self.data[:, 2]
        except Exception as e:
            raise ValueError(f"Fehler beim Laden von {self.filepath}: {e}")

    def apply_auto_style(self):
        """Wendet automatisch erkannten Stil an"""
        config = get_user_config()
        style = config.get_style_by_filename(self.filepath)
        if style:
            self.line_style = style.get('line_style')
            self.marker_style = style.get('marker_style')
            self.line_width = style.get('line_width', 2)
            self.marker_size = style.get('marker_size', 4)

    def apply_style_preset(self, preset_name):
        """Wendet Stil-Vorlage an"""
        config = get_user_config()
        if preset_name in config.style_presets:
            style = config.style_presets[preset_name]
            self.line_style = style.get('line_style')
            self.marker_style = style.get('marker_style')
            self.line_width = style.get('line_width', 2)
            self.marker_size = style.get('marker_size', 4)

    def get_plot_style(self):
        """Gibt Plot-Stil zurück"""
        line = self.line_style if self.line_style else ''
        marker = self.marker_style if self.marker_style else ''
        if not line and not marker:
            # Auto: Fit=Linie, sonst Marker
            if 'fit' in self.name.lower():
                return '-'
            return 'o'
        return line + marker

    def to_dict(self):
        """Serialisierung"""
        return {
            'filepath': str(self.filepath),
            'name': self.name,
            'display_label': self.display_label,
            'line_style': self.line_style,
            'marker_style': self.marker_style,
            'color': self.color,
            'line_width': self.line_width,
            'marker_size': self.marker_size,
            'show_in_legend': self.show_in_legend
        }

    @classmethod
    def from_dict(cls, data):
        """Deserialisierung"""
        ds = cls(data['filepath'], data.get('name'), apply_auto_style=False)
        ds.display_label = data.get('display_label', ds.name)
        ds.line_style = data.get('line_style')
        ds.marker_style = data.get('marker_style')
        ds.color = data.get('color')
        ds.line_width = data.get('line_width', 2)
        ds.marker_size = data.get('marker_size', 4)
        ds.show_in_legend = data.get('show_in_legend', True)
        return ds


class DataGroup:
    """Datengruppe"""
    def __init__(self, name, stack_factor=1.0):
        self.name = name
        self.datasets = []
        self.stack_factor = stack_factor
        self.visible = True
        self.collapsed = False

    def add_dataset(self, dataset):
        """Datensatz hinzufügen"""
        self.datasets.append(dataset)

    def remove_dataset(self, dataset):
        """Datensatz entfernen"""
        if dataset in self.datasets:
            self.datasets.remove(dataset)

    def to_dict(self):
        """Serialisierung"""
        return {
            'name': self.name,
            'stack_factor': self.stack_factor,
            'visible': self.visible,
            'collapsed': self.collapsed,
            'datasets': [ds.to_dict() for ds in self.datasets]
        }

    @classmethod
    def from_dict(cls, data):
        """Deserialisierung"""
        group = cls(data['name'], data.get('stack_factor', 1.0))
        group.visible = data.get('visible', True)
        group.collapsed = data.get('collapsed', False)
        group.datasets = [DataSet.from_dict(ds_data) for ds_data in data.get('datasets', [])]
        return group


class ScatterPlotApp(QMainWindow):
    """Hauptanwendung (Qt-basiert)"""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("TUBAF Scattering Plot Tool v4.0")
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

        export_png_action = QAction("PNG Export...", self)
        export_png_action.triggered.connect(self.export_png)
        file_menu.addAction(export_png_action)

        export_svg_action = QAction("SVG Export...", self)
        export_svg_action.triggered.connect(self.export_svg)
        file_menu.addAction(export_svg_action)

        file_menu.addSeparator()

        quit_action = QAction("Beenden", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # Plot-Menü
        plot_menu = menubar.addMenu("Plot")

        update_action = QAction("Aktualisieren", self)
        update_action.triggered.connect(self.update_plot)
        plot_menu.addAction(update_action)

        settings_action = QAction("Erweiterte Einstellungen...", self)
        settings_action.triggered.connect(self.show_plot_settings)
        plot_menu.addAction(settings_action)

        # Design-Menü
        design_menu = menubar.addMenu("Design")

        manager_action = QAction("Design-Manager...", self)
        manager_action.triggered.connect(self.show_design_manager)
        design_menu.addAction(manager_action)

        design_menu.addSeparator()

        dark_mode_action = QAction("🌙 Dark Mode umschalten", self)
        dark_mode_action.triggered.connect(self.toggle_dark_mode)
        design_menu.addAction(dark_mode_action)

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
        """Wendet Dark/Light Theme an"""
        dark_mode = self.config.get_dark_mode()

        if dark_mode:
            # Fusion Style mit Dark Palette
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
        else:
            # Standard Style
            QApplication.setStyle('Fusion')
            QApplication.setPalette(QApplication.style().standardPalette())

        # Plot bleibt immer im Light Mode
        plt.style.use('default')

    def toggle_dark_mode(self):
        """Schaltet Dark Mode um"""
        current_mode = self.config.get_dark_mode()
        new_mode = not current_mode
        self.config.set_dark_mode(new_mode)

        QMessageBox.information(self, "Dark Mode",
                               f"Dark Mode {'aktiviert' if new_mode else 'deaktiviert'}.\n"
                               "Bitte starten Sie die Anwendung neu, damit alle Änderungen wirksam werden.")

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
        self.ax_main.set_xlabel(plot_info['xlabel'])
        self.ax_main.set_ylabel(plot_info['ylabel'])
        self.ax_main.set_xscale(plot_info['xscale'])
        self.ax_main.set_yscale(plot_info['yscale'])

        if self.show_grid:
            self.ax_main.grid(True, alpha=0.3)

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

        # Legende
        if any(group.visible and group.datasets for group in self.groups) or self.unassigned_datasets:
            self.ax_main.legend(loc='best')

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

                    # In Tree einfügen
                    item = QTreeWidgetItem(self.unassigned_item, [dataset.name, ""])
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
                from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QDoubleSpinBox
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

    def show_context_menu(self, position):
        """Kontextmenü für Tree"""
        item = self.tree.itemAt(position)
        if not item:
            return

        from PySide6.QtWidgets import QMenu
        menu = QMenu()

        rename_action = menu.addAction("Umbenennen")
        menu.addSeparator()
        delete_action = menu.addAction("Löschen")

        action = menu.exec(self.tree.viewport().mapToGlobal(position))

        if action == rename_action:
            self.rename_item(item)
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

    def show_about(self):
        """Zeigt Über-Dialog"""
        QMessageBox.about(self, "Über TUBAF Scattering Plot Tool",
                         "TUBAF Scattering Plot Tool - Version 4.0 (Qt)\n\n"
                         "Professionelles Tool für Streudaten-Analyse\n\n"
                         "Features:\n"
                         "• Qt6-basierte moderne GUI\n"
                         "• Native Dark Mode Support\n"
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
                    'axis_limits': self.axis_limits
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
                        item.setData(0, Qt.UserRole, ('dataset', dataset))

                for dataset in self.unassigned_datasets:
                    item = QTreeWidgetItem(self.unassigned_item, [dataset.name, ""])
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


class PlotSettingsDialog(QDialog):
    """Dialog für erweiterte Plot-Einstellungen"""

    def __init__(self, parent, axis_limits):
        super().__init__(parent)
        self.setWindowTitle("Erweiterte Plot-Einstellungen")
        self.axis_limits = axis_limits.copy()

        layout = QVBoxLayout(self)

        # Achsenlimits
        limits_group = QGroupBox("Achsenlimits")
        limits_layout = QGridLayout()

        limits_layout.addWidget(QLabel("X min:"), 0, 0)
        self.xmin_edit = QLineEdit()
        if axis_limits['xmin'] is not None:
            self.xmin_edit.setText(str(axis_limits['xmin']))
        limits_layout.addWidget(self.xmin_edit, 0, 1)

        limits_layout.addWidget(QLabel("X max:"), 0, 2)
        self.xmax_edit = QLineEdit()
        if axis_limits['xmax'] is not None:
            self.xmax_edit.setText(str(axis_limits['xmax']))
        limits_layout.addWidget(self.xmax_edit, 0, 3)

        limits_layout.addWidget(QLabel("Y min:"), 1, 0)
        self.ymin_edit = QLineEdit()
        if axis_limits['ymin'] is not None:
            self.ymin_edit.setText(str(axis_limits['ymin']))
        limits_layout.addWidget(self.ymin_edit, 1, 1)

        limits_layout.addWidget(QLabel("Y max:"), 1, 2)
        self.ymax_edit = QLineEdit()
        if axis_limits['ymax'] is not None:
            self.ymax_edit.setText(str(axis_limits['ymax']))
        limits_layout.addWidget(self.ymax_edit, 1, 3)

        self.auto_checkbox = QCheckBox("Automatisch")
        self.auto_checkbox.setChecked(axis_limits.get('auto', True))
        limits_layout.addWidget(self.auto_checkbox, 2, 0, 1, 4)

        limits_group.setLayout(limits_layout)
        layout.addWidget(limits_group)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_limits(self):
        """Gibt Limits zurück"""
        try:
            xmin = float(self.xmin_edit.text()) if self.xmin_edit.text() else None
        except:
            xmin = None

        try:
            xmax = float(self.xmax_edit.text()) if self.xmax_edit.text() else None
        except:
            xmax = None

        try:
            ymin = float(self.ymin_edit.text()) if self.ymin_edit.text() else None
        except:
            ymin = None

        try:
            ymax = float(self.ymax_edit.text()) if self.ymax_edit.text() else None
        except:
            ymax = None

        return {
            'xmin': xmin,
            'xmax': xmax,
            'ymin': ymin,
            'ymax': ymax,
            'auto': self.auto_checkbox.isChecked()
        }


class CreateGroupDialog(QDialog):
    """Dialog zum Erstellen einer neuen Gruppe"""

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Neue Gruppe")
        self.resize(400, 150)

        layout = QVBoxLayout(self)

        # Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Gruppenname:"))
        self.name_edit = QLineEdit()
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        # Stack-Faktor
        factor_layout = QHBoxLayout()
        factor_layout.addWidget(QLabel("Stack-Faktor:"))
        from PySide6.QtWidgets import QDoubleSpinBox
        self.factor_spin = QDoubleSpinBox()
        self.factor_spin.setRange(0.1, 10000.0)
        self.factor_spin.setValue(1.0)
        self.factor_spin.setDecimals(2)
        self.factor_spin.setSingleStep(0.1)
        factor_layout.addWidget(self.factor_spin)
        layout.addLayout(factor_layout)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self):
        """Gibt Name und Stack-Faktor zurück"""
        return self.name_edit.text(), self.factor_spin.value()


class DesignManagerDialog(QDialog):
    """Design-Manager Dialog mit Tabs"""

    def __init__(self, parent, config):
        super().__init__(parent)
        self.setWindowTitle("Design-Manager")
        self.resize(700, 500)
        self.config = config
        self.parent_app = parent

        layout = QVBoxLayout(self)

        # Tab Widget
        from PySide6.QtWidgets import QTabWidget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Tabs erstellen
        self.create_styles_tab()
        self.create_colors_tab()
        self.create_autodetect_tab()

        # Schließen Button
        close_btn = QPushButton("Schließen")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def create_styles_tab(self):
        """Erstellt den Stil-Vorlagen Tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel("Verfügbare Stil-Vorlagen:"))

        # List Widget
        self.styles_list = QListWidget()
        layout.addWidget(self.styles_list)
        self.refresh_styles_list()

        # Buttons
        btn_layout = QHBoxLayout()
        new_btn = QPushButton("Neu...")
        new_btn.clicked.connect(self.create_new_style)
        btn_layout.addWidget(new_btn)

        edit_btn = QPushButton("Bearbeiten...")
        edit_btn.clicked.connect(self.edit_style)
        btn_layout.addWidget(edit_btn)

        delete_btn = QPushButton("Löschen")
        delete_btn.clicked.connect(self.delete_style)
        btn_layout.addWidget(delete_btn)

        layout.addLayout(btn_layout)
        self.tabs.addTab(tab, "Stil-Vorlagen")

    def create_colors_tab(self):
        """Erstellt den Farbschemata Tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel("Verfügbare Farbschemata:"))

        # List Widget
        self.colors_list = QListWidget()
        layout.addWidget(self.colors_list)
        self.refresh_colors_list()

        # Buttons
        btn_layout = QHBoxLayout()
        new_btn = QPushButton("Neu...")
        new_btn.clicked.connect(self.create_new_scheme)
        btn_layout.addWidget(new_btn)

        edit_btn = QPushButton("Bearbeiten...")
        edit_btn.clicked.connect(self.edit_scheme)
        btn_layout.addWidget(edit_btn)

        delete_btn = QPushButton("Löschen")
        delete_btn.clicked.connect(self.delete_scheme)
        btn_layout.addWidget(delete_btn)

        layout.addLayout(btn_layout)
        self.tabs.addTab(tab, "Farbschemata")

    def create_autodetect_tab(self):
        """Erstellt den Auto-Erkennung Tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel("Keyword → Stil Zuordnung:"))

        # List Widget
        self.autodetect_list = QListWidget()
        layout.addWidget(self.autodetect_list)
        self.refresh_autodetect_list()

        # Aktivieren Checkbox
        self.autodetect_enabled = QCheckBox("Auto-Erkennung aktiviert")
        self.autodetect_enabled.setChecked(self.config.auto_detection_enabled)
        self.autodetect_enabled.stateChanged.connect(self.toggle_autodetect)
        layout.addWidget(self.autodetect_enabled)

        # Buttons
        btn_layout = QHBoxLayout()
        new_btn = QPushButton("Neue Regel...")
        new_btn.clicked.connect(self.create_autodetect_rule)
        btn_layout.addWidget(new_btn)

        delete_btn = QPushButton("Löschen")
        delete_btn.clicked.connect(self.delete_autodetect_rule)
        btn_layout.addWidget(delete_btn)

        layout.addLayout(btn_layout)
        self.tabs.addTab(tab, "Auto-Erkennung")

    def refresh_styles_list(self):
        """Aktualisiert Stil-Liste"""
        self.styles_list.clear()
        for name, style in self.config.style_presets.items():
            desc = style.get('description', '')
            self.styles_list.addItem(f"{name}: {desc}")

    def refresh_colors_list(self):
        """Aktualisiert Farb-Liste"""
        self.colors_list.clear()
        for name in sorted(self.config.color_schemes.keys()):
            self.colors_list.addItem(name)

    def refresh_autodetect_list(self):
        """Aktualisiert Auto-Erkennung-Liste"""
        self.autodetect_list.clear()
        for keyword, style in self.config.auto_detection_rules.items():
            self.autodetect_list.addItem(f"{keyword} → {style}")

    def create_new_style(self):
        """Erstellt neuen Stil"""
        name, ok = QInputDialog.getText(self, "Neuer Stil", "Stil-Name:")
        if ok and name:
            style = {
                'line_style': '-',
                'marker_style': '',
                'line_width': 2,
                'marker_size': 4,
                'description': 'Benutzerdefiniert'
            }
            self.config.add_style_preset(name, style)
            self.refresh_styles_list()
            self.parent_app.update_plot()

    def edit_style(self):
        """Bearbeitet Stil"""
        current_item = self.styles_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "Info", "Bitte wählen Sie einen Stil aus")
            return

        name = current_item.text().split(':')[0]
        dialog = StylePresetEditDialog(self, name, self.config, self.refresh_styles_list, self.parent_app.update_plot)
        dialog.exec()

    def delete_style(self):
        """Löscht Stil"""
        current_item = self.styles_list.currentItem()
        if not current_item:
            return

        name = current_item.text().split(':')[0]
        reply = QMessageBox.question(self, "Löschen", f"Stil '{name}' löschen?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.config.delete_style_preset(name)
            self.refresh_styles_list()
            self.parent_app.update_plot()

    def create_new_scheme(self):
        """Erstellt neues Farbschema"""
        name, ok = QInputDialog.getText(self, "Neues Schema", "Schema-Name:")
        if not name or not ok:
            return

        # 5 Farben abfragen
        colors = []
        for i in range(5):
            color = QColorDialog.getColor(title=f"Farbe {i+1}")
            if color.isValid():
                colors.append(color.name())
            else:
                break

        if colors:
            self.config.save_color_scheme(name, colors)
            self.refresh_colors_list()
            self.parent_app.update_plot()

    def edit_scheme(self):
        """Bearbeitet Farbschema"""
        current_item = self.colors_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "Info", "Bitte wählen Sie ein Schema aus")
            return

        name = current_item.text()

        # Matplotlib-Schemata nicht bearbeitbar
        try:
            from user_config import get_matplotlib_colormaps
            matplotlib_maps = list(get_matplotlib_colormaps().keys())

            if name in matplotlib_maps:
                QMessageBox.information(self, "Info",
                    "Matplotlib-Schemata können nicht bearbeitet werden.\n"
                    "Sie können aber ein neues Schema erstellen und dieses als Vorlage verwenden.")
                return
        except Exception as e:
            print(f"Warnung: Fehler beim Laden der Matplotlib-Colormaps: {e}")
            matplotlib_maps = []

        if name in self.config.color_schemes:
            try:
                dialog = ColorSchemeEditDialog(self, name, self.config, self.refresh_colors_list, self.parent_app.update_plot)
                dialog.exec()
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Fehler beim Öffnen des Dialogs:\n{e}")
                print(f"Fehler beim Öffnen ColorSchemeEditDialog: {e}")
                import traceback
                traceback.print_exc()

    def delete_scheme(self):
        """Löscht Farbschema"""
        current_item = self.colors_list.currentItem()
        if not current_item:
            return

        name = current_item.text()
        if self.config.delete_color_scheme(name):
            self.refresh_colors_list()
            self.parent_app.update_plot()
        else:
            QMessageBox.information(self, "Info", "Standard-Schemata können nicht gelöscht werden")

    def create_autodetect_rule(self):
        """Erstellt Auto-Erkennungs-Regel"""
        keyword, ok = QInputDialog.getText(self, "Neues Keyword", "Keyword (z.B. 'fit'):")
        if not ok or not keyword:
            return

        styles = list(self.config.style_presets.keys())
        style, ok2 = QInputDialog.getItem(self, "Stil", "Stil wählen:", styles, 0, False)
        if not ok2 or not style:
            return

        self.config.auto_detection_rules[keyword.lower()] = style
        self.config.save_config()
        self.refresh_autodetect_list()

    def delete_autodetect_rule(self):
        """Löscht Auto-Erkennungs-Regel"""
        current_item = self.autodetect_list.currentItem()
        if not current_item:
            return

        text = current_item.text()
        keyword = text.split(' → ')[0]

        if keyword in self.config.auto_detection_rules:
            del self.config.auto_detection_rules[keyword]
            self.config.save_config()
            self.refresh_autodetect_list()

    def toggle_autodetect(self):
        """Schaltet Auto-Erkennung um"""
        self.config.auto_detection_enabled = self.autodetect_enabled.isChecked()
        self.config.save_config()


class StylePresetEditDialog(QDialog):
    """Dialog zum Bearbeiten von Stil-Vorlagen"""

    def __init__(self, parent, style_name, config, refresh_callback, plot_callback):
        super().__init__(parent)
        self.style_name = style_name
        self.config = config
        self.refresh_callback = refresh_callback
        self.plot_callback = plot_callback
        self.style = config.style_presets[style_name].copy()

        self.setWindowTitle(f"Stil bearbeiten: {style_name}")
        self.resize(450, 350)

        layout = QGridLayout(self)
        row = 0

        # Name
        layout.addWidget(QLabel("Name:"), row, 0)
        self.name_edit = QLineEdit(style_name)
        layout.addWidget(self.name_edit, row, 1)
        row += 1

        # Beschreibung
        layout.addWidget(QLabel("Beschreibung:"), row, 0)
        self.desc_edit = QLineEdit(self.style.get('description', ''))
        layout.addWidget(self.desc_edit, row, 1)
        row += 1

        # Linientyp
        layout.addWidget(QLabel("Linientyp:"), row, 0)
        self.line_combo = QComboBox()
        self.line_combo.addItems(['', '-', '--', '-.', ':'])
        self.line_combo.setCurrentText(self.style.get('line_style', ''))
        layout.addWidget(self.line_combo, row, 1)
        row += 1

        # Marker
        layout.addWidget(QLabel("Marker:"), row, 0)
        self.marker_combo = QComboBox()
        self.marker_combo.addItems(['', 'o', 's', '^', 'v', 'D', '*', '+', 'x', 'p', 'h'])
        self.marker_combo.setCurrentText(self.style.get('marker_style', ''))
        layout.addWidget(self.marker_combo, row, 1)
        row += 1

        # Linienbreite
        layout.addWidget(QLabel("Linienbreite:"), row, 0)
        from PySide6.QtWidgets import QDoubleSpinBox
        self.lw_spin = QDoubleSpinBox()
        self.lw_spin.setRange(0.5, 10.0)
        self.lw_spin.setValue(self.style.get('line_width', 2))
        self.lw_spin.setSingleStep(0.5)
        layout.addWidget(self.lw_spin, row, 1)
        row += 1

        # Markergröße
        layout.addWidget(QLabel("Markergröße:"), row, 0)
        from PySide6.QtWidgets import QSpinBox
        self.ms_spin = QSpinBox()
        self.ms_spin.setRange(1, 20)
        self.ms_spin.setValue(self.style.get('marker_size', 4))
        layout.addWidget(self.ms_spin, row, 1)
        row += 1

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons, row, 0, 1, 2)

    def save(self):
        """Speichert den bearbeiteten Stil"""
        new_name = self.name_edit.text()
        if not new_name:
            QMessageBox.critical(self, "Fehler", "Name darf nicht leer sein")
            return

        # Stil aktualisieren
        new_style = {
            'line_style': self.line_combo.currentText() or '',
            'marker_style': self.marker_combo.currentText() or '',
            'line_width': self.lw_spin.value(),
            'marker_size': self.ms_spin.value(),
            'description': self.desc_edit.text()
        }

        # Wenn Name geändert, alten löschen
        if new_name != self.style_name and self.style_name in self.config.style_presets:
            del self.config.style_presets[self.style_name]

        self.config.style_presets[new_name] = new_style
        self.config.save_style_presets()

        self.refresh_callback()
        self.plot_callback()
        self.accept()


class ColorSchemeEditDialog(QDialog):
    """Dialog zum Bearbeiten von Farbschemata"""

    def __init__(self, parent, scheme_name, config, refresh_callback, plot_callback):
        super().__init__(parent)
        self.scheme_name = scheme_name
        self.config = config
        self.refresh_callback = refresh_callback
        self.plot_callback = plot_callback
        self.colors = config.color_schemes[scheme_name].copy()

        self.setWindowTitle(f"Farbschema bearbeiten: {scheme_name}")
        self.resize(500, 500)

        layout = QVBoxLayout(self)

        # Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit(scheme_name)
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        # Farbliste
        layout.addWidget(QLabel("Farben:"))
        self.color_list = QListWidget()
        layout.addWidget(self.color_list)
        self.refresh_color_list()

        # Buttons für Farben
        color_btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ Hinzufügen")
        add_btn.clicked.connect(self.add_color)
        color_btn_layout.addWidget(add_btn)

        edit_btn = QPushButton("✏️ Ändern")
        edit_btn.clicked.connect(self.edit_color)
        color_btn_layout.addWidget(edit_btn)

        up_btn = QPushButton("↑ Hoch")
        up_btn.clicked.connect(self.move_up)
        color_btn_layout.addWidget(up_btn)

        down_btn = QPushButton("↓ Runter")
        down_btn.clicked.connect(self.move_down)
        color_btn_layout.addWidget(down_btn)

        remove_btn = QPushButton("× Entfernen")
        remove_btn.clicked.connect(self.remove_color)
        color_btn_layout.addWidget(remove_btn)

        layout.addLayout(color_btn_layout)

        # Hauptbuttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def refresh_color_list(self):
        """Aktualisiert die Farbliste mit Vorschau"""
        self.color_list.clear()
        for i, color in enumerate(self.colors):
            # Item mit Farb-Icon
            from PySide6.QtGui import QPixmap, QIcon
            pixmap = QPixmap(20, 20)
            pixmap.fill(QColor(color))
            icon = QIcon(pixmap)

            item = QListWidgetItem(icon, f"{i+1}. {color}")
            self.color_list.addItem(item)

    def add_color(self):
        """Fügt Farbe hinzu"""
        color = QColorDialog.getColor(title="Farbe wählen")
        if color.isValid():
            self.colors.append(color.name())
            self.refresh_color_list()

    def edit_color(self):
        """Ändert Farbe"""
        current_row = self.color_list.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "Info", "Bitte wählen Sie eine Farbe aus")
            return

        old_color = self.colors[current_row]
        color = QColorDialog.getColor(QColor(old_color), self, "Farbe ändern")
        if color.isValid():
            self.colors[current_row] = color.name()
            self.refresh_color_list()
            self.color_list.setCurrentRow(current_row)

    def move_up(self):
        """Verschiebt Farbe nach oben"""
        current_row = self.color_list.currentRow()
        if current_row <= 0:
            return

        self.colors[current_row], self.colors[current_row-1] = self.colors[current_row-1], self.colors[current_row]
        self.refresh_color_list()
        self.color_list.setCurrentRow(current_row-1)

    def move_down(self):
        """Verschiebt Farbe nach unten"""
        current_row = self.color_list.currentRow()
        if current_row < 0 or current_row >= len(self.colors) - 1:
            return

        self.colors[current_row], self.colors[current_row+1] = self.colors[current_row+1], self.colors[current_row]
        self.refresh_color_list()
        self.color_list.setCurrentRow(current_row+1)

    def remove_color(self):
        """Entfernt Farbe"""
        current_row = self.color_list.currentRow()
        if current_row < 0:
            return

        if len(self.colors) <= 2:
            QMessageBox.warning(self, "Warnung", "Mindestens 2 Farben erforderlich")
            return

        del self.colors[current_row]
        self.refresh_color_list()

    def save(self):
        """Speichert das Farbschema"""
        new_name = self.name_edit.text()
        if not new_name:
            QMessageBox.critical(self, "Fehler", "Name darf nicht leer sein")
            return

        if len(self.colors) < 2:
            QMessageBox.critical(self, "Fehler", "Mindestens 2 Farben erforderlich")
            return

        # Speichern
        self.config.save_color_scheme(new_name, self.colors)

        # Wenn Name geändert und nicht TUBAF, altes löschen
        if new_name != self.scheme_name and self.scheme_name != 'TUBAF':
            from user_config import get_matplotlib_colormaps
            if self.scheme_name not in get_matplotlib_colormaps():
                self.config.delete_color_scheme(self.scheme_name)

        self.refresh_callback()
        self.plot_callback()
        QMessageBox.information(self, "Erfolg", f"Farbschema '{new_name}' gespeichert")
        self.accept()


def main():
    """Hauptfunktion"""
    app = QApplication(sys.argv)

    # App-Metadaten
    app.setApplicationName("TUBAF Scattering Plot Tool")
    app.setOrganizationName("TU Bergakademie Freiberg")
    app.setApplicationVersion("4.0")

    # Hauptfenster
    window = ScatterPlotApp()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
