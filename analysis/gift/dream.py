"""
DREAM(ZS) — Differential Evolution Adaptive Metropolis mit Archiv vergangener Zustände
(ter Braak & Vrugt 2008; Vrugt 2016, Environ. Model. Softw. 75, 273).

Allgemeiner MCMC-Sampler für eine Zieldichte log p(θ) auf einem Kasten [lower, upper]
(gleichverteilte Priorverteilung; eine zusätzliche Priordichte steckt in log p). Intern
wird in Einheitskoordinaten u ∈ [0, 1]^d gerechnet.

Vorschläge (je Kette und Generation):
- **Parallele Richtung** (Wahrscheinlichkeit 1 − p_snooker): Differenz von δ Paaren aus
  dem Archiv Z, δ ∈ {1, …, δ_max}; nur die Dimensionen mit U < CR werden verändert
  (Randomized Subspace Sampling), Sprungweite γ = 2.38/√(2δd*), mit Wahrscheinlichkeit
  p_unit_gamma γ = 1 (Sprünge zwischen Modi); dazu (1+e) mit e ~ U(−b, b) und ε ~ N(0, b*).
- **Snooker-Update** (p_snooker): Sprung entlang x − z (z aus Z) um die Projektion der
  Differenz zweier weiterer Archivpunkte, γ ~ U(1.2, 2.2); Metropolis-Korrektur
  (‖x' − z‖/‖x − z‖)^{d−1}.
- Randbehandlung: Faltung (periodisch) in den Kasten; mit der Gleichverteilung verträglich.

Adaption in der Einlaufphase: Die Wahrscheinlichkeiten der CR-Werte folgen der normierten
Sprungdistanz; Ausreißer-Ketten (IQR-Test auf die mittlere log-Dichte der letzten Hälfte)
werden auf den Zustand der besten Kette gesetzt. Alle 10 Generationen werden die aktuellen
Zustände an Z angehängt.

Zwei Phasen:
1. **Einlauf** (Adaption von CR, Ausreißer-Ketten): endet, sobald R̂ < Ziel über die
   zweite Hälfte der bisherigen Ketten (frühestens nach `min_burn_in` Generationen).
   Dann werden die Startpunkte aus der Priorverteilung aus dem Archiv entfernt; es
   enthält danach nur noch Kettenzustände (sonst erzeugen die weit gestreuten
   Priorpunkte noch lange zu große, fast immer verworfene Sprünge).
2. **Sampling** ohne Adaption: Die Posterior-Stichprobe sind alle Zustände nach dem
   Einlauf. Konvergiert ist der Lauf, wenn R̂ < Ziel über diese Stichprobe und
   mindestens `min_samples` Zustände vorliegen.
Ein vorzeitiges „R̂ < 1.1“ in einer noch nicht eingeschwungenen Ketten-Hälfte (etwa mit
einer einzelnen Kette im Ausläufer) wird dadurch in der Sampling-Phase erneut geprüft.

Reproduzierbarkeit: Alle Zufallszahlen stammen aus einem einzigen Generator im
aufrufenden Prozess; die Zielfunktion wird je Generation für alle Ketten als Stapel
ausgewertet (z. B. im Prozess-Pool). Das Ergebnis hängt damit nicht davon ab, wie die
Auswertung verteilt wird.
"""

from dataclasses import dataclass, field, asdict
from typing import Callable, List, Optional

import numpy as np


class DreamCancelled(Exception):
    """Abbruch durch den Benutzer."""


@dataclass
class DreamSettings:
    n_chains: int = 8
    max_evals: int = 40000
    seed: int = 12345
    r_hat_target: float = 1.1
    min_burn_in: int = 100               # Mindestlänge der Einlaufphase (Generationen)
    min_samples: int = 5000              # Mindestzahl Posterior-Zustände nach dem Einlauf
    check_every: int = 20                # R̂-Prüfung alle n Generationen
    archive_every: int = 10              # Zustände alle n Generationen an Z anhängen
    delta_max: int = 3
    n_cr: int = 3
    p_snooker: float = 0.1
    p_unit_gamma: float = 0.2
    b: float = 0.05
    b_star: float = 1e-6
    outlier_iqr: float = 2.0

    def to_dict(self):
        return asdict(self)


