"""
Export Settings Dialog with Live Preview

This dialog provides advanced export settings with:
- Live preview of the exported plot
- Preset system for common export scenarios
- Metadata editor
- Advanced format-specific options
"""

import io
import json
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox,
    QDialogButtonBox, QLineEdit, QSplitter, QScrollArea,
    QWidget, QFrame, QPushButton, QToolButton, QTextEdit,
    QColorDialog, QListWidget, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtGui import QPixmap, QImage
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from i18n import tr


class CollapsibleSection(QWidget):
    """Collapsible section widget for accordion-style UI"""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.is_expanded = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header button
        self.toggle_button = QToolButton()
        self.toggle_button.setText(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.setStyleSheet("""
            QToolButton {
                border: none;
                background: palette(alternate-base);
                padding: 8px;
                text-align: left;
                font-weight: bold;
                color: palette(text);
            }
            QToolButton:hover {
                background: palette(mid);
            }
            QToolButton::indicator {
                width: 0px;
            }
        """)
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.RightArrow)
        self.toggle_button.clicked.connect(self.toggle)

        # Content area
        self.content_area = QFrame()
        self.content_area.setFrameShape(QFrame.StyledPanel)
        self.content_area.setMaximumHeight(0)
        self.content_area.setMinimumHeight(0)

        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(10, 10, 10, 10)

        layout.addWidget(self.toggle_button)
        layout.addWidget(self.content_area)

    def toggle(self):
        """Toggle section open/closed"""
        self.is_expanded = not self.is_expanded

        if self.is_expanded:
            self.toggle_button.setArrowType(Qt.DownArrow)
            self.content_area.setMaximumHeight(16777215)  # Max height
        else:
            self.toggle_button.setArrowType(Qt.RightArrow)
            self.content_area.setMaximumHeight(0)

    def set_expanded(self, expanded):
        """Set expanded state"""
        if expanded != self.is_expanded:
            self.toggle()

    def add_widget(self, widget):
        """Add widget to content area"""
        self.content_layout.addWidget(widget)

    def add_layout(self, layout):
        """Add layout to content area"""
        self.content_layout.addLayout(layout)


