# Changelog — Version 7.13

## Version 7.13.0 — ScatterForge Plot (RELEASE)

**Release Date:** 23. September 2026
**Status:** Stable Release — Explorer und Kennzahlen gegen oszillierende p(r)

Phase 4 des GIFT-Moduls (Planung: `docs/GIFT/PLAN.md`). Anlass war ein Testlauf mit echten
Daten (ASAXS-Normalterme einer Mizellprobe bei 20 °C / 60 °C / 20 °C nach Heizen, ESRF), bei
dem p(r) nur oszillierte und keine Einstellung half.

### 🔎 Befund an den Testdaten

1. **Artefakte bei kleinem q:** Die ersten 6–7 Punkte stammen aus der Separation im
   Beamstop-Bereich (Vorzeichenwechsel +340 / −797 / −224 bei |I/σ| = 10–20). Die
   Signifikanz-Auswahl hielt sie für gute Daten, und q_min stand auf dem ersten Punkt.
2. **Teilchen größer als π/q_min:** Ohne Guinier-Bereich setzte der Dialog Dmax = π/q_min
   (124 nm). Darunter findet die IFT keinen Wendepunkt, und p(r) muss oszillieren
   (Oszillation 15–22, 7–10 Maxima). Glatt wird p(r) bei Dmax ≈ 160–230 nm (Oszillation
   1.1–1.45).
3. **Numerik:** Ohne Kleinwinkelbereich reichen die Eigenwerte über ~20 Dekaden. Die
   Eigenzerlegung von B = AᵀWA verlor die kleinen im Rundungsfehler, und der λ-Scan endete
   bei 10⁻¹⁴, bevor die Daten angepasst waren.
4. **Wendepunkt-Regel:** Bei flachem log N_c ab dem Scanrand wurde der Rand (10⁻¹⁴) gewählt
   statt des Plateau-Endes.

### ✨ Neue Features & Verbesserungen (7.13.0)

#### 1. Kennzahlen (`analysis/gift/explorer.py`)
- SasView-kompatibel (gleiche Formel und Stützstellen): **Oszillation**, **Positive
  Fraction**, **1σ-Positive Fraction** (hier mit voller Kovarianz), **Maxima**.
- Zusätzlich: MD, χ²/dof, **N_g** (effektive Parameterzahl), **log-Evidenz**, **Randanteil**
  (p(r) im letzten Zehntel vor Dmax), Rg, I(0), Untergrund.
- Anzeige im Ergebnisbereich, im Datei-Kopf, im Sidecar und in der Serienübersicht.
- Neue Dokumentation **`docs/GIFT/KENNZAHLEN.md`**: Definitionen und die unterschiedliche
  Interpretation bei Moore/SasView (schwingende Sinusbasis, α·∫p′²), Glatter-IFT (lokale
  Splines) und GIFT (p(r) des Formfaktors; Rest-Oszillation diagnostiziert S(q)).

#### 2. Explorer-Tab
- **Karte Dmax × λ** für eine wählbare Kennzahl mit Wendepunkt-λ (weiß; Kreuze: kein
  Wendepunkt), Evidenz-Maximum (cyan), π/q_min, aktueller Einstellung (★) und **grünem
  „gutem Bereich“**: Oszillation ≤ Schwelle (1.6), I(0) > 0, Randanteil ≤ 0.1 und MD so gut
  wie die beste glatte Lösung (± max(25 %, 3·√(2/M))).
- **1D-Scans** über Dmax, λ oder N mit Auswahl der Kennzahl (wie SasViews Explorer).
- **Klick übernimmt** Dmax / λ (manuell) / N in den Dialog. Die Karte bleibt stehen und wird
  als veraltet markiert, wenn sich q-Bereich, N, K, Untergrund oder S(q) ändern.
- Laufzeit: Karte 33 × 43 ≈ 0.1–0.2 s (eine Zerlegung je Dmax, alle λ in O(N²)). Bei GIFT
  wird mit festem S(q) am Optimum gerechnet.

