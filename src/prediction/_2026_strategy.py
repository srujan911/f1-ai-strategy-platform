"""
Seasonal strategy predictions for the 2026 F1 season.

This module provides functions to predict team strategies and performance
for the upcoming F1 season based on historical data and trends.
"""

from typing import Dict, List, Tuple


def predict_team_strategies(
    season: int = 2026,
    num_races: int = 24
) -> Dict[str, Dict]:
    """
    Predict team strategies for the upcoming F1 season.

    Analyzes historical strategy patterns and predicts likely pit stop
    strategies for each team based on circuit characteristics and
    team performance trends.

    Args:
        season (int): F1 season year (default: 2026)
        num_races (int): Number of races in the season (default: 24)

    Returns:
        Dict[str, Dict]: Dictionary mapping team names to predicted strategies,
                        each containing:
                        - "avg_pit_stops": Average number of pit stops
                        - "preferred_compounds": List of favored compounds
                        - "aggressive_score": Strategy aggressiveness (0-10)

    Example:
        >>> strategies = predict_team_strategies(2026)
        >>> print(strategies['Red Bull']['avg_pit_stops'])
        1.8
    """
    # Placeholder predictions based on 2025 trends
    team_strategies = {
        "Red Bull Racing": {
            "avg_pit_stops": 1.8,
            "preferred_compounds": ["SOFT", "HARD"],
            "aggressive_score": 8,
            "reasoning": "Historically aggressive with two-stop strategies"
        },
        "Mercedes": {
            "avg_pit_stops": 2.1,
            "preferred_compounds": ["MEDIUM", "HARD"],
            "aggressive_score": 6,
            "reasoning": "Balanced approach with reliability focus"
        },
        "Ferrari": {
            "avg_pit_stops": 2.2,
            "preferred_compounds": ["SOFT", "MEDIUM"],
            "aggressive_score": 7,
            "reasoning": "Performance-oriented with medium-length stints"
        },
        "McLaren": {
            "avg_pit_stops": 1.9,
            "preferred_compounds": ["HARD", "SOFT"],
            "aggressive_score": 7,
            "reasoning": "Competitive with varied strategy approaches"
        },
        "Aston Martin": {
            "avg_pit_stops": 2.0,
            "preferred_compounds": ["MEDIUM", "SOFT"],
            "aggressive_score": 6,
            "reasoning": "Conservative-aggressive balance"
        },
        "Alpine": {
            "avg_pit_stops": 2.2,
            "preferred_compounds": ["SOFT", "MEDIUM"],
            "aggressive_score": 5,
            "reasoning": "Midfield aggressiveness with undercut attempts"
        },
        "Williams": {
            "avg_pit_stops": 2.3,
            "preferred_compounds": ["MEDIUM", "HARD"],
            "aggressive_score": 5,
            "reasoning": "Tends toward longer first stints"
        },
        "Racing Bulls": {
            "avg_pit_stops": 2.1,
            "preferred_compounds": ["SOFT", "MEDIUM"],
            "aggressive_score": 6,
            "reasoning": "Opportunistic with safety-car windows"
        },
        "Stake Sauber": {
            "avg_pit_stops": 2.3,
            "preferred_compounds": ["MEDIUM", "HARD"],
            "aggressive_score": 4,
            "reasoning": "Conservative tyre management"
        },
        "Haas": {
            "avg_pit_stops": 2.4,
            "preferred_compounds": ["MEDIUM", "HARD"],
            "aggressive_score": 4,
            "reasoning": "Often extends stints to reduce stops"
        }
    }

    return team_strategies


def predict_degradation_trends(season: int = 2026) -> Dict[str, float]:
    """
    Predict tyre degradation trends for the 2026 season.

    Estimates how tyre degradation patterns may change based on
    regulation updates and track modifications.

    Args:
        season (int): F1 season year (default: 2026)

    Returns:
        Dict[str, float]: Degradation multipliers by compound
                         (1.0 = baseline, >1.0 = increased wear)

    Example:
        >>> trends = predict_degradation_trends()
        >>> print(f"SOFT degradation: {trends['SOFT']}")
        SOFT degradation: 1.05
    """
    return {
        "SOFT": 1.05,      # Slightly increased degradation
        "MEDIUM": 1.02,    # Minimal change
        "HARD": 1.00,      # Baseline
        "INTERMEDIATE": 0.98,  # Improved performance
        "WET": 0.95        # Better wet performance
    }


def predict_pit_timing_windows(circuit_name: str) -> Dict[str, int]:
    """
    Predict optimal pit timing windows for a specific circuit.

    Provides expected lap ranges where pit stops are typically executed
    based on historical data and circuit characteristics.

    Args:
        circuit_name (str): Name of the F1 circuit (e.g., "Monza", "Monaco")

    Returns:
        Dict[str, int]: Pit timing windows with keys:
                       - "first_pit_window_start": Lap number
                       - "first_pit_window_end": Lap number
                       - "second_pit_window_start": Lap number
                       - "second_pit_window_end": Lap number

    Example:
        >>> windows = predict_pit_timing_windows("Monza")
        >>> print(windows['first_pit_window_start'])
        15
    """
    # Circuit-specific pit window predictions
    circuit_windows = {
        "Monza": {
            "first_pit_window_start": 15,
            "first_pit_window_end": 22,
            "second_pit_window_start": 38,
            "second_pit_window_end": 45,
        },
        "Monaco": {
            "first_pit_window_start": 20,
            "first_pit_window_end": 28,
            "second_pit_window_start": 45,
            "second_pit_window_end": 52,
        },
        "Spa": {
            "first_pit_window_start": 10,
            "first_pit_window_end": 18,
            "second_pit_window_start": 30,
            "second_pit_window_end": 40,
        },
        "Bahrain": {
            "first_pit_window_start": 14,
            "first_pit_window_end": 22,
            "second_pit_window_start": 36,
            "second_pit_window_end": 45,
        }
    }

    # Return circuit-specific or generic windows
    if circuit_name in circuit_windows:
        return circuit_windows[circuit_name]
    else:
        # Generic fallback
        return {
            "first_pit_window_start": 15,
            "first_pit_window_end": 25,
            "second_pit_window_start": 35,
            "second_pit_window_end": 50,
        }
