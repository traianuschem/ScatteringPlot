"""
Plot-Layout: freies Grid aus Panels (v8.1)

Angelehnt an LabPlot (Worksheet → mehrere CartesianPlots im Grid-Layout): Die Figur
besteht aus einem Grid mit `rows × cols` Zellen. Jedes Panel belegt einen
rechteckigen Zellbereich, hat einen eigenen Panel-Typ, eigene Achsen-Einstellungen,
Titel und Legenden-Modus und kann ein-/ausgeschaltet werden. Gruppen wählen über
`DataGroup.panel_ids`, in welchen Panels sie erscheinen.

Das Panel mit der ID 'main' existiert immer (Anker für Annotationen, Referenzlinien,
die Plot-Typ-Auswahl im Hauptfenster und die bisherigen Achsen-Einstellungen).
"""

import copy
import uuid

from core.panel_types import PANEL_TYPES, get_panel_type, default_options_for

MAIN_ID = 'main'

LEGEND_MODES = ('all', 'own', 'off')


def default_axis_settings():
    """Achsen-Einstellungen eines Panels (Schema wie früher `axis_limits`,
    ergänzt um Achsentitel-Overrides und X-Skala)."""
    return {
        'xlabel': None, 'ylabel': None,
        'xmin': None, 'xmax': None, 'ymin': None, 'ymax': None,
        'auto': True, 'xscale': None, 'yscale': None,
        'symlog_decades': 4, 'symlog_linscale': 1.0,
    }


