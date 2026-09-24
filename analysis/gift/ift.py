"""
Indirekte Fourier-Transformation nach Glatter (1977).

    I(q) ≈ Σ c_ν ψ_ν(q)  [+ Untergrund]
    (B + λK) c = b,   B = AᵀWA,  b = AᵀW·I,  W = diag(1/σ²)          [G77 Gl. 12–15]

λ wird standardmäßig über die Wendepunkt-Methode [G77, Fig. 2] bestimmt: log N_c(λ) zeigt
einen Wendepunkt (minimale |Steigung|) im Bereich kurz vor dem starken Anstieg der
mittleren Abweichung MD(λ). Alternativ (v7.13): Maximum der Bayes'schen Evidenz
[Hansen 2000], dieselbe Größe wie in der DREAM-Analyse. λ wird intern relativ angegeben
(λ_rel), damit der Scanbereich unabhängig von Intensitätsskala und Fehlergröße ist:
λ = λ_rel · tr(B)/tr(K).
"""

from dataclasses import dataclass, field, asdict
from typing import Optional

import numpy as np

from .transform import cached_design_matrix, make_basis, moment_vectors
from .kernels import PDDF, get_kernel
from .smearing import IdentitySmearing

K_GLATTER = 'glatter'      # Σ (c_{ν+1} − c_ν)²            [G77 Gl. 14]
K_DIRICHLET = 'dirichlet'  # wie oben, zusätzlich c_0 = c_{N+1} = 0 (positiv definit)
K_CURVATURE = 'curvature'  # Σ (c_{ν+1} − 2c_ν + c_{ν−1})², c_0 = c_{N+1} = 0

LAMBDA_AUTO = 'auto'
LAMBDA_INFLEXION = 'inflexion'   # Wendepunkt nach Glatter (Standard)
LAMBDA_EVIDENCE = 'evidence'     # Maximum der Evidenz p(I | λ) [Hansen 2000]

_LOG_2PI = float(np.log(2.0 * np.pi))


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
    # Verfahren für lam = 'auto': Wendepunkt (Standard) oder Evidenz-Maximum
    lam_method: str = LAMBDA_INFLEXION
    # Art der Transformation (v8.0): p(r), Querschnitt, Dicke, Größenverteilung (kernels.py)
    kind: str = PDDF

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
    log_evidence: Optional[np.ndarray] = None   # log p(I | λ) [Hansen 2000]
    n_good: Optional[np.ndarray] = None         # effektive Parameterzahl N_g = Σ β/(β+λ)
    index_inflexion: Optional[int] = None
    index_evidence: Optional[int] = None
    method: str = LAMBDA_INFLEXION


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


def settings_kind(settings):
    """IFT-Art der Einstellungen (ältere Sidecars ohne Feld: p(r))."""
    return getattr(settings, 'kind', None) or PDDF


def regularization_matrix(n, kind=K_GLATTER, left_free=False):
    """Glättungsmatrix K für die Norm der ersten Differenzen der Koeffizienten.

    left_free: nur der rechte Rand ist fest auf 0 (Dicken-Verteilung, p_t(0) ≠ 0)."""
    inner = slice(0, -1) if left_free else slice(1, -1)
    pad = n + 1 if left_free else n + 2
    if kind == K_GLATTER:
        D = np.diff(np.eye(n), axis=0)                 # (N−1) × N
    elif kind == K_DIRICHLET:
        D = np.diff(np.eye(pad), axis=0)[:, inner]     # (N+1) × N, Ränder fest auf 0
    elif kind == K_CURVATURE:
        D = np.diff(np.eye(pad), n=2, axis=0)[:, inner]  # 2. Differenzen, Ränder auf 0
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
        idx = int(candidates.max())
        if idx == 0:
            # Randplateau: log N_c ist ab dem linken Scanrand flach (z. B. grobe Basis bei
            # großem Dmax). Gemeint ist das Plateau *vor* dem MD-Anstieg, also dessen
            # rechtes Ende — nicht der willkürliche Scanrand (v7.13).
            flat = plateau_slope / 6.0
            while idx + 1 < len(x) - 1 and abs_slope[idx + 1] < flat and admissible[idx + 1]:
                idx += 1
        return idx, abs_slope, True

    # Kein Wendepunkt: größtes λ, das die MD-Toleranz noch einhält (Flag!)
    idx = int(np.nonzero(admissible)[0].max())
    return idx, abs_slope, False


