"""
Hayter-Penfold-MSA-Strukturfaktor mit Rescaling nach Hansen & Hayter (RMSA) für
geladene Kugeln (abgeschirmtes Coulomb-/Yukawa-Potential).

    [HP81] J. B. Hayter, J. Penfold, Mol. Phys. 42 (1981) 109–118
    [HH82] J.-P. Hansen, J. B. Hayter, Mol. Phys. 46 (1982) 651–656
    [F00]  G. Fritz, A. Bergmann, O. Glatter, J. Chem. Phys. 113 (2000) 9733

Diese Datei ist eine zeilengetreue Python-Portierung von `hayter_msa.c` aus sasmodels
(Version 1.0.12), das wiederum auf Hayters Fortran-Routinen SQHPA/SQCOEF/SQFUN/SQHCAL
(ILL 1981) zurückgeht. Variablennamen und die Belegung des Arbeitsvektors `w`
(gMSAWave) sind beibehalten, damit die Portierung Zeile für Zeile prüfbar bleibt:

    w[0] A   w[1] B   w[2] C   w[3] F   w[4] η   w[5] γe^{-k} (Kontaktpotential)
    w[6] k = κσ   w[7] U   w[8] V   w[9] Kopplung   w[10] η' (reskaliert)
    w[11] γ'e^{-k'}   w[12] k'   w[13] s = σ'/σ   w[14] g(1+)   w[15], w[16] Hilfswerte

Auch die physikalischen Konstanten sind die aus sasmodels (ältere CODATA-Werte), damit
Ergebnisse mit SasView vergleichbar sind (Abweichung zu CODATA 2018 ~1e-5 relativ).

----------------------------------------------------------------------------------------
Lizenz des portierten Codes (sasmodels, BSD-3-Clause):

Copyright (c) 2009-2025, SasView Developers
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are
permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright notice, this list of
   conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice, this list
   of conditions and the following disclaimer in the documentation and/or other
   materials provided with the distribution.
3. Neither the name of the copyright holder nor the names of its contributors may be
   used to endorse or promote products derived from this software without specific
   prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL
THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT
OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
----------------------------------------------------------------------------------------
"""

import math

import numpy as np

# Konstanten wie in sasmodels/hayter_msa.c
ELCHARGE = 1.602189e-19        # C
K_BOLTZMANN = 1.380662e-23     # J/K
EPS0 = 8.85418782e-12          # C²/(N m²)
AVOGADRO = 6.022e23            # 1/mol


class RMSAError(ArithmeticError):
    """Die HP-/RMSA-Lösung konvergiert nicht (ir < 0 in sqcoef)."""


