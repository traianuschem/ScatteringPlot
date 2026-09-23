# Referenzdaten (SasView/sasmodels-Simulationen)

Rauschfreie Simulationen, erstellt vom Projektinhaber mit SasView (Einheiten wie in
SasView: **q in Å⁻¹, Intensität in cm⁻¹**). Sie dienen als unabhängige Referenz für die
Strukturfaktor-Implementierungen.

| Datei | Modell |
|-------|--------|
| `sasview_sphere140A_hardsphere.txt` | `sphere@hardsphere`, P*S |
| `sasview_sphere140A_haytermsa.txt` | `sphere@hayter_msa`, P*S |

Gemeinsame Parameter: scale = 1, background = 0.001 cm⁻¹, sld = 1, sld_solvent = 6
(10⁻⁶ Å⁻²), radius = 140 Å, radius_effective = 140 Å (Modus „radius“), volfraction = 0.2.

Zusätzlich bei `hayter_msa`: charge = 19 e, temperature = 318.16 K,
concentration_salt = 0.001 M, dielectconst = 71.08.

Laut sasmodels gilt I(q) = scale · volfraction · V · Δρ² · P(q) · S(q) + background,
also I_P(0) = 0.2 · 28 735 cm⁻¹ = 5 747 cm⁻¹.
