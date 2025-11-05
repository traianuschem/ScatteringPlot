#!/usr/bin/env python3
"""
Scattering Plot Tool für TUBAF
Grafische Oberfläche zur Darstellung von Streukurven mit Gruppierung und gestackter Ansicht
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import numpy as np
from pathlib import Path
import json

from data_loader import load_scattering_data
from config import TUBAF_COLORS


class DataSet:
    """Repräsentiert einen einzelnen Datensatz"""
    def __init__(self, filepath, name=None):
        self.filepath = Path(filepath)
        self.name = name or self.filepath.stem
        self.data = None
        self.x = None
        self.y = None
        self.y_err = None
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


class DataGroup:
    """Repräsentiert eine Gruppe von Datensätzen"""
    def __init__(self, name, stack_factor=1.0):
        self.name = name
        self.datasets = []
        self.stack_factor = stack_factor
        self.color = None

    def add_dataset(self, dataset):
        """Fügt einen Datensatz zur Gruppe hinzu"""
        self.datasets.append(dataset)

    def remove_dataset(self, dataset):
        """Entfernt einen Datensatz aus der Gruppe"""
        if dataset in self.datasets:
            self.datasets.remove(dataset)


class ScatterPlotApp:
    """Hauptanwendung für Scattering Plot Tool"""

    def __init__(self, root):
        self.root = root
        self.root.title("TUBAF Scattering Plot Tool")
        self.root.geometry("1400x900")

        # Datenverwaltung
        self.groups = []
        self.current_stack_offset = 0

        # GUI erstellen
        self.create_gui()

    def create_gui(self):
        """Erstellt die grafische Benutzeroberfläche"""

        # Hauptcontainer mit Paned Window für flexible Größenanpassung
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Linke Seite: Datenverwaltung
        left_frame = ttk.Frame(main_paned, width=400)
        main_paned.add(left_frame, weight=1)

        # Rechte Seite: Plot
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=3)

        # === Linke Seite: Kontrollen ===

        # Buttons für Datenverwaltung
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(button_frame, text="Neue Gruppe",
                   command=self.create_group).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Daten laden",
                   command=self.load_data).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Löschen",
                   command=self.delete_selected).pack(side=tk.LEFT, padx=2)

        # Treeview für Gruppen und Datensätze
        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Scrollbars
        tree_scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(tree_frame,
                                  columns=("stack_factor",),
                                  yscrollcommand=tree_scroll_y.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll_y.config(command=self.tree.yview)

        self.tree.heading("#0", text="Name")
        self.tree.heading("stack_factor", text="Stack-Faktor")
        self.tree.column("stack_factor", width=100)

        # Doppelklick zum Bearbeiten des Stack-Faktors
        self.tree.bind("<Double-Button-1>", self.edit_stack_factor)

        # Plot-Optionen
        options_frame = ttk.LabelFrame(left_frame, text="Plot-Optionen")
        options_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(options_frame, text="Stack-Modus:").grid(row=0, column=0,
                                                            sticky=tk.W, padx=5, pady=2)
        self.stack_mode_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Aktiviert",
                        variable=self.stack_mode_var).grid(row=0, column=1,
                                                           sticky=tk.W, padx=5, pady=2)

        ttk.Label(options_frame, text="X-Label:").grid(row=1, column=0,
                                                        sticky=tk.W, padx=5, pady=2)
        self.xlabel_var = tk.StringVar(value="q / nm⁻¹")
        ttk.Entry(options_frame, textvariable=self.xlabel_var).grid(row=1, column=1,
                                                                     sticky=tk.EW, padx=5, pady=2)

        ttk.Label(options_frame, text="Y-Label:").grid(row=2, column=0,
                                                        sticky=tk.W, padx=5, pady=2)
        self.ylabel_var = tk.StringVar(value="Intensität / a.u.")
        ttk.Entry(options_frame, textvariable=self.ylabel_var).grid(row=2, column=1,
                                                                     sticky=tk.EW, padx=5, pady=2)

        options_frame.columnconfigure(1, weight=1)

        # Plot-Button
        plot_button_frame = ttk.Frame(left_frame)
        plot_button_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(plot_button_frame, text="Plot aktualisieren",
                   command=self.update_plot).pack(fill=tk.X)

        # === Rechte Seite: Matplotlib Plot ===

        self.fig = Figure(figsize=(10, 8), dpi=100)
        self.ax = self.fig.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(self.fig, master=right_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Matplotlib Toolbar
        toolbar = NavigationToolbar2Tk(self.canvas, right_frame)
        toolbar.update()

        # Initial-Plot
        self.update_plot()

    def create_group(self):
        """Erstellt eine neue Gruppe"""
        name = simpledialog.askstring("Neue Gruppe", "Gruppenname:")
        if name:
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

            messagebox.showinfo("Erfolg", f"Gruppe '{name}' erstellt")

    def load_data(self):
        """Lädt Datensätze und fügt sie einer Gruppe hinzu"""
        # Prüfen, ob Gruppen vorhanden sind
        if not self.groups:
            messagebox.showwarning("Keine Gruppe",
                                   "Bitte erstellen Sie zuerst eine Gruppe!")
            return

        # Gruppe auswählen
        group_names = [g.name for g in self.groups]
        group_name = simpledialog.askstring("Gruppe wählen",
                                            f"Gruppenname (verfügbar: {', '.join(group_names)}):")

        group = next((g for g in self.groups if g.name == group_name), None)
        if not group:
            messagebox.showerror("Fehler", f"Gruppe '{group_name}' nicht gefunden")
            return

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

        # Dateien laden und zur Gruppe hinzufügen
        for filepath in filepaths:
            try:
                dataset = DataSet(filepath)
                group.add_dataset(dataset)

                # In Treeview einfügen
                # Finde die Gruppe im Tree
                for item in self.tree.get_children():
                    if self.tree.item(item, "text") == group.name:
                        self.tree.insert(item, tk.END, text=dataset.name,
                                        values=("",), tags=("dataset",))
                        break

            except Exception as e:
                messagebox.showerror("Fehler", f"Fehler beim Laden von {filepath}:\n{e}")

        messagebox.showinfo("Erfolg", f"{len(filepaths)} Datensatz/-sätze geladen")

    def delete_selected(self):
        """Löscht ausgewählte Gruppe oder Datensatz"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie ein Element aus")
            return

        for item in selected:
            item_text = self.tree.item(item, "text")
            parent = self.tree.parent(item)

            if not parent:  # Es ist eine Gruppe
                # Gruppe aus Liste entfernen
                group = next((g for g in self.groups if g.name == item_text), None)
                if group:
                    self.groups.remove(group)
            else:  # Es ist ein Datensatz
                parent_text = self.tree.item(parent, "text")
                group = next((g for g in self.groups if g.name == parent_text), None)
                if group:
                    dataset = next((d for d in group.datasets if d.name == item_text), None)
                    if dataset:
                        group.remove_dataset(dataset)

            self.tree.delete(item)

    def edit_stack_factor(self, event):
        """Bearbeitet den Stack-Faktor einer Gruppe per Doppelklick"""
        selected = self.tree.selection()
        if not selected:
            return

        item = selected[0]
        parent = self.tree.parent(item)

        # Nur für Gruppen (keine Parent)
        if not parent:
            item_text = self.tree.item(item, "text")
            group = next((g for g in self.groups if g.name == item_text), None)

            if group:
                new_factor = simpledialog.askfloat("Stack-Faktor bearbeiten",
                                                    f"Neuer Stack-Faktor für '{group.name}':",
                                                    initialvalue=group.stack_factor)
                if new_factor is not None:
                    group.stack_factor = new_factor
                    self.tree.item(item, values=(f"×{new_factor}",))

    def update_plot(self):
        """Aktualisiert den Plot mit allen Gruppen und Datensätzen"""
        self.ax.clear()

        if not self.groups:
            self.ax.text(0.5, 0.5, "Keine Daten geladen",
                        ha='center', va='center', transform=self.ax.transAxes)
            self.canvas.draw()
            return

        # Farbpalette vorbereiten
        colors = TUBAF_COLORS.copy()

        stack_mode = self.stack_mode_var.get()

        # Plot jede Gruppe
        for group_idx, group in enumerate(self.groups):
            if not group.datasets:
                continue

            # Farbe für die Gruppe
            group_color = colors[group_idx % len(colors)]

            # Stack-Faktor für diese Gruppe
            stack_factor = group.stack_factor if stack_mode else 1.0

            # Plot jeden Datensatz in der Gruppe
            for ds_idx, dataset in enumerate(group.datasets):
                if dataset.x is None or dataset.y is None:
                    continue

                # Y-Werte mit Stack-Faktor multiplizieren
                y_plot = dataset.y * stack_factor

                # Label nur beim ersten Datensatz der Gruppe
                label = f"{group.name} (×{stack_factor})" if ds_idx == 0 else None

                # Hauptlinie plotten
                line_style = '-' if 'fit' in dataset.name.lower() else 'o'
                markersize = 3 if line_style == 'o' else 0

                self.ax.plot(dataset.x, y_plot, line_style,
                           color=group_color, markersize=markersize,
                           label=label, alpha=0.8)

                # Fehlerbereich als transparente Fläche
                if dataset.y_err is not None:
                    y_err_plot = dataset.y_err * stack_factor
                    self.ax.fill_between(dataset.x,
                                        y_plot - y_err_plot,
                                        y_plot + y_err_plot,
                                        color=group_color, alpha=0.2)

        # Achsen-Einstellungen
        self.ax.set_xscale('log')
        self.ax.set_yscale('log')
        self.ax.set_xlabel(self.xlabel_var.get(), fontsize=12)
        self.ax.set_ylabel(self.ylabel_var.get(), fontsize=12)
        self.ax.grid(True, alpha=0.3, which='both')
        self.ax.legend(fontsize=10, framealpha=0.9)

        self.fig.tight_layout()
        self.canvas.draw()

    def save_project(self, filepath):
        """Speichert das aktuelle Projekt"""
        # TODO: Implementierung zum Speichern des Projektzustands
        pass

    def load_project(self, filepath):
        """Lädt ein gespeichertes Projekt"""
        # TODO: Implementierung zum Laden eines Projektzustands
        pass


def main():
    """Hauptfunktion"""
    root = tk.Tk()
    app = ScatterPlotApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
