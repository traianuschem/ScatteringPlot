"""
Tests Phase 6a: IFT-Arten (kernels.py) — Querschnitt, Dicke, Größenverteilungen
[Glatter 1980a/b]; Skalierungstabelle für DREAM, Guinier-Varianten, Export.
"""

import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy.special import j1

from analysis.gift.ift import IFTSettings, run_ift, IFTDecomposition, regularization_matrix
from analysis.gift.kernels import KINDS, get_kernel, dmax_limit
from analysis.gift.likelihood import (ScaledBasisTable, MarginalLikelihood, ParameterSpace,
                                      LOG_LAMBDA)
from analysis.gift.transform import design_matrix, make_basis
from analysis.gift.diagnostics import guinier_rg, shannon_channels
from analysis.gift.sizes import size_statistics
from analysis.gift.pipeline import run_ift_analysis, export_ift_results
from tests.analysis.synthetic import noisy

Q = np.geomspace(0.05, 3.0, 250)


def cylinder_cross_section(q, R):
    """Lange Zylinder (L = 1): I = (π/q)·(πR²)²·[2J₁(qR)/(qR)]²."""
    x = q * R
    return (np.pi / q) * (np.pi * R ** 2) ** 2 * (2 * j1(x) / x) ** 2


def lamella(q, T):
    """Flache Lamelle (A = 1): I = (2π/q²)·T²·[sin(qT/2)/(qT/2)]²."""
    return (2 * np.pi / q ** 2) * T ** 2 * np.sinc(q * T / 2 / np.pi) ** 2


def sphere_amp(x):
    return 3 * (np.sin(x) - x * np.cos(x)) / x ** 3


def polydisperse_spheres(q, mean, sd):
    R = np.linspace(0.05, mean + 8 * sd, 3000)
    w = np.exp(-0.5 * ((R - mean) / sd) ** 2)
    w /= np.trapezoid(w, R)                          # D_V normiert (∫D_V = 1)
    V = 4 / 3 * np.pi * R ** 3
    return np.trapezoid(w * V * sphere_amp(np.outer(q, R)) ** 2, R, axis=1), R, w


class TestKernels(unittest.TestCase):
    def test_scaled_table_matches_design(self):
        for kind in KINDS:
            t = ScaledBasisTable(15, 3.0 * 25 * 1.01, kind=kind)
            for d in (12.0, 25.0):
                A1 = t.design(Q, d)
                A2 = design_matrix(Q, make_basis(d, 15, kind), kind)
                self.assertLess(np.max(np.abs(A1 - A2)) / np.max(np.abs(A2)), 1e-7, kind)

    def test_left_free_basis(self):
        b = make_basis(10.0, 12, 'thickness')
        self.assertEqual(b.evaluate([0.0]).shape, (1, 12))
        self.assertAlmostEqual(b.evaluate([0.0])[0, 0], 1.0)
        self.assertAlmostEqual(np.abs(b.evaluate([10.0])).max(), 0.0)
        K = regularization_matrix(12, 'dirichlet', left_free=True)
        self.assertTrue(np.all(np.linalg.eigvalsh(K) > 0))
        self.assertAlmostEqual(np.abs(make_basis(10.0, 12).evaluate([0.0])).max(), 0.0)

    def test_limits_for_radius_distributions(self):
        self.assertAlmostEqual(dmax_limit(0.1, 'size_sphere'), np.pi / 0.2)
        self.assertAlmostEqual(dmax_limit(0.1, 'size_lamella'), np.pi / 0.1)
        self.assertAlmostEqual(shannon_channels(10, 0.1, 1.1, 'size_cylinder'),
                               2 * shannon_channels(10, 0.1, 1.1))


