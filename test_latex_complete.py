#!/usr/bin/env python3
"""Test script for complete LaTeX/MathText support in v7.0"""

from utils.mathtext_formatter import preprocess_mathtext, format_legend_text

print("=" * 70)
print("Version 7.0 - Vollständige LaTeX/MathText Unterstützung")
print("=" * 70)
print()

# ============================================================================
# TEST 1: Legenden-Formatierung
# ============================================================================
print("TEST 1: Legenden-Formatierung")
print("-" * 70)

test_cases = [
    ("**Messung** mit $\\alpha$", "Fette Messung mit Alpha-Symbol"),
    ("*Fit* für $q^2$", "Kursiver Fit mit Hochstellung"),
    ("$I \\cdot q^4$ (**Porod**)", "Formel mit fettem Text"),
    ("Protein bei $T=25°C$", "Mix aus Text und Formel"),
    ("**SAXS** $H_2O$ Lösung", "Fett, Tiefstellung, Text"),
]

for text, description in test_cases:
    result = preprocess_mathtext(text)
    print(f"  {description}:")
    print(f"    Input:  {text}")
    print(f"    Output: {result}")
    print()

# ============================================================================
# TEST 2: Annotations-Formatierung
# ============================================================================
print("\nTEST 2: Annotations-Formatierung")
print("-" * 70)

annotation_tests = [
    "**Bereich A**",
    "Guinier-Bereich ($q \\cdot R_g < 1$)",
    "*Übergangsbereich*",
    "$q^{-4}$ Skalierung",
]

for text in annotation_tests:
    result = preprocess_mathtext(text)
    print(f"  Input:  {text}")
    print(f"  Output: {result}")
    print()

# ============================================================================
# TEST 3: Achsenbeschriftungen
# ============================================================================
print("\nTEST 3: Achsenbeschriftungen")
print("-" * 70)

axis_tests = [
    ("$q$ [$\\AA^{-1}$]", "Q mit Angström hoch -1"),
    ("**Intensität** $I$ [cm$^{-1}$]", "Fette Intensität"),
    ("$I \\cdot q^4$ [a.u.]", "Porod-Darstellung"),
    ("2$\\theta$ [°]", "2-Theta Winkel"),
]

for text, description in axis_tests:
    result = preprocess_mathtext(text)
    print(f"  {description}:")
    print(f"    Input:  {text}")
    print(f"    Output: {result}")
    print()

# ============================================================================
# TEST 4: Format Legend Text (mit bold/italic Flags)
# ============================================================================
print("\nTEST 4: Format Legend Text (mit Flags)")
print("-" * 70)

flag_tests = [
    ("Messung", True, False, "Nur bold-Flag"),
    ("Fit", False, True, "Nur italic-Flag"),
    ("**Messung**", True, False, "** im Text + bold-Flag"),
    ("Text mit $\\alpha$", True, False, "Text mit Symbol + bold"),
]

for text, bold, italic, description in flag_tests:
    result = format_legend_text(text, bold, italic)
    flags = []
    if bold: flags.append("bold")
    if italic: flags.append("italic")
    flag_str = ", ".join(flags) if flags else "none"

    print(f"  {description} ({flag_str}):")
    print(f"    Input:  {text}")
    print(f"    Output: {result}")
    print()

# ============================================================================
# TEST 5: Griechische Buchstaben
# ============================================================================
print("\nTEST 5: Griechische Buchstaben")
print("-" * 70)

greek_letters = [
    "$\\alpha$", "$\\beta$", "$\\gamma$", "$\\delta$",
    "$\\theta$", "$\\lambda$", "$\\mu$", "$\\pi$", "$\\sigma$"
]

result = preprocess_mathtext(" ".join(greek_letters))
print(f"  Input:  {' '.join(greek_letters)}")
print(f"  Output: {result}")
print()

# ============================================================================
# TEST 6: Komplexe Formeln
# ============================================================================
print("\nTEST 6: Komplexe wissenschaftliche Formeln")
print("-" * 70)

complex_formulas = [
    "$I(q) = I_0 \\exp(-q^2 R_g^2/3)$",
    "$\\rho(r) = \\frac{1}{2\\pi^2} \\int q^2 I(q) \\sin(qr) dq$",
    "$d = \\frac{2\\pi}{q}$",
]

for formula in complex_formulas:
    result = preprocess_mathtext(formula)
    print(f"  Input:  {formula}")
    print(f"  Output: {result}")
    print()

# ============================================================================
# TEST 7: Fehlerhafte Eingaben
# ============================================================================
print("\nTEST 7: Robustheit bei speziellen Eingaben")
print("-" * 70)

edge_cases = [
    ("", "Leerer String"),
    ("Normaler Text ohne Formatierung", "Nur Text"),
    ("$", "Einzelnes Dollarzeichen"),
    ("****", "Nur Sterne"),
    ("**unvollständig", "Nicht geschlossene **"),
]

for text, description in edge_cases:
    try:
        result = preprocess_mathtext(text)
        print(f"  {description}: OK")
        print(f"    Input:  '{text}'")
        print(f"    Output: '{result}'")
    except Exception as e:
        print(f"  {description}: FEHLER")
        print(f"    Input:  '{text}'")
        print(f"    Error:  {e}")
    print()

# ============================================================================
# Zusammenfassung
# ============================================================================
print("=" * 70)
print("ZUSAMMENFASSUNG")
print("=" * 70)
print("""
Version 7.0 unterstützt jetzt LaTeX/MathText in:
  ✓ Legenden-Einträgen (Gruppen + Datasets)
  ✓ Annotations (Textfelder im Plot)
  ✓ Achsenbeschriftungen (X- und Y-Achse)

Verfügbare Syntax:
  • **text** → Fettdruck
  • *text* → Kursiv
  • $\\alpha$, $\\beta$, etc. → Griechische Buchstaben
  • $x^2$ → Hochstellung
  • $H_2O$ → Tiefstellung
  • Komplexe Formeln mit MathText

Alle Dialoge haben:
  • Live-Vorschau
  • Syntax-Hilfe-Button (📖)
  • HTML-Approximation der Formatierung
""")
print("=" * 70)
