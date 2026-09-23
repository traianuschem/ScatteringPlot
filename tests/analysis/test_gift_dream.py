"""
Tests Phase 3d: marginale Likelihood (Hansen 2000), DREAM(ZS) (Validierung 9 im Plan:
korrelierte Gaußverteilung, bimodale Verteilung, Rosenbrock-„Banane“), Screening,
Unsicherheitsanalyse von IFT/GIFT, Flags und Export/Provenance.
"""

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from analysis.gift import parallel
from analysis.gift.dream import (DreamSettings, DreamCancelled, sample, gelman_rubin,
                                 latin_hypercube)
from analysis.gift.ift import IFTSettings, regularization_matrix
from analysis.gift.gift import GIFTSettings
from analysis.gift.likelihood import (ScaledBasisTable, MarginalLikelihood, ParameterSpace,
                                      LOG_LAMBDA, DMAX, evaluate_log_posterior)
from analysis.gift.pipeline import (run_ift_analysis, run_uncertainty_analysis,
                                    export_ift_results)
from analysis.gift.provenance import ProvenanceRecord
from analysis.gift.splines import SplineBasis
from analysis.gift.structure_factors import s_percus_yevick_avg
from analysis.gift.transform import design_matrix
from analysis.gift.uncertainty import UncertaintySettings, count_modes
from tests.analysis.synthetic import sphere_intensity, noisy

Q = np.linspace(0.05, 2.0, 200)
RG_SPHERE = np.sqrt(3.0 / 5.0) * 10.0


def _interacting():
    return noisy(sphere_intensity(Q, 10.0, 1e3) * s_percus_yevick_avg(Q, 10.0, 0.15, 0.4), 0.02, 1)


def _sphere():
    return noisy(sphere_intensity(Q, 10.0, 1e3), 0.02, 1)


def _run(log_density, lo, hi, seed=1, n_z=30, **kw):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    rng = np.random.default_rng(seed)
    z = lo + latin_hypercube(n_z, len(lo), rng) * (hi - lo)
    lp = log_density(z)
    st = DreamSettings(seed=seed, **kw)
    x0 = z[np.argsort(-lp, kind='stable')[:st.n_chains]]
    return sample(log_density, lo, hi, st, z, x0)


class TestMarginalLikelihood(unittest.TestCase):
    def test_scaled_table_matches_quadrature(self):
        table = ScaledBasisTable(25, 2.0 * 40.0)
        for dmax in (15.0, 22.0, 37.3):
            A = design_matrix(Q, SplineBasis(dmax, 25))
            err = np.max(np.abs(table.design(Q, dmax) - A)) / np.max(np.abs(A))
            self.assertLess(err, 1e-7)

    def test_evidence_equals_gaussian_marginal(self):
        """log p(I|θ) gegen die direkte Gauß-Marginale N(0, Σ_σ + A(λK)⁻¹Aᵀ)."""
        q = np.linspace(0.1, 1.5, 40)
        I, s = noisy(sphere_intensity(q, 5.0, 50.0), 0.03, 3)
        st = IFTSettings(dmax=12.0, n_splines=8)
        for with_dmax in (False, True):
            names = [LOG_LAMBDA] + ([DMAX] if with_dmax else [])
            space = ParameterSpace(names, [-8.0, 5.0][:len(names)], [2.0, 20.0][:len(names)])
            ev = MarginalLikelihood(q, I, s, st, 'none', {}, space, 1e-3)
            for theta in ([-3.0, 12.0], [-1.0, 10.5], [0.5, 14.0]):
                th = np.array([theta[:len(names)]])
                res = ev.solve(th, want_solution=True)
                dmax = theta[1] if with_dmax else st.dmax
                A = design_matrix(q, SplineBasis(dmax, 8))
                K = regularization_matrix(8, st.k_type)
                B = (A / s[:, None]).T @ (A / s[:, None])
                lam = 10 ** theta[0] * np.trace(B) / np.trace(K)
                cov = np.diag(s ** 2) + A @ np.linalg.inv(lam * K) @ A.T
                sign, logdet = np.linalg.slogdet(cov)
                direct = -0.5 * (I @ np.linalg.solve(cov, I) + logdet + len(q) * np.log(2 * np.pi))
                self.assertAlmostEqual(res['log_likelihood'][0], direct, delta=1e-6 * abs(direct))

    def test_batch_invalid_and_prior(self):
        I, s = _interacting()
        space = ParameterSpace(['phi', 'r_hs', LOG_LAMBDA], [0.01, 5.0, -14.0], [0.5, 20.0, 0.0])
        ev = MarginalLikelihood(Q, I, s, IFTSettings(dmax=22.0, n_splines=25), 'hs_py_avg',
                                {'phi': 0.15, 'r_hs': 10.0, 'mu': 0.4}, space, 1e-11)
        rng = np.random.default_rng(0)
        theta = space.from_unit(rng.random((12, 3)))
        batch = ev.log_posterior(theta)
        single = np.concatenate([ev.log_posterior(t[None]) for t in theta])
        np.testing.assert_array_equal(batch, single)
        self.assertTrue(np.isneginf(ev.log_posterior([[0.6, 10.0, -11.0]])[0]))  # außerhalb
        # Gaußsche Priorverteilung verschiebt die Dichte um −½((x−μ)/σ)²
        space.gaussian = {'phi': (0.15, 0.01)}
        lp_g = ev.log_posterior([[0.17, 10.0, -11.0]])[0]
        space.gaussian = {}
        self.assertAlmostEqual(ev.log_posterior([[0.17, 10.0, -11.0]])[0] - lp_g, 2.0, places=9)

    def test_evidence_prefers_true_dmax(self):
        I, s = _sphere()
        space = ParameterSpace([DMAX], [12.0], [40.0])
        ev = MarginalLikelihood(Q, I, s, IFTSettings(dmax=22.0, n_splines=25), 'none', {},
                                space, 1e-11)
        d = np.linspace(14.0, 38.0, 49)
        best = d[np.argmax(ev.log_posterior(d[:, None]))]
        self.assertTrue(19.0 <= best <= 21.5, best)


