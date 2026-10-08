"""
MathText Formatter

Provides utilities for formatting text with LaTeX-style syntax for use in Matplotlib.
Converts simple Markdown-like syntax to Matplotlib MathText formatting.

Version: 7.0
"""

import re


# ── Chemische Formeln: \ce{...} (Teilmenge von LaTeX-mhchem, v8.1.1) ────────────

_CE_ARROWS = {
    '<=>': r'\rightleftharpoons',
    '<->': r'\leftrightarrow',
    '->': r'\rightarrow',
    '<-': r'\leftarrow',
}


def _read_script_group(token, i):
    """Liest das Argument nach ^ oder _ ab Position i: {…}, Ladung (z. B. 2+, -)
    oder ein einzelnes Zeichen. Gibt (Inhalt, neue Position) zurück."""
    if i >= len(token):
        return '', i
    if token[i] == '{':
        depth, j = 0, i
        while j < len(token):
            if token[j] == '{':
                depth += 1
            elif token[j] == '}':
                depth -= 1
                if depth == 0:
                    return token[i + 1:j], j + 1
            j += 1
        return token[i + 1:], len(token)
    m = re.match(r'\d*[+-]|\d+|[A-Za-z]+|.', token[i:])
    return m.group(0), i + len(m.group(0))


def _convert_ce_token(token):
    """Wandelt ein Leerzeichen-freies Formel-Token um (z. B. 'Fe2+', 'SO4^2-', '2H2O')."""
    if token in _CE_ARROWS:
        return _CE_ARROWS[token]
    out = []
    i = 0
    # Stöchiometrischer Koeffizient am Anfang bleibt normal (2H2O, 1/2O2)
    m = re.match(r'\d+(?:[./]\d+)?', token)
    if m:
        out.append(m.group(0))
        i = m.end()
    while i < len(token):
        ch = token[i]
        prev = token[i - 1] if i > 0 else ''
        if ch in '^_':
            content, i = _read_script_group(token, i + 1)
            out.append(f'{ch}{{{content}}}')
        elif ch == '\\':
            # LaTeX-Befehl unverändert übernehmen (\alpha, \cdot, …)
            m = re.match(r'\\[A-Za-z]+|\\.', token[i:])
            out.append(m.group(0))
            i += len(m.group(0))
            if i < len(token) and token[i].isalnum():
                out.append(' ')
        elif ch.isdigit() and (prev.isalpha() or (prev and prev in ')]')):
            m = re.match(r'\d+', token[i:])
            digits = m.group(0)
            j = i + len(digits)
            if j < len(token) and token[j] in '+-' and j == len(token) - 1:
                # Ladung am Token-Ende: Fe2+ → Fe^{2+}
                out.append(f'^{{{digits}{token[j]}}}')
                i = j + 1
            else:
                out.append(f'_{{{digits}}}')
                i = j
        elif ch in '+-' and i == len(token) - 1 and (prev.isalnum() or (prev and prev in ')]')):
            out.append(f'^{{{ch}}}')  # Na+ → Na^{+}
            i += 1
        elif ch in '*·':
            out.append(r'{\cdot}')  # Hydrat: CuSO4*5H2O
            i += 1
        else:
            out.append(ch)
            i += 1
    return ''.join(out)


def convert_ce(formula):
    r"""Wandelt eine mhchem-ähnliche Formel in MathText um (ohne umgebende $).

    Unterstützt: Indizes (H2O), Ladungen (Na+, Fe3+, SO4^2-), explizite ^{…}/_{…},
    Koeffizienten (2H2O), Hydrate (CuSO4*5H2O), Pfeile (->, <-, <=>, <->),
    Zustände ((aq), (s)) und LaTeX-Befehle (\alpha).

    >>> convert_ce('SO4^2-')
    '\\mathrm{SO_{4}^{2-}}'
    """
    tokens = formula.strip().split()
    return r'\mathrm{' + r'\ '.join(_convert_ce_token(t) for t in tokens) + '}'


def _find_ce(text, start=0):
    """Findet das nächste \\ce{…} (mit verschachtelten Klammern).
    Gibt (Anfang, Ende, Inhalt) oder None zurück."""
    idx = text.find('\\ce{', start)
    if idx < 0:
        return None
    depth = 0
    for j in range(idx + 3, len(text)):
        if text[j] == '{':
            depth += 1
        elif text[j] == '}':
            depth -= 1
            if depth == 0:
                return idx, j + 1, text[idx + 4:j]
    return None


def expand_ce(text):
    r"""Ersetzt alle \ce{…} durch MathText. Außerhalb von $…$ wird die Formel in
    $…$ eingeschlossen, innerhalb einer Formel direkt eingesetzt."""
    if not text or '\\ce{' not in text:
        return text
    result, pos = [], 0
    while True:
        found = _find_ce(text, pos)
        if found is None:
            break
        start, end, content = found
        before = text[pos:start]
        result.append(before)
        in_math = _count_unescaped_dollars(''.join(result)) % 2 == 1
        converted = convert_ce(content)
        result.append(converted if in_math else f'${converted}$')
        pos = end
    result.append(text[pos:])
    return ''.join(result)


def _count_unescaped_dollars(text):
    return len(re.findall(r'(?<!\\)\$', text))


def is_in_math(text, position):
    """True, wenn `position` in `text` innerhalb eines $…$-Bereichs liegt."""
    return _count_unescaped_dollars(text[:position]) % 2 == 1


_MATH_SEGMENT = re.compile(r'(?<!\\)\$(?:[^$\\]|\\.)+?(?<!\\)\$')


def preprocess_mathtext(text):
    r"""
    Konvertiert einfache Formatierungssyntax in MathText-Format.

    Unterstützt:
    - **text** → Fettdruck ($\mathbf{text}$)
    - *text* → Kursiv ($\mathit{text}$)
    - \\ce{H2SO4} → chemische Formel (v8.1.1)
    - Bereits vorhandenes MathText bleibt unverändert ($...$), auch ein * darin
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

    text = expand_ce(text)

    # Formel-Inhalte schützen, damit * und ** darin (z. B. $a*b$) nicht als
    # Markdown interpretiert werden; die Platzhalter bleiben $…$-Bereiche.
    protected = []

    def _protect(match):
        protected.append(match.group(0))
        return f'$\x00{len(protected) - 1}\x00$'

    text = _MATH_SEGMENT.sub(_protect, text)

    # Erst ** verarbeiten, dann *
    text = process_bold_with_mathtext(text)
    text = process_italic_with_mathtext(text)

    return re.sub(r'\$\x00(\d+)\x00\$', lambda m: protected[int(m.group(1))], text)


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

<b>Chemische Formeln (wie LaTeX-mhchem):</b><br>
• <code>\\ce{H2SO4}</code> → H₂SO₄ &nbsp; <code>\\ce{SO4^2-}</code> → SO₄²⁻ &nbsp; <code>\\ce{Fe3+}</code> → Fe³⁺<br>
• <code>\\ce{CuSO4*5H2O}</code> → CuSO₄·5H₂O &nbsp; <code>\\ce{2H2 + O2 -> 2H2O}</code><br>
• Beliebiges LaTeX/MathText in <code>$...$</code>, z. B. <code>$\\mathrm{Fe_3O_4}$</code><br><br>

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
