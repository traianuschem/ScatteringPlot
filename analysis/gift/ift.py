"""
Indirekte Fourier-Transformation nach Glatter (1977).

    I(q) ≈ Σ c_ν ψ_ν(q)  [+ Untergrund]
    (B + λK) c = b,   B = AᵀWA,  b = AᵀW·I,  W = diag(1/σ²)          [G77 Gl. 12–15]

λ wird über die Wendepunkt-Methode [G77, Fig. 2] bestimmt: log N_c(λ) zeigt einen
Wendepunkt (minimale |Steigung|) im Bereich kurz vor dem starken Anstieg der mittleren
Abweichung MD(λ). λ wird intern relativ angegeben (λ_rel), damit der Scanbereich
unabhängig von Intensitätsskala und Fehlergröße ist: λ = λ_rel · tr(B)/tr(K).
"""

from dataclasses import dataclass, field, asdict
from typing import Optional

import numpy as np

from .splines import SplineBasis
from .transform import cached_design_matrix, FOUR_PI
from .smearing import IdentitySmearing

K_GLATTER = 'glatter'      # Σ (c_{ν+1} − c_ν)²            [G77 Gl. 14]
K_DIRICHLET = 'dirichlet'  # wie oben, zusätzlich c_0 = c_{N+1} = 0 (positiv definit)
K_CURVATURE = 'curvature'  # Σ (c_{ν+1} − 2c_ν + c_{ν−1})², c_0 = c_{N+1} = 0

LAMBDA_AUTO = 'auto'


@dataclass
class IFTSettings:
    """Einstellungen einer IFT-Rechnung (vollständig in der Provenance dokumentiert)."""
    dmax: float
    n_splines: int = 20
    lam: object = LAMBDA_AUTO          # 'auto' oder fester λ_rel-Wert
    lam_rel_min: float = 1e-14
    lam_rel_max: float = 1e4
    n_lam: int = 145                   # 8 Punkte pro Dekade
    md_tolerance: float = 0.25         # zulässiger MD-Anstieg für λ_opt (relativ zum Minimum)
    plateau_slope: float = 0.3         # max. |d log N_c / d log λ| eines Plateaus
    # Standard 'dirichlet': bestraft zusätzlich Sprünge zu p(0)=p(Dmax)=0. Die reine
    # Glatter-Form lässt einen konstanten Koeffizientenvektor unbestraft, der bei fehlenden
    # Kleinwinkeldaten unbestimmt bleibt (negatives p(r), Rg undefiniert).
    k_type: str = K_DIRICHLET
    background: bool = False
    n_r: int = 201

    def to_dict(self):
        return asdict(self)


@dataclass
class LambdaScan:
    """Ergebnis des λ-Scans (für die Darstellung wie G77 Fig. 2)."""
    lam_rel: np.ndarray
    md: np.ndarray
    nc: np.ndarray
    abs_slope: np.ndarray
    index_opt: int
    inflexion_found: bool
    lam_scale: float


@dataclass
class IFTSolution:
    """Numerisches Ergebnis einer IFT (ohne Diagnose/Provenance)."""
    settings: IFTSettings
    q: np.ndarray
    intensity: np.ndarray
    sigma: np.ndarray
    lam_rel: float
    lam: float
    lam_manual: bool
    coefficients: np.ndarray            # Spline-Koeffizienten c
    covariance: np.ndarray              # Kovarianz von c (inkl. Untergrund)
    background: Optional[float]
    background_err: Optional[float]
    r: np.ndarray
    pr: np.ndarray
    pr_err: np.ndarray
    i_fit: np.ndarray                   # Fit auf dem q-Gitter der Daten (inkl. Untergrund)
    i_fit_err: np.ndarray
    chi2: float
    md: float                           # mittlere Abweichung pro Punkt [G77 Gl. 16]
    rg: float
    rg_err: float
    i0: float
    i0_err: float
    scan: Optional[LambdaScan] = None
    extras: dict = field(default_factory=dict)


