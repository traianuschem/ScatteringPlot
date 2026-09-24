"""
Tests Phase 4: Artefakterkennung bei kleinem q, SasView-kompatible Kennzahlen, Evidenz-λ,
Randplateau-Regel, Explorer (Scans, Karte, Dmax-Vorschlag), neue Flags und Serienauswertung.
"""

import csv
import tempfile
import unittest
from pathlib import Path

import numpy as np

from analysis.significance import detect_lowq_artifacts, select_q_range, QRANGE_SIGMA, \
    QRANGE_MANUAL
from analysis.gift.ift import IFTSettings, IFTDecomposition, run_ift, LAMBDA_EVIDENCE
from analysis.gift.likelihood import MarginalLikelihood, ParameterSpace, LOG_LAMBDA
from analysis.gift.explorer import (solution_metrics, scan_1d, scan_map, suggest_dmax,
                                    _grid_metrics, OSC_GOOD)
from analysis.gift.diagnostics import diagnose_ift, guinier_rg
from analysis.gift.pipeline import run_ift_analysis, export_ift_results, QRangeSettings
from analysis.gift.provenance import ProvenanceRecord
from analysis.gift.batch import (BatchItem, run_batch, write_summary, DMAX_SUGGEST,
                                 DMAX_FIXED)
from tests.analysis.synthetic import sphere_intensity, noisy

Q = np.linspace(0.05, 2.0, 200)


def _sphere(radius=10.0, noise=0.02, seed=1, q=Q):
    return noisy(sphere_intensity(q, radius, 1e3), noise, seed)


def _with_artifacts(q, I, s):
    """Vorangestellter Artefaktblock wie bei den ESRF-Separationsdaten: positiver Ausreißer,
    Vorzeichenwechsel, nicht signifikanter Übergangspunkt."""
    dq = q[1] - q[0]
    qa = q[0] - dq * np.arange(6, 0, -1)
    Ia = np.array([3.0, -6.0, -7.0, -3.0, -0.5, 0.05]) * I[0]
    sa = np.array([0.15, 0.4, 0.5, 0.25, 0.1, 0.05]) * I[0]
    return np.concatenate([qa, q]), np.concatenate([Ia, I]), np.concatenate([sa, s])


class TestLowQArtifacts(unittest.TestCase):
    def test_detects_leading_block(self):
        I, s = _sphere()
        q2, I2, s2 = _with_artifacts(Q, I, s)
        self.assertEqual(detect_lowq_artifacts(I2, s2), 6)
        sel = select_q_range(q2, I2, s2, mode=QRANGE_SIGMA, auto_qmin=True)
        self.assertEqual(sel.n_artifacts, 6)
        self.assertAlmostEqual(sel.q_min, Q[0])
        self.assertFalse(sel.q_min_manual)
        # nσ-Grenze wie ohne Artefakte
        self.assertAlmostEqual(sel.q_max, select_q_range(Q, I, s, mode=QRANGE_SIGMA).q_max)

    def test_clean_data_untouched(self):
        for noise in (0.02, 0.1, 0.3):
            for seed in range(20):
                I, s = _sphere(noise=noise, seed=seed)
                self.assertEqual(detect_lowq_artifacts(I, s), 0, (noise, seed))

    def test_negative_point_later_is_not_a_block(self):
        I, s = _sphere()
        I = I.copy()
        I[30] = -abs(I[30])                      # negativer Punkt im Formfaktor-Minimum
        self.assertEqual(detect_lowq_artifacts(I, s), 0)

    def test_manual_limits_take_precedence(self):
        I, s = _sphere()
        q2, I2, s2 = _with_artifacts(Q, I, s)
        sel = select_q_range(q2, I2, s2, mode=QRANGE_SIGMA, q_min=q2[2], auto_qmin=True)
        self.assertEqual(sel.n_artifacts, 0)
        self.assertAlmostEqual(sel.q_min, q2[2])
        sel = select_q_range(q2, I2, s2, mode=QRANGE_MANUAL, auto_qmin=True)
        self.assertEqual(sel.n_artifacts, 0)


