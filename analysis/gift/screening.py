"""
Latin-Hypercube-Screening der Posterior-Landschaft (Schritt 1 der DREAM-Analyse).

Eine LHS-Stichprobe über den Kasten der Priorverteilung wird (parallel) ausgewertet. Sie
liefert das Startarchiv Z und die Startzustände für DREAM(ZS) sowie einen groben Überblick
über die log-Posterior-Landschaft (z. B. Nebenmaxima bei geladenen Systemen [F00]).
"""

from dataclasses import dataclass

import numpy as np

from .dream import latin_hypercube
from .likelihood import MarginalLikelihood, evaluate_log_posterior


@dataclass
class ScreeningResult:
    samples: np.ndarray          # (n, d) physikalische Koordinaten
    log_p: np.ndarray            # (n,)
    seed_entropy: list           # SeedSequence-Entropie des LHS-Generators

    @property
    def n_finite(self):
        return int(np.count_nonzero(np.isfinite(self.log_p)))

    def best(self, k=1):
        order = np.argsort(np.where(np.isfinite(self.log_p), -self.log_p, np.inf),
                           kind='stable')
        return order[:k]

    def summary(self, names):
        i = int(self.best(1)[0])
        return {'n': int(len(self.log_p)), 'n_finite': self.n_finite,
                'best': dict(zip(names, map(float, self.samples[i]))),
                'best_log_posterior': float(self.log_p[i])}


def default_screen_size(dim):
    return int(np.clip(100 * dim, 200, 1000))


def screen(ev: MarginalLikelihood, n: int, seed: int, n_workers: int, chunk: int = 16,
           ) -> ScreeningResult:
    entropy = [int(seed), 1]
    rng = np.random.default_rng(entropy)
    u = latin_hypercube(int(n), ev.space.dim, rng)
    theta = ev.space.from_unit(u)
    log_p = evaluate_log_posterior(ev, theta, n_workers, chunk)
    return ScreeningResult(samples=theta, log_p=log_p, seed_entropy=entropy)
