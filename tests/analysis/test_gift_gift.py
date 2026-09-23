"""
Tests Phase 3a: Strukturfaktoren (HS-PY, S_ave), BSSA, GIFT (Validierung 4 und 6 im Plan).
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy.integrate import quad

from analysis.gift.structure_factors import (s_percus_yevick, s_percus_yevick_avg, get_model,
                                             _py_coefficients, _j_closed, _j_quadrature)
from analysis.gift.bssa import minimize, BSSASettings, BSSACancelled
from analysis.gift.ift import IFTSettings, run_ift
from analysis.gift.gift import GIFTSettings, run_gift
from analysis.gift.pipeline import run_ift_analysis, export_ift_results
from analysis.gift.provenance import compute_sha256
from tests.analysis.synthetic import sphere_intensity, sphere_pr, noisy


class TestPercusYevick(unittest.TestCase):
    def test_forward_value(self):
        for phi in (0.05, 0.2, 0.4):
            s0 = s_percus_yevick(np.array([1e-9]), 7.0, phi)[0]
            self.assertAlmostEqual(s0, (1 - phi) ** 4 / (1 + 2 * phi) ** 2, places=12)

    def test_against_independent_quadrature(self):
        """J(x) = ∫₀¹ (α+βu+γu³) u² j₀(xu) du, geschlossene Form und GL gegen scipy.quad."""
        for phi in (0.1, 0.35):
            a, b, g = _py_coefficients(phi)
            for x in (0.3, 0.999, 1.001, 4.0, 25.0):
                ref = quad(lambda u: (a + b * u + g * u ** 3) * u ** 2 * np.sinc(x * u / np.pi),
                           0, 1, limit=200)[0]
                J = s_percus_yevick(np.array([x / 20.0]), 10.0, phi)   # x = 2qR
                S_ref = 1.0 / (1.0 + 24 * phi * ref)
                self.assertAlmostEqual(J[0], S_ref, places=10)
            # beide Zweige stimmen am Umschaltpunkt überein
            xs = np.array([0.8, 1.0, 1.2])
            aa, bb, gg = (np.full(3, v) for v in (a, b, g))
            np.testing.assert_allclose(_j_quadrature(xs, aa, bb, gg), _j_closed(xs, a, b, g),
                                       rtol=1e-9)

    def test_peak_and_limit(self):
        q = np.linspace(0.01, 3, 400)
        s = s_percus_yevick(q, 10.0, 0.3)
        self.assertGreater(s.max(), 1.3)                           # Wechselwirkungspeak
        self.assertAlmostEqual(q[np.argmax(s)] * 20.0, 2 * np.pi, delta=1.5)  # q_peak·σ ≈ 2π
        self.assertAlmostEqual(s[-1], 1.0, delta=0.02)

    def test_average_reduces_to_monodisperse(self):
        q = np.linspace(0.01, 2, 50)
        np.testing.assert_allclose(s_percus_yevick_avg(q, 10.0, 0.2, 0.0),
                                   s_percus_yevick(q, 10.0, 0.2), atol=1e-12)

    def test_average_damps_oscillations_but_keeps_s0(self):
        """[BP97 Fig. 1c]: Polydispersität glättet die Maxima, S(0) bleibt unverändert."""
        q = np.linspace(1e-4, 2, 300)
        mono = s_percus_yevick(q, 10.0, 0.15)
        avg = s_percus_yevick_avg(q, 10.0, 0.15, 0.4)
        self.assertAlmostEqual(avg[0], mono[0], places=6)
        self.assertLess(avg.max(), mono.max())

    def test_batch_shapes(self):
        q = np.linspace(0.01, 2, 30)
        out = s_percus_yevick_avg(q, np.array([8.0, 10.0, 12.0]), np.array([0.1, 0.2, 0.3]),
                                  np.array([0.0, 0.2, 0.4]))
        self.assertEqual(out.shape, (3, 30))
        np.testing.assert_allclose(out[1], s_percus_yevick_avg(q, 10.0, 0.2, 0.2), rtol=1e-12)


class TestBSSA(unittest.TestCase):
    @staticmethod
    def rosen(x):
        z = 4 * x - 2
        return (1 - z[0]) ** 2 + 100 * (z[1] - z[0] ** 2) ** 2

    @staticmethod
    def double_well(x):
        """Lokales Minimum bei z₀ ≈ +0.96 (f ≈ 0.29), globales bei z₀ ≈ −1.04 (f ≈ −0.31)."""
        z = 4 * x - 2
        return (z[0] ** 2 - 1) ** 2 + 0.3 * z[0] + z[1] ** 2

    def test_rosenbrock(self):
        r = minimize(self.rosen, [0.1, 0.9], BSSASettings(seed=3))
        np.testing.assert_allclose(r.x, [0.75, 0.75], atol=1e-4)
        self.assertLess(r.f, 1e-8)

    def test_escapes_local_minimum(self):
        """Reiner Simplex bleibt vom Start (+1) in der lokalen Mulde; BSSA findet meist die globale."""
        hits = sum(minimize(self.double_well, [0.75, 0.6], BSSASettings(seed=s)).f < -0.30
                   for s in range(30))
        self.assertGreaterEqual(hits, 25)

    def test_reproducible(self):
        r1 = minimize(self.double_well, [0.75, 0.6], BSSASettings(seed=7))
        r2 = minimize(self.double_well, [0.75, 0.6], BSSASettings(seed=7))
        np.testing.assert_array_equal(r1.x, r2.x)
        self.assertEqual(r1.n_evals, r2.n_evals)

    def test_bounds_respected_and_cancel(self):
        r = minimize(lambda x: float(np.sum((x - 1.3) ** 2)), [0.5, 0.5], BSSASettings(seed=1))
        self.assertTrue(np.all(r.x <= 1.0) and np.all(r.x >= 0.0))
        with self.assertRaises(BSSACancelled):
            minimize(self.rosen, [0.1, 0.9], BSSASettings(seed=1), callback=lambda *a: False)


def _bp97_data(noise, seed):
    """[BP97 §3.2.1]: Kugel R = 10 nm, S_ave(φ = 0.15, R_HS = 10 nm, μ = 0.4)."""
    q = np.linspace(0.05, 2.0, 200)
    intensity = sphere_intensity(q, 10.0, 1e3) * s_percus_yevick_avg(q, 10.0, 0.15, 0.4)
    I, s = noisy(intensity, noise, seed)
    return q, I, s


class TestGIFT(unittest.TestCase):
    START = {'phi': 0.18, 'r_hs': 12.0, 'mu': 0.5}   # überschätzte Startwerte wie [BP97]

    def _run(self, seed=1, noise=0.02, **kw):
        q, I, s = _bp97_data(noise, seed)
        return q, I, s, run_gift(q, I, s, IFTSettings(dmax=22.0, n_splines=25),
                                 GIFTSettings(model='hs_py_avg', start=dict(self.START),
                                              bssa=BSSASettings(seed=seed), **kw))

    def test_recovers_bp97_parameters_and_pr(self):
        q, I, s, r = self._run(seed=1)
        self.assertAlmostEqual(r.params['phi'], 0.15, delta=0.01)
        self.assertAlmostEqual(r.params['r_hs'], 10.0, delta=0.5)
        self.assertAlmostEqual(r.params['mu'], 0.40, delta=0.05)
        sol = r.solution
        self.assertLess(abs(sol.rg / (np.sqrt(0.6) * 10.0) - 1), 0.01)
        pt = sphere_pr(sol.r, 10.0)
        pt *= sol.i0 / (4 * np.pi * np.trapezoid(pt, sol.r))
        self.assertLess(np.linalg.norm(sol.pr - pt) / np.linalg.norm(pt), 0.02)
        self.assertLess(r.md, 1.5)
        self.assertGreater(r.md_without_sq, 10 * r.md)          # S(q) ist nötig
        for name in ('phi', 'r_hs', 'mu'):
            self.assertTrue(np.isfinite(r.param_errors[name]) and r.param_errors[name] > 0)
        # Formfaktor P(q) ≈ wahre Kugel
        pq = sol.extras['form_factor']
        true = sphere_intensity(q, 10.0, 1e3)
        self.assertLess(np.median(np.abs(pq / true - 1)[:60]), 0.03)

    def test_reproducible_with_seed(self):
        _, _, _, r1 = self._run(seed=4)
        _, _, _, r2 = self._run(seed=4)
        self.assertEqual(r1.params, r2.params)

    def test_fixed_parameter(self):
        _, _, _, r = self._run_fixed()
        self.assertEqual(r.params['mu'], 0.4)
        self.assertEqual(r.param_errors['mu'], 0.0)
        self.assertNotIn('mu', r.free)

    def _run_fixed(self):
        q, I, s = _bp97_data(0.02, 2)
        start = dict(self.START, mu=0.4)
        return q, I, s, run_gift(q, I, s, IFTSettings(dmax=22.0, n_splines=25),
                                 GIFTSettings(start=start, fixed=['mu'],
                                              bssa=BSSASettings(seed=2)))

    def test_invalid_start(self):
        q, I, s = _bp97_data(0.02, 1)
        with self.assertRaises(ValueError):
            run_gift(q, I, s, IFTSettings(dmax=22.0), GIFTSettings(start={'phi': 0.9}))


DATA_DIR = Path(__file__).resolve().parent / 'data'


def _sasview_curve(name):
    """SasView-Referenzkurve laden; q von Å⁻¹ nach nm⁻¹ (siehe data/README.md)."""
    d = np.loadtxt(DATA_DIR / name, skiprows=1)
    return 10.0 * d[:, 0], d[:, 1]


class TestSasViewReference(unittest.TestCase):
    """Unabhängige Referenz: SasView/sasmodels `sphere@hardsphere` bzw. `sphere@hayter_msa`,
    R = 140 Å = 14 nm, φ = 0.2, Untergrund 0.001 cm⁻¹, rauschfrei."""

    R = 14.0

    def test_percus_yevick_matches_sasmodels(self):
        q, I = _sasview_curve('sasview_sphere140A_hardsphere.txt')
        model = sphere_intensity(q, self.R, 1.0) * s_percus_yevick(q, self.R, 0.2)
        A = np.column_stack([model, np.ones_like(q)])
        (scale, bg), *_ = np.linalg.lstsq(A / I[:, None], np.ones_like(I), rcond=None)
        self.assertAlmostEqual(scale, 0.2 * 28735.0, delta=5.0)     # φ·V·Δρ² in cm⁻¹
        self.assertAlmostEqual(bg, 0.001, places=6)
        self.assertLess(np.max(np.abs((A @ [scale, bg]) / I - 1)), 1e-9)

    def test_gift_recovers_hardsphere_parameters(self):
        from analysis.gift.pipeline import relative_sigma
        from analysis.gift.diagnostics import suggest_n_splines
        q, I = _sasview_curve('sasview_sphere140A_hardsphere.txt')
        ift = IFTSettings(dmax=30.0, n_splines=suggest_n_splines(30.0, q[0], q[-1]))
        r = run_gift(q, I, relative_sigma(I, 0.01), ift,
                     GIFTSettings(model='hs_py', start={'phi': 0.25, 'r_hs': 16.0},
                                  bssa=BSSASettings(seed=1)))
        self.assertAlmostEqual(r.params['phi'], 0.2, delta=2e-3)
        self.assertAlmostEqual(r.params['r_hs'], self.R, delta=0.05)
        self.assertLess(abs(r.solution.rg / (np.sqrt(0.6) * self.R) - 1), 5e-4)

    def test_hs_average_represents_msa_with_apparent_parameters(self):
        """[W99]: S_ave bildet einen anderen S(q) (hier geladen, MSA) mit scheinbaren
        Parametern nach — p(r) bzw. Rg bleiben dennoch korrekt."""
        from analysis.gift.pipeline import relative_sigma
        from analysis.gift.diagnostics import suggest_n_splines
        q, I = _sasview_curve('sasview_sphere140A_haytermsa.txt')
        ift = IFTSettings(dmax=30.0, n_splines=suggest_n_splines(30.0, q[0], q[-1]))
        plain = run_ift(q, I, relative_sigma(I, 0.01), ift)
        r = run_gift(q, I, relative_sigma(I, 0.01), ift,
                     GIFTSettings(model='hs_py_avg',
                                  start={'phi': 0.25, 'r_hs': 16.0, 'mu': 0.2},
                                  bssa=BSSASettings(seed=1)))
        rg_true = np.sqrt(0.6) * self.R
        self.assertGreater(abs(plain.rg / rg_true - 1), 0.03)       # ohne S(q) deutlich falsch
        self.assertLess(abs(r.solution.rg / rg_true - 1), 2e-3)
        self.assertGreater(r.params['phi'], 0.22)                   # scheinbarer Parameter


class TestGIFTPipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        q, I, s = _bp97_data(0.02, 5)
        self.f = self.tmp / "bp97.dat"
        np.savetxt(self.f, np.column_stack([q, I, s]))
        self.q, self.I, self.s = q, I, s

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_model_none_equals_ift(self):
        a = run_ift_analysis(self.q, self.I, self.s, IFTSettings(dmax=22.0, n_splines=25),
                             gift_settings=GIFTSettings(model='none'))
        self.assertIsNone(a.gift)
        plain = run_ift(self.q, self.I, self.s, IFTSettings(dmax=22.0, n_splines=25))
        self.assertAlmostEqual(a.solution.rg, plain.rg, places=10)

    def test_provenance_and_export(self):
        seen = []
        a = run_ift_analysis(self.q, self.I, self.s, IFTSettings(dmax=22.0, n_splines=25),
                             source_file=self.f,
                             gift_settings=GIFTSettings(start=dict(TestGIFT.START),
                                                        bssa=BSSASettings(seed=9)),
                             progress=lambda *args: seen.append(args) or True)
        self.assertTrue(seen)
        codes = {f.code: f for f in a.flags}
        self.assertEqual(codes['gift_improvement'].variant, 'improved')
        self.assertEqual(codes['gift_apparent'].level, 'info')
        self.assertEqual(codes['gift_bound'].level, 'ok')
        paths = export_ift_results(a)
        for key in ('sq', 'pq'):
            self.assertTrue(paths[key].exists())
        rec = json.loads(paths['prov'].read_text(encoding='utf-8'))
        types = [x['type'] for x in rec['processing']['activities']]
        self.assertEqual(types, ['data_loading', 'preprocessing', 'gift_bssa', 'ift', 'export'])
        gift_act = rec['processing']['activities'][2]
        self.assertEqual(gift_act['parameters']['bssa']['seed'], 9)
        self.assertEqual(gift_act['parameters']['model'], 'hs_py_avg')
        self.assertEqual(rec['reproducibility']['random_seed'], 9)
        for out in rec['output']['catalog']:
            self.assertEqual(out['sha256'], compute_sha256(out['path']))
        self.assertIn("GIFT: S(q) = hs_py_avg", paths['pr'].read_text(encoding='utf-8'))
        sq = np.loadtxt(paths['sq'])
        np.testing.assert_allclose(sq[:, 1], a.gift.structure_factor)

    def test_models_registered(self):
        for key in ('none', 'hs_py', 'hs_py_avg', 'rmsa'):
            self.assertEqual(get_model(key).key, key)
        with self.assertRaises(ValueError):
            get_model('unbekanntes_modell')


if __name__ == '__main__':
    unittest.main()
