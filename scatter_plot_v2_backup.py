#!/usr/bin/env python3
"""
Scattering Plot Tool für TUBAF
Grafische Oberfläche zur Darstellung von Streukurven mit Gruppierung und gestackter Ansicht

Features:
- Drag & Drop für Gruppenzuordnung
- Individuelle Farb-, Stil- und Label-Anpassung
- PNG/SVG Export mit DPI-Einstellungen
- Session speichern/laden
- 4K DPI-Unterstützung
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser
import matplotlib
matplotlib.use('TkAgg')  # Backend für bessere Performance
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import numpy as np
from pathlib import Path
import json
import platform
import sys

from data_loader import load_scattering_data

# TUBAF Farben importieren
try:
    from tu_freiberg_colors import PRIMARY, SECONDARY, TERTIARY, get_profile_colors
    # Standard-Farbpalette für Plots erstellen
    DEFAULT_COLORS = [
        PRIMARY['uniblau']['hex'],
        SECONDARY['geo']['hex'],
        SECONDARY['material']['hex'],
        SECONDARY['energie']['hex'],
        SECONDARY['umwelt']['hex'],
        TERTIARY['orange_2']['hex'],
        TERTIARY['gruen_3']['hex'],
        TERTIARY['tuerkis_2']['hex'],
        TERTIARY['rot_6']['hex'],
        TERTIARY['blau_2']['hex'],
    ]
except ImportError:
    # Fallback falls tu_freiberg_colors nicht verfügbar
    DEFAULT_COLORS = ['#0069b4', '#8b7530', '#007b99', '#b71e3f', '#15882e',
                      '#e18409', '#95c11f', '#1e959a', '#cd1222', '#a1d9ef']


# ============================================================================
# DPI Awareness für 4K Displays
# ============================================================================

def enable_dpi_awareness():
    """Aktiviert DPI Awareness für scharfe Darstellung auf 4K Displays"""
    try:
        if platform.system() == 'Windows':
            # Windows DPI Awareness
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        elif platform.system() == 'Linux':
            # Linux/X11 DPI Scaling
            pass  # Wird über Tk scalingFactor gehandhabt
    except Exception as e:
        print(f"DPI Awareness konnte nicht aktiviert werden: {e}")


# ============================================================================
# Datenklassen
# ============================================================================

class DataSet:
    """Repräsentiert einen einzelnen Datensatz"""
    def __init__(self, filepath, name=None):
        self.filepath = Path(filepath)
        self.name = name or self.filepath.stem
        self.display_label = self.name  # Anzeigename (editierbar)
        self.data = None
        self.x = None
        self.y = None
        self.y_err = None

        # Plot-Stil Einstellungen
        self.line_style = None  # None = auto
        self.marker_style = None  # None = auto
        self.color = None  # None = Gruppenfarbe verwenden
        self.line_width = 2
        self.marker_size = 4
        self.show_in_legend = True

        self.load_data()

    def load_data(self):
        """Lädt die Daten aus der Datei"""
        try:
            self.data = load_scattering_data(self.filepath)
            self.x = self.data[:, 0]
            self.y = self.data[:, 1]
            if self.data.shape[1] > 2:
                self.y_err = self.data[:, 2]
            else:
                self.y_err = None
        except Exception as e:
            raise ValueError(f"Fehler beim Laden von {self.filepath}: {e}")

    def get_plot_style(self):
        """Gibt den Plot-Stil zurück (auto oder manuell gesetzt)"""
        line_style = self.line_style
        marker_style = self.marker_style

        if line_style is None:
            # Auto-Erkennung: Fits bekommen Linien, Messungen Punkte
            line_style = '-' if 'fit' in self.name.lower() else ''

        if marker_style is None:
            marker_style = '' if 'fit' in self.name.lower() else 'o'

        return line_style + marker_style

    def to_dict(self):
        """Serialisiert den Datensatz für Session-Speicherung"""
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
        """Lädt Datensatz aus gespeicherten Daten"""
        dataset = cls(data['filepath'], data.get('name'))
        dataset.display_label = data.get('display_label', dataset.name)
        dataset.line_style = data.get('line_style')
        dataset.marker_style = data.get('marker_style')
        dataset.color = data.get('color')
        dataset.line_width = data.get('line_width', 2)
        dataset.marker_size = data.get('marker_size', 4)
        dataset.show_in_legend = data.get('show_in_legend', True)
        return dataset


class DataGroup:
    """Repräsentiert eine Gruppe von Datensätzen"""
    def __init__(self, name, stack_factor=1.0):
        self.name = name
        self.datasets = []
        self.stack_factor = stack_factor
        self.color = None  # None = Auto-Farbe
        self.show_group_in_legend = True

    def add_dataset(self, dataset):
        """Fügt einen Datensatz zur Gruppe hinzu"""
        self.datasets.append(dataset)

    def remove_dataset(self, dataset):
        """Entfernt einen Datensatz aus der Gruppe"""
        if dataset in self.datasets:
            self.datasets.remove(dataset)

    def to_dict(self):
        """Serialisiert die Gruppe für Session-Speicherung"""
        return {
            'name': self.name,
            'stack_factor': self.stack_factor,
            'color': self.color,
            'show_group_in_legend': self.show_group_in_legend,
            'datasets': [ds.to_dict() for ds in self.datasets]
        }

    @classmethod
    def from_dict(cls, data):
        """Lädt Gruppe aus gespeicherten Daten"""
        group = cls(data['name'], data.get('stack_factor', 1.0))
        group.color = data.get('color')
        group.show_group_in_legend = data.get('show_group_in_legend', True)
        for ds_data in data.get('datasets', []):
            try:
                dataset = DataSet.from_dict(ds_data)
                group.add_dataset(dataset)
            except Exception as e:
                print(f"Fehler beim Laden von Datensatz: {e}")
        return group


# ============================================================================
# Haupt-Anwendung
# ============================================================================

class ScatterPlotApp:
    """Hauptanwendung für Scattering Plot Tool"""

    def __init__(self, root):
        self.root = root
        self.root.title("TUBAF Scattering Plot Tool")
        self.root.geometry("1600x1000")

        # Datenverwaltung
        self.groups = []
        self.color_palette = DEFAULT_COLORS.copy()

        # Plot-Einstellungen
        self.plot_settings = {
            'stack_mode': True,
            'xlabel': 'q / nm⁻¹',
            'ylabel': 'Intensität / a.u.',
            'show_grid': True,
            'grid_which': 'both',
            'grid_alpha': 0.3,
            'legend_fontsize': 10,
            'axis_fontsize': 12,
            'figure_dpi': 100,
            'export_dpi': 300,
        }

        # Drag & Drop State
        self.drag_data = None

        # GUI erstellen
        self.create_gui()
        self.create_menu()

    def create_menu(self):
        """Erstellt die Menüleiste"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Datei-Menü
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Datei", menu=file_menu)
        file_menu.add_command(label="Session speichern", command=self.save_session)
        file_menu.add_command(label="Session laden", command=self.load_session)
        file_menu.add_separator()
        file_menu.add_command(label="Exportieren als PNG", command=self.export_png)
        file_menu.add_command(label="Exportieren als SVG", command=self.export_svg)
        file_menu.add_separator()
        file_menu.add_command(label="Beenden", command=self.root.quit)

        # Plot-Menü
        plot_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Plot", menu=plot_menu)
        plot_menu.add_command(label="Aktualisieren", command=self.update_plot)
        plot_menu.add_command(label="Einstellungen", command=self.show_plot_settings)

        # Hilfe-Menü
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Hilfe", menu=help_menu)
        help_menu.add_command(label="Über", command=self.show_about)

    def create_gui(self):
        """Erstellt die grafische Benutzeroberfläche"""

        # Hauptcontainer mit Paned Window
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Linke Seite: Datenverwaltung
        left_frame = ttk.Frame(main_paned, width=450)
        main_paned.add(left_frame, weight=1)

        # Rechte Seite: Plot
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=3)

        # === Linke Seite: Kontrollen ===

        # Buttons für Datenverwaltung
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(button_frame, text="➕ Neue Gruppe",
                   command=self.create_group).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="📁 Daten laden",
                   command=self.load_data_simple).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="🗑 Löschen",
                   command=self.delete_selected).pack(side=tk.LEFT, padx=2)

        # Treeview für Gruppen und Datensätze
        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Scrollbars
        tree_scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(tree_frame,
                                  columns=("info",),
                                  yscrollcommand=tree_scroll_y.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll_y.config(command=self.tree.yview)

        self.tree.heading("#0", text="Name")
        self.tree.heading("info", text="Info")
        self.tree.column("info", width=100)

        # Event-Bindings für Drag & Drop und Kontextmenü
        self.tree.bind("<ButtonPress-1>", self.on_tree_press)
        self.tree.bind("<B1-Motion>", self.on_tree_motion)
        self.tree.bind("<ButtonRelease-1>", self.on_tree_release)
        self.tree.bind("<Double-Button-1>", self.on_tree_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)  # Rechtsklick

        # Kontext-Menü erstellen
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Umbenennen", command=self.rename_item)
        self.context_menu.add_command(label="Farbe ändern", command=self.change_color)
        self.context_menu.add_command(label="Stil ändern", command=self.change_style)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Löschen", command=self.delete_selected)

        # Schnell-Optionen
        options_frame = ttk.LabelFrame(left_frame, text="Schnell-Optionen")
        options_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(options_frame, text="Stack-Modus:").grid(row=0, column=0,
                                                            sticky=tk.W, padx=5, pady=2)
        self.stack_mode_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Aktiviert",
                        variable=self.stack_mode_var,
                        command=self.update_plot).grid(row=0, column=1,
                                                        sticky=tk.W, padx=5, pady=2)

        ttk.Label(options_frame, text="Grid:").grid(row=1, column=0,
                                                     sticky=tk.W, padx=5, pady=2)
        self.grid_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Anzeigen",
                        variable=self.grid_var,
                        command=self.update_plot).grid(row=1, column=1,
                                                        sticky=tk.W, padx=5, pady=2)

        options_frame.columnconfigure(1, weight=1)

        # Plot-Button
        plot_button_frame = ttk.Frame(left_frame)
        plot_button_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(plot_button_frame, text="🔄 Plot aktualisieren",
                   command=self.update_plot).pack(fill=tk.X)

        # === Rechte Seite: Matplotlib Plot ===

        self.fig = Figure(figsize=(12, 9), dpi=self.plot_settings['figure_dpi'])
        self.ax = self.fig.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(self.fig, master=right_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Matplotlib Toolbar
        toolbar = NavigationToolbar2Tk(self.canvas, right_frame)
        toolbar.update()

        # Initial-Plot
        self.update_plot()

    # ========================================================================
    # Drag & Drop Funktionalität
    # ========================================================================

    def on_tree_press(self, event):
        """Start von Drag & Drop"""
        item = self.tree.identify_row(event.y)
        if item:
            self.drag_data = {'item': item, 'start_y': event.y}

    def on_tree_motion(self, event):
        """Während Drag & Drop"""
        if self.drag_data and abs(event.y - self.drag_data['start_y']) > 5:
            # Cursor ändern um Drag zu signalisieren
            self.tree.config(cursor="hand2")

    def on_tree_release(self, event):
        """Ende von Drag & Drop"""
        if self.drag_data:
            source_item = self.drag_data['item']
            target_item = self.tree.identify_row(event.y)

            if target_item and source_item != target_item:
                # Prüfen ob Datensatz auf Gruppe gedroppt wird
                source_parent = self.tree.parent(source_item)
                target_parent = self.tree.parent(target_item)

                # Datensatz wird auf Gruppe gedroppt
                if source_parent and not target_parent:
                    self.move_dataset_to_group(source_item, target_item)
                # Datensatz wird auf Datensatz gedroppt (zur gleichen Gruppe)
                elif source_parent and target_parent:
                    self.move_dataset_to_group(source_item, target_parent)

            self.tree.config(cursor="")
            self.drag_data = None

    def move_dataset_to_group(self, dataset_item, target_group_item):
        """Verschiebt einen Datensatz in eine andere Gruppe"""
        # Namen ermitteln
        dataset_name = self.tree.item(dataset_item, 'text')
        source_group_name = self.tree.item(self.tree.parent(dataset_item), 'text')
        target_group_name = self.tree.item(target_group_item, 'text')

        if source_group_name == target_group_name:
            return  # Gleiche Gruppe

        # Datensatz und Gruppen finden
        source_group = next((g for g in self.groups if g.name == source_group_name), None)
        target_group = next((g for g in self.groups if g.name == target_group_name), None)

        if source_group and target_group:
            dataset = next((d for d in source_group.datasets if d.name == dataset_name), None)
            if dataset:
                # Verschieben
                source_group.remove_dataset(dataset)
                target_group.add_dataset(dataset)

                # Tree aktualisieren
                self.tree.delete(dataset_item)
                self.tree.insert(target_group_item, tk.END, text=dataset.display_label,
                               values=("",), tags=("dataset",))

                self.update_plot()

    # ========================================================================
    # Kontextmenü und Bearbeitungs-Funktionen
    # ========================================================================

    def show_context_menu(self, event):
        """Zeigt Kontextmenü bei Rechtsklick"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def on_tree_double_click(self, event):
        """Doppelklick zum schnellen Bearbeiten"""
        selected = self.tree.selection()
        if not selected:
            return

        item = selected[0]
        parent = self.tree.parent(item)

        if not parent:  # Gruppe
            self.edit_stack_factor(item)
        else:  # Datensatz
            self.rename_item()

    def rename_item(self):
        """Benennt Gruppe oder Datensatz um"""
        selected = self.tree.selection()
        if not selected:
            return

        item = selected[0]
        item_text = self.tree.item(item, 'text')
        parent = self.tree.parent(item)

        new_name = simpledialog.askstring("Umbenennen", "Neuer Name:", initialvalue=item_text)
        if not new_name:
            return

        if not parent:  # Gruppe
            group = next((g for g in self.groups if g.name == item_text), None)
            if group:
                group.name = new_name
                self.tree.item(item, text=new_name)
        else:  # Datensatz
            parent_name = self.tree.item(parent, 'text')
            group = next((g for g in self.groups if g.name == parent_name), None)
            if group:
                dataset = next((d for d in group.datasets if d.display_label == item_text), None)
                if dataset:
                    dataset.display_label = new_name
                    self.tree.item(item, text=new_name)

        self.update_plot()

    def change_color(self):
        """Ändert die Farbe einer Gruppe oder eines Datensatzes"""
        selected = self.tree.selection()
        if not selected:
            return

        item = selected[0]
        item_text = self.tree.item(item, 'text')
        parent = self.tree.parent(item)

        # Aktuelle Farbe ermitteln
        current_color = '#0069b4'
        if not parent:  # Gruppe
            group = next((g for g in self.groups if g.name == item_text), None)
            if group and group.color:
                current_color = group.color
        else:  # Datensatz
            parent_name = self.tree.item(parent, 'text')
            group = next((g for g in self.groups if g.name == parent_name), None)
            if group:
                dataset = next((d for d in group.datasets if d.display_label == item_text), None)
                if dataset and dataset.color:
                    current_color = dataset.color

        # Farbauswahl-Dialog
        color = colorchooser.askcolor(color=current_color, title="Farbe wählen")
        if not color[1]:
            return

        new_color = color[1]

        # Farbe setzen
        if not parent:  # Gruppe
            group = next((g for g in self.groups if g.name == item_text), None)
            if group:
                group.color = new_color
        else:  # Datensatz
            parent_name = self.tree.item(parent, 'text')
            group = next((g for g in self.groups if g.name == parent_name), None)
            if group:
                dataset = next((d for d in group.datasets if d.display_label == item_text), None)
                if dataset:
                    dataset.color = new_color

        self.update_plot()

    def change_style(self):
        """Ändert den Stil eines Datensatzes (Linientyp, Marker)"""
        selected = self.tree.selection()
        if not selected:
            return

        item = selected[0]
        parent = self.tree.parent(item)

        if not parent:
            messagebox.showinfo("Info", "Stil kann nur für Datensätze geändert werden")
            return

        item_text = self.tree.item(item, 'text')
        parent_name = self.tree.item(parent, 'text')
        group = next((g for g in self.groups if g.name == parent_name), None)

        if not group:
            return

        dataset = next((d for d in group.datasets if d.display_label == item_text), None)
        if not dataset:
            return

        # Dialog für Stil-Einstellungen
        StyleDialog(self.root, dataset, self.update_plot)

    def edit_stack_factor(self, item=None):
        """Bearbeitet den Stack-Faktor einer Gruppe"""
        if item is None:
            selected = self.tree.selection()
            if not selected:
                return
            item = selected[0]

        parent = self.tree.parent(item)
        if parent:  # Nur für Gruppen
            return

        item_text = self.tree.item(item, 'text')
        group = next((g for g in self.groups if g.name == item_text), None)

        if group:
            new_factor = simpledialog.askfloat("Stack-Faktor bearbeiten",
                                                f"Neuer Stack-Faktor für '{group.name}':",
                                                initialvalue=group.stack_factor)
            if new_factor is not None:
                group.stack_factor = new_factor
                self.tree.item(item, values=(f"×{new_factor}",))
                self.update_plot()

    # ========================================================================
    # Daten laden und verwalten
    # ========================================================================

    def create_group(self):
        """Erstellt eine neue Gruppe"""
        name = simpledialog.askstring("Neue Gruppe", "Gruppenname:")
        if not name:
            return

        stack_factor = simpledialog.askfloat("Stack-Faktor",
                                              "Stack-Faktor (z.B. 1, 10, 100):",
                                              initialvalue=1.0)
        if stack_factor is None:
            stack_factor = 1.0

        group = DataGroup(name, stack_factor)
        self.groups.append(group)

        # In Treeview einfügen
        group_id = self.tree.insert("", tk.END, text=name,
                                    values=(f"×{stack_factor}",),
                                    tags=("group",))
        self.tree.item(group_id, open=True)

    def load_data_simple(self):
        """Einfaches Laden von Daten - Dateien wählen, dann Gruppe zuordnen"""
        # Dateien auswählen
        filepaths = filedialog.askopenfilenames(
            title="Datensätze auswählen",
            filetypes=[("Alle Dateien", "*.*"),
                       ("Text-Dateien", "*.txt"),
                       ("CSV-Dateien", "*.csv"),
                       ("DAT-Dateien", "*.dat")]
        )

        if not filepaths:
            return

        # Falls keine Gruppen vorhanden, eine erstellen
        if not self.groups:
            self.create_group()
            if not self.groups:  # Benutzer hat abgebrochen
                return

        # Gruppe auswählen
        group_names = [g.name for g in self.groups]
        if len(group_names) == 1:
            group_name = group_names[0]
        else:
            group_name = simpledialog.askstring("Gruppe wählen",
                                                f"Gruppenname (verfügbar: {', '.join(group_names)}):")

        group = next((g for g in self.groups if g.name == group_name), None)
        if not group:
            messagebox.showerror("Fehler", f"Gruppe '{group_name}' nicht gefunden")
            return

        # Dateien laden
        for filepath in filepaths:
            try:
                dataset = DataSet(filepath)
                group.add_dataset(dataset)

                # In Treeview einfügen
                for item in self.tree.get_children():
                    if self.tree.item(item, "text") == group.name:
                        self.tree.insert(item, tk.END, text=dataset.display_label,
                                        values=("",), tags=("dataset",))
                        break

            except Exception as e:
                messagebox.showerror("Fehler", f"Fehler beim Laden von {filepath}:\n{e}")

        self.update_plot()

    def delete_selected(self):
        """Löscht ausgewählte Gruppe oder Datensatz"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie ein Element aus")
            return

        for item in selected:
            item_text = self.tree.item(item, "text")
            parent = self.tree.parent(item)

            if not parent:  # Gruppe
                group = next((g for g in self.groups if g.name == item_text), None)
                if group:
                    self.groups.remove(group)
            else:  # Datensatz
                parent_text = self.tree.item(parent, "text")
                group = next((g for g in self.groups if g.name == parent_text), None)
                if group:
                    dataset = next((d for d in group.datasets if d.display_label == item_text), None)
                    if dataset:
                        group.remove_dataset(dataset)

            self.tree.delete(item)

        self.update_plot()

    # ========================================================================
    # Plot-Funktionen
    # ========================================================================

    def update_plot(self):
        """Aktualisiert den Plot mit allen Gruppen und Datensätzen"""
        self.ax.clear()

        if not self.groups:
            self.ax.text(0.5, 0.5, "Keine Daten geladen\n\nDateien per Drag & Drop oder '📁 Daten laden'",
                        ha='center', va='center', transform=self.ax.transAxes,
                        fontsize=14, color='gray')
            self.canvas.draw()
            return

        # Farbpalette vorbereiten
        colors = self.color_palette.copy()

        stack_mode = self.stack_mode_var.get()

        # Plot jede Gruppe
        for group_idx, group in enumerate(self.groups):
            if not group.datasets:
                continue

            # Farbe für die Gruppe
            group_color = group.color if group.color else colors[group_idx % len(colors)]

            # Stack-Faktor
            stack_factor = group.stack_factor if stack_mode else 1.0

            # Plot jeden Datensatz in der Gruppe
            for ds_idx, dataset in enumerate(group.datasets):
                if dataset.x is None or dataset.y is None:
                    continue

                # Y-Werte mit Stack-Faktor
                y_plot = dataset.y * stack_factor

                # Farbe: Datensatz-Farbe oder Gruppenfarbe
                plot_color = dataset.color if dataset.color else group_color

                # Label
                if dataset.show_in_legend:
                    if stack_mode and ds_idx == 0:
                        label = f"{group.name} (×{stack_factor}) - {dataset.display_label}"
                    else:
                        label = f"{group.name} - {dataset.display_label}"
                else:
                    label = None

                # Plot-Stil
                plot_style = dataset.get_plot_style()

                # Hauptplot
                self.ax.plot(dataset.x, y_plot, plot_style,
                           color=plot_color,
                           linewidth=dataset.line_width,
                           markersize=dataset.marker_size,
                           label=label,
                           alpha=0.8)

                # Fehlerbereich
                if dataset.y_err is not None:
                    y_err_plot = dataset.y_err * stack_factor
                    self.ax.fill_between(dataset.x,
                                        y_plot - y_err_plot,
                                        y_plot + y_err_plot,
                                        color=plot_color,
                                        alpha=0.2)

        # Achsen-Einstellungen
        self.ax.set_xscale('log')
        self.ax.set_yscale('log')
        self.ax.set_xlabel(self.plot_settings['xlabel'],
                          fontsize=self.plot_settings['axis_fontsize'])
        self.ax.set_ylabel(self.plot_settings['ylabel'],
                          fontsize=self.plot_settings['axis_fontsize'])

        if self.grid_var.get():
            self.ax.grid(True,
                        alpha=self.plot_settings['grid_alpha'],
                        which=self.plot_settings['grid_which'])

        self.ax.legend(fontsize=self.plot_settings['legend_fontsize'],
                      framealpha=0.9)

        self.fig.tight_layout()
        self.canvas.draw()

    def show_plot_settings(self):
        """Zeigt Dialog für erweiterte Plot-Einstellungen"""
        PlotSettingsDialog(self.root, self.plot_settings, self.update_plot)

    # ========================================================================
    # Session speichern/laden
    # ========================================================================

    def save_session(self):
        """Speichert die aktuelle Session"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Dateien", "*.json"), ("Alle Dateien", "*.*")],
            title="Session speichern"
        )

        if not filepath:
            return

        try:
            session_data = {
                'groups': [g.to_dict() for g in self.groups],
                'plot_settings': self.plot_settings,
                'color_palette': self.color_palette
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2)

            messagebox.showinfo("Erfolg", f"Session gespeichert in:\n{filepath}")

        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Speichern:\n{e}")

    def load_session(self):
        """Lädt eine gespeicherte Session"""
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON Dateien", "*.json"), ("Alle Dateien", "*.*")],
            title="Session laden"
        )

        if not filepath:
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            # Alte Daten löschen
            self.groups.clear()
            for item in self.tree.get_children():
                self.tree.delete(item)

            # Gruppen laden
            for group_data in session_data.get('groups', []):
                group = DataGroup.from_dict(group_data)
                self.groups.append(group)

                # In Tree einfügen
                group_id = self.tree.insert("", tk.END, text=group.name,
                                           values=(f"×{group.stack_factor}",),
                                           tags=("group",))
                self.tree.item(group_id, open=True)

                for dataset in group.datasets:
                    self.tree.insert(group_id, tk.END, text=dataset.display_label,
                                   values=("",), tags=("dataset",))

            # Einstellungen laden
            if 'plot_settings' in session_data:
                self.plot_settings.update(session_data['plot_settings'])

            if 'color_palette' in session_data:
                self.color_palette = session_data['color_palette']

            self.update_plot()
            messagebox.showinfo("Erfolg", "Session geladen")

        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Laden:\n{e}")

    # ========================================================================
    # Export-Funktionen
    # ========================================================================

    def export_png(self):
        """Exportiert den Plot als PNG"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Dateien", "*.png"), ("Alle Dateien", "*.*")],
            title="Als PNG exportieren"
        )

        if not filepath:
            return

        # DPI abfragen
        dpi = simpledialog.askinteger("Export DPI",
                                      "DPI für Export (z.B. 300 für Publikation):",
                                      initialvalue=self.plot_settings['export_dpi'],
                                      minvalue=72,
                                      maxvalue=1200)
        if not dpi:
            dpi = self.plot_settings['export_dpi']

        try:
            self.fig.savefig(filepath, dpi=dpi, bbox_inches='tight', facecolor='white')
            messagebox.showinfo("Erfolg", f"Plot exportiert als:\n{filepath}\nDPI: {dpi}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Exportieren:\n{e}")

    def export_svg(self):
        """Exportiert den Plot als SVG"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".svg",
            filetypes=[("SVG Dateien", "*.svg"), ("Alle Dateien", "*.*")],
            title="Als SVG exportieren"
        )

        if not filepath:
            return

        try:
            self.fig.savefig(filepath, format='svg', bbox_inches='tight')
            messagebox.showinfo("Erfolg", f"Plot exportiert als:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Exportieren:\n{e}")

    def show_about(self):
        """Zeigt Über-Dialog"""
        about_text = """TUBAF Scattering Plot Tool