class TestCrossSectionThickness(unittest.TestCase):
    def test_cross_section(self):
        R = 5.0
        I, s = noisy(cylinder_cross_section(Q, R), 0.02, 1)
        sol = run_ift(Q, I, s, IFTSettings(dmax=2 * R, n_splines=20, kind='cross_section'))
        self.assertAlmostEqual(sol.rg, R / np.sqrt(2), delta=0.01 * R)
        self.assertAlmostEqual(sol.i0 / (np.pi * R ** 2) ** 2, 1.0, delta=0.03)
        self.assertLess(sol.md, 1.3)
        g = guinier_rg(Q, I, s, dim=2)
        self.assertAlmostEqual(g[0], R / np.sqrt(2), delta=0.03 * R)

    def test_finite_cylinder(self):
        """Orientierungsgemittelter Zylinder (L = 20·R); Querschnitts-IFT im Bereich q > 2π/L."""
        R, L = 3.0, 60.0
        q = np.geomspace(2 * np.pi / L * 1.5, 3.0, 200)
        mu, wmu = np.polynomial.legendre.leggauss(200)
        mu, wmu = 0.5 * (mu + 1), 0.5 * wmu
        qa = np.outer(q, np.sqrt(1 - mu ** 2)) * R
        qc = np.outer(q, mu) * L / 2
        amp = np.where(qa > 1e-8, 2 * j1(qa) / np.where(qa > 1e-8, qa, 1), 1) * np.sinc(qc / np.pi)
        I0 = (np.pi * R ** 2 * L) ** 2 * (amp ** 2 @ wmu)
        I, s = noisy(I0, 0.01, 4)
        sol = run_ift(q, I, s, IFTSettings(dmax=2 * R, n_splines=15, kind='cross_section'))
        self.assertAlmostEqual(sol.rg, R / np.sqrt(2), delta=0.03 * R)

    def test_finite_cylinder_lowq_flag(self):
        """[G80b]: q_min zu klein → q·I steigt am Anfang an → Flag; passend gewählt → ok."""
        R, L = 3.0, 60.0
        mu, wmu = np.polynomial.legendre.leggauss(200)
        mu, wmu = 0.5 * (mu + 1), 0.5 * wmu
        for q_min, level in ((0.02, 'warning'), (2 * np.pi / L * 1.5, 'ok')):
            q = np.geomspace(q_min, 3.0, 200)
            qa = np.outer(q, np.sqrt(1 - mu ** 2)) * R
            qc = np.outer(q, mu) * L / 2
            amp = 2 * j1(qa) / qa * np.sinc(qc / np.pi)
            I, s = noisy((np.pi * R ** 2 * L) ** 2 * (amp ** 2 @ wmu), 0.01, 4)
            a = run_ift_analysis(q, I, s, IFTSettings(dmax=2 * R, n_splines=15,
                                                      kind='cross_section'))
            flag = next(f for f in a.flags if f.code == 'cross_section_lowq')
            self.assertEqual(flag.level, level)

    def test_thickness(self):
        T = 4.0
        I, s = noisy(lamella(Q, T), 0.02, 2)
        sol = run_ift(Q, I, s, IFTSettings(dmax=T, n_splines=20, kind='thickness'))
        self.assertAlmostEqual(sol.rg, T / np.sqrt(12), delta=0.01 * T)
        self.assertAlmostEqual(sol.i0 / T ** 2, 1.0, delta=0.03)
        self.assertAlmostEqual(sol.pr[0] / T, 1.0, delta=0.05)     # p_t(0) = T (≠ 0)
        g = guinier_rg(Q, I, s, dim=1)
        self.assertAlmostEqual(g[0], T / np.sqrt(12), delta=0.03 * T)


class TestSizeDistributions(unittest.TestCase):
    def test_spheres(self):
        I0, R, w = polydisperse_spheres(Q, 8.0, 1.5)
        I, s = noisy(I0, 0.02, 3)
        sol = run_ift(Q, I, s, IFTSettings(dmax=16.0, n_splines=25, kind='size_sphere'))
        z = size_statistics(sol)
        self.assertAlmostEqual(z['mean_V'], 8.0, delta=0.1)
        self.assertAlmostEqual(z['std_V'], 1.5, delta=0.1)
        self.assertAlmostEqual(z['mode'], 8.0, delta=0.3)
        self.assertAlmostEqual(z['volume'], 1.0, delta=0.02)
        self.assertLess(z['negative_fraction'], 0.02)
        V = 4 / 3 * np.pi * R ** 3
        rg = np.sqrt(0.6 * np.trapezoid(w * V * R ** 2, R) / np.trapezoid(w * V, R))
        self.assertAlmostEqual(sol.rg, rg, delta=0.01 * rg)
        # Anzahlverteilung: nur im signifikanten Bereich, aber in der richtigen Größenordnung
        self.assertAlmostEqual(z['mean_N'], 6.9, delta=0.4)

    def test_number_distribution_direct(self):
        """D_N als Primärgröße [G80a Gl. 1a]: Anzahlmittel ohne Einschränkung auf R ≥ π/q_max."""
        I0, R, w = polydisperse_spheres(Q, 8.0, 1.5)
        I, s = noisy(I0, 0.02, 3)
        sol = run_ift(Q, I, s, IFTSettings(dmax=16.0, n_splines=25, kind='size_sphere_n'))
        z = size_statistics(sol)
        self.assertEqual(z['primary'], 'D_N')
        self.assertFalse(z['number_restricted'])
        wn = w / (4 / 3 * np.pi * R ** 3)
        wn /= np.trapezoid(wn, R)
        mean_n = np.trapezoid(wn * R, R)
        sd_n = np.sqrt(np.trapezoid(wn * (R - mean_n) ** 2, R))
        self.assertAlmostEqual(z['mean_N'], mean_n, delta=0.15)
        # Der Ausläufer kleiner Teilchen streut kaum (∝ R⁶) und wird geglättet: Breite ±15 %
        self.assertAlmostEqual(z['std_N'], sd_n, delta=0.15 * sd_n)
        self.assertAlmostEqual(z['mean_V'], 8.0, delta=0.15)
        self.assertIn('D_V', z['derived'])
        V = 4 / 3 * np.pi * R ** 3
        rg = np.sqrt(0.6 * np.trapezoid(w * V * R ** 2, R) / np.trapezoid(w * V, R))
        self.assertAlmostEqual(sol.rg, rg, delta=0.01 * rg)

    def test_cylinders_and_lamellae(self):
        Rr = np.linspace(0.05, 12, 2000)
        w = np.exp(-0.5 * ((Rr - 5.0) / 0.8) ** 2)
        w /= np.trapezoid(w, Rr)
        x = np.outer(Q, Rr)
        Ic = (np.pi / Q) * np.trapezoid(w * np.pi * Rr ** 2 * (2 * j1(x) / x) ** 2, Rr, axis=1)
        I, s = noisy(Ic, 0.02, 5)
        z = size_statistics(run_ift(Q, I, s, IFTSettings(dmax=9.0, n_splines=20,
                                                          kind='size_cylinder')))
        self.assertAlmostEqual(z['mean_V'], 5.0, delta=0.1)
        self.assertAlmostEqual(z['std_V'], 0.8, delta=0.1)
        It = (2 * np.pi / Q ** 2) * np.trapezoid(w * Rr * np.sinc(x / 2 / np.pi) ** 2, Rr, axis=1)
        I, s = noisy(It, 0.02, 6)
        z = size_statistics(run_ift(Q, I, s, IFTSettings(dmax=9.0, n_splines=20,
                                                          kind='size_lamella')))
        self.assertAlmostEqual(z['mean_V'], 5.0, delta=0.1)
        self.assertAlmostEqual(z['std_V'], 0.8, delta=0.1)


