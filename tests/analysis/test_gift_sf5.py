"""
Tests Phase 5: S_eff nach Vrij (PY-Mischung, Schulz), klebrige harte Kugeln, fraktales
Aggregat, Stäbchen (Mean-Field); numerische Robustheit bei sehr kleinem λ; neue Flags.

Referenzwerte für Baxter und Fraktal: sasmodels 1.0.12 (`stickyhardsphere`, `fractal`,
double precision), q in Å⁻¹ und Längen in Å → hier in nm⁻¹ bzw. nm umgerechnet.
"""

import unittest

import numpy as np

from analysis.gift import parallel
from analysis.gift.ift import IFTSettings, IFTProblem, IFTDecomposition
from analysis.gift.gift import GIFTSettings, run_gift
from analysis.gift.likelihood import MarginalLikelihood, ParameterSpace, LOG_LAMBDA
from analysis.gift.structure_factors import get_model, s_percus_yevick
from analysis.gift.sf_models import (py_mixture_intensity, _baxter_q, _sphere_amplitude,
                                     s_eff_vrij, schulz_nodes, s_sticky, s_fractal, s_rod)
from analysis.gift.diagnostics import diagnose_gift
from tests.analysis.synthetic import sphere_intensity, rod_intensity, noisy

QA = np.array([0.001, 0.003, 0.01, 0.03, 0.06, 0.1, 0.2])        # Å⁻¹


class TestVrij(unittest.TestCase):
    def test_one_component_equals_py(self):
        q = np.linspace(0.005, 3.0, 300)
        R, phi = 5.0, 0.3
        rho = phi / (4.0 / 3.0 * np.pi * R ** 3)
        F = _sphere_amplitude(q, np.array([R]))
        S = py_mixture_intensity(q, [R], [rho], F) / (rho * F[:, 0] ** 2)
        np.testing.assert_allclose(S, s_percus_yevick(q, R, phi), atol=1e-12)
        F2 = _sphere_amplitude(q, np.array([R, R]))           # zwei identische Spezies
        S2 = py_mixture_intensity(q, [R, R], [0.3 * rho, 0.7 * rho], F2) / (rho * F[:, 0] ** 2)
        np.testing.assert_allclose(S2, S, atol=1e-12)

    def test_mixture_compressibility(self):
        """(∂βP/∂ρ)_x = Σ √(x_i x_j)[1 − ρ̂Ĉ(0)]_ij mit der PY-Kompressibilitätsgleichung."""
        Rb = np.array([3.0, 6.0])
        x = np.array([0.6, 0.4])
        rho_t = 0.25 / np.sum(x * 4.0 / 3.0 * np.pi * Rb ** 3)
        rho_b = x * rho_t

        def beta_p(rhos):
            sig = 2 * Rb
            xi = [np.pi / 6 * np.sum(rhos * sig ** n) for n in range(4)]
            return 6 / np.pi * (xi[0] / (1 - xi[3]) + 3 * xi[1] * xi[2] / (1 - xi[3]) ** 2
                                + 3 * xi[2] ** 3 / (1 - xi[3]) ** 3)

        eps = 1e-6
        dp = (beta_p(rho_b * (1 + eps)) - beta_p(rho_b * (1 - eps))) / (2 * eps * rho_t)
        Q = _baxter_q(np.array([1e-5]), Rb, rho_b)[0]
        A0 = (np.conj(Q).T @ Q).real
        self.assertAlmostEqual(np.sum(np.sqrt(np.outer(x, x)) * A0), dp, delta=1e-6 * dp)

    def test_schulz_and_polydispersity_trend(self):
        R, w = schulz_nodes(10.0, 0.2)
        self.assertAlmostEqual(np.sum(w * R), 10.0, delta=0.02)
        self.assertAlmostEqual(np.sqrt(np.sum(w * (R - 10.0) ** 2)) / 10.0, 0.2, delta=0.005)
        q = np.linspace(0.005, 1.5, 200)
        s0 = [s_eff_vrij(q, 10.0, 0.3, mu)[0] for mu in (0.0005, 0.1, 0.2, 0.3)]
        self.assertTrue(np.all(np.diff(s0) > 0), s0)          # [W99 Fig. 2/3]
        np.testing.assert_allclose(s_eff_vrij(q, 10.0, 0.3, 0.0005), s_percus_yevick(q, 10.0, 0.3))
        self.assertTrue(np.isnan(s_eff_vrij(q, 10.0, 0.8, 0.2)).all())