def _sqfun(ix, ir, w):
    """SQFUN: MSA-Koeffizienten für die (reskalierte) Packungsdichte w[16]."""
    acc = 1.0e-6
    itm = 40
    a2 = a3 = b2 = b3 = v2 = v3 = p2 = p3 = 0.0

    reta = w[16]
    eta2 = reta * reta
    eta3 = eta2 * reta
    e12 = 12.0 * reta
    e24 = e12 + e12
    w[13] = (w[4] / w[16]) ** (1.0 / 3.0)
    w[12] = w[6] / w[13]
    ibig = 1 if (w[12] > 15.0 and ix == 1) else 0

    w[11] = w[5] * w[13] * math.exp(w[6] - w[12])
    rgek = w[11]
    rak = w[12]
    ak2 = rak * rak
    ak1 = 1.0 + rak
    dak2 = 1.0 / ak2
    dak4 = dak2 * dak2
    d = 1.0 - reta
    d2 = d * d
    dak = d / rak
    dd2 = 1.0 / d2
    dd4 = dd2 * dd2
    dd45 = dd4 * 2.0e-1
    eta3d = 3.0 * reta
    eta6d = eta3d + eta3d
    eta32 = eta3 + eta3
    eta2d = reta + 2.0
    eta2d2 = eta2d * eta2d
    eta21 = 2.0 * reta + 1.0
    eta22 = eta21 * eta21

    # ALPHA(I)
    al1 = -eta21 * dak
    al2 = (14.0 * eta2 - 4.0 * reta - 1.0) * dak2
    al3 = 36.0 * eta2 * dak4
    # BETA(I)
    be1 = -(eta2 + 7.0 * reta + 1.0) * dak
    be2 = 9.0 * reta * (eta2 + 4.0 * reta - 2.0) * dak2
    be3 = 12.0 * reta * (2.0 * eta2 + 8.0 * reta - 1.0) * dak4
    # NU(I)
    vu1 = -(eta3 + 3.0 * eta2 + 45.0 * reta + 5.0) * dak
    vu2 = (eta32 + 3.0 * eta2 + 42.0 * reta - 2.0e1) * dak2
    vu3 = (eta32 + 3.0e1 * reta - 5.0) * dak4
    vu4 = vu1 + e24 * rak * vu3
    vu5 = eta6d * (vu2 + 4.0 * vu3)
    # PHI(I)
    ph1 = eta6d / rak
    ph2 = d - e12 * dak2
    # TAU(I)
    ta1 = (reta + 5.0) / (5.0 * rak)
    ta2 = eta2d * dak2
    ta3 = -e12 * rgek * (ta1 + ta2)
    ta4 = eta3d * ak2 * (ta1 * ta1 - ta2 * ta2)
    ta5 = eta3d * (reta + 8.0) * 1.0e-1 - 2.0 * eta22 * dak2

    # SINH(K), COSH(K)
    ex1 = math.exp(rak)
    ex2 = math.exp(-rak) if w[12] < 20.0 else 0.0
    sk = 0.5 * (ex1 - ex2)
    ck = 0.5 * (ex1 + ex2)
    ckma = ck - 1.0 - rak * sk
    skma = sk - rak * ck

    # a(I)
    a1 = (e24 * rgek * (al1 + al2 + ak1 * al3) - eta22) * dd4
    if ibig == 0:
        a2 = e24 * (al3 * skma + al2 * sk - al1 * ck) * dd4
        a3 = e24 * (eta22 * dak2 - 0.5 * d2 + al3 * ckma - al1 * sk + al2 * ck) * dd4
    # b(I)
    b1 = (1.5 * reta * eta2d2 - e12 * rgek * (be1 + be2 + ak1 * be3)) * dd4
    if ibig == 0:
        b2 = e12 * (-be3 * skma - be2 * sk + be1 * ck) * dd4
        b3 = e12 * (0.5 * d2 * eta2d - eta3d * eta2d2 * dak2 - be3 * ckma + be1 * sk
                    - be2 * ck) * dd4
    # V(I)
    v1 = (eta21 * (eta2 - 2.0 * reta + 1.0e1) * 2.5e-1 - rgek * (vu4 + vu5)) * dd45
    if ibig == 0:
        v2 = (vu4 * ck - vu5 * sk) * dd45
        v3 = ((eta3 - 6.0 * eta2 + 5.0) * d
              - eta6d * (2.0 * eta3 - 3.0 * eta2 + 18.0 * reta + 1.0e1) * dak2
              + e24 * vu3 + vu4 * sk - vu5 * ck) * dd45
    # P(I)
    pp1 = ph1 * ph1
    pp2 = ph2 * ph2
    pp = pp1 + pp2
    p1p2 = ph1 * ph2 * 2.0
    p1 = (rgek * (pp1 + pp2 - p1p2) - 0.5 * eta2d) * dd2
    if ibig == 0:
        p2 = (pp * sk + p1p2 * ck) * dd2
        p3 = (pp * ck + p1p2 * sk + pp1 - pp2) * dd2
    # T(I)
    t1 = ta3 + ta4 * a1 + ta5 * b1

    if ibig != 0:
        # SEHR GROSSE ABSCHIRMUNG: ASYMPTOTISCHE LÖSUNG
        v3 = ((eta3 - 6.0 * eta2 + 5.0) * d
              - eta6d * (2.0 * eta3 - 3.0 * eta2 + 18.0 * reta + 1.0e1) * dak2 + e24 * vu3) * dd45
        t3 = ta4 * a3 + ta5 * b3 + e12 * ta2 - 4.0e-1 * reta * (reta + 1.0e1) - 1.0
        p3 = (pp1 - pp2) * dd2
        b3 = e12 * (0.5 * d2 * eta2d - eta3d * eta2d2 * dak2 + be3) * dd4
        a3 = e24 * (eta22 * dak2 - 0.5 * d2 - al3) * dd4
        um6 = t3 * a3 - e12 * v3 * v3
        um5 = t1 * a3 + a1 * t3 - e24 * v1 * v3
        um4 = t1 * a1 - e12 * v1 * v1
        al6 = e12 * p3 * p3
        al5 = e24 * p1 * p3 - b3 - b3 - ak2
        al4 = e12 * p1 * p1 - b1 - b1
        w56 = um5 * al6 - al5 * um6
        w46 = um4 * al6 - al4 * um6
        fa = -w46 / w56
        ca = -fa
        w[3] = fa
        w[2] = ca
        w[1] = b1 + b3 * fa
        w[0] = a1 + a3 * fa
        w[8] = v1 + v3 * fa
        w[14] = -(p1 + p3 * fa)
        w[15] = w[14]
        if abs(w[15]) < 1.0e-3:
            w[15] = 0.0
        w[10] = w[16]
    else:
        t2 = ta4 * a2 + ta5 * b2 + e12 * (ta1 * ck - ta2 * sk)
        t3 = (ta4 * a3 + ta5 * b3 + e12 * (ta1 * sk - ta2 * (ck - 1.0))
              - 4.0e-1 * reta * (reta + 1.0e1) - 1.0)
        # MU(i)
        um1 = t2 * a2 - e12 * v2 * v2
        um2 = t1 * a2 + t2 * a1 - e24 * v1 * v2
        um3 = t2 * a3 + t3 * a2 - e24 * v2 * v3
        um4 = t1 * a1 - e12 * v1 * v1
        um5 = t1 * a3 + t3 * a1 - e24 * v1 * v3
        um6 = t3 * a3 - e12 * v3 * v3

        if ix == 1 or ix == 3:
            # LAMBDA(I)
            al1 = e12 * p2 * p2
            al2 = e24 * p1 * p2 - b2 - b2
            al3 = e24 * p2 * p3
            al4 = e12 * p1 * p1 - b1 - b1
            al5 = e24 * p1 * p3 - b3 - b3 - ak2
            al6 = e12 * p3 * p3
            # OMEGA(I)
            w16 = um1 * al6 - al1 * um6
            w15 = um1 * al5 - al1 * um5
            w14 = um1 * al4 - al1 * um4
            w13 = um1 * al3 - al1 * um3
            w12 = um1 * al2 - al1 * um2
            w26 = um2 * al6 - al2 * um6
            w25 = um2 * al5 - al2 * um5
            w24 = um2 * al4 - al2 * um4
            w36 = um3 * al6 - al3 * um6
            w35 = um3 * al5 - al3 * um5
            w34 = um3 * al4 - al3 * um4
            w32 = um3 * al2 - al3 * um2
            w46 = um4 * al6 - al4 * um6
            w56 = um5 * al6 - al5 * um6
            w3526 = w35 + w26
            w3425 = w34 + w25
            # QUARTIK-KOEFFIZIENTEN [HP81 Gl. 8]
            w4 = w16 * w16 - w13 * w36
            w3 = 2.0 * w16 * w15 - w13 * w3526 - w12 * w36
            w2 = w15 * w15 + 2.0 * w16 * w14 - w13 * w3425 - w12 * w3526
            w1 = 2.0 * w15 * w14 - w13 * w24 - w12 * w3425
            w0 = w14 * w14 - w12 * w24
            # STARTWERT FÜR F
            if ix == 1:
                fap = (w14 - w34 - w46) / (w12 - w15 + w35 - w26 + w56 - w32)
            else:
                w[14] = 0.5 * eta2d * dd2 * math.exp(-rgek)
                if w[11] <= 2.0 and w[11] >= 0.0 and w[12] <= 1.0:
                    e24g = e24 * rgek * math.exp(rak)
                    pwk = math.sqrt(e24g)
                    qpw = (1.0 - math.sqrt(1.0 + 2.0 * d2 * d * pwk / eta22)) * eta21 / d
                    w[14] = -qpw * qpw / e24 + 0.5 * eta2d * dd2
                pg = p1 + w[14]
                ca = ak2 * pg + 2.0 * (b3 * pg - b1 * p3) + e12 * w[14] * w[14] * p3
                ca = -ca / (ak2 * p2 + 2.0 * (b3 * p2 - b2 * p3))
                fap = -(pg + p2 * ca) / p3
            # NEWTON-VERFEINERUNG
            ii = 0
            while True:
                ii += 1
                if ii > itm:
                    return -2
                fa = fap
                fun = w0 + (w1 + (w2 + (w3 + w4 * fa) * fa) * fa) * fa
                fund = w1 + (2.0 * w2 + (3.0 * w3 + 4.0 * w4 * fa) * fa) * fa
                fap = fa - fun / fund
                delta = abs((fap - fa) / fa)
                if not delta > acc:
                    break
            ir = ir + ii
            fa = fap
            ca = -(w16 * fa * fa + w15 * fa + w14) / (w13 * fa + w12)
            w[14] = -(p1 + p2 * ca + p3 * fa)
            w[15] = w[14]
            if abs(w[15]) < 1.0e-3:
                w[15] = 0.0
            w[10] = w[16]
        else:
            ca = ak2 * p1 + 2.0 * (b3 * p1 - b1 * p3)
            ca = -ca / (ak2 * p2 + 2.0 * (b3 * p2 - b2 * p3))
            fa = -(p1 + p2 * ca) / p3
            if ix == 2:
                w[15] = um1 * ca * ca + (um2 + um3 * fa) * ca + um4 + um5 * fa + um6 * fa * fa
            if ix == 4:
                w[15] = -(p1 + p2 * ca + p3 * fa)
        w[3] = fa
        w[2] = ca
        w[1] = b1 + b2 * ca + b3 * fa
        w[0] = a1 + a2 * ca + a3 * fa
        w[8] = (v1 + v2 * ca + v3 * fa) / w[0]
    g24 = e24 * rgek * ex1
    w[7] = (rak * ak2 * ca - g24) / (ak2 * g24)
    return ir