class PanelSpec:
    """Ein Panel im Grid."""

    def __init__(self, panel_id=None, panel_type='Log-Log', name=None, enabled=True,
                 row=0, col=0, rowspan=1, colspan=1, share_x_with=None,
                 legend=None, apply_stack=True, options=None, axis=None, title=''):
        self.id = panel_id or uuid.uuid4().hex[:8]
        self.panel_type = panel_type if panel_type in PANEL_TYPES else 'Log-Log'
        self.name = name or self.panel_type
        self.enabled = enabled
        self.row, self.col = row, col
        self.rowspan, self.colspan = rowspan, colspan
        self.share_x_with = share_x_with
        # Standard: Hauptpanel zeigt die komplette Legende, weitere Panels keine
        self.legend = legend or ('all' if self.id == MAIN_ID else 'off')
        self.apply_stack = apply_stack
        self.options = default_options_for(self.panel_type)
        if options:
            self.options.update(options)
        self.axis = default_axis_settings()
        if axis:
            self.axis.update(axis)
        self.title = title or ''

    @property
    def is_main(self):
        return self.id == MAIN_ID

    @property
    def type_info(self):
        return get_panel_type(self.panel_type)

    def set_type(self, panel_type):
        """Wechselt den Panel-Typ; typ-spezifische Optionen werden ergänzt, der Name
        folgt dem Typ, solange er nicht manuell geändert wurde."""
        if panel_type not in PANEL_TYPES or panel_type == self.panel_type:
            return
        if self.name == self.panel_type:
            self.name = panel_type
        self.panel_type = panel_type
        for k, v in default_options_for(panel_type).items():
            self.options.setdefault(k, v)

    def cells(self):
        return {(r, c)
                for r in range(self.row, self.row + self.rowspan)
                for c in range(self.col, self.col + self.colspan)}

    def to_dict(self):
        return {
            'id': self.id, 'panel_type': self.panel_type, 'name': self.name,
            'enabled': self.enabled, 'row': self.row, 'col': self.col,
            'rowspan': self.rowspan, 'colspan': self.colspan,
            'share_x_with': self.share_x_with, 'legend': self.legend,
            'apply_stack': self.apply_stack, 'options': copy.deepcopy(self.options),
            'axis': dict(self.axis), 'title': self.title,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(panel_id=d.get('id'), panel_type=d.get('panel_type', 'Log-Log'),
                   name=d.get('name'), enabled=d.get('enabled', True),
                   row=d.get('row', 0), col=d.get('col', 0),
                   rowspan=d.get('rowspan', 1), colspan=d.get('colspan', 1),
                   share_x_with=d.get('share_x_with'), legend=d.get('legend'),
                   apply_stack=d.get('apply_stack', True), options=d.get('options'),
                   axis=d.get('axis'), title=d.get('title', ''))


class PlotLayout:
    """Grid-Layout aus Panels."""

    def __init__(self, rows=1, cols=1, panels=None, row_ratios=None, col_ratios=None,
                 hspace=None, wspace=None):
        self.rows = rows
        self.cols = cols
        self.panels = panels if panels is not None else [PanelSpec(MAIN_ID)]
        self.row_ratios = list(row_ratios) if row_ratios else [1.0] * rows
        self.col_ratios = list(col_ratios) if col_ratios else [1.0] * cols
        self.hspace = hspace   # None = automatisch
        self.wspace = wspace
        if self.get(MAIN_ID) is None:
            self.panels.insert(0, PanelSpec(MAIN_ID))

    # ── Zugriff ──────────────────────────────────────────────────────────────

    @property
    def main(self):
        return self.get(MAIN_ID)

    def get(self, panel_id):
        for p in self.panels:
            if p.id == panel_id:
                return p
        return None

    def enabled_panels(self):
        """Aktive Panels; das Hauptpanel ist immer aktiv."""
        return [p for p in self.panels if p.enabled or p.is_main]

    def is_multi(self):
        return len(self.enabled_panels()) > 1

    # ── Bearbeitung ──────────────────────────────────────────────────────────

    def set_grid(self, rows, cols):
        """Ändert die Grid-Größe; Verhältnislisten werden angepasst."""
        rows, cols = max(1, int(rows)), max(1, int(cols))
        self.row_ratios = (self.row_ratios + [1.0] * rows)[:rows]
        self.col_ratios = (self.col_ratios + [1.0] * cols)[:cols]
        self.rows, self.cols = rows, cols

    def free_cell(self):
        """Erste freie Zelle (Zeile, Spalte) oder None."""
        used = set()
        for p in self.panels:
            used |= p.cells()
        for r in range(self.rows):
            for c in range(self.cols):
                if (r, c) not in used:
                    return r, c
        return None

    def add_panel(self, panel_type='Log-Log', **kwargs):
        """Fügt ein Panel hinzu. Ohne Positionsangabe wird die erste freie Zelle
        benutzt bzw. eine neue Zeile angehängt."""
        if 'row' not in kwargs:
            cell = self.free_cell()
            if cell is None:
                self.set_grid(self.rows + 1, self.cols)
                self.row_ratios[-1] = 1.0
                cell = (self.rows - 1, 0)
                kwargs.setdefault('colspan', self.cols)
            kwargs['row'], kwargs['col'] = cell
        panel = PanelSpec(panel_type=panel_type, **kwargs)
        self.panels.append(panel)
        return panel

    def remove_panel(self, panel_id):
        """Entfernt ein Panel (nicht das Hauptpanel). Verweise darauf werden gelöst."""
        if panel_id == MAIN_ID:
            return False
        panel = self.get(panel_id)
        if panel is None:
            return False
        self.panels.remove(panel)
        for p in self.panels:
            if p.share_x_with == panel_id:
                p.share_x_with = None
        return True

    def compact(self):
        """Entfernt leere Zeilen/Spalten am Ende des Grids."""
        max_r = max(p.row + p.rowspan for p in self.panels)
        max_c = max(p.col + p.colspan for p in self.panels)
        if max_r < self.rows or max_c < self.cols:
            self.set_grid(max_r, max_c)

    # ── Validierung ──────────────────────────────────────────────────────────

    def validate(self):
        """Prüft das Layout. Gibt eine Liste von Fehlermeldungen zurück (leer = gültig).

        Deaktivierte Panels dürfen sich mit aktiven überlappen (sie werden nicht
        gezeichnet), aktive Panels untereinander nicht.
        """
        errors = []
        if len(self.row_ratios) != self.rows or len(self.col_ratios) != self.cols:
            errors.append("Anzahl der Höhen-/Breitenverhältnisse passt nicht zum Grid")
        if any(r <= 0 for r in self.row_ratios + self.col_ratios):
            errors.append("Verhältnisse müssen > 0 sein")
        ids = [p.id for p in self.panels]
        if len(ids) != len(set(ids)):
            errors.append("Panel-IDs sind nicht eindeutig")

        occupied = {}
        for p in self.panels:
            if p.rowspan < 1 or p.colspan < 1 or p.row < 0 or p.col < 0 \
                    or p.row + p.rowspan > self.rows or p.col + p.colspan > self.cols:
                errors.append(f"Panel '{p.name}' liegt außerhalb des Grids")
                continue
            if not (p.enabled or p.is_main):
                continue
            for cell in p.cells():
                if cell in occupied:
                    errors.append(f"Panel '{p.name}' überlappt mit '{occupied[cell]}'")
                    break
                occupied[cell] = p.name

        enabled_ids = {p.id for p in self.enabled_panels()}
        for p in self.panels:
            if p.share_x_with is None:
                continue
            target = self.get(p.share_x_with)
            if target is None or target is p:
                errors.append(f"Panel '{p.name}': ungültiges Ziel für geteilte X-Achse")
                continue
            if target.type_info.x_domain != p.type_info.x_domain:
                errors.append(f"Panel '{p.name}' kann die X-Achse nicht mit '{target.name}' "
                              f"teilen (unterschiedliche X-Größe)")
            if p.id in enabled_ids and target.id not in enabled_ids:
                errors.append(f"Panel '{p.name}' teilt die X-Achse mit dem "
                              f"deaktivierten Panel '{target.name}'")
        if self._share_cycle():
            errors.append("Zyklische X-Achsen-Kopplung")
        return errors

    def _share_cycle(self):
        for p in self.panels:
            seen = set()
            cur = p
            while cur is not None and cur.share_x_with:
                if cur.id in seen:
                    return True
                seen.add(cur.id)
                cur = self.get(cur.share_x_with)
        return False

    def creation_order(self, panels):
        """Sortiert Panels so, dass Ziele einer X-Kopplung vor ihren Nutzern kommen."""
        remaining = list(panels)
        ordered, done = [], set()
        while remaining:
            progressed = False
            for p in list(remaining):
                dep = p.share_x_with
                if dep is None or dep in done or dep not in {q.id for q in panels}:
                    ordered.append(p)
                    done.add(p.id)
                    remaining.remove(p)
                    progressed = True
            if not progressed:  # Zyklus: Rest ohne Kopplung anhängen
                ordered.extend(remaining)
                break
        return ordered

    def compatible_share_targets(self, panel):
        """Panels, mit denen `panel` die X-Achse teilen darf."""
        domain = panel.type_info.x_domain
        return [p for p in self.panels
                if p is not panel and p.type_info.x_domain == domain
                and p.share_x_with != panel.id]

    # ── Serialisierung ───────────────────────────────────────────────────────

    def to_dict(self):
        return {
            'rows': self.rows, 'cols': self.cols,
            'row_ratios': list(self.row_ratios), 'col_ratios': list(self.col_ratios),
            'hspace': self.hspace, 'wspace': self.wspace,
            'panels': [p.to_dict() for p in self.panels],
        }

    @classmethod
    def from_dict(cls, d):
        panels = [PanelSpec.from_dict(pd) for pd in d.get('panels', [])]
        return cls(rows=d.get('rows', 1), cols=d.get('cols', 1), panels=panels,
                   row_ratios=d.get('row_ratios'), col_ratios=d.get('col_ratios'),
                   hspace=d.get('hspace'), wspace=d.get('wspace'))

    def copy(self):
        return PlotLayout.from_dict(self.to_dict())

    # ── Presets ──────────────────────────────────────────────────────────────

    @classmethod
    def preset(cls, name, main_type='Log-Log', main_axis=None):
        """Vordefinierte Layouts. `main_axis` übernimmt vorhandene Achsen-
        Einstellungen des Hauptpanels."""
        main = PanelSpec(MAIN_ID, main_type, axis=main_axis)
        if name == 'main+P(r)':
            sub = PanelSpec('sub', 'P(r)', row=1)
            return cls(2, 1, [main, sub], row_ratios=[1, 1])
        if name == 'main+Significance':
            sub = PanelSpec('sub', 'Significance', row=1, share_x_with=MAIN_ID)
            return cls(2, 1, [main, sub], row_ratios=[3, 1])
        if name == 'main+I linear':
            sub = PanelSpec('sub', 'I linear', row=1, share_x_with=MAIN_ID)
            return cls(2, 1, [main, sub], row_ratios=[3, 1])
        if name == '2x2':
            panels = [main,
                      PanelSpec(panel_type='Kratky', row=0, col=1),
                      PanelSpec(panel_type='P(r)', row=1, col=0),
                      PanelSpec(panel_type='Significance', row=1, col=1)]
            return cls(2, 2, panels)
        return cls(1, 1, [main])


PRESET_NAMES = ['single', 'main+P(r)', 'main+Significance', 'main+I linear', '2x2']


# ── Migration alter Sessions (≤ v8.0) ────────────────────────────────────────

# Frühere Plot-Typen mit fest gekoppeltem Subplot → (Haupt-Typ, Preset, Subplot aktiv)
LEGACY_PLOT_TYPES = {
    'PDDF': ('Log-Log', 'main+P(r)', True),
    'Significance': ('Log-Log', 'main+Significance', True),
    'ASAXS': ('ASAXS', 'main+I linear', False),
}


def layout_from_legacy(plot_type, axis_limits=None, custom_xlabel=None, custom_ylabel=None,
                       sub_axis_limits=None, subplot_text='', subplot_enabled=None):
    """Erzeugt ein PlotLayout aus den Einstellungen einer v7.x/v8.0-Session."""
    main_axis = dict(axis_limits or {})
    main_axis['xlabel'] = custom_xlabel
    main_axis['ylabel'] = custom_ylabel
    main_axis.setdefault('xscale', None)

    if plot_type in LEGACY_PLOT_TYPES:
        main_type, preset_name, enabled = LEGACY_PLOT_TYPES[plot_type]
        layout = PlotLayout.preset(preset_name, main_type, main_axis)
        sub = layout.get('sub')
        sub.enabled = enabled if subplot_enabled is None else subplot_enabled
        if sub_axis_limits:
            sub.axis.update({k: v for k, v in sub_axis_limits.items() if k in sub.axis})
        sub.title = subplot_text or ''
        return layout

    main_type = plot_type if plot_type in PANEL_TYPES else 'Log-Log'
    return PlotLayout.preset('single', main_type, main_axis)


def migrate_legacy_session(session):
    """Ergänzt eine v7.x/v8.0-Session um 'plot_layout' (in-place, gibt die Session zurück).

    Gruppen-Zuordnungen ('subplot_target') werden von `DataGroup.from_dict` übersetzt;
    der Subplot früherer Sessions hat deshalb die feste ID 'sub'.
    """
    if 'plot_layout' in session:
        return session
    title_settings = session.get('title_settings') or {}
    layout = layout_from_legacy(
        session.get('plot_type', 'Log-Log'),
        axis_limits=session.get('axis_limits'),
        custom_xlabel=session.get('custom_xlabel'),
        custom_ylabel=session.get('custom_ylabel'),
        sub_axis_limits=session.get('sub_axis_limits'),
        subplot_text=title_settings.get('subplot_text', ''),
    )
    session['plot_layout'] = layout.to_dict()
    return session