#### 3. Artefakterkennung bei kleinem q (`analysis/significance.py`)
- `detect_lowq_artifacts()`: führender Block mit I ≤ 0 bzw. Vorzeichenwechseln (bis zum
  ersten Lauf von 5 positiven Punkten), danach nicht signifikante Übergangspunkte. Gilt nur
  für den Kurvenanfang; ein negativer Punkt z. B. im Formfaktor-Minimum zählt nicht. Keine
  Fehlauslöser bei 150 verrauschten Kugelkurven (2–30 % Rauschen).
- Standardmäßig aktiv (Kontrollkästchen im q-Bereich); manuelle Grenzen haben Vorrang. Die
  nσ-Grenze wird erst ab dem ersten vertrauenswürdigen Punkt bestimmt.
- Flags `lowq_artifacts` (Info) und `lowq_rise` (Info: Anstieg zu größerem q —
  Randschatten oder repulsive Wechselwirkung, wird nicht entfernt).

#### 4. Dmax und λ
- **„Vorschlagen“** (neben π/q_min): kleinstes Dmax im guten Bereich eines Dmax-Scans
  (0.05 … 3 × π/q_min, logarithmisch); N wird mitgesetzt.
- Neue **Voreinstellung ohne Guinier-Bereich**: Dmax aus dem Vorschlag statt stillschweigend
  π/q_min. Dazu das Flag `guinier_missing` (Warnung).
- **λ-Wahl** als Auswahl: Wendepunkt (Standard), **Evidenz-Maximum** (Hansen 2000, dieselbe
  Größe wie in DREAM) oder manuell. Im DREAM-Tab: **„λ und Dmax aus DREAM übernehmen“**
  (Posterior-Mediane).
- λ-Tab zusätzlich mit log-Evidenz und N_g sowie Markierungen für Wendepunkt, Evidenz und
  Wahl.

#### 5. Robustere Numerik (`analysis/gift/ift.py`)
- `IFTDecomposition`: **SVD der gewichteten Designmatrix** statt Eigenzerlegung von B
  (halbiert die Kondition in Dekaden); auch Lösung und Kovarianz werden direkt aus der SVD
  gebildet. Synthetische Kugel ab q = 0.2 nm⁻¹: MD 0.67 statt ≥ 11.
- **Automatische Erweiterung des λ-Scans** unter 10⁻¹⁴ (bis 10⁻³⁰), wenn die MD am Rand noch
  deutlich über dem unregularisierten Wert MD₀ liegt und dieser die Daten beschreibt
  (MD₀ ≤ 2). Bei nicht beschreibbaren Daten (z. B. IFT bei Wechselwirkung) brächte ein
  kleineres λ nur Überanpassung. Der Scanbereich steht im Sidecar.
- **Randplateau-Regel:** Bei flachem log N_c ab dem Scanrand wird das Ende des Plateaus
  gewählt.
- Evidenz und N_g werden im λ-Scan mitberechnet; geprüft gegen die DREAM-Likelihood.

#### 6. Flags
- Neu: `lowq_artifacts`, `lowq_rise`, `guinier_missing`, `pr_smoothness` (Oszillation mit
  wahrscheinlichster Ursache: kein Wendepunkt, Dmax zu klein, MD ≫ 1, viele Splines,
  λ ≪ Evidenz-Optimum), `pr_peaks` (Info), `lambda.evidence`.
- `pr_negative` ist nur noch ein Hinweis (Kontrastwechsel im Teilchen ist möglich, wenn
  auch selten).

#### 7. Serienauswertung (rudimentär; `analysis/gift/batch.py`, `dialogs/gift_batch_dialog.py`)
- Knopf **„Serie…“**: die aktuellen Einstellungen auf mehrere geladene Datensätze anwenden,
  optional **Dmax und N je Datensatz vorschlagen**. Jeder Datensatz wird mit eigenem Sidecar
  exportiert. Tabelle und überlagertes p(r)/I(0); Übersicht
  `GIFT/GIFT_Serie_<Zeit>.csv` (Semikolon, UTF-8 mit BOM) mit record_id; optional als
  Gruppen übernehmen.
