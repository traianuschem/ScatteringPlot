# Kennzahlen einer p(r)-Lösung — Definition und Interpretation

Stand: ScatterForge Plot v7.13 (`analysis/gift/explorer.py`). Die Kennzahlen stehen im
Ergebnisbereich des IFT/GIFT-Dialogs, im Kopf aller Ergebnisdateien, im Provenance-Sidecar
(`ift.results_summary.metrics`), in der Serienübersicht (CSV) und als wählbare Größe im
Explorer (1D-Scans, Karte Dmax × λ).

## 1. Definitionen

| Kennzahl | Definition | Entspricht in SasView |
|---|---|---|
| Oszillation | (Dmax/π)·√(∫p′² dr / ∫p² dr) auf 100 Stützstellen r = 0 … Dmax − Dmax/100, p′ analytisch | `Invertor.oscillations` (identische Formel und Stützstellen) |
| Positive Fraction | Σ max(p, 0) / Σ \|p\| | `positive_integral` |
| 1σ-Positive Fraction | Σ p·[p > σ_p] / Σ \|p\| | `positive_errors` — SasView verwendet für σ_p nur die **Diagonale** der Koeffizienten-Kovarianz, hier die **volle** Kovarianz |
| Maxima | Zahl der lokalen Maxima (inkl. Rand, wenn p am Anfang fällt bzw. am Ende steigt) | `npeaks` |
| MD | χ²/M | SasView zeigt χ²/dof |
| χ²/dof | χ²/(M − N_g) | – |
| N_g | Σ β/(β+λ): Zahl der von den Daten tatsächlich bestimmten Parameter | – |
| log-Evidenz | log p(I \| λ, Dmax), Koeffizienten analytisch integriert [Hansen 2000] | – (BIFT) |
| Randanteil | max \|p(r)\| für r ≥ 0.9·Dmax relativ zum Maximum | entspricht dem Flag `pr_end` |
| Rg, I(0), Untergrund | Momente von p(r) (exakte Quadratur) | Rg in SasView per Summe über 100 Stützstellen |

Richtwerte: Eine homogene Kugel hat die Oszillation ≈ 1.1 (in beiden Programmen, weil die
Kennzahl eine Eigenschaft von p(r) ist). Der Explorer zählt eine Lösung als „glatt“ bis 1.6
(einstellbar); das Flag `pr_smoothness` meldet ab 1.6 einen Hinweis, ab 2.5 eine Warnung.

## 2. Gleiche Formel, andere Interpretation: Moore (SasView) vs. Glatter/GIFT

Die Zahlen sind direkt vergleichbar, weil sie p(r) beschreiben und identisch berechnet werden.
Woher eine hohe Oszillation kommt und was sie bedeutet, hängt aber vom Verfahren ab.

1. **Basis.** SasView (Moore) entwickelt p(r) = Σ cₙ·2r·sin(nπr/Dmax). Jede Basisfunktion
   schwingt selbst, und die Oszillation wächst direkt mit der Zahl und Gewichtung hoher
   Terme. Glatter verwendet lokale kubische B-Splines ohne eigene Schwingung. Hier entsteht
   Oszillation nur, wenn Daten und Annahmen sie erzwingen: Dmax zu klein, λ zu klein,
   Artefakte, Modellfehler.
2. **Regularisierung.** SasView bestraft α·∫p′² dr, also genau den Zähler der
   Oszillation; α steuert die Kennzahl unmittelbar. Die IFT bestraft λ·Σ(c_{ν+1} − c_ν)²
   (erste Differenzen der Spline-Koeffizienten mit p(0) = p(Dmax) = 0). Das ist verwandt,
   aber nicht identisch. Bei gleichem Datensatz können beide Programme deshalb leicht
   unterschiedliche Oszillationen liefern, auch wenn die Anpassung gleich gut ist.
3. **Wahl der Regularisierung.** SasView schätzt α als größtes α, bei dem p(r) genau ein
   Maximum hat (bzw. aus dem Verhältnis Regularisierung/χ²). Das Kriterium „ein Maximum“
   setzt ein kompaktes, homogenes Teilchen voraus. Hier sind die Standardwahl Glatters
   Wendepunkt und die Alternative das Evidenz-Maximum (Hansen 2000). Beide machen keine
   Annahme über die Form von p(r). SasViews Regel wird bewusst nicht angeboten (siehe 5.).
4. **1σ-Positive Fraction.** Die volle Kovarianz berücksichtigt die starken Korrelationen
   benachbarter Koeffizienten; SasViews Diagonalnäherung kann σ_p über- oder
   unterschätzen. Die Werte können daher leicht abweichen.
5. **Positivität und Maxima.** In beiden Programmen ist p(r) < 0 oder mehr als ein Maximum
   kein Fehler an sich. Kern-Schale-Teilchen mit entgegengesetztem Kontrast haben
   physikalisch negative Bereiche (selten); Hantel-, Kern-Schale- oder Aggregatstrukturen
   haben mehrere Maxima. Deshalb sind `pr_negative` und `pr_peaks` nur Hinweise. Hart ist
   nur I(0) = (Σ Δρ·V)² > 0 (auch bei Kontrastwechsel), das der Explorer voraussetzt.
