"""
Validierung des IFT-Kerns an den Testfällen aus Glatter (1977).

Fall 1 (Kugel, voller Messbereich): Rg auf < 2 %, p(r) nahe an der analytischen
Lösung. Fälle 2/3 (Kette, Stab mit h₁Rg = 1.6): Dort ist Dmax·q_min/π ≈ 2, also
Information bei kleinen q nicht vorhanden. Wir prüfen den Median über mehrere
Rauschrealisierungen mit großzügigen Grenzen und dass das Dmax-Flag anschlägt.
Glatter nennt für diese Fälle 2 % (Kette) bzw. < 10 % (Stab); die hier erreichte
Genauigkeit liegt im Median bei ~10–15 % (siehe CHANGELOG_v7.8.md).
"""

import unittest

import numpy as np
from scipy.integrate import quad

from analysis.gift.splines import SplineBasis
from analysis.gift.transform import design_matrix, cached_design_matrix
from analysis.gift.ift import (IFTSettings, run_ift, regularization_matrix, estimate_sigma,
                               K_GLATTER, K_DIRICHLET, K_CURVATURE)
from analysis.gift.diagnostics import (diagnose_ift, guinier_rg, check_dmax_qmin,
                                       shannon_channels, LEVEL_WARNING, LEVEL_OK)
from tests.analysis.synthetic import (sphere_intensity, sphere_pr, debye_intensity,
                                      rod_intensity, noisy)

RG = 10.0
R_SPHERE = RG / np.sqrt(0.6)
L_ROD = RG * np.sqrt(12.0)


class TestBasis(unittest.TestCase):
    def test_boundary_values_and_partition(self):
        b = SplineBasis(30.0, 20)
        phi = b.evaluate(np.array([0.0, 30.0, -1.0, 31.0]))
        np.testing.assert_allclose(phi, 0.0, atol=1e-14)
        # Innen summieren sich die Basisfunktionen (ohne die beiden Randsplines) zu 1
        r = np.linspace(2 * b.h, 30.0 - 2 * b.h, 50)
        np.testing.assert_allclose(b.evaluate(r).sum(axis=1), 1.0, atol=1e-12)

    def test_free_slope_at_origin(self):
        b = SplineBasis(30.0, 20)
        r = np.array([1e-3])
        self.assertGreater(b.evaluate(r)[0, 0] / 1e-3, 0.1)   # lineares Verhalten bei r→0

    def test_scaling_property(self):
        b1, b2 = SplineBasis(1.0, 15), SplineBasis(37.0, 15)
        u = np.linspace(0, 1, 33)
        np.testing.assert_allclose(b1.evaluate(u), b2.evaluate(37.0 * u), atol=1e-12)


class TestTransform(unittest.TestCase):
    def test_against_adaptive_quadrature(self):
        b = SplineBasis(30.0, 20)
        q = np.array([0.0, 0.02, 0.5, 1.0, 2.0])
        A = design_matrix(q, b)
        for nu in (0, 7, 19):
            for i, qq in enumerate(q):
                f = lambda r: b.evaluate(np.array([r]))[0, nu] * np.sinc(qq * r / np.pi)
                ref = 4 * np.pi * quad(f, 0, 30.0, points=list(b.knots[3:-3]), limit=400)[0]
                self.assertAlmostEqual(A[i, nu], ref, delta=1e-9 * max(1.0, abs(ref)))

    def test_cache_is_readonly_and_consistent(self):
        q = np.linspace(0.05, 2, 40)
        A1 = cached_design_matrix(q, 25.0, 12)
        A2 = cached_design_matrix(q.copy(), 25.0, 12)
        self.assertIs(A1, A2)
        self.assertFalse(A1.flags.writeable)


class TestRegularization(unittest.TestCase):
    def test_matrices(self):
        Kg = regularization_matrix(5, K_GLATTER)
        np.testing.assert_allclose(Kg @ np.ones(5), 0.0)          # Konstante unbestraft
        Kd = regularization_matrix(5, K_DIRICHLET)
        self.assertGreater(np.linalg.eigvalsh(Kd).min(), 0.0)     # positiv definit
        np.testing.assert_allclose(np.diag(Kd), 2.0)
        Kc = regularization_matrix(5, K_CURVATURE)
        self.assertGreater(np.linalg.eigvalsh(Kc).min(), 0.0)


