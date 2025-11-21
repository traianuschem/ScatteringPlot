# Test-Checkliste - Version 7.0

## Umfassende Testanleitung für ScatterForge Plot v7.0

Diese Checkliste hilft dir, alle neuen Features und bestehenden Funktionen gründlich zu testen, um sicherzustellen, dass nichts übersehen wurde.

---

## ✅ Vor dem Testing

### Vorbereitung
- [ ] Branch `claude/add-latex-support-018vqfpKqgyWMDMfEjQp8v29` ausgecheckt
- [ ] Dependencies installiert (PySide6, matplotlib, numpy)
- [ ] Testdaten vorbereitet (2-3 Datensätze mit verschiedenen Formaten)
- [ ] Logging-Ausgabe beobachten (für Debugging)

### Quick-Check
- [ ] `python3 -m py_compile scatter_plot.py` läuft ohne Fehler
- [ ] `python3 scatter_plot.py` startet die Anwendung
- [ ] Keine Python-Exceptions beim Start
- [ ] UI lädt vollständig

---

## 1. LaTeX/MathText-Support

### 1.1 Legenden

**Setup:**
- [ ] Lade 2-3 Datensätze
- [ ] Öffne Legenden-Editor (Ctrl+L oder Menü)

**Tests:**
- [ ] **Fettdruck:** Ändere Eintrag zu `**Messung**` → Vorschau zeigt **Messung**
- [ ] **Kursiv:** Ändere Eintrag zu `*Fit*` → Vorschau zeigt *Fit*
- [ ] **Griechisch:** Ändere zu `Daten mit $\alpha$` → Vorschau zeigt α
- [ ] **Hochstellung:** Ändere zu `$q^2$ Plot` → Vorschau zeigt q²
- [ ] **Tiefstellung:** Ändere zu `$H_2O$` → Vorschau zeigt H₂O
- [ ] **Kombination:** `**SAXS** $\alpha$ ($q^{-1}$)` → Alle Formatierungen korrekt
- [ ] **Syntax-Hilfe:** Button "📖 LaTeX/MathText Syntax-Hilfe" öffnet Dialog
- [ ] **Plot:** Legende im Plot zeigt korrekte Formatierung
- [ ] **Session:** Speichere + Lade Session → Formatierung bleibt erhalten

**Edge Cases:**
- [ ] Leerer Text → Vorschau zeigt Platzhalter
- [ ] Nur `$` (einzelnes Dollarzeichen) → Keine Fehler
- [ ] Unvollständiges `**Text` → Wird nicht formatiert (OK)

---

### 1.2 Annotations

**Setup:**
- [ ] Öffne Annotations-Dialog (Menü → Plot → Annotation hinzufügen)

**Tests:**
- [ ] **Einfacher Text:** `Test` → Vorschau zeigt Text
- [ ] **Fettdruck:** `**Wichtig**` → Vorschau fett
- [ ] **Mathematisch:** `Bereich $\alpha$` → Vorschau mit α
- [ ] **Formel:** `$I \cdot q^4$` → Vorschau zeigt Formel
- [ ] **Syntax-Hilfe:** Button öffnet Dialog
- [ ] **Plot:** Annotation im Plot korrekt formatiert
- [ ] **Verschieben:** Annotation kann im Plot verschoben werden
- [ ] **Session:** Formatierung bleibt nach Speichern/Laden erhalten

---

### 1.3 Achsenbeschriftungen

**Setup:**
- [ ] Öffne Achsen-Dialog (Menü → Plot → Achsen und Limits)

**Tests:**
- [ ] **X-Achse:** `$q$ [$\AA^{-1}$]` → Vorschau zeigt q [Å⁻¹]
- [ ] **Y-Achse:** `**Intensität** $I$ [a.u.]` → Vorschau fett mit I
- [ ] **Beide:** Beide Achsen mit Formatierung → Vorschau zeigt X: ... | Y: ...
- [ ] **Syntax-Hilfe:** Button öffnet Dialog
- [ ] **Plot:** Achsen zeigen korrekte Formatierung
- [ ] **Zurücksetzen:** "Auf Standard zurücksetzen" löscht custom labels
- [ ] **Session:** Custom labels mit Formatierung bleiben erhalten

