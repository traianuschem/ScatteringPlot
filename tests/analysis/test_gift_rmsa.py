"""
Tests Phase 3b: RMSA-Strukturfaktor für geladene Kugeln (Hayter-Penfold/Hansen-Hayter)
und GIFT für geladene Systeme (Validierung 8 im Plan).

Referenzen:
- Testwerte aus sasmodels `hayter_msa.py` (R = 20.75 Å, z = 19, φ = 0.0192, salzfrei)
- SasView-Kurve `sphere@hayter_msa` (tests/analysis/data, R = 140 Å, φ = 0.2)
- Simulation nach Fritz, Bergmann & Glatter (2000): R = 2.5 nm, φ = 0.05, z = 25, 10 mM Salz
"""

import unittest
from pathlib import Path

import numpy as np

from analysis.gift.rmsa import (s_hayter_msa, rmsa_coefficients, dielectric_constant_water,
                                RMSAError)
from analysis.gift.structure_factors import s_percus_yevick, get_model
from analysis.gift.ift import IFTSettings
from analysis.gift.gift import GIFTSettings, run_gift
from analysis.gift.bssa import BSSASettings
from analysis.gift.pipeline import relative_sigma
from analysis.gift.diagnostics import suggest_n_splines, diagnose_gift
from tests.analysis.synthetic import sphere_intensity, noisy

DATA = Path(__file__).resolve().parent / 'data'
ENV_SASVIEW = {'temperature': 318.16, 'salt': 0.001, 'eps_r': 71.08}


class TestRMSAStructureFactor(unittest.TestCase):
    def test_sasmodels_reference_values(self):
        """sasmodels-Unit-Test (q in Å⁻¹ → nm⁻¹, R = 20.75 Å): 6-stellige Referenzwerte."""
        q = 10 * np.array([0.00001, 0.0010, 0.01, 0.075])
        ref = np.array([0.0711646, 0.0712928, 0.0847006, 1.07150])
        s = s_hayter_msa(q, 2.075, 0.0192, 19.0, 298.0, 0.0, 78.0)
        np.testing.assert_allclose(s, ref, rtol=1e-5)

    def test_rescaling_in_dilute_case(self):
        """[HH82]: bei φ = 0.0192 gäbe die MSA g(σ+) < 0 → Rescaling bis g(σ'+) = 0."""
        _, info = rmsa_coefficients(2.075, 0.0192, 19.0, 298.0, 0.0, 78.0)
        self.assertLess(info['rescale_s'], 0.9)
        self.assertGreater(info['eta_rescaled'], 0.0192)
        self.assertAlmostEqual(info['g_contact'], 0.0, places=3)

    def test_no_rescaling_when_concentrated(self):
        _, info = rmsa_coefficients(14.0, 0.2, 19.0, **{'temperature': 318.16,
                                                        'salt_molar': 0.001, 'eps_r': 71.08})
        self.assertEqual(info['rescale_s'], 1.0)
        self.assertGreater(info['g_contact'], 0.0)

    def test_sasview_curve(self):
        d = np.loadtxt(DATA / 'sasview_sphere140A_haytermsa.txt', skiprows=1)
        q, I = 10 * d[:, 0], d[:, 1]
        model = sphere_intensity(q, 14.0, 1.0) * s_hayter_msa(q, 14.0, 0.2, 19.0, **ENV_SASVIEW)
        A = np.column_stack([model, np.ones_like(q)])
        (scale, bg), *_ = np.linalg.lstsq(A / I[:, None], np.ones_like(I), rcond=None)
        self.assertAlmostEqual(scale, 5747.0, delta=1.0)             # wie bei der HS-Kurve
        self.assertLess(np.max(np.abs((A @ [scale, bg]) / I - 1)), 1e-6)

    def test_zero_charge_limit_is_percus_yevick(self):
        q = np.linspace(0.05, 3, 60)
        s = s_hayter_msa(q, 5.0, 0.2, 0.01, 298.15, 0.01, 78.3)
        np.testing.assert_allclose(s, s_percus_yevick(q, 5.0, 0.2), atol=1e-5)

    def test_charge_lowers_compressibility(self):
        q = np.array([1e-3])
        s_low = s_hayter_msa(q, 5.0, 0.1, 5.0, 298.15, 0.01, 78.3)[0]
        s_high = s_hayter_msa(q, 5.0, 0.1, 50.0, 298.15, 0.01, 78.3)[0]
        self.assertLess(s_high, s_low)                               # [HP81]: S(0) sinkt

    def test_batch_and_failure_gives_nan(self):
        q = np.linspace(0.05, 2, 20)
        out = s_hayter_msa(q, np.array([5.0, 5.0]), np.array([0.2, 0.2]),
                           np.array([10.0, 1e-5]), 298.15, 0.1, 78.3)
        self.assertEqual(out.shape, (2, 20))
        self.assertTrue(np.all(np.isfinite(out[0])))
        with self.assertRaises(RMSAError):
            rmsa_coefficients(5.0, 0.2, 1e-5, 298.15, 0.1, 78.3)

    def test_dielectric_constant_water(self):
        self.assertAlmostEqual(dielectric_constant_water(298.15), 78.30, delta=0.05)
        self.assertAlmostEqual(dielectric_constant_water(318.16), 71.4, delta=0.5)

    def test_registry_defaults(self):
        m = get_model('rmsa')
        self.assertEqual(set(m.default_fixed()), {'temperature', 'salt', 'eps_r'})
        self.assertEqual(m.default_starts, 8)