class IFTProblem:
    """Vorbereitete (gewichtete) Designmatrix für viele schnelle Auswertungen mit
    wechselndem Strukturfaktor S(q) und festem λ — Zielfunktion der GIFT-Optimierung.

        I(q) = S(q) · Σ c_ν ψ_ν(q)   [+ Untergrund]            [BP97 Gl. 5–7]
    """

    def __init__(self, q, intensity, sigma, settings: IFTSettings, smearing=None):
        self.q = np.asarray(q, dtype=float)
        self.I = np.asarray(intensity, dtype=float)
        self.s = np.asarray(sigma, dtype=float)
        self.settings = settings
        smearing = smearing or IdentitySmearing()
        kind = settings_kind(settings)
        self.A = smearing.apply(cached_design_matrix(self.q, settings.dmax, settings.n_splines,
                                                     kind))
        self.K = regularization_matrix(settings.n_splines, settings.k_type,
                                       get_kernel(kind).left_free)
        self.Aw = self.A / self.s[:, None]
        self.yw = self.I / self.s
        if settings.background:
            self.w = 1.0 / self.s
            self.w_norm2 = float(self.w @ self.w)
            self.yw_p = self.yw - self.w * (self.w @ self.yw) / self.w_norm2
        else:
            self.yw_p = self.yw
        self.trace_k = float(np.trace(self.K))
        self.n_eval = 0

    def _project(self, M):
        if not self.settings.background:
            return M
        return M - np.outer(self.w, self.w @ M) / self.w_norm2

    def md(self, structure_factor, lam_rel):
        """Mittlere Abweichung χ²/M für gegebenes S(q) und festes λ_rel (inf bei Fehlern)."""
        self.n_eval += 1
        S = np.asarray(structure_factor, dtype=float)
        if not np.all(np.isfinite(S)):
            return np.inf
        Aw_p = self._project(self.Aw * S[:, None])
        B = Aw_p.T @ Aw_p
        lam = lam_rel * np.trace(B) / self.trace_k
        try:
            L = np.linalg.cholesky(B + lam * self.K)
            d = np.diag(L)
            ill = d.min() < 1e-7 * d.max()         # Kondition von B + λK > ~10¹⁴
        except np.linalg.LinAlgError:
            ill = True
        if ill:
            # Sehr kleines λ (erweiterter λ-Scan, v7.13): Normalgleichungen sind zu schlecht
            # konditioniert. Stabil über QR/SVD des gestapelten Systems [Aw_p; √λ·Dᵀ].
            if not (lam > 0 and np.isfinite(lam)):
                return np.inf
            self._chol_k = getattr(self, '_chol_k', None)
            if self._chol_k is None:
                n = self.K.shape[0]
                self._chol_k = np.linalg.cholesky(
                    self.K + 1e-10 * np.mean(np.diag(self.K)) * np.eye(n)).T
            M_stack = np.vstack([Aw_p, np.sqrt(lam) * self._chol_k])
            y_stack = np.concatenate([self.yw_p, np.zeros(self.K.shape[0])])
            c = np.linalg.lstsq(M_stack, y_stack, rcond=None)[0]
        else:
            c = np.linalg.solve(L.T, np.linalg.solve(L, Aw_p.T @ self.yw_p))
        r = Aw_p @ c - self.yw_p
        return float(r @ r) / len(self.q)

    def md_batch(self, structure_factors, lam_rel, chunk=64):
        """MD für K Strukturfaktoren auf einmal (Form (K, M)) — vektorisiert.

        Gleiche Mathematik wie md(); gestapelte Cholesky-Zerlegungen (K, N, N). Parametersätze
        mit nicht-endlichem S(q) oder nicht positiv definitem System ergeben ∞. Grundlage
        für DREAM und das Screening (viele Parametersätze je Generation).
        """
        S_all = np.atleast_2d(np.asarray(structure_factors, dtype=float))
        out = np.full(len(S_all), np.inf)
        lam_rel = np.broadcast_to(np.asarray(lam_rel, dtype=float), (len(S_all),))
        for start in range(0, len(S_all), chunk):
            S = S_all[start:start + chunk]
            lr = lam_rel[start:start + chunk]
            ok = np.all(np.isfinite(S), axis=1)
            if not ok.any():
                continue
            Aw = self.Aw[None, :, :] * S[ok][:, :, None]                    # (K, M, N)
            if self.settings.background:
                Aw = Aw - self.w[None, :, None] * \
                    (np.einsum('m,kmn->kn', self.w, Aw) / self.w_norm2)[:, None, :]
            AwT = np.swapaxes(Aw, 1, 2)                                      # (K, N, M)
            B = np.matmul(AwT, Aw)                                           # BLAS-GEMM je k
            b = np.matmul(AwT, self.yw_p)
            lam = lr[ok] * np.trace(B, axis1=1, axis2=2) / self.trace_k
            H = B + lam[:, None, None] * self.K[None, :, :]
            md = np.full(len(B), np.inf)
            try:
                L = np.linalg.cholesky(H)
                dg = np.diagonal(L, axis1=1, axis2=2)
                if np.any(dg.min(axis=1) < 1e-7 * dg.max(axis=1)):
                    raise np.linalg.LinAlgError   # schlecht konditioniert → wie md()
                c = np.linalg.solve(np.swapaxes(L, 1, 2),
                                    np.linalg.solve(L, b[..., None]))[..., 0]
                r = np.matmul(Aw, c[..., None])[..., 0] - self.yw_p[None, :]
                md = np.sum(r * r, axis=1) / len(self.q)
            except np.linalg.LinAlgError:
                # Einzelne nicht positiv definite Systeme: einzeln auswerten
                for j in range(len(B)):
                    md[j] = self.md(S[ok][j], lr[ok][j])
            idx = np.nonzero(ok)[0] + start
            out[idx] = md
        self.n_eval += len(S_all)
        return out


