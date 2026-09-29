"""Tests für das Panel-Layout (v8.1). Ausführen: python -m unittest discover tests"""
import unittest

import numpy as np

from core.plot_layout import (PlotLayout, PanelSpec, MAIN_ID, migrate_legacy_session,
                              layout_from_legacy, PRESET_NAMES)
from core.panel_types import PANEL_TYPES, get_panel_type, np_trapezoid
from core.models import DataGroup


class TestPlotLayout(unittest.TestCase):

    def test_default_has_main(self):
        layout = PlotLayout()
        self.assertIsNotNone(layout.main)
        self.assertEqual(layout.validate(), [])
        self.assertFalse(layout.is_multi())

    def test_presets_valid(self):
        for name in PRESET_NAMES:
            with self.subTest(preset=name):
                self.assertEqual(PlotLayout.preset(name).validate(), [])

    def test_overlap_detected(self):
        layout = PlotLayout(1, 1)
        layout.panels.append(PanelSpec('x', 'Kratky', row=0, col=0))
        self.assertTrue(any('überlappt' in e for e in layout.validate()))
        layout.get('x').enabled = False  # deaktivierte Panels dürfen überlappen
        self.assertEqual(layout.validate(), [])

    def test_out_of_grid(self):
        layout = PlotLayout(1, 1)
        layout.panels.append(PanelSpec('x', 'Kratky', row=1, col=0))
        self.assertTrue(any('außerhalb' in e for e in layout.validate()))

    def test_sharex_domain(self):
        layout = PlotLayout.preset('main+P(r)')
        layout.get('sub').share_x_with = MAIN_ID  # r ≠ q
        self.assertTrue(any('X-Größe' in e for e in layout.validate()))
        layout.get('sub').set_type('I linear')
        self.assertEqual(layout.validate(), [])

    def test_sharex_cycle(self):
        layout = PlotLayout(2, 1, [PanelSpec(MAIN_ID, share_x_with='b'),
                                   PanelSpec('b', row=1, share_x_with=MAIN_ID)])
        self.assertTrue(any('Zyklisch' in e for e in layout.validate()))

    def test_creation_order(self):
        layout = PlotLayout(2, 1, [PanelSpec('b', row=1, share_x_with=MAIN_ID),
                                   PanelSpec(MAIN_ID)])
        order = [p.id for p in layout.creation_order(layout.panels)]
        self.assertLess(order.index(MAIN_ID), order.index('b'))

    def test_add_and_remove_panel(self):
        layout = PlotLayout()
        p = layout.add_panel('P(r)')
        self.assertEqual((layout.rows, layout.cols), (2, 1))
        self.assertEqual((p.row, p.col), (1, 0))
        self.assertEqual(layout.validate(), [])
        self.assertFalse(layout.remove_panel(MAIN_ID))
        self.assertTrue(layout.remove_panel(p.id))
        layout.compact()
        self.assertEqual((layout.rows, layout.cols), (1, 1))

    def test_roundtrip(self):
        layout = PlotLayout.preset('2x2')
        layout.panels[2].options['normalize_area'] = True
        layout.main.axis['ymin'] = 1e-3
        again = PlotLayout.from_dict(layout.to_dict())
        self.assertEqual(again.to_dict(), layout.to_dict())

    def test_set_type_keeps_custom_name(self):
        p = PanelSpec('x', 'Kratky')
        p.set_type('Porod')
        self.assertEqual(p.name, 'Porod')
        p.name = 'Mein Panel'
        p.set_type('P(r)')
        self.assertEqual(p.name, 'Mein Panel')
        self.assertIn('normalize_area', p.options)


