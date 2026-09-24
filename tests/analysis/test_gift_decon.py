"""
Tests Phase 6b: DECON — Kontrastprofil als Faltungswurzel von p(r) [Glatter 1981],
analytische Überlappungsintegrale [Glatter & Hainisch 1984], Polydispersität
[Mittelbach & Glatter 1998], Stufenmodell mit variablen Breiten [GH84].
"""

import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy.special import j0, j1

from analysis.gift import parallel
from analysis.gift.ift import IFTSettings, run_ift
from analysis.gift.gift import GIFTSettings
from analysis.gift.decon import (step_forms, ProfileBasis, poly_forms, poly_intensity,
                                 size_nodes, run_decon, optimize_step_model, DeconSettings)
from analysis.gift.pipeline import (run_ift_analysis, run_decon_analysis,
                                    run_step_model_analysis, export_ift_results)
from analysis.gift.sf_models import s_sticky
from tests.analysis.synthetic import sphere_pr, noisy

Q = np.geomspace(0.03, 3.0, 300)


def sphere_amp(q, R):
    x = q * R
    return 4 / 3 * np.pi * R ** 3 * 3 * (np.sin(x) - x * np.cos(x)) / x ** 3


def core_shell(q, r_core, r_out, rho_core, rho_shell):
    return rho_core * sphere_amp(q, r_core) + rho_shell * (sphere_amp(q, r_out)
                                                           - sphere_amp(q, r_core))


def at(d, x):
    return float(np.interp(x, d.x, d.rho))


class TestOverlapIntegrals(unittest.TestCase):
    R = 10.0
    r = np.linspace(0, 20.0, 201)

    def test_homogeneous_shapes(self):
        """Eine Stufe: Kugel [G77], Kreisscheibe (Porod 1948) und Strecke exakt."""
        p = step_forms([0, self.R], self.r, 'sphere')[:, 0, 0]
        ref = sphere_pr(self.r, self.R)
        ref *= (4 / 3 * np.pi * self.R ** 3) ** 2 / (4 * np.pi * np.trapezoid(ref, self.r))
        self.assertLess(np.max(np.abs(p - ref)) / ref.max(), 1e-8)
        x = self.r / (2 * self.R)
        g = np.where(x < 1, np.arccos(np.minimum(x, 1)) - x * np.sqrt(np.maximum(1 - x * x, 0)), 0)
        pc = step_forms([0, self.R], self.r, 'cylinder')[:, 0, 0]
        np.testing.assert_allclose(pc, self.r * 2 * self.R ** 2 * g, atol=1e-10)
        pt = step_forms([0, self.R], self.r, 'lamella')[:, 0, 0]
        np.testing.assert_allclose(pt, np.maximum(2 * self.R - self.r, 0), atol=1e-12)

    def test_pr_and_amplitude_agree(self):
        """Fourier-Transformierte von p(r) = I(q) aus den Amplituden, auch polydispers."""
        b = ProfileBasis(self.R, 8)
        xs = np.linspace(0, self.R, 300)
        c = np.linalg.lstsq(b.evaluate(xs), np.where(xs < 6, -0.5, 1.0), rcond=None)[0]
        q = np.geomspace(0.02, 1.5, 25)
        rr = np.linspace(0, 2 * self.R * 1.8, 4001)
        kern = {'sphere': lambda: 4 * np.pi * np.sinc(np.outer(q, rr) / np.pi),
                'cylinder': lambda: (np.pi / q)[:, None] * 2 * np.pi * j0(np.outer(q, rr)),
                'lamella': lambda: (2 * np.pi / q ** 2)[:, None] * 2 * np.cos(np.outer(q, rr))}
        for geom, K in kern.items():
            for sig in (0.0, 0.15):
                p = np.einsum('i,kij,j->k', c, poly_forms(b, rr, geom, sig), c)
                I1 = np.trapezoid(p * K(), rr, axis=1)
                I2 = poly_intensity(b, q, geom, c, sig)
                self.assertLess(np.max(np.abs(I1 - I2)) / np.max(np.abs(I2)), 1e-4, (geom, sig))


