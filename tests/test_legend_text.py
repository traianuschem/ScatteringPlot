"""Tests für Legenden-Texte (v8.1.1): \\ce{…}-Formeln, Schutz von $…$ vor
Markdown-Ersetzung und verlustfreies Umsortieren aus dem Legenden-Editor."""

import unittest
from types import SimpleNamespace

import matplotlib
matplotlib.use('Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

from utils.mathtext_formatter import convert_ce, preprocess_mathtext, format_legend_text, is_in_math


def renders(text):
    fig = Figure()
    FigureCanvasAgg(fig)
    fig.text(0, 0, text)
    fig.canvas.draw()
    return True


class TestChemicalFormulas(unittest.TestCase):

    def test_subscripts_and_charges(self):
        self.assertEqual(convert_ce('H2SO4'), r'\mathrm{H_{2}SO_{4}}')
        self.assertEqual(convert_ce('SO4^2-'), r'\mathrm{SO_{4}^{2-}}')
        self.assertEqual(convert_ce('Fe3+'), r'\mathrm{Fe^{3+}}')
        self.assertEqual(convert_ce('Na+'), r'\mathrm{Na^{+}}')
        self.assertEqual(convert_ce('[Fe(CN)6]^3-'), r'\mathrm{[Fe(CN)_{6}]^{3-}}')

    def test_coefficients_operators_arrows(self):
        self.assertEqual(convert_ce('2H2 + O2 -> 2H2O'),
                         r'\mathrm{2H_{2}\ +\ O_{2}\ \rightarrow\ 2H_{2}O}')
        self.assertIn(r'\rightleftharpoons', convert_ce('A <=> B'))
        self.assertEqual(convert_ce('CuSO4*5H2O'), r'\mathrm{CuSO_{4}{\cdot}5H_{2}O}')

    def test_ce_in_text_and_math(self):
        self.assertEqual(preprocess_mathtext(r'Probe \ce{H2O}'), r'Probe $\mathrm{H_{2}O}$')
        self.assertEqual(preprocess_mathtext(r'$x = \ce{H2O}$'), r'$x = \mathrm{H_{2}O}$')

    def test_all_examples_render(self):
        for text in [r'\ce{Na+ + Cl- <=> NaCl(s)}', r'**Probe** \ce{Fe3O4}@\ce{SiO2}',
                     r'\ce{\alpha-Fe2O3}', r'\ce{CuSO4*5H2O}']:
            self.assertTrue(renders(format_legend_text(text, bold=True)))

    def test_plain_names_unchanged(self):
        self.assertEqual(preprocess_mathtext('sample_01'), 'sample_01')


class TestMarkdownProtection(unittest.TestCase):

    def test_star_inside_math_untouched(self):
        self.assertEqual(preprocess_mathtext('$a*b*c$ und *kursiv*'),
                         r'$a*b*c$ und $\mathit{kursiv}$')

    def test_bold_around_math(self):
        self.assertEqual(preprocess_mathtext('**T $q^2$ T**'), r'$\mathbf{T }$$q^2$$\mathbf{ T}$')

    def test_is_in_math(self):
        self.assertTrue(is_in_math('$x = ', 3))
        self.assertFalse(is_in_math('$x$ y', 4))


class TestApplyLegendOrder(unittest.TestCase):

    def test_reorder_keeps_everything(self):
        import scatter_plot
        a, b, c, u1, u2 = (SimpleNamespace(name=n) for n in 'a b c u1 u2'.split())
        g1 = SimpleNamespace(name='G1', datasets=[a, b])
        g2 = SimpleNamespace(name='G2', datasets=[])          # leer – darf nicht verschwinden
        g3 = SimpleNamespace(name='G3', datasets=[c])
        app = SimpleNamespace(groups=[g1, g2, g3], unassigned_datasets=[u1, u2])
        # Editor liefert nur einen Teil (z. B. G2 fehlt) – Rest bleibt erhalten
        scatter_plot.ScatterPlotApp.apply_legend_order(
            app, [g3, g1], {id(g1): [b, a]}, [u2])
        self.assertEqual([g.name for g in app.groups], ['G3', 'G1', 'G2'])
        self.assertEqual([d.name for d in g1.datasets], ['b', 'a'])
        self.assertEqual([d.name for d in app.unassigned_datasets], ['u2', 'u1'])


if __name__ == '__main__':
    unittest.main()
