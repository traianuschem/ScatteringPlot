#!/usr/bin/env python3
"""Test script for MathText formatter"""

from utils.mathtext_formatter import preprocess_mathtext, format_legend_text

print("=" * 60)
print("MathText Formatter Tests")
print("=" * 60)
print()

# Test 1: Einfache Formatierung
print('Test 1: **Messung** mit $\\alpha$')
result = preprocess_mathtext('**Messung** mit $\\alpha$')
print(f'  Ergebnis: {result}')
print(f'  Erwartet: $\\mathbf{{Messung}}$ mit $\\alpha$')
print(f'  ✓ OK' if result == '$\\mathbf{Messung}$ mit $\\alpha$' else '  ✗ FEHLER')
print()

# Test 2: Kursiv
print('Test 2: *Fit* für $q^2$')
result = preprocess_mathtext('*Fit* für $q^2$')
print(f'  Ergebnis: {result}')
print(f'  Erwartet: $\\mathit{{Fit}}$ für $q^2$')
print(f'  ✓ OK' if result == '$\\mathit{Fit}$ für $q^2$' else '  ✗ FEHLER')
print()

# Test 3: Normaler Text
print('Test 3: Normale Messung')
result = preprocess_mathtext('Normale Messung')
print(f'  Ergebnis: {result}')
print(f'  Erwartet: Normale Messung')
print(f'  ✓ OK' if result == 'Normale Messung' else '  ✗ FEHLER')
print()

# Test 4: format_legend_text mit bold=True
print('Test 4: format_legend_text("Messung", bold=True)')
result = format_legend_text('Messung', bold=True)
print(f'  Ergebnis: {result}')
print(f'  Erwartet: $\\mathbf{{Messung}}$')
print(f'  ✓ OK' if result == '$\\mathbf{Messung}$' else '  ✗ FEHLER')
print()

# Test 5: Kombination
print('Test 5: **Messung** von $H_2O$ bei $T=25°C$')
result = preprocess_mathtext('**Messung** von $H_2O$ bei $T=25°C$')
print(f'  Ergebnis: {result}')
print(f'  Erwartet: $\\mathbf{{Messung}}$ von $H_2O$ bei $T=25°C$')
print(f'  ✓ OK' if result == '$\\mathbf{Messung}$ von $H_2O$ bei $T=25°C$' else '  ✗ FEHLER')
print()

# Test 6: Bold und Italic
print('Test 6: **Bold** und *italic*')
result = preprocess_mathtext('**Bold** und *italic*')
print(f'  Ergebnis: {result}')
print(f'  Erwartet: $\\mathbf{{Bold}}$ und $\\mathit{{italic}}$')
print(f'  ✓ OK' if result == '$\\mathbf{Bold}$ und $\\mathit{italic}$' else '  ✗ FEHLER')
print()

# Test 7: Griechische Buchstaben
print('Test 7: Intensität $I$ für $\\alpha$, $\\beta$, $\\gamma$')
result = preprocess_mathtext('Intensität $I$ für $\\alpha$, $\\beta$, $\\gamma$')
print(f'  Ergebnis: {result}')
print(f'  Erwartet: Intensität $I$ für $\\alpha$, $\\beta$, $\\gamma$')
print(f'  ✓ OK' if result == 'Intensität $I$ für $\\alpha$, $\\beta$, $\\gamma$' else '  ✗ FEHLER')
print()

# Test 8: format_legend_text mit **text** und bold=True (user nutzt beides)
print('Test 8: format_legend_text("**Messung**", bold=True)')
result = format_legend_text('**Messung**', bold=True)
print(f'  Ergebnis: {result}')
print(f'  Hinweis: ** im Text hat Vorrang vor bold-Flag')
print()

# Test 9: Komplexes Beispiel
print('Test 9: $I \\cdot q^4$ (**Porod**)')
result = preprocess_mathtext('$I \\cdot q^4$ (**Porod**)')
print(f'  Ergebnis: {result}')
print(f'  Erwartet: $I \\cdot q^4$ ($\\mathbf{{Porod}}$)')
print(f'  ✓ OK' if result == '$I \\cdot q^4$ ($\\mathbf{Porod}$)' else '  ✗ FEHLER')
print()

print("=" * 60)
print("Tests abgeschlossen!")
print("=" * 60)
