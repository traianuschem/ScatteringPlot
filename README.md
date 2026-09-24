# ScatterForge Plot v8.0.0

**Professionelles Tool für wissenschaftliche Streudaten-Analyse mit publikationsreifer Visualisierung**

![Version](https://img.shields.io/badge/version-8.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-GPL--3.0-blue)

---

## 📄 Über ScatterForge Plot

ScatterForge Plot ist eine Qt6-basierte Desktop-Anwendung für die professionelle Visualisierung und Analyse von Streudaten (SAXS/SANS/XRD). Entwickelt für Naturwissenschaftler und Ingenieure, die publikationsreife Grafiken mit präziser Kontrolle über alle Aspekte benötigen.

### 🎯 Alleinstellungsmerkmale

**1. Intelligentes Gruppen-Management**
- Organisieren Sie Datensätze in Gruppen mit individuellen Stack-Faktoren
- Nicht-kumulative Multiplikatoren für perfekte Kurvenseparation
- Gruppenspezifische Farbpaletten und Batch-Formatierung
- Drag & Drop zwischen Gruppen, Auto-Gruppierung mit Zehnerpotenzen

**2. Wissenschaftliches Metadaten-System**
- XMP-Sidecar-Dateien (.xmp) für alle Export-Formate, die XMP nicht eingebettet unterstützen
- Eingebettete Metadaten (Autor, Institution, Projekt, Lizenz)
- Benutzer-Konfigurationssystem für dauerhafte Metadaten
- Volle Rückverfolgbarkeit für wissenschaftliche Publikationen

**3. LaTeX/MathText-Integration**
- Mathematische Notation in Legenden, Achsen und Annotations
- Live-Vorschau mit automatischer Konvertierung

---

## 📑 Inhaltsverzeichnis

- [Feature-Übersicht](#-feature-übersicht)
- [Was ist neu in v7.5](#-was-ist-neu-in-v75)
- [Was ist neu in v7.4](#-was-ist-neu-in-v74)
- [Was ist neu in v7.3](#-was-ist-neu-in-v73)
- [Was ist neu in v7.1](#-was-ist-neu-in-v71)
- [Was ist neu in v7.0](#-was-ist-neu-in-v70)
- [Installation](#-installation)
- [Schnellstart (5 Minuten)](#-schnellstart-5-minuten)
- [Benutzerhandbuch](#-benutzerhandbuch)
  - [1. Daten laden](#1-daten-laden)
  - [2. Plot-Typ wählen](#2-plot-typ-wählen)
  - [3. Gruppen organisieren](#3-gruppen-organisieren-alleinstellungsmerkmal)
  - [4. Kurven gestalten](#4-kurven-gestalten)
  - [5. Plot formatieren](#5-plot-formatieren)
  - [6. Exportieren](#6-exportieren-mit-metadaten)
  - [7. Sessions speichern](#7-sessions-speichern)
- [Feature-Referenz](#-feature-referenz)
- [Konfiguration](#-konfiguration)
- [Troubleshooting](#-troubleshooting)
- [Mitwirken & Lizenz](#-mitwirken--lizenz)

---

## 🎨 Feature-Übersicht

### Was kann ScatterForge Plot?

| Feature | Beschreibung | Status |
|---------|--------------|--------|
| **Weitere Glatter-Auswertungen** | IFT-Arten Querschnitt p_c(r) und Dicke p_t(r), Größenverteilungen D_V(R)/D_N(R) für Kugeln, Zylinder und Lamellen; DECON: radiales Kontrastprofil aus p(r) mit exakten Überlappungsintegralen, Polydispersitäts-Scan (Mittelbach & Glatter 1998) und optimiertem Stufenmodell | ✅ **v8.0.0** |
| **Weitere GIFT-Strukturfaktoren** | S_eff polydisperser harter Kugeln (Vrij, Schulz), klebrige harte Kugeln (Baxter), fraktales Aggregat (Teixeira), Stäbchen (Mean-Field) — validiert gegen sasmodels bzw. PY-Grenzfälle, mit Flags zur Bestimmbarkeit | ✅ **v7.14.0** |
| **p(r)-Explorer & Kennzahlen** | SasView-kompatible Kennzahlen (Oszillation, Positive Fraction, Maxima, χ²) plus N_g und Evidenz; Karte Dmax × λ mit „gutem Bereich“ und Klick-Übernahme, 1D-Scans über Dmax/λ/N, Dmax-Vorschlag, λ per Evidenz-Maximum, automatische Artefakterkennung bei kleinem q, Serienauswertung mit CSV-Übersicht | ✅ **v7.13.0** |
| **Unsicherheit per DREAM** | MCMC-Analyse (DREAM(ZS)) der IFT/GIFT-Parameter auf Knopfdruck: S(q)-Parameter, log λ und Dmax mit analytisch herausintegrierten Spline-Koeffizienten (Hansen 2000); Intervalle, Korrelationen, Corner-Plot, p(r)-/I(q)-/S(q)-Bänder, eigene Flags, Ketten als .npz | ✅ **v7.12.0** |
| **Parallele GIFT-Rechnung** | BSSA-Mehrfachstarts im Prozess-Pool, Ergebnis bitgleich unabhängig von der Prozesszahl; vektorisierte Batch-Likelihood | ✅ **v7.11.0** |
| **GIFT für geladene Systeme** | RMSA-Strukturfaktor (Hayter-Penfold, Rescaling nach Hansen-Hayter) mit Ladung, Salz, Temperatur, ε_r; validiert gegen sasmodels/SasView; BSSA-Mehrfachstart | ✅ **v7.10.0** |
| **GIFT (Strukturfaktor)** | Generalisierte IFT für konzentrierte Systeme: S(q) (Harte Kugeln PY bzw. gemittelt S_ave) und modellfreies p(r) gleichzeitig, Optimierung per Boltzmann-Simplex-Simulated-Annealing, Hintergrund-Thread, S(q)/P(q)-Export | ✅ **v7.9.0** |
| **P(r) per IFT (Glatter)** | Neues Menü „Analyse“: modellfreie Paarabstandsverteilung p(r) nach Glatter (1977) mit automatischer λ-Wahl (Wendepunkt-Methode), Fehlerbändern, Rg/I(0), q-Fitbereich per 1σ/2σ/3σ-Signifikanz, Plausibilitäts-Flags (u. a. Dmax ≤ π/q_min) | ✅ **v7.8.0** |
| **Provenance-Sidecar** | Jede IFT-Auswertung schreibt ein JSON-Sidecar (SHA-256 der Ein-/Ausgaben, alle Parameter, Flags, record_id; optional W3C PROV-JSON), prüfbar und wiederholbar | ✅ **v7.8.0** |
| **Subplot-Achsen-Editor** | Achsen und Limits-Dialog sowie Titel-Editor steuern jetzt auch die untere Subplot-Achse (PDDF/ASAXS-Cross-Term/Significance): Titel-Override, Limits, Y-Skala, eigener Subplot-Titel | ✅ **v7.7.0** |
| **Plot-Typen** | 11 spezialisierte Darstellungen: Log-Log, Porod, Kratky, Guinier, Bragg Spacing, 2-Theta, PDDF, Azimuthal Profile, ASAXS, dlnI/dlnq, **Significance** | ✅ **v7.6.0** |
| **Significance-Plot** | Subplot mit punktweiser Signifikanz \|I(q)/σ(q)\| (roh + median-geglättet) und einstellbaren σ-Schwellenlinien, um den vertrauenswürdigen q-Bereich einer Kurve abzulesen | ✅ **v7.6.0** |
| **Symlog-Skala (ASAXS)** | Y-Achse zeigt negative Cross-Term-Werte jetzt auch im Hauptplot, mit einstellbaren Dekaden/Nullbereich | ✅ **v7.5.0** |
| **PDDF-Subplot-Routing** | Gemischte Gruppen (I(q)-Daten + Fit + P(r), z. B. GIFT/GNOM-Export) werden pro Datensatz korrekt der richtigen Achse zugeordnet | ✅ **v7.5.0** |
| **dlnI/dlnq-Plot** | Logarithmische Ableitung zur schnellen Identifikation versteckter Features/Schultern, mit einstellbarem Glättungsfenster | ✅ **v7.4.0** |
| **Flexible Spaltenzuordnung** | X/Y/Fehler-Spalte frei wählbar im Kurven-Editor, auch bei 4+ Spalten pro Datei | ✅ **v7.4.0** |
| **Gruppen-Sichtbarkeit** | Ganze Gruppen per Checkbox im Baum ein-/ausblenden | ✅ **v7.4.0** |
| **ASAXS-Analyse** | Separation I_N / I_cross / I_A mit optionalem linearem Subplot für negative Werte | ✅ **v7.3** |
| **SNR-Qualitätsmarker** | Datenpunkte nach Signal-Rausch-Verhältnis visuell differenzieren (alle Plot-Typen) | ✅ **v7.3** |
| **Subplot-Routing** | Pro Gruppe wählbar: Hauptplot, Subplot oder beides (ASAXS & PDDF) | ✅ **v7.3** |
| **2D SAXS Viewer** | NeXus/HDF5-Laden, q-Map, Polarkarte, Azimutalprofil, Sektor-Integral | ✅ **v7.1** |
| **q-Ring-Selektor** | Ziehbare Grenzen direkt in der Polarkarte | ✅ **v7.1** |
| **sin(φ)-Korrektur** | Lorentz- und Jacobi-Korrektur mit Voigt-Polextrapolation | ✅ **v7.1** |
| **Gruppen-Management** | Datasets organisieren mit Stack-Faktoren, Drag & Drop, Auto-Gruppierung | ✅ **USP** |
| **Metadaten-Export** | XMP-Sidecar + eingebettete Metadaten, Benutzer-Profil-System | ✅ **USP** |
| **LaTeX/MathText** | Wissenschaftliche Notation mit Live-Vorschau | ✅ v7.0 |
| **Mehrsprachigkeit** | Deutsch/Englisch, vollständig lokalisiert | ✅ v7.0 |
| **Export-Formate** | PNG, SVG, PDF, EPS, TIFF mit Live-Vorschau | ✅ |
| **Fehlerbalken** | 3 Darstellungen: Transparente Fläche, Balken mit Caps, Stem/Anker | ✅ |
| **Stil-Vorlagen** | Vollständig konfigurierbarer Editor (Marker, Linie, Fehlerbalken, SNR) | ✅ **v7.3.2** |
| **Farbpaletten** | 30+ Paletten (TUBAF, Matplotlib), gruppenspezifisch | ✅ |
| **Keyboard Shortcuts** | Vollständige Tastatursteuerung | ✅ v7.0 |
| **Session-Verwaltung** | Komplette Projektzustände speichern/laden | ✅ |
| **Annotations** | Interaktiv verschiebbar, LaTeX-Support | ✅ |
| **Dark Mode** | Vollständige Dark-Mode-Unterstützung | ✅ |

---

## 🎉 Was ist neu in v8.0?

**Major Release v8.0.0** — GIFT-Modul vollständig: IFT/GIFT, DREAM, Explorer, Strukturfaktoren und weitere Glatter-Auswertungen (v7.8–v8.0); Bugfixes folgen als 8.0.x

### Hauptfeatures v8.0

- 📏 **Querschnitts- und Dicken-IFT** (Glatter 1980b): p_c(r) für lange Zylinder, p_t(r) für Lamellen, mit R_c bzw. R_t und äquivalenter homogener Größe
- 📊 **Größenverteilungen per IFT** (Glatter 1980a): Anzahl- oder Volumenverteilung als Primärgröße, abgeleitete Verteilungen, Momente mit Fehlern
- 🧅 **DECON** (Glatter 1981; Glatter & Hainisch 1984): radiales Kontrastprofil aus p(r) mit exakten Überlappungsintegralen, **Polydispersität** (Mittelbach & Glatter 1998) und optimiertem Stufenmodell (Kern-/Außenradius)
- Explorer, DREAM, GIFT und Export funktionieren mit allen IFT-Arten

**Vollständige Änderungen:** Siehe [CHANGELOG_v8.0.md](CHANGELOG_v8.0.md)

---

## 🎉 Was ist neu in v7.14?

**Minor Release v7.14.0** — Weitere Strukturfaktoren für GIFT

### Hauptfeatures v7.14

- 🧪 **S_eff nach Vrij**: polydisperse harte Kugeln (Percus-Yevick-Mischung, Schulz-Verteilung) als physikalische Alternative zum „scheinbaren“ S_ave
- 🍯 **Klebrige harte Kugeln** (Baxter): kurzreichweitige Anziehung, Parametrisierung wie SasView (τ = stickiness, δ = perturb)
- 🕸️ **Fraktales Aggregat** (Teixeira): p(r) beschreibt die Bausteine, S(q) die Aggregation (D_f, ξ, Zahl der Bausteine)
- 🥢 **Stäbchen** (Mean-Field nach van der Schoot, [W99])
- 🛡️ Robustere Numerik für sehr kleine λ in GIFT und DREAM

**Vollständige Änderungen:** Siehe [CHANGELOG_v7.14.md](CHANGELOG_v7.14.md)

---

## 🎉 Was ist neu in v7.13?

**Minor Release v7.13.0** — Explorer und Kennzahlen gegen oszillierende p(r)

### Hauptfeatures v7.13

- 🗺️ **Explorer-Tab**: Karte Dmax × λ (Oszillation, MD, Evidenz, …) mit Wendepunkt-λ, Evidenz-Maximum, π/q_min und grünem „gutem Bereich“; Klick übernimmt die Werte; 1D-Scans über Dmax, λ und N wie in SasView
- 📏 **Kennzahlen** in SasView-Definition (Oszillation, Positive Fraction, 1σ-Positive Fraction, Maxima) plus N_g, log-Evidenz und Randanteil — mit Hinweisen zur unterschiedlichen Interpretation (Moore vs. Glatter/GIFT, [docs/GIFT/KENNZAHLEN.md](docs/GIFT/KENNZAHLEN.md))
- ✂️ **Artefakte bei kleinem q** (Beamstop, Separation) werden automatisch erkannt und ausgeschlossen
- 🎯 **Dmax vorschlagen** und neue Voreinstellung, wenn kein Guinier-Bereich gemessen ist; **λ-Wahl** Wendepunkt (Standard), Evidenz-Maximum oder aus DREAM
- 🧮 Robustere Numerik: SVD-Zerlegung, automatisch erweiterter λ-Scan, Randplateau-Regel
- 📚 **Serienauswertung** (rudimentär): gleiche Einstellungen für mehrere Datensätze, Dmax je Datensatz, CSV-Übersicht

**Vollständige Änderungen:** Siehe [CHANGELOG_v7.13.md](CHANGELOG_v7.13.md)

---

## 🎉 Was ist neu in v7.12?

**Minor Release v7.12.0** — Statistische Absicherung der IFT/GIFT-Parameter (DREAM)

### Hauptfeatures v7.12

- 🎲 **„Unsicherheit bestimmen“**: DREAM(ZS)-MCMC über die S(q)-Parameter, log λ und Dmax, gestartet aus einem Latin-Hypercube-Screening
- 📐 **Marginale Likelihood** nach Hansen (2000): Die Spline-Koeffizienten werden analytisch herausintegriert; Dmax variiert ohne neue Quadratur (skalierte Spline-Tabelle)
- 📊 Neuer Tab **„Unsicherheit“**: Median/68 %/95 %, R̂, Corner-Plot, Ketten, Posterior-Bänder für p(r), I(q) und S(q)
- 🚩 **DREAM-Flags**: Konvergenz, nicht bestimmbare Parameter, Masse an Priorgrenzen, starke Korrelationen, Multimodalität, Dmax-Posterior vs. π/q_min
- 🧾 Sidecar mit den Aktivitäten `screening` und `dream`; `_GIFT_dream.npz` und `_GIFT_pr_band.dat`; „Einstellungen aus Sidecar“ wiederholt auch DREAM (bitgleich)

**Vollständige Änderungen:** Siehe [CHANGELOG_v7.12.md](CHANGELOG_v7.12.md)

---

## 🎉 Was ist neu in v7.11?

**Minor Release v7.11.0** — Parallelisierung der GIFT-Rechnung

### Hauptfeatures v7.11

- 🚀 **BSSA-Mehrfachstarts parallel** im persistenten Prozess-Pool (RMSA-Beispiel: 11.4 s → 5.5 s)
- 🎯 **Bitgleich unabhängig von der Prozesszahl**: Seeds hängen an den Starts, BLAS rechnet im Pool einfädig
- 🪟 **Windows-tauglich**: Worker starten ohne erneuten Import des Hauptprogramms (kein PySide6 in den Workern)
- 🧮 **Vektorisierte Batch-Likelihood** als Grundlage für DREAM
- ⚙️ Neues Feld „Prozesse“ im GIFT-Bereich des Dialogs

**Vollständige Änderungen:** Siehe [CHANGELOG_v7.11.md](CHANGELOG_v7.11.md)

---

## 🎉 Was ist neu in v7.10?

**Minor Release v7.10.0** — GIFT für geladene Systeme (RMSA)

### Hauptfeatures v7.10

- ⚡ **Neues Strukturfaktor-Modell „Geladene Kugeln, RMSA“**: Hayter-Penfold-MSA mit Rescaling nach Hansen & Hayter (Fritz, Bergmann & Glatter 2000); Temperatur, Salz und ε_r standardmäßig fest
- ✅ **Validiert** gegen die sasmodels-Referenzwerte und eine SasView-Simulation (Abweichung < 10⁻⁵)
- 🎯 **BSSA-Mehrfachstart** (4 bzw. 8 unabhängige Läufe) gegen Nebenminima der MD-Fläche, mit Flag zur Übereinstimmung
- 🧾 Debye-Länge, κσ, Kontaktpotential und Rescaling-Faktor in Ergebnisanzeige und Sidecar

**Vollständige Änderungen:** Siehe [CHANGELOG_v7.10.md](CHANGELOG_v7.10.md) · Lizenzhinweise: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)

---

## 🎉 Was ist neu in v7.9?

**Minor Release v7.9.0** — GIFT: generalisierte indirekte Fourier-Transformation mit Strukturfaktor

### Hauptfeatures v7.9

- 🧮 **GIFT-Modus im P(r)-Dialog**: Formfaktor (modellfrei, p(r)) und Strukturfaktor S(q) werden gleichzeitig bestimmt — für konzentrierte, wechselwirkende Systeme (Brunner-Popela & Glatter 1997)
- ⚛️ **Strukturfaktoren**: Harte Kugeln Percus-Yevick sowie der gemittelte S_ave(q) mit Polydispersität μ (empfohlen, Weyerich et al. 1999)
- 🔥 **BSSA-Optimierer** (Bergmann et al. 2000) im Hintergrund-Thread mit Fortschritt und Abbrechen; reproduzierbar über Seed
- 📊 **Neue Tabs** „S(q) & P(q)“ und „BSSA-Verlauf“, zusätzliche Flags (Parameter am Rand, S(q) < 0, Verbesserung gegenüber S = 1)
- 🧾 **Provenance**: neue Aktivität `gift_bssa` mit allen Einstellungen, Seed und Ergebnissen; Export zusätzlich von S(q) und P(q)

**Vollständige Änderungen:** Siehe [CHANGELOG_v7.9.md](CHANGELOG_v7.9.md)

---

## 🎉 Was ist neu in v7.8?

**Minor Release v7.8.0** — P(r) per indirekter Fourier-Transformation (IFT, Glatter 1977) mit Provenance-Sidecar

### Hauptfeatures v7.8

- 🔬 **Neues Menü „Analyse → P(r) berechnen (IFT/GIFT)…“** (`Strg+Umschalt+G`, auch per Rechtsklick auf einen Datensatz): modellfreie Berechnung der Paarabstandsverteilung p(r) mit kubischen B-Splines, automatischer Wahl des Stabilisierungsparameters λ nach Glatters Wendepunkt-Methode, Fehlerbändern für p(r) und Fit sowie Rg und I(0) mit Unsicherheiten
- 📏 **q-Fitbereich aus der Signifikanzanalyse**: voller Bereich, 1σ/2σ/3σ-Voreinstellung (gleiche Rechnung wie im Significance-Plot) oder manuell
- 🚦 **Plausibilitäts-Flags**: u. a. Dmax > π/q_min, Shannon-Kanäle, fehlender Wendepunkt, Anpassungsgüte, p(r) am Rand/negativ/oszillierend, Vergleich mit Guinier-Rg
- 🧾 **Provenance-Sidecar** nach dem Vorbild von JADE-DLS: SHA-256 von Daten und Ergebnissen, lückenlose Aktivitätenkette, record_id in jeder Ergebnisdatei; „Analyse → Provenance-Sidecar prüfen…“ und „Einstellungen aus Sidecar…“ für die Reproduzierbarkeit
- 📈 **Übernehmen** legt automatisch eine PDDF-Gruppe (Daten + IFT-Fit + p(r)) an und wechselt in den PDDF-Plot

**Vollständige Änderungen:** Siehe [CHANGELOG_v7.8.md](CHANGELOG_v7.8.md)

---

## 🎉 Was ist neu in v7.7?

**Minor Release v7.7.0** — Titel- und Achsen-Dialog jetzt subplot-fähig

### Hauptfeatures v7.7

- ⚙️ **Achsen und Limits-Dialog mit Subplot-Bereich**: Eigener Y-Achsentitel, Y-Limits und Y-Skala (Auto/Linear/Log) für die untere Subplot-Achse (PDDF P(r), ASAXS-Cross-Term, Significance); beim PDDF-Subplot zusätzlich eigener X-Achsentitel und X-Limits, da die r-Achse unabhängig vom Hauptplot ist
- 📝 **Optionaler Subplot-Titel** im Titel-Editor: eigener Titel oberhalb des unteren Subplot-Bereichs, unabhängig vom figurweiten Haupttitel
- 💾 **Session-Persistenz**: Neue Subplot-Achseneinstellungen werden beim Speichern/Laden von Sessions mitgesichert (mit Backward-Compat für ältere Session-Dateien)

**Vollständige Änderungen:** Siehe [CHANGELOG_v7.7.md](CHANGELOG_v7.7.md)

---

## 🎉 Was ist neu in v7.6?

**Minor Release v7.6.0** — Neuer Plot-Typ „Significance" (Signifikanz-Subplot)

### Hauptfeatures v7.6

- 📊 **Neuer Plot-Typ „Significance"**: Zeigt neben den I(q)-Daten (Hauptplot mit Fehlerband) einen Subplot mit der punktweisen Signifikanz |I(q)/σ(q)| — dünn als Rohkurve, dick als gleitender Median geglättet (robust gegen einzelne Ausreißer). So lässt sich direkt ablesen, bis zu welchem q-Wert eine Kurve noch statistisch belastbar ist
- 📏 **Einstellbare σ-Schwellenlinien**: Gestrichelte Referenzlinien (Standard 3σ/2σ/1σ) im Subplot, Schwellenwerte und Glättungsfenster frei einstellbar im Options-Panel
- 🎯 **Subplot-Routing berücksichtigt**: Gruppen mit `subplot_target = "nur Hauptplot"` werden aus dem Signifikanz-Subplot ausgeblendet, analog zum bestehenden ASAXS/PDDF-Mechanismus

**Vollständige Änderungen:** Siehe [CHANGELOG_v7.6.md](CHANGELOG_v7.6.md)

---

## 🎉 Was ist neu in v7.5?

**Minor Release v7.5.0** — ASAXS Symlog-Skala, PDDF-Subplot-Routing-Fixes

### Hauptfeatures v7.5

- 📈 **Symlog-Skala für ASAXS**: Der ASAXS-Hauptplot zeigt negative Cross-Term-Werte jetzt auch bei log-artiger Skalierung, statt sie zu verwerfen. Feinsteuerung über „Dekaden bis Null" und „Größe des linearen Bereichs" im Achsen-Dialog
- 🩹 **PDDF-Subplot-Routing korrigiert**: Gemischte Gruppen (Rohdaten + Fit im q-Raum zusammen mit P(r) im r-Raum, typisch für GIFT/GNOM-Exporte aus SASview) werden jetzt pro Datensatz der richtigen Achse zugeordnet, statt fälschlich auf beiden Achsen dupliziert zu werden
- 🩹 **P(r)-Datenfilterung korrigiert**: Der r=0-Startpunkt und leicht negative P(r)-Werte im Tail-Bereich (normales GIFT/GNOM-Verhalten) werden nicht mehr fälschlich aus dem Plot entfernt

**Vollständige Änderungen:** Siehe [CHANGELOG_v7.5.md](CHANGELOG_v7.5.md)

---

## 🎉 Was ist neu in v7.4?

**Minor Release v7.4.0** — Flexible Spaltenzuordnung, dlnI/dlnq-Plot, Gruppen-Sichtbarkeit

### Hauptfeatures v7.4

- 🧮 **Flexible Spaltenzuordnung**: Neue Sektion „Datenspalten" im „Kurve bearbeiten"-Dialog erlaubt bei Dateien mit mehr als 2 Spalten die freie Wahl, welche Spalte als X, Y und Fehler verwendet wird — nützlich bei 4-Spalten-Dateien oder abweichender Spaltenreihenfolge. Standardauswahl bleibt abwärtskompatibel zum bisherigen Verhalten
- 📉 **Neuer Plot-Typ „dlnI/dlnq"**: Stellt die logarithmische Ableitung d ln(I)/d ln(q) gegen q dar, um versteckte Schultern und Features in Streukurven aufzudecken. Einstellbares Savitzky-Golay-Glättungsfenster reduziert Rauschen in realen Messdaten
- 👁️ **Gruppen-Sichtbarkeit**: Neue Checkbox auf Gruppen-Ebene im Datensatz-Baum blendet komplette Gruppen im Plot ein oder aus — bisher nur für einzelne Kurven möglich

**Vollständige Änderungen:** Siehe [CHANGELOG_v7.4.md](CHANGELOG_v7.4.md)

---

## 🎉 Was ist neu in v7.3?

**Minor Release v7.3.2** — ASAXS-Analyse, SNR-Qualitätsmarker, Subplot-Routing, Unified Editor

### Hauptfeatures v7.3

- 🔬 **ASAXS Plot-Typ**: Neuer spezialisierter Log-Log-Plot für anomale Kleinwinkelröntgenstreuung mit automatischer Term-Erkennung (`_IN`, `_Icross`, `_IA`) aus dem Dateinamen und optionalem linearen Subplot für den Cross-Term I_cross (inkl. negativer Werte)
- 📊 **SNR-Qualitätsmarker**: Datenpunkte werden nach SNR = |y|/σ visuell differenziert — gute Punkte (SNR ≥ Schwellenwert) als gefüllter Marker, schlechte Punkte als offener, gedimmter Marker. Für alle Plot-Typen verfügbar, konfigurierbar per Datensatz
- 🎯 **Subplot-Routing per Gruppe**: Jede Gruppe kann individuell in Hauptplot, Subplot oder beiden Bereichen gezeigt werden — relevant für ASAXS und PDDF
- 🎨 **Unified Curve & Preset Editor**: Der „Kurve bearbeiten"-Dialog und der Stil-Vorlagen-Editor im Design-Manager sind vollständig vereinheitlicht — Stil-Vorlagen enthalten jetzt alle Fehlerbalken- und SNR-Einstellungen
- 🐛 **Drag & Drop Bugfix**: Gruppenfarben werden beim Zuweisen eines Datensatzes nicht mehr fälschlicherweise zurückgesetzt

### Aktuelles Update v7.3.2 (13. Mai 2026)

- ✅ `StylePresetEditDialog` durch vollständigen `CurveSettingsDialog` (preset_mode) ersetzt
- ✅ Alle hardcodierten deutschen Strings im CurveSettingsDialog durch `tr()` ersetzt
- ✅ Neue i18n-Abschnitte: `quality`, `subplot`, `asaxs`, `preset_meta`, Fehlerbalken-Info-Texte
- ✅ Bugfix: Doppelter `errorbar_alpha`-Widget in CurveSettingsDialog entfernt
- ✅ `apply_style_preset()` wendet jetzt alle Fehlerbalken- und SNR-Einstellungen an
- ✅ Neue Stil-Vorlage öffnet sofort den vollständigen Editor

### v7.3.1 (12. Mai 2026)

- ✅ Neuer Plot-Typ „ASAXS" mit Log-Log-Haupt-Plot und optionalem linearen Subplot
- ✅ Auto-Erkennung des ASAXS-Terms aus dem Dateinamen
- ✅ SNR-Qualitätsmarker für alle Datensätze (konfigurierbar pro Datensatz)
- ✅ Subplot-Routing: `group.subplot_target` steuert Rendering-Ziel
- ✅ Drag & Drop Farb-Reset-Bugfix in `unify_group_colors()`

**Vollständige Änderungen:** Siehe [CHANGELOG_v7.3.md](CHANGELOG_v7.3.md)

---

## 🎉 Was ist neu in v7.1?

**Minor Release v7.1.2** — Vollständiger 2D-SAXS-Analyzer + Qualitätsupdates

### Hauptfeatures v7.1

- 🔬 **2D SAXS Viewer**: NeXus/HDF5-Dateien laden und in 4 Ansichten analysieren (q-Map, Polarkarte, Azimutalprofil, Sektor-Integral)
- 🎯 **q-Ring-Selektor**: Zwei ziehbare Linien in der Polarkarte setzen die Integrationsgrenzen für das Azimutalprofil direkt im Plot
- 📐 **sin(φ)-Korrektur**: Lorentz-Korrektur (I/sin φ) und Jacobi-Gewichtung (I·sin φ) mit drei Polbehandlungen: Maskierung, Epsilon-Clamp und Voigt-Extrapolation
- 🎨 **Farbskala-Schieberegler**: Interaktive vmin/vmax-Kontrolle per Perzentil-Slider ohne Neuberechnung des Histogramms
- 📤 **Integrierter Export**: 2D-Export nutzt den bestehenden ExportSettingsDialog mit Metadaten-Unterstützung
- 🔁 **1D-Transfer**: Azimutalprofil und Sektor-Integral direkt in den 1D-Datensatz-Baum übernehmen

### Aktuelles Update v7.1.2 (30. April 2026)

**Azimutalprofil im 1D-Plotter:**
- ✅ Neuer Plot-Typ „Azimuthal Profile" (φ [°] / I [a.u.], lineare Achsen)
- ✅ Automatische X-Limits −180…180° bei aktiviertem Auto-Scaling
- ✅ Y-Achsen-Skala-Override im Achsen-Dialog (Auto / Linear / Logarithmisch)
- ✅ Tastenkürzel Ctrl+Shift+8 für Azimutalprofil
- ✅ Auto-Style-Erkennung für azim*/azimuthal*-Dateien (→ Messung-Stil)

### v7.1.1 (29. April 2026)

**Qualitätsupdates für den 2D-Analyzer:**
- ✅ Farbskala-Schieberegler für q-Map und Polar Map (live, ohne Neuberechnung)
- ✅ PNG-Export über ExportSettingsDialog (Metadaten, DPI, Format)
- ✅ Optional: q-Ring-Overlay beim Export ein-/ausblenden
- ✅ sin(φ)-Korrektur mit Voigt-Polextrapolation (scipy)
- ✅ Colorbar-Textfarbe im Dark-Theme korrigiert (weiß statt schwarz)

### Erstes 7.1-Release v7.1.0 (29. April 2026)

**2D SAXS Viewer:**
- ✅ NeXus/HDF5-Unterstützung (.h5 und .h5z)
- ✅ Kartesische q-Map und logarithmische Polarkarte
- ✅ Interaktiver q-Ring-Selektor mit Drag & Drop
- ✅ Azimutalprofil I(φ) und Sektor-Integral I(|q|)
- ✅ Session-Persistenz für 2D-Datensätze

**Vollständige Änderungen:** Siehe [CHANGELOG_v7.1.md](CHANGELOG_v7.1.md)

---

## 🎉 Was ist neu in v7.0?

**Major Release v7.0.4** mit wissenschaftlicher Text-Unterstützung und internationalem Support:

### Hauptfeatures v7.0

- 📝 **LaTeX/MathText**: Wissenschaftliche Notation überall (Legenden, Achsen, Annotations)
- 🌍 **Mehrsprachigkeit**: Vollständige Deutsch/Englisch-Lokalisierung
- 📊 **Advanced Export**: Live-Vorschau + XMP-Metadaten-System
- ⌨️ **Keyboard Shortcuts**: Effizienter Workflow
- 🔧 **UI-Verbesserungen**: Tree-Reihenfolge bestimmt Legende
- 🖼️ **TIFF-Export**: Zusätzliches hochwertiges Format
- 🐛 **Stabilitätsverbesserungen**: Kritische Bugfixes in v7.0.2-7.0.4

**Vollständige Änderungen:** Siehe [CHANGELOG_v7.0.md](CHANGELOG_v7.0.md)

---

## 🛠️ Installation

### Voraussetzungen

- Python 3.8 oder höher
- PySide6 (Qt6 für Python)
- Matplotlib
- NumPy

### Installation via Git

```bash
# Repository klonen
git clone https://github.com/traianuschem/ScatteringPlot.git
cd ScatteringPlot

# Abhängigkeiten installieren
pip install -r requirements.txt

# Programm starten
python scatter_plot.py
```

### Requirements

```txt
PySide6>=6.5.0
matplotlib>=3.5.0
numpy>=1.20.0
scipy>=1.7.0
h5py>=3.0
```

---

## ⚡ Schnellstart (5 Minuten)

### Ihr erster Plot in 5 Schritten

```
1. ✅ Programm starten: python scatter_plot.py
2. 📁 Daten laden: Strg+O → .dat/.csv/.txt Dateien auswählen
3. 📊 Plot-Typ wählen: Dropdown "Log-Log" (Standard)
4. 🎨 Kurve formatieren: Rechtsklick auf Dataset → "Kurve bearbeiten"
5. 💾 Exportieren: Strg+E → Format wählen → Speichern
```

**Fertig!** Sie haben Ihren ersten wissenschaftlichen Plot erstellt.

### Nächste Schritte

- **Gruppen erstellen:** Organisieren Sie mehrere Datensätze → [Gruppen-Management](#3-gruppen-organisieren-alleinstellungsmerkmal)
- **Metadaten hinzufügen:** Autor, Projekt, Lizenz → [Metadaten-System](#benutzer-metadaten-system)
- **Session speichern:** Projekt für später sichern → `Strg+S`

---

## 📖 Benutzerhandbuch

Folgen Sie dem typischen Workflow von Datenimport bis Export.

---

### 1. Daten laden

#### Unterstützte Formate

ScatterForge Plot liest ASCII-Dateien mit Whitespace-getrennten Spalten:

**2-Spalten-Format** (q, I):
```
# q / nm^-1    I / a.u.
0.1            1000.5
0.2            856.3
0.3            723.1
```

**3-Spalten-Format** (q, I, I_err):
```
# q / nm^-1    I / a.u.    I_err
0.1            1000.5      15.2
0.2            856.3       12.8
0.3            723.1       10.5
```

**4+ Spalten (v7.4.0):** Dateien mit mehr als 3 Spalten werden vollständig eingelesen.
Standardmäßig wird bei 4 Spalten `x, y, x_err, y_err` angenommen (x_err wird ignoriert,
y_err aus Spalte 4 verwendet) — bei abweichendem Aufbau lässt sich die Zuordnung manuell
korrigieren (siehe unten).

**Hinweise:**
- Dateierweiterungen: `.dat`, `.txt`, `.csv`
- Kommentarzeilen beginnen mit `#`
- Dezimaltrennzeichen: Punkt (`.`)
- Fehler-Spalte optional

#### Spaltenzuordnung anpassen (v7.4.0)

Bei Dateien mit mehr als 2 Spalten kann festgelegt werden, welche Spalte als X, Y und
Fehler verwendet wird — etwa wenn die Reihenfolge von der Standardannahme abweicht oder
zusätzliche, nicht benötigte Spalten enthalten sind.

```
Rechtsklick auf Dataset → "🎨 Kurve bearbeiten..." → Abschnitt "Datenspalten"
→ X-Spalte, Y-Spalte, Fehler-Spalte ("Keine" möglich) wählen → OK
```

**Hinweise:**
- Nur sichtbar bei Dateien mit mehr als 2 Spalten und nur im Einzel-Dataset-Editor
  (nicht bei Gruppen-Bearbeitung, da das Spaltenlayout dateispezifisch ist)
- Änderung wird sofort auf den Plot angewendet, ohne die Datei erneut einzulesen
- Wird in der Session gespeichert

#### Daten importieren

**Methode 1: Menü**
```
Datei → Daten laden... → Dateien auswählen
```

**Methode 2: Keyboard**
```
Strg+O → Dateien auswählen
```

**Methode 3: Drag & Drop** (geplant für v7.1)

**Nach dem Import:**
- Datasets erscheinen in der Kategorie "Nicht zugeordnet"
- Automatische Stil-Erkennung anhand Dateinamen:
  - `*messung*.dat` → Messung-Stil (Marker + transparente Fehlerfläche)
  - `*fit*.dat` → Fit-Stil (durchgezogene Linie)
  - `*sim*.dat` → Simulation-Stil (gestrichelt)
  - `*theo*.dat` → Theorie-Stil (Strich-Punkt)

---

### 2. Plot-Typ wählen

ScatterForge Plot bietet 11 spezialisierte Plot-Typen für verschiedene Analysen:

| Plot-Typ | X-Achse | Y-Achse | Anwendung |
|----------|---------|---------|-----------|
| **Log-Log** | q [nm⁻¹] | I [a.u.] | Standard-Streukurven (logarithmisch) |
| **Porod** | q [nm⁻¹] | I·q⁴ [a.u.] | Grenzflächenanalyse, Oberflächen-Fraktale |
| **Kratky** | q [nm⁻¹] | I·q² [a.u.] | Kompaktheit, Faltungszustand |
| **Guinier** | q² [nm⁻²] | ln(I) | Trägheitsradius Rg bestimmen |
| **Bragg Spacing** | d [nm] | I [a.u.] | Realraum-Darstellung (d = 2π/q) |
| **2-Theta** | 2θ [°] | I [a.u.] | XRD-Winkeldarstellung |
| **PDDF** | r [nm] | p(r) | Paardistanzverteilungsfunktion |
| **Azimuthal Profile** | φ [°] | I [a.u.] | Azimutale Intensitätsprofile aus 2D-Daten |
| **ASAXS** | q [nm⁻¹] | I [cm⁻¹] | Anomale SAXS-Separation (I_N, I_cross, I_A) |
| **dlnI/dlnq** | q [nm⁻¹] | d ln(I)/d ln(q) | Versteckte Features/Schultern in Streukurven identifizieren |
| **Significance** | q [nm⁻¹] | I [a.u.] | Hauptplot wie Log-Log; Subplot zeigt |I(q)/σ(q)| zur Beurteilung des vertrauenswürdigen q-Bereichs |

**Plot-Typ wechseln:**
```
Dropdown "Plot-Typ" → Typ auswählen
oder
Strg+1 bis Strg+7 (Tastaturkürzel)
```

**ASAXS-Spezial-Einstellungen:**
```
1. Plot-Typ „ASAXS" wählen
2. Datensätze laden → Term-Typ wird auto-erkannt (_IN, _Icross, _IA)
3. „± Subplot" Button aktivieren für linearen I_cross-Subplot
4. Per Rechtsklick → „Kurve bearbeiten" → ASAXS: Term-Typ manuell überschreiben
```

**2-Theta Spezial-Einstellung:**
```
Ansicht → 2-Theta-Einstellungen...
→ Wellenlänge einstellen (Standard: Cu K-alpha = 0.1524 nm)
```

**dlnI/dlnq-Spezial-Einstellung (v7.4.0):**
```
1. Plot-Typ „dlnI/dlnq" wählen
2. Glättungsfenster im Options-Panel einstellen (Savitzky-Golay, Standard: 5)
   → größer = glatter, kann aber feine Features abschwächen
```

**Significance-Spezial-Einstellung (v7.6.0):**
```
1. Plot-Typ „Significance" wählen
2. Hauptplot zeigt I(q) + Fehlerband wie gewohnt; Subplot zeigt |I(q)/σ(q)|
   → dünn: Rohdaten, dick: gleitender Median (Ausreißer-robust)
3. Im Options-Panel einstellbar:
   - Signifikanz-Fenster (Punkte, ungerade, Standard: 9)
   - σ-Schwellen (kommagetrennt, Standard: „3,2,1") → gestrichelte Linien im Subplot
```

---

### 3. Gruppen organisieren (Alleinstellungsmerkmal)

**Das Gruppen-System ist das Herzstück von ScatterForge Plot!**

#### Was sind Gruppen?

Gruppen organisieren Datasets und ermöglichen:
- **Stack-Faktoren**: Kurven vertikal trennen (nicht-kumulativ!)
- **Batch-Formatierung**: Alle Kurven einer Gruppe gleichzeitig formatieren
- **Farbpaletten**: Gruppenspezifische Farbschemata
- **Übersichtlichkeit**: Strukturierte Organisation vieler Datensätze

#### Stack-Faktoren verstehen

**WICHTIG: Nicht-kumulative Multiplikatoren!**

```
Gruppe A (Stack-Faktor: ×1)      → y_plot = y_original × 1
Gruppe B (Stack-Faktor: ×10)     → y_plot = y_original × 10
Gruppe C (Stack-Faktor: ×100)    → y_plot = y_original × 100
```

**Nicht** wie bei kumulativen Stacks:
```
❌ Gruppe C würde NICHT ×1000 sein (10 × 10 × 10)
✅ Gruppe C ist IMMER ×100 (direkt)
```

**Vorteil:** Präzise Kontrolle über Kurvenseparation in Log-Plots!

#### Gruppe erstellen (Manuell)

```
1. Button "➕ Gruppe" klicken
2. Gruppen-Name eingeben (z.B. "Konzentration 1 mg/ml")
3. Stack-Faktor setzen (z.B. 1, 10, 100, ...)
4. Datasets per Drag & Drop in Gruppe ziehen
```

**Tastaturkürzel:** `Strg+G`

#### Auto-Gruppierung (Empfohlen!)

Perfekt für viele Datensätze:

```
1. Datasets in "Nicht zugeordnet" auswählen (Strg+Klick für Mehrfachauswahl)
2. Button "🔢 Auto-Gruppieren" klicken
3. ✅ Fertig!
```

**Ergebnis:**
- Jedes Dataset bekommt eigene Gruppe
- Automatische Stack-Faktoren: 10⁰, 10¹, 10², 10³, ...
- Gruppen-Name = Dataset-Name

**Tastaturkürzel:** `Strg+A`

#### Gruppen-Bearbeitung

**Gruppe umbenennen:**
```
Doppelklick auf Gruppennamen → Neuen Namen eingeben → Enter
```

**Stack-Faktor ändern:**
```
Rechtsklick auf Gruppe → "Stack-Faktor ändern..." → Wert eingeben
```

**Alle Kurven einer Gruppe formatieren:**
```
Rechtsklick auf Gruppe → "Gruppe bearbeiten..."
→ Farbe, Marker, Linie, Fehlerbalken für ALLE Datasets setzen
```

**Gruppenspezifische Farbpalette:**
```
Rechtsklick auf Gruppe → "Farbpalette wählen..."
→ Palette auswählen (z.B. "viridis", "plasma", "TUBAF")
→ Datasets in dieser Gruppe nutzen nur diese Palette
```

**Gruppe ein-/ausblenden (v7.4.0):**
```
Checkbox vor dem Gruppennamen im Baum an-/abwählen
```

Blendet alle Kurven der Gruppe inkl. Legendeneintrag komplett aus dem Plot aus —
unabhängig vom Sichtbarkeits-Status der einzelnen Kurven darin. Praktisch, um bei vielen
Gruppen gezielt einzelne Messreihen temporär aus dem Plot zu nehmen, ohne sie zu löschen.

#### Datasets zwischen Gruppen verschieben

**Drag & Drop:**
```
Dataset anklicken → Gedrückt halten → Auf Zielgruppe ziehen → Loslassen
```

**Aus Gruppe entfernen:**
```
Dataset auf "Nicht zugeordnet" ziehen
```

#### Gruppen löschen

```
Rechtsklick auf Gruppe → "Gruppe löschen"
→ Datasets wandern zurück nach "Nicht zugeordnet"
```

**Tastaturkürzel:** `Entf` (Gruppe auswählen, dann Entf drücken)

---

### 4. Kurven gestalten

#### Kurven-Editor (Umfassend)

Der Kurven-Editor gibt Ihnen vollständige Kontrolle über alle visuellen Eigenschaften:

```
Rechtsklick auf Dataset → "🎨 Kurve bearbeiten..."
```

**Tastaturkürzel:** `Strg+K`

**Einstellungen im Dialog:**

**1. Farbe**
- Farbwähler für beliebige RGB-Farben
- Schnellauswahl aus aktueller Palette (bis zu 10 Farben)
- "Farbe zurücksetzen" für automatische Zuweisung

**2. Marker**
- 13 Stile: Kreis (o), Quadrat (s), Dreieck (^,v,<,>), Raute (D), Stern (*), Plus (+), Kreuz (x), Punkt (.), Pixel (,)
- Größe: 0-20 pt (Standard: 4)
- "Kein Marker" für reine Linien

**3. Linie**
- 5 Stile: Durchgezogen (-), Gestrichelt (--), Strich-Punkt (-.), Gepunktet (:), Keine
- Breite: 0-10 pt (Standard: 2)

**4. Fehlerbalken**
- **Darstellung:**
  - **Transparente Fläche** (`fill_between`): Ideal für dichte Datenpunkte
  - **Balken mit Caps** (`errorbar`): Klassische Darstellung
  - **Stem/Anker**: Vertikale Linien von der x-Achse (XRD-Reflexmuster)
- **Transparenz:** 0-100% (Standard: 30%)
- **Cap-Größe:** 0-10 pt (nur bei Balken)
- **Linienbreite:** 0.1-5 pt (bei Balken und Stem)

**5. SNR-Qualitätsmarker** (benötigt Fehlerdaten)
- Aktivieren unter „Datenqualität" im Kurven-Dialog
- Punkte mit SNR ≥ Schwellenwert: gefüllter Marker
- Punkte mit SNR < Schwellenwert: offener Marker, gedimmt
- Konfigurierbar: Schwellenwert, Marker-Stile, Transparenz, Fehlerbalken

#### Schnellfarben

Schneller Zugriff auf Farben der aktuellen Palette:

```
Rechtsklick auf Dataset → "Schnellfarben" → Farbe wählen
```

**Vorteil:** Sofortige Anwendung ohne Dialog!

#### Stil-Vorlagen anwenden

Vordefinierte Stile für typische Datentypen:

```
Rechtsklick auf Dataset → "Stil anwenden" → Stil wählen:
- Messung (Marker + transparente Fehlerfläche)
- Fit (durchgezogene Linie, keine Marker)
- Simulation (gestrichelte Linie)
- Theorie (Strich-Punkt-Linie)
```

#### Stil-Vorlagen bearbeiten (v7.3.2)

Vollständiger Editor — identisch mit dem Kurven-Dialog:

```
Design → Design-Manager... → Tab "Stil-Vorlagen" → Vorlage auswählen → "Bearbeiten..."
```

**Einstellbar in der Vorlage:**
- Name und Beschreibung
- Marker-Stil und -Größe
- Linien-Stil und -Breite
- Fehlerbalken (Stil, Cap-Größe, Linienbreite, Transparenz)
- SNR-Qualitätsmarker (Schwellenwert, Marker, Transparenz)

#### Individuelle Plotgrenzen

Pro Dataset eigene X/Y-Limits setzen:

```
Rechtsklick auf Dataset → "Plotgrenzen setzen..."
→ X-Min, X-Max, Y-Min, Y-Max eingeben
```

**Anwendung:**
- Unerwünschte Datenbereiche ausblenden
- Auf interessanten Bereich zoomen
- Pro Dataset individuell

---

### 5. Plot formatieren

#### Legenden

**Legende bearbeiten:**
```
Legende → Legende bearbeiten...
```

**Tastaturkürzel:** `Strg+M`

**Funktionen:**
- Einträge umbenennen (unabhängig von Dataset-Namen)
- LaTeX/MathText-Formatierung (`Sample_{1}`, `I·q^{2}`)
- Fett/Kursiv pro Eintrag
- Reihenfolge per Drag & Drop im Tree ändern

**Legenden-Einstellungen:**
```
Legende → Legende-Einstellungen...
```

**Optionen:**
- Position: 9 vordefinierte Positionen
- Spalten: 1-4
- Transparenz: 0-100%
- Rahmen, Schatten

**Wichtig:** Tree-Reihenfolge = Legendenreihenfolge (v7.0)!

#### Achsen

**Achsen-Einstellungen:**
```
Achsen → Achsen-Einstellungen...
```

**Tastaturkürzel:** `Strg+U`

**Funktionen:**
- Achsenbeschriftungen anpassen (LaTeX-Support!)
- Tick-Parameter (Major/Minor)
- Scientific Notation ein/aus
- **Achsenlimits** (feste X/Y-Bereiche)
- Unit-Format-Konvertierung (nm ↔ Å)

**Achsenlimits setzen:**
```
Im Achsen-Dialog:
→ Tab "Limits"
→ X-Min, X-Max, Y-Min, Y-Max
→ Checkbox "Feste Limits verwenden"
```

**Vorteil:** Limits bleiben beim Plot-Update erhalten!

#### Grid

**Grid-Einstellungen:**
```
Grid → Grid-Einstellungen...
```

**Tastaturkürzel:** `Strg+I`

**Optionen:**
- Major/Minor Grid separat steuerbar
- Linienstile und Farben
- Anzeigen/Ausblenden

#### Plot-Titel

**Titel bearbeiten:**
```
Ansicht → Titel bearbeiten...
```

**Tastaturkürzel:** `Strg+T`

**Features:**
- LaTeX/MathText-Support
- Live-Vorschau
- Font-Einstellungen (Größe, Fett, Kursiv)

#### Annotations & Referenzlinien

**Annotation hinzufügen:**
```
Annotations → Annotation hinzufügen...
→ Text, Position, Farbe, Größe
```

**Features:**
- LaTeX/MathText-Unterstützung
- Interaktiv verschiebbar (Drag & Drop)
- Rotation

**Referenzlinie hinzufügen:**
```
Annotations → Referenzlinie hinzufügen...
→ Vertikal/Horizontal, Position, Farbe
```

**Anwendung:**
- Peak-Markierung in XRD-Plots
- Theoretische Werte anzeigen
- Grenzwerte markieren

---

### 6. Exportieren (mit Metadaten)

#### Benutzer-Metadaten-System

**Das zweite Alleinstellungsmerkmal!**

ScatterForge Plot bietet ein umfassendes Metadaten-System für wissenschaftliche Publikationen:

**Benutzer-Profil einrichten:**
```
Datei → Benutzer-Metadaten...
```

**Eingaben:**
- **Autor:** Ihr Name
- **Institution:** Universität/Institut
- **E-Mail:** Kontakt
- **Projekt:** Projektname
- **Beschreibung:** Kurzbeschreibung
- **Copyright:** Copyright-Hinweis
- **Lizenz:** CC-BY, CC0, proprietary, etc.
- **Keywords:** Stichwörter (kommagetrennt)

**Vorteil:** Einmal eingeben, bei jedem Export verwendet!

**Speicherort:** `~/.tubaf_scatter_plots/config.json`

#### Export-Dialog

**Export starten:**
```
Datei → Exportieren...
```

**Tastaturkürzel:** `Strg+E`

**Export-Dialog Features:**

**1. Live-Vorschau**
- Echtzeit-Ansicht während Konfiguration
- Zoom & Pan
- Was Sie sehen = Was Sie bekommen

**2. Format wählen**

| Format | Verwendung | Metadaten |
|--------|------------|-----------|
| PNG | Präsentationen, Web | tEXt chunks |
| TIFF | Publikationen, Druck | TIFF tags  |
| PDF | Dokumente | PDF Info + XMP |
| SVG | Vektorgrafik | XML + XMP |
| EPS | LaTeX-Dokumente | Comments + XMP |

**3. Größe & Auflösung**
- Vordefinierte Formate: 16:10 (25.4×15.875 cm), 4:3
- Custom-Größe
- DPI: 300, 600, 900, 1200

**4. Metadaten überprüfen**
- Automatisch aus Benutzer-Profil geladen
- Im Export-Dialog noch anpassbar
- Keywords hinzufügen

**5. Erweiterte Optionen**
- PNG Transparenz
- Tight Layout (automatische Rand-Optimierung)

#### XMP-Sidecar-Dateien

**Was sind XMP-Dateien?**

XMP (Extensible Metadata Platform) ist ein Adobe-Standard für Metadaten:

```
plot_export.png        ← Ihr Bild
plot_export.png.xmp    ← Metadaten-Datei
```

**Inhalt der .xmp-Datei:**
- Autor, Institution, E-Mail
- Projekt, Beschreibung
- Copyright, Lizenz
- Keywords
- Software-Version
- Erstellungsdatum
- Plot-Typ, verwendete Datasets

**Vorteil:**
- Standardisiertes Format (ISO 16684-1)
- Lesbar mit Metadaten-Browsern
- Unabhängig vom Bildformat
- Volle Rückverfolgbarkeit für Publikationen

**Workflow für Publikationen:**
```
1. Benutzer-Metadaten einmal einrichten
2. Plot erstellen und exportieren
3. .xmp-Datei zusammen mit Bild archivieren
4. Bei Fragen zur Herkunft: Metadaten prüfen
```

---

### 7. Sessions speichern

Sessions speichern den **kompletten** Projektzustand:

**Was wird gespeichert:**
- Alle geladenen Datasets (mit Pfaden)
- Gruppen mit Stack-Faktoren
- Kurven-Formatierungen (Farben, Marker, Fehlerbalken)
- Plot-Einstellungen (Legende, Grid, Achsen)
- Annotations & Referenzlinien
- Aktives Plot-Design
- Individuelle Plotgrenzen
- Farbpaletten (global + gruppenspezifisch)

**Session speichern:**
```
Datei → Session speichern...
```

**Tastaturkürzel:** `Strg+S`

**Session laden:**
```
Datei → Session laden...
```

**Tastaturkürzel:** `Strg+L`

**Format:** JSON (`.scatterforge`)

**Vorteil:** Perfekt für:
- Wiederkehrende Analysen
- Projektdokumentation
- Kollaboration (Session-Datei teilen)
- Backup vor großen Änderungen

---

## 📚 Feature-Referenz

Detaillierte Dokumentation zu ausgewählten Features.

---

### LaTeX/MathText-Unterstützung

ScatterForge Plot unterstützt vollständig LaTeX/MathText-Syntax für wissenschaftliche Notation.

#### Wo verfügbar?

- ✅ Legenden
- ✅ Achsenbeschriftungen
- ✅ Annotations
- ✅ Plot-Titel

#### Syntax-Beispiele

**Indizes:**
```
μ_exp        → μ_{exp}
R_g          → R_{g}
Sample_1     → Sample_{1}
```

**Exponenten:**
```
I·q^2        → I·q^{2}
10^-3        → 10^{-3}
nm^-1        → nm^{-1}
```

**Kombinationen:**
```
I(q) / a.u.              → I(q) / a.u.
R_g = 5.3 nm             → R_{g} = 5.3 nm
Form-Faktor P(q)         → Form-Faktor P(q)
Peak bei q* = 0.5 nm^-1  → Peak bei q^{*} = 0.5 nm^{-1}
```

**Griechische Buchstaben:**
```
\alpha, \beta, \gamma, \delta, \epsilon
\theta, \lambda, \mu, \sigma, \phi
```

#### Live-Vorschau

Alle Editoren mit LaTeX-Unterstützung zeigen eine Live-Vorschau:

```
Legende bearbeiten → Eintrag auswählen → LaTeX eingeben → Vorschau erscheint sofort
```

**Fehlerbehandlung:** Ungültige Syntax wird rot markiert.

#### Verwendung

**In Legenden:**
```
1. Legende → Legende bearbeiten...
2. Eintrag auswählen
3. LaTeX-Syntax eingeben (z.B. "Sample_{1}")
4. Live-Vorschau prüfen
5. OK
```

**In Achsenbeschriftungen:**
```
1. Achsen → Achsen-Einstellungen...
2. Tab "Beschriftungen"
3. X/Y-Label eingeben (z.B. "q / nm^{-1}")
4. Checkbox "LaTeX verwenden" aktivieren
5. OK
```

**In Annotations:**
```
1. Annotations → Annotation hinzufügen...
2. Text eingeben (z.B. "R_g = 5.3 nm")
3. Position wählen
4. OK
```

---

### Mehrsprachigkeit

ScatterForge Plot ist vollständig zweisprachig.

#### Unterstützte Sprachen

- 🇩🇪 **Deutsch** (Standard)
- 🇬🇧 **Englisch**

#### Sprache wechseln

```
Einstellungen → Einstellungen... → Sprache auswählen
```
**Persistenz:** Sprachwahl wird gespeichert und beim nächsten Start geladen.

#### Was ist übersetzt?

- Alle Menüs und Buttons
- Alle Dialoge
- Fehlermeldungen und Bestätigungen
- Tooltips

#### Eigene Sprache hinzufügen

Das i18n-System ist JSON-basiert und einfach erweiterbar:

```
i18n/
├── de.json  (Deutsch)
├── en.json  (Englisch)
└── xx.json  (Ihre Sprache)
```

Erstellen Sie eine neue `.json`-Datei nach dem Schema von `en.json`.

---

### Keyboard Shortcuts

Vollständige Referenz aller Tastaturkürzel.

#### Hauptaktionen

| Shortcut | Aktion |
|----------|--------|
| `Strg+O` | Daten laden |
| `Strg+S` | Session speichern |
| `Strg+Shift+S` | Session speichern als... |
| `Strg+L` | Session laden |
| `Strg+E` | Exportieren |
| `Strg+Q` | Beenden |

#### Gruppen & Daten

| Shortcut | Aktion |
|----------|--------|
| `Strg+G` | Neue Gruppe |
| `Strg+A` | Auto-Gruppieren |
| `Entf` | Ausgewähltes löschen |
| `F2` | Umbenennen |

#### Plot & Ansicht

| Shortcut | Aktion |
|----------|--------|
| `F5` | Plot aktualisieren |
| `Strg+1` | Log-Log |
| `Strg+2` | Porod |
| `Strg+3` | Kratky |
| `Strg+4` | Guinier |
| `Strg+5` | Bragg Spacing |
| `Strg+6` | 2-Theta |
| `Strg+7` | PDDF |

#### Editoren

| Shortcut | Aktion |
|----------|--------|
| `Strg+K` | Kurven-Editor |
| `Strg+T` | Titel bearbeiten |
| `Strg+Umschalt+G` | P(r) berechnen (IFT/GIFT) |
| `Strg+U` | Achsen-Einstellungen |
| `Strg+I` | Grid-Einstellungen |
| `Strg+M` | Legende bearbeiten |
| `Esc` | Dialog schließen |

---

### Farbpaletten & Designs

#### Globale Farbpalette

```
Dropdown "Farbschema" → Palette auswählen
```

**Verfügbare Paletten:**
- **TUBAF** (Corporate Design)
- **Matplotlib Colormaps:** tab10, tab20, Set1, Set2, Set3, Paired, viridis, plasma, inferno, magma, cividis, twilight, etc.
- **Benutzerdefiniert** (eigene Paletten erstellen)

#### Gruppenspezifische Paletten

```
Rechtsklick auf Gruppe → "Farbpalette wählen..."
```

**Verhalten:**
- Datasets in dieser Gruppe nutzen nur diese Palette
- Überschreibt globale Palette für diese Gruppe
- Fallback auf global, wenn nicht gesetzt

#### Eigene Farbpalette erstellen

```
Design → Design-Manager... → Tab "Farbschemata"
→ "Neues Schema erstellen"
→ Name + Farben definieren
```

#### Plot-Designs

Vordefinierte Design-Sets für verschiedene Anwendungen:

| Design | Beschreibung |
|--------|--------------|
| Standard | Ausgewogene Einstellungen |
| Präsentation | Große Schrift, kräftige Farben |
| Publikation | Kleine Schrift, dezente Farben |
| Poster | Sehr große Schrift |
| Minimalistisch | Reduziert auf Wesentliches |

**Design anwenden:**
```
Design → Design wählen → Design auswählen
```

**Design als Standard speichern:**
```
Design → Design-Manager... → "⭐ Als Programmstandard speichern"
```

**Vorteil:** Beim nächsten Programmstart werden diese Einstellungen automatisch geladen.

---

## ⚙️ Konfiguration

Alle Einstellungen werden in `~/.tubaf_scatter_plots/` gespeichert.

### Dateistruktur

```
~/.tubaf_scatter_plots/
├── config.json              # Hauptkonfiguration
│   ├── Benutzer-Metadaten
│   ├── Standard-Plot-Einstellungen
│   └── Sprachwahl
├── color_schemes.json       # Benutzerdefinierte Farbpaletten
├── style_presets.json       # Benutzerdefinierte Stil-Vorlagen
└── logs/                    # Log-Dateien
    └── scatterplot_20251225.log
```

### Benutzer-Metadaten bearbeiten

**Im Programm:**
```
Datei → Benutzer-Metadaten...
```

**Manuell in `config.json`:**
```json
{
  "user_metadata": {
    "author": "Dr. Max Mustermann",
    "institution": "TU Bergakademie Freiberg",
    "email": "max.mustermann@example.com",
    "project": "Nanopartikel-Analyse",
    "description": "SAXS-Messungen an Gold-Nanopartikeln",
    "copyright": "© 2025 Max Mustermann",
    "license": "CC-BY-4.0",
    "keywords": "SAXS, Gold, Nanopartikel"
  }
}
```

### Standard-Einstellungen zurücksetzen

```bash
# Config löschen (Backup empfohlen!)
rm ~/.tubaf_scatter_plots/config.json

# Beim nächsten Start werden Defaults erstellt
```

---



## Lizenz

**GPL-3.0 License**

Dieses Projekt ist unter der GNU General Public License v3.0 lizenziert.

**Was bedeutet das?**
- ✅ Kostenlos verwenden
- ✅ Quellcode einsehen und ändern
- ✅ Weitergeben (unter gleicher Lizenz)
- ❌ Proprietäre Closed-Source-Versionen erstellen

Siehe [LICENSE](LICENSE) für Details.

### Zitation

Wenn Sie ScatterForge Plot in Ihrer Forschung verwenden, zitieren Sie bitte:

```bibtex
@software{scatterforge_plot,
  author = {Richard Neubert},
  title = {ScatterForge Plot: Professional Scattering Data Visualization Tool},
  year = {2026},
  version = {7.4.0},
  url = {https://github.com/traianuschem/ScatteringPlot},
  note = {Software developed with Claude AI assistance}
}
```

### AI Transparency

The program code for ScatterForge Plot v7.0+ was written by Claude (Anthropic's AI assistant) under the orchestration and direction of Richard Neubert. This follows best practices for AI transparency in software development. All features were designed by the project owner, and all code has been thoroughly reviewed, tested, and approved.

## Kontakt & Support

**Issues:** [GitHub Issues](https://github.com/traianuschem/ScatteringPlot/issues)

**Vor dem Erstellen eines Issues:**
1. Log prüfen
2. Issue mit Log-Auszug erstellen

### Autoren

- **Richard Neubert** - *Project owner, orchestration, feature design, testing*
- **Claude (Anthropic AI)** - *Code implementation and development (v7.0+)*

---

## 📚 Weitere Ressourcen

- **CHANGELOG v7.4:** Aktuelle Versionshistorie → [CHANGELOG_v7.4.md](CHANGELOG_v7.4.md)
- **CHANGELOG v7.3:** Ältere Versionen → [CHANGELOG_v7.3.md](CHANGELOG_v7.3.md)
- **CHANGELOG v7.1:** Ältere Versionen → [CHANGELOG_v7.1.md](CHANGELOG_v7.1.md)
- **CHANGELOG v7.0:** Frühere Versionen → [CHANGELOG_v7.0.md](CHANGELOG_v7.0.md)
- **GitHub:** Repository → [traianuschem/ScatteringPlot](https://github.com/traianuschem/ScatteringPlot)
- **Releases:** Stabile Versionen → [GitHub Releases](https://github.com/traianuschem/ScatteringPlot/releases)

---

**Made with ❤️ for the scientific community**

*ScatterForge Plot v7.4.0 - Juli 2026*

---
