"""Tests für Pipeline, Export und Provenance-Sidecar (Validierung 11 im Plan)."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

from analysis.gift.ift import IFTSettings
from analysis.gift.pipeline import run_ift_analysis, export_ift_results, QRangeSettings
from analysis.gift.provenance import ProvenanceRecord, compute_sha256, GIFT_SCHEMA_URI
from analysis.significance import QRANGE_SIGMA
from utils.data_loader import load_scattering_data
from tests.analysis.synthetic import sphere_intensity, noisy


class TestPipelineExport(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        q = np.arange(0.02, 3.0, 0.01)
        I, s = noisy(sphere_intensity(q, 12.9, 1e4) + 0.5, 0.05, 7)
        s = np.sqrt(s ** 2 + 0.3 ** 2)            # Untergrundrauschen → fallende Signifikanz
        I = I + np.random.default_rng(8).normal(0, 0.3, len(q))
        self.data_file = self.tmp / "sample_sphere.dat"
        np.savetxt(self.data_file, np.column_stack([q, I, s]), header="q I err")
        self.q, self.I, self.s = q, I, s

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _analyze(self, **kw):
        return run_ift_analysis(self.q, self.I, self.s,
                                IFTSettings(dmax=30.0, n_splines=25),
                                q_range=QRangeSettings(mode=QRANGE_SIGMA, n_sigma=2.0),
                                source_file=self.data_file,
                                source_metadata={'col_x': 0, 'col_y': 1, 'col_err': 2}, **kw)

    def test_sidecar_structure_and_hashes(self):
        analysis = self._analyze()
        self.assertLess(analysis.selection.q_max, self.q[-1])   # σ-Schnitt aktiv
        paths = export_ift_results(analysis)

        self.assertEqual(paths['pr'].parent.name, 'GIFT')
        for key in ('pr', 'fit', 'prov', 'prov_w3c'):
            self.assertTrue(paths[key].exists(), key)

        data = json.loads(paths['prov'].read_text(encoding='utf-8'))
        self.assertEqual(data['$schema'], GIFT_SCHEMA_URI)
        rid = data['record_id']
        types = [a['type'] for a in data['processing']['activities']]
        self.assertEqual(types, ['data_loading', 'preprocessing', 'ift', 'export'])
        # Aktivitätenkette
        acts = data['processing']['activities']
        for prev, act in zip(acts, acts[1:]):
            self.assertEqual(act['used'], [prev['id']])
        # Eingabe-Hash
        ent = data['input']['entities'][0]
        self.assertEqual(ent['sha256'], compute_sha256(self.data_file))
        # Output-Hashes stimmen und record_id steht in den Datei-Headern
        for out in data['output']['catalog']:
            self.assertEqual(out['sha256'], compute_sha256(out['path']))
            self.assertEqual(out['record_id'], rid)
        for key in ('pr', 'fit'):
            self.assertIn(f"record_id: {rid}", paths[key].read_text(encoding='utf-8'))
        # Flags und q-Bereich dokumentiert
        codes = {f['code'] for f in data['flags']}
        self.assertTrue({'dmax_qmin', 'shannon', 'lambda', 'fit_quality'} <= codes)
        pre = acts[1]['results_summary']
        self.assertEqual(pre['mode'], 'sigma')
        self.assertAlmostEqual(pre['q_max'], analysis.selection.q_max)
        self.assertIn('numpy_version', data['agent'])

    def test_results_readable_by_app_loader(self):
        paths = export_ift_results(self._analyze())
        pr = load_scattering_data(paths['pr'], filter_nonpositive=False)
        self.assertEqual(pr.shape[1], 3)
        self.assertAlmostEqual(pr[0, 0], 0.0)
        fit = load_scattering_data(paths['fit'])
        self.assertGreater(len(fit), 10)

    def test_verify_detects_modification(self):
        paths = export_ift_results(self._analyze())
        rec = ProvenanceRecord.load(paths['prov'])
        self.assertTrue(all(r['status'] == 'ok' for r in rec.verify_outputs()))
        self.assertTrue(all(r['status'] == 'ok' for r in rec.verify_inputs()))
        with open(paths['pr'], 'a', encoding='utf-8') as fh:
            fh.write("# manipuliert\n")
        status = {r['label']: r['status'] for r in rec.verify_outputs()}
        self.assertEqual(status[paths['pr'].name], 'modified')

    def test_w3c_prov_json_structure(self):
        paths = export_ift_results(self._analyze())
        doc = json.loads(paths['prov_w3c'].read_text(encoding='utf-8'))
        for key in ('prefix', 'agent', 'entity', 'activity', 'wasGeneratedBy',
                    'wasDerivedFrom', 'wasInformedBy', 'used'):
            self.assertIn(key, doc)
        self.assertIn('prov', doc['prefix'])

    def test_repeat_from_sidecar_reproduces(self):
        """Grundlage für „Aus Sidecar wiederholen“: Einstellungen aus dem Record reichen aus."""
        a1 = self._analyze()
        paths = export_ift_results(a1)
        rec = ProvenanceRecord.load(paths['prov'])
        ift_params = next(a for a in rec.to_dict()['processing']['activities']
                          if a['type'] == 'ift')['parameters']
        qr = next(a for a in rec.to_dict()['processing']['activities']
                  if a['type'] == 'preprocessing')['parameters']['q_range']
        settings = IFTSettings(**{k: ift_params[k] for k in IFTSettings.__dataclass_fields__})
        data = load_scattering_data(self.data_file, filter_nonpositive=False)
        a2 = run_ift_analysis(data[:, 0], data[:, 1], data[:, 2], settings,
                              q_range=QRangeSettings(**qr), source_file=self.data_file)
        self.assertAlmostEqual(a2.solution.rg, a1.solution.rg, places=5)
        np.testing.assert_allclose(a2.solution.pr, a1.solution.pr, rtol=1e-5, atol=1e-8)

    def test_estimated_sigma_is_flagged(self):
        analysis = run_ift_analysis(self.q, self.I, None, IFTSettings(dmax=30.0, n_splines=25),
                                    source_file=self.data_file)
        self.assertTrue(analysis.sigma_estimated)
        codes = {f.code: f.level for f in analysis.flags}
        self.assertEqual(codes['sigma_estimated'], 'warning')

    def test_json_has_no_nan(self):
        paths = export_ift_results(self._analyze())
        text = paths['prov'].read_text(encoding='utf-8')
        self.assertNotIn('NaN', text)
        json.loads(text)


if __name__ == '__main__':
    unittest.main()
