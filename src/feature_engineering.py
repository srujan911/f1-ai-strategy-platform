"""
Feature engineering module for F1 telemetry data processing.

This module provides utilities for preprocessing F1 race telemetry data,
including driver normalization, encoding, and feature extraction for
machine learning models.
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple

COMPOUND_MAP: Dict[str, int] = {
    "SOFT": 0,
    "MEDIUM": 1,
    "HARD": 2,
    "INTERMEDIATE": 3,
    "WET": 4
}


def add_driver_normalization(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add driver-normalized lap times to remove driver-specific performance variations.

    Calculates the mean lap time for each driver and subtracts it from individual
    lap times. This helps the model focus on tyre degradation effects rather than
    driver performance differences.

    Args:
        df (pd.DataFrame): Input DataFrame with 'Driver' and 'LapTime' columns

    Returns:
        pd.DataFrame: DataFrame with added 'LapTimeSeconds' and 'NormalizedLapTime' columns

    Example:
        >>> df = add_driver_normalization(laps)
        >>> print(df[['Driver', 'NormalizedLapTime']].head())
    """
    df = df.copy()

    df["LapTimeSeconds"] = df["LapTime"].dt.total_seconds()

    driver_mean = df.groupby("Driver")["LapTimeSeconds"].transform("mean")
    df["NormalizedLapTime"] = df["LapTimeSeconds"] - driver_mean

    return df


def preprocess_laps(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Preprocess lap data for machine learning model training.

    Applies driver normalization, encodes tyre compounds, and removes incomplete
    records. Returns features and target variables ready for model training.

    Args:
        df (pd.DataFrame): Input DataFrame with lap and tyre information

    Returns:
        Tuple[pd.DataFrame, pd.Series]: Features and target (normalized lap times)

    Raises:
        ValueError: If required columns are missing from input DataFrame

    Example:
        >>> X, y = preprocess_laps(laps)
        >>> print(f"Features shape: {X.shape}, Target shape: {y.shape}")
        Features shape: (300, 4), Target shape: (300,)
    """
    df = df.copy()

    df = add_driver_normalization(df)

    df["CompoundEncoded"] = df["Compound"].map(COMPOUND_MAP)

    df = df.dropna(subset=["CompoundEncoded", "NormalizedLapTime"])

    features = df[
        ["LapNumber", "TyreLife", "Stint", "CompoundEncoded"]
    ]

    target = df["NormalizedLapTime"]

    return features, target