def _sqcoef(ir, w):
    """SQCOEF: reskalierte Packungsdichte (Gillan-Bedingung g(1+) = 0) und Koeffizienten."""
    itm = 40
    acc = 5.0e-6
    f1 = 0.0
    f2 = 0.0
    e2 = 0.0

    ig = 1
    if w[6] >= (1.0 + 8.0 * w[4]):
        ig = 0
        w[15] = w[14]
        w[16] = w[4]
        ir = _sqfun(1, ir, w)
        w[14] = w[15]
        w[4] = w[16]
        if ir < 0.0 or w[14] >= 0.0:
            return ir
    w[10] = min(w[4], 0.20)
    if ig != 1 or w[9] >= 0.15:
        ii = 0
        while True:
            ii += 1
            if ii > itm:
                return -1
            if w[10] <= 0.0:
                w[10] = w[4] / ii
            if w[10] > 0.6:
                w[10] = 0.35 / ii
            e1 = w[10]
            w[15] = f1
            w[16] = e1
            ir = _sqfun(2, ir, w)
            f1 = w[15]
            e1 = w[16]
            e2 = w[10] * 1.01
            w[15] = f2
            w[16] = e2
            ir = _sqfun(2, ir, w)
            f2 = w[15]
            e2 = w[16]
            e2 = e1 - (e2 - e1) * f1 / (f2 - f1)
            w[10] = e2
            delta = abs((e2 - e1) / e1)
            if not delta > acc:
                break
        w[15] = w[14]
        w[16] = e2
        ir = _sqfun(4, ir, w)
        w[14] = w[15]
        e2 = w[16]
        ir = ii
        if ig != 1 or w[10] >= w[4]:
            return ir
    w[15] = w[14]
    w[16] = w[4]
    ir = _sqfun(3, ir, w)
    w[14] = w[15]
    w[4] = w[16]
    if ir >= 0 and w[14] < 0.0:
        ir = -3
    return ir


