"""
Data loading module for Formula 1 telemetry data using FastF1.

This module provides functions to load and cache F1 race telemetry data
from the FastF1 API, including lap times, tyre information, and driver details.
"""

import fastf1
import pandas as pd
from pathlib import Path
from typing import Tuple

# Use absolute path for cache
cache_dir = Path(__file__).parent.parent / "data" / "raw"
fastf1.Cache.enable_cache(str(cache_dir))


def load_race_data(year: int, gp: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load race telemetry data for a specific Grand Prix.

    Args:
        year (int): Calendar year of the race (e.g., 2023, 2025)
        gp (str): Grand Prix name (e.g., "Monza", "Monaco")

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: Tuple containing:
            - laps: DataFrame with lap times, tyre data, and driver info
            - results: DataFrame with final race results

    Raises:
        fastf1.core.SessionNotAvailableError: If the session data is not available
        Exception: For other data loading errors

    Example:
        >>> laps, results = load_race_data(2023, "Monza")
        >>> print(laps.shape)
        (300, 8)
    """
    session = fastf1.get_session(year, gp, 'R')
    session.load()

    laps = session.laps
    laps = laps[[
        'Driver', 'Team', 'LapTime', 'LapNumber',
        'Compound', 'TyreLife',
        'Stint', 'IsAccurate', 'IsPersonalBest'
    ]]

    # Filter for accurate laps only and remove NaN values
    laps = laps[laps['IsAccurate'] == True].copy()
    laps = laps.dropna(subset=['LapTime', 'Driver'])
    # Keep lap count in results to derive total race distance
    keep_cols = [c for c in ['Abbreviation', 'TeamName', 'Laps', 'Position'] if c in session.results.columns]
    results = session.results[keep_cols].dropna(subset=['Abbreviation']) if keep_cols else session.results
    return laps, results


def load_multiple_races(year: int, gps: list) -> None:
    """
    Load and cache data for multiple Grand Prix races in a given year.

    This function iterates through a list of Grand Prix events and loads
    their telemetry data, caching it locally for future use. Failures are
    logged but do not interrupt the loading process.

    Args:
        year (int): Calendar year of the races
        gps (list): List of Grand Prix names to load

    Returns:
        None

    Example:
        >>> load_multiple_races(2023, ["Monza", "Spa", "Monaco"])
        Loading data for 2023 Monza...
        Successfully loaded Monza
        ...
    """
    for gp in gps:
        print(f"Loading data for {year} {gp}...")
        try:
            session = fastf1.get_session(year, gp, 'R')
            session.load()
            print(f"Successfully loaded {gp}")
        except Exception as e:
            print(f"Failed to load {gp}: {e}")
    print("All races loaded.")
