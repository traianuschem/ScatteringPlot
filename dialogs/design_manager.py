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
from utils.logger import get_logger
from i18n import tr


# Vordefinierte Design-Keys (intern, nicht übersetzt)
PREDEFINED_DESIGN_KEYS = ['standard', 'publication', 'presentation', 'tubaf', 'minimalist']


def get_predefined_design_name(key):
    """Gibt den übersetzten Namen für ein vordefiniertes Design zurück (v7.0.3)"""
    return tr(f"design_manager.plot_designs.predefined.{key}")


def get_all_predefined_design_names():
    """Gibt alle übersetzten vordefinierten Design-Namen zurück (v7.0.3)"""
    return [get_predefined_design_name(key) for key in PREDEFINED_DESIGN_KEYS]


def normalize_design_name(name):
    """
    Konvertiert einen Design-Namen (übersetzt oder alt) zu einem internen Key (v7.0.3).
    Unterstützt Rückwärtskompatibilität mit alten deutschen Design-Namen.
    """
    # Mapping von alten deutschen Namen zu internen Keys
    legacy_mapping = {
        'Standard': 'standard',
        'Publikation': 'publication',
        'Publication': 'publication',
        'Präsentation': 'presentation',
        'Presentation': 'presentation',
        'TUBAF': 'tubaf',
        'Minimalistisch': 'minimalist',
        'Minimalist': 'minimalist'
    }

    # Wenn es ein alter Name ist, konvertiere zu internem Key
    if name in legacy_mapping:
        return legacy_mapping[name]

    # Ansonsten gebe den Namen zurück (könnte schon ein interner Key oder ein benutzerdefinierter Name sein)
    return name