def _sqhcal(qq, w):
    """SQHCAL: S(Q·σ) aus den Koeffizienten [HP81 Gl. 13/14], vektorisiert über qq."""
    qq = np.asarray(qq, dtype=float)
    etaz = w[10]
    akz = w[12]
    gekz = w[11]
    e24 = 24.0 * etaz
    x1 = math.exp(akz)
    x2 = math.exp(-akz) if w[12] < 20.0 else 0.0
    ck = 0.5 * (x1 + x2)
    sk = 0.5 * (x1 - x2)
    ak2 = akz * akz
    A, B, C, F = w[0], w[1], w[2], w[3]

    qk = qq / w[13]
    q2k = qk * qk
    out = np.empty_like(qk)

    zero = qk <= 1.0e-8
    out[zero] = -1.0 / A

    # Taylor-Entwicklung für kleine qk (sasmodels, RKH 2016)
    small = (~zero) & (qk <= 0.01)
    if small.any():
        q2 = q2k[small]
        aqk = (A * (8.0 + 2.0 * etaz) + 6 * B - 12.0 * F
               - 24 * (gekz * (1.0 + akz) - ck * akz * C + F * (ck - 1.0) + (C - F * akz) * sk) / ak2
               + q2 * (-(A * (48.0 + 15.0 * etaz) + 40.0 * B) / 60.0 + F
                       + (4.0 / ak2) * (gekz * (9.0 + 7.0 * akz) + ck * (9.0 * F - 7.0 * C * akz)
                                        + sk * (9.0 * C - 7.0 * F * akz))))
        out[small] = 1.0 / (1.0 - etaz * aqk)

    big = qk > 0.01
    if big.any():
        k = qk[big]
        k2 = q2k[big]
        qk2 = 1.0 / k2
        qk3 = qk2 / k
        qqk = 1.0 / (k * (k2 + ak2))
        sink = np.sin(k)
        cosk = np.cos(k)
        asink = akz * sink
        qcosk = k * cosk
        aqk = A * (sink - qcosk)
        aqk = aqk + B * ((2.0 * qk2 - 1.0) * qcosk + 2.0 * sink - 2.0 / k)
        inter = 24.0 * qk3 + 4.0 * (1.0 - 6.0 * qk2) * sink
        aqk = (aqk + 0.5 * etaz * A * (inter - (1.0 - 12.0 * qk2 + 24.0 * qk2 * qk2) * qcosk)) * qk3
        aqk = aqk + C * (ck * asink - sk * qcosk) * qqk
        aqk = aqk + F * (sk * asink - k * (ck * cosk - 1.0)) * qqk
        aqk = aqk + F * (cosk - 1.0) * qk2
        aqk = aqk - gekz * (asink + qcosk) * qqk
        out[big] = 1.0 / (1.0 - e24 * aqk)
    return out