**Verschiedene Plot-Typen:**
- [ ] Log-Log → Achsenbeschriftungen korrekt
- [ ] Porod → Achsenbeschriftungen korrekt
- [ ] Kratky → Achsenbeschriftungen korrekt

---

## 2. Keyboard Shortcuts

### 2.1 Plot-Typen

**Tests (Daten müssen geladen sein):**
- [ ] **Ctrl+Shift+1** → Wechselt zu Log-Log
- [ ] **Ctrl+Shift+2** → Wechselt zu Porod
- [ ] **Ctrl+Shift+3** → Wechselt zu Kratky
- [ ] **Ctrl+Shift+4** → Wechselt zu Guinier
- [ ] **Ctrl+Shift+5** → Wechselt zu Bragg Spacing
- [ ] **Ctrl+Shift+6** → Wechselt zu 2-Theta
- [ ] **Ctrl+Shift+7** → Wechselt zu PDDF

**Workflow-Test:**
- [ ] Schnelles Durchschalten (1→2→3→4) funktioniert flüssig
- [ ] Plot aktualisiert sich automatisch
- [ ] Keine Verzögerungen oder Fehler

---

### 2.2 Dialoge

**Tests:**
- [ ] **Ctrl+E** ohne Auswahl → Nichts passiert (oder Info-Message)
- [ ] Wähle Dataset → **Ctrl+E** → Kurven-Editor öffnet
- [ ] Wähle Gruppe → **Ctrl+E** → Gruppen-Kurven-Editor öffnet
- [ ] **Ctrl+L** → Legenden-Editor öffnet
- [ ] **Ctrl+G** → Dialog "Neue Gruppe" öffnet

---

### 2.3 Datei-Operationen

**Tests:**
- [ ] **Ctrl+S** → Session-Speichern-Dialog öffnet
- [ ] Speichere Session → Datei wird erstellt
- [ ] **Ctrl+O** → Session-Laden-Dialog öffnet
- [ ] **Ctrl+Shift+S** → Session-Laden-Dialog öffnet (alternative)
- [ ] **Ctrl+Shift+E** → Export-Dialog öffnet

**Im Menü:**
- [ ] Shortcuts sind im Menü sichtbar (neben den Einträgen)

---

### 2.4 Bearbeiten

**Tests:**
- [ ] Wähle Dataset → **Delete** → Bestätigungs-Dialog + Löschen
- [ ] Wähle Gruppe → **Delete** → Bestätigungs-Dialog + Löschen
- [ ] Keine Auswahl → **Delete** → Nichts passiert (OK)

---

## 3. Tree-Reihenfolge → Plot/Legende

### 3.1 Plot-Reihenfolge

**Setup:**
- [ ] Lade 3 Datensätze: A, B, C
- [ ] Alle in "Nicht zugeordnet"

**Tests:**
- [ ] **Initial:** Plot zeigt A, B, C (von unten nach oben im z-order)
- [ ] Verschiebe B über A im Tree → Plot zeigt B, A, C
- [ ] Verschiebe C ganz nach oben → Plot zeigt C, B, A
- [ ] Reihenfolge im Plot entspricht Tree (oberster Tree-Eintrag = oberste Linie)

**Mit Gruppen:**
- [ ] Erstelle Gruppe G1 mit Dataset A
- [ ] Erstelle Gruppe G2 mit Dataset B, C
- [ ] Verschiebe G2 über G1 → G2-Datasets werden über G1 geplottet
- [ ] Verschiebe C über B innerhalb G2 → C wird über B geplottet

---

### 3.2 Legenden-Reihenfolge

**Setup:**
- [ ] Lade 3 Datensätze: A, B, C

**Tests:**
- [ ] **Initial:** Legende zeigt A, B, C (von oben nach unten)
- [ ] Verschiebe B über A im Tree → Legende zeigt B, A, C
- [ ] Verschiebe C ganz nach oben → Legende zeigt C, B, A
- [ ] Tree-Reihenfolge = Legenden-Reihenfolge

---

### 3.3 Invertieren-Button

**Setup:**
- [ ] 3 Datensätze mit Stack-Faktoren (gestackt)
- [ ] Tree-Reihenfolge: A (unten), B (mitte), C (oben)

