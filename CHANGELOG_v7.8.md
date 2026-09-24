# Changelog — Version 7.8

## Version 7.8.0 — ScatterForge Plot (RELEASE)

**Release Date:** 23. September 2026
**Status:** Stable Release — P(r) per indirekter Fourier-Transformation (IFT) mit Provenance-Sidecar

Erster Baustein des GIFT-Moduls (Planung: `GIFT/PLAN.md`). Enthalten sind die IFT nach
Glatter (1977) und die Infrastruktur für Diagnose und Provenance. GIFT mit
Strukturfaktoren (Hard-Sphere, RMSA), Parallelisierung und die DREAM-Unsicherheitsanalyse
folgen in weiteren Versionen.

### ✨ Neue Features & Verbesserungen (7.8.0)

#### 1. Menü „Analyse → P(r) berechnen (IFT/GIFT)…“

Erreichbar über das neue Menü, per `Strg+Umschalt+G` (für den im Baum ausgewählten
Datensatz) oder per Rechtsklick auf einen Datensatz. Der nicht-modale Dialog bietet:

- **q-Fitbereich:** voller Bereich, **1σ / 2σ / 3σ** oder manuell. Die σ-Voreinstellungen
  verwenden dieselbe Signifikanzrechnung wie der Significance-Plot (gleitender Median
  von |I/σ|, gleiches Fenster). q_max ist der letzte Punkt vor dem ersten *dauerhaften*
  Abfall unter nσ, sodass einzelne Rauschspitzen den Bereich nicht verlängern.
- **IFT nach Glatter (1977):** kubische B-Splines auf [0, Dmax] mit p(0) = p(Dmax) = 0,
  stabilisierter gewichteter Least-Squares-Fit und automatische Wahl von λ über die
  Wendepunkt-Methode (λ lässt sich manuell übersteuern). Dazu Fehlerbänder für p(r)
  und den Fit, Rg und I(0) aus den Momenten von p(r) mit Fehlern sowie ein optionaler
  konstanter Untergrund.
- **Dmax-Hilfe:** Die Grenze **π/q_min** und das Verhältnis Dmax·q_min/π werden live
  angezeigt (rot bei Überschreitung). Der Knopf „π/q_min“ setzt Dmax auf die Grenze.
  Der Startwert ist min(π/q_min, 3.5·Rg_Guinier).
- **Spline-Anzahl aus den Shannon-Kanälen:** Der Startwert von N ist
  ≈ 1.2·N_s + 5 (N_s = Dmax·(q_max − q_min)/π, zwischen 20 und 200), dazu gibt es einen
  „Vorschlag“-Knopf. Ist N < N_s, erscheint eine Warnung mit empfohlenem N. Anlass war
  eine SasView-Simulation einer Kugel (R = 142 Å; als nm⁻¹ eingelesen formal R = 142 nm,
  siehe v7.9 „q-Einheit“) mit N_s ≈ 90–125: Mit zu wenigen
  Splines ist MD ≫ 1, mit dem Vorschlag wird Rg auf < 0.01 % genau bestimmt.
- **σ ohne Fehlerspalte:** Wählbar ist „aus Rauschen schätzen“ oder „relativ annehmen“
  (σ = x %·|I|). Letzteres ist für rauschfreie Simulationen gedacht; der Modus wird im
  Sidecar dokumentiert.
- **Werte I ≤ 0** (nach Untergrundabzug) werden für die IFT standardmäßig verwendet,
  obwohl der Hauptplot sie für die log-Darstellung ausblendet. Eine Checkbox schaltet
  das ab.
- **Tabs:** I(q) + Fit mit normierten Residuen, p(r) ± σ, λ-Wahl (log N_c und MD über λ,
  wie Glatter 1977 Fig. 2), Signifikanz mit Fitbereich sowie Provenance (Baumansicht).
- **Flags (Ampel-Liste):**
  - Dmax > π/q_min
  - Shannon-Kanäle
  - Anteil verworfener Punkte
  - σ geschätzt
  - kein Wendepunkt
  - MD ≫ 1 oder ≪ 1
  - p(r) am Ende nicht bei 0
  - langer Null-Ausläufer
  - negative p(r)
  - Oszillationen (Hinweis auf Wechselwirkung → GIFT)
  - Abweichung vom Guinier-Rg

#### 2. Ergebnisse und PDDF-Gruppe

„Übernehmen“ schreibt in den Unterordner `GIFT/` neben der Datendatei (änderbar):

| Datei | Inhalt |
|-------|--------|
| `<name>_GIFT_pr.dat` | r, p(r), σ_p(r) |
| `<name>_GIFT_fit-PDDF.dat` | q, I_fit, σ_fit (Fitbereich) |
| `<name>_GIFT_prov.json` | Provenance-Sidecar |
| `<name>_GIFT.prov-w3c.json` | dieselbe Information als W3C PROV-JSON (optional) |

Jede Ergebnisdatei trägt im Kopf die `record_id`, die wichtigsten Parameter und die
Flags. Anschließend wird eine Gruppe „GIFT: <name>“ mit Daten, IFT-Fit und p(r)
angelegt; die Rollen werden explizit gesetzt, also unabhängig von der
Dateinamen-Heuristik. Das Programm wechselt dann in den PDDF-Plot.

#### 3. Provenance-Sidecar (nach dem Vorbild von JADE-DLS)

