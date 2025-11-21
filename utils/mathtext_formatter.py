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
    - Verkettungen: **text $formula$ text**

    Args:
        text (str): Input-Text mit einfacher Formatierung

    Returns:
        str: MathText-formatierter String

    Examples:
        >>> preprocess_mathtext("**Messung** mit $\\alpha$")
        '$\\mathbf{Messung}$ mit $\\alpha$'

        >>> preprocess_mathtext("*Fit* für $q^2$")
        '$\\mathit{Fit}$ für $q^2$'

        >>> preprocess_mathtext("**Text $formula$ Text**")
        '$\\mathbf{Text }$$formula$$\\mathbf{ Text}$'
    """
    if not text:
        return text

    # Schritt 1: Verarbeite **...** und *...* MIT Berücksichtigung von $...$
    # Wir müssen hier intelligenter sein und ** INNERHALB von $...$ nicht anfassen,
    # aber ** AUSSERHALB schon

    def process_bold_with_mathtext(text):
        """Verarbeitet **...** auch wenn $...$ darin vorkommt"""
        # Finde alle **...** Bereiche
        result = []
        pos = 0

        for match in re.finditer(r'\*\*(.+?)\*\*', text):
            # Füge Text vor dem Match hinzu
            result.append(text[pos:match.start()])

            content = match.group(1)
            # Prüfe ob der Inhalt $...$ enthält
            if '$' in content:
                # Zerlege in Teile: normale Teile und $...$ Teile
                parts = []
                last_end = 0
                for dollar_match in re.finditer(r'\$[^$]+\$', content):
                    # Text vor $...$
                    before = content[last_end:dollar_match.start()]
                    if before:
                        parts.append(f'$\\mathbf{{{before}}}$')
                    # $...$ selbst (ohne bold, da es schon formatiert ist)
                    parts.append(dollar_match.group(0))
                    last_end = dollar_match.end()

                # Rest nach letztem $...$
                after = content[last_end:]
                if after:
                    parts.append(f'$\\mathbf{{{after}}}$')

                result.append(''.join(parts))
            else:
                # Kein $...$ im Inhalt - einfach umwandeln
                result.append(f'$\\mathbf{{{content}}}$')

            pos = match.end()

        # Rest des Textes
        result.append(text[pos:])
        return ''.join(result)

    def process_italic_with_mathtext(text):
        """Verarbeitet *...* auch wenn $...$ darin vorkommt (aber nicht **...**)"""
        result = []
        pos = 0

        for match in re.finditer(r'(?<!\*)\*(.+?)\*(?!\*)', text):
            # Füge Text vor dem Match hinzu
            result.append(text[pos:match.start()])

            content = match.group(1)
            # Prüfe ob der Inhalt $...$ enthält
            if '$' in content:
                # Zerlege in Teile
                parts = []
                last_end = 0
                for dollar_match in re.finditer(r'\$[^$]+\$', content):
                    before = content[last_end:dollar_match.start()]
                    if before:
                        parts.append(f'$\\mathit{{{before}}}$')
                    parts.append(dollar_match.group(0))
                    last_end = dollar_match.end()

                after = content[last_end:]
                if after:
                    parts.append(f'$\\mathit{{{after}}}$')

                result.append(''.join(parts))
            else:
                result.append(f'$\\mathit{{{content}}}$')

            pos = match.end()

        result.append(text[pos:])
        return ''.join(result)

    # Erst ** verarbeiten, dann *
    text = process_bold_with_mathtext(text)
    text = process_italic_with_mathtext(text)

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

        >>> format_legend_text("Messung $\\alpha$", bold=True)
        '$\\mathbf{Messung }$$\\alpha$'
    """
    if not text:
        return text

    # Zuerst Preprocessing für **/** Syntax
    processed = preprocess_mathtext(text)

    # Wenn bold/italic-Flags gesetzt sind, Text entsprechend formatieren
    if bold or italic:
        # Prüfe ob es bereits MathText gibt
        if '$' in processed:
            # Text enthält bereits MathText - formatiere nur die Nicht-MathText-Teile
            parts = []
            last_end = 0

            # Finde alle $...$ Bereiche
            for match in re.finditer(r'\$[^$]+\$', processed):
                # Text vor dem $...$ Bereich
                before = processed[last_end:match.start()]
                if before:
                    # Formatiere den normalen Text
                    if bold and italic:
                        parts.append(f'$\\mathbf{{\\mathit{{{before}}}}}$')
                    elif bold:
                        parts.append(f'$\\mathbf{{{before}}}$')
                    elif italic:
                        parts.append(f'$\\mathit{{{before}}}$')

                # Füge den $...$ Bereich unverändert hinzu
                parts.append(match.group(0))
                last_end = match.end()

            # Rest nach dem letzten $...$ Bereich
            after = processed[last_end:]
            if after:
                if bold and italic:
                    parts.append(f'$\\mathbf{{\\mathit{{{after}}}}}$')
                elif bold:
                    parts.append(f'$\\mathbf{{{after}}}$')
                elif italic:
                    parts.append(f'$\\mathit{{{after}}}$')

            processed = ''.join(parts)
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