**Tests:**
- [ ] **Ohne Invertieren:** Legende zeigt A, B, C (von oben nach unten)
- [ ] Öffne Legenden-Einstellungen (Ctrl+L)
- [ ] Aktiviere "☑ Reihenfolge invertieren"
- [ ] **Mit Invertieren:** Legende zeigt C, B, A (von oben nach unten)
- [ ] Tooltip erklärt Funktion korrekt
- [ ] Deaktiviere wieder → Legende zeigt wieder A, B, C

**Mit Gruppen:**
- [ ] 2 Gruppen (G1: A, B | G2: C, D)
- [ ] Invertieren → Gesamte Reihenfolge invertiert (D, C, G2, B, A, G1)

---

## 4. Regressions-Tests (Bestehende Funktionalität)

### 4.1 Daten laden
- [ ] .dat Datei laden → Funktioniert
- [ ] .csv Datei laden → Funktioniert
- [ ] .txt Datei laden → Funktioniert
- [ ] Mit Fehlerbalken (3. Spalte) → Werden erkannt
- [ ] Fehlerhafte Datei → Sinnvolle Fehlermeldung

### 4.2 Gruppen
- [ ] Neue Gruppe erstellen → Funktioniert
- [ ] Dataset in Gruppe verschieben (Drag & Drop) → Funktioniert
- [ ] Gruppe löschen → Datasets bleiben erhalten (in "Nicht zugeordnet")
- [ ] Stack-Faktoren ändern → Plot aktualisiert sich
- [ ] Auto-Gruppierung → Erstellt Gruppen mit 10^n Faktoren

### 4.3 Kurven-Editor
- [ ] Farbe ändern → Plot aktualisiert
- [ ] Linien-Stil ändern → Plot aktualisiert
- [ ] Marker-Stil ändern → Plot aktualisiert
- [ ] Linienstärke ändern → Plot aktualisiert
- [ ] Fehlerbalken: "Transparente Fläche" → Korrekt dargestellt
- [ ] Fehlerbalken: "Balken mit Caps" → Korrekt dargestellt

### 4.4 Design-Manager
- [ ] Farbschema ändern → Alle Kurven aktualisiert
- [ ] Plot-Design laden → Funktioniert
- [ ] Eigenes Design speichern → Funktioniert
- [ ] Als Standard setzen → Bei erneutem Start geladen

### 4.5 Export
- [ ] PNG Export → Datei erstellt, korrekt
- [ ] SVG Export → Datei erstellt, korrekt
- [ ] PDF Export → Datei erstellt, korrekt
- [ ] Mit transparentem Hintergrund → Funktioniert
- [ ] Mit MathText in Legende → Korrekt exportiert

### 4.6 Session-Management
- [ ] Session speichern → .scatterforge Datei erstellt
- [ ] Session laden → Alles wiederhergestellt:
  - [ ] Alle Datasets geladen
  - [ ] Gruppen mit Stack-Faktoren
  - [ ] Kurven-Formatierungen
  - [ ] Legenden-Einstellungen (inkl. reverse_order!)
  - [ ] Achsenlimits
  - [ ] Custom Achsenbeschriftungen mit LaTeX
  - [ ] Annotations mit LaTeX
  - [ ] Plot-Design

---

## 5. Edge Cases & Fehlerbehandlung

### 5.1 LaTeX-Fehler
- [ ] Ungültige MathText-Syntax → Graceful degradation (wird nicht gerendert, aber kein Crash)
- [ ] Sehr lange Formeln → UI bleibt responsiv
- [ ] Sonderzeichen (`$`, `{`, `}` ohne Escaping) → Keine Crashes

### 5.2 Tree-Manipulationen
- [ ] Alle Datasets löschen → Leerer Tree, kein Crash
- [ ] Gruppe mit 0 Datasets → Kein Crash
- [ ] Sehr viele Datasets (>50) → Performance OK

### 5.3 Shortcuts-Konflikte
- [ ] Ctrl+S in Text-Feldern → System-Shortcut oder App-Shortcut? (Sollte App-Shortcut sein wenn Focus nicht auf Textfeld)
- [ ] Shortcuts in Dialogen → Funktionieren auch in Dialogen

---

## 6. Performance-Tests