class TestGIFTCharged(unittest.TestCase):
    def test_sasview_msa_with_known_volume_fraction(self):
        """φ aus der Einwaage bekannt (fest) → R_HS und z eindeutig [F00]."""
        d = np.loadtxt(DATA / 'sasview_sphere140A_haytermsa.txt', skiprows=1)
        q, I = 10 * d[:, 0], d[:, 1]
        ift = IFTSettings(dmax=30.0, n_splines=suggest_n_splines(30.0, q[0], q[-1]))
        r = run_gift(q, I, relative_sigma(I, 0.01), ift,
                     GIFTSettings(model='rmsa', n_starts=2,
                                  start={'phi': 0.2, 'r_hs': 16.0, 'charge': 30.0, **ENV_SASVIEW},
                                  fixed=['phi', 'temperature', 'salt', 'eps_r'],
                                  bssa=BSSASettings(seed=1)))
        self.assertAlmostEqual(r.params['r_hs'], 14.0, delta=0.05)
        self.assertAlmostEqual(r.params['charge'], 19.0, delta=0.3)
        self.assertLess(abs(r.solution.rg / (np.sqrt(0.6) * 14.0) - 1), 1e-3)
        self.assertIn('debye_length_nm', r.model_info)

    def test_fritz_simulation(self):
        """[F00 §IV]: R = 2.5 nm, φ = 0.05, z = 25, 10 mM Salz, 298.15 K, Wasser."""
        q = np.linspace(0.1, 3.0, 150)
        env = {'temperature': 298.15, 'salt': 0.01, 'eps_r': 78.30}
        I, s = noisy(sphere_intensity(q, 2.5, 100.0) * s_hayter_msa(q, 2.5, 0.05, 25.0, **env),
                     0.02, 1)
        r = run_gift(q, I, s, IFTSettings(dmax=6.0, n_splines=20),
                     GIFTSettings(model='rmsa', n_starts=4,
                                  start={'phi': 0.08, 'r_hs': 3.0, 'charge': 40.0, **env},
                                  bssa=BSSASettings(seed=1)))
        self.assertAlmostEqual(r.params['phi'], 0.05, delta=0.015)
        self.assertAlmostEqual(r.params['r_hs'], 2.5, delta=0.35)
        self.assertAlmostEqual(r.params['charge'], 25.0, delta=6.0)
        self.assertLess(abs(r.solution.rg / (np.sqrt(0.6) * 2.5) - 1), 0.01)
        self.assertLess(r.md, 1.5)
        codes = {f.code: f for f in diagnose_gift(r, get_model('rmsa'))}
        self.assertIn('gift_multistart', codes)
        self.assertEqual(codes['gift_rmsa_rescaled'].variant, 'rescaled')

    def test_charge_and_salt_free_is_flagged(self):
        q = np.linspace(0.1, 3.0, 80)
        env = {'temperature': 298.15, 'salt': 0.01, 'eps_r': 78.30}
        I, s = noisy(sphere_intensity(q, 2.5, 100.0) * s_hayter_msa(q, 2.5, 0.05, 25.0, **env),
                     0.02, 3)
        r = run_gift(q, I, s, IFTSettings(dmax=6.0, n_splines=15),
                     GIFTSettings(model='rmsa', n_starts=1, lambda_cycles=1,
                                  start={'phi': 0.05, 'r_hs': 2.5, 'charge': 25.0, **env},
                                  fixed=['phi', 'r_hs', 'temperature', 'eps_r'],
                                  bssa=BSSASettings(seed=1, max_evals=400)))
        codes = {f.code for f in diagnose_gift(r, get_model('rmsa'))}
        self.assertIn('gift_rmsa_degenerate', codes)


if __name__ == '__main__':
    unittest.main()