class DesignManagerDialog(QDialog):
    """Design-Manager Dialog mit Tabs"""

    def __init__(self, parent, config):
        super().__init__(parent)
        self.setWindowTitle(tr("design_manager.title"))
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
        close_btn = QPushButton(tr("design_manager.close"))
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def create_styles_tab(self):
        """Erstellt den Stil-Vorlagen Tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel(tr("design_manager.styles.available")))

        # List Widget
        self.styles_list = QListWidget()
        layout.addWidget(self.styles_list)
        self.refresh_styles_list()

        # Buttons
        btn_layout = QHBoxLayout()
        new_btn = QPushButton(tr("design_manager.styles.new"))
        new_btn.clicked.connect(self.create_new_style)
        btn_layout.addWidget(new_btn)

        edit_btn = QPushButton(tr("design_manager.styles.edit"))
        edit_btn.clicked.connect(self.edit_style)
        btn_layout.addWidget(edit_btn)

        delete_btn = QPushButton(tr("design_manager.styles.delete"))
        delete_btn.clicked.connect(self.delete_style)
        btn_layout.addWidget(delete_btn)

        layout.addLayout(btn_layout)
        self.tabs.addTab(tab, tr("design_manager.tabs.styles"))

    def create_colors_tab(self):
        """Erstellt den Farbschemata Tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel(tr("design_manager.colors.available")))

        # List Widget
        self.colors_list = QListWidget()
        layout.addWidget(self.colors_list)
        self.refresh_colors_list()

        # Buttons
        btn_layout = QHBoxLayout()
        new_btn = QPushButton(tr("design_manager.colors.new"))
        new_btn.clicked.connect(self.create_new_scheme)
        btn_layout.addWidget(new_btn)

        edit_btn = QPushButton(tr("design_manager.colors.edit"))
        edit_btn.clicked.connect(self.edit_scheme)
        btn_layout.addWidget(edit_btn)

        delete_btn = QPushButton(tr("design_manager.colors.delete"))
        delete_btn.clicked.connect(self.delete_scheme)
        btn_layout.addWidget(delete_btn)

        layout.addLayout(btn_layout)
        self.tabs.addTab(tab, tr("design_manager.tabs.colors"))

    def create_autodetect_tab(self):
        """Erstellt den Auto-Erkennung Tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel(tr("design_manager.autodetect.mapping")))

        # List Widget
        self.autodetect_list = QListWidget()
        layout.addWidget(self.autodetect_list)
        self.refresh_autodetect_list()

        # Aktivieren Checkbox
        self.autodetect_enabled = QCheckBox(tr("design_manager.autodetect.enabled"))
        self.autodetect_enabled.setChecked(self.config.auto_detection_enabled)
        self.autodetect_enabled.stateChanged.connect(self.toggle_autodetect)
        layout.addWidget(self.autodetect_enabled)

        # Buttons
        btn_layout = QHBoxLayout()
        new_btn = QPushButton(tr("design_manager.autodetect.new_rule"))
        new_btn.clicked.connect(self.create_autodetect_rule)
        btn_layout.addWidget(new_btn)

        delete_btn = QPushButton(tr("design_manager.autodetect.delete"))
        delete_btn.clicked.connect(self.delete_autodetect_rule)
        btn_layout.addWidget(delete_btn)

        layout.addLayout(btn_layout)
        self.tabs.addTab(tab, tr("design_manager.tabs.autodetect"))

    def create_plot_designs_tab(self):
        """Erstellt den Plot-Designs Tab (Version 5.2)"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel(tr("design_manager.plot_designs.description")))

        # List Widget
        self.plot_designs_list = QListWidget()
        layout.addWidget(self.plot_designs_list)
        self.refresh_plot_designs_list()

        # Info Label
        info_label = QLabel(tr("design_manager.plot_designs.active_default"))
        info_label.setStyleSheet("font-style: italic; color: #888;")
        self.plot_design_info_label = info_label
        layout.addWidget(info_label)

        # Buttons
        btn_layout = QHBoxLayout()

        apply_btn = QPushButton(tr("design_manager.plot_designs.apply"))
        apply_btn.clicked.connect(self.apply_plot_design)
        btn_layout.addWidget(apply_btn)

        edit_btn = QPushButton(tr("design_manager.plot_designs.edit"))
        edit_btn.clicked.connect(self.edit_plot_design)
        btn_layout.addWidget(edit_btn)

        save_btn = QPushButton(tr("design_manager.plot_designs.save_current"))
        save_btn.clicked.connect(self.save_current_as_design)
        btn_layout.addWidget(save_btn)

        delete_btn = QPushButton(tr("design_manager.plot_designs.delete"))
        delete_btn.clicked.connect(self.delete_plot_design)
        btn_layout.addWidget(delete_btn)

        layout.addLayout(btn_layout)

        # Zweite Button-Reihe für Standard-Einstellungen (v5.4)
        default_layout = QHBoxLayout()

        save_default_btn = QPushButton(tr("design_manager.plot_designs.save_as_default"))
        save_default_btn.setToolTip(tr("design_manager.plot_designs.save_as_default_tooltip"))
        save_default_btn.clicked.connect(self.save_as_default)
        default_layout.addWidget(save_default_btn)

        layout.addLayout(default_layout)
        self.tabs.addTab(tab, tr("design_manager.tabs.plot_designs"))

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
        name, ok = QInputDialog.getText(self, tr("design_manager.styles.new_title"), tr("design_manager.styles.name_prompt"))
        if ok and name:
            style = {
                'line_style': '-',
                'marker_style': '',
                'line_width': 2,
                'marker_size': 4,
                'description': tr("design_manager.styles.custom")
            }
            self.config.add_style_preset(name, style)
            self.refresh_styles_list()
            self.parent_app.update_plot()

    def edit_style(self):
        """Bearbeitet Stil"""
        current_item = self.styles_list.currentItem()
        if not current_item:
            QMessageBox.information(self, tr("design_manager.info"), tr("design_manager.styles.select_style"))
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
        reply = QMessageBox.question(self, tr("design_manager.delete"), tr("design_manager.styles.delete_confirm", name=name),
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.config.delete_style_preset(name)
            self.refresh_styles_list()
            self.parent_app.update_plot()

    def create_new_scheme(self):
        """Erstellt neues Farbschema"""
        name, ok = QInputDialog.getText(self, tr("design_manager.colors.new_title"), tr("design_manager.colors.name_prompt"))
        if not name or not ok:
            return

        # 5 Farben abfragen
        colors = []
        for i in range(5):
            color = QColorDialog.getColor(title=tr("design_manager.colors.color_n", n=i+1))
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
            QMessageBox.information(self, tr("design_manager.info"), tr("design_manager.colors.select_scheme"))
            return

        name = current_item.text()

        # Matplotlib-Schemata nicht bearbeitbar
        try:
            from utils.user_config import get_matplotlib_colormaps
            matplotlib_maps = list(get_matplotlib_colormaps().keys())

            if name in matplotlib_maps:
                QMessageBox.information(self, tr("design_manager.info"),
                    tr("design_manager.colors.matplotlib_not_editable"))
                return
        except Exception as e:
            print(f"Warnung: Fehler beim Laden der Matplotlib-Colormaps: {e}")
            matplotlib_maps = []

        if name in self.config.color_schemes:
            try:
                dialog = ColorSchemeEditDialog(self, name, self.config, self.refresh_colors_list, self.parent_app.update_plot)
                dialog.exec()
            except Exception as e:
                QMessageBox.critical(self, tr("design_manager.error"), tr("design_manager.colors.dialog_error", error=str(e)))
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
            QMessageBox.information(self, tr("design_manager.info"), tr("design_manager.colors.cannot_delete_default"))

    def create_autodetect_rule(self):
        """Erstellt Auto-Erkennungs-Regel"""
        keyword, ok = QInputDialog.getText(self, tr("design_manager.autodetect.new_keyword"), tr("design_manager.autodetect.keyword_prompt"))
        if not ok or not keyword:
            return

        styles = list(self.config.style_presets.keys())
        style, ok2 = QInputDialog.getItem(self, tr("design_manager.autodetect.style"), tr("design_manager.autodetect.select_style"), styles, 0, False)
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
        """Aktualisiert Plot-Designs-Liste (Version 5.2, erweitert v7.0.3)"""
        self.plot_designs_list.clear()

        # Standard-Designs (v7.0.3: jetzt übersetzt)
        predefined_names = get_all_predefined_design_names()
        for name in predefined_names:
            self.plot_designs_list.addItem(f"⭐ {name}")

        # Benutzerdefinierte Designs
        if hasattr(self.config, 'plot_designs'):
            for name in self.config.plot_designs.keys():
                if name not in predefined_names and name not in PREDEFINED_DESIGN_KEYS:
                    self.plot_designs_list.addItem(f"👤 {name}")

    def apply_plot_design(self):
        """Wendet ausgewähltes Plot-Design an (Version 5.2, erweitert v7.0.3)"""
        current_item = self.plot_designs_list.currentItem()
        if not current_item:
            QMessageBox.information(self, tr("design_manager.info"), tr("design_manager.plot_designs.select_design"))
            return

        # Namen extrahieren (ohne Emoji-Prefix)
        name = current_item.text().split(' ', 1)[1]

        # Design laden
        design = self.get_design_by_name(name)
        if not design:
            QMessageBox.warning(self, tr("design_manager.error"), tr("design_manager.plot_designs.not_found", name=name))
            return

        # Design anwenden (v7.0.3: inkl. xlabel, ylabel, axis_limits)
        self.parent_app.grid_settings = design['grid_settings'].copy()
        self.parent_app.font_settings = design['font_settings'].copy()
        self.parent_app.legend_settings = design['legend_settings'].copy()
        self.parent_app.custom_xlabel = design.get('custom_xlabel', None)
        self.parent_app.custom_ylabel = design.get('custom_ylabel', None)
        if design.get('axis_limits'):
            self.parent_app.axis_limits = design['axis_limits'].copy()
        else:
            self.parent_app.axis_limits = {'xmin': None, 'xmax': None, 'ymin': None, 'ymax': None, 'auto': True}
        # Normalisiere den Namen vor dem Speichern (v7.0.3)
        self.parent_app.current_plot_design = normalize_design_name(name)

        # Info aktualisieren
        self.plot_design_info_label.setText(tr("design_manager.plot_designs.active", name=name))

        # Plot aktualisieren
        self.parent_app.update_plot()

        QMessageBox.information(self, tr("design_manager.success"), tr("design_manager.plot_designs.applied", name=name))

    def save_current_as_design(self):
        """Speichert aktuelle Einstellungen als neues Design (Version 5.2, erweitert v7.0.3)"""
        name, ok = QInputDialog.getText(self, tr("design_manager.plot_designs.save_title"), tr("design_manager.plot_designs.name_prompt"))
        if not ok or not name:
            return

        # Design erstellen (v7.0.3: inkl. xlabel, ylabel, axis_limits)
        design = {
            'grid_settings': self.parent_app.grid_settings.copy(),
            'font_settings': self.parent_app.font_settings.copy(),
            'legend_settings': self.parent_app.legend_settings.copy(),
            'custom_xlabel': self.parent_app.custom_xlabel,
            'custom_ylabel': self.parent_app.custom_ylabel,
            'axis_limits': self.parent_app.axis_limits.copy() if self.parent_app.axis_limits else None
        }

        # In Config speichern
        if not hasattr(self.config, 'plot_designs'):
            self.config.plot_designs = {}

        self.config.plot_designs[name] = design
        self.config.save_config()

        self.refresh_plot_designs_list()
        QMessageBox.information(self, tr("design_manager.success"), tr("design_manager.plot_designs.saved", name=name))

    def save_as_default(self):
        """Speichert aktuelle Einstellungen als Programmstandard (Version 5.4)"""
        logger = get_logger()
        logger.info("Speichere aktuelle Einstellungen als Programmstandard...")

        reply = QMessageBox.question(
            self,
            tr("design_manager.plot_designs.save_default_title"),
            tr("design_manager.plot_designs.save_default_prompt"),
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            logger.debug(f"  Legend Settings: {list(self.parent_app.legend_settings.keys())}")
            logger.debug(f"  Grid Settings: {list(self.parent_app.grid_settings.keys())}")
            logger.debug(f"  Font Settings: {list(self.parent_app.font_settings.keys())}")
            logger.debug(f"  Plot Design: {self.parent_app.current_plot_design}")
            logger.debug(f"  Custom X-Label: {self.parent_app.custom_xlabel}")
            logger.debug(f"  Custom Y-Label: {self.parent_app.custom_ylabel}")

            self.config.save_default_plot_settings(
                self.parent_app.legend_settings,
                self.parent_app.grid_settings,
                self.parent_app.font_settings,
                self.parent_app.current_plot_design,
                self.parent_app.custom_xlabel,
                self.parent_app.custom_ylabel,
                self.parent_app.axis_limits
            )
            logger.info("Standard-Einstellungen erfolgreich gespeichert")
            QMessageBox.information(
                self,
                tr("design_manager.success"),
                tr("design_manager.plot_designs.save_default_success")
            )
        else:
            logger.debug("Speichern als Standard abgebrochen")

    def delete_plot_design(self):
        """Löscht benutzerdefiniertes Plot-Design (Version 5.2)"""
        current_item = self.plot_designs_list.currentItem()
        if not current_item:
            return

        text = current_item.text()
        if text.startswith('⭐'):
            QMessageBox.information(self, tr("design_manager.info"), tr("design_manager.plot_designs.cannot_delete_default"))
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
            QMessageBox.information(self, tr("design_manager.info"), tr("design_manager.plot_designs.select_design"))
            return

        # Namen extrahieren (ohne Emoji-Prefix)
        name = current_item.text().split(' ', 1)[1]

        # Design laden
        design = self.get_design_by_name(name)
        if not design:
            QMessageBox.warning(self, tr("design_manager.error"), tr("design_manager.plot_designs.not_found", name=name))
            return

        # Edit-Dialog öffnen
        dialog = PlotDesignEditDialog(self, name, design, self.config,
                                      self.refresh_plot_designs_list, self.parent_app.update_plot)
        dialog.exec()

    def get_design_by_name(self, name):
        """Gibt Design-Dict für Namen zurück (Version 5.2, erweitert v7.0.3)"""
        # Name normalisieren (v7.0.3: Unterstützt alte deutsche Namen)
        name = normalize_design_name(name)

        # Vordefinierte Designs (v7.0.3: jetzt mit internen Keys)
        predefined = {
            'standard': {
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
            'publication': {
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
            'presentation': {
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
            'tubaf': {
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
            'minimalist': {
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

        self.setWindowTitle(tr("style_preset.edit_title", name=style_name))
        self.resize(450, 350)

        layout = QGridLayout(self)
        row = 0

        # Name
        layout.addWidget(QLabel(tr("style_preset.name")), row, 0)
        self.name_edit = QLineEdit(style_name)
        layout.addWidget(self.name_edit, row, 1)
        row += 1

        # Beschreibung
        layout.addWidget(QLabel(tr("style_preset.description")), row, 0)
        self.desc_edit = QLineEdit(self.style.get('description', ''))
        layout.addWidget(self.desc_edit, row, 1)
        row += 1

        # Linientyp
        layout.addWidget(QLabel(tr("style_preset.line_style")), row, 0)
        self.line_combo = QComboBox()
        self.line_combo.addItems(['', '-', '--', '-.', ':'])
        self.line_combo.setCurrentText(self.style.get('line_style', ''))
        layout.addWidget(self.line_combo, row, 1)
        row += 1

        # Marker
        layout.addWidget(QLabel(tr("style_preset.marker")), row, 0)
        self.marker_combo = QComboBox()
        self.marker_combo.addItems(['', 'o', 's', '^', 'v', 'D', '*', '+', 'x', 'p', 'h'])
        self.marker_combo.setCurrentText(self.style.get('marker_style', ''))
        layout.addWidget(self.marker_combo, row, 1)
        row += 1

        # Linienbreite
        layout.addWidget(QLabel(tr("style_preset.line_width")), row, 0)
        self.lw_spin = QDoubleSpinBox()
        self.lw_spin.setRange(0.5, 10.0)
        self.lw_spin.setValue(self.style.get('line_width', 2))
        self.lw_spin.setSingleStep(0.5)
        layout.addWidget(self.lw_spin, row, 1)
        row += 1

        # Markergröße
        layout.addWidget(QLabel(tr("style_preset.marker_size")), row, 0)
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
            QMessageBox.critical(self, tr("design_manager.error"), tr("style_preset.name_required"))
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

        self.setWindowTitle(tr("color_scheme.edit_title", name=scheme_name))
        self.resize(500, 500)

        layout = QVBoxLayout(self)

        # Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel(tr("color_scheme.name")))
        self.name_edit = QLineEdit(scheme_name)
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        # Farbliste
        layout.addWidget(QLabel(tr("color_scheme.colors")))
        self.color_list = QListWidget()
        layout.addWidget(self.color_list)
        self.refresh_color_list()

        # Buttons für Farben
        color_btn_layout = QHBoxLayout()
        add_btn = QPushButton(tr("color_scheme.add"))
        add_btn.clicked.connect(self.add_color)
        color_btn_layout.addWidget(add_btn)

        edit_btn = QPushButton(tr("color_scheme.edit"))
        edit_btn.clicked.connect(self.edit_color)
        color_btn_layout.addWidget(edit_btn)

        up_btn = QPushButton(tr("color_scheme.move_up"))
        up_btn.clicked.connect(self.move_up)
        color_btn_layout.addWidget(up_btn)

        down_btn = QPushButton(tr("color_scheme.move_down"))
        down_btn.clicked.connect(self.move_down)
        color_btn_layout.addWidget(down_btn)

        remove_btn = QPushButton(tr("color_scheme.remove"))
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
        color = QColorDialog.getColor(title=tr("color_scheme.choose_color"))
        if color.isValid():
            self.colors.append(color.name())
            self.refresh_color_list()

    def edit_color(self):
        """Ändert Farbe"""
        current_row = self.color_list.currentRow()
        if current_row < 0:
            QMessageBox.information(self, tr("design_manager.info"), tr("color_scheme.select_color"))
            return

        old_color = self.colors[current_row]
        color = QColorDialog.getColor(QColor(old_color), self, tr("color_scheme.change_color"))
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
            QMessageBox.warning(self, tr("design_manager.warning"), tr("color_scheme.min_colors"))
            return

        del self.colors[current_row]
        self.refresh_color_list()

    def save(self):
        """Speichert das Farbschema"""
        new_name = self.name_edit.text()
        if not new_name:
            QMessageBox.critical(self, tr("design_manager.error"), tr("color_scheme.name_required"))
            return

        if len(self.colors) < 2:
            QMessageBox.critical(self, tr("design_manager.error"), tr("color_scheme.min_colors_required"))
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
        QMessageBox.information(self, tr("design_manager.success"), tr("color_scheme.saved", name=new_name))
        self.accept()


class PlotDesignEditDialog(QDialog):
    """Dialog zum Bearbeiten von Plot-Designs (Version 5.3)"""

    def __init__(self, parent, design_name, design, config, refresh_callback, plot_callback):
        super().__init__(parent)
        self.design_name = design_name
        self.config = config
        self.refresh_callback = refresh_callback
        self.plot_callback = plot_callback
        # v7.0.3: Verwende interne Keys und normalisiere den Namen
        normalized_name = normalize_design_name(design_name)
        self.is_predefined = normalized_name in PREDEFINED_DESIGN_KEYS

        # Deep copy der Settings
        import copy
        self.grid_settings = copy.deepcopy(design['grid_settings'])
        self.font_settings = copy.deepcopy(design['font_settings'])
        self.legend_settings = copy.deepcopy(design['legend_settings'])

        self.setWindowTitle(tr("plot_design.edit_title", name=design_name))
        self.resize(600, 700)

        layout = QVBoxLayout(self)

        # Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel(tr("plot_design.name")))
        self.name_edit = QLineEdit(design_name)
        if self.is_predefined:
            self.name_edit.setPlaceholderText(tr("plot_design.name_placeholder", name=design_name))
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        # Info für Standard-Designs
        if self.is_predefined:
            info_label = QLabel(tr("plot_design.default_info"))
            info_label.setStyleSheet("font-style: italic; color: #888; padding: 5px;")
            layout.addWidget(info_label)

        # Tabs für verschiedene Einstellungs-Kategorien
        tabs = QTabWidget()
        tabs.addTab(self.create_grid_tab(), tr("plot_design.tabs.grid"))
        tabs.addTab(self.create_font_tab(), tr("plot_design.tabs.fonts"))
        tabs.addTab(self.create_legend_tab(), tr("plot_design.tabs.legend"))
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
        major_group = QGroupBox(tr("plot_design.grid.major"))
        major_layout = QGridLayout()

        self.major_enable = QCheckBox(tr("plot_design.grid.enabled"))
        self.major_enable.setChecked(self.grid_settings['major_enable'])
        major_layout.addWidget(self.major_enable, 0, 0, 1, 2)

        major_layout.addWidget(QLabel(tr("plot_design.grid.axis")), 1, 0)
        self.major_axis = QComboBox()
        self.major_axis.addItems(['both', 'x', 'y'])
        self.major_axis.setCurrentText(self.grid_settings['major_axis'])
        major_layout.addWidget(self.major_axis, 1, 1)

        major_layout.addWidget(QLabel(tr("plot_design.grid.linestyle")), 2, 0)
        self.major_linestyle = QComboBox()
        self.major_linestyle.addItems(['solid', 'dashed', 'dotted', 'dashdot'])
        self.major_linestyle.setCurrentText(self.grid_settings['major_linestyle'])
        major_layout.addWidget(self.major_linestyle, 2, 1)

        major_layout.addWidget(QLabel(tr("plot_design.grid.linewidth")), 3, 0)
        self.major_linewidth = QDoubleSpinBox()
        self.major_linewidth.setRange(0.1, 5.0)
        self.major_linewidth.setSingleStep(0.1)
        self.major_linewidth.setValue(self.grid_settings['major_linewidth'])
        major_layout.addWidget(self.major_linewidth, 3, 1)

        major_layout.addWidget(QLabel(tr("plot_design.grid.alpha")), 4, 0)
        self.major_alpha = QDoubleSpinBox()
        self.major_alpha.setRange(0.0, 1.0)
        self.major_alpha.setSingleStep(0.05)
        self.major_alpha.setDecimals(2)
        self.major_alpha.setValue(self.grid_settings['major_alpha'])
        major_layout.addWidget(self.major_alpha, 4, 1)

        major_layout.addWidget(QLabel(tr("plot_design.grid.color")), 5, 0)
        self.major_color_btn = QPushButton()
        self.major_color = self.grid_settings['major_color']
        self.major_color_btn.setStyleSheet(f"background-color: {self.major_color}; border: 1px solid #555;")
        self.major_color_btn.setText(self.major_color)
        self.major_color_btn.clicked.connect(self.choose_major_color)
        major_layout.addWidget(self.major_color_btn, 5, 1)

        major_group.setLayout(major_layout)
        layout.addWidget(major_group)

        # Minor Grid
        minor_group = QGroupBox(tr("plot_design.grid.minor"))
        minor_layout = QGridLayout()

        self.minor_enable = QCheckBox(tr("plot_design.grid.enabled"))
        self.minor_enable.setChecked(self.grid_settings['minor_enable'])
        minor_layout.addWidget(self.minor_enable, 0, 0, 1, 2)

        minor_layout.addWidget(QLabel(tr("plot_design.grid.axis")), 1, 0)
        self.minor_axis = QComboBox()
        self.minor_axis.addItems(['both', 'x', 'y'])
        self.minor_axis.setCurrentText(self.grid_settings['minor_axis'])
        minor_layout.addWidget(self.minor_axis, 1, 1)

        minor_layout.addWidget(QLabel(tr("plot_design.grid.linestyle")), 2, 0)
        self.minor_linestyle = QComboBox()
        self.minor_linestyle.addItems(['solid', 'dashed', 'dotted', 'dashdot'])
        self.minor_linestyle.setCurrentText(self.grid_settings['minor_linestyle'])
        minor_layout.addWidget(self.minor_linestyle, 2, 1)

        minor_layout.addWidget(QLabel(tr("plot_design.grid.linewidth")), 3, 0)
        self.minor_linewidth = QDoubleSpinBox()
        self.minor_linewidth.setRange(0.1, 5.0)
        self.minor_linewidth.setSingleStep(0.1)
        self.minor_linewidth.setValue(self.grid_settings['minor_linewidth'])
        minor_layout.addWidget(self.minor_linewidth, 3, 1)

        minor_layout.addWidget(QLabel(tr("plot_design.grid.alpha")), 4, 0)
        self.minor_alpha = QDoubleSpinBox()
        self.minor_alpha.setRange(0.0, 1.0)
        self.minor_alpha.setSingleStep(0.05)
        self.minor_alpha.setDecimals(2)
        self.minor_alpha.setValue(self.grid_settings['minor_alpha'])
        minor_layout.addWidget(self.minor_alpha, 4, 1)

        minor_layout.addWidget(QLabel(tr("plot_design.grid.color")), 5, 0)
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
        family_layout.addWidget(QLabel(tr("plot_design.font.family")))
        self.font_family = QComboBox()
        self.font_family.addItems(['sans-serif', 'serif', 'monospace'])
        self.font_family.setCurrentText(self.font_settings.get('font_family', 'sans-serif'))
        family_layout.addWidget(self.font_family)
        layout.addLayout(family_layout)

        # Math Text
        self.use_math_text = QCheckBox(tr("plot_design.font.use_math_text"))
        self.use_math_text.setChecked(self.font_settings.get('use_math_text', False))
        layout.addWidget(self.use_math_text)

        # Titel
        title_group = QGroupBox(tr("plot_design.font.title"))
        title_layout = QGridLayout()

        title_layout.addWidget(QLabel(tr("plot_design.font.size")), 0, 0)
        self.title_size = QSpinBox()
        self.title_size.setRange(8, 32)
        self.title_size.setValue(self.font_settings.get('title_size', 14))
        title_layout.addWidget(self.title_size, 0, 1)

        self.title_bold = QCheckBox(tr("plot_design.font.bold"))
        self.title_bold.setChecked(self.font_settings.get('title_bold', True))
        title_layout.addWidget(self.title_bold, 1, 0)

        self.title_italic = QCheckBox(tr("plot_design.font.italic"))
        self.title_italic.setChecked(self.font_settings.get('title_italic', False))
        title_layout.addWidget(self.title_italic, 1, 1)

        title_group.setLayout(title_layout)
        layout.addWidget(title_group)

        # Labels
        labels_group = QGroupBox(tr("plot_design.font.labels"))
        labels_layout = QGridLayout()

        labels_layout.addWidget(QLabel(tr("plot_design.font.size")), 0, 0)
        self.labels_size = QSpinBox()
        self.labels_size.setRange(8, 32)
        self.labels_size.setValue(self.font_settings.get('labels_size', 12))
        labels_layout.addWidget(self.labels_size, 0, 1)

        self.labels_bold = QCheckBox(tr("plot_design.font.bold"))
        self.labels_bold.setChecked(self.font_settings.get('labels_bold', False))
        labels_layout.addWidget(self.labels_bold, 1, 0)

        self.labels_italic = QCheckBox(tr("plot_design.font.italic"))
        self.labels_italic.setChecked(self.font_settings.get('labels_italic', False))
        labels_layout.addWidget(self.labels_italic, 1, 1)

        labels_group.setLayout(labels_layout)
        layout.addWidget(labels_group)

        # Ticks
        ticks_group = QGroupBox(tr("plot_design.font.ticks"))
        ticks_layout = QGridLayout()

        ticks_layout.addWidget(QLabel(tr("plot_design.font.size")), 0, 0)
        self.ticks_size = QSpinBox()
        self.ticks_size.setRange(6, 24)
        self.ticks_size.setValue(self.font_settings.get('ticks_size', 10))
        ticks_layout.addWidget(self.ticks_size, 0, 1)

        self.ticks_bold = QCheckBox(tr("plot_design.font.bold"))
        self.ticks_bold.setChecked(self.font_settings.get('ticks_bold', False))
        ticks_layout.addWidget(self.ticks_bold, 1, 0)

        self.ticks_italic = QCheckBox(tr("plot_design.font.italic"))
        self.ticks_italic.setChecked(self.font_settings.get('ticks_italic', False))
        ticks_layout.addWidget(self.ticks_italic, 1, 1)

        ticks_group.setLayout(ticks_layout)
        layout.addWidget(ticks_group)

        # Legend Size
        legend_size_group = QGroupBox(tr("plot_design.font.legend"))
        legend_size_layout = QGridLayout()

        legend_size_layout.addWidget(QLabel(tr("plot_design.font.size")), 0, 0)
        self.legend_font_size = QSpinBox()
        self.legend_font_size.setRange(6, 24)
        self.legend_font_size.setValue(self.font_settings.get('legend_size', 10))
        legend_size_layout.addWidget(self.legend_font_size, 0, 1)

        self.legend_bold = QCheckBox(tr("plot_design.font.bold"))
        self.legend_bold.setChecked(self.font_settings.get('legend_bold', False))
        legend_size_layout.addWidget(self.legend_bold, 1, 0)

        self.legend_italic = QCheckBox(tr("plot_design.font.italic"))
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

        layout.addWidget(QLabel(tr("plot_design.legend.position")), 0, 0)
        self.legend_position = QComboBox()
        self.legend_position.addItems(['best', 'upper right', 'upper left', 'lower right', 'lower left',
                                       'center right', 'center left', 'upper center', 'lower center', 'center'])
        self.legend_position.setCurrentText(self.legend_settings.get('position', 'best'))
        layout.addWidget(self.legend_position, 0, 1)

        layout.addWidget(QLabel(tr("plot_design.legend.columns")), 1, 0)
        self.legend_ncol = QSpinBox()
        self.legend_ncol.setRange(1, 5)
        self.legend_ncol.setValue(self.legend_settings.get('ncol', 1))
        layout.addWidget(self.legend_ncol, 1, 1)

        layout.addWidget(QLabel(tr("plot_design.legend.alpha")), 2, 0)
        self.legend_alpha = QDoubleSpinBox()
        self.legend_alpha.setRange(0.0, 1.0)
        self.legend_alpha.setSingleStep(0.05)
        self.legend_alpha.setDecimals(2)
        self.legend_alpha.setValue(self.legend_settings.get('alpha', 0.9))
        layout.addWidget(self.legend_alpha, 2, 1)

        self.legend_frameon = QCheckBox(tr("plot_design.legend.show_frame"))
        self.legend_frameon.setChecked(self.legend_settings.get('frameon', True))
        layout.addWidget(self.legend_frameon, 3, 0, 1, 2)

        self.legend_shadow = QCheckBox(tr("plot_design.legend.shadow"))
        self.legend_shadow.setChecked(self.legend_settings.get('shadow', False))
        layout.addWidget(self.legend_shadow, 4, 0, 1, 2)

        self.legend_fancybox = QCheckBox(tr("plot_design.legend.rounded_corners"))
        self.legend_fancybox.setChecked(self.legend_settings.get('fancybox', True))
        layout.addWidget(self.legend_fancybox, 5, 0, 1, 2)

        layout.setRowStretch(6, 1)
        return tab

    def choose_major_color(self):
        """Wählt Farbe für Haupt-Grid"""
        color = QColorDialog.getColor(QColor(self.major_color), self, tr("plot_design.grid.choose_major_color"))
        if color.isValid():
            self.major_color = color.name()
            self.major_color_btn.setStyleSheet(f"background-color: {self.major_color}; border: 1px solid #555;")
            self.major_color_btn.setText(self.major_color)

    def choose_minor_color(self):
        """Wählt Farbe für Neben-Grid"""
        color = QColorDialog.getColor(QColor(self.minor_color), self, tr("plot_design.grid.choose_minor_color"))
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
                QMessageBox.critical(self, tr("design_manager.error"), tr("plot_design.name_required"))
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
            QMessageBox.information(self, tr("design_manager.success"),
                tr("plot_design.default_overwritten", name=new_name))
        else:
            QMessageBox.information(self, tr("design_manager.success"), tr("plot_design.saved", name=new_name))

        self.accept()