class TestMetricsAndLambda(unittest.TestCase):
    def test_sphere_oscillation_like_sasview(self):
        """SasView: Oszillation einer Kugel ≈ 1.1."""
        I, s = _sphere()
        m = solution_metrics(run_ift(Q, I, s, IFTSettings(dmax=20.5, n_splines=25)))
        self.assertTrue(1.0 < m['oscillation'] < 1.25, m['oscillation'])
        self.assertAlmostEqual(m['positive_fraction'], 1.0, places=3)
        self.assertLess(m['end_fraction'], 0.1)
        self.assertTrue(0 < m['n_good'] < 25)

    def test_grid_metrics_equal_solution_metrics(self):
        I, s = _sphere()
        for bg in (False, True):
            st = IFTSettings(dmax=21.0, n_splines=25, background=bg)
            sol = run_ift(Q, I, s, st)
            a = solution_metrics(sol)
            b = _grid_metrics(IFTDecomposition(Q, I, s, st), [sol.lam_rel])
            for k, v in a.items():
                if np.isfinite(v):
                    self.assertAlmostEqual(b[k][0], v, delta=1e-6 * max(abs(v), 1.0), msg=k)

    def test_evidence_scan_matches_marginal_likelihood(self):
        I, s = _sphere()
        st = IFTSettings(dmax=22.0, n_splines=25)
        sol = run_ift(Q, I, s, st)
        ev = MarginalLikelihood(Q, I, s, st, 'none', {}, ParameterSpace([LOG_LAMBDA], [-14], [4]),
                                1e-10)
        for i in range(40, 120, 10):                # λ_rel ≥ 1e-9: Ridge von K vernachlässigbar
            lr = sol.scan.lam_rel[i]
            self.assertAlmostEqual(sol.scan.log_evidence[i], ev.log_posterior([[np.log10(lr)]])[0],
                                   delta=1e-6 * abs(sol.scan.log_evidence[i]) + 1e-3)

    def test_evidence_method(self):
        I, s = _sphere()
        sol = run_ift(Q, I, s, IFTSettings(dmax=22.0, n_splines=25, lam_method=LAMBDA_EVIDENCE))
        self.assertEqual(sol.scan.index_opt, sol.scan.index_evidence)
        self.assertEqual(sol.lam_rel, sol.scan.lam_rel[int(np.argmax(sol.scan.log_evidence))])
        flags = {f.code: f for f in diagnose_ift(sol)}
        self.assertEqual(flags['lambda'].variant, 'evidence')
        self.assertAlmostEqual(sol.rg, np.sqrt(0.6) * 10.0, delta=0.05)

    def test_edge_plateau_moves_to_plateau_end(self):
        """Grobe Basis bei großem Dmax: log N_c ist ab dem Scanrand flach. Gewählt wird das
        Ende des Plateaus, nicht der willkürliche Scanrand 10⁻¹⁴."""
        I, s = _sphere()
        sol = run_ift(Q, I, s, IFTSettings(dmax=60.0, n_splines=12))
        self.assertTrue(sol.scan.inflexion_found)
        self.assertLess(sol.scan.abs_slope[0], 1e-3)
        self.assertGreater(sol.lam_rel, 1e3 * sol.settings.lam_rel_min)
        self.assertLessEqual(sol.md, 1.25 * np.min(sol.scan.md))


