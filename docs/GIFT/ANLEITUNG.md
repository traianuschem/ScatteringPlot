# IFT/GIFT in ScatterForge Plot — Bedienungsanleitung

Stand: ScatterForge Plot 8.0.0 (`analysis.gift` 0.8.0). Literaturkürzel in eckigen
Klammern verweisen auf das Verzeichnis in [Abschnitt 17](#17-literatur).

Das Modul berechnet aus eindimensionalen Kleinwinkelstreudaten (SAXS/SANS) modellfrei die
Paarabstandsverteilung p(r) durch **indirekte Fourier-Transformation (IFT)** [G77].
Bei wechselwirkenden Teilchen berücksichtigt es einen Strukturfaktor über die
**generalisierte IFT (GIFT)** [BP97, W99, B00]. Darauf bauen weitere Auswertungen auf:

- Querschnitts- und Dicken-IFT [G80b]
- Größenverteilungen [G80a]
- radiale Kontrastprofile (DECON) [G81, GH84, MG98]
- statistische Absicherung aller Parameter per MCMC [H00, TV08, V16]

---

## Inhalt

1. [Start und Überblick](#1-start-und-überblick)
2. [Kurzanleitung](#2-kurzanleitung)
3. [Daten und Fehler σ](#3-daten-und-fehler-σ)
4. [q-Fitbereich](#4-q-fitbereich)
5. [IFT-Einstellungen](#5-ift-einstellungen)
6. [Ergebnisse, Tabs und Kennzahlen](#6-ergebnisse-tabs-und-kennzahlen)
7. [Explorer: Dmax und λ systematisch wählen](#7-explorer-dmax-und-λ-systematisch-wählen)
8. [GIFT: Strukturfaktoren](#8-gift-strukturfaktoren)
9. [Unsicherheit (DREAM)](#9-unsicherheit-dream)
10. [Querschnitt und Dicke](#10-querschnitt-und-dicke)
11. [Größenverteilungen](#11-größenverteilungen)
12. [DECON: radiales Kontrastprofil](#12-decon-radiales-kontrastprofil)
13. [Serienauswertung](#13-serienauswertung)
14. [Ausgabe, Provenance und Reproduktion](#14-ausgabe-provenance-und-reproduktion)
15. [Flags (Plausibilitätsprüfungen)](#15-flags-plausibilitätsprüfungen)
16. [Typische Probleme und Rezepte](#16-typische-probleme-und-rezepte)
17. [Literatur](#17-literatur)

---

## 1. Start und Überblick

**Öffnen:** Datensatz im Datenbaum markieren und dann
*Analyse → P(r) berechnen (IFT/GIFT)…* wählen oder im Kontextmenü des Datensatzes
*P(r) berechnen (IFT/GIFT)…*. Der Dialog ist nicht modal; mehrere Datensätze lassen sich
parallel auswerten.

**Aufbau des Dialogs:**

- **Links** stehen die Einstellungen:
  - Daten
  - q-Fitbereich
  - IFT
  - Strukturfaktor (GIFT)
  - Unsicherheit (DREAM)
  - Ausgabe
- **Rechts** stehen die Tabs mit den Ergebnissen:
  - I(q) & Fit
  - p(r)
  - S(q) & P(q)
  - λ-Wahl
  - Signifikanz
  - BSSA-Verlauf
  - Explorer
  - DECON
  - Unsicherheit
  - Provenance
- **Darunter** folgen die Ergebniszusammenfassung und die Liste der Flags.
- **Unten** liegen die Schaltflächen *Berechnen*, *GIFT starten*, *Abbrechen*,
  *Einstellungen aus Sidecar…*, *Serie…* und *Übernehmen*.

**Einheiten:** q in nm⁻¹, r in nm. Dateien mit q in Å⁻¹ (z. B. SasView-Export) werden über
*q-Einheit der Datei → Å⁻¹ (×10)* umgerechnet; der Faktor wird protokolliert.

**Live-Vorschau:** Ist sie aktiv, rechnet die IFT bei jeder Änderung neu (nur ohne
Strukturfaktor). GIFT, DREAM und DECON starten immer nur auf Knopfdruck.

---

## 2. Kurzanleitung

1. **Fehler prüfen:** Liegt eine Fehlerspalte vor, wird σ daraus verwendet. Sonst σ
   schätzen lassen oder relativ annehmen (Abschnitt 3).
2. **q-Bereich:** Die Voreinstellung *2σ (Signifikanz)* schneidet bei großen q ab,
   *Artefakte bei kleinem q automatisch ausschließen* entfernt problematische Punkte am
   Anfang (Abschnitt 4).
3. **Dmax:** Den Startwert setzt der Dialog selbst: aus dem Guinier-Rg bzw. über
   *Vorschlagen*. Im Tab *p(r)* sollte die Kurve vor Dmax glatt auf null auslaufen.
4. **Splines N:** *Vorschlag* wählt N aus den Shannon-Kanälen.
5. **λ:** Standard ist die Wendepunkt-Methode [G77]; Kontrolle im Tab *λ-Wahl*.
6. **Berechnen** und dann die Flags lesen. Gelbe oder rote Einträge nennen die
   wahrscheinliche Ursache.
7. **Bei Wechselwirkung:** Das zeigt sich an Oszillation von p(r), negativen Bereichen oder
   einem Korrelationsmaximum in I(q). Dann ein Strukturfaktor-Modell wählen und
   *GIFT starten* (Abschnitt 8).
8. **Optional:**
   - *Unsicherheit bestimmen* (DREAM, Abschnitt 9)
   - DECON für das Kontrastprofil (Abschnitt 12)
   - Explorer für die Wahl von Dmax/λ (Abschnitt 7)
9. **Übernehmen** schreibt alle Ergebnisse mit Provenance-Sidecar in den Unterordner
   `GIFT/` neben der Datendatei und lädt p(r) und den Fit ins Hauptfenster.

---

## 3. Daten und Fehler σ

| Situation | Einstellung | Bedeutung |
|---|---|---|
| Fehlerspalte vorhanden | *aus Fehlerspalte* | Gewichtung mit 1/σ²; MD ist absolut interpretierbar |
| keine Fehlerspalte, echte Messung | *σ ohne Fehlerspalte → aus Rauschen schätzen* | Savitzky-Golay-Residuen, lokal robust skaliert; MD nur relativ aussagekräftig |
| keine Fehlerspalte, Simulation ohne Rauschen | *relativ annehmen* (z. B. 1 %) | σ = f·\|I\| |

- **Werte I ≤ 0** (z. B. nach Untergrundabzug) bleiben standardmäßig in den Daten
  (*Werte I ≤ 0 verwenden*); die IFT kann sie beschreiben. Abgewählt werden sie
  verworfen. Negative Punkte am Kurvenanfang erfasst ohnehin der Artefakt-Ausschluss
  (Abschnitt 4).
- **Instrumentelle Verschmierung:** Die Rechnung setzt Punktkollimation voraus
  (Pinhole). Spalt- und Wellenlängenverschmierung [G77] sind nicht implementiert.

---

## 4. q-Fitbereich

| Auswahl | q_min | q_max |
|---|---|---|
| *Voller Bereich* | erster Punkt | letzter Punkt |
| *1σ / 2σ / 3σ (Signifikanz)* | erster Punkt bzw. manuell | letztes q, bis zu dem die geglättete Signifikanz \|I/σ\| ≥ nσ bleibt |
| *Manuell* | Eingabe | Eingabe |

- **Signifikanz:** Sie wird mit demselben Code und demselben *Glättungsfenster* berechnet
  wie der Signifikanz-Plot des Hauptfensters (Tab *Signifikanz*). Abgeschnitten wird erst,
  wenn die Signifikanz über ein halbes Fenster hinweg unter der Schwelle bleibt.
- **Artefakte bei kleinem q automatisch ausschließen** (Standard an): Erkannt wird ein
  führender Block mit I ≤ 0 bzw. Vorzeichenwechseln, etwa am Rand des Beamstops oder durch
  Separationsartefakte, samt anschließender nicht signifikanter Punkte. q_min wird dahinter
  gesetzt. Manuelle Grenzen haben Vorrang.
- **Anzeige:** Der gewählte Bereich ist in I(q) grau schattiert. Die Informationszeile
  zeigt die Zahl der Punkte und die Grenzen.
- **Warum q_min wichtig ist:** q_min begrenzt den größten auflösbaren Abstand,
  **Dmax ≤ π/q_min** (Abtasttheorem, [G80b Gl. 1], [M80]). Die Differenz q_max − q_min
  bestimmt die Zahl der Shannon-Kanäle N_s = Dmax·(q_max − q_min)/π, also den
  Informationsgehalt [M80].

---

## 5. IFT-Einstellungen

### 5.1 Auswertung (Art der Transformation)

| Auswertung | Ergebnis | Voraussetzung | Quelle |
|---|---|---|---|
| p(r) — Paarabstandsverteilung | p(r), I(0), Rg | beliebige Teilchen, verdünnt oder mit S(q) (GIFT) | [G77] |
| p_c(r) — Querschnitt | p_c(r), I_c(0), R_c | lange Zylinder (Länge ≥ 10 × Querschnitt) | [G80b] |
| p_t(r) — Dicke | p_t(r), I_t(0), R_t | flache Lamellen (Ausdehnung ≥ 10 × Dicke) | [G80b] |
| Größenverteilung D_V bzw. Anzahlverteilung D_N — Kugeln, lange Zylinder, Lamellen | Verteilung, Momente | Form bekannt und homogen | [G80a] |

Details stehen in Abschnitt 10 und 11. Beim Wechsel zwischen Abstand (Dmax) und Radius
(R_max) rechnet der Dialog den Wert um, sodass die Teilchengröße gleich bleibt.

### 5.2 Dmax

- **Bedeutung:** Dmax ist der größte Abstand im Teilchen; p(r) ist auf [0, Dmax] definiert
  und bei Dmax null [G77].
- **Info-Zeile:** Sie zeigt π/q_min und das Verhältnis Dmax·q_min/π. Werte > 1 bedeuten,
  dass die größten Abstände nicht durch die Messung gedeckt sind; das gibt eine Warnung,
  die Rechnung läuft trotzdem.
- **Schaltfläche π/q_min** setzt Dmax auf die Grenze.
- **Vorschlagen** sucht mit dem Explorer (Abschnitt 7) das kleinste Dmax, bei dem gilt:
  - p(r) ist glatt (Oszillation ≤ 1.6) und läuft vor Dmax aus (Randanteil ≤ 0.1);
  - I(0) > 0;
  - die Anpassung ist so gut wie die beste glatte Lösung.

  Das ist gedacht für Teilchen ohne Guinier-Bereich, bei denen Dmax nicht aus Rg
  abgeschätzt werden kann.
- **Faustregel:** Ein zu kleines Dmax führt zu abgeschnittenem, oft oszillierendem p(r)
  und schlechter MD. Ein zu großes Dmax lässt p(r) vor Dmax lange bei null laufen oder
  erzeugt kleine Wellen im Ausläufer.

### 5.3 Splines N

- **Basis:** p(r) wird durch N kubische B-Splines mit äquidistanten Knoten dargestellt
  [G77].
- **Vorschlag:** N ≈ 1.2·N_s + 5. Die Stabilisierung korreliert überzählige Koeffizienten;
  eine zu grobe Basis kann die Information dagegen nicht darstellen [G80b Tab. 1].

### 5.4 λ-Wahl (Stabilisierung)

Die Koeffizienten minimieren χ² + λ·‖K c‖² [G77 Gl. 12–15].

| Verfahren | Kriterium | Quelle |
|---|---|---|
| *Wendepunkt (Glatter)* (Standard) | Plateau von log N_c(λ) vor dem steilen Anstieg der mittleren Abweichung MD | [G77, Fig. 2] |
| *Evidenz-Maximum (Bayes)* | Maximum der marginalen Likelihood p(I \| λ) | [H00] |
| *manuell* | log₁₀ λ_rel vorgeben (z. B. aus Explorer oder DREAM) | – |

- **Tab *λ-Wahl*:** Er zeigt log N_c und MD über λ [G77, Fig. 2], die log-Evidenz, die
  effektive Parameterzahl N_g = Σβ/(β+λ) und das gewählte λ.
- **λ_rel:** λ wird relativ zu tr(B)/tr(K) angegeben. Der Scan reicht standardmäßig von
  10⁻¹⁴ bis 10⁴ und wird bei Bedarf automatisch nach unten erweitert.

### 5.5 Glättung K und Untergrund

- **Glättung K:**
  - *1. Differenzen, Ränder 0* (Standard): bestraft zusätzlich Sprünge zu p(0) = p(Dmax) = 0.
  - *1. Differenzen (Glatter 1977)* [G77 Gl. 14].
  - *2. Differenzen (Krümmung)*.
- **Konstanten Untergrund anpassen:** Das ist sinnvoll, wenn ein Rest-Untergrund bei großem
  q sichtbar ist. Ein nicht berücksichtigter Untergrund lässt p(r) bei r → 0 ansteigen
  [G77].

---

## 6. Ergebnisse, Tabs und Kennzahlen

- **Ergebnisbereich:**
  - Rg (bzw. R_c, R_t) und I(0) mit Fehlern, für p(r) aus den Momenten [G77 Gl. 19/20];
  - die äquivalente homogene Größe: Kugel R = √(5/3)·Rg, Zylinder R = √2·R_c,
    Lamelle T = √12·R_t [G80b Gl. 19];
  - Rg aus dem Guinier-Fit zum Vergleich [GF55];
  - MD = χ²/M, λ_rel und Verfahren, Kennzahlen, N_g, log-Evidenz, N_s.
- **Tabs:**
  - *I(q) & Fit*: Daten, Fitbereich, Fit mit Band, normierte Residuen.
  - *p(r)*: p(r) ± σ mit Markierungen für Dmax und π/q_min; bei Größenverteilungen
    zusätzlich die abgeleiteten Verteilungen.
  - *S(q) & P(q)* und *BSSA-Verlauf*: nur bei GIFT.
  - *Signifikanz*: |I/σ| mit Schwelle und Fitbereich.
- **Kennzahlen** (SasView-kompatibel, Definition und Interpretation in
  [KENNZAHLEN.md](KENNZAHLEN.md)):
  - Oszillation (homogene Kugel ≈ 1.1)
  - Positive Fraction, 1σ-Positive Fraction
  - Zahl der Maxima
  - χ²/dof, N_g, log-Evidenz, Randanteil

  Formeln wie bei der Moore-Inversion in SasView [M80]. Die Interpretation unterscheidet
  sich wegen der Spline-Basis (siehe dort).

---

## 7. Explorer: Dmax und λ systematisch wählen

Tab *Explorer*:

- **Scan-Arten:**
  - *Karte Dmax × λ* ist der empfohlene Einstieg.
  - *Scan über Dmax*, *Scan über λ* und *Scan über N* laufen jeweils bei festen übrigen
    Einstellungen.
- **Kennzahl:** Sie wird oben gewählt, etwa Oszillation, MD, log-Evidenz, Rg oder
  Positive Fraction.
- **Karte:**
  - weiße Linie: Wendepunkt-λ je Dmax;
  - cyan gepunktet: Evidenz-Maximum;
  - grün: der „gute Bereich“, also glatt, physikalisch und so gut wie die beste glatte
    Lösung;
  - ★: aktuelle Einstellung.
- **Übernehmen:** Ein Klick in die Karte oder die Scan-Kurve übernimmt Dmax (und λ) in
  die Einstellungen.
- **Aktualität:** Ändern sich q-Bereich, N, K, Untergrund oder S(q), wird der Explorer
  als *veraltet* markiert.

---

## 8. GIFT: Strukturfaktoren

- **Modell:** Bei wechselwirkenden Teilchen gilt I(q) = S(q)·Σ c_ν ψ_ν(q) [BP97 Gl. 5–7].
- **Ablauf:** Für jeden Parametersatz d des Strukturfaktors wird die IFT gelöst; die
  S(q)-Parameter minimieren MD(d). Das erledigt eine **Boltzmann-Simplex-Simulated-
  Annealing**-Suche (BSSA) [B00] mit Simplex nach [NM65]. λ wird in Zyklen mitgeführt.
  Mehrere Starts laufen parallel. Das Ergebnis ist bei gleichem *Seed* unabhängig von der
  Zahl der *Prozesse* bitgleich.

### 8.1 Modelle

| Modell | Parameter | Einsatz | Quelle |
|---|---|---|---|
| Harte Kugeln, Percus-Yevick | φ, R_HS | monodisperse, ungeladene Kugeln | [PY58, W63], [BP97 §2.4] |
| Harte Kugeln, gemittelt S_ave (empfohlen) | φ, R_HS, μ | polydisperse Kugeln, „scheinbarer“ Strukturfaktor | [BP97 Gl. 34], [W99 Gl. 8] |
| Harte Kugeln, polydispers S_eff (Vrij, Schulz) | φ, R_HS, μ | polydisperse harte Kugeln, PY-Mischung | [V79, B70, S39], [W99 §2.2] |
| Geladene Kugeln, RMSA (Hayter-Penfold) | φ, R, Ladung z, Salz, T, ε_r | geladene Kolloide, Mizellen | [HP81, HH82, F00] |
| Klebrige harte Kugeln (Baxter) | φ, R_HS, τ, δ (standardmäßig fest) | kurzreichweitige Anziehung | [B68, MMR91] |
| Fraktales Aggregat (Teixeira) | r₀, D_f, ξ | Aggregate aus Bausteinen | [T88] |
| Stäbchen, Mean-Field (S_rod) | c, L, μ_L | dünne, lange Stäbchen | [vdS92], [W99 Gl. 16–17] |

Für RMSA, Sticky und Fraktal wurden die Formeln aus sasmodels [SAS] übernommen und
geprüft. Die Validierung ist in den Changelogs v7.10 und v7.14 dokumentiert.

### 8.2 Bedienung

1. **Modell** wählen. Die Tabelle zeigt für jeden Parameter *Start*, *min*, *max* und
   *fix*; feste Parameter werden nicht angepasst.
2. **Startwerte aus IFT:** Radien kommen aus Rg der vorausgehenden IFT (√(5/3)·Rg), dazu
   ξ = 10·R und eine Stäbchenlänge gleich Dmax. [BP97] empfiehlt eher überschätzte
   Startwerte.
3. **GIFT starten.** Fortschritt und Abbruch laufen über die Statuszeile. Die Tabs *S(q) &
   P(q)* und *BSSA-Verlauf* zeigen das Ergebnis.
4. **Flags prüfen**, vor allem:
   - Parameter am Rand der Grenzen (`gift_bound`);
   - Verbesserung gegenüber der IFT (`gift_improvement`);
   - uneinheitliche Mehrfachstarts (`gift_multistart`);
   - nicht bestimmbare Parameter, z. B. Ladung und Salz bei RMSA (`gift_rmsa_degenerate`)
     oder S_rod (`gift_rod`).

**Hinweise:**

- **Grenzfälle:** S_ave ist ein „scheinbarer“ Strukturfaktor [W99]. Bei kleinem φ ist
  RMSA mit dem Rescaling nach [HH82] zuverlässiger. Beim Stäbchenmodell kann das freie p(r)
  den Strukturfaktor fast vollständig aufnehmen; c sollte dann aus der Konzentration
  vorgegeben werden.
- **Grenzen der Bestimmbarkeit:** Formfaktor und Strukturfaktor sind nur dann trennbar,
  wenn sie sich in I(q) unterschiedlich äußern. Wie sicher die Parameter sind, zeigt
  DREAM (Abschnitt 9).

---

## 9. Unsicherheit (DREAM)

*Unsicherheit bestimmen* tastet die Posterior-Verteilung der gewählten Größen ab:
S(q)-Parameter, log λ und optional Dmax. Die Spline-Koeffizienten werden dabei analytisch
herausintegriert (marginale Likelihood) [H00].

- **Ablauf:**
  1. Latin-Hypercube-Screening der Posterior-Landschaft [MBC79].
  2. **DREAM(ZS)** [TV08, V16] mit mehreren Ketten, bis die Konvergenz erreicht ist
     (R̂ < 1.1 [GR92]; Einlaufphase verworfen).
  3. Posterior-Prädiktion der Bänder.
- **Einstellungen:**
  - Tabelle *abtasten* mit Priorgrenzen; *Standardgrenzen* setzt sie zurück.
  - *π/q_min als Obergrenze für Dmax*
  - *σ mit √MD skalieren*, wenn MD deutlich von 1 abweicht
  - *Ketten*, *Budget*
- **Ergebnis (Tab *Unsicherheit*):**
  - *Übersicht*: Median, 68-%- und 95-%-Intervalle, R̂, MAP.
  - *Corner-Plot*: Korrelationen.
  - *Ketten* und *Bänder* für p(r), I(q) und S(q).
  - Die Schaltfläche *λ und Dmax aus DREAM übernehmen* überträgt die Werte in die
    Einstellungen.
- **Flags:** `dream_*` melden fehlende Konvergenz, nicht bestimmbare Parameter,
  Randlagen, starke Korrelation, Mehrgipfligkeit und ein Optimum außerhalb des
  95-%-Intervalls.
- **Reproduzierbarkeit:** Bei gleichem Seed und gleichen Daten ist das Ergebnis bitgleich;
  die Ketten werden als `.npz` gespeichert.

---

## 10. Querschnitt und Dicke

Für lange Zylinder bzw. flache Lamellen faktorisiert die Intensität [G80b Gl. 6]:

    I(q) = (πL/q)·I_c(q),   I_c(q) = 2π ∫ p_c(r) J₀(qr) dr        (Zylinder)
    I(q) = (2πA/q²)·I_t(q), I_t(q) = 2 ∫ p_t(r) cos(qr) dr         (Lamelle)

- **Auswertung** *p_c(r) — Querschnitt* bzw. *p_t(r) — Dicke* wählen.
- **Dmax** ist hier die maximale Querschnitts- bzw. Dickenabmessung. Sie lässt sich aus
  p(r) abschätzen [G79]:
  - Stäbchen: Wendepunkt am Übergang in den linearen Abfall;
  - Lamellen: aus f(r) = p(r)/r.
- **q-Bereich:** q_min muss groß genug sein, dass die Teilchen „unendlich lang bzw.
  flach“ erscheinen; endliche Teilchen senken q·I bzw. q²·I nahe dem Ursprung ab.
  Andererseits muss q_min < π/D_c bzw. π/D_t bleiben [G80b Gl. 17]. Das Flag
  `cross_section_lowq` meldet einen Anstieg von q·I bzw. q²·I am Anfang des Fitbereichs;
  dann q_min erhöhen. Quantitativ ist die Auswertung nur für Länge/Querschnitt ≥ 10
  [G80b Gl. 16].
- **Ergebnisse:**
  - R_c bzw. R_t aus den Momenten, R² = ∫p r² dr / (2∫p dr) [G80b Gl. 12];
  - homogen R = √2·R_c bzw. T = √12·R_t [G80b Gl. 19];
  - Guinier des Querschnitts ln(qI) bzw. der Dicke ln(q²I) [G80b Gl. 11].
- **p_t(0) ist nicht null;** die Spline-Basis lässt den linken Rand dafür frei.

---

## 11. Größenverteilungen

Unter der Annahme, dass alle Teilchen dieselbe bekannte Form haben und sich nur in einer
Größe R unterscheiden, gilt [G80a Gl. 1]:

    I(q) = ∫ D_N(R) m²(R) Φ(qR) dR = ∫ D_V(R) m(R) Φ(qR) dR.

- **Wahl:** Kugeln, lange Zylinder (Radius des Querschnitts) oder Lamellen (Dicke), jeweils
  mit der **Anzahlverteilung D_N** (Primärgröße in [G80a]) oder der **Volumenverteilung
  D_V** als Unbekannter.
- **Ausgabe:** Die jeweils anderen Verteilungen (D_V, D_N, Intensitätsverteilung D_I)
  werden abgeleitet und normiert dargestellt. Dazu kommen Modus, ⟨R⟩_V, σ_V, ⟨R⟩_N und
  σ_N mit Fehlern.
- **R_max** ist durch π/(2·q_min) begrenzt, weil der größte Abstand 2R ist [G80a Gl. 12].
- **Instabile Division:** Eine aus D_V berechnete D_N ist bei kleinem R instabil. Sie wird
  nur für R ≥ π/q_max und signifikantes D_V angegeben. Für Anzahlwerte deshalb besser die
  Anzahlverteilung direkt wählen.
- **Negative Werte** werden nicht unterdrückt. Bei sehr schmalen Verteilungen sind sie für
  eine gute Beschreibung nötig [G80a]. Das Flag `size_distribution` warnt ab 10 %
  Negativanteil: entweder schmale, fast monodisperse Verteilung oder falsche Formannahme.
- **Formannahme:** Eine falsche Form verschiebt die Verteilung, bricht die Rechnung aber
  nicht ab. Aus einer guten Anpassung folgt nicht, dass die Form stimmt; Form und
  Größenverteilung sind aus einer Streukurve nicht gleichzeitig bestimmbar
  [G80a; MP62 zitiert in MG98].
  Für Kern-Schale-Teilchen und andere inhomogene Teilchen sind p(r) und DECON geeigneter.

---

## 12. DECON: radiales Kontrastprofil

Für zentrosymmetrische Teilchen ist p(r) das Faltungsquadrat des Kontrastprofils Δρ:
p(r) = r^(dim−1)·(Δρ * Δρ)(r) mit dim = 3 (Kugel), 2 (Zylinderquerschnitt) oder
1 (Lamelle) [G81 Gl. 2]. DECON bestimmt Δρ als **Faltungswurzel**, ohne das
Phasenproblem der Amplituden [G81].

Die Geometrie folgt aus der Auswertung: p(r) → Kugel, p_c(r) → Zylinder, p_t(r) → Lamelle.

### 12.1 Bedienung (Tab *DECON*)

| Einstellung | Bedeutung | Quelle |
|---|---|---|
| *Basis* | *Splines* (glatt, Standard) oder *Stufen* (Originalverfahren) | [MG98 §2.2], [G81] |
| *Intervalle* | *auto*: Stufenbreite = Knotenabstand der IFT | [G81 §III.1] |
| λ | Wendepunkt-Methode oder manuell | [G81 §III.2] |
| *Polydispersität* | *keine*, *bestimmen (Scan P = 0–40 %)* oder *fester Wert* | [MG98 §2.3] |
| Verteilung | *Schulz (verschoben)* (Standard) oder *Gauß* | [MG98 Gl. 10], [S39] |
| *Stufenmodell* | 2–4 Stufen mit frei optimierten Grenzen | [GH84 §II] |

1. **IFT bzw. GIFT** rechnen und prüfen, ob p(r) glatt ist.
2. **Profil berechnen.** Der Polydispersitäts-Scan dauert etwa 0.5–2 min und läuft im
   Hintergrund; *Abbrechen* ist möglich.
3. Optional **Stufenmodell optimieren**, z. B. mit 2 Stufen für Kern- und Außenradius.

### 12.2 Verfahren

- **Überlappungsintegrale:** Sie sind exakt; das Maß ist das Schnittvolumen zweier Kugeln,
  die Schnittfläche zweier Kreise bzw. die Schnittlänge zweier Strecken [GH84 Anhang,
  Gl. A2–A5]. Splines werden intern in feine Stufen zerlegt [MG98].
- **Anpassung:** gewichtete kleinste Quadrate gegen p(r) ± σ, linearisiert und iterativ,
  mit Stabilisierung B + λK [G81 Gl. 7–19]. Das Startprofil ist konstant mit ∫p̃ = ∫p
  [G81 Gl. 5].
- **Mehrdeutigkeit:** Zusätzlich werden weitere Startprofile gerechnet. Gleich gute, aber
  deutlich verschiedene Lösungen erscheinen als *Alternativen* (Flag `decon_ambiguous`),
  typisch bei Kontrastumkehr.
- **Vorzeichen:** Das globale Vorzeichen ist unbestimmt [G81] und wird auf ∫Δρ dV > 0
  normiert.
- **Polydispersität** [MG98 Gl. 9]: Die Überlappungsmatrix wird über eine
  Anzahlverteilung gemittelt, V^P(r) = ∫ D(P,x) x^(2dim−1) V(r/x) dx mit x = R/R_Modus. Das
  Profil beschreibt dann die **häufigste Teilchengröße**. Der Scan findet P im Minimum der
  mittleren Abweichung (Plot MD(P), [MG98 Fig. 2d]); P = σ·√(2 ln 2) ist die relative
  Halbwertsbreite [MG98 Gl. 11].
- **Güte:**
  - MD(p) = √(χ²/M) gegen p(r) [G81 Gl. 20]. Große Werte zeigen fehlende Symmetrie oder
    Polydispersität an; das Verfahren dient damit auch als Test der Symmetrie [G81].
  - MD(I) vergleicht mit der entschmierten IFT-Kurve bzw. dem GIFT-Fit [MG98].

### 12.3 Grenzen

- **Symmetrie:** Leichte Abweichungen, etwa ein Achsenverhältnis von 1:1.2, sind
  unkritisch. Ab etwa 1:1.5 wird das Profil bedeutungslos [G81].
- **Eine Größe:** Die Polydispersität wird durch eine lineare Größe beschrieben; Kern und
  Schale skalieren gemeinsam. Korrelierte Polydispersität, etwa bei fester Schalendicke,
  ist nicht abgedeckt [MG98 §4].
- **Scanbereich:** Der Scan reicht bis P = 40 %. Ein Minimum am Rand meldet das
  Flag `decon_poly`; die Teilchen sind dann stark polydispers oder nicht kugelsymmetrisch.

---

## 13. Serienauswertung

*Serie…* wertet mehrere geladene Datensätze mit den Einstellungen des Dialogs aus
(IFT oder GIFT).

- **Dmax:** *Dmax je Datensatz vorschlagen* (Explorer) oder *Dmax und N wie im Dialog*.
- **Ausgabe:** Eine Übersichtstabelle (CSV) enthält je Datensatz q-Bereich, Dmax, N, λ,
  MD, Rg, I(0), Guinier-Rg, Kennzahlen, die Warnungen, die `record_id` und gegebenenfalls
  die S(q)-Parameter mit Fehlern. Dazu kommt ein Plot p(r)/I(0) aller Datensätze.
  Optional werden die Ergebnisse als Gruppen ins Hauptfenster übernommen.

---

## 14. Ausgabe, Provenance und Reproduktion

*Übernehmen* schreibt in den *Zielordner* (Standard `GIFT/` neben der Datendatei):

| Datei | Inhalt |
|---|---|
| `…_GIFT_pr.dat` | p(r) (bzw. p_c, p_t, D(R)) ± σ; bei Größenverteilungen zusätzlich die abgeleiteten Verteilungen |
| `…_GIFT_fit-PDDF.dat` | Fit I(q) ± σ im Fitbereich |
| `…_GIFT_data.dat` | Eingangsdaten nach q-Umrechnung (nur bei Umrechnung) |
| `…_GIFT_Sq.dat`, `…_GIFT_Pq.dat` | Strukturfaktor und Formfaktor (GIFT) |
| `…_GIFT_dream.npz`, `…_GIFT_pr_band.dat` | DREAM-Ketten und p(r)-Band |
| `…_GIFT_decon.dat` | Kontrastprofil ± σ, Alternativen, Stufenmodell |
| `…_GIFT_prov.json` | Provenance-Sidecar (alle Einstellungen, Ergebnisse, Flags, SHA-256-Hashes) |
| `…_GIFT.prov-w3c.json` | optional W3C-PROV-JSON [PROV] |

- **Dateinamen je Auswertung:** Andere Auswertungsarten erhalten eine Kennung im
  Dateinamen, z. B. `probe-xs_GIFT_pr.dat` (Querschnitt), `-thk` (Dicke), `-sizeS`,
  `-sizeSn` (Kugeln D_V bzw. D_N).
- **Kopfzeilen:** Alle Dateien beginnen mit einem Kopf, der `record_id`, Einstellungen,
  Kenngrößen und Flags enthält.
- **Reproduktion:** *Einstellungen aus Sidecar…* lädt einen Sidecar, stellt alle
  Einstellungen einschließlich Auswertungsart, GIFT-Modell und DREAM wieder her und
  rechnet neu. Eine veränderte Datendatei wird über den Hash erkannt und gemeldet.

---

## 15. Flags (Plausibilitätsprüfungen)

Die Flags stehen in der Liste unter dem Ergebnis: grün ok, blau Hinweis, gelb/rot Warnung.
Sie werden auch in der Provenance gespeichert.

| Bereich | Flags |
|---|---|
| Messbereich | `dmax_qmin`, `shannon`, `q_range`, `lowq_artifacts`, `lowq_rise`, `guinier_missing`, `cross_section_lowq` |
| Fehler und Anpassung | `sigma_estimated`, `fit_quality`, `lambda`, `rg_consistency` |
| Form von p(r) | `pr_end`, `pr_tail`, `pr_negative`, `pr_oscillation`, `pr_smoothness` (mit wahrscheinlicher Ursache), `pr_peaks` |
| Größenverteilung | `size_distribution` |
| GIFT | `gift_bound`, `gift_structure_factor`, `gift_improvement`, `gift_lambda`, `gift_errors`, `gift_multistart`, `gift_apparent`, `gift_rmsa_degenerate`, `gift_rmsa_rescaled`, `gift_sticky`, `gift_sticky_coupled`, `gift_fractal`, `gift_rod` |
| DREAM | `dream_convergence`, `dream_identifiability`, `dream_boundary`, `dream_correlation`, `dream_multimodal`, `dream_reference`, `dream_dmax_qmin`, `dream_sigma`, `dream_acceptance` |
| DECON | `decon_ambiguous`, `decon_fit`, `decon_poly` |

---

## 16. Typische Probleme und Rezepte

| Beobachtung | Wahrscheinliche Ursache | Vorgehen |
|---|---|---|
| p(r) oszilliert, Flag `pr_smoothness` | Dmax zu klein (Teilchen > π/q_min, kein Guinier-Bereich), λ zu klein, Artefakte bei kleinem q | *Vorschlagen* bzw. Explorer-Karte; Artefakt-Ausschluss prüfen; λ per Evidenz vergleichen |
| p(r) mit negativem Bereich hinter dem Maximum, Korrelationsmaximum in I(q) | Wechselwirkung | GIFT mit passendem Strukturfaktor [BP97] |
| p(r) steigt bei r → 0 | Untergrund nicht abgezogen | *Konstanten Untergrund anpassen* [G77] |
| MD ≫ 1 trotz glattem p(r) | σ unterschätzt, Modellfehler, Untergrund | σ-Quelle prüfen; Untergrund; ggf. GIFT |
| MD ≪ 1 | σ überschätzt | σ-Quelle prüfen; in DREAM *σ mit √MD skalieren* |
| GIFT-Parameter am Rand | Grenzen zu eng oder Modell ungeeignet | Grenzen erweitern; anderes Modell; DREAM zur Bestimmbarkeit |
| Größenverteilung stark negativ | falsche Form oder sehr schmale Verteilung | p(r)/DECON verwenden; anderes Formmodell |
| DECON: MD(p) groß | Polydispersität oder fehlende Symmetrie | Polydispersitäts-Scan; bleibt MD groß, ist das Teilchen nicht zentrosymmetrisch |
| DECON: mehrere Alternativen | Faltungswurzel mehrdeutig (Kontrastumkehr) | Stufenmodell rechnen; Vorwissen (Kontraste) heranziehen |
| Querschnitt/Dicke: Rg unplausibel, Flag `cross_section_lowq` | q_min zu klein | q_min bis zum Maximum von q·I bzw. q²·I erhöhen [G80b] |

---

## 17. Literatur

**Indirekte Fourier-Transformation und Auswertung im Realraum**

- **[G77]** Glatter, O. (1977). A new method for the evaluation of small-angle scattering
  data. *J. Appl. Cryst.* **10**, 415–421.
- **[G79]** Glatter, O. (1979). The interpretation of real-space information from
  small-angle scattering experiments. *J. Appl. Cryst.* **12**, 166–175.
- **[G80a]** Glatter, O. (1980). Determination of particle-size distribution functions from
  small-angle scattering data by means of the indirect transformation method.
  *J. Appl. Cryst.* **13**, 7–11.
- **[G80b]** Glatter, O. (1980). Evaluation of small-angle scattering data from lamellar and
  cylindrical particles by the indirect transformation method. *J. Appl. Cryst.* **13**,
  577–584.
- **[G81]** Glatter, O. (1981). Convolution square root of band-limited symmetrical
  functions and its application to small-angle scattering data. *J. Appl. Cryst.* **14**,
  101–108.
- **[GH84]** Glatter, O. & Hainisch, B. (1984). Improvements in real-space deconvolution
  of small-angle scattering data. *J. Appl. Cryst.* **17**, 435–441.
- **[MG98]** Mittelbach, R. & Glatter, O. (1998). Direct structure analysis of small-angle
  scattering data from polydisperse colloidal particles. *J. Appl. Cryst.* **31**,
  600–608.
- **[M80]** Moore, P. B. (1980). Small-angle scattering. Information content and error
  analysis. *J. Appl. Cryst.* **13**, 168–175. *(Shannon-Kanäle; Grundlage der
  P(r)-Inversion in SasView)*
- **[GF55]** Guinier, A. & Fournet, G. (1955). *Small-Angle Scattering of X-rays.* New York:
  Wiley.
- **[P48]** Porod, G. (1948). Die Abhängigkeit der Röntgen-Kleinwinkelstreuung von Form und
  Größe der kolloiden Teilchen in verdünnten Systemen. *Acta Phys. Austriaca* **2**,
  255–292. *(p_c(r) des homogenen Zylinders, Prüfung der Überlappungsintegrale)*

**GIFT und Strukturfaktoren**

- **[BP97]** Brunner-Popela, J. & Glatter, O. (1997). Small-angle scattering of interacting
  particles. I. Basic principles of a global evaluation technique. *J. Appl. Cryst.* **30**,
  431–442.
- **[W99]** Weyerich, B., Brunner-Popela, J. & Glatter, O. (1999). Small-angle scattering of
  interacting particles. II. Generalized indirect Fourier transformation under
  consideration of the effective structure factor for polydisperse systems.
  *J. Appl. Cryst.* **32**, 197–209.
- **[B00]** Bergmann, A., Fritz, G. & Glatter, O. (2000). Solving the generalized indirect
  Fourier transformation (GIFT) by Boltzmann simplex simulated annealing (BSSA).
  *J. Appl. Cryst.* **33**, 1212–1216.
- **[F00]** Fritz, G., Bergmann, A. & Glatter, O. (2000). Evaluation of small-angle
  scattering data of charged particles using the generalized indirect Fourier
  transformation technique. *J. Chem. Phys.* **113**, 9733–9740.
- **[PY58]** Percus, J. K. & Yevick, G. J. (1958). Analysis of classical statistical
  mechanics by means of collective coordinates. *Phys. Rev.* **110**, 1–13.
- **[W63]** Wertheim, M. S. (1963). Exact solution of the Percus–Yevick integral equation
  for hard spheres. *Phys. Rev. Lett.* **10**, 321–323.
- **[V79]** Vrij, A. (1979). Mixtures of hard spheres in the Percus–Yevick approximation.
  Light scattering at finite angles. *J. Chem. Phys.* **71**, 3267–3270.
- **[B68]** Baxter, R. J. (1968). Percus–Yevick equation for hard spheres with surface
  adhesion. *J. Chem. Phys.* **49**, 2770–2774.
- **[B70]** Baxter, R. J. (1970). Ornstein–Zernike relation and Percus–Yevick approximation
  for fluid mixtures. *J. Chem. Phys.* **52**, 4559–4562.
- **[MMR91]** Menon, S. V. G., Manohar, C. & Srinivasa Rao, K. (1991). A new interpretation
  of the sticky hard sphere model. *J. Chem. Phys.* **95**, 9186–9190.
- **[HP81]** Hayter, J. B. & Penfold, J. (1981). An analytic structure factor for macroion
  solutions. *Mol. Phys.* **42**, 109–118.
- **[HH82]** Hansen, J.-P. & Hayter, J. B. (1982). A rescaled MSA structure factor for dilute
  charged colloidal dispersions. *Mol. Phys.* **46**, 651–656.
- **[T88]** Teixeira, J. (1988). Small-angle scattering by fractal systems.
  *J. Appl. Cryst.* **21**, 781–785.
- **[vdS92]** van der Schoot, P. (1992). *Macromolecules* **25**, 2923–2927. *(Mean-Field-
  Strukturfaktor für Stäbchen, wie in [W99] verwendet)*
- **[S39]** Schulz, G. V. (1939). *Z. Phys. Chem. B* **43**, 25–46. *(Schulz-Verteilung)*
- **[MP62]** Mittelbach, P. & Porod, G. (1962). *Acta Phys. Austriaca* **15**, 122–147.
  *(Nicht-Eindeutigkeit von Form und Größenverteilung, zitiert nach [MG98])*

**Statistik und Numerik**

- **[H00]** Hansen, S. (2000). Bayesian estimation of hyperparameters for indirect Fourier
  transformation in small-angle scattering. *J. Appl. Cryst.* **33**, 1415–1421.
- **[TV08]** ter Braak, C. J. F. & Vrugt, J. A. (2008). Differential Evolution Markov Chain
  with snooker updater and fewer chains. *Stat. Comput.* **18**, 435–446.
- **[V16]** Vrugt, J. A. (2016). Markov chain Monte Carlo simulation using the DREAM software
  package: Theory, concepts, and MATLAB implementation. *Environ. Model. Softw.* **75**,
  273–316.
- **[GR92]** Gelman, A. & Rubin, D. B. (1992). Inference from iterative simulation using
  multiple sequences. *Stat. Sci.* **7**, 457–472.
- **[MBC79]** McKay, M. D., Beckman, R. J. & Conover, W. J. (1979). A comparison of three
  methods for selecting values of input variables in the analysis of output from a
  computer code. *Technometrics* **21**, 239–245.
- **[NM65]** Nelder, J. A. & Mead, R. (1965). A simplex method for function minimization.
  *Comput. J.* **7**, 308–313.

**Software und Standards**

- **[SAS]** SasView/sasmodels, https://www.sasview.org, https://github.com/SasView/sasmodels
  (BSD-3-Lizenz; portierte Teile siehe `THIRD_PARTY_NOTICES.md`).
- **[PROV]** W3C (2013). PROV-DM: The PROV Data Model. https://www.w3.org/TR/prov-dm/

Die mit dem Modul ausgelieferten Volltexte liegen in `GIFT/0_Sources/`. Die Entwicklung
und die Validierung jeder Phase sind in `docs/GIFT/PLAN.md` und den Changelogs
v7.8–v8.0 dokumentiert.