class TestStickyFractalRod(unittest.TestCase):
    def test_sticky_matches_sasmodels(self):
        ref = {(50.0, 0.1, 0.05, 0.2): [1.0971784883, 1.0878295335, 0.9979509711, 0.7417654528,
                                        1.058822532, 0.9018545625, 1.0387570684],
               (120.0, 0.3, 0.03, 0.5): [0.1910244552, 0.1947764437, 0.246907542, 1.3907044253,
                                         1.058324666, 0.9851716665, 0.9765372239]}
        for (r, phi, perturb, tau), values in ref.items():
            np.testing.assert_allclose(s_sticky(10 * QA, r / 10, phi, tau, perturb), values,
                                       rtol=1e-8)

    def test_fractal_matches_sasmodels(self):
        ref = {(50.0, 2.0, 1000.0): [401.0, 81.0, 8.9207920792, 1.8879023307, 1.222160511,
                                     1.0799920008, 1.0199995],
               (20.0, 2.6, 300.0): [3713.6845118, 1691.9411829, 128.58516842, 7.2604676528,
                                    1.9480694206, 1.2412094639, 1.0384896502]}
        for (r0, df, xi), values in ref.items():
            np.testing.assert_allclose(s_fractal(10 * QA, r0 / 10, df, xi / 10), values, rtol=1e-8)

    def test_rod_limits(self):
        q = np.linspace(0.001, 2.0, 300)
        np.testing.assert_allclose(s_rod(q, 0.0, 50.0, 0.0), 1.0)
        S = s_rod(q, 1.5, 50.0, 0.0)
        self.assertAlmostEqual(S[0], 1.0 / (1.0 + 2 * 1.5), places=3)
        self.assertTrue(np.all(np.diff(S) >= -1e-12))         # [W99 Fig. 5]

    def test_models_vectorised(self):
        q = np.linspace(0.01, 2.0, 80)
        for key in ('hs_vrij', 'sticky', 'fractal', 'rod'):
            m = get_model(key)
            v = m.defaults()
            one = m.evaluate(q, v)
            many = m.evaluate(q, {n: np.full(3, x) for n, x in v.items()})
            self.assertEqual(many.shape, (3, len(q)))
            np.testing.assert_allclose(many[2], one, rtol=1e-12)