class TestExplorer(unittest.TestCase):
    """Kugel R = 10 nm (D = 20 nm), gemessen erst ab q = 0.2 nm⁻¹: kein Guinier-Bereich,
    π/q_min = 15.7 nm < D — der Fall der ESRF-Daten."""

    @classmethod
    def setUpClass(cls):
        cls.q = np.linspace(0.2, 2.0, 180)
        cls.I, cls.s = _sphere(q=cls.q)

    def test_dmax_at_limit_oscillates_and_names_cause(self):
        """Dmax = π/q_min < D (das Symptom der ESRF-Daten): p(r) oszilliert stark; die Flags
        nennen den fehlenden Guinier-Bereich und „Dmax zu klein“ als Ursache."""
        self.assertIsNone(guinier_rg(self.q, self.I, self.s))
        a = run_ift_analysis(self.q, self.I, self.s, IFTSettings(dmax=np.pi / 0.2, n_splines=25))
        flags = {f.code: f for f in a.flags}
        self.assertEqual(flags['guinier_missing'].level, 'warning')
        self.assertGreater(a.metrics['oscillation'], 5.0)
        self.assertEqual(flags['pr_smoothness'].level, 'warning')
        self.assertIn('dmax_small', flags['pr_smoothness'].params['cause_codes'])
        self.assertEqual(flags['pr_end'].level, 'warning')

    def test_scan_extends_to_small_lambda(self):
        """Ohne Kleinwinkelbereich reichen die Eigenwerte über ~20 Dekaden; der λ-Scan wird
        automatisch nach unten erweitert (sonst MD ≫ 1 bei allen λ ≥ 10⁻¹⁴)."""
        sol = run_ift(self.q, self.I, self.s, IFTSettings(dmax=22.0, n_splines=25))
        self.assertLess(sol.scan.lam_rel[0], 1e-15)
        self.assertLess(sol.lam_rel, 1e-14)
        self.assertLess(sol.md, 1.0)
        self.assertLessEqual(solution_metrics(sol)['oscillation'], OSC_GOOD)
        self.assertAlmostEqual(sol.rg, np.sqrt(0.6) * 10.0, delta=0.1)

    def test_suggest_dmax_finds_particle_size(self):
        dmax, scan = suggest_dmax(self.q, self.I, self.s, IFTSettings(dmax=15.7, n_splines=25))
        self.assertIsNotNone(dmax)
        self.assertTrue(19.0 <= dmax <= 26.0, dmax)
        sol = run_ift(self.q, self.I, self.s, IFTSettings(dmax=dmax, n_splines=25))
        m = solution_metrics(sol)
        self.assertLessEqual(m['oscillation'], OSC_GOOD)
        self.assertAlmostEqual(sol.rg, np.sqrt(0.6) * 10.0, delta=0.4)

    def test_map_and_scans(self):
        st = IFTSettings(dmax=20.0, n_splines=25)
        D = np.linspace(10, 40, 13)
        L = np.logspace(-20, 0, 21)
        mp = scan_map(self.q, self.I, self.s, st, D, L)
        self.assertEqual(mp.metrics["oscillation"].shape, (21, 13))
        good = mp.good_region()
        self.assertTrue(good.any())
        cols = np.nonzero(good.any(axis=0))[0]
        self.assertTrue(np.any((D[cols] >= 19) & (D[cols] <= 30)))
        self.assertFalse(good[:, D < 15].any())            # Dmax < D: nie „gut“
        # Kartenspalte = 1D-λ-Scan bei gleichem Dmax
        s1 = scan_1d(self.q, self.I, self.s, IFTSettings(dmax=float(D[4]), n_splines=25), 'lam', L)
        np.testing.assert_allclose(s1.metrics['md'], mp.metrics['md'][:, 4], rtol=1e-10)
        sd = scan_1d(self.q, self.I, self.s, st, 'dmax', D)
        np.testing.assert_allclose(sd.lam_rel, mp.lam_inflexion, rtol=1e-12)
        self.assertEqual(s1.metrics['md'].shape, (21,))
        sn = scan_1d(self.q, self.I, self.s, st, 'n_splines', [15, 25, 40])
        self.assertEqual(len(sn.metrics['oscillation']), 3)


