"""
Daten-Lade-Modul für verschiedene ASCII-Formate
Unterstützt Tab-, Komma- und Leerzeichen-getrennte Dateien
"""

import numpy as np
from pathlib import Path


def detect_delimiter(filepath, max_lines=10):
    """
    Erkennt automatisch das Trennzeichen in der Datei

    Args:
        filepath: Pfad zur Datei
        max_lines: Anzahl der Zeilen zur Analyse

    Returns:
        Erkanntes Trennzeichen (str)
    """
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = []
        for _ in range(max_lines):
            line = f.readline()
            if not line:
                break
            # Überspringe Kommentarzeilen
            if line.strip().startswith('#') or line.strip().startswith('%'):
                continue
            lines.append(line)

    if not lines:
        return None

    # Zähle verschiedene Trennzeichen
    tab_count = sum(line.count('\t') for line in lines)
    comma_count = sum(line.count(',') for line in lines)
    semicolon_count = sum(line.count(';') for line in lines)

    # Entscheide basierend auf der Häufigkeit
    if tab_count > comma_count and tab_count > semicolon_count:
        return '\t'
    elif comma_count > semicolon_count:
        return ','
    elif semicolon_count > 0:
        return ';'
    else:
        # Standardmäßig Whitespace
        return None


def skip_header_lines(filepath):
    """
    Zählt die Anzahl der Header-Zeilen (Kommentare, Text)

    Args:
        filepath: Pfad zur Datei

    Returns:
        Anzahl der zu überspringenden Zeilen
    """
    skip_lines = 0
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            stripped = line.strip()
            # Überspringe leere Zeilen und Kommentare
            if not stripped or stripped.startswith('#') or stripped.startswith('%'):
                skip_lines += 1
                continue
            # Versuche, die erste Zahl zu parsen
            try:
                # Teste, ob die Zeile numerische Daten enthält
                parts = stripped.replace(',', ' ').replace('\t', ' ').replace(';', ' ').split()
                float(parts[0])
                # Wenn erfolgreich, haben wir die Datenzeilen erreicht
                break
            except (ValueError, IndexError):
                # Nicht-numerische Zeile -> Header
                skip_lines += 1
                continue

    return skip_lines


def load_scattering_data(filepath):
    """
    Lädt Streudaten aus verschiedenen ASCII-Formaten

    Erwartet Spalten:
    - 2 Spalten: x, y
    - 3 Spalten: x, y, y_err
    - 4 Spalten: x, y, x_err, y_err (x_err wird ignoriert)

    Args:
        filepath: Pfad zur Datendatei

    Returns:
        numpy array mit shape (n, 2) oder (n, 3)
        Spalten: x, y, [y_err]

    Raises:
        ValueError: Wenn die Datei nicht gelesen werden kann
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise ValueError(f"Datei nicht gefunden: {filepath}")

    # Erkenne Trennzeichen
    delimiter = detect_delimiter(filepath)

    # Erkenne Header-Zeilen
    skip_rows = skip_header_lines(filepath)

    try:
        # Lade Daten mit numpy
        if delimiter:
            data = np.loadtxt(filepath, delimiter=delimiter, skiprows=skip_rows)
        else:
            data = np.loadtxt(filepath, skiprows=skip_rows)

        # Stelle sicher, dass es ein 2D-Array ist
        if data.ndim == 1:
            data = data.reshape(-1, 1)

        # Prüfe Spaltenanzahl
        if data.shape[1] < 2:
            raise ValueError(f"Datei hat zu wenige Spalten (erwartet mindestens 2): {filepath}")

        # Wenn mehr als 3 Spalten, nehme nur x, y, y_err
        if data.shape[1] == 4:
            # Annahme: x, y, x_err, y_err -> nehme x, y, y_err
            data = data[:, [0, 1, 3]]
        elif data.shape[1] > 4:
            # Nehme nur die ersten 3 Spalten
            data = data[:, :3]

        # Entferne NaN und Inf Werte
        mask = np.isfinite(data).all(axis=1)
        data = data[mask]

        # Entferne negative oder Null-Werte für log-Plot
        mask = (data[:, 0] > 0) & (data[:, 1] > 0)
        data = data[mask]

        if len(data) == 0:
            raise ValueError(f"Keine gültigen Datenpunkte in Datei: {filepath}")

        return data

    except Exception as e:
        raise ValueError(f"Fehler beim Laden der Datei {filepath}: {str(e)}")


def create_example_data(output_dir="."):
    """
    Erstellt Beispiel-Datensätze für Tests

    Args:
        output_dir: Ausgabeverzeichnis
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    # Beispiel 1: Messdaten (Tab-getrennt)
    x = np.logspace(-1, 2, 50)
    y = 100 * x**(-2) * np.exp(-x/10) + np.random.normal(0, 5, len(x))
    y = np.abs(y)  # Stelle sicher, dass y positiv ist
    y_err = 0.1 * y + 1

    with open(output_dir / "messung1.dat", 'w') as f:
        f.write("# Beispiel Streudaten - Messung 1\n")
        f.write("# q [nm^-1]\tIntensität [a.u.]\tFehler [a.u.]\n")
        for xi, yi, ei in zip(x, y, y_err):
            f.write(f"{xi:.6f}\t{yi:.6f}\t{ei:.6f}\n")

    # Beispiel 2: Fit-Daten (Komma-getrennt)
    y_fit = 100 * x**(-2) * np.exp(-x/10)

    with open(output_dir / "fit1.csv", 'w') as f:
        f.write("# Fit-Daten zu Messung 1\n")
        f.write("# q [nm^-1],Intensität [a.u.]\n")
        for xi, yi in zip(x, y_fit):
            f.write(f"{xi:.6f},{yi:.6f}\n")

    # Beispiel 3: Weitere Messung
    x2 = np.logspace(-1, 2, 50)
    y2 = 50 * x2**(-1.5) + np.random.normal(0, 3, len(x2))
    y2 = np.abs(y2)
    y2_err = 0.15 * y2 + 0.5

    with open(output_dir / "messung2.dat", 'w') as f:
        f.write("# Beispiel Streudaten - Messung 2\n")
        f.write("# q [nm^-1]\tIntensität [a.u.]\tFehler [a.u.]\n")
        for xi, yi, ei in zip(x2, y2, y2_err):
            f.write(f"{xi:.6f}\t{yi:.6f}\t{ei:.6f}\n")

    print(f"Beispieldaten erstellt in: {output_dir}")


if __name__ == "__main__":
    # Teste den Daten-Loader mit Beispieldaten
    create_example_data("example_data")

    # Lade und zeige Beispieldaten
    data = load_scattering_data("example_data/messung1.dat")
    print(f"Geladene Daten: {data.shape}")
    print(f"Erste 5 Zeilen:\n{data[:5]}")