class ExportPreview(QWidget):
    """Preview widget showing how the export will look"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel(tr("export.preview")))
        toolbar.addStretch()

        self.zoom_combo = QComboBox()
        self.zoom_combo.addItems(["25%", "50%", "75%", "100%", "150%", "200%", tr("export.zoom_fit")])
        self.zoom_combo.setCurrentText("100%")
        toolbar.addWidget(QLabel(tr("export.zoom")))
        toolbar.addWidget(self.zoom_combo)

        layout.addLayout(toolbar)

        # Scroll area for preview
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.StyledPanel)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("background: white; border: 1px solid #ccc;")
        self.preview_label.setText(tr("export.loading_preview"))

        scroll.setWidget(self.preview_label)
        layout.addWidget(scroll)

        # File size info
        self.size_label = QLabel(tr("export.estimated_size_default"))
        self.size_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.size_label)

    def update_preview(self, fig, settings):
        """Update preview with current settings"""
        try:
            # Render the actual figure with export settings
            buf = io.BytesIO()

            # Store original size
            original_size = fig.get_size_inches()

            # Temporarily set export size
            fig.set_size_inches(settings['width'], settings['height'])

            # Build save parameters
            save_kwargs = {
                'format': 'png',
                'dpi': min(settings.get('dpi', 100), 150),  # Limit preview DPI
                'bbox_inches': 'tight' if settings.get('tight_layout') else None
            }

            # Apply transparency and background
            if settings.get('transparent', False):
                save_kwargs['transparent'] = True
            else:
                save_kwargs['facecolor'] = settings.get('bg_color', 'white')

            # Render to buffer
            fig.savefig(buf, **save_kwargs)
            buf.seek(0)

            # Restore original size
            fig.set_size_inches(original_size)

            # Load and display image
            qimage = QImage.fromData(buf.getvalue())
            pixmap = QPixmap.fromImage(qimage)

            # Apply zoom
            zoom_text = self.zoom_combo.currentText()
            if zoom_text != tr("export.zoom_fit"):
                zoom = int(zoom_text.replace('%', '')) / 100.0
                scaled_pixmap = pixmap.scaled(
                    pixmap.size() * zoom,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled_pixmap)
            else:
                # Fit to widget
                self.preview_label.setPixmap(pixmap)
                self.preview_label.setScaledContents(True)

            # Estimate file size (extrapolate from preview to actual DPI)
            preview_bytes = len(buf.getvalue())
            actual_dpi = settings.get('dpi', 300)
            preview_dpi = min(actual_dpi, 150)

            # Size scales roughly with (DPI ratio)^2 for raster formats
            if settings.get('format', 'PNG') == 'PNG':
                dpi_factor = (actual_dpi / preview_dpi) ** 2
                estimated_bytes = int(preview_bytes * dpi_factor)
            elif settings.get('format', 'PNG') == 'SVG':
                # SVG is usually much smaller and DPI-independent
                estimated_bytes = preview_bytes // 2
            else:
                # PDF/EPS
                estimated_bytes = preview_bytes * 2

            if estimated_bytes < 1024:
                size_str = f"{estimated_bytes} B"
            elif estimated_bytes < 1024 * 1024:
                size_str = f"{estimated_bytes / 1024:.1f} KB"
            else:
                size_str = f"{estimated_bytes / (1024 * 1024):.2f} MB"

            self.size_label.setText(tr("export.estimated_size", size=size_str))

        except Exception as e:
            self.preview_label.setText(tr("export.preview_error", error=str(e)))
            self.size_label.setText(tr("export.estimated_size_default"))


class ExportSettingsDialog(QDialog):
    """Advanced Export Settings Dialog with Live Preview"""

    # Built-in presets
    PRESETS = {
        'Publikation': {
            'format': 'PDF',
            'dpi': 600,
            'width': 8.5,  # inches (A4 width in landscape ~8.27)
            'height': 6.0,
            'transparent': False,
            'tight_layout': True,
            'facecolor_white': True,
            'embed_fonts': True,
            'pdf_version': '1.5'
        },
        'Präsentation': {
            'format': 'PNG',
            'dpi': 150,
            'width': 10.0,  # 16:10
            'height': 6.25,
            'transparent': True,
            'tight_layout': True,
            'facecolor_white': False,
            'png_compression': 6
        },
        'Web': {
            'format': 'PNG',
            'dpi': 96,
            'width': 8.0,
            'height': 6.0,
            'transparent': False,
            'tight_layout': True,
            'facecolor_white': True,
            'png_compression': 9
        },
        'Druck': {
            'format': 'PDF',
            'dpi': 600,
            'width': 8.27,  # A4 landscape
            'height': 11.69,
            'transparent': False,
            'tight_layout': False,
            'facecolor_white': True,
            'embed_fonts': True
        }
    }

    # Size presets (name: (width_cm, height_cm))
    SIZE_PRESETS = {
        'Benutzerdefiniert': None,
        'A4 Querformat': (29.7, 21.0),
        'A4 Hochformat': (21.0, 29.7),
        'A5 Querformat': (21.0, 14.8),
        'A5 Hochformat': (14.8, 21.0),
        'Slide 16:9': (25.4, 14.29),
        'Slide 16:10': (25.4, 15.875),
        'Slide 4:3': (25.4, 19.05),
    }

    def __init__(self, parent, export_settings, main_figure=None):
        super().__init__(parent)
        self.setWindowTitle(tr("export.title"))
        self.resize(1200, 700)

        self.export_settings = export_settings.copy()
        self.main_figure = main_figure
        self.user_presets = self.load_user_presets()

        self.init_ui()
        self.connect_signals()
        self.update_preview()

    def init_ui(self):
        """Initialize user interface"""
        main_layout = QVBoxLayout(self)

        # Create splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left side: Settings
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(350)

        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)

        # Presets section (always visible)
        settings_layout.addWidget(self.create_presets_section())

        # Accordion sections
        self.format_section = self.create_format_section()
        self.format_section.set_expanded(True)  # Open by default
        settings_layout.addWidget(self.format_section)

        self.layout_section = self.create_layout_section()
        settings_layout.addWidget(self.layout_section)

        self.metadata_section = self.create_metadata_section()
        settings_layout.addWidget(self.metadata_section)

        self.advanced_section = self.create_advanced_section()
        settings_layout.addWidget(self.advanced_section)

        settings_layout.addStretch()

        scroll.setWidget(settings_widget)
        left_layout.addWidget(scroll)

        # Bottom buttons for left side
        left_buttons = QHBoxLayout()
        self.save_preset_btn = QPushButton(tr("export.save_preset"))
        self.save_preset_btn.clicked.connect(self.save_custom_preset)
        left_buttons.addWidget(self.save_preset_btn)
        left_buttons.addStretch()
        left_layout.addLayout(left_buttons)

        splitter.addWidget(left_widget)

        # Right side: Preview
        self.preview_widget = ExportPreview()
        self.preview_widget.setMinimumWidth(400)
        splitter.addWidget(self.preview_widget)

        # Set splitter sizes (30% settings, 70% preview)
        splitter.setSizes([350, 850])

        main_layout.addWidget(splitter)

        # Bottom dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.button(QDialogButtonBox.Ok).setText(tr("export.export_button"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

    def create_presets_section(self):
        """Create presets selection section"""
        group = QGroupBox(tr("export.presets.title"))
        layout = QVBoxLayout()

        self.preset_combo = QComboBox()
        self.preset_combo.addItem(tr("export.presets.custom"))
        for preset_name in self.PRESETS.keys():
            self.preset_combo.addItem(tr(f"export.presets.{preset_name.lower()}"))

        # Add user presets
        if self.user_presets:
            self.preset_combo.insertSeparator(self.preset_combo.count())
            for user_preset in self.user_presets.keys():
                self.preset_combo.addItem(f"★ {user_preset}")

        self.preset_combo.currentTextChanged.connect(self.apply_preset)
        layout.addWidget(self.preset_combo)

        group.setLayout(layout)
        return group

    def create_format_section(self):
        """Create format and size section"""
        section = CollapsibleSection(tr("export.format_size.title"))

        grid = QGridLayout()
        row = 0

        # Format
        grid.addWidget(QLabel(tr("export.format_size.format")), row, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(['PNG', 'SVG', 'PDF', 'EPS'])
        current_format = self.export_settings.get('format', 'PNG')
        index = self.format_combo.findText(current_format)
        if index >= 0:
            self.format_combo.setCurrentIndex(index)
        grid.addWidget(self.format_combo, row, 1)
        row += 1

        # DPI
        grid.addWidget(QLabel(tr("export.format_size.dpi")), row, 0)
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 1200)
        self.dpi_spin.setSingleStep(50)
        self.dpi_spin.setValue(self.export_settings.get('dpi', 300))
        grid.addWidget(self.dpi_spin, row, 1)
        row += 1

        # Size presets
        grid.addWidget(QLabel(tr("export.format_size.size_preset")), row, 0)
        self.size_preset_combo = QComboBox()
        for preset_name in self.SIZE_PRESETS.keys():
            self.size_preset_combo.addItem(tr(f"export.format_size.{preset_name.lower().replace(' ', '_').replace(':', '_')}"))
        self.size_preset_combo.currentTextChanged.connect(self.apply_size_preset)
        grid.addWidget(self.size_preset_combo, row, 1)
        row += 1

        # Width
        grid.addWidget(QLabel(tr("export.format_size.width")), row, 0)
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(2.5, 127.0)
        self.width_spin.setSingleStep(1.0)
        self.width_spin.setValue(self.export_settings.get('width', 10.0) * 2.54)
        self.width_spin.setSuffix(" cm")
        self.width_spin.setDecimals(1)
        grid.addWidget(self.width_spin, row, 1)
        row += 1

        # Height
        grid.addWidget(QLabel(tr("export.format_size.height")), row, 0)
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(2.5, 127.0)
        self.height_spin.setSingleStep(1.0)
        self.height_spin.setValue(self.export_settings.get('height', 6.25) * 2.54)
        self.height_spin.setSuffix(" cm")
        self.height_spin.setDecimals(1)
        grid.addWidget(self.height_spin, row, 1)
        row += 1

        # Keep aspect ratio
        self.keep_aspect = QCheckBox(tr("export.format_size.keep_aspect"))
        self.keep_aspect.setChecked(self.export_settings.get('keep_aspect', True))
        grid.addWidget(self.keep_aspect, row, 0, 1, 2)

        section.add_layout(grid)
        return section

    def create_layout_section(self):
        """Create layout options section"""
        section = CollapsibleSection(tr("export.layout.title"))

        layout = QVBoxLayout()

        self.transparent_bg = QCheckBox(tr("export.layout.transparent"))
        self.transparent_bg.setChecked(self.export_settings.get('transparent', False))
        layout.addWidget(self.transparent_bg)

        self.tight_layout = QCheckBox(tr("export.layout.tight_layout"))
        self.tight_layout.setChecked(self.export_settings.get('tight_layout', True))
        layout.addWidget(self.tight_layout)

        # Background color
        bg_layout = QHBoxLayout()
        bg_layout.addWidget(QLabel(tr("export.layout.bg_color")))
        self.bg_color_btn = QPushButton(tr("export.layout.choose_color"))
        self.bg_color_btn.clicked.connect(self.choose_bg_color)
        self.current_bg_color = self.export_settings.get('bg_color', '#FFFFFF')
        self.bg_color_btn.setStyleSheet(f"background-color: {self.current_bg_color};")
        bg_layout.addWidget(self.bg_color_btn)
        bg_layout.addStretch()
        layout.addLayout(bg_layout)

        section.add_layout(layout)
        return section

    def create_metadata_section(self):
        """Create metadata editor section"""
        section = CollapsibleSection(tr("export.metadata.title"))

        grid = QGridLayout()
        row = 0

        # Title
        grid.addWidget(QLabel(tr("export.metadata.doc_title")), row, 0)
        self.meta_title = QLineEdit()
        self.meta_title.setText(self.export_settings.get('meta_title', ''))
        self.meta_title.setPlaceholderText(tr("export.metadata.doc_title_placeholder"))
        grid.addWidget(self.meta_title, row, 1)
        row += 1

        # Author
        grid.addWidget(QLabel(tr("export.metadata.author")), row, 0)
        self.meta_author = QLineEdit()
        self.meta_author.setText(self.export_settings.get('meta_author', ''))
        self.meta_author.setPlaceholderText(tr("export.metadata.author_placeholder"))
        grid.addWidget(self.meta_author, row, 1)
        row += 1

        # Subject
        grid.addWidget(QLabel(tr("export.metadata.description")), row, 0)
        self.meta_subject = QLineEdit()
        self.meta_subject.setText(self.export_settings.get('meta_subject', ''))
        self.meta_subject.setPlaceholderText(tr("export.metadata.description_placeholder"))
        grid.addWidget(self.meta_subject, row, 1)
        row += 1

        # Keywords
        grid.addWidget(QLabel(tr("export.metadata.keywords")), row, 0)
        self.meta_keywords = QLineEdit()
        self.meta_keywords.setText(self.export_settings.get('meta_keywords', ''))
        self.meta_keywords.setPlaceholderText(tr("export.metadata.keywords_placeholder"))
        grid.addWidget(self.meta_keywords, row, 1)
        row += 1

        # Copyright
        grid.addWidget(QLabel(tr("export.metadata.copyright")), row, 0)
        self.meta_copyright = QLineEdit()
        self.meta_copyright.setText(self.export_settings.get('meta_copyright', ''))
        self.meta_copyright.setPlaceholderText(tr("export.metadata.copyright_placeholder"))
        grid.addWidget(self.meta_copyright, row, 1)

        section.add_layout(grid)
        return section

    def create_advanced_section(self):
        """Create advanced format-specific options section"""
        section = CollapsibleSection(tr("export.advanced.title"))

        layout = QVBoxLayout()

        # PDF options
        self.pdf_group = QGroupBox(tr("export.advanced.pdf_options"))
        pdf_layout = QVBoxLayout()

        self.embed_fonts = QCheckBox(tr("export.advanced.embed_fonts"))
        self.embed_fonts.setChecked(self.export_settings.get('embed_fonts', True))
        pdf_layout.addWidget(self.embed_fonts)

        pdf_version_layout = QHBoxLayout()
        pdf_version_layout.addWidget(QLabel(tr("export.advanced.pdf_version")))
        self.pdf_version_combo = QComboBox()
        self.pdf_version_combo.addItems(['1.4', '1.5', '1.6', '1.7'])
        self.pdf_version_combo.setCurrentText(self.export_settings.get('pdf_version', '1.5'))
        pdf_version_layout.addWidget(self.pdf_version_combo)
        pdf_version_layout.addStretch()
        pdf_layout.addLayout(pdf_version_layout)

        self.pdf_group.setLayout(pdf_layout)
        layout.addWidget(self.pdf_group)

        # PNG options
        self.png_group = QGroupBox(tr("export.advanced.png_options"))
        png_layout = QVBoxLayout()

        compression_layout = QHBoxLayout()
        compression_layout.addWidget(QLabel(tr("export.advanced.png_compression")))
        self.png_compression = QSpinBox()
        self.png_compression.setRange(0, 9)
        self.png_compression.setValue(self.export_settings.get('png_compression', 6))
        compression_layout.addWidget(self.png_compression)
        compression_layout.addStretch()
        png_layout.addLayout(compression_layout)

        self.png_group.setLayout(png_layout)
        layout.addWidget(self.png_group)

        # SVG options
        self.svg_group = QGroupBox(tr("export.advanced.svg_options"))
        svg_layout = QVBoxLayout()

        self.svg_text_as_path = QCheckBox(tr("export.advanced.svg_text_as_path"))
        self.svg_text_as_path.setChecked(self.export_settings.get('svg_text_as_path', False))
        svg_layout.addWidget(self.svg_text_as_path)

        self.svg_group.setLayout(svg_layout)
        layout.addWidget(self.svg_group)

        section.add_layout(layout)
        return section

    def connect_signals(self):
        """Connect all signals for live preview update"""
        # Format & Size
        self.format_combo.currentTextChanged.connect(self.on_settings_changed)
        self.dpi_spin.valueChanged.connect(self.on_settings_changed)
        self.width_spin.valueChanged.connect(self.on_width_changed)
        self.height_spin.valueChanged.connect(self.on_height_changed)
        self.keep_aspect.stateChanged.connect(self.on_settings_changed)

        # Layout
        self.transparent_bg.stateChanged.connect(self.on_settings_changed)
        self.tight_layout.stateChanged.connect(self.on_settings_changed)

        # Preview zoom
        self.preview_widget.zoom_combo.currentTextChanged.connect(self.update_preview)

    def on_width_changed(self):
        """Handle width change with aspect ratio lock"""
        if self.keep_aspect.isChecked() and hasattr(self, '_aspect_ratio'):
            new_height = self.width_spin.value() / self._aspect_ratio
            self.height_spin.blockSignals(True)
            self.height_spin.setValue(new_height)
            self.height_spin.blockSignals(False)
        else:
            self._aspect_ratio = self.width_spin.value() / self.height_spin.value()
        self.on_settings_changed()

    def on_height_changed(self):
        """Handle height change with aspect ratio lock"""
        if self.keep_aspect.isChecked() and hasattr(self, '_aspect_ratio'):
            new_width = self.height_spin.value() * self._aspect_ratio
            self.width_spin.blockSignals(True)
            self.width_spin.setValue(new_width)
            self.width_spin.blockSignals(False)
        else:
            self._aspect_ratio = self.width_spin.value() / self.height_spin.value()
        self.on_settings_changed()

    def on_settings_changed(self):
        """Handle any settings change"""
        # Update format-specific visibility
        format_type = self.format_combo.currentText()
        self.pdf_group.setVisible(format_type == 'PDF')
        self.png_group.setVisible(format_type == 'PNG')
        self.svg_group.setVisible(format_type == 'SVG')

        # Update size preset to custom if manual changes
        if self.sender() in [self.width_spin, self.height_spin]:
            self.size_preset_combo.blockSignals(True)
            self.size_preset_combo.setCurrentIndex(0)  # First item is always custom
            self.size_preset_combo.blockSignals(False)

        self.update_preview()

    def apply_preset(self, preset_name):
        """Apply a preset configuration"""
        if preset_name == tr("export.presets.custom"):
            return

        # Check if it's a user preset
        if preset_name.startswith("★ "):
            preset_name = preset_name[2:]  # Remove star
            preset = self.user_presets.get(preset_name)
        else:
            # Reverse lookup: find the original English key
            preset_mapping = {
                tr("export.presets.publikation"): "Publikation",
                tr("export.presets.präsentation"): "Präsentation",
                tr("export.presets.web"): "Web",
                tr("export.presets.druck"): "Druck"
            }
            preset_key = preset_mapping.get(preset_name)
            preset = self.PRESETS.get(preset_key) if preset_key else None

        if not preset:
            return

        # Block signals during update
        self.blockSignals(True)

        # Apply settings
        self.format_combo.setCurrentText(preset.get('format', 'PNG'))
        self.dpi_spin.setValue(preset.get('dpi', 300))
        self.width_spin.setValue(preset.get('width', 10.0) * 2.54)
        self.height_spin.setValue(preset.get('height', 6.25) * 2.54)
        self.transparent_bg.setChecked(preset.get('transparent', False))
        self.tight_layout.setChecked(preset.get('tight_layout', True))

        # Advanced options
        if 'embed_fonts' in preset:
            self.embed_fonts.setChecked(preset['embed_fonts'])
        if 'pdf_version' in preset:
            self.pdf_version_combo.setCurrentText(preset['pdf_version'])
        if 'png_compression' in preset:
            self.png_compression.setValue(preset['png_compression'])

        self.blockSignals(False)
        self.on_settings_changed()

    def apply_size_preset(self, preset_name):
        """Apply a size preset"""
        # First item is always custom/benutzerdefiniert
        if self.size_preset_combo.currentIndex() == 0:
            return

        # Reverse lookup: map translated names back to original keys
        size_mapping = {
            tr("export.format_size.benutzerdefiniert"): "Benutzerdefiniert",
            tr("export.format_size.a4_querformat"): "A4 Querformat",
            tr("export.format_size.a4_hochformat"): "A4 Hochformat",
            tr("export.format_size.a5_querformat"): "A5 Querformat",
            tr("export.format_size.a5_hochformat"): "A5 Hochformat",
            tr("export.format_size.slide_16_9"): "Slide 16:9",
            tr("export.format_size.slide_16_10"): "Slide 16:10",
            tr("export.format_size.slide_4_3"): "Slide 4:3",
        }
        preset_key = size_mapping.get(preset_name)
        size = self.SIZE_PRESETS.get(preset_key)
        if size:
            width_cm, height_cm = size
            self.width_spin.blockSignals(True)
            self.height_spin.blockSignals(True)
            self.width_spin.setValue(width_cm)
            self.height_spin.setValue(height_cm)
            self.width_spin.blockSignals(False)
            self.height_spin.blockSignals(False)
            self._aspect_ratio = width_cm / height_cm
            self.on_settings_changed()

    def choose_bg_color(self):
        """Open color picker for background color"""
        from PySide6.QtGui import QColor
        current_color = QColor(self.current_bg_color)
        color = QColorDialog.getColor(current_color, self, tr("export.layout.choose_bg_color"))
        if color.isValid():
            self.current_bg_color = color.name()
            self.bg_color_btn.setStyleSheet(f"background-color: {self.current_bg_color};")
            self.on_settings_changed()

    def update_preview(self):
        """Update the live preview"""
        settings = self.get_current_settings()

        # If we have the main figure, use it; otherwise create dummy
        if self.main_figure:
            self.preview_widget.update_preview(self.main_figure, settings)
            # Force redraw of parent canvas if it exists
            try:
                if hasattr(self.parent(), 'canvas'):
                    self.parent().canvas.draw_idle()
            except:
                pass
        else:
            # Create a dummy figure for preview
            fig = Figure(figsize=(settings['width'], settings['height']))
            ax = fig.add_subplot(111)
            ax.plot([0, 1], [0, 1], 'b-')
            ax.set_xlabel(tr("export.preview_x_axis"))
            ax.set_ylabel(tr("export.preview_y_axis"))
            ax.set_title(tr("export.preview_title"))
            self.preview_widget.update_preview(fig, settings)
            plt.close(fig)

    def get_current_settings(self):
        """Get current settings from UI"""
        return {
            'format': self.format_combo.currentText(),
            'dpi': self.dpi_spin.value(),
            'width': self.width_spin.value() / 2.54,  # cm → inch
            'height': self.height_spin.value() / 2.54,  # cm → inch
            'keep_aspect': self.keep_aspect.isChecked(),
            'transparent': self.transparent_bg.isChecked(),
            'tight_layout': self.tight_layout.isChecked(),
            'bg_color': self.current_bg_color,
            # Metadata
            'meta_title': self.meta_title.text(),
            'meta_author': self.meta_author.text(),
            'meta_subject': self.meta_subject.text(),
            'meta_keywords': self.meta_keywords.text(),
            'meta_copyright': self.meta_copyright.text(),
            # Advanced
            'embed_fonts': self.embed_fonts.isChecked(),
            'pdf_version': self.pdf_version_combo.currentText(),
            'png_compression': self.png_compression.value(),
            'svg_text_as_path': self.svg_text_as_path.isChecked(),
        }

    def get_settings(self):
        """Get settings for export (backward compatibility)"""
        return self.get_current_settings()

    def save_custom_preset(self):
        """Save current settings as a custom preset"""
        from PySide6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(
            self,
            tr("export.save_preset_dialog_title"),
            tr("export.save_preset_dialog_prompt")
        )

        if ok and name:
            self.user_presets[name] = self.get_current_settings()
            self.save_user_presets()

            # Update preset combo
            if not any(name in self.preset_combo.itemText(i) for i in range(self.preset_combo.count())):
                if self.preset_combo.findText("-- Separator --") == -1:
                    self.preset_combo.insertSeparator(self.preset_combo.count())
                self.preset_combo.addItem(f"★ {name}")

            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, tr("export.preset_saved_title"),
                                   tr("export.preset_saved_message", name=name))

    def load_user_presets(self):
        """Load user-defined presets from file"""
        presets_file = Path.home() / '.scatterforge' / 'export_presets.json'
        if presets_file.exists():
            try:
                with open(presets_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def save_user_presets(self):
        """Save user-defined presets to file"""
        presets_dir = Path.home() / '.scatterforge'
        presets_dir.mkdir(exist_ok=True)
        presets_file = presets_dir / 'export_presets.json'

        with open(presets_file, 'w') as f:
            json.dump(self.user_presets, f, indent=2)
