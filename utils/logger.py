"""
Zentrales Logging-System für TUBAF Scattering Plot Tool

Konfiguriert und stellt einen Logger für das gesamte Programm bereit.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger(name='ScatteringPlot', level=logging.DEBUG, log_to_file=True):
    """
    Richtet den Logger ein

    Args:
        name: Name des Loggers
        level: Log-Level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Wenn True, wird auch in Datei geloggt

    Returns:
        logging.Logger: Konfigurierter Logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Verhindere doppelte Handler
    if logger.handlers:
        return logger

    # Format mit Timestamp, Level und Nachricht
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)-8s %(message)s',
        datefmt='%H:%M:%S'
    )

    # Console Handler (nur INFO und höher für weniger Spam)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler (DEBUG und höher)
    if log_to_file:
        log_dir = Path.home() / ".tubaf_scatter_plots" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Dateiname mit Datum
        log_file = log_dir / f"scatterplot_{datetime.now().strftime('%Y%m%d')}.log"

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        logger.debug(f"Log-Datei: {log_file}")

    return logger


def get_logger():
    """Gibt den konfigurierten Logger zurück"""
    return logging.getLogger('ScatteringPlot')