### 6.1 Mit vielen Datensätzen
- [ ] 10 Datasets → Flüssig
- [ ] 50 Datasets → Akzeptabel
- [ ] Tree-Drag-and-Drop mit 50 Datasets → Responsiv

### 6.2 Große Dateien
- [ ] Datei mit 10.000 Datenpunkten → Lädt schnell
- [ ] Datei mit 100.000 Datenpunkten → Lädt akzeptabel

### 6.3 Plot-Updates
- [ ] Plot-Typ wechseln (Ctrl+Shift+1-7) → Schnell
- [ ] Farbe ändern → Sofortige Aktualisierung
- [ ] Viele Annotations (>10) → Performance OK

---

## 7. UI/UX-Tests

### 7.1 Dialoge
- [ ] Alle Dialoge öffnen ohne Fehler
- [ ] Vorschau-Widgets zeigen korrekte Formatierung
- [ ] Tooltips sind vorhanden und hilfreich
- [ ] Buttons sind klar beschriftet

### 7.2 Menüs
- [ ] Alle Menü-Einträge funktionieren
- [ ] Shortcuts sind im Menü sichtbar
- [ ] Menü-Struktur ist logisch

### 7.3 Fehlermeldungen
- [ ] Fehlerhafte Eingaben → Sinnvolle Fehlermeldungen
- [ ] Dialoge können abgebrochen werden
- [ ] Keine kryptischen Python-Tracebacks für User

---

## 8. Plattform-Tests (Optional)

Wenn möglich auf verschiedenen Systemen testen:

- [ ] **Linux** → Alle Features funktionieren
- [ ] **Windows** → Alle Features funktionieren
- [ ] **macOS** → Alle Features funktionieren

**Shortcuts:**
- [ ] Ctrl (Linux/Win) vs. Cmd (Mac) → Korrekt gemappt?

---

## 9. Logging & Debugging

### 9.1 Log-Ausgaben
- [ ] Öffne Log-Datei (`~/.tubaf_scatter_plots/logs/`)
- [ ] Tree-Order-Meldungen vorhanden
- [ ] Keine ERROR-Level-Meldungen ohne Grund
- [ ] DEBUG-Meldungen hilfreich

### 9.2 Console-Output
- [ ] Beim Start keine Warnings
- [ ] Bei Features keine Exceptions
- [ ] Performance-Warnings nur bei extrem großen Daten

---

## 10. Finaler Check

### 10.1 Version & Credits
- [ ] Version wird als "7.0-dev" angezeigt
- [ ] Über-Dialog zeigt korrekte Info

### 10.2 Dokumentation
- [ ] CHANGELOG_v7.0.md ist aktuell
- [ ] Alle Features dokumentiert
- [ ] Beispiele in docs/ vorhanden

### 10.3 Code-Qualität
- [ ] Keine Syntax-Fehler
- [ ] Keine Warnungen beim Compile-Check
- [ ] Code-Kommentare vorhanden (v7.0 markiert)

---

## ✅ Nach dem Testing

### Issues gefunden?
1. Erstelle eine Liste der Probleme
2. Priorisiere nach Schweregrad (Critical, High, Medium, Low)
3. Fixe Critical/High vor dem Merge

### Alles OK?
1. [ ] Commit Feature 3 (Tree-Order)
2. [ ] Push Branch
3. [ ] Erstelle Pull Request mit Changelog
4. [ ] Merge in main (nach Review)

---

## 📝 Notizen

Platz für deine Test-Ergebnisse und Beobachtungen:

```
[Deine Notizen hier]

Beispiel:
- LaTeX in Legende: ✅ Funktioniert perfekt
- Shortcut Ctrl+E: ✅ OK
- Tree-Order: ⚠ Bei 50 Datasets etwas langsam beim Drag
- ...
```

---

## 🎯 Zusammenfassung

**Total Items:** ~150 Test-Punkte
**Geschätzte Test-Dauer:** 1-2 Stunden (abhängig von Erfahrung)

**Tipps:**
- Teste nicht alles auf einmal - mache Pausen
- Beginne mit den neuen Features (1-3)
- Dann Regressions-Tests (4)
- Edge Cases zum Schluss (5)
- Notiere alle Probleme sofort

**Viel Erfolg beim Testen! 🚀**

---

*Letzte Aktualisierung: 2025-11-21*
