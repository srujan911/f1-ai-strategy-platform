"""
ML models module for F1 strategy platform.

This module contains trained models for predicting lap times and
tyre degradation patterns.
"""

from src.models.lap_time_model import train_lap_time_model
from src.models.tyre_deg_model import create_degradation_model, fit_tyre_degradation

__all__ = ["train_lap_time_model", "fit_tyre_degradation", "create_degradation_model"]