@dataclass
class DreamResult:
    chains: np.ndarray                   # (G, C, d) physikalische Koordinaten
    log_p: np.ndarray                    # (G, C)
    accepted: np.ndarray                 # (G, C) bool
    r_hat: np.ndarray                    # (d,) am Ende
    r_hat_history: List[tuple]           # (Generation, R̂ (d,))
    converged: bool
    n_evals: int
    n_generations: int
    burn_in: int                         # Einlauf: Generationen 0 … burn_in − 1 verworfen
    burn_in_completed: bool
    p_cr: np.ndarray
    outliers_reset: int
    archive_size: int
    settings: DreamSettings = field(default_factory=DreamSettings)

    def posterior(self):
        """Posterior-Stichprobe (Zustände nach dem Einlauf), (n, d), und log-Dichten (n,)."""
        x = self.chains[self.burn_in:]
        lp = self.log_p[self.burn_in:]
        return x.reshape(-1, x.shape[-1]), lp.reshape(-1)

    @property
    def acceptance_rate(self):
        acc = self.accepted[self.burn_in:]
        return float(np.mean(acc)) if acc.size else float('nan')


def gelman_rubin(chains):
    """R̂ je Parameter für chains (n, C, d) (klassisch, Gelman & Rubin 1992)."""
    x = np.asarray(chains, dtype=float)
    n = x.shape[0]
    if n < 4:
        return np.full(x.shape[-1], np.inf)
    means = x.mean(axis=0)                                   # (C, d)
    W = x.var(axis=0, ddof=1).mean(axis=0)                  # (d,)
    B_n = means.var(axis=0, ddof=1)                          # B/n
    var_plus = (n - 1) / n * W + B_n
    with np.errstate(divide='ignore', invalid='ignore'):
        r = np.sqrt(var_plus / W)
    return np.where(W > 0, r, np.where(B_n > 0, np.inf, 1.0))


def latin_hypercube(n, d, rng):
    """Latin-Hypercube-Stichprobe in [0, 1]^d."""
    u = (rng.random((n, d)) + np.arange(n)[:, None]) / n
    for j in range(d):
        u[:, j] = u[rng.permutation(n), j]
    return u


