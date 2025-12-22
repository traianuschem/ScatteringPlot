"""
Internationalization Manager für ScatterForge Plot
Verwaltet Übersetzungen und Sprachwechsel
"""

import json
from pathlib import Path
from typing import Dict, Optional
from utils.logger import get_logger


class I18nManager:
    """Manager für Internationalisierung"""

    _instance = None
    _current_language = 'de'
    _translations = {}
    _logger = None

    def __new__(cls):
        """Singleton Pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Logger wird später initialisiert, wenn setup_logger() bereits aufgerufen wurde
            cls._logger = None
        return cls._instance

    def __init__(self):
        """Initialisiert den I18n Manager"""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._translations_dir = Path(__file__).parent / 'translations'
            # Logger initialisieren (falls noch nicht geschehen)
            if self._logger is None:
                try:
                    self._logger = get_logger()
                except:
                    # Falls Logger noch nicht initialisiert, erstelle einen einfachen
                    import logging
                    self._logger = logging.getLogger('I18n')
            self._load_translations()

    def _load_translations(self):
        """Lädt alle Übersetzungen"""
        self._translations = {}

        # Lade verfügbare Sprachen
        if self._translations_dir.exists():
            for lang_file in self._translations_dir.glob('*.json'):
                lang_code = lang_file.stem
                try:
                    with open(lang_file, 'r', encoding='utf-8') as f:
                        self._translations[lang_code] = json.load(f)
                    if self._logger:
                        self._logger.debug(f"Übersetzung geladen: {lang_code}")
                except Exception as e:
                    if self._logger:
                        self._logger.error(f"Fehler beim Laden von {lang_file}: {e}")

    def set_language(self, lang_code: str):
        """
        Setzt die aktuelle Sprache

        Args:
            lang_code: Sprachcode (z.B. 'de', 'en')
        """
        if lang_code in self._translations:
            self._current_language = lang_code
            if self._logger:
                self._logger.info(f"Sprache gewechselt zu: {lang_code}")
        else:
            if self._logger:
                self._logger.warning(f"Sprache nicht verfügbar: {lang_code}, verwende {self._current_language}")

    def get_language(self) -> str:
        """Gibt die aktuelle Sprache zurück"""
        return self._current_language

    def get_available_languages(self) -> Dict[str, str]:
        """
        Gibt verfügbare Sprachen zurück

        Returns:
            Dictionary mit Sprachcodes als Keys und Namen als Values
        """
        available = {}
        for lang_code, translations in self._translations.items():
            # Verwende den _language_name aus der Übersetzungsdatei
            available[lang_code] = translations.get('_language_name', lang_code.upper())
        return available

    def tr(self, key: str, **kwargs) -> str:
        """
        Übersetzt einen Text

        Args:
            key: Übersetzungsschlüssel (z.B. 'menu.file.load')
            **kwargs: Optional, Variablen für String-Formatierung

        Returns:
            Übersetzter Text oder Key falls nicht gefunden
        """
        # Hole die Übersetzung für die aktuelle Sprache
        lang_dict = self._translations.get(self._current_language, {})

        # Navigiere durch den verschachtelten Dictionary
        keys = key.split('.')
        value = lang_dict

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    # Fallback: Versuche Englisch
                    if self._current_language != 'en' and 'en' in self._translations:
                        value = self._translations['en']
                        for k2 in keys:
                            if isinstance(value, dict):
                                value = value.get(k2)
                                if value is None:
                                    break
                            else:
                                break
                    break
            else:
                break

        # Wenn nichts gefunden wurde, gebe den Key zurück
        if value is None or not isinstance(value, str):
            if self._logger:
                self._logger.warning(f"Übersetzung nicht gefunden: {key}")
            return key

        # String-Formatierung falls nötig
        if kwargs:
            try:
                return value.format(**kwargs)
            except KeyError as e:
                if self._logger:
                    self._logger.error(f"Formatierungsfehler für {key}: {e}")
                return value

        return value


# Globale Instanz
_i18n = I18nManager()


def get_i18n() -> I18nManager:
    """Gibt die globale I18n-Instanz zurück"""
    return _i18n


def tr(key: str, **kwargs) -> str:
    """
    Shortcut-Funktion für Übersetzungen

    Args:
        key: Übersetzungsschlüssel
        **kwargs: Optional, Variablen für String-Formatierung

    Returns:
        Übersetzter Text
    """
    return _i18n.tr(key, **kwargs)
