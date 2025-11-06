"""
Design Manager Dialogs

This module contains all design-related dialogs:
- DesignManagerDialog: Main dialog with tabs for styles, colors, and auto-detection
- StylePresetEditDialog: Dialog for editing style presets
- ColorSchemeEditDialog: Dialog for editing color schemes
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QWidget,
    QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QCheckBox, QComboBox, QSpinBox, QDoubleSpinBox,
    QDialogButtonBox, QMessageBox, QInputDialog, QColorDialog,
    QTabWidget
)
from PySide6.QtGui import QColor, QPixmap, QIcon


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
            from utils.user_config import get_matplotlib_colormaps
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
        self.lw_spin = QDoubleSpinBox()
        self.lw_spin.setRange(0.5, 10.0)
        self.lw_spin.setValue(self.style.get('line_width', 2))
        self.lw_spin.setSingleStep(0.5)
        layout.addWidget(self.lw_spin, row, 1)
        row += 1

        # Markergröße
        layout.addWidget(QLabel("Markergröße:"), row, 0)
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
            from utils.user_config import get_matplotlib_colormaps
            if self.scheme_name not in get_matplotlib_colormaps():
                self.config.delete_color_scheme(self.scheme_name)

        self.refresh_callback()
        self.plot_callback()
        QMessageBox.information(self, "Erfolg", f"Farbschema '{new_name}' gespeichert")
        self.accept()