class IFTDecomposition:
    """Vorbereitete IFT bei festem (q, Dmax, N, S(q)): gewichtete Designmatrix, optional
    herausprojizierter Untergrund und die verallgemeinerte Eigenzerlegung von (B, K).

    Mit K = LLᵀ und L⁻¹BL⁻ᵀ = U diag(β) Uᵀ ist (B + λK)⁻¹ = L⁻ᵀ U diag(1/(β+λ)) Uᵀ L⁻¹ —
    numerisch stabil für alle λ > 0; jede λ-Lösung kostet nur O(N²). Grundlage für
    run_ift() und den Explorer (Dmax × λ-Karten).
    """

    def __init__(self, q, intensity, sigma, settings: IFTSettings, smearing=None,
                 structure_factor=None):
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
        self.q, self.I, self.s, self.settings = q, I, s, settings
        smearing = smearing or IdentitySmearing()
        kind = settings_kind(settings)
        self.basis = make_basis(settings.dmax, settings.n_splines, kind)
        self.A_form = smearing.apply(cached_design_matrix(q, settings.dmax, settings.n_splines,
                                                          kind))
        if structure_factor is not None:
            S_q = np.asarray(structure_factor, dtype=float)
            if S_q.shape != q.shape or not np.all(np.isfinite(S_q)):
                raise ValueError("S(q) muss endlich sein und dieselbe Länge wie q haben")
            self.A = self.A_form * S_q[:, None]      # ψ̃_ν(q) = ψ_ν(q)·S(q)  [BP97 Gl. 6]
        else:
            S_q = None
            self.A = self.A_form
        self.S_q = S_q
        self.K = regularization_matrix(settings.n_splines, settings.k_type,
                                       get_kernel(kind).left_free)
        n_spl = settings.n_splines
        self.Aw = self.A / s[:, None]
        self.yw = I / s
        if not (np.all(np.isfinite(self.Aw)) and np.all(np.isfinite(self.yw))):
            raise ValueError("Nicht-endliche Werte in Daten oder Designmatrix")

        # Optionaler konstanter Untergrund: wird analytisch herausprojiziert (gewichtete
        # Projektion P = 1 − w wᵀ/‖w‖², w = 1/σ). Die Regularisierung wirkt dann nur auf die
        # Splines, der Untergrund folgt exakt aus dem Residuum.
        if settings.background:
            w = 1.0 / s
            self.w, self.w_norm2 = w, float(w @ w)
            self.Aw_p = self.Aw - np.outer(w, w @ self.Aw) / self.w_norm2
            self.yw_p = self.yw - w * (w @ self.yw) / self.w_norm2
            m_eff = len(q) - 1
        else:
            self.Aw_p, self.yw_p = self.Aw, self.yw
            m_eff = len(q)

        # tr(B) = ‖Aw_p‖²_F (B selbst wird nicht gebildet)
        self.lam_scale = float(np.sum(self.Aw_p ** 2)) / np.trace(self.K)
        # Winziger Ridge: macht auch die (singuläre) Glatter-Form von K Cholesky-fähig
        K_reg = self.K + 1e-10 * np.mean(np.diag(self.K)) * np.eye(n_spl)
        L_inv = np.linalg.inv(np.linalg.cholesky(K_reg))
        # Verallgemeinerte Zerlegung per SVD von Ã = Aw_p·L⁻ᵀ = W diag(σ) Vᵀ (v7.13) statt
        # Eigenzerlegung von B = ÃᵀÃ: β = σ², z = σ·Wᵀy. Die SVD halbiert die Kondition in
        # Dekaden — bei Daten ohne Kleinwinkelbereich reicht β über ~20 Dekaden, die kleinen
        # Eigenwerte von B gingen im Rundungsfehler ε·β_max unter (MD stieg für kleine λ).
        W, sv, Vt = np.linalg.svd(self.Aw_p @ L_inv.T, full_matrices=False)
        self.beta = sv ** 2
        self.z = sv * (W.T @ self.yw_p)
        self.back = Vt @ L_inv                           # v ↦ c = backᵀ v
        # back·Aw_pᵀ = diag(σ)·Wᵀ exakt aus der SVD (das Produkt verlöre die Genauigkeit)
        self.sv, self.Wt = sv, W.T
        # Konstante der Evidenz (Gauß-Normierung der Daten)
        self.log_const = -0.5 * m_eff * _LOG_2PI - float(np.sum(np.log(s)))

    def scan(self, lam_rel):
        """Alle Größen für ein Gitter λ_rel (Λ,): Koeffizienten C (Λ, N), χ², MD, N_c, N_g
        und log-Evidenz log p(I | λ) [Hansen 2000]."""
        lam = np.atleast_1d(np.asarray(lam_rel, dtype=float)) * self.lam_scale
        V = self.z[None, :] / (self.beta[None, :] + lam[:, None])
        C = V @ self.back
        resid = C @ self.Aw_p.T - self.yw_p[None, :]
        chi2 = np.sum(resid ** 2, axis=1)
        nc = np.sum(V ** 2, axis=1)                       # cᵀKc = ‖v‖²
        n_good = np.sum(self.beta[None, :] / (self.beta[None, :] + lam[:, None]), axis=1)
        # log det(λK) − log det(B + λK) = N log λ − Σ log(β + λ)   (K = LLᵀ kürzt sich)
        log_ev = (self.log_const - 0.5 * (chi2 + lam * nc)
                  + 0.5 * (len(self.beta) * np.log(lam)
                           - np.sum(np.log(self.beta[None, :] + lam[:, None]), axis=1)))
        return {'lam': lam, 'C': C, 'chi2': chi2, 'md': chi2 / len(self.q), 'nc': nc,
                'n_good': n_good, 'log_evidence': log_ev}

    def coefficient_variance_weights(self, lam):
        """Kovarianz der Koeffizienten: Cov(c) = backᵀ diag(β/(β+λ)²) back (Einheits-
        kovarianz der gewichteten Daten; Aw_p·backᵀ ist in dieser Basis diagonal)."""
        return self.beta / (self.beta + lam) ** 2