class TestFlagsAndProvenance(unittest.TestCase):
    def test_artifacts_in_pipeline_and_sidecar(self):
        I, s = _sphere()
        q2, I2, s2 = _with_artifacts(Q, I, s)
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / 'probe.dat'
            np.savetxt(src, np.column_stack([q2, I2, s2]))
            a = run_ift_analysis(q2, I2, s2, IFTSettings(dmax=21.0, n_splines=25),
                                 q_range=QRangeSettings(mode=QRANGE_SIGMA), source_file=src)
            codes = {f.code: f for f in a.flags}
            self.assertEqual(codes['lowq_artifacts'].params['n'], '6')
            self.assertAlmostEqual(a.solution.rg, np.sqrt(0.6) * 10.0, delta=0.05)
            written = export_ift_results(a)
            rec = ProvenanceRecord.load(written['prov']).to_dict()
            acts = {x['type']: x for x in rec['processing']['activities']}
            self.assertEqual(acts['preprocessing']['results_summary']['n_artifacts'], 6)
            self.assertTrue(acts['preprocessing']['parameters']['q_range']['auto_qmin'])
            ift = acts['ift']['results_summary']
            self.assertIn('oscillation', ift['metrics'])
            self.assertEqual(ift['lambda_method'], 'inflexion')
            self.assertIn('# Kennzahlen: Oszillation', written['pr'].read_text(encoding='utf-8'))

    def test_without_auto_qmin_artifacts_stay(self):
        I, s = _sphere()
        q2, I2, s2 = _with_artifacts(Q, I, s)
        a = run_ift_analysis(q2, I2, s2, IFTSettings(dmax=21.0, n_splines=25),
                             q_range=QRangeSettings(mode=QRANGE_SIGMA, auto_qmin=False))
        self.assertEqual(a.selection.n_artifacts, 0)
        self.assertGreater(a.solution.md, 5.0)           # die Artefakte zerstören den Fit

    def test_negative_pr_is_info(self):
        I, s = _sphere()
        sol = run_ift(Q, I - 0.02 * I[0], s, IFTSettings(dmax=30.0, n_splines=25))
        f = {x.code: x for x in diagnose_ift(sol)}
        if f['pr_negative'].variant == 'negative':
            self.assertEqual(f['pr_negative'].level, 'info')


class TestBatch(unittest.TestCase):
    def test_series_with_suggested_dmax(self):
        with tempfile.TemporaryDirectory() as tmp:
            items = []
            for k, radius in enumerate((8.0, 10.0, 14.0)):
                I, s = _sphere(radius=radius, seed=k)
                q2, I2, s2 = _with_artifacts(Q, I, s)
                src = Path(tmp) / f"r{radius:g}.dat"
                np.savetxt(src, np.column_stack([q2, I2, s2]))
                items.append(BatchItem(src.stem, src, q2, I2, s2))
            items.append(BatchItem('kaputt', Path(tmp) / 'x.dat', Q[:5], np.ones(5), np.ones(5)))
            entries = run_batch(items, IFTSettings(dmax=25.0, n_splines=25),
                                QRangeSettings(mode=QRANGE_SIGMA), dmax_mode=DMAX_SUGGEST)
            self.assertEqual(len(entries), 4)
            self.assertIsNotNone(entries[3].error)
            for e, radius in zip(entries[:3], (8.0, 10.0, 14.0)):
                self.assertIsNone(e.error)
                self.assertTrue(e.dmax_suggested)
                d = e.analysis.solution.settings.dmax
                self.assertTrue(1.9 * radius <= d <= 2.6 * radius, (radius, d))
                self.assertAlmostEqual(e.analysis.solution.rg, np.sqrt(0.6) * radius,
                                       delta=0.03 * radius)
                self.assertTrue(e.paths['prov'].exists())
            path = write_summary(entries, Path(tmp) / 'GIFT' / 'serie.csv')
            with open(path, encoding='utf-8-sig') as f:
                rows = list(csv.DictReader(f, delimiter=';'))
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[1]['record_id'], entries[1].analysis.record.record_id)
            self.assertTrue(rows[3]['status'].startswith('Fehler'))
            fixed = run_batch(items[:1], IFTSettings(dmax=25.0, n_splines=25),
                              QRangeSettings(mode=QRANGE_SIGMA), dmax_mode=DMAX_FIXED, export=False)
            self.assertEqual(fixed[0].analysis.solution.settings.dmax, 25.0)


if __name__ == '__main__':
    unittest.main()
