"""
IFT/GIFT-Modul (GUI-frei).

- IFT nach Glatter (1977) mit Flags und Provenance-Sidecar (0.1)
- GIFT mit Hard-Sphere-Strukturfaktoren (PY, gemittelt S_ave) und BSSA-Optimierung
  nach Brunner-Popela & Glatter (1997) / Bergmann et al. (2000) (0.2)
- GIFT für geladene Kugeln: RMSA nach Hayter & Penfold (1981) / Hansen & Hayter (1982),
  Portierung aus sasmodels (BSD-3, siehe rmsa.py), BSSA-Mehrfachstart (0.3)
- Prozess-Pool für parallele BSSA-Starts (bitgleich unabhängig von der Worker-Zahl),
  vektorisierte Batch-Likelihood (0.4)
- Statistische Absicherung: marginale Likelihood (Hansen 2000), LHS-Screening und
  DREAM(ZS) über S(q)-Parameter, log λ und Dmax; Posterior-Bänder (0.5)
- Explorer (Kennzahlen SasView-kompatibel, Dmax × λ-Karte, 1D-Scans, Dmax-Vorschlag),
  Evidenz-λ, Artefakterkennung bei kleinem q, SVD-Zerlegung, Serienauswertung (0.6)
- Weitere Strukturfaktoren: S_eff nach Vrij (Schulz), klebrige harte Kugeln, fraktales
  Aggregat, Stäbchen (Mean-Field) (0.7)
- IFT-Arten: Querschnitt p_c(r), Dicke p_t(r), Größenverteilungen D_V(R) für Kugeln,
  Zylinder, Lamellen (Glatter 1980a/b); DECON-Kontrastprofil (Glatter 1981) (0.8)
"""

__version__ = "0.8.0"
