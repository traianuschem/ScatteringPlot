"""Tests für analysis.asaxs (Verhältnisse, Korrelation, Term-Zuordnung)."""

import unittest
from types import SimpleNamespace

import numpy as np

from analysis.asaxs import (
    Curve, ratio, correlation, cauchy_schwarz, compute, interpolate_to, pair_asaxs_terms, base_name,
    QUANTITY_ICROSS_IN, QUANTITY_CORRELATION, QUANTITY_CAUCHY_SCHWARZ,
    TERM_NORMAL, TERM_ANOMALOUS, TERM_CROSS,
)


class TestRatio(unittest.TestCase):

    def setUp(self):
        self.q = np.logspace(-1, 0, 50)
        self.i_n = 100.0 * self.q ** -2
        self.i_a = 5.0 * self.q ** -2

    def test_same_grid_value_and_error(self):
        num = Curve(self.q, self.i_a, 0.1 * self.i_a)     # 10 % rel. Fehler
        den = Curve(self.q, self.i_n, 0.05 * self.i_n)    # 5 %
        r = ratio(num, den)
        np.testing.assert_allclose(r.y, 0.05)
        np.testing.assert_allclose(r.err, 0.05 * np.hypot(0.1, 0.05))
        self.assertEqual(r.n_interpolated, 0)

    def test_interpolation_on_different_grid(self):
        # Potenzgesetz ist in log-log linear → Interpolation in log(q) ist nicht exakt
        # für I, aber für einen konstanten Zähler exakt.
        q_num = np.logspace(-1.2, 0.2, 37)
        num = Curve(q_num, np.full_like(q_num, 3.0), np.full_like(q_num, 0.3))
        den = Curve(self.q, np.full_like(self.q, 2.0), None)
        r = ratio(num, den)
        np.testing.assert_allclose(r.y, 1.5)
        np.testing.assert_allclose(r.err, 0.15)
        self.assertEqual(len(r.x), len(self.q))
        self.assertGreater(r.n_interpolated, 0)

    def test_overlap_only_and_nonpositive_denominator(self):
        q_num = np.logspace(-0.5, 0, 20)   # deckt nur den oberen Teil ab
        num = Curve(q_num, np.ones_like(q_num))
        den_y = np.ones_like(self.q)
        den_y[-1] = 0.0
        r = ratio(num, Curve(self.q, den_y))
        self.assertTrue(np.all(r.x >= q_num[0] - 1e-12))
        self.assertNotIn(self.q[-1], r.x)
        self.assertIsNone(r.err)

    def test_q_range(self):
        r = ratio(Curve(self.q, self.i_a), Curve(self.q, self.i_n), q_range=(0.2, 0.5))
        self.assertTrue(np.all((r.x >= 0.2) & (r.x <= 0.5)))

    def test_zero_numerator_error(self):
        num = Curve(self.q, np.zeros_like(self.q), np.full_like(self.q, 1.0))
        den = Curve(self.q, np.full_like(self.q, 4.0))
        r = ratio(num, den)
        np.testing.assert_allclose(r.err, 0.25)


class TestCorrelation(unittest.TestCase):

    def test_perfect_correlation(self):
        q = np.logspace(-1, 0, 30)
        i_n, i_a = 50 * q ** -3, 2 * q ** -3
        i_x = np.sqrt(i_n * i_a)
        c = correlation(Curve(q, i_n), Curve(q, i_a), Curve(q, i_x))
        np.testing.assert_allclose(c.y, 1.0)
        self.assertEqual(c.info['fraction_above_one'], 0.0)

    def test_error_propagation(self):
        q = np.array([0.1, 0.2])
        c = correlation(Curve(q, [4.0, 4.0], [0.4, 0.4]),     # 10 % → 5 % in √
                        Curve(q, [1.0, 1.0], [0.1, 0.1]),     # 10 % → 5 %
                        Curve(q, [-1.0, 1.0], [0.1, 0.1]))    # 10 %
        np.testing.assert_allclose(c.y, [-0.5, 0.5])
        np.testing.assert_allclose(c.err, 0.5 * np.sqrt(0.1 ** 2 + 0.05 ** 2 + 0.05 ** 2))

    def test_compute_missing_term(self):
        q = np.array([0.1])
        with self.assertRaises(KeyError):
            compute(QUANTITY_CORRELATION, {TERM_NORMAL: Curve(q, [1.0])})
        r = compute(QUANTITY_ICROSS_IN, {TERM_NORMAL: Curve(q, [2.0]), TERM_CROSS: Curve(q, [-1.0])})
        np.testing.assert_allclose(r.y, [-0.5])


