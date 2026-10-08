"""
Hilfsfunktionen für Dialoge, die auf kleinen Bildschirmen nutzbar bleiben müssen (v8.1.1).

- fit_to_screen: begrenzt die Startgröße auf den verfügbaren Bildschirmbereich
- scrollable_layout: Inhalt-Layout in einer Scroll-Area, Buttons bleiben sichtbar
- scroll_wrap: verpackt ein Widget (z. B. einen Tab-Inhalt) in eine Scroll-Area
"""

from PySide6.QtWidgets import QVBoxLayout, QWidget, QScrollArea, QFrame
from PySide6.QtGui import QGuiApplication


def fit_to_screen(dialog, width, height):
    """Setzt die Dialoggröße, begrenzt auf ~90 % des verfügbaren Bildschirms."""
    screen = dialog.screen() or QGuiApplication.primaryScreen()
    if screen is not None:
        avail = screen.availableGeometry()
        width = min(width, int(avail.width() * 0.9))
        height = min(height, int(avail.height() * 0.9))
    dialog.resize(width, height)


def scroll_wrap(widget):
    """Packt ein Widget in eine Scroll-Area ohne Rahmen und gibt diese zurück."""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setWidget(widget)
    return scroll


def render_text_pixmap(text, fontsize=10, fontfamily='sans-serif', dpi=110):
    """Rendert Text (inkl. MathText) mit Matplotlib als QPixmap – exakt so, wie er
    im Plot erscheint.

    Returns:
        (QPixmap oder None, Fehlermeldung oder None)
    """
    from io import BytesIO
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from PySide6.QtGui import QPixmap

    fig = Figure(dpi=dpi)
    FigureCanvasAgg(fig)
    fig.text(0, 0, text, fontsize=fontsize, fontfamily=fontfamily)
    buf = BytesIO()
    try:
        fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.06,
                    facecolor='white')
    except Exception as e:  # MathText-Syntaxfehler
        lines = [l for l in str(e).splitlines() if l.strip()]
        return None, lines[-1] if lines else str(e)
    pixmap = QPixmap()
    pixmap.loadFromData(buf.getvalue(), 'PNG')
    return pixmap, None


def scrollable_layout(dialog):
    """Richtet `dialog` mit scrollbarem Inhaltsbereich ein.

    Returns:
        (content_layout, outer_layout): Inhalte kommen in `content_layout`,
        der Button-Kasten in `outer_layout` (bleibt außerhalb des Scrollbereichs).
    """
    outer = QVBoxLayout(dialog)
    content = QWidget()
    outer.addWidget(scroll_wrap(content))
    return QVBoxLayout(content), outer
