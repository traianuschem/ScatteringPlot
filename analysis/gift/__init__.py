"""
IFT/GIFT-Modul (GUI-frei).

- IFT nach Glatter (1977) mit Flags und Provenance-Sidecar (0.1)
- GIFT mit Hard-Sphere-Strukturfaktoren (PY, gemittelt S_ave) und BSSA-Optimierung
  nach Brunner-Popela & Glatter (1997) / Bergmann et al. (2000) (0.2)
- GIFT für geladene Kugeln: RMSA nach Hayter & Penfold (1981) / Hansen & Hayter (1982),
  Portierung aus sasmodels (BSD-3, siehe rmsa.py), BSSA-Mehrfachstart (0.3)
- Prozess-Pool für parallele BSSA-Starts (bitgleich unabhängig von der Worker-Zahl),
  vektorisierte Batch-Likelihood (0.4)
DREAM folgt (siehe GIFT/PLAN.md).
"""

__version__ = "0.4.0"