class TestLegacyMigration(unittest.TestCase):

    def test_pddf(self):
        session = {'plot_type': 'PDDF',
                   'axis_limits': {'auto': False, 'ymin': 1.0},
                   'custom_xlabel': 'X',
                   'sub_axis_limits': {'ylabel': 'P', 'auto': False, 'xmax': 20.0},
                   'title_settings': {'subplot_text': 'Unten'}}
        layout = PlotLayout.from_dict(migrate_legacy_session(session)['plot_layout'])
        self.assertEqual(layout.main.panel_type, 'Log-Log')
        self.assertEqual(layout.main.axis['ymin'], 1.0)
        self.assertEqual(layout.main.axis['xlabel'], 'X')
        sub = layout.get('sub')
        self.assertEqual(sub.panel_type, 'P(r)')
        self.assertTrue(sub.enabled)
        self.assertIsNone(sub.share_x_with)
        self.assertEqual(sub.axis['xmax'], 20.0)
        self.assertEqual(sub.axis['ylabel'], 'P')
        self.assertEqual(sub.title, 'Unten')
        self.assertEqual(layout.validate(), [])

    def test_significance_and_asaxs(self):
        sig = layout_from_legacy('Significance')
        self.assertEqual(sig.get('sub').panel_type, 'Significance')
        self.assertEqual(sig.get('sub').share_x_with, MAIN_ID)
        self.assertEqual(sig.row_ratios, [3, 1])
        asaxs = layout_from_legacy('ASAXS')
        self.assertEqual(asaxs.main.panel_type, 'ASAXS')
        self.assertFalse(asaxs.get('sub').enabled)
        self.assertEqual(asaxs.enabled_panels(), [asaxs.main])

    def test_plain_type(self):
        layout = layout_from_legacy('Kratky')
        self.assertEqual(layout.main.panel_type, 'Kratky')
        self.assertEqual(len(layout.panels), 1)

    def test_new_session_untouched(self):
        session = {'plot_layout': {'rows': 1, 'cols': 1, 'panels': []}}
        self.assertIs(migrate_legacy_session(session)['plot_layout'], session['plot_layout'])

    def test_group_subplot_target(self):
        for legacy, expected in [('both', None), ('main', ['main']), ('sub', ['sub']), (None, None)]:
            data = {'name': 'g', 'datasets': []}
            if legacy:
                data['subplot_target'] = legacy
            self.assertEqual(DataGroup.from_dict(data).panel_ids, expected)
        g = DataGroup('g')
        g.panel_ids = ['main', 'abc']
        self.assertEqual(DataGroup.from_dict(g.to_dict()).panel_ids, ['main', 'abc'])


class TestPanelTransforms(unittest.TestCase):
    ctx = {'wavelength': 0.1524, 'options': {}}

    def test_porod(self):
        x = np.array([1.0, 2.0])
        _, y, e = get_panel_type('Porod').transform(x, np.array([1.0, 1.0]), np.array([0.1, 0.1]), self.ctx)
        np.testing.assert_allclose(y, [1, 16])
        np.testing.assert_allclose(e, [0.1, 1.6])

    def test_guinier_error_propagation(self):
        x = np.array([0.1, 0.2])
        xt, _, e = get_panel_type('Guinier').transform(x, np.array([10.0, 5.0]), np.array([1.0, 1.0]), self.ctx)
        np.testing.assert_allclose(xt, x ** 2)
        np.testing.assert_allclose(e, [0.1, 0.2])

    def test_pofr_normalization(self):
        r = np.linspace(0, 10, 101)
        ctx = {'options': {'normalize_area': True}}
        _, y, _ = get_panel_type('P(r)').transform(r, r * (10 - r), None, ctx)
        self.assertAlmostEqual(float(np_trapezoid(y, r)), 1.0, places=6)

    def test_two_theta_filters_invalid(self):
        q = np.array([1.0, 1e3])
        x, _, e = get_panel_type('2-Theta').transform(q, np.array([1.0, 2.0]), np.array([0.1, 0.2]), self.ctx)
        self.assertEqual(len(x), 1)
        self.assertEqual(len(e), 1)

    def test_all_types_have_labels(self):
        for key, pt in PANEL_TYPES.items():
            self.assertTrue(pt.xlabel and pt.ylabel, key)


if __name__ == '__main__':
    unittest.main()
