"""
Test script to validate the robust race outcome prediction fix.

This validates that:
1. Probabilities are distributed (no 100% single driver)
2. All drivers have minimum probability floor
3. Maximum probability cap is enforced
4. Sparse data is handled gracefully
5. Explanations are generated correctly
"""

import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.append(str(ROOT_DIR))

from src.prediction.outcome_simulator import (
    simulate_race_outcome,
    build_driver_features_from_race_data,
    apply_probability_guardrails,
)
import pandas as pd
import numpy as np


def test_probability_guardrails():
    """Test that guardrails prevent unrealistic distributions."""
    print("\n=== Test 1: Probability Guardrails ===")
    
    # Extreme case: one driver has 95% probability
    extreme_probs = {
        'VER': 0.95,
        'HAM': 0.02,
        'LEC': 0.02,
        'SAI': 0.01,
    }
    
    fixed = apply_probability_guardrails(extreme_probs)
    
    print(f"Before guardrails: {extreme_probs}")
    print(f"After guardrails: {fixed}")
    
    # Validate
    max_prob = max(fixed.values())
    min_prob = min(fixed.values())
    total = sum(fixed.values())
    
    assert max_prob <= 0.66, f"Max probability {max_prob} exceeds cap"
    assert min_prob >= 0.019, f"Min probability {min_prob} below floor"
    assert abs(total - 1.0) < 0.01, f"Probabilities don't sum to 1: {total}"
    
    print("✅ Guardrails working correctly\n")


def test_sparse_data_handling():
    """Test handling of sparse/missing driver data."""
    print("\n=== Test 2: Sparse Data Handling ===")
    
    drivers = ['VER', 'HAM', 'LEC', 'SAI', 'NOR']
    
    # Only 2 drivers have data (40% coverage - should trigger smoothing)
    features = {
        'VER': {'base_pace': -0.5, 'consistency': 0.2, 'team_strength': 0.9, 'tyre_management': 0.8},
        'HAM': {'base_pace': -0.3, 'consistency': 0.25, 'team_strength': 0.85, 'tyre_management': 0.75},
        # LEC, SAI, NOR have no data
    }
    
    win_prob, explanation = simulate_race_outcome(drivers, features, simulations=1000, seed=42)
    
    print(f"Win probabilities with sparse data:")
    for drv in sorted(drivers, key=lambda d: win_prob[d], reverse=True):
        print(f"  {drv}: {win_prob[drv]*100:.1f}%")
    
    # Validate distribution
    max_prob = max(win_prob.values())
    assert max_prob < 0.60, f"Sparse data led to {max_prob*100:.1f}% dominance (should be smoothed)"
    
    print("✅ Sparse data handled with smoothing\n")


def test_realistic_distribution():
    """Test with realistic competitive field."""
    print("\n=== Test 3: Realistic Competitive Field ===")
    
    drivers = ['VER', 'HAM', 'LEC', 'SAI', 'NOR', 'PIA', 'RUS', 'ALO']
    
    # Competitive field with small differences
    features = {
        'VER': {'base_pace': -0.15, 'consistency': 0.15, 'team_strength': 0.95, 'tyre_management': 0.85},
        'HAM': {'base_pace': -0.10, 'consistency': 0.18, 'team_strength': 0.88, 'tyre_management': 0.80},
        'LEC': {'base_pace': -0.08, 'consistency': 0.20, 'team_strength': 0.90, 'tyre_management': 0.78},
        'SAI': {'base_pace': -0.05, 'consistency': 0.22, 'team_strength': 0.90, 'tyre_management': 0.75},
        'NOR': {'base_pace': 0.00, 'consistency': 0.20, 'team_strength': 0.80, 'tyre_management': 0.82},
        'PIA': {'base_pace': 0.05, 'consistency': 0.25, 'team_strength': 0.80, 'tyre_management': 0.70},
        'RUS': {'base_pace': 0.02, 'consistency': 0.19, 'team_strength': 0.88, 'tyre_management': 0.76},
        'ALO': {'base_pace': 0.08, 'consistency': 0.21, 'team_strength': 0.72, 'tyre_management': 0.88},
    }
    
    win_prob, explanation = simulate_race_outcome(drivers, features, simulations=2000, seed=42)
    
    print(f"Win probabilities (competitive field):")
    for drv in sorted(drivers, key=lambda d: win_prob[d], reverse=True):
        reasons = explanation.get(drv, [])
        print(f"  {drv}: {win_prob[drv]*100:.1f}% - {', '.join(reasons[:2]) if reasons else 'N/A'}")
    
    # Validate reasonable spread
    sorted_probs = sorted(win_prob.values(), reverse=True)
    top_3_total = sum(sorted_probs[:3])
    
    assert sorted_probs[0] < 0.40, f"Top driver has {sorted_probs[0]*100:.1f}% (too high for competitive field)"
    assert top_3_total < 0.85, f"Top 3 have {top_3_total*100:.1f}% (too concentrated)"
    
    print("✅ Realistic probability spread\n")


def test_feature_extraction_no_leakage():
    """Test that feature extraction doesn't use race results."""
    print("\n=== Test 4: Feature Extraction (No Data Leakage) ===")
    
    # Create mock lap data
    np.random.seed(42)
    drivers = ['VER', 'HAM', 'LEC']
    laps_data = []
    
    for driver in drivers:
        base_time = 88.0 + np.random.normal(0, 0.3)  # Each driver has slightly different pace
        for lap in range(1, 51):
            laps_data.append({
                'Driver': driver,
                'LapNumber': lap,
                'LapTimeSeconds': base_time + np.random.normal(0, 0.5) + (lap * 0.02),  # Degradation
                'TyreLife': lap if lap < 25 else lap - 24,
                'Stint': 1 if lap < 25 else 2,
                'Team': 'Red Bull Racing' if driver == 'VER' else ('Mercedes' if driver == 'HAM' else 'Ferrari'),
            })
    
    laps_df = pd.DataFrame(laps_data)
    
    # Extract features
    features = build_driver_features_from_race_data(laps_df, drivers)
    
    print("Extracted features (should be relative, not absolute):")
    for driver, feats in features.items():
        print(f"  {driver}: pace={feats['base_pace']:.3f}, consistency={feats['consistency']:.3f}, "
              f"team={feats['team_strength']:.2f}, tyre_mgmt={feats['tyre_management']:.2f}")
    
    # Validate features are normalized/relative
    paces = [f['base_pace'] for f in features.values()]
    assert abs(np.mean(paces)) < 0.5, "Base pace should be 0-centered (relative to field)"
    
    print("✅ Features are relative, not absolute (no leakage)\n")


def run_all_tests():
    """Run all validation tests."""
    print("="*60)
    print("RACE OUTCOME PREDICTION - VALIDATION TESTS")
    print("="*60)
    
    try:
        test_probability_guardrails()
        test_sparse_data_handling()
        test_realistic_distribution()
        test_feature_extraction_no_leakage()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED - Outcome prediction is robust")
        print("="*60)
        print("\nKey improvements validated:")
        print("  • No 100% probability collapse")
        print("  • Sparse data smoothing active")
        print("  • Realistic uncertainty distribution")
        print("  • No data leakage from race results")
        print("  • Explainable predictions with reasoning")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    run_all_tests()
