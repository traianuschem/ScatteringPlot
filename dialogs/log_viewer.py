"""
Log Viewer Dialog

Zeigt Debug-Logs in einem separaten Fenster an.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class LogViewerDialog(QDialog):
    """Dialog zum Anzeigen von Debug-Logs"""

    def __init__(self, parent, log_buffer):
        super().__init__(parent)
        self.log_buffer = log_buffer
        self.setWindowTitle("Debug-Log Viewer")
        self.resize(800, 600)

        layout = QVBoxLayout(self)

        # Info-Label
        info_label = QLabel(
            "Debug-Informationen für Gruppen, Stacking und Plot-Updates.\n"
            "Das Log wird bei jedem Plot-Update aktualisiert."
        )
        info_label.setStyleSheet("font-style: italic; color: #888; padding: 5px;")
        layout.addWidget(info_label)

        # Text-Widget für Log-Anzeige
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.NoWrap)

        # Monospace Font für bessere Lesbarkeit
        font = QFont("Courier New", 9)
        font.setStyleHint(QFont.Monospace)
        self.log_text.setFont(font)

        layout.addWidget(self.log_text)

        # Buttons
        btn_layout = QHBoxLayout()

        refresh_btn = QPushButton("Aktualisieren")
        refresh_btn.clicked.connect(self.refresh_log)
        btn_layout.addWidget(refresh_btn)

        clear_btn = QPushButton("Log leeren")
        clear_btn.clicked.connect(self.clear_log)
        btn_layout.addWidget(clear_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("Schließen")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        # Initial befüllen
        self.refresh_log()

    def refresh_log(self):
        """Aktualisiert Log-Anzeige"""
        self.log_text.setPlainText(self.log_buffer.get_content())
        # Scrolle nach unten
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.End)
        self.log_text.setTextCursor(cursor)

    def clear_log(self):
        """Leert das Log"""
        self.log_buffer.clear()
        self.log_text.clear()


class LogBuffer:
    """Buffer für Log-Nachrichten"""

    def __init__(self):
        self.lines = []
        self.max_lines = 10000  # Maximal 10000 Zeilen speichern

    def write(self, line):
        """Schreibt eine Zeile in den Buffer"""
        self.lines.append(line)
        # Begrenze Anzahl der Zeilen
        if len(self.lines) > self.max_lines:
            self.lines = self.lines[-self.max_lines:]

    def get_content(self):
        """Gibt gesamten Inhalt zurück"""
        return '\n'.join(self.lines)

    def clear(self):
        """Leert den Buffer"""
        self.lines = []