def rmsa_coefficients(r_hs_nm, phi, charge, temperature, salt_molar, eps_r):
    """Dimensionslose Parameter und RMSA-Koeffizienten (Arbeitsvektor w).

    Args:
        r_hs_nm: Radius der harten Kugel (Wechselwirkungsradius) in nm
        phi: Volumenbruch
        charge: Ladung in Elementarladungen (Betrag)
        temperature: K
        salt_molar: Konzentration 1:1-Salz in mol/L (Gegenionen der Makroionen werden
            als einwertig zusätzlich berücksichtigt, wie in sasmodels)
        eps_r: relative Permittivität des Lösungsmittels

    Returns:
        (w, info) — info enthält κ, k = κσ, Debye-Länge, Kontaktpotential, g(σ+), s = σ'/σ

    Raises:
        RMSAError: wenn keine Lösung gefunden wird
    """
    zz = abs(float(charge))
    diam_m = 2.0 * float(r_hs_nm) * 1e-9
    beta = 1.0 / (K_BOLTZMANN * float(temperature))
    perm = float(eps_r) * EPS0
    q_e = zz * ELCHARGE
    vp = 4.0 / 3.0 * math.pi * (diam_m / 2.0) ** 3
    cs = float(salt_molar) * AVOGADRO * 1.0e3
    ion_st = 0.5 * ELCHARGE * ELCHARGE * (zz * float(phi) / vp + 2.0 * cs)
    kappa = math.sqrt(2 * beta * ion_st / perm)

    w = [float(i) for i in range(1, 18)]          # Initialisierung wie in sasmodels
    w[5] = beta * q_e * q_e / (math.pi * perm * diam_m * (2.0 + kappa * diam_m) ** 2)
    w[6] = kappa * diam_m
    w[4] = float(phi)
    ss = w[4] ** (1.0 / 3.0)
    w[9] = 2.0 * ss * w[5] * math.exp(w[6] - w[6] / ss)
    ir = _sqcoef(0, w)
    if ir < 0 or not all(math.isfinite(v) for v in w[:4]):
        raise RMSAError(f"RMSA-Lösung nicht gefunden (Fehlercode {ir})")
    info = {'kappa_nm-1': kappa * 1e-9, 'debye_length_nm': 1e9 / kappa if kappa > 0 else math.inf,
            'k': w[6], 'contact_potential_kT': w[5], 'coupling': w[9],
            'eta_rescaled': w[10], 'rescale_s': w[13], 'g_contact': w[14], 'iterations': ir}
    return w, info


