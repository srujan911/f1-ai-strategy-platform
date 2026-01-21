"""
Unit tests for F1 AI Strategy Platform modules.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import timedelta

# Test imports
from src.feature_engineering import add_driver_normalization, preprocess_laps, COMPOUND_MAP
from src.models.tyre_deg_model import fit_tyre_degradation, create_degradation_model
from src.models.lap_time_model import train_lap_time_model
from src.strategy.pit_strategy import should_pit, simulate_race_strategy


@pytest.fixture
def sample_race_data():
    """Create sample F1 telemetry data for testing."""
    np.random.seed(42)
    data = {
        'Driver': ['VER', 'HAM', 'LEC'] * 10,
        'Team': ['Red Bull', 'Mercedes', 'Ferrari'] * 10,
        'LapTime': [timedelta(seconds=85 + np.random.normal(0, 1)) for _ in range(30)],
        'LapNumber': list(range(1, 11)) * 3,
        'Compound': ['SOFT'] * 10 + ['MEDIUM'] * 10 + ['HARD'] * 10,
        'TyreLife': [i % 10 + 1 for i in range(30)],
        'Stint': [1] * 10 + [2] * 10 + [3] * 10,
        'IsAccurate': [True] * 30
    }
    return pd.DataFrame(data)


class TestFeatureEngineering:
    """Tests for feature engineering module."""

    def test_add_driver_normalization(self, sample_race_data):
        """Test driver normalization produces centered distributions."""
        df = add_driver_normalization(sample_race_data)
        
        # Check new columns exist
        assert 'LapTimeSeconds' in df.columns
        assert 'NormalizedLapTime' in df.columns
        
        # Check normalization works (mean should be near 0 for each driver)
        for driver in df['Driver'].unique():
            driver_data = df[df['Driver'] == driver]
            mean_normalized = driver_data['NormalizedLapTime'].mean()
            assert abs(mean_normalized) < 0.1  # Allow small numerical error

    def test_preprocess_laps(self, sample_race_data):
        """Test lap preprocessing produces valid features and targets."""
        X, y = preprocess_laps(sample_race_data)
        
        # Check shapes match
        assert len(X) == len(y)
        assert len(X) > 0
        
        # Check expected features
        expected_features = {'LapNumber', 'TyreLife', 'Stint', 'CompoundEncoded'}
        assert set(X.columns) == expected_features
        
        # Check no NaN values remain
        assert not X.isna().any().any()
        assert not y.isna().any()

    def test_compound_map(self):
        """Test that compound mapping is complete."""
        compounds = ["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"]
        for i, compound in enumerate(compounds):
            assert compound in COMPOUND_MAP
            assert COMPOUND_MAP[compound] == i


class TestTyreDegradationModel:
    """Tests for tyre degradation modeling."""

    def test_fit_tyre_degradation(self, sample_race_data):
        """Test fitting degradation model."""
        df = add_driver_normalization(sample_race_data)
        df['LapTimeSeconds'] = df['LapTime'].dt.total_seconds()
        
        coeffs = fit_tyre_degradation(df, "SOFT", min_samples=5)
        
        # Should return 3 coefficients for quadratic
        assert coeffs is not None
        assert len(coeffs) == 3

    def test_fit_insufficient_data(self, sample_race_data):
        """Test that insufficient data returns None."""
        df = add_driver_normalization(sample_race_data)
        df['LapTimeSeconds'] = df['LapTime'].dt.total_seconds()
        
        # Request a compound with very few samples
        coeffs = fit_tyre_degradation(df, "WET", min_samples=100)
        assert coeffs is None

    def test_create_degradation_model(self):
        """Test creating and using degradation model."""
        coeffs = np.array([0.01, 0.5, 85.0])  # Simple quadratic
        model = create_degradation_model(coeffs)
        
        # Test model evaluation
        result_5 = model(5)
        result_10 = model(10)
        
        # Model should increase with tyre life (positive quadratic coeff)
        assert result_10 > result_5


class TestLapTimeModel:
    """Tests for lap time prediction model."""

    def test_train_lap_time_model(self, sample_race_data):
        """Test training a lap time prediction model."""
        X, y = preprocess_laps(sample_race_data)
        
        if len(X) < 10:  # Need minimum samples for train/test split
            pytest.skip("Insufficient samples for training")
        
        model, mae = train_lap_time_model(X, y)
        
        # Check model is trained
        assert model is not None
        assert mae >= 0
        
        # Check can make predictions
        predictions = model.predict(X.iloc[:5])
        assert len(predictions) == 5


class TestPitStrategy:
    """Tests for pit strategy optimization."""

    def test_should_pit_true(self):
        """Test pit decision when pitting is beneficial."""
        result = should_pit(
            current_lap_time=85.0,
            predicted_next_lap=92.0,  # Large degradation
            pit_loss_seconds=22.0,
            lookahead_laps=5
        )
        # 7 seconds * 5 laps = 35 seconds > 22 pit loss
        assert result is True

    def test_should_pit_false(self):
        """Test pit decision when pitting is not beneficial."""
        result = should_pit(
            current_lap_time=85.0,
            predicted_next_lap=86.0,  # Small degradation
            pit_loss_seconds=22.0,
            lookahead_laps=5
        )
        # 1 second * 5 laps = 5 seconds < 22 pit loss
        assert result is False

    def test_simulate_race_no_stops(self):
        """Test simulating a race with no pit stops."""
        def simple_degradation(tyre_life, compound):
            return 0.1 * tyre_life  # Linear degradation
        
        pit_strategy = {
            "pits": [],
            "compounds": ["MEDIUM"],
            "pit_loss": 22.0
        }
        
        lap_times = simulate_race_strategy(
            total_laps=10,
            pit_strategy=pit_strategy,
            degradation_model=simple_degradation
        )
        
        assert len(lap_times) == 10
        # Times should increase (degradation)
        assert lap_times[-1] > lap_times[0]

    def test_simulate_race_with_stops(self):
        """Test simulating a race with pit stops."""
        def simple_degradation(tyre_life, compound):
            return 0.1 * tyre_life
        
        pit_strategy = {
            "pits": [5],
            "compounds": ["SOFT", "HARD"],
            "pit_loss": 22.0
        }
        
        lap_times = simulate_race_strategy(
            total_laps=10,
            pit_strategy=pit_strategy,
            degradation_model=simple_degradation
        )
        
        assert len(lap_times) == 10
        # Pit lap (5) should have large time penalty
        assert lap_times[4] > lap_times[0]  # pit_loss dominates


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
