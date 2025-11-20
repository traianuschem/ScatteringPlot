"""
Constants for TUBAF Scattering Plot Tool

This module contains application-wide constants such as plot types
and their configurations.
"""

# Plot-Typen mit Achsenbeschriftungen und Skalierung
PLOT_TYPES = {
    'Log-Log': {
        'xlabel': 'q / nm⁻¹',
        'ylabel': 'I / a.u.',
        'xscale': 'log',
        'yscale': 'log'
    },
    'Porod': {
        'xlabel': 'q / nm⁻¹',
        'ylabel': 'I·q⁴ / a.u.·nm⁻⁴',
        'xscale': 'log',
        'yscale': 'log'
    },
    'Kratky': {
        'xlabel': 'q / nm⁻¹',
        'ylabel': 'I·q² / a.u.·nm⁻²',
        'xscale': 'linear',
        'yscale': 'linear'
    },
    'Guinier': {
        'xlabel': 'q² / nm⁻²',
        'ylabel': 'ln(I)',
        'xscale': 'linear',
        'yscale': 'linear'
    },
    'Bragg Spacing': {
        'xlabel': 'd / nm',
        'ylabel': 'I / a.u.',
        'xscale': 'log',
        'yscale': 'log'
    },
    '2-Theta': {
        'xlabel': '2θ / °',
        'ylabel': 'I / a.u.',
        'xscale': 'linear',
        'yscale': 'log'
    },
    'PDDF': {
        'xlabel': 'q / nm⁻¹',
        'ylabel': 'I / a.u.',
        'xscale': 'log',
        'yscale': 'log'
    }
}