def regularization_matrix(n, kind=K_GLATTER):
    """Glättungsmatrix K für die Norm der ersten Differenzen der Koeffizienten."""
    if kind == K_GLATTER:
        D = np.diff(np.eye(n), axis=0)                 # (N−1) × N
    elif kind == K_DIRICHLET:
        D = np.diff(np.eye(n + 2), axis=0)[:, 1:-1]    # (N+1) × N, Ränder fest auf 0
    elif kind == K_CURVATURE:
        D = np.diff(np.eye(n + 2), n=2, axis=0)[:, 1:-1]  # 2. Differenzen, Ränder auf 0
    else:
        raise ValueError(f"Unbekannter K-Typ: {kind}")
    return D.T @ D


def _select_lambda(lam_rel, md, nc, md_tolerance, plateau_slope):
    """Wendepunkt-Methode: minimale |d log N_c / d log λ| vor dem MD-Anstieg.

    Kandidaten sind lokale Minima von |Steigung| (Plateaus von log N_c), deren MD
    höchstens um `md_tolerance` über dem Minimum liegt und deren Steigung unter
    `plateau_slope` bleibt. Gewählt wird der Kandidat mit dem größten λ — also das
    Plateau direkt vor dem starken MD-Anstieg (maximal stabilisiert ohne Verlust an
    Anpassungsgüte) [G77, Fig. 2].

    Returns:
        (index, abs_slope, gefunden)
    """
    x = np.log10(lam_rel)
    y = np.log10(np.maximum(nc, np.finfo(float).tiny))
    abs_slope = np.abs(np.gradient(y, x))
    md_limit = np.min(md) * (1.0 + md_tolerance)
    admissible = md <= md_limit

    # Lokale Minima von |Steigung|. Der linke Scanrand zählt mit: reicht das Plateau bis
    # dorthin, bestimmen die Daten die Lösung bereits ohne nennenswerte Regularisierung.
    idx_all = np.arange(0, len(x) - 1)
    left = np.concatenate([[np.inf], abs_slope[:-2]])
    is_min = (abs_slope[idx_all] <= left) & (abs_slope[idx_all] <= abs_slope[idx_all + 1])
    ok = is_min & admissible[idx_all] & (abs_slope[idx_all] < plateau_slope)
    candidates = idx_all[ok]
    if len(candidates) > 0:
        return int(candidates.max()), abs_slope, True

    # Kein Wendepunkt: größtes λ, das die MD-Toleranz noch einhält (Flag!)
    idx = int(np.nonzero(admissible)[0].max())
    return idx, abs_slope, False


