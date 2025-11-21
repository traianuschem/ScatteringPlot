"""
MathText Formatter

Provides utilities for formatting text with LaTeX-style syntax for use in Matplotlib.
Converts simple Markdown-like syntax to Matplotlib MathText formatting.

Version: 7.0
"""

import re


def preprocess_mathtext(text):
    """
    Konvertiert einfache Formatierungssyntax in MathText-Format.

    Unterstützt:
    - **text** → Fettdruck ($\mathbf{text}$)
    - *text* → Kursiv ($\mathit{text}$)
    - Bereits vorhandenes MathText bleibt unverändert ($...$)

    Args:
        text (str): Input-Text mit einfacher Formatierung

    Returns:
        str: MathText-formatierter String

    Examples:
        >>> preprocess_mathtext("**Messung** mit $\\alpha$")
        '$\\mathbf{Messung}$ mit $\\alpha$'

        >>> preprocess_mathtext("*Fit* für $q^2$")
        '$\\mathit{Fit}$ für $q^2$'

        >>> preprocess_mathtext("Normale Messung")
        'Normale Messung'
    """
    if not text:
        return text

    # Schritt 1: Bestehende $...$ Bereiche schützen (temporär ersetzen)
    # Um zu vermeiden, dass wir in bereits formatierten MathText-Bereichen arbeiten
    protected_regions = []

    def protect_mathtext(match):
        """Temporäre Ersetzung für bereits vorhandenes MathText"""
        protected_regions.append(match.group(0))
        return f"__MATHTEXT_{len(protected_regions)-1}__"

    # Schütze $...$ Bereiche
    text = re.sub(r'\$[^$]+\$', protect_mathtext, text)

    # Schritt 2: Formatierung konvertieren
    # **text** → $\mathbf{text}$
    text = re.sub(r'\*\*([^*]+)\*\*', r'$\\mathbf{\1}$', text)

    # *text* → $\mathit{text}$ (nur wenn nicht bereits ** ersetzt wurde)
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'$\\mathit{\1}$', text)

    # Schritt 3: Geschützte Bereiche wiederherstellen
    for i, region in enumerate(protected_regions):
        text = text.replace(f"__MATHTEXT_{i}__", region)

    # Schritt 4: Benachbarte $...$ $...$ zusammenführen für bessere Lesbarkeit
    # $\mathbf{A}$ $\mathit{B}$ → $\mathbf{A}$ $\mathit{B}$ (bleibt so)
    # Aber: "text$" "$more" → "text$ $more" ist OK

    return text


def format_legend_text(text, bold=False, italic=False):
    """
    Formatiert Text für Legenden-Einträge mit MathText.

    Kombiniert die Formatierungs-Flags (bold/italic) aus dem Legenden-Editor
    mit eventuellem MathText im Text selbst.

    Args:
        text (str): Der zu formatierende Text
        bold (bool): Ob der gesamte Text fett sein soll
        italic (bool): Ob der gesamte Text kursiv sein soll

    Returns:
        str: Formatierter MathText-String

    Examples:
        >>> format_legend_text("Messung", bold=True)
        '$\\mathbf{Messung}$'

        >>> format_legend_text("**Messung** mit $\\alpha$", bold=False)
        '$\\mathbf{Messung}$ mit $\\alpha$'
    """
    if not text:
        return text

    # Zuerst Preprocessing für **/** Syntax
    processed = preprocess_mathtext(text)

    # Wenn bold/italic-Flags gesetzt sind und der Text noch kein MathText ist,
    # den gesamten Text einpacken
    if (bold or italic) and not processed.strip().startswith('$'):
        # Text ist nicht bereits vollständig in MathText
        # Prüfe ob es Teile mit MathText gibt
        if '$' in processed:
            # Es gibt bereits MathText-Teile - nur die nicht-formatierten Teile einpacken
            # Dies ist komplexer - für jetzt: wenn der User bold/italic im Editor setzt,
            # sollte er ** oder * im Text selbst verwenden
            pass
        else:
            # Kein MathText vorhanden - gesamten Text formatieren
            if bold and italic:
                processed = f"$\\mathbf{{\\mathit{{{processed}}}}}$"
            elif bold:
                processed = f"$\\mathbf{{{processed}}}$"
            elif italic:
                processed = f"$\\mathit{{{processed}}}$"

    return processed


def get_syntax_help_text():
    """
    Gibt einen Hilfe-Text für die MathText-Syntax zurück.

    Returns:
        str: Formatierter Hilfe-Text für Dialoge
    """
    return """<b>LaTeX/MathText Formatierung:</b><br><br>

<b>Einfache Formatierung:</b><br>
• <code>**Text**</code> → <b>Fettdruck</b><br>
• <code>*Text*</code> → <i>Kursiv</i><br><br>

<b>Mathematische Symbole:</b><br>
• <code>$\\alpha$, $\\beta$, $\\gamma$</code> → α, β, γ<br>
• <code>$q^2$</code> → q² (Hochgestellt)<br>
• <code>$H_2O$</code> → H₂O (Tiefgestellt)<br>
• <code>$\\pm$</code> → ± (Plus-Minus)<br>
• <code>$\\times$</code> → × (Mal)<br>
• <code>$\\cdot$</code> → · (Punkt)<br><br>

<b>Kombinationen:</b><br>
• <code>**Messung** mit $\\alpha$</code><br>
• <code>*Fit* für $q^2$</code><br>
• <code>$I \\cdot q^4$ (**Porod**)</code><br><br>

<b>Hinweis:</b> Sie können die Checkboxen "Fett" und "Kursiv" verwenden,<br>
oder direkt ** und * im Text. Für mehr Kontrolle verwenden Sie die<br>
Syntax im Text selbst.
"""


def strip_mathtext_formatting(text):
    """
    Entfernt MathText-Formatierung aus einem String (für Vergleiche, etc.).

    Args:
        text (str): Text mit MathText-Formatierung

    Returns:
        str: Text ohne Formatierung

    Examples:
        >>> strip_mathtext_formatting("$\\mathbf{Messung}$")
        'Messung'

        >>> strip_mathtext_formatting("**Test** mit $\\alpha$")
        'Test mit α'  # (vereinfacht, in Realität komplexer)
    """
    if not text:
        return text

    # Entferne $\mathbf{...}$, $\mathit{...}$, etc.
    text = re.sub(r'\$\\mathbf\{([^}]+)\}\$', r'\1', text)
    text = re.sub(r'\$\\mathit\{([^}]+)\}\$', r'\1', text)
    text = re.sub(r'\$\\mathrm\{([^}]+)\}\$', r'\1', text)

    # Entferne ** und *
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)

    return text
