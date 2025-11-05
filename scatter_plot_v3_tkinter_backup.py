#!/usr/bin/env python3
"""
TUBAF Scattering Plot Tool - Version 3.0
========================================

Professionelles Tool für Streudaten-Analyse mit:
- Verschiedene Plot-Typen (Log-Log, Porod, Kratky, Guinier, PDDF)
- Stil-Vorlagen und Auto-Erkennung
- Farbschema-Manager
- Drag & Drop
- Session-Verwaltung
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
import numpy as np
from pathlib import Path
import json
import platform

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


def enable_dpi_awareness():
    """Aktiviert DPI Awareness für 4K Displays"""
    try:
        if platform.system() == 'Windows':
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass


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
        self.color = None
        self.show_group_in_legend = True
    
    def add_dataset(self, dataset):
        self.datasets.append(dataset)
    
    def remove_dataset(self, dataset):
        if dataset in self.datasets:
            self.datasets.remove(dataset)
    
    def to_dict(self):
        return {
            'name': self.name,
            'stack_factor': self.stack_factor,
            'color': self.color,
            'show_group_in_legend': self.show_group_in_legend,
            'datasets': [ds.to_dict() for ds in self.datasets]
        }
    
    @classmethod
    def from_dict(cls, data):
        group = cls(data['name'], data.get('stack_factor', 1.0))
        group.color = data.get('color')
        group.show_group_in_legend = data.get('show_group_in_legend', True)
        for ds_data in data.get('datasets', []):
            try:
                dataset = DataSet.from_dict(ds_data)
                group.add_dataset(dataset)
            except Exception as e:
                print(f"Fehler beim Laden: {e}")
        return group


class ScatterPlotApp:
    """Hauptanwendung"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("TUBAF Scattering Plot Tool v3.0")
        self.root.geometry("1600x1000")
        
        # Config
        self.config = get_user_config()
        
        # Daten
        self.groups = []
        self.unassigned_datasets = []
        
        # Plot-Einstellungen
        self.current_plot_type = 'Log-Log'
        self.stack_mode_var = None
        self.grid_var = None
        self.color_scheme = 'TUBAF'
        
        self.plot_settings = {
            'xlabel': 'q / nm⁻¹',
            'ylabel': 'Intensität / a.u.',
            'xscale': 'log',
            'yscale': 'log',
            'show_grid': True,
            'grid_which': 'both',
            'grid_alpha': 0.3,
            'legend_fontsize': 10,
            'axis_fontsize': 12,
            'legend_loc': 'best',
            'xlim_auto': True,
            'ylim_auto': True,
            'xlim': [None, None],
            'ylim': [None, None],
        }
        
        # Drag & Drop
        self.drag_data = None

        # DPI-Skalierung für Treeview-Zeilenhöhe
        self.setup_dpi_scaling()

        # GUI
        self.create_gui()
        self.create_menu()

        # Dark Mode anwenden
        self.apply_theme()

    def setup_dpi_scaling(self):
        """Setzt DPI-abhängige Zeilenhöhe für Treeview"""
        try:
            # DPI-Faktor berechnen (96 DPI = 1.0, 192 DPI = 2.0, etc.)
            dpi = self.root.winfo_fpixels('1i')
            dpi_scale = dpi / 96.0

            # Zeilenhöhe skalieren (Basis: 24px bei 96 DPI)
            rowheight = int(24 * dpi_scale)

            # ttk.Style für Treeview konfigurieren
            style = ttk.Style()
            style.configure("Treeview", rowheight=rowheight)

            print(f"DPI-Skalierung: {dpi:.0f} DPI, Faktor {dpi_scale:.2f}x, Zeilenhöhe {rowheight}px")
        except Exception as e:
            print(f"DPI-Skalierung fehlgeschlagen: {e}")
            # Fallback auf Standard-Höhe
            style = ttk.Style()
            style.configure("Treeview", rowheight=24)

    def apply_theme(self):
        """Wendet das aktuelle Theme (Light/Dark) an"""
        dark_mode = self.config.get_dark_mode()

        style = ttk.Style()

        # DPI-Skalierung für Zeilenhöhe (bei Theme-Wechsel beibehalten)
        try:
            dpi = self.root.winfo_fpixels('1i')
            dpi_scale = dpi / 96.0
            rowheight = int(24 * dpi_scale)
        except:
            rowheight = 24

        if dark_mode:
            # Dark Theme (nur GUI-Elemente, nicht Plots)
            bg_color = '#2b2b2b'
            fg_color = '#ffffff'
            select_bg = '#404040'
            select_fg = '#ffffff'
            field_bg = '#3c3c3c'

            # Root Window
            self.root.configure(bg=bg_color)

            # ttk Widgets
            style.theme_use('clam')
            style.configure('.', background=bg_color, foreground=fg_color,
                          fieldbackground=field_bg, bordercolor=bg_color)
            style.configure('TFrame', background=bg_color)
            style.configure('TLabel', background=bg_color, foreground=fg_color)
            style.configure('TLabelframe', background=bg_color, foreground=fg_color)
            style.configure('TLabelframe.Label', background=bg_color, foreground=fg_color)
            style.configure('TButton', background='#404040', foreground=fg_color)
            style.map('TButton', background=[('active', '#505050')])
            style.configure('TCheckbutton', background=bg_color, foreground=fg_color)
            style.configure('TCombobox', fieldbackground=field_bg, background=bg_color,
                          foreground=fg_color, selectbackground=select_bg, selectforeground=select_fg)
            style.configure('Treeview', background=field_bg, foreground=fg_color,
                          fieldbackground=field_bg, selectbackground=select_bg,
                          selectforeground=select_fg, rowheight=rowheight)
            style.configure('Treeview.Heading', background='#404040', foreground=fg_color)
            style.map('Treeview.Heading', background=[('active', '#505050')])
            style.configure('TPanedwindow', background=bg_color)

            # Menüs stylen (tk.Menu)
            self.root.option_add('*Menu.background', bg_color)
            self.root.option_add('*Menu.foreground', fg_color)
            self.root.option_add('*Menu.activeBackground', select_bg)
            self.root.option_add('*Menu.activeForeground', fg_color)
            self.root.option_add('*Menu.selectColor', fg_color)  # Für Checkbuttons

            # Matplotlib bleibt im Light Mode (für bessere Lesbarkeit der Plots)
            plt.style.use('default')
        else:
            # Light Theme (Standard)
            style.theme_use('clam')
            style.configure('Treeview', rowheight=rowheight)

            # Menüs zurücksetzen
            self.root.option_add('*Menu.background', 'SystemMenu')
            self.root.option_add('*Menu.foreground', 'SystemMenuText')
            self.root.option_add('*Menu.activeBackground', 'SystemHighlight')
            self.root.option_add('*Menu.activeForeground', 'SystemHighlightText')

            # Matplotlib im Standard
            plt.style.use('default')

        # Plot neu zeichnen
        if hasattr(self, 'fig') and hasattr(self, 'groups'):
            self.update_plot()

    def toggle_dark_mode(self):
        """Schaltet zwischen Light und Dark Mode um"""
        current_mode = self.config.get_dark_mode()
        new_mode = not current_mode
        self.config.set_dark_mode(new_mode)
        self.apply_theme()
        messagebox.showinfo("Dark Mode",
                           f"Dark Mode {'aktiviert' if new_mode else 'deaktiviert'}.\n"
                           "Die Änderung wird vollständig beim nächsten Start wirksam.")

    def create_menu(self):
        """Menü"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Datei
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Datei", menu=file_menu)
        file_menu.add_command(label="Daten laden...", command=self.load_data_to_unassigned)
        file_menu.add_separator()
        file_menu.add_command(label="Session speichern", command=self.save_session)
        file_menu.add_command(label="Session laden", command=self.load_session)
        file_menu.add_separator()
        file_menu.add_command(label="PNG Export...", command=self.export_png)
        file_menu.add_command(label="SVG Export...", command=self.export_svg)
        file_menu.add_separator()
        file_menu.add_command(label="Beenden", command=self.root.quit)
        
        # Plot
        plot_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Plot", menu=plot_menu)
        plot_menu.add_command(label="Aktualisieren", command=self.update_plot)
        plot_menu.add_command(label="Erweiterte Einstellungen...", command=self.show_plot_settings)
        
        # Design
        design_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Design", menu=design_menu)
        design_menu.add_command(label="Design-Manager...", command=self.show_design_manager)
        design_menu.add_separator()
        design_menu.add_command(label="🌙 Dark Mode umschalten", command=self.toggle_dark_mode)
        design_menu.add_separator()

        # Schnell-Stile
        for preset_name in self.config.style_presets.keys():
            design_menu.add_command(
                label=f"Stil '{preset_name}' anwenden",
                command=lambda p=preset_name: self.apply_style_to_selected(p)
            )
        
        # Hilfe
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Hilfe", menu=help_menu)
        help_menu.add_command(label="Über", command=self.show_about)
    
    def create_gui(self):
        """GUI erstellen"""
        # Main Paned Window
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Linke Seite
        left_frame = ttk.Frame(main_paned, width=450)
        main_paned.add(left_frame, weight=1)
        
        # Rechte Seite
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=3)
        
        # === Linke Seite ===
        
        # Buttons
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(btn_frame, text="➕ Gruppe", command=self.create_group).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="📁 Laden", command=self.load_data_to_unassigned).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🗑 Löschen", command=self.delete_selected).pack(side=tk.LEFT, padx=2)
        
        # Tree
        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree = ttk.Treeview(tree_frame, columns=("info",), yscrollcommand=tree_scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.config(command=self.tree.yview)
        
        self.tree.heading("#0", text="Name")
        self.tree.heading("info", text="Info")
        # DPI-Fix: Dynamische Spaltenbreiten für High-DPI Displays
        self.tree.column("#0", minwidth=200, width=300, stretch=True)
        self.tree.column("info", minwidth=80, width=100, stretch=False)
        
        # Tree Events
        self.tree.bind("<ButtonPress-1>", self.on_tree_press)
        self.tree.bind("<B1-Motion>", self.on_tree_motion)
        self.tree.bind("<ButtonRelease-1>", self.on_tree_release)
        self.tree.bind("<Double-Button-1>", self.on_tree_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)
        
        # Context Menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Umbenennen", command=self.rename_item)
        self.context_menu.add_command(label="Farbe ändern", command=self.change_color)
        self.context_menu.add_command(label="Stil ändern", command=self.change_style)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Löschen", command=self.delete_selected)
        
        # Unassigned Section erstellen
        self.unassigned_id = self.tree.insert("", 0, text="▼ Nicht zugeordnet", values=("",), tags=("unassigned_header",))
        
        # Optionen
        opt_frame = ttk.LabelFrame(left_frame, text="Optionen")
        opt_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Plot-Typ
        ttk.Label(opt_frame, text="Plot-Typ:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.plot_type_var = tk.StringVar(value='Log-Log')
        plot_combo = ttk.Combobox(opt_frame, textvariable=self.plot_type_var,
                                   values=list(PLOT_TYPES.keys()), state='readonly', width=15)
        plot_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        plot_combo.bind('<<ComboboxSelected>>', lambda e: self.change_plot_type())
        
        # Stack-Modus
        ttk.Label(opt_frame, text="Stack:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.stack_mode_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_frame, text="Aktiviert", variable=self.stack_mode_var,
                        command=self.update_plot).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Grid
        ttk.Label(opt_frame, text="Grid:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.grid_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_frame, text="Anzeigen", variable=self.grid_var,
                        command=self.update_plot).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Farbschema
        ttk.Label(opt_frame, text="Farbschema:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.color_scheme_var = tk.StringVar(value='TUBAF')
        schemes = list(self.config.color_schemes.keys())
        scheme_combo = ttk.Combobox(opt_frame, textvariable=self.color_scheme_var,
                                     values=schemes, state='readonly', width=15)
        scheme_combo.grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
        scheme_combo.bind('<<ComboboxSelected>>', lambda e: self.change_color_scheme())
        
        # Update Button
        ttk.Button(left_frame, text="🔄 Plot aktualisieren", command=self.update_plot).pack(fill=tk.X, padx=5, pady=5)
        
        # === Rechte Seite: Plot ===

        self.fig = Figure(figsize=(12, 9), dpi=100)
        self.ax_main = None
        self.ax_pddf = None

        # DPI-Fix: Toolbar in separatem Frame mit fester Höhe
        toolbar_frame = ttk.Frame(right_frame, height=50)
        toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)
        toolbar_frame.pack_propagate(False)  # Verhindert Größenänderung

        self.canvas = FigureCanvasTkAgg(self.fig, master=right_frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()
        
        self.setup_plot_axes()
        self.update_plot()
    
    def setup_plot_axes(self):
        """Richtet Plot-Achsen ein (mit/ohne PDDF Subplot)"""
        self.fig.clear()
        
        if self.current_plot_type == 'PDDF':
            # 2 Subplots: oben Scattering, unten PDDF
            gs = GridSpec(2, 1, height_ratios=[2, 1], hspace=0.3, figure=self.fig)
            self.ax_main = self.fig.add_subplot(gs[0])
            self.ax_pddf = self.fig.add_subplot(gs[1])
        else:
            # Ein Plot
            self.ax_main = self.fig.add_subplot(111)
            self.ax_pddf = None
    
    def change_plot_type(self):
        """Ändert Plot-Typ"""
        self.current_plot_type = self.plot_type_var.get()
        plot_info = PLOT_TYPES[self.current_plot_type]
        self.plot_settings['xlabel'] = plot_info['xlabel']
        self.plot_settings['ylabel'] = plot_info['ylabel']
        self.plot_settings['xscale'] = plot_info['xscale']
        self.plot_settings['yscale'] = plot_info['yscale']
        self.setup_plot_axes()
        self.update_plot()
    
    def change_color_scheme(self):
        """Ändert Farbschema"""
        self.color_scheme = self.color_scheme_var.get()
        self.update_plot()
    
    def apply_style_to_selected(self, preset_name):
        """Wendet Stil auf ausgewählte Datensätze an"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Bitte wählen Sie Datensätze aus")
            return
        
        for item in selected:
            parent = self.tree.parent(item)
            if parent and parent != self.unassigned_id:  # Datensatz in Gruppe
                item_text = self.tree.item(item, 'text')
                parent_name = self.tree.item(parent, 'text')
                group = next((g for g in self.groups if g.name == parent_name), None)
                if group:
                    ds = next((d for d in group.datasets if d.display_label == item_text), None)
                    if ds:
                        ds.apply_style_preset(preset_name)
            elif parent == self.unassigned_id:  # Unassigned
                item_text = self.tree.item(item, 'text')
                ds = next((d for d in self.unassigned_datasets if d.display_label == item_text), None)
                if ds:
                    ds.apply_style_preset(preset_name)
        
        self.update_plot()
    
    # ========================================================================
    # Drag & Drop
    # ========================================================================
    
    def on_tree_press(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.drag_data = {'item': item, 'start_y': event.y}
    
    def on_tree_motion(self, event):
        if self.drag_data and abs(event.y - self.drag_data['start_y']) > 5:
            self.tree.config(cursor="hand2")
    
    def on_tree_release(self, event):
        if self.drag_data:
            source_item = self.drag_data['item']
            target_item = self.tree.identify_row(event.y)
            
            if target_item and source_item != target_item:
                self.handle_drop(source_item, target_item)
            
            self.tree.config(cursor="")
            self.drag_data = None
    
    def handle_drop(self, source, target):
        """Verarbeitet Drag & Drop"""
        source_parent = self.tree.parent(source)
        target_parent = self.tree.parent(target)
        
        # Von Unassigned zu Gruppe
        if source_parent == self.unassigned_id and not target_parent:
            self.move_unassigned_to_group(source, target)
        # Von Gruppe zu Gruppe
        elif source_parent and target_parent and source_parent != self.unassigned_id:
            self.move_dataset_between_groups(source, target_parent if target_parent else target)
        # Von Gruppe zu Unassigned
        elif source_parent and source_parent != self.unassigned_id and target == self.unassigned_id:
            self.move_dataset_to_unassigned(source)
    
    def move_unassigned_to_group(self, source_item, target_group_item):
        """Verschiebt von Unassigned zu Gruppe"""
        dataset_name = self.tree.item(source_item, 'text')
        target_group_name = self.tree.item(target_group_item, 'text')
        
        dataset = next((d for d in self.unassigned_datasets if d.display_label == dataset_name), None)
        target_group = next((g for g in self.groups if g.name == target_group_name), None)
        
        if dataset and target_group:
            self.unassigned_datasets.remove(dataset)
            target_group.add_dataset(dataset)
            self.tree.delete(source_item)
            self.tree.insert(target_group_item, tk.END, text=dataset.display_label, values=("",), tags=("dataset",))
            self.update_plot()
    
    def move_dataset_between_groups(self, source_item, target_group_item):
        """Verschiebt zwischen Gruppen"""
        dataset_name = self.tree.item(source_item, 'text')
        source_group_name = self.tree.item(self.tree.parent(source_item), 'text')
        target_group_name = self.tree.item(target_group_item, 'text')
        
        if source_group_name == target_group_name:
            return
        
        source_group = next((g for g in self.groups if g.name == source_group_name), None)
        target_group = next((g for g in self.groups if g.name == target_group_name), None)
        
        if source_group and target_group:
            dataset = next((d for d in source_group.datasets if d.display_label == dataset_name), None)
            if dataset:
                source_group.remove_dataset(dataset)
                target_group.add_dataset(dataset)
                self.tree.delete(source_item)
                self.tree.insert(target_group_item, tk.END, text=dataset.display_label, values=("",), tags=("dataset",))
                self.update_plot()
    
    def move_dataset_to_unassigned(self, source_item):
        """Verschiebt zu Unassigned"""
        dataset_name = self.tree.item(source_item, 'text')
        source_group_name = self.tree.item(self.tree.parent(source_item), 'text')
        
        source_group = next((g for g in self.groups if g.name == source_group_name), None)
        if source_group:
            dataset = next((d for d in source_group.datasets if d.display_label == dataset_name), None)
            if dataset:
                source_group.remove_dataset(dataset)
                self.unassigned_datasets.append(dataset)
                self.tree.delete(source_item)
                self.tree.insert(self.unassigned_id, tk.END, text=dataset.display_label, values=("",), tags=("dataset",))
                self.update_plot()
    
    # ========================================================================
    # Tree Interaktion
    # ========================================================================
    
    def on_tree_double_click(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        
        item = selected[0]
        if item == self.unassigned_id:
            # Toggle Unassigned Section
            if self.tree.item(item, 'text').startswith('▼'):
                self.tree.item(item, text='▶ Nicht zugeordnet')
                for child in self.tree.get_children(item):
                    self.tree.detach(child)
            else:
                self.tree.item(item, text='▼ Nicht zugeordnet')
                for child in self.tree.get_children(item):
                    self.tree.reattach(child, item, 'end')
            return
        
        parent = self.tree.parent(item)
        if not parent or parent == self.unassigned_id:
            return
        
        if not self.tree.parent(self.tree.parent(item)):  # Gruppe
            self.edit_stack_factor(item)
        else:  # Datensatz
            self.rename_item()
    
    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item and item != self.unassigned_id:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
    
    def rename_item(self):
        selected = self.tree.selection()
        if not selected:
            return
        
        item = selected[0]
        old_name = self.tree.item(item, 'text')
        new_name = simpledialog.askstring("Umbenennen", "Neuer Name:", initialvalue=old_name)
        
        if not new_name:
            return
        
        parent = self.tree.parent(item)
        
        if not parent or parent == self.unassigned_id:
            return
        
        # Gruppe umbenennen
        if not self.tree.parent(parent):
            group = next((g for g in self.groups if g.name == old_name), None)
            if group:
                group.name = new_name
                self.tree.item(item, text=new_name)
        # Datensatz umbenennen
        else:
            parent_name = self.tree.item(parent, 'text')
            group = next((g for g in self.groups if g.name == parent_name), None)
            if group:
                ds = next((d for d in group.datasets if d.display_label == old_name), None)
                if ds:
                    ds.display_label = new_name
                    self.tree.item(item, text=new_name)
        
        self.update_plot()
    
    def change_color(self):
        """Ändert Farbe"""
        selected = self.tree.selection()
        if not selected:
            return
        
        item = selected[0]
        item_text = self.tree.item(item, 'text')
        parent = self.tree.parent(item)
        
        current_color = '#0069b4'
        
        # Gruppe
        if not parent or parent == self.unassigned_id:
            if parent != self.unassigned_id:
                group = next((g for g in self.groups if g.name == item_text), None)
                if group and group.color:
                    current_color = group.color
        # Datensatz
        else:
            parent_name = self.tree.item(parent, 'text')
            group = next((g for g in self.groups if g.name == parent_name), None)
            if group:
                ds = next((d for d in group.datasets if d.display_label == item_text), None)
                if ds and ds.color:
                    current_color = ds.color
        
        color = colorchooser.askcolor(color=current_color, title="Farbe wählen")
        if not color[1]:
            return
        
        new_color = color[1]
        
        # Setze Farbe
        if not parent or parent == self.unassigned_id:
            if parent != self.unassigned_id:
                group = next((g for g in self.groups if g.name == item_text), None)
                if group:
                    group.color = new_color
        else:
            parent_name = self.tree.item(parent, 'text')
            group = next((g for g in self.groups if g.name == parent_name), None)
            if group:
                ds = next((d for d in group.datasets if d.display_label == item_text), None)
                if ds:
                    ds.color = new_color
        
        self.update_plot()
    
    def change_style(self):
        """Ändert Stil"""
        selected = self.tree.selection()
        if not selected:
            return
        
        item = selected[0]
        parent = self.tree.parent(item)
        
        if not parent or parent == self.unassigned_id:
            if parent == self.unassigned_id:
                item_text = self.tree.item(item, 'text')
                ds = next((d for d in self.unassigned_datasets if d.display_label == item_text), None)
                if ds:
                    StyleDialog(self.root, ds, self.update_plot)
            return
        
        item_text = self.tree.item(item, 'text')
        parent_name = self.tree.item(parent, 'text')
        group = next((g for g in self.groups if g.name == parent_name), None)
        
        if group:
            ds = next((d for d in group.datasets if d.display_label == item_text), None)
            if ds:
                StyleDialog(self.root, ds, self.update_plot)
    
    def edit_stack_factor(self, item=None):
        if item is None:
            selected = self.tree.selection()
            if not selected:
                return
            item = selected[0]
        
        item_text = self.tree.item(item, 'text')
        group = next((g for g in self.groups if g.name == item_text), None)
        
        if group:
            new_factor = simpledialog.askfloat(
                "Stack-Faktor",
                f"Stack-Faktor für '{group.name}':",
                initialvalue=group.stack_factor
            )
            if new_factor is not None:
                group.stack_factor = new_factor
                self.tree.item(item, values=(f"×{new_factor}",))
                self.update_plot()
    
    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            return
        
        for item in selected:
            if item == self.unassigned_id:
                continue
            
            item_text = self.tree.item(item, 'text')
            parent = self.tree.parent(item)
            
            # Unassigned Dataset
            if parent == self.unassigned_id:
                ds = next((d for d in self.unassigned_datasets if d.display_label == item_text), None)
                if ds:
                    self.unassigned_datasets.remove(ds)
            # Gruppe
            elif not parent:
                group = next((g for g in self.groups if g.name == item_text), None)
                if group:
                    self.groups.remove(group)
            # Datensatz in Gruppe
            else:
                parent_name = self.tree.item(parent, 'text')
                group = next((g for g in self.groups if g.name == parent_name), None)
                if group:
                    ds = next((d for d in group.datasets if d.display_label == item_text), None)
                    if ds:
                        group.remove_dataset(ds)
            
            self.tree.delete(item)
        
        self.update_plot()
    
    # ========================================================================
    # Daten laden
    # ========================================================================
    
    def create_group(self):
        name = simpledialog.askstring("Neue Gruppe", "Gruppenname:")
        if not name:
            return
        
        stack_factor = simpledialog.askfloat("Stack-Faktor", "Stack-Faktor:", initialvalue=1.0)
        if stack_factor is None:
            stack_factor = 1.0
        
        group = DataGroup(name, stack_factor)
        self.groups.append(group)
        
        group_id = self.tree.insert("", tk.END, text=name, values=(f"×{stack_factor}",), tags=("group",))
        self.tree.item(group_id, open=True)
    
    def load_data_to_unassigned(self):
        """Lädt Dateien in Unassigned"""
        last_dir = self.config.get_last_directory()
        
        filepaths = filedialog.askopenfilenames(
            title="Datensätze auswählen",
            initialdir=last_dir,
            filetypes=[("Alle Dateien", "*.*"),
                       ("Text-Dateien", "*.txt"),
                       ("CSV-Dateien", "*.csv"),
                       ("DAT-Dateien", "*.dat")]
        )
        
        if not filepaths:
            return
        
        # Speichere Verzeichnis
        self.config.set_last_directory(str(Path(filepaths[0]).parent))
        
        for filepath in filepaths:
            try:
                dataset = DataSet(filepath, apply_auto_style=True)
                self.unassigned_datasets.append(dataset)
                self.tree.insert(self.unassigned_id, tk.END, text=dataset.display_label,
                               values=("",), tags=("dataset",))
            except Exception as e:
                messagebox.showerror("Fehler", f"Fehler bei {filepath}:\n{e}")
        
        # Unassigned aufklappen
        self.tree.item(self.unassigned_id, text='▼ Nicht zugeordnet')
    
    # ========================================================================
    # Plot
    # ========================================================================
    
    def transform_data(self, x, y, plot_type):
        """Transformiert Daten je nach Plot-Typ"""
        if plot_type == 'Porod':
            return x, y * (x ** 4)
        elif plot_type == 'Kratky':
            return x, y * (x ** 2)
        elif plot_type == 'Guinier':
            y_safe = np.where(y > 0, y, np.nan)
            return x ** 2, np.log(y_safe)
        else:
            return x, y
    
    def update_plot(self):
        """Aktualisiert Plot"""
        self.ax_main.clear()
        if self.ax_pddf:
            self.ax_pddf.clear()
        
        if not self.groups:
            self.ax_main.text(0.5, 0.5, "Keine Daten\n\nDateien laden und per Drag & Drop zuordnen",
                             ha='center', va='center', transform=self.ax_main.transAxes,
                             fontsize=14, color='gray')
            self.canvas.draw()
            return
        
        # Farben
        colors = self.config.color_schemes.get(self.color_scheme, self.config.color_schemes['TUBAF'])
        stack_mode = self.stack_mode_var.get()
        
        # Legende-Handles für Gruppen-Header
        legend_handles = []
        legend_labels = []
        
        for group_idx, group in enumerate(self.groups):
            if not group.datasets:
                continue
            
            group_color = group.color if group.color else colors[group_idx % len(colors)]
            stack_factor = group.stack_factor if stack_mode else 1.0
            
            # Gruppen-Header in Legende
            if group.show_group_in_legend and stack_mode:
                from matplotlib.lines import Line2D
                header_line = Line2D([0], [0], color='none', label=f'━━ {group.name} (×{stack_factor}) ━━')
                legend_handles.append(header_line)
                legend_labels.append(f'━━ {group.name} (×{stack_factor}) ━━')
            
            for dataset in group.datasets:
                if dataset.x is None or dataset.y is None:
                    continue
                
                # Transform
                x_plot, y_plot = self.transform_data(dataset.x, dataset.y, self.current_plot_type)
                y_plot = y_plot * stack_factor
                
                plot_color = dataset.color if dataset.color else group_color
                plot_style = dataset.get_plot_style()
                
                label = dataset.display_label if dataset.show_in_legend else None
                
                line, = self.ax_main.plot(x_plot, y_plot, plot_style,
                                         color=plot_color,
                                         linewidth=dataset.line_width,
                                         markersize=dataset.marker_size,
                                         label=label,
                                         alpha=0.8)
                
                if dataset.show_in_legend:
                    legend_handles.append(line)
                    legend_labels.append(dataset.display_label)
                
                # Fehler
                if dataset.y_err is not None:
                    _, y_err_plot = self.transform_data(dataset.x, dataset.y_err, self.current_plot_type)
                    y_err_plot = y_err_plot * stack_factor
                    self.ax_main.fill_between(x_plot,
                                              y_plot - y_err_plot,
                                              y_plot + y_err_plot,
                                              color=plot_color,
                                              alpha=0.2)
        
        # Achsen
        self.ax_main.set_xscale(self.plot_settings['xscale'])
        self.ax_main.set_yscale(self.plot_settings['yscale'])
        self.ax_main.set_xlabel(self.plot_settings['xlabel'], fontsize=self.plot_settings['axis_fontsize'])
        self.ax_main.set_ylabel(self.plot_settings['ylabel'], fontsize=self.plot_settings['axis_fontsize'])
        
        if self.grid_var.get():
            self.ax_main.grid(True, alpha=self.plot_settings['grid_alpha'], which=self.plot_settings['grid_which'])
        
        # Limits
        if not self.plot_settings['xlim_auto']:
            self.ax_main.set_xlim(self.plot_settings['xlim'])
        if not self.plot_settings['ylim_auto']:
            self.ax_main.set_ylim(self.plot_settings['ylim'])
        
        # Legende
        if legend_handles:
            self.ax_main.legend(handles=legend_handles, labels=legend_labels,
                               fontsize=self.plot_settings['legend_fontsize'],
                               loc=self.plot_settings['legend_loc'],
                               framealpha=0.9)
        
        # PDDF Subplot (Platzhalter)
        if self.ax_pddf:
            self.ax_pddf.set_xlabel('r / nm', fontsize=self.plot_settings['axis_fontsize'])
            self.ax_pddf.set_ylabel('p(r)', fontsize=self.plot_settings['axis_fontsize'])
            self.ax_pddf.text(0.5, 0.5, 'PDDF Darstellung\n(Implementierung erforderlich)',
                             ha='center', va='center', transform=self.ax_pddf.transAxes)
            if self.grid_var.get():
                self.ax_pddf.grid(True, alpha=self.plot_settings['grid_alpha'])
        
        self.fig.tight_layout()
        self.canvas.draw()
    
    # ========================================================================
    # Dialoge
    # ========================================================================
    
    def show_plot_settings(self):
        PlotSettingsDialog(self.root, self.plot_settings, self.update_plot)
    
    def show_design_manager(self):
        DesignManagerDialog(self.root, self.config, self.update_plot)
    
    def show_about(self):
        messagebox.showinfo("Über", 
            "TUBAF Scattering Plot Tool v3.0\n\n"
            "Features:\n"
            "• Verschiedene Plot-Typen\n"
            "• Stil-Vorlagen & Auto-Erkennung\n"
            "• Farbschema-Manager\n"
            "• Drag & Drop\n"
            "• Session-Verwaltung\n\n"
            "© 2024 TU Bergakademie Freiberg"
        )
    
    # ========================================================================
    # Session / Export
    # ========================================================================
    
    def save_session(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            title="Session speichern"
        )
        
        if not filepath:
            return
        
        try:
            session = {
                'groups': [g.to_dict() for g in self.groups],
                'unassigned': [d.to_dict() for d in self.unassigned_datasets],
                'plot_type': self.current_plot_type,
                'color_scheme': self.color_scheme,
                'plot_settings': self.plot_settings
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(session, f, indent=2)
            
            messagebox.showinfo("Erfolg", f"Session gespeichert:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler:\n{e}")
    
    def load_session(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON", "*.json")],
            title="Session laden"
        )
        
        if not filepath:
            return
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                session = json.load(f)
            
            # Clear
            self.groups.clear()
            self.unassigned_datasets.clear()
            for item in self.tree.get_children():
                if item != self.unassigned_id:
                    self.tree.delete(item)
            for item in self.tree.get_children(self.unassigned_id):
                self.tree.delete(item)
            
            # Load groups
            for g_data in session.get('groups', []):
                group = DataGroup.from_dict(g_data)
                self.groups.append(group)
                
                gid = self.tree.insert("", tk.END, text=group.name,
                                      values=(f"×{group.stack_factor}",), tags=("group",))
                self.tree.item(gid, open=True)
                
                for ds in group.datasets:
                    self.tree.insert(gid, tk.END, text=ds.display_label, values=("",), tags=("dataset",))
            
            # Load unassigned
            for d_data in session.get('unassigned', []):
                ds = DataSet.from_dict(d_data)
                self.unassigned_datasets.append(ds)
                self.tree.insert(self.unassigned_id, tk.END, text=ds.display_label, values=("",), tags=("dataset",))
            
            # Settings
            self.current_plot_type = session.get('plot_type', 'Log-Log')
            self.plot_type_var.set(self.current_plot_type)
            self.color_scheme = session.get('color_scheme', 'TUBAF')
            self.color_scheme_var.set(self.color_scheme)
            if 'plot_settings' in session:
                self.plot_settings.update(session['plot_settings'])
            
            self.setup_plot_axes()
            self.update_plot()
            messagebox.showinfo("Erfolg", "Session geladen")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler:\n{e}")
    
    def export_png(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png")],
            title="PNG Export"
        )
        
        if not filepath:
            return
        
        dpi = simpledialog.askinteger("DPI", "DPI:", initialvalue=self.config.get_export_dpi(),
                                      minvalue=72, maxvalue=1200)
        if not dpi:
            dpi = 300
        
        try:
            self.fig.savefig(filepath, dpi=dpi, bbox_inches='tight', facecolor='white')
            self.config.set_export_dpi(dpi)
            messagebox.showinfo("Erfolg", f"Exportiert:\n{filepath}\nDPI: {dpi}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler:\n{e}")
    
    def export_svg(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".svg",
            filetypes=[("SVG", "*.svg")],
            title="SVG Export"
        )
        
        if not filepath:
            return
        
        try:
            self.fig.savefig(filepath, format='svg', bbox_inches='tight')
            messagebox.showinfo("Erfolg", f"Exportiert:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler:\n{e}")


# ============================================================================
# Dialoge
# ============================================================================

class StyleDialog:
    """Stil-Dialog"""
    def __init__(self, parent, dataset, callback):
        self.dataset = dataset
        self.callback = callback
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Stil: {dataset.display_label}")
        self.dialog.geometry("400x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        ttk.Label(self.dialog, text="Linie:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        self.line_var = tk.StringVar(value=dataset.line_style or 'auto')
        ttk.Combobox(self.dialog, textvariable=self.line_var,
                     values=['auto', '-', '--', '-.', ':', ''], width=15).grid(row=0, column=1, padx=10, pady=5)
        
        ttk.Label(self.dialog, text="Marker:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        self.marker_var = tk.StringVar(value=dataset.marker_style or 'auto')
        ttk.Combobox(self.dialog, textvariable=self.marker_var,
                     values=['auto', 'o', 's', '^', 'v', 'D', '*', '+', 'x', ''], width=15).grid(row=1, column=1, padx=10, pady=5)
        
        ttk.Label(self.dialog, text="Linienbreite:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        self.lw_var = tk.DoubleVar(value=dataset.line_width)
        ttk.Spinbox(self.dialog, from_=0.5, to=10, increment=0.5,
                    textvariable=self.lw_var, width=15).grid(row=2, column=1, padx=10, pady=5)
        
        ttk.Label(self.dialog, text="Markergröße:").grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)
        self.ms_var = tk.DoubleVar(value=dataset.marker_size)
        ttk.Spinbox(self.dialog, from_=1, to=20, textvariable=self.ms_var, width=15).grid(row=3, column=1, padx=10, pady=5)
        
        ttk.Label(self.dialog, text="In Legende:").grid(row=4, column=0, sticky=tk.W, padx=10, pady=5)
        self.legend_var = tk.BooleanVar(value=dataset.show_in_legend)
        ttk.Checkbutton(self.dialog, text="Anzeigen", variable=self.legend_var).grid(row=4, column=1, sticky=tk.W, padx=10, pady=5)
        
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=20)
        ttk.Button(btn_frame, text="OK", command=self.apply).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Abbrechen", command=self.dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def apply(self):
        self.dataset.line_style = None if self.line_var.get() == 'auto' else self.line_var.get()
        self.dataset.marker_style = None if self.marker_var.get() == 'auto' else self.marker_var.get()
        self.dataset.line_width = self.lw_var.get()
        self.dataset.marker_size = self.ms_var.get()
        self.dataset.show_in_legend = self.legend_var.get()
        self.callback()
        self.dialog.destroy()


class PlotSettingsDialog:
    """Plot-Einstellungen"""
    def __init__(self, parent, settings, callback):
        self.settings = settings
        self.callback = callback
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Plot-Einstellungen")
        self.dialog.geometry("550x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        row = 0
        
        # X-Label
        ttk.Label(self.dialog, text="X-Label:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        self.xlabel_var = tk.StringVar(value=settings['xlabel'])
        ttk.Entry(self.dialog, textvariable=self.xlabel_var, width=30).grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1
        
        # Y-Label
        ttk.Label(self.dialog, text="Y-Label:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        self.ylabel_var = tk.StringVar(value=settings['ylabel'])
        ttk.Entry(self.dialog, textvariable=self.ylabel_var, width=30).grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1
        
        # X-Limits
        ttk.Label(self.dialog, text="X-Limits:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        self.xlim_auto_var = tk.BooleanVar(value=settings['xlim_auto'])
        ttk.Checkbutton(self.dialog, text="Auto", variable=self.xlim_auto_var).grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1
        
        xlim_frame = ttk.Frame(self.dialog)
        xlim_frame.grid(row=row, column=0, columnspan=2, padx=10, pady=5)
        ttk.Label(xlim_frame, text="Min:").pack(side=tk.LEFT, padx=5)
        self.xlim_min_var = tk.StringVar(value=str(settings['xlim'][0] or ''))
        ttk.Entry(xlim_frame, textvariable=self.xlim_min_var, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(xlim_frame, text="Max:").pack(side=tk.LEFT, padx=5)
        self.xlim_max_var = tk.StringVar(value=str(settings['xlim'][1] or ''))
        ttk.Entry(xlim_frame, textvariable=self.xlim_max_var, width=10).pack(side=tk.LEFT, padx=5)
        row += 1
        
        # Y-Limits
        ttk.Label(self.dialog, text="Y-Limits:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        self.ylim_auto_var = tk.BooleanVar(value=settings['ylim_auto'])
        ttk.Checkbutton(self.dialog, text="Auto", variable=self.ylim_auto_var).grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1
        
        ylim_frame = ttk.Frame(self.dialog)
        ylim_frame.grid(row=row, column=0, columnspan=2, padx=10, pady=5)
        ttk.Label(ylim_frame, text="Min:").pack(side=tk.LEFT, padx=5)
        self.ylim_min_var = tk.StringVar(value=str(settings['ylim'][0] or ''))
        ttk.Entry(ylim_frame, textvariable=self.ylim_min_var, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(ylim_frame, text="Max:").pack(side=tk.LEFT, padx=5)
        self.ylim_max_var = tk.StringVar(value=str(settings['ylim'][1] or ''))
        ttk.Entry(ylim_frame, textvariable=self.ylim_max_var, width=10).pack(side=tk.LEFT, padx=5)
        row += 1
        
        # Grid
        ttk.Label(self.dialog, text="Grid:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        self.grid_which_var = tk.StringVar(value=settings['grid_which'])
        ttk.Combobox(self.dialog, textvariable=self.grid_which_var,
                     values=['both', 'major', 'minor'], width=27).grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1
        
        # Legende Position
        ttk.Label(self.dialog, text="Legende:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        self.legend_loc_var = tk.StringVar(value=settings['legend_loc'])
        ttk.Combobox(self.dialog, textvariable=self.legend_loc_var,
                     values=['best', 'upper right', 'upper left', 'lower right', 'lower left', 'center'], 
                     width=27).grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1
        
        # Schriftgrößen
        ttk.Label(self.dialog, text="Legende-Schrift:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        self.legend_fs_var = tk.IntVar(value=settings['legend_fontsize'])
        ttk.Spinbox(self.dialog, from_=6, to=20, textvariable=self.legend_fs_var, width=27).grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1
        
        ttk.Label(self.dialog, text="Achsen-Schrift:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        self.axis_fs_var = tk.IntVar(value=settings['axis_fontsize'])
        ttk.Spinbox(self.dialog, from_=6, to=20, textvariable=self.axis_fs_var, width=27).grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1
        
        # Buttons
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=20)
        ttk.Button(btn_frame, text="OK", command=self.apply).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Abbrechen", command=self.dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def apply(self):
        self.settings['xlabel'] = self.xlabel_var.get()
        self.settings['ylabel'] = self.ylabel_var.get()
        
        self.settings['xlim_auto'] = self.xlim_auto_var.get()
        try:
            xmin = float(self.xlim_min_var.get()) if self.xlim_min_var.get() else None
            xmax = float(self.xlim_max_var.get()) if self.xlim_max_var.get() else None
            self.settings['xlim'] = [xmin, xmax]
        except:
            pass
        
        self.settings['ylim_auto'] = self.ylim_auto_var.get()
        try:
            ymin = float(self.ylim_min_var.get()) if self.ylim_min_var.get() else None
            ymax = float(self.ylim_max_var.get()) if self.ylim_max_var.get() else None
            self.settings['ylim'] = [ymin, ymax]
        except:
            pass
        
        self.settings['grid_which'] = self.grid_which_var.get()
        self.settings['legend_loc'] = self.legend_loc_var.get()
        self.settings['legend_fontsize'] = self.legend_fs_var.get()
        self.settings['axis_fontsize'] = self.axis_fs_var.get()
        
        self.callback()
        self.dialog.destroy()


class DesignManagerDialog:
    """Design-Manager mit Tabs"""
    def __init__(self, parent, config, callback):
        self.config = config
        self.callback = callback
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Design-Manager")
        self.dialog.geometry("700x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tabs
        self.create_styles_tab(notebook)
        self.create_colors_tab(notebook)
        self.create_autodetect_tab(notebook)
        
        # Buttons
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text="Schließen", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def create_styles_tab(self, notebook):
        """Stil-Vorlagen Tab"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="Stil-Vorlagen")
        
        ttk.Label(tab, text="Verfügbare Stile:").pack(anchor=tk.W, padx=10, pady=5)
        
        # Listbox
        list_frame = ttk.Frame(tab)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        scroll = ttk.Scrollbar(list_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.styles_listbox = tk.Listbox(list_frame, yscrollcommand=scroll.set)
        self.styles_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=self.styles_listbox.yview)
        
        self.refresh_styles_list()
        
        # Buttons
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(btn_frame, text="Neuer Stil...", command=self.create_new_style).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Bearbeiten...", command=self.edit_style).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Löschen", command=self.delete_style).pack(side=tk.LEFT, padx=2)
    
    def create_colors_tab(self, notebook):
        """Farbschemata Tab"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="Farbschemata")
        
        ttk.Label(tab, text="Verfügbare Schemata:").pack(anchor=tk.W, padx=10, pady=5)
        
        # Listbox
        list_frame = ttk.Frame(tab)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        scroll = ttk.Scrollbar(list_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.colors_listbox = tk.Listbox(list_frame, yscrollcommand=scroll.set)
        self.colors_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=self.colors_listbox.yview)
        
        self.refresh_colors_list()
        
        # Buttons
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(btn_frame, text="Neues Schema...", command=self.create_new_scheme).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Bearbeiten...", command=self.edit_scheme).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Löschen", command=self.delete_scheme).pack(side=tk.LEFT, padx=2)
    
    def create_autodetect_tab(self, notebook):
        """Auto-Erkennung Tab"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="Auto-Erkennung")
        
        ttk.Label(tab, text="Keyword → Stil Zuordnung:").pack(anchor=tk.W, padx=10, pady=5)
        
        # Listbox
        list_frame = ttk.Frame(tab)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        scroll = ttk.Scrollbar(list_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.autodetect_listbox = tk.Listbox(list_frame, yscrollcommand=scroll.set)
        self.autodetect_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=self.autodetect_listbox.yview)
        
        self.refresh_autodetect_list()
        
        # Aktivieren
        self.autodetect_enabled_var = tk.BooleanVar(value=self.config.auto_detection_enabled)
        ttk.Checkbutton(tab, text="Auto-Erkennung aktiviert",
                        variable=self.autodetect_enabled_var,
                        command=self.toggle_autodetect).pack(anchor=tk.W, padx=10, pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(btn_frame, text="Neue Regel...", command=self.create_autodetect_rule).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Löschen", command=self.delete_autodetect_rule).pack(side=tk.LEFT, padx=2)
    
    def refresh_styles_list(self):
        self.styles_listbox.delete(0, tk.END)
        for name, style in self.config.style_presets.items():
            desc = style.get('description', '')
            self.styles_listbox.insert(tk.END, f"{name}: {desc}")
    
    def refresh_colors_list(self):
        self.colors_listbox.delete(0, tk.END)
        for name in sorted(self.config.color_schemes.keys()):
            self.colors_listbox.insert(tk.END, name)
    
    def refresh_autodetect_list(self):
        self.autodetect_listbox.delete(0, tk.END)
        for keyword, style in self.config.auto_detection_rules.items():
            self.autodetect_listbox.insert(tk.END, f"{keyword} → {style}")
    
    def create_new_style(self):
        name = simpledialog.askstring("Neuer Stil", "Stil-Name:")
        if not name:
            return
        
        # Einfacher Dialog - könnte erweitert werden
        style = {
            'line_style': '-',
            'marker_style': '',
            'line_width': 2,
            'marker_size': 4,
            'description': 'Benutzerdefiniert'
        }
        
        self.config.add_style_preset(name, style)
        self.refresh_styles_list()
        self.callback()
    
    def delete_style(self):
        sel = self.styles_listbox.curselection()
        if not sel:
            return
        
        name = self.styles_listbox.get(sel[0]).split(':')[0]
        if messagebox.askyesno("Löschen", f"Stil '{name}' löschen?"):
            self.config.delete_style_preset(name)
            self.refresh_styles_list()
            self.callback()
    
    def create_new_scheme(self):
        name = simpledialog.askstring("Neues Schema", "Schema-Name:")
        if not name:
            return
        
        # Vereinfacht: 5 Farben abfragen
        colors = []
        for i in range(5):
            color = colorchooser.askcolor(title=f"Farbe {i+1}")
            if color[1]:
                colors.append(color[1])
            else:
                break
        
        if colors:
            self.config.save_color_scheme(name, colors)
            self.refresh_colors_list()
            self.callback()
    
    def delete_scheme(self):
        sel = self.colors_listbox.curselection()
        if not sel:
            return
        
        name = self.colors_listbox.get(sel[0])
        if self.config.delete_color_scheme(name):
            self.refresh_colors_list()
            self.callback()
        else:
            messagebox.showinfo("Info", "Standard-Schemata können nicht gelöscht werden")
    
    def create_autodetect_rule(self):
        keyword = simpledialog.askstring("Neues Keyword", "Keyword (z.B. 'fit'):")
        if not keyword:
            return
        
        styles = list(self.config.style_presets.keys())
        style = simpledialog.askstring("Stil", f"Stil-Name (verfügbar: {', '.join(styles)}):")
        if not style or style not in styles:
            return
        
        self.config.auto_detection_rules[keyword.lower()] = style
        self.config.save_config()
        self.refresh_autodetect_list()
    
    def delete_autodetect_rule(self):
        sel = self.autodetect_listbox.curselection()
        if not sel:
            return
        
        text = self.autodetect_listbox.get(sel[0])
        keyword = text.split(' → ')[0]
        
        if keyword in self.config.auto_detection_rules:
            del self.config.auto_detection_rules[keyword]
            self.config.save_config()
            self.refresh_autodetect_list()
    
    def toggle_autodetect(self):
        self.config.auto_detection_enabled = self.autodetect_enabled_var.get()
        self.config.save_config()

    def edit_style(self):
        """Bearbeitet einen Stil"""
        sel = self.styles_listbox.curselection()
        if not sel:
            messagebox.showinfo("Info", "Bitte wählen Sie einen Stil aus")
            return

        name = self.styles_listbox.get(sel[0]).split(':')[0]
        if name in self.config.style_presets:
            StylePresetEditDialog(self.dialog, name, self.config, self.refresh_styles_list, self.callback)

    def edit_scheme(self):
        """Bearbeitet ein Farbschema"""
        sel = self.colors_listbox.curselection()
        if not sel:
            messagebox.showinfo("Info", "Bitte wählen Sie ein Schema aus")
            return

        name = self.colors_listbox.get(sel[0])

        # Nur User-Schemata und TUBAF bearbeitbar
        from user_config import get_matplotlib_colormaps
        matplotlib_maps = list(get_matplotlib_colormaps().keys())

        if name in matplotlib_maps:
            messagebox.showinfo("Info",
                "Matplotlib-Schemata können nicht bearbeitet werden.\n"
                "Sie können aber ein neues Schema erstellen und dieses als Vorlage verwenden.")
            return

        if name in self.config.color_schemes:
            ColorSchemeEditDialog(self.dialog, name, self.config, self.refresh_colors_list, self.callback)


class StylePresetEditDialog:
    """Dialog zum Bearbeiten von Stil-Vorlagen"""
    def __init__(self, parent, style_name, config, refresh_callback, plot_callback):
        self.style_name = style_name
        self.config = config
        self.refresh_callback = refresh_callback
        self.plot_callback = plot_callback
        self.style = config.style_presets[style_name].copy()

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Stil bearbeiten: {style_name}")
        self.dialog.geometry("450x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        row = 0

        # Name
        ttk.Label(self.dialog, text="Name:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        self.name_var = tk.StringVar(value=style_name)
        ttk.Entry(self.dialog, textvariable=self.name_var, width=30).grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1

        # Description
        ttk.Label(self.dialog, text="Beschreibung:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        self.desc_var = tk.StringVar(value=self.style.get('description', ''))
        ttk.Entry(self.dialog, textvariable=self.desc_var, width=30).grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1

        # Linientyp
        ttk.Label(self.dialog, text="Linientyp:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        self.line_var = tk.StringVar(value=self.style.get('line_style', ''))
        ttk.Combobox(self.dialog, textvariable=self.line_var,
                     values=['', '-', '--', '-.', ':'], width=27).grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1

        # Marker
        ttk.Label(self.dialog, text="Marker:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        self.marker_var = tk.StringVar(value=self.style.get('marker_style', ''))
        ttk.Combobox(self.dialog, textvariable=self.marker_var,
                     values=['', 'o', 's', '^', 'v', 'D', '*', '+', 'x', 'p', 'h'], width=27).grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1

        # Linienbreite
        ttk.Label(self.dialog, text="Linienbreite:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        self.lw_var = tk.DoubleVar(value=self.style.get('line_width', 2))
        ttk.Spinbox(self.dialog, from_=0.5, to=10, increment=0.5,
                    textvariable=self.lw_var, width=27).grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1

        # Markergröße
        ttk.Label(self.dialog, text="Markergröße:").grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        self.ms_var = tk.DoubleVar(value=self.style.get('marker_size', 4))
        ttk.Spinbox(self.dialog, from_=1, to=20, increment=1,
                    textvariable=self.ms_var, width=27).grid(row=row, column=1, sticky=tk.W, padx=10, pady=5)
        row += 1

        # Buttons
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=20)
        ttk.Button(btn_frame, text="Speichern", command=self.save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Abbrechen", command=self.dialog.destroy).pack(side=tk.LEFT, padx=5)

    def save(self):
        """Speichert den bearbeiteten Stil"""
        new_name = self.name_var.get()
        if not new_name:
            messagebox.showerror("Fehler", "Name darf nicht leer sein")
            return

        # Stil aktualisieren
        new_style = {
            'line_style': self.line_var.get() or '',
            'marker_style': self.marker_var.get() or '',
            'line_width': self.lw_var.get(),
            'marker_size': self.ms_var.get(),
            'description': self.desc_var.get()
        }

        # Wenn Name geändert, alten löschen
        if new_name != self.style_name and self.style_name in self.config.style_presets:
            del self.config.style_presets[self.style_name]

        self.config.style_presets[new_name] = new_style
        self.config.save_style_presets()

        self.refresh_callback()
        self.plot_callback()
        self.dialog.destroy()


class ColorSchemeEditDialog:
    """Dialog zum Bearbeiten von Farbschemata"""
    def __init__(self, parent, scheme_name, config, refresh_callback, plot_callback):
        self.scheme_name = scheme_name
        self.config = config
        self.refresh_callback = refresh_callback
        self.plot_callback = plot_callback
        self.colors = config.color_schemes[scheme_name].copy()

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Farbschema bearbeiten: {scheme_name}")
        self.dialog.geometry("500x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Name
        name_frame = ttk.Frame(self.dialog)
        name_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(name_frame, text="Name:").pack(side=tk.LEFT, padx=5)
        self.name_var = tk.StringVar(value=scheme_name)
        ttk.Entry(name_frame, textvariable=self.name_var, width=30).pack(side=tk.LEFT, padx=5)

        # Farbliste mit Farbvorschau
        ttk.Label(self.dialog, text="Farben:").pack(anchor=tk.W, padx=10, pady=5)

        # Canvas mit Scrollbar für Farbliste
        list_frame = ttk.Frame(self.dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas = tk.Canvas(list_frame, yscrollcommand=scroll.set, height=300, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=self.canvas.yview)

        # Scrollbarer Frame im Canvas
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor='nw')

        # Canvas-Größe an Frame anpassen
        self.scrollable_frame.bind('<Configure>',
                                   lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', self._on_canvas_configure)

        # Ausgewählter Index
        self.selected_index = None
        self.color_labels = []

        self.refresh_color_list()

        # Buttons für Farben
        color_btn_frame = ttk.Frame(self.dialog)
        color_btn_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(color_btn_frame, text="➕ Hinzufügen", command=self.add_color).pack(side=tk.LEFT, padx=2)
        ttk.Button(color_btn_frame, text="✏️ Ändern", command=self.edit_color).pack(side=tk.LEFT, padx=2)
        ttk.Button(color_btn_frame, text="↑ Hoch", command=self.move_up).pack(side=tk.LEFT, padx=2)
        ttk.Button(color_btn_frame, text="↓ Runter", command=self.move_down).pack(side=tk.LEFT, padx=2)
        ttk.Button(color_btn_frame, text="× Entfernen", command=self.remove_color).pack(side=tk.LEFT, padx=2)

        # Speichern/Abbrechen
        main_btn_frame = ttk.Frame(self.dialog)
        main_btn_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(main_btn_frame, text="Speichern", command=self.save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(main_btn_frame, text="Abbrechen", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def _on_canvas_configure(self, event):
        """Passt die Canvas-Breite an"""
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)

    def _select_color(self, index):
        """Wählt eine Farbe aus und hebt sie hervor"""
        # Entferne alte Auswahl
        for i, label in enumerate(self.color_labels):
            if i == index:
                label.configure(relief=tk.RAISED, borderwidth=2)
            else:
                label.configure(relief=tk.FLAT, borderwidth=1)
        self.selected_index = index

    def refresh_color_list(self):
        """Aktualisiert die Farbliste mit Farbvorschau"""
        # Alte Labels löschen
        for label in self.color_labels:
            label.destroy()
        self.color_labels.clear()
        self.selected_index = None

        # Neue Labels erstellen
        for i, color in enumerate(self.colors):
            # Frame für jede Farbe
            row_frame = tk.Frame(self.scrollable_frame, relief=tk.FLAT, borderwidth=1,
                                bg='white', cursor='hand2')
            row_frame.pack(fill=tk.X, pady=2, padx=2)

            # Farb-Vorschau (20x20 px)
            color_preview = tk.Label(row_frame, bg=color, width=2, height=1, relief=tk.SOLID,
                                    borderwidth=1)
            color_preview.pack(side=tk.LEFT, padx=5, pady=2)

            # Text mit Index und Hex-Code
            color_text = tk.Label(row_frame, text=f"{i+1}. {color}", bg='white', anchor='w')
            color_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

            # Click-Binding für Auswahl
            def make_click_handler(idx):
                return lambda e: self._select_color(idx)

            row_frame.bind('<Button-1>', make_click_handler(i))
            color_preview.bind('<Button-1>', make_click_handler(i))
            color_text.bind('<Button-1>', make_click_handler(i))

            self.color_labels.append(row_frame)

    def add_color(self):
        """Fügt eine neue Farbe hinzu"""
        color = colorchooser.askcolor(title="Farbe wählen")
        if color[1]:
            self.colors.append(color[1])
            self.refresh_color_list()

    def edit_color(self):
        """Ändert die ausgewählte Farbe"""
        if self.selected_index is None:
            messagebox.showinfo("Info", "Bitte wählen Sie eine Farbe aus")
            return

        idx = self.selected_index
        old_color = self.colors[idx]

        color = colorchooser.askcolor(color=old_color, title="Farbe ändern")
        if color[1]:
            self.colors[idx] = color[1]
            self.refresh_color_list()
            self._select_color(idx)

    def move_up(self):
        """Verschiebt Farbe nach oben"""
        if self.selected_index is None or self.selected_index == 0:
            return

        idx = self.selected_index
        self.colors[idx], self.colors[idx-1] = self.colors[idx-1], self.colors[idx]
        self.refresh_color_list()
        self._select_color(idx-1)

    def move_down(self):
        """Verschiebt Farbe nach unten"""
        if self.selected_index is None or self.selected_index == len(self.colors) - 1:
            return

        idx = self.selected_index
        self.colors[idx], self.colors[idx+1] = self.colors[idx+1], self.colors[idx]
        self.refresh_color_list()
        self._select_color(idx+1)

    def remove_color(self):
        """Entfernt die ausgewählte Farbe"""
        if self.selected_index is None:
            return

        if len(self.colors) <= 2:
            messagebox.showwarning("Warnung", "Mindestens 2 Farben erforderlich")
            return

        idx = self.selected_index
        del self.colors[idx]
        self.refresh_color_list()

    def save(self):
        """Speichert das Farbschema"""
        new_name = self.name_var.get()
        if not new_name:
            messagebox.showerror("Fehler", "Name darf nicht leer sein")
            return

        if len(self.colors) < 2:
            messagebox.showerror("Fehler", "Mindestens 2 Farben erforderlich")
            return

        # Speichern
        self.config.save_color_scheme(new_name, self.colors)

        # Wenn Name geändert und nicht TUBAF, altes löschen
        if new_name != self.scheme_name and self.scheme_name != 'TUBAF':
            # Prüfe ob es ein User-Schema ist
            from user_config import get_matplotlib_colormaps
            if self.scheme_name not in get_matplotlib_colormaps():
                self.config.delete_color_scheme(self.scheme_name)

        self.refresh_callback()
        self.plot_callback()
        messagebox.showinfo("Erfolg", f"Farbschema '{new_name}' gespeichert")
        self.dialog.destroy()


# ============================================================================
# Main
# ============================================================================

def main():
    enable_dpi_awareness()
    
    root = tk.Tk()
    
    if platform.system() == 'Linux':
        try:
            dpi = root.winfo_fpixels('1i')
            if dpi > 96:
                root.tk.call('tk', 'scaling', dpi / 96)
        except:
            pass
    
    app = ScatterPlotApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