def run_ift(q, intensity, sigma, settings: IFTSettings, smearing=None):
    """Führt eine IFT durch.

    Args:
        q, intensity, sigma: Daten im Fitbereich (q in nm⁻¹, σ > 0)
        settings: IFTSettings
        smearing: Verschmierungsoperator (Standard: Pinhole/Identität)
    """
    q = np.asarray(q, dtype=float)
    I = np.asarray(intensity, dtype=float)
    s = np.asarray(sigma, dtype=float)
    if not (len(q) == len(I) == len(s)):
        raise ValueError("q, I und σ müssen gleich lang sein")
    if np.any(~np.isfinite(s)) or np.any(s <= 0):
        raise ValueError("σ muss überall positiv und endlich sein")
    n_params = settings.n_splines + (1 if settings.background else 0)
    if len(q) <= n_params:
        raise ValueError(f"Zu wenige Datenpunkte ({len(q)}) für {n_params} Parameter")

    smearing = smearing or IdentitySmearing()
    basis = SplineBasis(settings.dmax, settings.n_splines)
    A = smearing.apply(cached_design_matrix(q, settings.dmax, settings.n_splines))
    K = regularization_matrix(settings.n_splines, settings.k_type)
    n_spl = settings.n_splines

    Aw = A / s[:, None]
    yw = I / s
    if not (np.all(np.isfinite(Aw)) and np.all(np.isfinite(yw))):
        raise ValueError("Nicht-endliche Werte in Daten oder Designmatrix")

    # Optionaler konstanter Untergrund: wird analytisch herausprojiziert (gewichtete
    # Projektion P = 1 − w wᵀ/‖w‖², w = 1/σ). Die Regularisierung wirkt dann nur auf die
    # Splines, der Untergrund folgt exakt aus dem Residuum.
    if settings.background:
        w = 1.0 / s
        w_norm2 = float(w @ w)
        def project(x):
            return x - np.outer(w, w @ x) / w_norm2 if x.ndim == 2 else x - w * (w @ x) / w_norm2
        Aw_p, yw_p = project(Aw), project(yw)
    else:
        Aw_p, yw_p = Aw, yw

    B = Aw_p.T @ Aw_p
    b = Aw_p.T @ yw_p
    lam_scale = np.trace(B) / np.trace(K)

    # Verallgemeinerte Eigenzerlegung von (B, K): mit K = LLᵀ und L⁻¹BL⁻ᵀ = U diag(β) Uᵀ
    # ist (B + λK)⁻¹ = L⁻ᵀ U diag(1/(β+λ)) Uᵀ L⁻¹ — numerisch stabil für alle λ > 0 und
    # jede λ-Lösung kostet nur O(N²).
    # Winziger Ridge: macht auch die (singuläre) Glatter-Form von K Cholesky-fähig
    K_reg = K + 1e-10 * np.mean(np.diag(K)) * np.eye(n_spl)
    L_inv = np.linalg.inv(np.linalg.cholesky(K_reg))
    beta, U = np.linalg.eigh(L_inv @ B @ L_inv.T)
    beta = np.maximum(beta, 0.0)
    z = U.T @ (L_inv @ b)
    back = U.T @ L_inv                                 # v ↦ c = backᵀ v

    # λ-Scan (alle λ auf einmal)
    lam_grid = np.logspace(np.log10(settings.lam_rel_min), np.log10(settings.lam_rel_max),
                           int(settings.n_lam))
    V = z[None, :] / (beta[None, :] + (lam_grid * lam_scale)[:, None])
    C = V @ back
    resid = C @ Aw_p.T - yw_p[None, :]
    chi2_grid = np.sum(resid ** 2, axis=1)
    md_grid = chi2_grid / len(q)
    nc_grid = np.sum(V ** 2, axis=1)                    # cᵀKc = ‖v‖²

    idx, abs_slope, found = _select_lambda(lam_grid, md_grid, nc_grid,
                                           settings.md_tolerance, settings.plateau_slope)
    scan = LambdaScan(lam_rel=lam_grid, md=md_grid, nc=nc_grid, abs_slope=abs_slope,
                      index_opt=idx, inflexion_found=found, lam_scale=lam_scale)

    lam_manual = settings.lam != LAMBDA_AUTO
    lam_rel = float(settings.lam) if lam_manual else float(lam_grid[idx])
    lam = lam_rel * lam_scale

    # Linearer Lösungsoperator G (c = G·yw). Da yw Einheitskovarianz hat, gilt Cov = G·Gᵀ
    # (ohne Untergrund identisch mit H⁻¹BH⁻¹).
    # Aw_pᵀ ist bereits projiziert (Aw_pᵀP = Aw_pᵀ), daher wirkt G direkt auf yw.
    G = (back.T / (beta + lam)) @ back @ Aw_p.T         # (N × M)
    if settings.background:
        g_bg = (w - (w @ Aw) @ G) / w_norm2              # bg = g_bg · yw
        G_all = np.vstack([G, g_bg])
        A_all = np.hstack([A, np.ones((len(q), 1))])
    else:
        G_all, A_all = G, A
    c_all = G_all @ yw
    cov_all = G_all @ G_all.T
    c = c_all[:n_spl]
    cov_c = cov_all[:n_spl, :n_spl]

    fit = A_all @ c_all
    fit_err = np.sqrt(np.maximum(np.einsum('ij,jk,ik->i', A_all, cov_all, A_all), 0.0))
    chi2 = float(np.sum(((I - fit) / s) ** 2))

    # p(r) auf äquidistantem Gitter
    r = np.linspace(0.0, settings.dmax, int(settings.n_r))
    Phi = basis.evaluate(r)
    pr = Phi @ c
    pr_err = np.sqrt(np.maximum(np.einsum('ij,jk,ik->i', Phi, cov_c, Phi), 0.0))

    # Momente für I(0) und Rg [G77 Gl. 19/20] per exakter Quadratur
    rq, wq = basis.quadrature(8)
    Phi_q = basis.evaluate(rq)
    m0_vec = FOUR_PI * (wq @ Phi_q)                 # I(0) = m0_vec · c
    m2_vec = FOUR_PI * ((wq * rq ** 2) @ Phi_q)
    i0 = float(m0_vec @ c)
    m2 = float(m2_vec @ c)
    i0_err = float(np.sqrt(max(m0_vec @ cov_c @ m0_vec, 0.0)))
    if i0 > 0 and m2 > 0:
        rg2 = m2 / (2.0 * i0)
        rg = float(np.sqrt(rg2))
        grad = (m2_vec / (2.0 * i0) - m2 * m0_vec / (2.0 * i0 ** 2)) / (2.0 * rg)
        rg_err = float(np.sqrt(max(grad @ cov_c @ grad, 0.0)))
    else:
        rg, rg_err = float('nan'), float('nan')

    if settings.background:
        bg = float(c_all[-1])
        bg_err = float(np.sqrt(max(cov_all[-1, -1], 0.0)))
    else:
        bg, bg_err = None, None

    return IFTSolution(
        settings=settings, q=q, intensity=I, sigma=s,
        lam_rel=lam_rel, lam=lam, lam_manual=lam_manual,
        coefficients=c, covariance=cov_all, background=bg, background_err=bg_err,
        r=r, pr=pr, pr_err=pr_err, i_fit=fit, i_fit_err=fit_err,
        chi2=chi2, md=chi2 / len(q), rg=rg, rg_err=rg_err, i0=i0, i0_err=i0_err,
        scan=scan,
    )