class TestInverse(unittest.TestCase):
    def test_inverted_core(self):
        I, s = noisy(core_shell(Q, 6.0, 10.0, -0.6, 1.0) ** 2, 0.01, 1)
        d = run_decon(run_ift(Q, I, s, IFTSettings(dmax=20.0, n_splines=35)))
        self.assertAlmostEqual(at(d, 2.0) / at(d, 8.0), -0.6, delta=0.1)
        self.assertLess(d.md_pr, 2.0)
        self.assertTrue(d.inflexion_found)

    def test_steps_basis_and_sign(self):
        """Stufenbasis [G81]; Kern +1, Schale −0.4: ∫Δρ dV < 0 → umgekehrtes Vorzeichen."""
        I, s = noisy(core_shell(Q, 6.0, 10.0, 1.0, -0.4) ** 2, 0.01, 2)
        d = run_decon(run_ift(Q, I, s, IFTSettings(dmax=20.0, n_splines=35)),
                      DeconSettings(basis='steps'))
        self.assertLess(at(d, 2.0), 0)
        self.assertAlmostEqual(at(d, 2.0) / at(d, 8.0), -2.5, delta=0.5)

    def test_step_model(self):
        """Zweistufenmodell: Radien und Kontrastverhältnis [GH84 Fig. 5]."""
        I, s = noisy(core_shell(Q, 6.0, 10.0, -0.6, 1.0) ** 2, 0.01, 3)
        sm = optimize_step_model(run_ift(Q, I, s, IFTSettings(dmax=20.0, n_splines=35)), 2)
        np.testing.assert_allclose(sm['edges'], [6.0, 10.0], atol=0.15)
        self.assertAlmostEqual(sm['heights'][0] / sm['heights'][1], -0.6, delta=0.05)

    def test_polydispersity_scan(self):
        """[MG98]: Schulz-Polydispersität σ = 0.2 (P ≈ 24 %) wird gefunden, Profil stimmt."""
        xs, ws = size_nodes(0.2)
        I0 = sum(w * core_shell(Q, 6.0 * x, 10.0 * x, -0.6, 1.0) ** 2 for x, w in zip(xs, ws))
        I, s = noisy(I0, 0.01, 4)
        sol = run_ift(Q, I, s, IFTSettings(dmax=34.0, n_splines=35))
        mono = run_decon(sol)
        d = run_decon(sol, DeconSettings(polydispersity='scan', p_scan=(0.0, 0.4, 11)))
        self.assertAlmostEqual(d.sigma_poly, 0.2, delta=0.04)
        self.assertLess(d.md_pr, mono.md_pr / 5)
        self.assertIn('decon_poly', {f.code for f in d.flags})
        self.assertEqual(next(f for f in mono.flags if f.code == 'decon_fit').variant, 'worse')
        sm = optimize_step_model(sol, 2, d.sigma_poly)
        np.testing.assert_allclose(sm['edges'], [6.0, 10.0], atol=0.4)
        self.assertAlmostEqual(sm['heights'][0] / sm['heights'][1], -0.6, delta=0.1)

    def test_lamella_bilayer(self):
        """Symmetrische Doppelschicht (Kern −0.5, Kopfgruppen +1): Stufenmodell exakt; das
        glatte Profil ist mehrdeutig — dann muss die richtige Lösung unter den Alternativen
        sein oder die Hauptlösung sein."""
        q = np.geomspace(0.05, 4.0, 300)
        A = 2 * (-0.5 * np.sin(2 * q) / q + 1.0 * (np.sin(3 * q) - np.sin(2 * q)) / q)
        I, s = noisy(2 * np.pi / q ** 2 * A ** 2, 0.01, 5)
        sol = run_ift(q, I, s, IFTSettings(dmax=6.0, n_splines=25, kind='thickness'))
        d = run_decon(sol)
        self.assertEqual(d.geometry, 'lamella')
        ratios = [at(d, 0.5) / at(d, 2.6)] + [
            np.interp(0.5, d.x, a['rho']) / np.interp(2.6, d.x, a['rho']) for a in d.alternatives]
        self.assertLess(min(abs(r_ + 0.5) for r_ in ratios), 0.15, ratios)
        sm = optimize_step_model(sol, 2)
        np.testing.assert_allclose(sm['edges'], [2.0, 3.0], atol=0.1)

    def test_cylinder_cross_section(self):
        q = np.geomspace(0.05, 3.0, 300)

        def disk(R):
            x = q * R
            return np.pi * R ** 2 * 2 * j1(x) / x
        A = -0.5 * disk(3.0) + 1.0 * (disk(5.0) - disk(3.0))
        I, s = noisy(np.pi / q * A ** 2, 0.01, 6)
        sol = run_ift(q, I, s, IFTSettings(dmax=10.0, n_splines=25, kind='cross_section'))
        d = run_decon(sol)
        self.assertEqual(d.geometry, 'cylinder')
        self.assertAlmostEqual(at(d, 1.0) / at(d, 4.2), -0.5, delta=0.15)

    def test_size_distribution_rejected(self):
        I, s = noisy(sphere_amp(Q, 5.0) ** 2, 0.01, 7)
        sol = run_ift(Q, I, s, IFTSettings(dmax=6.0, n_splines=15, kind='size_sphere'))
        with self.assertRaises(ValueError):
            run_decon(sol)