def _sphere_data(seed):
    q = np.arange(0.2, 20.0001, 0.2) / RG      # h₁Rg = 0.2 … h₂Rg = 20 [G77 Fig. 3]
    I, s = noisy(sphere_intensity(q, R_SPHERE, 1e4), 0.10, seed)
    return q, I, s


class TestSphere(unittest.TestCase):
    """[G77] Fig. 4/7: Kugel, Rg = 100 Å (hier 10 nm), D = 300 Å, 10 % Fehler."""

    def test_rg_i0_and_pr(self):
        for seed in range(5):
            q, I, s = _sphere_data(seed)
            sol = run_ift(q, I, s, IFTSettings(dmax=30.0, n_splines=25))
            self.assertLess(abs(sol.rg / RG - 1), 0.02)
            self.assertLess(abs(sol.i0 / 1e4 - 1), 0.05)
            self.assertTrue(sol.scan.inflexion_found)
            self.assertLess(sol.md, 1.5)
            pt = sphere_pr(sol.r, R_SPHERE)
            pt *= sol.i0 / (4 * np.pi * np.trapezoid(pt, sol.r))
            self.assertLess(np.linalg.norm(sol.pr - pt) / np.linalg.norm(pt), 0.05)

    def test_error_band_is_consistent(self):
        """Rg-Fehler aus der Kovarianz hat die richtige Größenordnung (Streuung über Seeds)."""
        rgs, errs = [], []
        for seed in range(15):
            q, I, s = _sphere_data(100 + seed)
            sol = run_ift(q, I, s, IFTSettings(dmax=30.0, n_splines=25))
            rgs.append(sol.rg)
            errs.append(sol.rg_err)
        ratio = np.std(rgs) / np.mean(errs)
        self.assertTrue(0.3 < ratio < 3.0, ratio)

    def test_flags_clean(self):
        q, I, s = _sphere_data(0)
        sol = run_ift(q, I, s, IFTSettings(dmax=30.0, n_splines=25))
        flags = {f.code: f for f in diagnose_ift(sol, guinier=guinier_rg(q, I, s))}
        self.assertEqual(flags['dmax_qmin'].level, LEVEL_OK)
        self.assertEqual(flags['lambda'].level, LEVEL_OK)
        self.assertEqual(flags['pr_negative'].level, LEVEL_OK)
        self.assertEqual(flags['pr_end'].level, LEVEL_OK)
        self.assertEqual(flags['rg_consistency'].level, LEVEL_OK)

    def test_too_small_dmax_is_flagged(self):
        q, I, s = _sphere_data(0)
        sol = run_ift(q, I, s, IFTSettings(dmax=18.0, n_splines=20))   # D_true = 25.8 nm
        flags = {f.code: f for f in diagnose_ift(sol)}
        problems = [flags['pr_end'].level, flags['fit_quality'].level]
        self.assertIn(LEVEL_WARNING, problems)

    def test_background_term(self):
        q, I, s = _sphere_data(1)
        sol = run_ift(q, I + 5.0, s, IFTSettings(dmax=30.0, n_splines=25, background=True))
        self.assertIsNotNone(sol.background)
        self.assertLess(abs(sol.background - 5.0), 5 * sol.background_err + 1.0)
        self.assertLess(abs(sol.rg / RG - 1), 0.03)

    def test_manual_lambda(self):
        q, I, s = _sphere_data(0)
        sol = run_ift(q, I, s, IFTSettings(dmax=30.0, n_splines=25, lam=1e-6))
        self.assertTrue(sol.lam_manual)
        self.assertEqual(sol.lam_rel, 1e-6)


class TestTruncatedLowQ(unittest.TestCase):
    """[G77] Fig. 9/10: Kette und Stab mit h₁Rg = 1.6, ΔhRg = 0.1, h₂Rg = 10, 5 % Fehler."""

    q = np.arange(1.6, 10.0001, 0.1) / RG

    def _median_rg_error(self, intensity, dmax, n_seeds=12):
        errs = []
        for seed in range(n_seeds):
            I, s = noisy(intensity, 0.05, 200 + seed)
            sol = run_ift(self.q, I, s, IFTSettings(dmax=dmax, n_splines=20))
            errs.append(abs(sol.rg / RG - 1) if np.isfinite(sol.rg) else 1.0)
        return float(np.median(errs))

    def test_chain(self):
        self.assertLess(self._median_rg_error(debye_intensity(self.q, RG, 1e4), 4 * RG), 0.2)

    def test_rod_near_true_length(self):
        for d in (3.0, 3.5):
            self.assertLess(self._median_rg_error(rod_intensity(self.q, L_ROD, 1e4), d * RG), 0.25)

    def test_dmax_flag_fires(self):
        flag = check_dmax_qmin(4 * RG, self.q[0])
        self.assertEqual(flag.level, LEVEL_WARNING)
        self.assertAlmostEqual(flag.value, 4 * RG * self.q[0] / np.pi)

    def test_guinier_not_applicable(self):
        I, s = noisy(debye_intensity(self.q, RG, 1e4), 0.05, 1)
        self.assertIsNone(guinier_rg(self.q, I, s))