LAM_REL_FLOOR = 1e-30      # untere Grenze der automatischen Scan-Erweiterung
MD0_EXTEND_MAX = 2.0       # Erweiterung nur, wenn die unregularisierte Lösung passt


def lambda_grid(dec: 'IFTDecomposition', settings: IFTSettings):
    """λ_rel-Gitter des Scans und Scan-Ergebnisse.

    Standardbereich lam_rel_min … lam_rel_max. Liegt die MD am linken Rand noch deutlich über
    dem Wert ohne Regularisierung MD₀ (MD ≤ 1.25·MD₀ + 3·√(2/M) verfehlt), wird der Bereich in
    Schritten von 4 Dekaden bis 10⁻³⁰ nach unten erweitert (v7.13). Das tritt auf, wenn die
    Eigenwerte β über viele Dekaden reichen (z. B. Daten ohne Kleinwinkelbereich): Die
    Normierung λ_rel = λ·tr(K)/tr(B) wird dann von den größten β bestimmt.
    Nur wenn die Daten überhaupt beschreibbar sind (MD₀ ≤ 2): Passt schon die
    unregularisierte Lösung nicht (z. B. IFT bei Wechselwirkung), brächte ein kleineres λ nur
    Überanpassung.
    """
    lo = float(np.log10(settings.lam_rel_min))
    hi = float(np.log10(settings.lam_rel_max))
    per_decade = (int(settings.n_lam) - 1) / (hi - lo)
    floor = float(np.log10(LAM_REL_FLOOR))
    md0 = float(dec.scan([LAM_REL_FLOOR])['md'][0])
    tol = 0.25 * md0 + 3.0 * np.sqrt(2.0 / len(dec.q))
    while True:
        n = int(round((hi - lo) * per_decade)) + 1
        grid = np.logspace(lo, hi, n)
        g = dec.scan(grid)
        if lo <= floor or md0 > MD0_EXTEND_MAX or g['md'][0] <= md0 + tol:
            return grid, g
        lo = max(lo - 4.0, floor)