def estimate_sigma(q, intensity, window=11, polyorder=2):
    """Schätzt σ, falls keine Fehlerspalte vorhanden ist.

    Residuen eines Savitzky-Golay-Glätters, lokal robust skaliert (MAD über ein
    gleitendes Fenster). Funktioniert auch bei Werten ≤ 0 (z. B. nach
    Untergrundabzug). Das Ergebnis ist nur eine grobe Näherung — die MD ist dann nur
    relativ aussagekräftig.
    """
    from scipy.signal import savgol_filter
    from ..significance import rolling_median

    I = np.asarray(intensity, dtype=float)
    n = len(I)
    window = min(window, n if n % 2 else n - 1)
    scale = max(float(np.median(np.abs(I))), np.finfo(float).tiny)
    if window <= polyorder + 1:
        return np.full(n, 0.1 * scale)
    smooth = savgol_filter(I, window, polyorder)
    # Die Residuen eines Glätters mit Fensterbreite w unterschätzen das Rauschen leicht;
    # Faktor √(w/(w−p−1)) korrigiert die verlorenen Freiheitsgrade näherungsweise.
    dof = np.sqrt(window / (window - polyorder - 1))
    sigma = 1.4826 * dof * rolling_median(np.abs(I - smooth), 2 * window + 1)
    floor = np.maximum(1e-4 * np.abs(smooth), 1e-6 * scale)
    return np.where(np.isfinite(sigma), np.maximum(sigma, floor), floor)
