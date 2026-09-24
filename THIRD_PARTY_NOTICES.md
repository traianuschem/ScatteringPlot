# Third-Party Notices

ScatterForge Plot steht unter der GPL-3.0 (siehe `LICENSE`). Folgende Bestandteile
stammen aus Projekten mit anderer, GPL-kompatibler Lizenz:

## sasmodels — Hayter-Penfold-RMSA-Strukturfaktor und klebrige harte Kugeln

- **Dateien:** `analysis/gift/rmsa.py`; Funktion `s_sticky` in `analysis/gift/sf_models.py`
- **Herkunft:** Python-Portierungen von `sasmodels/models/hayter_msa.c` (geht auf die
  Fortran-Routinen von J. B. Hayter, ILL, 1981 zurück) und
  `sasmodels/models/stickyhardsphere.c` (sasmodels 1.0.12,
  https://github.com/SasView/sasmodels). Das fraktale S(q) (`s_fractal`) folgt derselben
  Formel wie `sasmodels/models/lib/fractal_sq.c` (Teixeira 1988, Gl. 15), ist aber
  eigenständig implementiert.
- **Lizenz:** BSD-3-Clause

```
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
```
