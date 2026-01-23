"""
Version Management für ScatterForge Plot

Zentrale Definition von Version und Metadaten für die Software-Provenienz.
"""

__version__ = "7.0.4"
__app_name__ = "ScatterForge Plot"
__year__ = "2026"
__author__ = "TU Bergakademie Freiberg"


def get_version_string():
    """
    Gibt formatierte Versions-String zurück.

    Returns:
        str: "ScatterForge Plot v7.0.2"
    """
    return f"{__app_name__} v{__version__}"


def get_metadata_provenance():
    """
    Gibt Software-Provenienz-Informationen für Metadaten zurück.

    Enthält Informationen über die verwendete Software und deren Versionen
    für wissenschaftliche Reproduzierbarkeit.

    Returns:
        dict: Dictionary mit Software-Informationen
            - software: Name der Software
            - version: Version der Software
            - python_version: Python-Version
            - matplotlib_version: Matplotlib-Version
    """
    import sys
    import matplotlib

    return {
        'software': __app_name__,
        'version': __version__,
        'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        'matplotlib_version': matplotlib.__version__
    }
