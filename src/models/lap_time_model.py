"""
Lap time prediction model using Random Forest regression.

This module provides functionality to train a Random Forest model that predicts
F1 lap times based on telemetry features like lap number, tyre life, and compound.
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from typing import Tuple, Dict, List


def train_lap_time_model(X: pd.DataFrame, y: pd.Series) -> Tuple[RandomForestRegressor, float]:
    """
    Train a Random Forest model to predict lap times.

    Splits data into train/test sets, trains the model with optimized hyperparameters,
    and evaluates performance using Mean Absolute Error (MAE).

    Args:
        X (pd.DataFrame): Feature matrix with columns [LapNumber, TyreLife, Stint, CompoundEncoded]
        y (pd.Series): Target variable (normalized lap times in seconds)

    Returns:
        Tuple[RandomForestRegressor, float]: Trained model and MAE on test set

    Example:
        >>> model, mae = train_lap_time_model(X, y)
        >>> print(f"Test MAE: {mae:.2f} seconds")
        Test MAE: 1.11 seconds
    """
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Use tuned hyperparameters optimized for F1 telemetry data
    model = RandomForestRegressor(
        n_estimators=100,      # Number of trees
        max_depth=10,          # Maximum tree depth
        min_samples_split=2,   # Minimum samples to split
        random_state=42,       # Reproducibility
        n_jobs=-1              # Use all available cores
    )

    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)

    return model, mae


# --- Enhanced forecasting helpers ---

def train_explainable_model(X: pd.DataFrame, y: pd.Series) -> Dict[str, object]:
    """Train a RandomForest model and return feature importances and MAE."""
    model, mae = train_lap_time_model(X, y)
    importances = model.feature_importances_.tolist()
    return {"model": model, "mae": mae, "importances": importances}


def predict_future_laps(
    model: RandomForestRegressor,
    last_row: pd.Series,
    horizon: int = 5,
) -> List[Dict[str, float]]:
    """
    Predict lap times for the next N laps using incremental feature updates.

    Uses tyre age increments and fuel burn proxy (small negative trend per lap).
    Confidence intervals estimated from tree ensemble variance.
    """
    predictions: List[Dict[str, float]] = []
    features = last_row.copy()

    for step in range(1, horizon + 1):
        features["LapNumber"] += 1
        features["TyreLife"] += 1
        if "FuelLoadProxy" in features:
            features["FuelLoadProxy"] = max(0, features["FuelLoadProxy"] - 0.015)

        sample = pd.DataFrame([features])
        point_pred = float(model.predict(sample)[0])

        # Confidence via per-tree predictions
        tree_preds = np.array([est.predict(sample)[0] for est in model.estimators_])
        std = float(tree_preds.std()) if len(tree_preds) > 1 else 0.25
        interval = 1.64 * std  # ~90% interval

        predictions.append({
            "lap_ahead": step,
            "prediction": point_pred,
            "lower": point_pred - interval,
            "upper": point_pred + interval,
        })

    return predictions