def sample(log_density: Callable, lower, upper, settings: DreamSettings,
           z_init, x_init, lp_init=None, progress: Optional[Callable] = None) -> DreamResult:
    """DREAM(ZS).

    Args:
        log_density: θ (K, d) → log p (K,), physikalische Koordinaten (Stapel)
        lower, upper: Kasten der Priorverteilung
        z_init: Startarchiv (m, d), z. B. eine LHS-Stichprobe der Priorverteilung
        x_init: Startzustände der Ketten (C, d)
        lp_init: log p der Startzustände (sonst werden sie ausgewertet)
        progress: progress(n_evals, generation, max R̂, Akzeptanzrate) → False bricht ab
    """
    st = settings
    lower = np.asarray(lower, dtype=float)
    upper = np.asarray(upper, dtype=float)
    span = upper - lower
    d = len(lower)
    C = int(st.n_chains)
    rng = np.random.default_rng(int(st.seed))

    def to_phys(u):
        return lower + u * span

    Z = list((np.asarray(z_init, dtype=float) - lower) / span)
    X = (np.asarray(x_init, dtype=float) - lower) / span
    if X.shape != (C, d):
        raise ValueError(f"x_init muss die Form ({C}, {d}) haben")
    if len(Z) < 2 * st.delta_max + 1:
        raise ValueError("Archiv zu klein")
    n_evals = 0
    if lp_init is None:
        lp = np.asarray(log_density(to_phys(X)), dtype=float)
        n_evals += C
    else:
        lp = np.asarray(lp_init, dtype=float).copy()

    max_gen = max(1, (int(st.max_evals) - n_evals) // C)
    chains = np.empty((max_gen + 1, C, d))
    log_p = np.empty((max_gen + 1, C))
    accepted = np.zeros((max_gen + 1, C), dtype=bool)
    chains[0], log_p[0] = to_phys(X), lp

    p_cr = np.full(st.n_cr, 1.0 / st.n_cr)
    cr_values = (np.arange(st.n_cr) + 1.0) / st.n_cr
    jump = np.zeros(st.n_cr)
    count = np.zeros(st.n_cr)
    burn_in_phase = True
    burn_in = 0
    n_prior = len(Z)
    r_hat = np.full(d, np.inf)
    r_hat_history = []
    outliers = 0
    converged = False
    g = 0

    for g in range(1, max_gen + 1):
        Zarr = np.asarray(Z)
        nz = len(Zarr)
        Xp = X.copy()
        log_corr = np.zeros(C)
        cr_idx = np.full(C, -1)
        for i in range(C):
            if rng.random() < st.p_snooker:
                a, r1, r2 = rng.choice(nz, 3, replace=False)
                v = X[i] - Zarr[a]
                vv = float(v @ v)
                if vv <= 0:
                    continue
                proj = ((Zarr[r1] - Zarr[r2]) @ v) / vv * v
                Xp[i] = X[i] + rng.uniform(1.2, 2.2) * proj
                Xp[i] = np.mod(Xp[i], 1.0)
                num = np.linalg.norm(Xp[i] - Zarr[a])
                den = np.sqrt(vv)
                log_corr[i] = (d - 1) * (np.log(max(num, 1e-300)) - np.log(den))
            else:
                delta = int(rng.integers(1, st.delta_max + 1))
                pick = rng.choice(nz, 2 * delta, replace=False)
                m = int(rng.choice(st.n_cr, p=p_cr))
                cr_idx[i] = m
                A = rng.random(d) < cr_values[m]
                if not A.any():
                    A[rng.integers(d)] = True
                d_star = int(A.sum())
                gamma = 2.38 / np.sqrt(2.0 * delta * d_star)
                if rng.random() < st.p_unit_gamma:
                    gamma = 1.0
                diff = Zarr[pick[:delta]].sum(axis=0) - Zarr[pick[delta:]].sum(axis=0)
                e = rng.uniform(-st.b, st.b, d_star)
                eps = rng.normal(0.0, st.b_star, d_star)
                Xp[i, A] = X[i, A] + (1.0 + e) * gamma * diff[A] + eps
                Xp[i] = np.mod(Xp[i], 1.0)

        lp_new = np.asarray(log_density(to_phys(Xp)), dtype=float)
        n_evals += C
        with np.errstate(invalid='ignore'):
            log_alpha = lp_new - lp + log_corr
        acc = np.log(rng.random(C)) < np.where(np.isnan(log_alpha), -np.inf, log_alpha)
        if burn_in_phase:
            std = np.std(X, axis=0)
            std = np.where(std > 0, std, 1.0)
            for i in range(C):
                if cr_idx[i] >= 0:
                    count[cr_idx[i]] += 1
                    if acc[i]:
                        jump[cr_idx[i]] += float(np.sum(((Xp[i] - X[i]) / std) ** 2))
        X[acc] = Xp[acc]
        lp[acc] = lp_new[acc]
        chains[g], log_p[g], accepted[g] = to_phys(X), lp, acc

        if g % st.archive_every == 0:
            Z.extend(X.copy())

        if burn_in_phase and g % 10 == 0:
            if np.all(count > 0) and jump.sum() > 0:
                rate = jump / count
                p_cr = np.maximum(rate / rate.sum(), 0.02)
                p_cr = p_cr / p_cr.sum()
            # Ausreißer-Ketten (IQR) auf den Zustand der besten Kette setzen
            half = log_p[g // 2 + 1:g + 1]
            mean_lp = np.where(np.isfinite(half), half, -1e300).mean(axis=0)
            q1, q3 = np.percentile(mean_lp, [25, 75])
            bad = mean_lp < q1 - st.outlier_iqr * (q3 - q1)
            if bad.any() and not bad.all():
                best = int(np.argmax(lp))
                X[bad] = X[best]
                lp[bad] = lp[best]
                outliers += int(bad.sum())

        if g % st.check_every == 0 and g >= 20:
            if burn_in_phase:
                r_hat = gelman_rubin(chains[g // 2 + 1:g + 1])
                if g >= st.min_burn_in and np.all(r_hat < st.r_hat_target):
                    burn_in_phase = False
                    burn_in = g + 1
                    # Priorpunkte aus dem Archiv entfernen (nur Kettenzustände behalten)
                    if len(Z) - n_prior >= 2 * st.delta_max + 1:
                        del Z[:n_prior]
                        n_prior = 0
            else:
                r_hat = gelman_rubin(chains[burn_in:g + 1])
                n_post = (g + 1 - burn_in) * C
                if n_post >= st.min_samples and np.all(r_hat < st.r_hat_target):
                    converged = True
            r_hat_history.append((g, r_hat.copy()))
        if progress is not None:
            start = min(burn_in if not burn_in_phase else g // 2 + 1, g)
            rate = float(np.mean(accepted[max(1, start):g + 1]))
            if progress(n_evals, g, float(np.max(r_hat)), rate) is False:
                raise DreamCancelled()
        if converged:
            break

    n_gen = g
    completed = not burn_in_phase
    if not completed:
        burn_in = n_gen // 2 + 1          # Budget im Einlauf erschöpft: zweite Hälfte
    if not converged:
        r_hat = gelman_rubin(chains[burn_in:n_gen + 1])
        r_hat_history.append((n_gen, r_hat.copy()))
    return DreamResult(
        chains=chains[:n_gen + 1], log_p=log_p[:n_gen + 1], accepted=accepted[:n_gen + 1],
        r_hat=r_hat, r_hat_history=r_hat_history, converged=converged, n_evals=n_evals,
        n_generations=n_gen, burn_in=burn_in, burn_in_completed=completed, p_cr=p_cr,
        outliers_reset=outliers,
        archive_size=len(Z), settings=st)