class TestGIFTRecovery(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        parallel.shutdown_pool()

    def _fit(self, q, I0, model, start, dmax, **kw):
        I, s = noisy(I0, 0.02, 3)
        return run_gift(q, I, s, IFTSettings(dmax=dmax, n_splines=25),
                        GIFTSettings(model=model, start=start, **kw))

    def test_sticky(self):
        q = np.linspace(0.05, 2.0, 200)
        r = self._fit(q, sphere_intensity(q, 10.0, 1e3) * s_sticky(q, 10.0, 0.2, 0.3, 0.05),
                      'sticky', dict(phi=0.15, r_hs=12.0, stickiness=0.5), 22.0)
        self.assertAlmostEqual(r.params['phi'], 0.2, delta=0.01)
        self.assertAlmostEqual(r.params['r_hs'], 10.0, delta=0.1)
        self.assertAlmostEqual(r.params['stickiness'], 0.3, delta=0.03)

    def test_fractal_needs_low_q(self):
        q = np.geomspace(0.005, 2.0, 250)
        r = self._fit(q, sphere_intensity(q, 5.0, 1e3) * s_fractal(q, 5.0, 2.2, 60.0),
                      'fractal', dict(r0=6.0, df=2.0, xi=50.0), 11.0)
        self.assertAlmostEqual(r.params['r0'], 5.0, delta=0.2)
        self.assertAlmostEqual(r.params['df'], 2.2, delta=0.05)
        self.assertAlmostEqual(r.params['xi'], 60.0, delta=3.0)
        codes = {f.code: f.variant for f in diagnose_gift(r, get_model('fractal'))}
        self.assertEqual(codes['gift_fractal'], 'aggregate')

    def test_vrij(self):
        q = np.linspace(0.05, 2.0, 150)
        R, x = schulz_nodes(10.0, 0.15)
        V = 4.0 / 3.0 * np.pi * R ** 3
        P = sum(xi * sphere_intensity(q, Ri, 1.0) * Vi ** 2 for xi, Ri, Vi in zip(x, R, V))
        r = self._fit(q, 1e3 * P / P[0] * s_eff_vrij(q, 10.0, 0.25, 0.15), 'hs_vrij',
                      dict(phi=0.2, r_hs=12.0, mu=0.25), 30.0, n_starts=2)
        self.assertAlmostEqual(r.params['phi'], 0.25, delta=0.03)
        self.assertAlmostEqual(r.params['r_hs'], 10.0, delta=0.4)
        self.assertAlmostEqual(r.params['mu'], 0.15, delta=0.05)

    def test_rod_is_degenerate_and_flagged(self):
        """S_rod hängt nur über F(qL) von q ab; das freie p(r) nimmt den Strukturfaktor auf
        (MD praktisch unabhängig von c). Dokumentierte Grenze, Flag gift_rod."""
        q = np.geomspace(0.02, 1.0, 220)
        I, s = noisy(rod_intensity(q, 60.0, 1e3) * s_rod(q, 1.0, 60.0, 0.1), 0.02, 2)
        prob = IFTProblem(q, I, s, IFTSettings(dmax=62.0, n_splines=30))
        mds = [prob.md(s_rod(q, c, 60.0, 0.1), 1e-10) for c in (0.0, 1.0, 10.0)]
        self.assertLess(np.ptp(mds), 0.05 * np.min(mds))
        r = run_gift(q, I, s, IFTSettings(dmax=62.0, n_splines=30),
                     GIFTSettings(model='rod', start=dict(c=1.0, length=60.0, mu_l=0.1),
                                  fixed=['length', 'mu_l'], n_starts=1, lambda_cycles=1))
        self.assertIn('gift_rod', {f.code for f in diagnose_gift(r, get_model('rod'))})

    def test_sticky_without_attraction_flag(self):
        q = np.linspace(0.05, 2.0, 200)
        r = self._fit(q, sphere_intensity(q, 10.0, 1e3) * s_percus_yevick(q, 10.0, 0.2),
                      'sticky', dict(phi=0.15, r_hs=12.0, stickiness=2.0), 22.0,
                      fixed=['perturb'], n_starts=2)
        flags = {f.code: f for f in diagnose_gift(r, get_model('sticky'))}
        if r.params['stickiness'] > 9.5:
            self.assertEqual(flags['gift_sticky'].variant, 'no_attraction')
            self.assertNotEqual(flags['gift_bound'].variant, 'at_bound')


class TestSmallLambdaRobustness(unittest.TestCase):
    """Sehr kleine λ (erweiterter λ-Scan): GIFT-Zielfunktion, DREAM-Likelihood und IFT-Scan
    müssen übereinstimmen (Normalgleichungen wären dort zu schlecht konditioniert)."""

    def test_paths_agree(self):
        q = np.linspace(0.2, 2.0, 180)
        I, s = noisy(sphere_intensity(q, 10.0, 1e3), 0.02, 1)
        st = IFTSettings(dmax=22.0, n_splines=25)
        prob = IFTProblem(q, I, s, st)
        dec = IFTDecomposition(q, I, s, st)
        ev = MarginalLikelihood(q, I, s, st, 'none', {}, ParameterSpace([LOG_LAMBDA], [-30], [4]),
                                1e-17)
        for lg in (-14.0, -17.0, -22.0):
            g = dec.scan([10.0 ** lg])
            self.assertAlmostEqual(prob.md(np.ones_like(q), 10.0 ** lg), g['md'][0],
                                   delta=1e-6 * g['md'][0])
            self.assertAlmostEqual(ev.log_posterior([[lg]])[0], g['log_evidence'][0],
                                   delta=1e-6 * abs(g['log_evidence'][0]))


if __name__ == '__main__':
    unittest.main()
