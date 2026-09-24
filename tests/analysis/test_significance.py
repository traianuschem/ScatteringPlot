"""Tests für analysis.significance (rolling median, σ-basierte q-Bereichsauswahl)."""

import unittest

import numpy as np

from analysis.significance import (
    significance, rolling_median, sigma_cutoff_index, select_q_range,
    QRANGE_FULL, QRANGE_SIGMA, QRANGE_MANUAL,
)


def _reference_rolling_median(arr, window):
    """Ursprüngliche Schleifen-Implementierung aus scatter_plot.py (v7.6)."""
    n = len(arr)
    half = window // 2
    out = np.empty(n)
    for i in range(n):
        lo, hi = max(0, i - half), min(n, i + half + 1)
        out[i] = np.nanmedian(arr[lo:hi])
    return out


class TestRollingMedian(unittest.TestCase):
    def test_matches_original_implementation(self):
        rng = np.random.default_rng(0)
        arr = rng.normal(size=200)
        arr[[3, 50, 51, 199]] = np.nan
        for window in (3, 5, 9, 21):
            np.testing.assert_allclose(rolling_median(arr, window),
                                       _reference_rolling_median(arr, window))

    def test_short_and_empty(self):
        self.assertEqual(len(rolling_median(np.array([]), 9)), 0)
        np.testing.assert_allclose(rolling_median(np.array([1.0, 3.0]), 9), [2.0, 2.0])


class TestSignificance(unittest.TestCase):
    def test_nonfinite_becomes_nan(self):
        sig = significance([1.0, -2.0, 3.0], [0.5, 1.0, 0.0])
        np.testing.assert_allclose(sig[:2], [2.0, 2.0])
        self.assertTrue(np.isnan(sig[2]))


class TestCutoff(unittest.TestCase):
    def test_single_spike_does_not_extend_range(self):
        s = np.array([10, 9, 8, 5, 1, 1, 1, 1, 6, 1, 1, 1], dtype=float)
        self.assertEqual(sigma_cutoff_index(s, 2.0, 3), 3)

    def test_never_below(self):
        self.assertEqual(sigma_cutoff_index(np.full(10, 5.0), 2.0, 3), 9)

    def test_short_trailing_run_is_excluded(self):
        s = np.array([5, 5, 5, 5, 1, 1], dtype=float)
        self.assertEqual(sigma_cutoff_index(s, 2.0, 4), 3)

    def test_first_point_below(self):
        self.assertEqual(sigma_cutoff_index(np.full(10, 0.5), 2.0, 3), -1)


class TestSelectQRange(unittest.TestCase):
    def setUp(self):
        self.q = np.linspace(0.1, 10.0, 100)
        self.I = 1e3 * np.exp(-self.q)
        self.err = np.full_like(self.q, 1.0)   # Signifikanz = I, fällt monoton

    def test_full(self):
        sel = select_q_range(self.q, self.I, self.err, mode=QRANGE_FULL)
        self.assertEqual(sel.n_selected, 100)
        self.assertEqual(sel.n_excluded, 0)

    def test_sigma_levels_are_ordered(self):
        qmax = [select_q_range(self.q, self.I, self.err, mode=QRANGE_SIGMA, n_sigma=n).q_max
                for n in (3.0, 2.0, 1.0)]
        self.assertTrue(qmax[0] < qmax[1] < qmax[2])
        # Analytisch: I = n ⇔ q = ln(1000/n)
        self.assertAlmostEqual(qmax[1], np.log(1000 / 2.0), delta=0.1)

    def test_sigma_requires_errors(self):
        with self.assertRaises(ValueError):
            select_q_range(self.q, self.I, None, mode=QRANGE_SIGMA)

    def test_sigma_with_manual_qmin(self):
        sel = select_q_range(self.q, self.I, self.err, mode=QRANGE_SIGMA, q_min=0.5)
        self.assertEqual(sel.q_min, 0.5)
        self.assertTrue(sel.q_min_manual)

    def test_manual(self):
        sel = select_q_range(self.q, self.I, self.err, mode=QRANGE_MANUAL, q_min=1.0, q_max=2.0)
        m = sel.mask(self.q)
        self.assertTrue(np.all(self.q[m] >= 1.0) and np.all(self.q[m] <= 2.0))
        self.assertEqual(sel.to_dict()['n_excluded'], 100 - sel.n_selected)

    def test_empty_range_raises(self):
        with self.assertRaises(ValueError):
            select_q_range(self.q, self.I, self.err, mode=QRANGE_MANUAL, q_min=3.0, q_max=2.0)


if __name__ == '__main__':
    unittest.main()
