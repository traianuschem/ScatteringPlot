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
    QTabWidget, QGroupBox
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
        self.create_plot_designs_tab()  # Version 5.2

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

    def create_plot_designs_tab(self):
        """Erstellt den Plot-Designs Tab (Version 5.2)"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel("Plot-Designs kombinieren Grid-, Font- und Legenden-Einstellungen:"))

        # List Widget
        self.plot_designs_list = QListWidget()
        layout.addWidget(self.plot_designs_list)
        self.refresh_plot_designs_list()

        # Info Label
        info_label = QLabel("Aktives Design: Standard")
        info_label.setStyleSheet("font-style: italic; color: #888;")
        self.plot_design_info_label = info_label
        layout.addWidget(info_label)

        # Buttons
        btn_layout = QHBoxLayout()

        apply_btn = QPushButton("Design anwenden")
        apply_btn.clicked.connect(self.apply_plot_design)
        btn_layout.addWidget(apply_btn)

        edit_btn = QPushButton("Bearbeiten...")
        edit_btn.clicked.connect(self.edit_plot_design)
        btn_layout.addWidget(edit_btn)

        save_btn = QPushButton("Aktuelles speichern...")
        save_btn.clicked.connect(self.save_current_as_design)
        btn_layout.addWidget(save_btn)

        delete_btn = QPushButton("Löschen")
        delete_btn.clicked.connect(self.delete_plot_design)
        btn_layout.addWidget(delete_btn)

        layout.addLayout(btn_layout)
        self.tabs.addTab(tab, "Plot-Designs")

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

    def refresh_plot_designs_list(self):
        """Aktualisiert Plot-Designs-Liste (Version 5.2)"""
        self.plot_designs_list.clear()

        # Standard-Designs
        default_designs = ['Standard', 'Publikation', 'Präsentation', 'TUBAF', 'Minimalistisch']
        for name in default_designs:
            self.plot_designs_list.addItem(f"⭐ {name}")

        # Benutzerdefinierte Designs
        if hasattr(self.config, 'plot_designs'):
            for name in self.config.plot_designs.keys():
                if name not in default_designs:
                    self.plot_designs_list.addItem(f"👤 {name}")

    def apply_plot_design(self):
        """Wendet ausgewähltes Plot-Design an (Version 5.2)"""
        current_item = self.plot_designs_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "Info", "Bitte wählen Sie ein Design aus")
            return

        # Namen extrahieren (ohne Emoji-Prefix)
        name = current_item.text().split(' ', 1)[1]

        # Design laden
        design = self.get_design_by_name(name)
        if not design:
            QMessageBox.warning(self, "Fehler", f"Design '{name}' nicht gefunden")
            return

        # Design anwenden
        self.parent_app.grid_settings = design['grid_settings'].copy()
        self.parent_app.font_settings = design['font_settings'].copy()
        self.parent_app.legend_settings = design['legend_settings'].copy()
        self.parent_app.current_plot_design = name

        # Info aktualisieren
        self.plot_design_info_label.setText(f"Aktives Design: {name}")

        # Plot aktualisieren
        self.parent_app.update_plot()

        QMessageBox.information(self, "Erfolg", f"Design '{name}' wurde angewendet")

    def save_current_as_design(self):
        """Speichert aktuelle Einstellungen als neues Design (Version 5.2)"""
        name, ok = QInputDialog.getText(self, "Design speichern", "Name des neuen Designs:")
        if not ok or not name:
            return

        # Design erstellen
        design = {
            'grid_settings': self.parent_app.grid_settings.copy(),
            'font_settings': self.parent_app.font_settings.copy(),
            'legend_settings': self.parent_app.legend_settings.copy()
        }

        # In Config speichern
        if not hasattr(self.config, 'plot_designs'):
            self.config.plot_designs = {}

        self.config.plot_designs[name] = design
        self.config.save_config()

        self.refresh_plot_designs_list()
        QMessageBox.information(self, "Erfolg", f"Design '{name}' wurde gespeichert")

    def delete_plot_design(self):
        """Löscht benutzerdefiniertes Plot-Design (Version 5.2)"""
        current_item = self.plot_designs_list.currentItem()
        if not current_item:
            return

        text = current_item.text()
        if text.startswith('⭐'):
            QMessageBox.information(self, "Info", "Standard-Designs können nicht gelöscht werden")
            return

        name = text.split(' ', 1)[1]

        if hasattr(self.config, 'plot_designs') and name in self.config.plot_designs:
            del self.config.plot_designs[name]
            self.config.save_config()
            self.refresh_plot_designs_list()

    def edit_plot_design(self):
        """Bearbeitet Plot-Design (Version 5.3)"""
        current_item = self.plot_designs_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "Info", "Bitte wählen Sie ein Design aus")
            return

        # Namen extrahieren (ohne Emoji-Prefix)
        name = current_item.text().split(' ', 1)[1]

        # Design laden
        design = self.get_design_by_name(name)
        if not design:
            QMessageBox.warning(self, "Fehler", f"Design '{name}' nicht gefunden")
            return

        # Edit-Dialog öffnen
        dialog = PlotDesignEditDialog(self, name, design, self.config,
                                      self.refresh_plot_designs_list, self.parent_app.update_plot)
        dialog.exec()

    def get_design_by_name(self, name):
        """Gibt Design-Dict für Namen zurück (Version 5.2)"""
        # Vordefinierte Designs
        predefined = {
            'Standard': {
                'grid_settings': {
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
                },
                'font_settings': {
                    'title_size': 14,
                    'title_bold': True,
                    'title_italic': False,
                    'labels_size': 12,
                    'labels_bold': False,
                    'labels_italic': False,
                    'ticks_size': 10,
                    'legend_size': 10,
                    'font_family': 'sans-serif',
                    'use_math_text': False
                },
                'legend_settings': {
                    'position': 'best',
                    'fontsize': 10,
                    'ncol': 1,
                    'alpha': 0.9,
                    'frameon': True,
                    'shadow': False,
                    'fancybox': True
                }
            },
            'Publikation': {
                'grid_settings': {
                    'major_enable': False,
                    'major_axis': 'both',
                    'major_linestyle': 'solid',
                    'major_linewidth': 0.5,
                    'major_alpha': 0.2,
                    'major_color': '#888888',
                    'minor_enable': False,
                    'minor_axis': 'both',
                    'minor_linestyle': 'dotted',
                    'minor_linewidth': 0.3,
                    'minor_alpha': 0.1,
                    'minor_color': '#888888'
                },
                'font_settings': {
                    'title_size': 16,
                    'title_bold': True,
                    'title_italic': False,
                    'labels_size': 14,
                    'labels_bold': True,
                    'labels_italic': False,
                    'ticks_size': 12,
                    'legend_size': 11,
                    'font_family': 'serif',
                    'use_math_text': True
                },
                'legend_settings': {
                    'position': 'best',
                    'fontsize': 11,
                    'ncol': 1,
                    'alpha': 0.95,
                    'frameon': True,
                    'shadow': False,
                    'fancybox': False
                }
            },
            'Präsentation': {
                'grid_settings': {
                    'major_enable': True,
                    'major_axis': 'both',
                    'major_linestyle': 'solid',
                    'major_linewidth': 1.0,
                    'major_alpha': 0.4,
                    'major_color': '#FFFFFF',
                    'minor_enable': True,
                    'minor_axis': 'both',
                    'minor_linestyle': 'dotted',
                    'minor_linewidth': 0.7,
                    'minor_alpha': 0.25,
                    'minor_color': '#FFFFFF'
                },
                'font_settings': {
                    'title_size': 20,
                    'title_bold': True,
                    'title_italic': False,
                    'labels_size': 16,
                    'labels_bold': True,
                    'labels_italic': False,
                    'ticks_size': 14,
                    'legend_size': 14,
                    'font_family': 'sans-serif',
                    'use_math_text': False
                },
                'legend_settings': {
                    'position': 'upper right',
                    'fontsize': 14,
                    'ncol': 1,
                    'alpha': 0.85,
                    'frameon': True,
                    'shadow': True,
                    'fancybox': True
                }
            },
            'TUBAF': {
                'grid_settings': {
                    'major_enable': True,
                    'major_axis': 'both',
                    'major_linestyle': 'solid',
                    'major_linewidth': 0.9,
                    'major_alpha': 0.35,
                    'major_color': '#003A5D',
                    'minor_enable': False,
                    'minor_axis': 'both',
                    'minor_linestyle': 'dotted',
                    'minor_linewidth': 0.5,
                    'minor_alpha': 0.2,
                    'minor_color': '#003A5D'
                },
                'font_settings': {
                    'title_size': 15,
                    'title_bold': True,
                    'title_italic': False,
                    'labels_size': 13,
                    'labels_bold': True,
                    'labels_italic': False,
                    'ticks_size': 11,
                    'legend_size': 11,
                    'font_family': 'sans-serif',
                    'use_math_text': True
                },
                'legend_settings': {
                    'position': 'best',
                    'fontsize': 11,
                    'ncol': 1,
                    'alpha': 0.9,
                    'frameon': True,
                    'shadow': False,
                    'fancybox': True
                }
            },
            'Minimalistisch': {
                'grid_settings': {
                    'major_enable': False,
                    'major_axis': 'both',
                    'major_linestyle': 'solid',
                    'major_linewidth': 0.5,
                    'major_alpha': 0.15,
                    'major_color': '#CCCCCC',
                    'minor_enable': False,
                    'minor_axis': 'both',
                    'minor_linestyle': 'dotted',
                    'minor_linewidth': 0.3,
                    'minor_alpha': 0.1,
                    'minor_color': '#CCCCCC'
                },
                'font_settings': {
                    'title_size': 12,
                    'title_bold': False,
                    'title_italic': False,
                    'labels_size': 10,
                    'labels_bold': False,
                    'labels_italic': False,
                    'ticks_size': 9,
                    'legend_size': 9,
                    'font_family': 'sans-serif',
                    'use_math_text': False
                },
                'legend_settings': {
                    'position': 'best',
                    'fontsize': 9,
                    'ncol': 1,
                    'alpha': 0.7,
                    'frameon': False,
                    'shadow': False,
                    'fancybox': False
                }
            }
        }

        if name in predefined:
            return predefined[name]
        elif hasattr(self.config, 'plot_designs') and name in self.config.plot_designs:
            return self.config.plot_designs[name]
        else:
            return None


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


class PlotDesignEditDialog(QDialog):
    """Dialog zum Bearbeiten von Plot-Designs (Version 5.3)"""

    def __init__(self, parent, design_name, design, config, refresh_callback, plot_callback):
        super().__init__(parent)
        self.design_name = design_name
        self.config = config
        self.refresh_callback = refresh_callback
        self.plot_callback = plot_callback
        self.is_predefined = design_name in ['Standard', 'Publikation', 'Präsentation', 'TUBAF', 'Minimalistisch']

        # Deep copy der Settings
        import copy
        self.grid_settings = copy.deepcopy(design['grid_settings'])
        self.font_settings = copy.deepcopy(design['font_settings'])
        self.legend_settings = copy.deepcopy(design['legend_settings'])

        self.setWindowTitle(f"Plot-Design bearbeiten: {design_name}")
        self.resize(600, 700)

        layout = QVBoxLayout(self)

        # Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit(design_name)
        if self.is_predefined:
            self.name_edit.setPlaceholderText(f"Neuer Name (leer lassen für '{design_name}')")
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        # Info für Standard-Designs
        if self.is_predefined:
            info_label = QLabel("ℹ️  Standard-Designs werden beim Speichern überschrieben und können wiederhergestellt werden.")
            info_label.setStyleSheet("font-style: italic; color: #888; padding: 5px;")
            layout.addWidget(info_label)

        # Tabs für verschiedene Einstellungs-Kategorien
        tabs = QTabWidget()
        tabs.addTab(self.create_grid_tab(), "Grid")
        tabs.addTab(self.create_font_tab(), "Schriftarten")
        tabs.addTab(self.create_legend_tab(), "Legende")
        layout.addWidget(tabs)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def create_grid_tab(self):
        """Erstellt Grid-Einstellungen Tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Major Grid
        major_group = QGroupBox("Haupt-Grid")
        major_layout = QGridLayout()

        self.major_enable = QCheckBox("Aktiviert")
        self.major_enable.setChecked(self.grid_settings['major_enable'])
        major_layout.addWidget(self.major_enable, 0, 0, 1, 2)

        major_layout.addWidget(QLabel("Achse:"), 1, 0)
        self.major_axis = QComboBox()
        self.major_axis.addItems(['both', 'x', 'y'])
        self.major_axis.setCurrentText(self.grid_settings['major_axis'])
        major_layout.addWidget(self.major_axis, 1, 1)

        major_layout.addWidget(QLabel("Linienstil:"), 2, 0)
        self.major_linestyle = QComboBox()
        self.major_linestyle.addItems(['solid', 'dashed', 'dotted', 'dashdot'])
        self.major_linestyle.setCurrentText(self.grid_settings['major_linestyle'])
        major_layout.addWidget(self.major_linestyle, 2, 1)

        major_layout.addWidget(QLabel("Linienbreite:"), 3, 0)
        self.major_linewidth = QDoubleSpinBox()
        self.major_linewidth.setRange(0.1, 5.0)
        self.major_linewidth.setSingleStep(0.1)
        self.major_linewidth.setValue(self.grid_settings['major_linewidth'])
        major_layout.addWidget(self.major_linewidth, 3, 1)

        major_layout.addWidget(QLabel("Alpha:"), 4, 0)
        self.major_alpha = QDoubleSpinBox()
        self.major_alpha.setRange(0.0, 1.0)
        self.major_alpha.setSingleStep(0.05)
        self.major_alpha.setDecimals(2)
        self.major_alpha.setValue(self.grid_settings['major_alpha'])
        major_layout.addWidget(self.major_alpha, 4, 1)

        major_layout.addWidget(QLabel("Farbe:"), 5, 0)
        self.major_color_btn = QPushButton()
        self.major_color = self.grid_settings['major_color']
        self.major_color_btn.setStyleSheet(f"background-color: {self.major_color}; border: 1px solid #555;")
        self.major_color_btn.setText(self.major_color)
        self.major_color_btn.clicked.connect(self.choose_major_color)
        major_layout.addWidget(self.major_color_btn, 5, 1)

        major_group.setLayout(major_layout)
        layout.addWidget(major_group)

        # Minor Grid
        minor_group = QGroupBox("Neben-Grid")
        minor_layout = QGridLayout()

        self.minor_enable = QCheckBox("Aktiviert")
        self.minor_enable.setChecked(self.grid_settings['minor_enable'])
        minor_layout.addWidget(self.minor_enable, 0, 0, 1, 2)

        minor_layout.addWidget(QLabel("Achse:"), 1, 0)
        self.minor_axis = QComboBox()
        self.minor_axis.addItems(['both', 'x', 'y'])
        self.minor_axis.setCurrentText(self.grid_settings['minor_axis'])
        minor_layout.addWidget(self.minor_axis, 1, 1)

        minor_layout.addWidget(QLabel("Linienstil:"), 2, 0)
        self.minor_linestyle = QComboBox()
        self.minor_linestyle.addItems(['solid', 'dashed', 'dotted', 'dashdot'])
        self.minor_linestyle.setCurrentText(self.grid_settings['minor_linestyle'])
        minor_layout.addWidget(self.minor_linestyle, 2, 1)

        minor_layout.addWidget(QLabel("Linienbreite:"), 3, 0)
        self.minor_linewidth = QDoubleSpinBox()
        self.minor_linewidth.setRange(0.1, 5.0)
        self.minor_linewidth.setSingleStep(0.1)
        self.minor_linewidth.setValue(self.grid_settings['minor_linewidth'])
        minor_layout.addWidget(self.minor_linewidth, 3, 1)

        minor_layout.addWidget(QLabel("Alpha:"), 4, 0)
        self.minor_alpha = QDoubleSpinBox()
        self.minor_alpha.setRange(0.0, 1.0)
        self.minor_alpha.setSingleStep(0.05)
        self.minor_alpha.setDecimals(2)
        self.minor_alpha.setValue(self.grid_settings['minor_alpha'])
        minor_layout.addWidget(self.minor_alpha, 4, 1)

        minor_layout.addWidget(QLabel("Farbe:"), 5, 0)
        self.minor_color_btn = QPushButton()
        self.minor_color = self.grid_settings['minor_color']
        self.minor_color_btn.setStyleSheet(f"background-color: {self.minor_color}; border: 1px solid #555;")
        self.minor_color_btn.setText(self.minor_color)
        self.minor_color_btn.clicked.connect(self.choose_minor_color)
        minor_layout.addWidget(self.minor_color_btn, 5, 1)

        minor_group.setLayout(minor_layout)
        layout.addWidget(minor_group)

        layout.addStretch()
        return tab

    def create_font_tab(self):
        """Erstellt Font-Einstellungen Tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Font-Familie
        family_layout = QHBoxLayout()
        family_layout.addWidget(QLabel("Schriftfamilie:"))
        self.font_family = QComboBox()
        self.font_family.addItems(['sans-serif', 'serif', 'monospace'])
        self.font_family.setCurrentText(self.font_settings.get('font_family', 'sans-serif'))
        family_layout.addWidget(self.font_family)
        layout.addLayout(family_layout)

        # Math Text
        self.use_math_text = QCheckBox("Math Text verwenden (für Exponenten)")
        self.use_math_text.setChecked(self.font_settings.get('use_math_text', False))
        layout.addWidget(self.use_math_text)

        # Titel
        title_group = QGroupBox("Titel")
        title_layout = QGridLayout()

        title_layout.addWidget(QLabel("Größe:"), 0, 0)
        self.title_size = QSpinBox()
        self.title_size.setRange(8, 32)
        self.title_size.setValue(self.font_settings.get('title_size', 14))
        title_layout.addWidget(self.title_size, 0, 1)

        self.title_bold = QCheckBox("Fett")
        self.title_bold.setChecked(self.font_settings.get('title_bold', True))
        title_layout.addWidget(self.title_bold, 1, 0)

        self.title_italic = QCheckBox("Kursiv")
        self.title_italic.setChecked(self.font_settings.get('title_italic', False))
        title_layout.addWidget(self.title_italic, 1, 1)

        title_group.setLayout(title_layout)
        layout.addWidget(title_group)

        # Labels
        labels_group = QGroupBox("Achsenbeschriftungen")
        labels_layout = QGridLayout()

        labels_layout.addWidget(QLabel("Größe:"), 0, 0)
        self.labels_size = QSpinBox()
        self.labels_size.setRange(8, 32)
        self.labels_size.setValue(self.font_settings.get('labels_size', 12))
        labels_layout.addWidget(self.labels_size, 0, 1)

        self.labels_bold = QCheckBox("Fett")
        self.labels_bold.setChecked(self.font_settings.get('labels_bold', False))
        labels_layout.addWidget(self.labels_bold, 1, 0)

        self.labels_italic = QCheckBox("Kursiv")
        self.labels_italic.setChecked(self.font_settings.get('labels_italic', False))
        labels_layout.addWidget(self.labels_italic, 1, 1)

        labels_group.setLayout(labels_layout)
        layout.addWidget(labels_group)

        # Ticks
        ticks_group = QGroupBox("Tick-Labels")
        ticks_layout = QGridLayout()

        ticks_layout.addWidget(QLabel("Größe:"), 0, 0)
        self.ticks_size = QSpinBox()
        self.ticks_size.setRange(6, 24)
        self.ticks_size.setValue(self.font_settings.get('ticks_size', 10))
        ticks_layout.addWidget(self.ticks_size, 0, 1)

        self.ticks_bold = QCheckBox("Fett")
        self.ticks_bold.setChecked(self.font_settings.get('ticks_bold', False))
        ticks_layout.addWidget(self.ticks_bold, 1, 0)

        self.ticks_italic = QCheckBox("Kursiv")
        self.ticks_italic.setChecked(self.font_settings.get('ticks_italic', False))
        ticks_layout.addWidget(self.ticks_italic, 1, 1)

        ticks_group.setLayout(ticks_layout)
        layout.addWidget(ticks_group)

        # Legend Size
        legend_size_group = QGroupBox("Legende")
        legend_size_layout = QGridLayout()

        legend_size_layout.addWidget(QLabel("Größe:"), 0, 0)
        self.legend_font_size = QSpinBox()
        self.legend_font_size.setRange(6, 24)
        self.legend_font_size.setValue(self.font_settings.get('legend_size', 10))
        legend_size_layout.addWidget(self.legend_font_size, 0, 1)

        self.legend_bold = QCheckBox("Fett")
        self.legend_bold.setChecked(self.font_settings.get('legend_bold', False))
        legend_size_layout.addWidget(self.legend_bold, 1, 0)

        self.legend_italic = QCheckBox("Kursiv")
        self.legend_italic.setChecked(self.font_settings.get('legend_italic', False))
        legend_size_layout.addWidget(self.legend_italic, 1, 1)

        legend_size_group.setLayout(legend_size_layout)
        layout.addWidget(legend_size_group)

        layout.addStretch()
        return tab

    def create_legend_tab(self):
        """Erstellt Legenden-Einstellungen Tab"""
        tab = QWidget()
        layout = QGridLayout(tab)

        layout.addWidget(QLabel("Position:"), 0, 0)
        self.legend_position = QComboBox()
        self.legend_position.addItems(['best', 'upper right', 'upper left', 'lower right', 'lower left',
                                       'center right', 'center left', 'upper center', 'lower center', 'center'])
        self.legend_position.setCurrentText(self.legend_settings.get('position', 'best'))
        layout.addWidget(self.legend_position, 0, 1)

        layout.addWidget(QLabel("Spalten:"), 1, 0)
        self.legend_ncol = QSpinBox()
        self.legend_ncol.setRange(1, 5)
        self.legend_ncol.setValue(self.legend_settings.get('ncol', 1))
        layout.addWidget(self.legend_ncol, 1, 1)

        layout.addWidget(QLabel("Alpha:"), 2, 0)
        self.legend_alpha = QDoubleSpinBox()
        self.legend_alpha.setRange(0.0, 1.0)
        self.legend_alpha.setSingleStep(0.05)
        self.legend_alpha.setDecimals(2)
        self.legend_alpha.setValue(self.legend_settings.get('alpha', 0.9))
        layout.addWidget(self.legend_alpha, 2, 1)

        self.legend_frameon = QCheckBox("Rahmen anzeigen")
        self.legend_frameon.setChecked(self.legend_settings.get('frameon', True))
        layout.addWidget(self.legend_frameon, 3, 0, 1, 2)

        self.legend_shadow = QCheckBox("Schatten")
        self.legend_shadow.setChecked(self.legend_settings.get('shadow', False))
        layout.addWidget(self.legend_shadow, 4, 0, 1, 2)

        self.legend_fancybox = QCheckBox("Abgerundete Ecken")
        self.legend_fancybox.setChecked(self.legend_settings.get('fancybox', True))
        layout.addWidget(self.legend_fancybox, 5, 0, 1, 2)

        layout.setRowStretch(6, 1)
        return tab

    def choose_major_color(self):
        """Wählt Farbe für Haupt-Grid"""
        color = QColorDialog.getColor(QColor(self.major_color), self, "Haupt-Grid Farbe")
        if color.isValid():
            self.major_color = color.name()
            self.major_color_btn.setStyleSheet(f"background-color: {self.major_color}; border: 1px solid #555;")
            self.major_color_btn.setText(self.major_color)

    def choose_minor_color(self):
        """Wählt Farbe für Neben-Grid"""
        color = QColorDialog.getColor(QColor(self.minor_color), self, "Neben-Grid Farbe")
        if color.isValid():
            self.minor_color = color.name()
            self.minor_color_btn.setStyleSheet(f"background-color: {self.minor_color}; border: 1px solid #555;")
            self.minor_color_btn.setText(self.minor_color)

    def save(self):
        """Speichert das Plot-Design"""
        new_name = self.name_edit.text().strip()

        # Wenn Name leer und es ist ein Standard-Design, verwende Original-Namen
        if not new_name:
            if self.is_predefined:
                new_name = self.design_name
            else:
                QMessageBox.critical(self, "Fehler", "Name darf nicht leer sein")
                return

        # Einstellungen sammeln
        new_design = {
            'grid_settings': {
                'major_enable': self.major_enable.isChecked(),
                'major_axis': self.major_axis.currentText(),
                'major_linestyle': self.major_linestyle.currentText(),
                'major_linewidth': self.major_linewidth.value(),
                'major_alpha': self.major_alpha.value(),
                'major_color': self.major_color,
                'minor_enable': self.minor_enable.isChecked(),
                'minor_axis': self.minor_axis.currentText(),
                'minor_linestyle': self.minor_linestyle.currentText(),
                'minor_linewidth': self.minor_linewidth.value(),
                'minor_alpha': self.minor_alpha.value(),
                'minor_color': self.minor_color
            },
            'font_settings': {
                'title_size': self.title_size.value(),
                'title_bold': self.title_bold.isChecked(),
                'title_italic': self.title_italic.isChecked(),
                'title_underline': self.font_settings.get('title_underline', False),
                'labels_size': self.labels_size.value(),
                'labels_bold': self.labels_bold.isChecked(),
                'labels_italic': self.labels_italic.isChecked(),
                'labels_underline': self.font_settings.get('labels_underline', False),
                'ticks_size': self.ticks_size.value(),
                'ticks_bold': self.ticks_bold.isChecked(),
                'ticks_italic': self.ticks_italic.isChecked(),
                'ticks_underline': self.font_settings.get('ticks_underline', False),
                'legend_size': self.legend_font_size.value(),
                'legend_bold': self.legend_bold.isChecked(),
                'legend_italic': self.legend_italic.isChecked(),
                'legend_underline': self.font_settings.get('legend_underline', False),
                'font_family': self.font_family.currentText(),
                'use_math_text': self.use_math_text.isChecked()
            },
            'legend_settings': {
                'position': self.legend_position.currentText(),
                'fontsize': self.legend_font_size.value(),  # Für Kompatibilität
                'ncol': self.legend_ncol.value(),
                'alpha': self.legend_alpha.value(),
                'frameon': self.legend_frameon.isChecked(),
                'shadow': self.legend_shadow.isChecked(),
                'fancybox': self.legend_fancybox.isChecked()
            }
        }

        # In Config speichern
        if not hasattr(self.config, 'plot_designs'):
            self.config.plot_designs = {}

        self.config.plot_designs[new_name] = new_design
        self.config.save_config()

        # Wenn Name geändert wurde und es kein Standard-Design ist, altes löschen
        if new_name != self.design_name and not self.is_predefined:
            if self.design_name in self.config.plot_designs:
                del self.config.plot_designs[self.design_name]
                self.config.save_config()

        self.refresh_callback()
        self.plot_callback()

        if self.is_predefined and new_name == self.design_name:
            QMessageBox.information(self, "Erfolg",
                f"Standard-Design '{new_name}' wurde überschrieben.\n\n"
                "Löschen Sie das Design in der Liste, um die Standardwerte wiederherzustellen.")
        else:
            QMessageBox.information(self, "Erfolg", f"Design '{new_name}' wurde gespeichert")

        self.accept()
