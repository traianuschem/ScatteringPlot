"""
Tests Phase 3c: Prozess-Pool, parallele BSSA-Mehrfachstarts, Batch-Likelihood
(Validierung 10 im Plan: identische Ergebnisse für 1 und n Worker).
"""

import unittest

import numpy as np

from analysis.gift import parallel
from analysis.gift.ift import IFTSettings, IFTProblem
from analysis.gift.gift import GIFTSettings, run_gift
from analysis.gift.bssa import BSSASettings, BSSACancelled
from analysis.gift.structure_factors import s_percus_yevick_avg
from tests.analysis.synthetic import sphere_intensity, noisy


def _data():
    q = np.linspace(0.05, 2.0, 200)
    I, s = noisy(sphere_intensity(q, 10.0, 1e3) * s_percus_yevick_avg(q, 10.0, 0.15, 0.4),
                 0.02, 1)
    return q, I, s


def _gift(n_workers, progress=None, seed=5):
    q, I, s = _data()
    return run_gift(q, I, s, IFTSettings(dmax=22.0, n_splines=25),
                    GIFTSettings(model='hs_py_avg', start={'phi': 0.18, 'r_hs': 12.0, 'mu': 0.5},
                                 n_starts=3, lambda_cycles=1, n_workers=n_workers,
                                 bssa=BSSASettings(seed=seed)),
                    progress=progress)


class TestWorkerPool(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        parallel.shutdown_pool()

    def test_workers_do_not_run_main_module(self):
        """Die Worker dürfen das Hauptmodul (hier den Test-Runner, in der App scatter_plot.py
        mit PySide6) nicht erneut ausführen."""
        import PySide6  # noqa: F401  — Hauptprozess wie in der App
        info = parallel.get_pool(2).worker_info()
        self.assertEqual(len(info), 2)
        self.assertTrue(all(not pyside for _, pyside, _ in info))

    def test_pool_is_reused(self):
        self.assertIs(parallel.get_pool(2), parallel.get_pool(2))

    def test_results_independent_of_worker_count(self):
        r1 = _gift(1)
        r3 = _gift(3)
        self.assertEqual(r1.params, r3.params)
        self.assertEqual(r1.md, r3.md)
        self.assertEqual(r1.n_evals, r3.n_evals)
        self.assertEqual(r1.starts, r3.starts)
        self.assertEqual([h['md'] for h in r1.history], [h['md'] for h in r3.history])
        self.assertEqual(r3.n_workers, 3)

    def test_progress_and_cancel(self):
        seen = []
        _gift(2, progress=lambda *a: seen.append(a) or True)
        self.assertTrue(seen)
        self.assertTrue(all(len(a) == 5 for a in seen))
        with self.assertRaises(BSSACancelled):
            _gift(2, progress=lambda n, *a: n < 300)
        # Pool bleibt nach dem Abbruch nutzbar
        self.assertEqual(_gift(2).params, _gift(1).params)


class TestBatchLikelihood(unittest.TestCase):
    def test_batch_equals_single(self):
        q, I, s = _data()
        rng = np.random.default_rng(0)
        S = s_percus_yevick_avg(q, rng.uniform(6, 14, 70), rng.uniform(0.05, 0.3, 70),
                                rng.uniform(0, 0.6, 70))
        for background in (False, True):
            prob = IFTProblem(q, I, s, IFTSettings(dmax=22.0, n_splines=25,
                                                   background=background))
            single = np.array([prob.md(S[k], 1e-6) for k in range(len(S))])
            np.testing.assert_allclose(prob.md_batch(S, 1e-6, chunk=32), single, rtol=1e-6)

    def test_invalid_rows_are_infinite(self):
        q, I, s = _data()
        prob = IFTProblem(q, I, s, IFTSettings(dmax=22.0, n_splines=25))
        S = np.ones((3, len(q)))
        S[1, 4] = np.nan
        md = prob.md_batch(S, 1e-6)
        self.assertTrue(np.isfinite(md[0]) and np.isinf(md[1]) and np.isfinite(md[2]))


if __name__ == '__main__':
    unittest.main()