def s_hayter_msa(q, r_hs, phi, charge, temperature=298.15, salt=0.01, eps_r=78.36):
    """RMSA-Strukturfaktor S(q) (q in nm⁻¹, R_HS in nm).

    Vektorisiert wie die übrigen Modelle: Parameter-Arrays der Länge K liefern (K × M).
    Parameter, für die keine Lösung existiert, ergeben NaN (→ MD = ∞ in GIFT).
    """
    q = np.asarray(q, dtype=float)
    params = [np.atleast_1d(np.asarray(v, dtype=float))
              for v in (r_hs, phi, charge, temperature, salt, eps_r)]
    scalar = all(np.ndim(v) == 0 for v in (r_hs, phi, charge, temperature, salt, eps_r))
    params = np.broadcast_arrays(*params)
    out = np.full((len(params[0]), len(q)), np.nan)
    for k in range(len(params[0])):
        r, ph, z, t, cs, er = (float(p[k]) for p in params)
        try:
            w, _ = rmsa_coefficients(r, ph, z, t, cs, er)
        except (RMSAError, ZeroDivisionError, ValueError, OverflowError):
            continue
        out[k] = _sqhcal(q * 2.0 * r, w)
    return out[0] if scalar else out


def dielectric_constant_water(temperature_k):
    """ε_r von Wasser (Malmberg & Maryott 1956), gültig 0–100 °C; wie in sasmodels dokumentiert."""
    t = float(temperature_k) - 273.15
    return 87.740 - 0.40008 * t + 9.398e-4 * t ** 2 - 1.410e-6 * t ** 3