- Testserie (Dmax vorgeschlagen): 20 °C Rg = 54 nm (Dmax 173 nm), 60 °C Rg = 56 nm (158 nm),
  20 °C nach Heizen Rg = 78 nm (227 nm), alle mit glattem p(r). Das passt zur vermuteten
  Aggregation nach dem Heizen.
- Metadaten (z. B. Temperatur) werden noch nicht ausgelesen.

### 📦 Neue / geänderte Dateien (7.13.0)

| Datei | Änderungen |
|-------|------------|
| `analysis/gift/explorer.py` | **neu** — Kennzahlen, 1D-Scans, Karte, Dmax-Vorschlag |
| `analysis/gift/batch.py` | **neu** — Serienauswertung, CSV |
| `dialogs/gift_batch_dialog.py` | **neu** — Serien-Dialog |
| `docs/GIFT/KENNZAHLEN.md` | **neu** — Definitionen und Interpretation |
| `analysis/gift/ift.py` | `IFTDecomposition` (SVD), `lambda_grid` (Erweiterung), Evidenz/N_g im Scan, `lam_method`, Randplateau |
| `analysis/gift/splines.py` | `evaluate_derivative()` |
| `analysis/significance.py` | `detect_lowq_artifacts()`, `auto_qmin` |
| `analysis/gift/diagnostics.py` | neue Flags, `pr_negative` als Hinweis |
| `analysis/gift/pipeline.py` | `QRangeSettings.auto_qmin`, `IFTAnalysis.metrics`, Sidecar/Datei-Kopf |
| `analysis/gift/uncertainty.py` | λ-Prior folgt dem erweiterten Scanbereich |
| `dialogs/gift_dialog.py` | Explorer-Tab, λ-Wahl, „Vorschlagen“, Artefakt-Kontrollkästchen, Kennzahlen, „Aus DREAM übernehmen“, „Serie…“ |
| `scatter_plot.py` | Liste der geladenen Datensätze für die Serie |
| `i18n/translations/de.json`, `en.json` | Explorer, Kennzahlen, Ursachen, Serie, neue Flags |
| `tests/analysis/test_gift_explorer.py` | **neu** — 17 Tests |
| `core/version.py` | `7.12.0` → `7.13.0`; `analysis.gift` 0.5.0 → 0.6.0 |

Tests: `python -m unittest discover -s tests/analysis -t .` → 114 Tests (≈ 70 s).

### ⚠️ Hinweise

- Durch die SVD-Zerlegung und die Scan-Erweiterung weichen IFT-Ergebnisse älterer Sidecars
  in den letzten Stellen ab; bei Daten ohne Kleinwinkelbereich können sie sich deutlich
  ändern (dort waren die alten Ergebnisse numerisch unzuverlässig). Sidecars vor v7.13
  werden ohne automatisches q_min wiederholt.
- Die „gut“-Schwellen des Explorers sind Faustregeln. Bei Kern-Schale-Teilchen mit
  Kontrastwechsel und bei Aggregaten sind mehrere Maxima bzw. negative Bereiche möglich.

---

## 👥 Contributors & AI Transparency

**Development:**
- **Claude (Anthropic AI)** — Code-Implementierung und Entwicklung
- **Richard Neubert (traianuschem)** — Projektleitung, Feature-Design, SAXS-Fachanalyse,
  Testing und Qualitätssicherung

**AI Transparency Notice:**
Der Programmcode für ScatterForge Plot v7.13 wurde von Claude (Anthropic AI) unter der
Leitung und Orchestrierung von Richard Neubert geschrieben.

---

*Letzte Aktualisierung: 2026-09-23*