class TestDream(unittest.TestCase):
    """Validierung 9: analytisch bekannte Posterior-Verteilungen."""

    def test_correlated_gaussian(self):
        C = np.array([[1.0, 1.8], [1.8, 4.0]])
        Ci = np.linalg.inv(C)
        mu = np.array([1.0, -2.0])

        def f(T):
            d = T - mu
            return -0.5 * np.einsum('ki,ij,kj->k', d, Ci, d)

        r = _run(f, [-10, -10], [10, 10], min_samples=16000)
        self.assertTrue(r.converged)
        x, _ = r.posterior()
        np.testing.assert_allclose(x.mean(axis=0), mu, atol=0.25)
        np.testing.assert_allclose(np.cov(x.T), C, rtol=0.25, atol=0.1)
        self.assertGreater(r.acceptance_rate, 0.1)

    def test_bimodal(self):
        def f(T):
            a = np.log(1 / 3) - 0.5 * ((T[:, 0] + 3) / 0.5) ** 2
            b = np.log(2 / 3) - 0.5 * ((T[:, 0] - 3) / 0.5) ** 2
            return np.logaddexp(a, b) - 0.5 * T[:, 1] ** 2

        r = _run(f, [-10, -10], [10, 10], min_samples=16000)
        x, _ = r.posterior()
        self.assertAlmostEqual(np.mean(x[:, 0] < 0), 1 / 3, delta=0.08)
        self.assertEqual(count_modes(x[:, 0], -10, 10), 2)
        self.assertEqual(count_modes(x[:, 1], -10, 10), 1)

    def test_banana(self):
        """Haario-Banane (b = 0.1): x₁ ~ N(0, 10²), x₂ = u₂ − 0.1(x₁² − 100)."""
        def f(T):
            x1 = T[:, 0]
            x2 = T[:, 1] + 0.1 * (x1 ** 2 - 100)
            return -0.5 * (x1 ** 2 / 100 + x2 ** 2)

        r = _run(f, [-40, -80], [40, 30], max_evals=400000, min_samples=50000)
        x, _ = r.posterior()
        self.assertTrue(r.converged)
        self.assertLess(abs(x[:, 0].mean()), 2.0)
        self.assertAlmostEqual(x[:, 0].std(), 9.86, delta=1.5)
        self.assertAlmostEqual(np.median(x[:, 1]), 5.4, delta=1.0)

    def test_reproducible_and_cancel(self):
        def f(T):
            return -0.5 * np.sum(T ** 2, axis=1)

        a = _run(f, [-5, -5], [5, 5], seed=4, max_evals=3000)
        b = _run(f, [-5, -5], [5, 5], seed=4, max_evals=3000)
        c = _run(f, [-5, -5], [5, 5], seed=5, max_evals=3000)
        np.testing.assert_array_equal(a.chains, b.chains)
        self.assertFalse(np.array_equal(a.chains, c.chains))
        rng = np.random.default_rng(0)
        z = latin_hypercube(30, 2, rng) * 10 - 5
        with self.assertRaises(DreamCancelled):
            sample(f, [-5, -5], [5, 5], DreamSettings(), z, z[:8],
                   progress=lambda n, g, *a: g < 10)

    def test_gelman_rubin(self):
        rng = np.random.default_rng(0)
        same = rng.normal(size=(500, 4, 2))
        self.assertTrue(np.all(gelman_rubin(same) < 1.02))
        shifted = same + np.array([0, 0, 0, 5.0])[None, :, None]
        self.assertTrue(np.all(gelman_rubin(shifted) > 1.5))


class TestUncertaintyAnalysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        I, s = _interacting()
        cls.gift = run_ift_analysis(
            Q, I, s, IFTSettings(dmax=22.0, n_splines=25),
            gift_settings=GIFTSettings(model='hs_py_avg',
                                       start={'phi': 0.18, 'r_hs': 12.0, 'mu': 0.5}))

    @classmethod
    def tearDownClass(cls):
        parallel.shutdown_pool()

    def test_ift_sphere_intervals(self):
        I, s = _sphere()
        a = run_ift_analysis(Q, I, s, IFTSettings(dmax=22.0, n_splines=25))
        u = run_uncertainty_analysis(a, UncertaintySettings())
        self.assertIs(a.uncertainty, u)
        self.assertEqual(u.names, [LOG_LAMBDA, DMAX])
        self.assertTrue(u.dream.converged)
        sm = u.summary[DMAX]
        self.assertTrue(sm['q2.5'] <= 20.0 <= sm['q97.5'], sm)
        self.assertTrue(u.rg['q2.5'] <= RG_SPHERE <= u.rg['q97.5'], u.rg)
        codes = {f.code: f for f in u.flags}
        self.assertEqual(codes['dream_convergence'].level, 'ok')
        self.assertEqual(codes['dream_dmax_qmin'].variant, 'ok')
        self.assertIn(a.all_flags[-1], u.flags)
        # Bänder: p(r) bei r = 0 null, Median nahe der Punktschätzung
        self.assertEqual(u.bands['pr'].shape, (5, a.solution.settings.n_r))
        self.assertTrue(np.allclose(u.bands['pr'][:, 0], 0.0))

    def test_gift_posterior_covers_truth(self):
        u = run_uncertainty_analysis(self.gift, UncertaintySettings())
        self.assertTrue(u.dream.converged)
        for name, true in (('phi', 0.15), ('r_hs', 10.0), ('mu', 0.4), (DMAX, 20.0)):
            sm = u.summary[name]
            self.assertTrue(sm['q2.5'] <= true <= sm['q97.5'], (name, sm))
        codes = {f.code for f in u.flags}
        self.assertNotIn('dream_identifiability', codes)
        self.assertNotIn('dream_multimodal', codes)

    def test_results_independent_of_worker_count(self):
        us = dict(dream=DreamSettings(max_evals=2000, min_samples=500), n_screen=200)
        u1 = run_uncertainty_analysis(self.gift, UncertaintySettings(n_workers=1, **us))
        u3 = run_uncertainty_analysis(self.gift, UncertaintySettings(n_workers=3, **us))
        np.testing.assert_array_equal(u1.dream.chains, u3.dream.chains)
        np.testing.assert_array_equal(u1.screening.log_p, u3.screening.log_p)
        np.testing.assert_array_equal(u1.bands['pr'], u3.bands['pr'])

    def test_ift_on_interacting_data_flags_dmax_bound(self):
        """Ohne S(q) versucht die IFT die Wechselwirkung über große Abstände zu beschreiben:
        Das Dmax-Posterior drängt an die obere Priorgrenze (Flag dream_boundary)."""
        I, s = _interacting()
        a = run_ift_analysis(Q, I, s, IFTSettings(dmax=22.0, n_splines=25))
        u = run_uncertainty_analysis(a, UncertaintySettings(
            dream=DreamSettings(max_evals=8000, min_samples=2000)))
        flags = {f.code: f for f in u.flags}
        self.assertIn('dream_boundary', flags)
        self.assertIn('Dmax', flags['dream_boundary'].params['names'])

    def test_sigma_scaling_and_settings_roundtrip(self):
        us = UncertaintySettings(scale_sigma=True, sample_params=['phi'], sample_dmax=False,
                                 gaussian={'phi': (0.15, 0.02)},
                                 dream=DreamSettings(max_evals=2000, min_samples=500, seed=7),
                                 n_screen=200)
        u = run_uncertainty_analysis(self.gift, us)
        self.assertEqual(u.names, ['phi', LOG_LAMBDA])
        self.assertAlmostEqual(u.sigma_scale, np.sqrt(self.gift.solution.md))
        self.assertIn('dream_sigma', {f.code for f in u.flags})
        back = UncertaintySettings.from_dict(json.loads(json.dumps(us.to_dict())))
        self.assertEqual(back.to_dict(), us.to_dict())

    def test_export_and_provenance(self):
        us = UncertaintySettings(dream=DreamSettings(max_evals=2000, min_samples=500),
                                 n_screen=200)
        I, s = _interacting()
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / 'probe.dat'
            np.savetxt(src, np.column_stack([Q, I, s]))
            a = run_ift_analysis(Q, I, s, IFTSettings(dmax=22.0, n_splines=25), source_file=src)
            run_uncertainty_analysis(a, us)
            written = export_ift_results(a)
            self.assertTrue(written['dream'].exists() and written['pr_band'].exists())
            rec = ProvenanceRecord.load(written['prov'])
            types = [x['type'] for x in rec.to_dict()['processing']['activities']]
            self.assertEqual(types, ['data_loading', 'preprocessing', 'ift', 'screening',
                                     'dream', 'export'])
            self.assertTrue(all(r['status'] == 'ok' for r in rec.verify_outputs()))
            codes = [f['code'] for f in rec.to_dict()['flags']]
            self.assertIn('dream_convergence', codes)
            self.assertEqual(rec.reproducibility['dream_seed'], us.dream.seed)
            with np.load(written['dream']) as z:
                self.assertEqual(str(z['record_id']), rec.record_id)
                self.assertEqual(z['chains'].shape[1:], (8, 2))
            band = np.loadtxt(written['pr_band'])
            self.assertEqual(band.shape[1], 6)
            head = written['pr_band'].read_text(encoding='utf-8')
            self.assertIn(rec.record_id, head)
            self.assertIn('DREAM (Median [95 %])', head)
            # Die Analyse selbst bleibt ohne DREAM-Aktivitäten (Export arbeitet auf einer Kopie)
            self.assertNotIn('dream', [x['type'] for x in
                                       a.record.to_dict()['processing']['activities']])

    def test_screening_and_pool_evaluation(self):
        space = ParameterSpace([LOG_LAMBDA, DMAX], [-14.0, 15.0], [-6.0, 30.0])
        sol = self.gift.solution
        ev = MarginalLikelihood(sol.q, sol.intensity, sol.sigma, sol.settings, 'hs_py_avg',
                                self.gift.gift.params, space, sol.lam_rel)
        theta = space.from_unit(np.random.default_rng(1).random((10, 2)))
        a = evaluate_log_posterior(ev, theta, 2, 3)
        b = evaluate_log_posterior(ev, theta, 3, 3)
        np.testing.assert_array_equal(a, b)
        # Hauptprozess (mehrfädiges BLAS): nur Rundung, bei winzigem λ (fast singuläres
        # B + λK) etwas verstärkt
        np.testing.assert_allclose(a, evaluate_log_posterior(ev, theta, 0, 10), rtol=1e-4)


if __name__ == '__main__':
    unittest.main()
