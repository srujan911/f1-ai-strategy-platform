"""
Prediction module for F1 strategy platform.

This module contains functions for predicting future season strategies,
degradation trends, and pit timing windows.
"""

from src.prediction._2026_strategy import (
    predict_team_strategies,
    predict_degradation_trends,
    predict_pit_timing_windows
)

__all__ = [
    "predict_team_strategies",
    "predict_degradation_trends",
    "predict_pit_timing_windows"
]
