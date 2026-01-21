"""
F1 AI Strategy Platform - AI-powered Formula 1 race strategy system.

This package provides tools for analyzing F1 telemetry data, modeling tyre degradation,
predicting lap times, and optimizing race strategy.

Example:
    Basic usage::

        from src.data_loader import load_race_data
        from src.models.tyre_deg_model import fit_tyre_degradation

        # Load race data
        laps, results = load_race_data(2023, "Monza")

        # Analyze tyre degradation
        coeffs = fit_tyre_degradation(laps, "SOFT")
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"
__license__ = "MIT"

# Version info
VERSION = __version__