class TestLargeSphereSimulation(unittest.TestCase):
    """Rauschfreie Simulation wie `GIFT/0_Sources/Sphere_142.txt` (SasView-Kugel R = 142 Å,
    q = 0.001 … 1 Å⁻¹; hier skaleninvariant als R = 142 nm bei q in nm⁻¹ gerechnet,
    1000 log-verteilte Punkte, Untergrund 0.001). Viele Shannon-Kanäle
    (≈ 90–125) → N muss aus N_s abgeleitet werden; σ wird relativ angenommen."""

    R = 142.0

    @classmethod
    def setUpClass(cls):
        from analysis.gift.pipeline import relative_sigma
        cls.q = np.logspace(-3, 0, 1000)
        cls.I = 29984.3 * sphere_intensity(cls.q, cls.R, 1.0) + 0.001
        cls.sigma = relative_sigma(cls.I, 0.01)
        cls.rg_true = np.sqrt(0.6) * cls.R

    def test_suggested_n_recovers_sphere(self):
        from analysis.gift.diagnostics import suggest_n_splines
        n = suggest_n_splines(300.0, self.q[0], self.q[-1])
        self.assertGreater(n, 100)
        sol = run_ift(self.q, self.I, self.sigma, IFTSettings(dmax=300.0, n_splines=n))
        self.assertLess(abs(sol.rg / self.rg_true - 1), 1e-3)
        self.assertLess(abs(sol.i0 / 29984.3 - 1), 1e-3)
        pt = sphere_pr(sol.r, self.R)
        pt *= sol.i0 / (4 * np.pi * np.trapezoid(pt, sol.r))
        self.assertLess(np.linalg.norm(sol.pr - pt) / np.linalg.norm(pt), 0.01)

    def test_coarse_basis_is_flagged(self):
        sol = run_ift(self.q, self.I, self.sigma, IFTSettings(dmax=300.0, n_splines=60))
        flags = {f.code: f for f in diagnose_ift(sol, sigma_source='relative',
                                                 sigma_relative=0.01)}
        self.assertEqual(flags['shannon'].level, LEVEL_WARNING)
        self.assertEqual(flags['shannon'].variant, 'coarse')
        self.assertEqual(flags['sigma_estimated'].variant, 'relative')

    def test_relative_sigma_in_pipeline(self):
        from analysis.gift.pipeline import run_ift_analysis
        a = run_ift_analysis(self.q, self.I, None, IFTSettings(dmax=300.0, n_splines=120),
                             sigma_relative=0.01)
        self.assertEqual(a.sigma_source, 'relative')
        pre = a.record.to_dict()['processing']['activities'][1]['parameters']
        self.assertEqual(pre['sigma_relative'], 0.01)
        self.assertLess(abs(a.solution.rg / self.rg_true - 1), 1e-3)


class TestMisc(unittest.TestCase):
    def test_shannon(self):
        self.assertAlmostEqual(shannon_channels(np.pi, 0.0, 3.0), 3.0)

    def test_estimate_sigma_order_of_magnitude(self):
        q, I, s = _sphere_data(3)
        est = estimate_sigma(q[:40], I[:40])
        ratio = np.median(est / s[:40])
        self.assertTrue(0.2 < ratio < 5.0, ratio)

    def test_input_validation(self):
        q = np.linspace(0.1, 1, 10)
        with self.assertRaises(ValueError):
            run_ift(q, q, np.zeros(10), IFTSettings(dmax=10))
        with self.assertRaises(ValueError):
            run_ift(q, q, np.ones(10), IFTSettings(dmax=10, n_splines=20))


if __name__ == '__main__':
    unittest.main()
