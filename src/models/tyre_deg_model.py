"""
Tyre degradation modeling using polynomial regression.

This module provides functions to fit quadratic degradation curves per tyre compound
and simulate how lap times worsen as tyre life increases across a race.
"""

import numpy as np
import pandas as pd
from typing import Callable, Optional


def fit_tyre_degradation(df: pd.DataFrame, compound: str, min_samples: int = 10) -> Optional[np.ndarray]:
    """
    Fit a quadratic degradation model for a specific tyre compound.

    Filters data to representative laps (removes safety car, VSC, pit in/out) and
    applies fuel correction to normalize lap times across different fuel loads.

    Args:
        df (pd.DataFrame): Input lap data with columns: Compound, TyreLife, LapTimeSeconds, 
                          LapNumber, IsAccurate
        compound (str): Tyre compound ("SOFT", "MEDIUM", "HARD", etc.)
        min_samples (int): Minimum laps required to fit model (default: 10)

    Returns:
        Optional[np.ndarray]: Polynomial coefficients [a, b, c] for f(x) = ax² + bx + c,
                             or None if insufficient data

    Example:
        >>> coeffs = fit_tyre_degradation(laps, "SOFT")
        >>> if coeffs is not None:
        ...     print(f"Quadratic coefficient: {coeffs[0]:.6f}")
    """
    data = df[df["Compound"] == compound].copy()

    # Require valid tyre life values
    data = data[data["TyreLife"] >= 1]

    # Filter out non-representative laps (Safety Car, VSC, Pit In/Out)
    if "IsAccurate" in data.columns:
        data = data[data["IsAccurate"] == True]

    if len(data) < min_samples:
        print(f"⚠️ Not enough data for {compound} (samples={len(data)})")
        return None

    x = data["TyreLife"].values
    # Convert LapTime timedelta to seconds
    y = data["LapTime"].dt.total_seconds().values

    # Basic Fuel Correction (~0.06s per lap of fuel)
    # Normalizes early heavy laps to be comparable with late light laps
    if "LapNumber" in data.columns:
        max_laps = df["LapNumber"].max()
        fuel_penalty = 0.06
        laps_remaining = max_laps - data["LapNumber"].values
        y = y - (laps_remaining * fuel_penalty)

    # Fit quadratic polynomial - degradation only (no negative coefficients)
    coeffs = np.polyfit(x, y, deg=2)
    
    # Ensure positive degradation (quadratic term should be positive)
    # This prevents unrealistic curves that improve then worsen
    if coeffs[0] < 0:
        # If degradation curve is inverted, force it to be positive
        coeffs[0] = abs(coeffs[0])
    
    return coeffs


def create_degradation_model(coeffs: np.ndarray) -> Callable[[float], float]:
    """
    Create a callable degradation model function from polynomial coefficients.

    Args:
        coeffs (np.ndarray): Polynomial coefficients [a, b, c] from polyfit

    Returns:
        Callable: Function that takes tyre_life and returns predicted lap time

    Example:
        >>> model = create_degradation_model(coeffs)
        >>> predicted_lap_time = model(15)  # Predict lap time at tyre age 15
        >>> print(f"Predicted time: {predicted_lap_time:.2f}s")
    """
    def model(tyre_life: float, compound: Optional[str] = None) -> float:
        """
        Evaluate degradation model at a given tyre life.

        Args:
            tyre_life (float): Tyre age in laps
            compound (Optional[str]): Tyre compound used for baseline speeds

        Returns:
            float: Predicted lap time in seconds
        """
        # Model: f(x) = ax^2 + bx + c
        raw_time = coeffs[0] * (tyre_life**2) + coeffs[1] * tyre_life + coeffs[2]

        # Apply realistic baseline offsets so SOFT < MEDIUM < HARD
        # These represent real F1 tyre speed differences
        offset_map = {
            "SOFT": -1.2,    # Fastest (peak grip)
            "MEDIUM": -0.4,  # Mid-range
            "HARD": 0.4,     # Slowest (conservative grip)
            "C4": -1.2,      # Soft equivalent
            "C3": -0.4,      # Medium equivalent
            "C2": 0.4,       # Hard equivalent
            "C1": 0.8,       # Harder still
        }
        offset = offset_map.get(str(compound).upper(), 0.0) if compound else 0.0
        return raw_time + offset

    return model


# --- Driver-specific extensions ---

def fit_driver_tyre_degradation(
    df: pd.DataFrame,
    driver: str,
    compound: str,
    min_samples: int = 6,
) -> Optional[np.ndarray]:
    """
    Fit a degradation curve for a single driver/compound pair.

    Applies the same filtering logic as `fit_tyre_degradation` but scoped to a driver.
    Returns polynomial coefficients or None if insufficient data.
    """
    subset = df[(df["Driver"] == driver) & (df["Compound"] == compound)].copy()
    if "LapTimeSeconds" not in subset.columns and "LapTime" in subset.columns:
        subset["LapTimeSeconds"] = subset["LapTime"].dt.total_seconds()

    if len(subset) < min_samples:
        return None

    subset = subset[subset["TyreLife"] >= 1]
    if "IsAccurate" in subset.columns:
        subset = subset[subset["IsAccurate"] == True]

    if len(subset) < min_samples:
        return None

    x = subset["TyreLife"].values
    y = subset["LapTimeSeconds"].values
    coeffs = np.polyfit(x, y, deg=2)
    return coeffs


def classify_driver_style(deg_coeff: np.ndarray) -> str:
    """Classify driver tyre management style using quadratic slope."""
    if deg_coeff is None or len(deg_coeff) < 2:
        return "Unknown"

    slope = deg_coeff[1]
    if slope >= 0.12:
        return "Aggressive"
    if slope <= 0.05:
        return "Conservative"
    return "Balanced"


def build_driver_degradation_profiles(df: pd.DataFrame) -> dict:
    """Generate per-driver degradation coefficients and style labels."""
    if "LapTimeSeconds" not in df.columns and "LapTime" in df.columns:
        df = df.copy()
        df["LapTimeSeconds"] = df["LapTime"].dt.total_seconds()

    drivers = df["Driver"].dropna().unique().tolist()
    compounds = df["Compound"].dropna().unique().tolist()

    profiles = {}
    for driver in drivers:
        profile = {"compounds": {}, "style": "Unknown"}
        slopes = []
        for compound in compounds:
            coeffs = fit_driver_tyre_degradation(df, driver, compound)
            if coeffs is not None:
                profile["compounds"][compound] = coeffs.tolist()
                slopes.append(coeffs[1])

        if slopes:
            avg_slope = float(np.mean(slopes))
            profile["style"] = classify_driver_style(np.array([0, avg_slope, 0]))
        profiles[driver] = profile

    return profiles