class TestCauchySchwarz(unittest.TestCase):

    def setUp(self):
        self.q = np.array([0.1, 0.2, 0.3, 0.4])
        self.i_n = np.array([4.0, 4.0, 4.0, 4.0])
        self.i_a = np.array([1.0, 1.0, 1.0, 1.0])      # √(I_N·I_A) = 2

    def test_values_and_no_violation(self):
        i_x = np.array([2.0, -1.0, 0.5, -2.0])
        r = cauchy_schwarz(Curve(self.q, self.i_n), Curve(self.q, self.i_a), Curve(self.q, i_x))
        np.testing.assert_allclose(r.y, [1.0, 2.0, 4.0, 1.0])     # Vorzeichen von I_cross egal
        self.assertEqual(r.info['fraction_below_one'], 0.0)

    def test_violation_fraction(self):
        i_x = np.array([3.0, 1.0, -4.0, 1.0])
        r = cauchy_schwarz(Curve(self.q, self.i_n), Curve(self.q, self.i_a), Curve(self.q, i_x))
        np.testing.assert_allclose(r.y, [2 / 3, 2.0, 0.5, 2.0])
        self.assertEqual(r.info['fraction_below_one'], 0.5)

    def test_error_propagation(self):
        r = cauchy_schwarz(Curve(self.q[:1], [4.0], [0.4]),      # 10 % → 5 % in √
                           Curve(self.q[:1], [1.0], [0.1]),      # 10 % → 5 %
                           Curve(self.q[:1], [-1.0], [0.1]))     # 10 %
        np.testing.assert_allclose(r.y, [2.0])
        np.testing.assert_allclose(r.err, 2.0 * np.sqrt(0.1 ** 2 + 0.05 ** 2 + 0.05 ** 2))

    def test_zero_cross_and_nonpositive_terms_dropped(self):
        i_n = np.array([4.0, 4.0, -1.0, 4.0])
        i_a = np.array([1.0, 1.0, 1.0, 0.0])
        i_x = np.array([0.0, 1.0, 1.0, 1.0])
        r = cauchy_schwarz(Curve(self.q, i_n), Curve(self.q, i_a), Curve(self.q, i_x))
        np.testing.assert_allclose(r.x, [0.2])

    def test_compute_dispatch_and_missing_term(self):
        terms = {TERM_NORMAL: Curve(self.q, self.i_n), TERM_ANOMALOUS: Curve(self.q, self.i_a),
                 TERM_CROSS: Curve(self.q, np.ones(4))}
        r = compute(QUANTITY_CAUCHY_SCHWARZ, terms, q_range=(0.15, 0.35))
        self.assertEqual(r.quantity, QUANTITY_CAUCHY_SCHWARZ)
        np.testing.assert_allclose(r.x, [0.2, 0.3])
        del terms[TERM_CROSS]
        with self.assertRaises(KeyError):
            compute(QUANTITY_CAUCHY_SCHWARZ, terms)


class TestPairing(unittest.TestCase):

    def test_base_name(self):
        self.assertEqual(base_name('probeA_IA'), 'probeA')
        self.assertEqual(base_name('probeA_Icross_merged'), 'probeA_merged')
        self.assertEqual(base_name('probeA_in'), 'probeA')
        self.assertEqual(base_name('protein'), 'protein')

    def test_pairing(self):
        ds = [SimpleNamespace(name=n, data_term=t) for n, t in [
            ('a_IN', 'normal'), ('a_IA', 'anomalous'), ('a_Icross', 'cross'),
            ('b_IN', 'normal'), ('b_IA', 'anomalous'), ('ref', '')]]
        pairs = pair_asaxs_terms(ds)
        self.assertEqual(list(pairs), ['a', 'b'])
        self.assertEqual(set(pairs['a']), {TERM_NORMAL, TERM_ANOMALOUS, TERM_CROSS})
        self.assertNotIn(TERM_CROSS, pairs['b'])

    def test_interpolate_outside_is_nan(self):
        y, err, mask = interpolate_to(Curve([1.0, 2.0], [1.0, 2.0]), np.array([0.5, 1.5, 3.0]))
        self.assertTrue(np.isnan(y[0]) and np.isnan(y[2]))
        self.assertEqual(mask.tolist(), [False, True, False])
        self.assertIsNone(err)


if __name__ == '__main__':
    unittest.main()