class TestCoreShellSticky(unittest.TestCase):
    """Nachbau der SasView-Referenz (core_shell_sphere@stickyhardsphere): Kern R = 33 nm,
    Schale 17.6 nm, Kontraste −2/−1, φ = 0.1, τ = 0.4, δ = 0.07, R_HS = 50.6 nm."""

    @classmethod
    def tearDownClass(cls):
        parallel.shutdown_pool()

    def test_gift_and_decon(self):
        q = np.geomspace(0.005, 1.0, 350)
        P = core_shell(q, 33.0, 50.6, -2.0, -1.0) ** 2 * 1e-6
        I, s = noisy(P * s_sticky(q, 50.6, 0.1, 0.4, 0.07), 0.01, 8)
        a = run_ift_analysis(q, I, s, IFTSettings(dmax=101.2, n_splines=60),
                             gift_settings=GIFTSettings(
                                 model='sticky', fixed=['perturb'],
                                 start=dict(phi=0.15, r_hs=55.0, stickiness=0.5, perturb=0.07)))
        g = a.gift.params
        self.assertAlmostEqual(g['phi'], 0.1, delta=0.01)
        self.assertAlmostEqual(g['r_hs'], 50.6, delta=1.0)
        self.assertAlmostEqual(g['stickiness'], 0.4, delta=0.04)
        d = run_decon_analysis(a)
        self.assertAlmostEqual(at(d, 15.0) / at(d, 42.0), 2.0, delta=0.2)
        sm = run_step_model_analysis(a, 2)
        np.testing.assert_allclose(sm['edges'], [33.0, 50.6], atol=1.0)
        self.assertAlmostEqual(sm['heights'][0] / sm['heights'][1], 2.0, delta=0.1)
        with tempfile.TemporaryDirectory() as tmp:
            w = export_ift_results(a, out_dir=tmp, source_file=Path(tmp) / 'cs.dat',
                                   write_w3c=False)
            text = w['decon'].read_text(encoding='utf-8')
            self.assertTrue(text.startswith('# Kontrastprofil DECON'))
            self.assertIn('Stufenmodell: Grenzen', text)
            acts = a.extras['exported_record'].to_dict()['processing']['activities']
            dec = next(x for x in acts if x['type'] == 'decon')
            self.assertIn('step_model', dec['results_summary'])


if __name__ == '__main__':
    unittest.main()
