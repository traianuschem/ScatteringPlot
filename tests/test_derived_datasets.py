"""Tests für abgeleitete Datensätze ohne Datei (v8.1). Ausführen: python -m unittest tests.test_derived_datasets"""
import unittest

import numpy as np

from core.models import DataSet, DataGroup
from core.panel_types import get_panel_type


class TestDerivedDataset(unittest.TestCase):

    def test_from_arrays_keeps_nonpositive_and_term(self):
        # Name enthält "_IN" und "_pr…" – die Dateinamen-Heuristiken dürfen nicht greifen
        ds = DataSet.from_arrays([0.1, 0.2, 0.3], [-1.0, 0.0, 2.0], [0.1, 0.1, 0.1],
                                 name='probe_projection_IA_IN', data_term='ratio')
        self.assertTrue(ds.is_derived())
        self.assertEqual(ds.data_term, 'ratio')
        self.assertFalse(ds.is_pofr())
        np.testing.assert_allclose(ds.y, [-1.0, 0.0, 2.0])

    def test_session_roundtrip(self):
        ds = DataSet.from_arrays([0.1, 0.2], [1.5, -0.5], None, name='x',
                                 data_term='ratio', derived_from={'quantity': 'ia_in'})
        group = DataGroup('g')
        group.add_dataset(ds)
        again = DataGroup.from_dict(group.to_dict()).datasets[0]
        self.assertTrue(again.data_loaded)
        self.assertEqual(again.derived_from, {'quantity': 'ia_in'})
        np.testing.assert_allclose(again.y, [1.5, -0.5])
        self.assertIsNone(again.y_err)

    def test_panel_routing_predicates(self):
        ratio = DataSet.from_arrays([0.1], [1.0], [0.1], name='r', data_term='ratio')
        plain = DataSet.from_arrays([0.1], [1.0], [0.1], name='p')
        self.assertTrue(get_panel_type('Ratio').accepts(ratio))
        self.assertFalse(get_panel_type('Log-Log').accepts(ratio))
        self.assertFalse(get_panel_type('Significance').accepts(ratio))
        self.assertTrue(get_panel_type('Log-Log').accepts(plain))
        self.assertFalse(get_panel_type('Ratio').accepts(plain))


if __name__ == '__main__':
    unittest.main()