class TestIntegration(unittest.TestCase):
    def test_likelihood_matches_scan(self):
        """DREAM-Likelihood = Evidenz des IFT-Scans auch für andere Kerne (inkl. Dmax-Tabelle)."""
        R = 5.0
        I, s = noisy(cylinder_cross_section(Q, R), 0.02, 7)
        st = IFTSettings(dmax=10.0, n_splines=18, kind='cross_section')
        dec = IFTDecomposition(Q, I, s, st)
        g = dec.scan([1e-3])
        ev = MarginalLikelihood(Q, I, s, st, 'none', {}, ParameterSpace([LOG_LAMBDA], [-10], [4]),
                                1e-3)
        self.assertAlmostEqual(ev.log_posterior([[-3.0]])[0], g['log_evidence'][0],
                               delta=1e-6 * abs(g['log_evidence'][0]))
        ev2 = MarginalLikelihood(Q, I, s, st, 'none', {},
                                 ParameterSpace([LOG_LAMBDA, 'dmax'], [-10, 8.0], [4, 12.0]), 1e-3)
        self.assertAlmostEqual(ev2.log_posterior([[-3.0, 10.0]])[0], g['log_evidence'][0],
                               delta=1e-5 * abs(g['log_evidence'][0]))

    def test_pipeline_export(self):
        I0, _R, _w = polydisperse_spheres(Q, 8.0, 1.5)
        I, s = noisy(I0, 0.02, 8)
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / 'probe.dat'
            src.write_text('x')
            a = run_ift_analysis(Q, I, s, IFTSettings(dmax=16.0, n_splines=25,
                                                      kind='size_sphere'), source_file=src)
            codes = {f.code: f.level for f in a.flags}
            self.assertEqual(codes['size_distribution'], 'ok')
            self.assertIn('dmax_qmin', codes)
            w = export_ift_results(a, write_w3c=False)
            self.assertEqual(w['pr'].name, 'probe-sizeS_GIFT_pr.dat')
            text = w['pr'].read_text(encoding='utf-8')
            self.assertIn('# Verteilung: Modus', text)
            data = np.loadtxt(w['pr'])
            self.assertEqual(data.shape[1], 5)
            summary = a.record.to_dict()['processing']['activities']
            ift = next(x for x in summary if x['type'] == 'ift')
            self.assertEqual(ift['parameters']['kind'], 'size_sphere')

    def test_size_flag_for_wrong_shape(self):
        """Kern-Schale-Kugel mit Kontrastwechsel als homogene Kugeln → negatives D_V, Flag."""
        R1, R2 = 6.0, 9.0
        V1, V2 = 4 / 3 * np.pi * R1 ** 3, 4 / 3 * np.pi * R2 ** 3
        amp = -1.0 * V1 * sphere_amp(Q * R1) + 1.0 * (V2 * sphere_amp(Q * R2) - V1 * sphere_amp(Q * R1))
        I, s = noisy(amp ** 2, 0.02, 9)
        a = run_ift_analysis(Q, I, s, IFTSettings(dmax=12.0, n_splines=25, kind='size_sphere'))
        flag = next(f for f in a.flags if f.code == 'size_distribution')
        self.assertEqual(flag.level, 'warning')


if __name__ == '__main__':
    unittest.main()