def run_ift(q, intensity, sigma, settings: IFTSettings, smearing=None, structure_factor=None):
    """Führt eine IFT durch.

    Args:
        q, intensity, sigma: Daten im Fitbereich (q in nm⁻¹, σ > 0)
        settings: IFTSettings
        smearing: Verschmierungsoperator (Standard: Pinhole/Identität)
        structure_factor: optional S(q) auf dem q-Gitter (GIFT): I = S·P [BP97 Gl. 5];
            p(r), Rg und I(0) beziehen sich dann auf den Formfaktor P(q)
    """
    dec = IFTDecomposition(q, intensity, sigma, settings, smearing, structure_factor)
    q, I, s = dec.q, dec.I, dec.s
    basis, A_form, A, S_q = dec.basis, dec.A_form, dec.A, dec.S_q
    n_spl = settings.n_splines
    Aw, Aw_p, yw = dec.Aw, dec.Aw_p, dec.yw
    beta, back, lam_scale = dec.beta, dec.back, dec.lam_scale

    # λ-Scan (alle λ auf einmal; bei Bedarf nach unten erweitert)
    lam_grid, grid = lambda_grid(dec, settings)
    md_grid, nc_grid = grid['md'], grid['nc']

    idx_infl, abs_slope, found = _select_lambda(lam_grid, md_grid, nc_grid,
                                                settings.md_tolerance, settings.plateau_slope)
    idx_ev = int(np.argmax(grid['log_evidence']))
    method = getattr(settings, 'lam_method', LAMBDA_INFLEXION)
    if method not in (LAMBDA_INFLEXION, LAMBDA_EVIDENCE):
        raise ValueError(f"Unbekanntes λ-Verfahren: {method}")
    idx = idx_ev if method == LAMBDA_EVIDENCE else idx_infl
    scan = LambdaScan(lam_rel=lam_grid, md=md_grid, nc=nc_grid, abs_slope=abs_slope,
                      index_opt=idx, inflexion_found=found, lam_scale=lam_scale,
                      log_evidence=grid['log_evidence'], n_good=grid['n_good'],
                      index_inflexion=idx_infl, index_evidence=idx_ev, method=method)

    lam_manual = settings.lam != LAMBDA_AUTO
    lam_rel = float(settings.lam) if lam_manual else float(lam_grid[idx])
    lam = lam_rel * lam_scale

    # Linearer Lösungsoperator G (c = G·yw). Da yw Einheitskovarianz hat, gilt Cov = G·Gᵀ
    # (ohne Untergrund identisch mit H⁻¹BH⁻¹).
    # Aw_pᵀ ist bereits projiziert (Aw_pᵀP = Aw_pᵀ), daher wirkt G direkt auf yw.
    G = back.T @ ((dec.sv / (beta + lam))[:, None] * dec.Wt)   # (N × M), = H⁻¹·Aw_pᵀ
    if settings.background:
        g_bg = (dec.w - (dec.w @ Aw) @ G) / dec.w_norm2  # bg = g_bg · yw
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

    # Momente für I(0) und Rg [G77 Gl. 19/20] per exakter Quadratur; andere Arten:
    # Vorwärtswert und Trägheitsradius der jeweiligen Geometrie (kernels.py)
    m0_vec, m2_vec = moment_vectors(basis, settings_kind(settings))   # I(0) = m0_vec · c
    i0 = float(m0_vec @ c)
    m2 = float(m2_vec @ c)
    i0_err = float(np.sqrt(max(m0_vec @ cov_c @ m0_vec, 0.0)))
    if i0 > 0 and m2 > 0:
        rg2 = m2 / i0
        rg = float(np.sqrt(rg2))
        grad = (m2_vec / i0 - m2 * m0_vec / i0 ** 2) / (2.0 * rg)
        rg_err = float(np.sqrt(max(grad @ cov_c @ grad, 0.0)))
    else:
        rg, rg_err = float('nan'), float('nan')

    if settings.background:
        bg = float(c_all[-1])
        bg_err = float(np.sqrt(max(cov_all[-1, -1], 0.0)))
    else:
        bg, bg_err = None, None

    extras = {}
    if S_q is not None:
        # Formfaktor P(q) = Σ c_ν ψ_ν(q) (ohne S, ohne Untergrund) mit Fehlerband
        extras['structure_factor'] = S_q
        extras['form_factor'] = A_form @ c
        extras['form_factor_err'] = np.sqrt(np.maximum(
            np.einsum('ij,jk,ik->i', A_form, cov_c, A_form), 0.0))
    # Evidenz und effektive Parameterzahl beim gewählten λ
    at = dec.scan([lam_rel])
    extras['log_evidence'] = float(at['log_evidence'][0])
    extras['n_good'] = float(at['n_good'][0])

    return IFTSolution(
        settings=settings, q=q, intensity=I, sigma=s,
        lam_rel=lam_rel, lam=lam, lam_manual=lam_manual,
        coefficients=c, covariance=cov_all, background=bg, background_err=bg_err,
        r=r, pr=pr, pr_err=pr_err, i_fit=fit, i_fit_err=fit_err,
        chi2=chi2, md=chi2 / len(q), rg=rg, rg_err=rg_err, i0=i0, i0_err=i0_err,
        scan=scan, extras=extras,
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