Version 2.0

Entwickelt für die TU Bergakademie Freiberg

Features:
• Drag & Drop Gruppenzuordnung
• Individuelle Farb- und Stil-Anpassung
• PNG/SVG Export
• Session speichern/laden
• 4K Display-Unterstützung

© 2024 TU Bergakademie Freiberg"""

        messagebox.showinfo("Über", about_text)


# ============================================================================
# Dialog-Klassen
# ============================================================================

class StyleDialog:
    """Dialog zum Ändern des Datensatz-Stils"""
    def __init__(self, parent, dataset, update_callback):
        self.dataset = dataset
        self.update_callback = update_callback

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Stil ändern: {dataset.display_label}")
        self.dialog.geometry("400x350")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Linientyp
        ttk.Label(self.dialog, text="Linientyp:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        self.line_var = tk.StringVar(value=dataset.line_style or 'auto')
        line_combo = ttk.Combobox(self.dialog, textvariable=self.line_var,
                                   values=['auto', '-', '--', '-.', ':', ''], width=15)
        line_combo.grid(row=0, column=1, sticky=tk.W, padx=10, pady=5)

        # Markertyp
        ttk.Label(self.dialog, text="Marker:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        self.marker_var = tk.StringVar(value=dataset.marker_style or 'auto')
        marker_combo = ttk.Combobox(self.dialog, textvariable=self.marker_var,
                                     values=['auto', 'o', 's', '^', 'v', 'D', '*', '+', 'x', ''], width=15)
        marker_combo.grid(row=1, column=1, sticky=tk.W, padx=10, pady=5)

        # Linienbreite
        ttk.Label(self.dialog, text="Linienbreite:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        self.linewidth_var = tk.DoubleVar(value=dataset.line_width)
        ttk.Spinbox(self.dialog, from_=0.5, to=10, increment=0.5,
                    textvariable=self.linewidth_var, width=15).grid(row=2, column=1, sticky=tk.W, padx=10, pady=5)

        # Markergröße
        ttk.Label(self.dialog, text="Markergröße:").grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)
        self.markersize_var = tk.DoubleVar(value=dataset.marker_size)
        ttk.Spinbox(self.dialog, from_=1, to=20, increment=1,
                    textvariable=self.markersize_var, width=15).grid(row=3, column=1, sticky=tk.W, padx=10, pady=5)

        # In Legende anzeigen
        ttk.Label(self.dialog, text="In Legende:").grid(row=4, column=0, sticky=tk.W, padx=10, pady=5)
        self.legend_var = tk.BooleanVar(value=dataset.show_in_legend)
        ttk.Checkbutton(self.dialog, text="Anzeigen",
                        variable=self.legend_var).grid(row=4, column=1, sticky=tk.W, padx=10, pady=5)

        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.grid(row=5, column=0, columnspan=2, pady=20)

        ttk.Button(button_frame, text="Übernehmen", command=self.apply).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Abbrechen", command=self.dialog.destroy).pack(side=tk.LEFT, padx=5)

    def apply(self):
        """Wendet die Änderungen an"""
        line_val = self.line_var.get()
        self.dataset.line_style = None if line_val == 'auto' else line_val

        marker_val = self.marker_var.get()
        self.dataset.marker_style = None if marker_val == 'auto' else marker_val

        self.dataset.line_width = self.linewidth_var.get()
        self.dataset.marker_size = self.markersize_var.get()
        self.dataset.show_in_legend = self.legend_var.get()

        self.update_callback()
        self.dialog.destroy()


class PlotSettingsDialog:
    """Dialog für erweiterte Plot-Einstellungen"""
    def __init__(self, parent, settings, update_callback):
        self.settings = settings
        self.update_callback = update_callback

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Plot-Einstellungen")
        self.dialog.geometry("500x450")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # X-Label
        ttk.Label(self.dialog, text="X-Achsen Label:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        self.xlabel_var = tk.StringVar(value=settings['xlabel'])
        ttk.Entry(self.dialog, textvariable=self.xlabel_var, width=30).grid(row=0, column=1, sticky=tk.W, padx=10, pady=5)

        # Y-Label
        ttk.Label(self.dialog, text="Y-Achsen Label:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        self.ylabel_var = tk.StringVar(value=settings['ylabel'])
        ttk.Entry(self.dialog, textvariable=self.ylabel_var, width=30).grid(row=1, column=1, sticky=tk.W, padx=10, pady=5)

        # Grid
        ttk.Label(self.dialog, text="Grid Modus:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        self.grid_which_var = tk.StringVar(value=settings['grid_which'])
        ttk.Combobox(self.dialog, textvariable=self.grid_which_var,
                     values=['both', 'major', 'minor'], width=27).grid(row=2, column=1, sticky=tk.W, padx=10, pady=5)

        # Grid Alpha
        ttk.Label(self.dialog, text="Grid Transparenz:").grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)
        self.grid_alpha_var = tk.DoubleVar(value=settings['grid_alpha'])
        ttk.Scale(self.dialog, from_=0, to=1, variable=self.grid_alpha_var,
                  orient=tk.HORIZONTAL).grid(row=3, column=1, sticky=tk.EW, padx=10, pady=5)

        # Legenden-Schriftgröße
        ttk.Label(self.dialog, text="Legenden-Schriftgröße:").grid(row=4, column=0, sticky=tk.W, padx=10, pady=5)
        self.legend_fontsize_var = tk.IntVar(value=settings['legend_fontsize'])
        ttk.Spinbox(self.dialog, from_=6, to=20, textvariable=self.legend_fontsize_var,
                    width=27).grid(row=4, column=1, sticky=tk.W, padx=10, pady=5)

        # Achsen-Schriftgröße
        ttk.Label(self.dialog, text="Achsen-Schriftgröße:").grid(row=5, column=0, sticky=tk.W, padx=10, pady=5)
        self.axis_fontsize_var = tk.IntVar(value=settings['axis_fontsize'])
        ttk.Spinbox(self.dialog, from_=6, to=20, textvariable=self.axis_fontsize_var,
                    width=27).grid(row=5, column=1, sticky=tk.W, padx=10, pady=5)

        # Export DPI
        ttk.Label(self.dialog, text="Standard Export DPI:").grid(row=6, column=0, sticky=tk.W, padx=10, pady=5)
        self.export_dpi_var = tk.IntVar(value=settings['export_dpi'])
        ttk.Spinbox(self.dialog, from_=72, to=1200, increment=50,
                    textvariable=self.export_dpi_var, width=27).grid(row=6, column=1, sticky=tk.W, padx=10, pady=5)

        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.grid(row=7, column=0, columnspan=2, pady=20)

        ttk.Button(button_frame, text="Übernehmen", command=self.apply).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Abbrechen", command=self.dialog.destroy).pack(side=tk.LEFT, padx=5)

    def apply(self):
        """Wendet die Änderungen an"""
        self.settings['xlabel'] = self.xlabel_var.get()
        self.settings['ylabel'] = self.ylabel_var.get()
        self.settings['grid_which'] = self.grid_which_var.get()
        self.settings['grid_alpha'] = self.grid_alpha_var.get()
        self.settings['legend_fontsize'] = self.legend_fontsize_var.get()
        self.settings['axis_fontsize'] = self.axis_fontsize_var.get()
        self.settings['export_dpi'] = self.export_dpi_var.get()

        self.update_callback()
        self.dialog.destroy()


# ============================================================================
# Hauptfunktion
# ============================================================================

def main():
    """Hauptfunktion"""
    # DPI Awareness aktivieren
    enable_dpi_awareness()

    root = tk.Tk()

    # Verbesserte DPI-Skalierung für Linux/X11
    if platform.system() == 'Linux':
        try:
            dpi = root.winfo_fpixels('1i')
            if dpi > 96:  # 4K oder High-DPI Display
                scale_factor = dpi / 96
                root.tk.call('tk', 'scaling', scale_factor)
        except:
            pass

    app = ScatterPlotApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