- Gleiche Feldstruktur wie der `ProvenanceRecord` in JADE-DLS, eigene Schema-URI
  `…/gift-provenance/v1.0`. Er enthält:
  - Agent mit Software-, Modul-, Python-, numpy- und scipy-Version sowie Git-Commit
  - Eingangsdatei mit SHA-256 und Spaltenzuordnung
  - die Aktivitätenkette Laden → q-Bereich/Fehler → IFT → Export mit allen Parametern
    und Ergebniszusammenfassungen
  - die vollständige Flag-Liste
  - einen Output-Katalog mit SHA-256
- **„Analyse → Provenance-Sidecar prüfen…“:** vergleicht die SHA-256 von Eingangs- und
  Ergebnisdateien mit dem aktuellen Stand auf der Platte.
- **„Einstellungen aus Sidecar…“** (im Dialog): übernimmt alle Einstellungen einer
  gespeicherten Auswertung, rechnet neu und meldet eine veränderte Datendatei.
- Die `record_id` wird an der Gruppe gespeichert (Tooltip im Baum) und in Sessions
  mitgesichert.

#### 4. Refactoring: Signifikanzanalyse

`_rolling_median()` und die |I/σ|-Berechnung liegen jetzt in `analysis/significance.py`
und sind vektorisiert. Der Significance-Plot und der IFT-Dialog verwenden denselben
Code. Die Plot-Ausgabe wurde vorher/nachher verglichen und ist identisch.

### 📦 Neue / geänderte Dateien (7.8.0)

| Datei | Änderungen |
|-------|------------|
| `analysis/significance.py` | **neu** — Signifikanz, gleitender Median, `select_q_range()` |
| `analysis/gift/*.py` | **neu** — `splines`, `transform`, `smearing`, `ift`, `diagnostics`, `provenance`, `pipeline` (GUI-frei, nur numpy/scipy) |
| `dialogs/gift_dialog.py` | **neu** — IFT-Dialog |
| `tests/analysis/*` | **neu** — 42 Tests (Glatter-Testfälle Kugel/Kette/Stab, große rauschfreie Kugel R = 142 nm, q-Bereich, Provenance) |
| `scatter_plot.py` | Menü „Analyse“, Kontextmenü-Eintrag, `show_gift_dialog()`, `add_gift_results()`, `verify_gift_sidecar()`, Tooltip mit record_id; Significance-Plot nutzt `analysis.significance` |
| `core/models.py` | `DataGroup.provenance_record_id` (inkl. Session-Serialisierung) |
| `i18n/translations/de.json`, `en.json` | `menu.analysis.*`, `context_menu.gift`, `tree.provenance_tooltip`, `messages.gift_*`, `gift.*` (inkl. aller Flag-Texte) |
| `core/version.py` | `7.7.0` → `7.8.0` |

Tests ausführen: `python -m unittest discover -s tests/analysis -t .`

### 🔬 Methodische Hinweise

Die Validierung erfolgte an synthetischen Daten nach Glatter (1977):

- **Kugel (voller Messbereich):** Rg auf ≈ 0.3 % genau, p(r) mit < 1 % Abweichung.
- **Gaußkette/Stab mit Messbeginn bei h₁Rg = 1.6:** Rg-Fehler ≈ 10–13 % im Median.
  Glatter gibt hier 2 % bzw. < 10 % an. In diesen Fällen ist Dmax·q_min/π ≈ 2, und das
  Dmax-Flag schlägt an.

Gegenüber der Originalbeschreibung wurden zwei Details angepasst:

- **Basis:** Die Spline-Basis lässt die Steigung bei r = 0 frei (geklemmte B-Splines).
- **Glättungsnorm:** Standard ist die Variante mit c₀ = c_{N+1} = 0. Die reine
  Glatter-Form bestraft einen konstanten Koeffizientenanteil nicht; bei fehlenden
  Kleinwinkeldaten führt das zu negativem p(r). Die Glatter-Form ist weiterhin
  wählbar.

Details stehen in `GIFT/PLAN.md` §10.

### ⚠️ Bekannte Einschränkungen

- Nur Punktkollimation (Pinhole); keine Spalt- oder Wellenlängen-Entschmierung.
- Die Fehlerbänder aus der Kovarianz enthalten nicht den Regularisierungs-Bias und
  nicht die Unsicherheit von Dmax und λ. Das deckt die geplante DREAM-Analyse ab.
- GIFT (Strukturfaktoren) ist noch nicht enthalten; der Menüeintrag nennt es bereits,
  weil der Dialog in den nächsten Versionen erweitert wird.

---

## 👥 Contributors & AI Transparency

**Development:**
- **Claude (Anthropic AI)** — Code-Implementierung und Entwicklung
- **Richard Neubert (traianuschem)** — Projektleitung, Feature-Design, SAXS-Fachanalyse,
  Testing und Qualitätssicherung

**AI Transparency Notice:**
Der Programmcode für ScatterForge Plot v7.8 wurde von Claude (Anthropic AI) unter der
Leitung und Orchestrierung von Richard Neubert geschrieben. Die fachlichen Anforderungen
stammen vom Projektinhaber: GIFT-Auswertung nach Glatter statt der vereinfachten
Moore-Inversion in SASview, Dmax ≤ π/q_min als Flag, q-Fitbereich aus der
Signifikanzanalyse und ein Provenance-Sidecar nach dem Vorbild von JADE-DLS.

---

*Letzte Aktualisierung: 2026-09-23*