6. **GIFT.** Bei GIFT beschreibt p(r) nur den Formfaktor P(q) = I(q)/S(q). Oszillationen oder
   negative Bereiche, die in einer reinen IFT (oder in SasView) von der Wechselwirkung
   herrühren, verschwinden mit passendem S(q). Bleiben sie bei GIFT bestehen, ist meist das
   S(q)-Modell unzureichend (falsches Modell, Nebenminimum der BSSA-Suche). Die Kennzahlen
   diagnostizieren dann S(q), nicht das Teilchen.
7. **Abhängigkeit von Dmax.** Wegen des Faktors Dmax/π und des Null-Ausläufers wächst die
   Oszillation mit zu großem Dmax an (Kugel R = 10 nm: 1.11 bei Dmax = 20 nm, 1.66 bei 30 nm).
   Ein Minimum der Oszillation allein ist daher kein Kriterium für Dmax. Der Explorer
   kombiniert sie mit MD, I(0) > 0 und dem Randanteil.

## 3. Vorgehen bei oszillierendem p(r)

Das Flag `pr_smoothness` nennt die wahrscheinlichste Ursache. Typische Reihenfolge:

1. **Artefakte bei kleinem q** (Beamstop-Bereich, Separations- oder Abzugsartefakte):
   Flag `lowq_artifacts`. Die automatische Erkennung setzt q_min hinter einen führenden Block
   mit I ≤ 0 bzw. Vorzeichenwechseln. Ein Anstieg von I(q) direkt danach (`lowq_rise`) kann
   ein Randschatten oder eine repulsive Wechselwirkung sein und bleibt drin.
2. **Kein Guinier-Bereich** (`guinier_missing`): Das Teilchen ist vermutlich größer als
   π/q_min. Ein Dmax ≤ π/q_min erzwingt dann Oszillationen. Dmax mit „Vorschlagen“ oder der
   Karte Dmax × λ bestimmen. Die Warnung `dmax_qmin` bleibt zu Recht bestehen, denn die
   größten Abstände sind durch die Messung nicht abgedeckt; die DREAM-Analyse zeigt, wie
   unsicher Dmax dann ist.
3. **Kein Wendepunkt / λ zu klein:** Evidenz-Maximum als λ-Wahl oder λ aus der Karte übernehmen.
4. **MD ≫ 1:** σ, Untergrund oder Wechselwirkung (→ GIFT) prüfen.
5. **Viele Splines im Verhältnis zu den Shannon-Kanälen:** N reduzieren (Scan über N).

Beispiel (ASAXS-Normalterm einer Mizellprobe, ESRF): Mit q_min am ersten Punkt
bestimmten die Artefakte den Fit (MD ≈ 5, Dmax = π/q_min ≈ 300 nm). Ohne die 6–7
Artefaktpunkte, aber mit Dmax = π/q_min ≈ 124 nm, ergaben sich Oszillation 15–22 und 7–10
Maxima, weil kein Guinier-Bereich gemessen ist. Die Karte zeigt für Dmax ≲ 130 nm keinen
Wendepunkt. Der glatte Bereich (Oszillation 1.1–1.45, 1–2 Maxima) liegt bei
Dmax ≈ 160–230 nm; „Vorschlagen“ liefert 158–227 nm je nach Temperatur.

## 4. Numerik (v7.13)

- Die Zerlegung der IFT erfolgt per SVD der gewichteten Designmatrix statt über B = AᵀWA.
  Bei Daten ohne Kleinwinkelbereich reichen die Eigenwerte über ~20 Dekaden; über B
  gingen die kleinen im Rundungsfehler unter.
- Der λ-Scan wird automatisch unter 10⁻¹⁴ erweitert (bis 10⁻³⁰), wenn die MD am Rand noch
  deutlich über dem unregularisierten Wert liegt und dieser die Daten beschreibt (MD₀ ≤ 2).
  Der tatsächliche Scanbereich steht im Sidecar (`lambda_rel_scan_min`).
- Randplateau: Ist log N_c ab dem linken Scanrand flach, wird das rechte Ende des Plateaus
  gewählt (Glatters „Plateau vor dem MD-Anstieg“), nicht der Scanrand.

## Literatur

- O. Glatter (1977), J. Appl. Cryst. 10, 415 — IFT, Wendepunkt-Methode
- P. B. Moore (1980), J. Appl. Cryst. 13, 168 — Sinus-Entwicklung (SasView P(r) Inversion)
- S. Hansen (2000), J. Appl. Cryst. 33, 1415 — Bayes'sche IFT, Evidenz
- J. Brunner-Popela, O. Glatter (1997), J. Appl. Cryst. 30, 431 — GIFT
