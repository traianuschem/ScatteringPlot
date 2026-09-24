"""
Verschmierungs-Operatoren (T2–T4 nach Glatter 1977).

Für Pinhole-Kollimation ist der Operator die Identität. Die Schnittstelle erlaubt es,
später Spalt- oder Wellenlängenverschmierung als lineare Abbildung auf die
transformierten Splines zu ergänzen: A_smeared = S · A.
"""

import numpy as np


class IdentitySmearing:
    """Punktkollimation: keine Verschmierung."""

    name = 'pinhole'

    def apply(self, A):
        return np.asarray(A)

    def to_dict(self):
        return {'type': self.name}
