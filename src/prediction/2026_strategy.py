import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from src.data_loader import load_race_data
from src.models.tyre_deg_model import fit_tyre_degradation, create_degradation_model
from src.strategy.pit_strategy import optimize_pit_strategy, simulate_race_strategy
from src.analysis.multi_race_analysis import TRACK_NAMES, YEARS

# 2026 Regulation Adjustments
REG_2026_LAP_TIME_REDUCTION = 0.08  # 8% faster lap times due to new power units and aero
REG_2026_DEG_SCALING = 0.9  # 10% less degradation due to improved tyres and cars
SAFETY_CAR_PROBABILITY = 0.3  # 30% chance of safety car per race
SAFETY_CAR_FREE_PIT = True  # Safety car allows free pit stops

TOP_TEAMS = ["Mercedes", "Red Bull Racing", "Ferrari", "McLaren", "Aston Martin", "Alpine", "Williams", "Haas"]

def adjust_model_for_2026(coeffs: np.ndarray) -> np.ndarray:
    """
    Adjust historical degradation coefficients for 2026 regulations.
    """
    # Scale degradation (reduce by REG_2026_DEG_SCALING)
    adjusted = coeffs * np.array([REG_2026_DEG_SCALING, REG_2026_DEG_SCALING, 1.0])
    # Reduce base lap time (constant term)
    adjusted[2] *= (1 - REG_2026_LAP_TIME_REDUCTION)
    return adjusted

def predict_2026_degradation_models(track: str) -> Dict[str, callable]:
    """
    Predict 2026 degradation models for a track based on historical data.
    """
    models = {}
    compounds = ["SOFT", "MEDIUM", "HARD"]

    # Use average from recent years
    for compound in compounds:
        coeffs_list = []
        for year in YEARS[-3:]:  # Last 3 years
            try:
                df, _ = load_race_data(year, track)
                coeffs = fit_tyre_degradation(df, compound)
                if coeffs is not None:
                    coeffs_list.append(coeffs)
            except:
                pass

        if coeffs_list:
            avg_coeffs = np.mean(coeffs_list, axis=0)
            adjusted_coeffs = adjust_model_for_2026(avg_coeffs)
            models[compound] = create_degradation_model(adjusted_coeffs)

    return models

def simulate_safety_car_benefit(strategy: dict, total_laps: int, safety_car_lap: int = None) -> dict:
    """
    Simulate safety car benefit: free pit stop if pitting during SC.
    """
    if safety_car_lap and safety_car_lap in strategy['pits']:
        # Remove pit loss for the SC pit
        idx = strategy['pits'].index(safety_car_lap)
        strategy = strategy.copy()
        strategy['total_time'] -= 22.0  # Remove pit loss
    return strategy

def predict_team_strategies(track: str) -> Dict[str, dict]:
    """
    Predict optimal strategies for top teams in 2026 for a given track.
    """
    strategies = {}

    # Get historical race data for lap count
    try:
        df, _ = load_race_data(2023, track)  # Use 2023 as base
        total_laps = int(df['LapNumber'].max())
    except:
        total_laps = 60  # Default

    deg_models = predict_2026_degradation_models(track)

    if not deg_models:
        return {}

    for team in TOP_TEAMS:
        # Assume teams have similar starting compounds based on historical patterns
        starting_compound = "MEDIUM"  # Default

        base_strategy = optimize_pit_strategy(
            total_laps=total_laps,
            degradation_models=deg_models,
            starting_compound=starting_compound,
            available_compounds=list(deg_models.keys())
        )

        # Simulate with safety car benefit (assume SC at lap 30 if probability met)
        if np.random.random() < SAFETY_CAR_PROBABILITY:
            safety_car_lap = 30  # Assume mid-race
            strategy_with_sc = simulate_safety_car_benefit(base_strategy, total_laps, safety_car_lap)
            strategies[team] = {
                'strategy': strategy_with_sc,
                'safety_car_used': True,
                'safety_car_lap': safety_car_lap
            }
        else:
            strategies[team] = {
                'strategy': base_strategy,
                'safety_car_used': False
            }

    return strategies

def get_all_tracks_predictions() -> Dict[str, Dict[str, dict]]:
    """
    Get predictions for all tracks.
    """
    all_predictions = {}
    for track in TRACK_NAMES:
        predictions = predict_team_strategies(track)
        if predictions:
            all_predictions[track] = predictions
    return all_predictions
