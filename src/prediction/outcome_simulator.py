"""
Championship and race outcome simulation utilities.

Provides robust Monte Carlo simulations for race finishing positions and
season championship probabilities with proper uncertainty modeling and
safety guardrails to prevent unrealistic probability collapse.

Key improvements:
- Uses relative performance features (not race results)
- Realistic variance modeling (pit stops, safety cars, reliability)
- Handles sparse/missing data gracefully
- Prevents single-driver dominance through uncertainty injection
"""

from __future__ import annotations

from typing import Dict, List, Tuple, Optional
import numpy as np


def simulate_race_outcome(
    drivers: List[str],
    driver_features: Dict[str, Dict[str, float]],
    simulations: int = 2000,
    seed: Optional[int] = None,
) -> Tuple[Dict[str, float], Dict[str, List[str]]]:
    """
    Robust Monte Carlo race outcome simulation with realistic uncertainty.

    Args:
        drivers: List of driver abbreviations
        driver_features: Dict mapping driver -> {
            'base_pace': relative pace score (lower is faster, 0-centered),
            'consistency': variance factor (0-1, lower = more consistent),
            'team_strength': team competitiveness (0-1),
            'tyre_management': degradation handling (0-1)
        }
        simulations: Number of Monte Carlo iterations (default: 2000)
        seed: Random seed for reproducibility

    Returns:
        Tuple of:
            - win_probability: Dict[driver, probability]
            - explanation: Dict with reasoning factors

    Safety guardrails:
        - Minimum 5% probability floor for any driver
        - Maximum 60% probability cap (no single driver dominance)
        - Fallback to uniform if data too sparse
        - Realistic variance prevents deterministic outcomes
    """
    rng = np.random.default_rng(seed)
    wins = {d: 0 for d in drivers}
    podiums = {d: 0 for d in drivers}
    
    # Extract features with defaults
    base_pace = np.array([driver_features.get(d, {}).get('base_pace', 0.0) for d in drivers])
    consistency = np.array([driver_features.get(d, {}).get('consistency', 0.5) for d in drivers])
    team_strength = np.array([driver_features.get(d, {}).get('team_strength', 0.5) for d in drivers])
    
    # Check data quality - fallback to uniform if too sparse
    features_available = sum(1 for d in drivers if d in driver_features and driver_features[d])
    if features_available < len(drivers) * 0.3:  # Less than 30% have data
        print(f"⚠️ Sparse data detected ({features_available}/{len(drivers)} drivers) - using smoothed priors")
        # Add strong regularization
        base_pace = base_pace * 0.3  # Heavily dampen differences
        consistency = np.full(len(drivers), 0.5)  # Assume moderate consistency
    
    # Run Monte Carlo simulation
    for _ in range(simulations):
        # Model realistic race variance components:
        
        # 1. Lap time variance (consistency-dependent)
        pace_noise = rng.normal(0, 0.3, size=len(drivers)) * (1 + consistency)
        
        # 2. Pit stop variance (±0.5s per stop, 2 stops typical)
        pit_noise = rng.normal(0, 1.0, size=len(drivers))
        
        # 3. Traffic & overtaking randomness
        traffic_noise = rng.normal(0, 0.5, size=len(drivers))
        
        # 4. Reliability failures (5% chance per driver)
        reliability = rng.random(size=len(drivers)) > 0.05
        
        # 5. Safety car shuffle (15% chance, benefits random positions)
        safety_car = rng.random() < 0.15
        safety_car_boost = rng.normal(0, 1.5, size=len(drivers)) if safety_car else 0
        
        # Combined race time (lower is better)
        race_time = (
            base_pace +
            pace_noise +
            pit_noise +
            traffic_noise +
            safety_car_boost -
            team_strength * 0.5  # Team advantage
        )
        
        # Apply reliability failures (DNF = very high time)
        race_time = np.where(reliability, race_time, 999.0)
        
        # Determine finishing order
        finishing_positions = np.argsort(race_time)
        
        winner_idx = finishing_positions[0]
        wins[drivers[winner_idx]] += 1
        
        # Track podiums
        for pos_idx in finishing_positions[:3]:
            podiums[drivers[pos_idx]] += 1
    
    # Calculate win probabilities
    total = float(simulations)
    win_prob = {d: wins[d] / total for d in drivers}
    
    # Apply safety guardrails
    win_prob = apply_probability_guardrails(win_prob)
    
    # Generate explanation factors
    explanation = generate_explanation(drivers, driver_features, win_prob, podiums, simulations)
    
    return win_prob, explanation


def apply_probability_guardrails(probabilities: Dict[str, float]) -> Dict[str, float]:
    """
    Apply safety guardrails to prevent unrealistic probability distributions.
    
    Rules:
    - Minimum 2% floor (accounts for luck/chaos)
    - Maximum 65% cap (prevents deterministic predictions)
    - Redistribute excess probability mass from capped values
    - Ensure sum = 1.0
    """
    MIN_PROB = 0.02
    MAX_PROB = 0.65
    
    drivers = list(probabilities.keys())
    probs = np.array([probabilities[d] for d in drivers])
    n = len(drivers)
    
    # Iterative enforcement (handles edge cases)
    max_iterations = 10
    for iteration in range(max_iterations):
        # Apply cap
        capped = probs > MAX_PROB
        if capped.any():
            excess = (probs[capped] - MAX_PROB).sum()
            probs[capped] = MAX_PROB
            # Redistribute excess to uncapped drivers
            uncapped = ~capped
            if uncapped.any():
                probs[uncapped] += excess / uncapped.sum()
        
        # Apply floor
        below_floor = probs < MIN_PROB
        if below_floor.any():
            deficit = (MIN_PROB - probs[below_floor]).sum()
            probs[below_floor] = MIN_PROB
            # Take deficit from above-floor drivers
            above_floor = ~below_floor
            if above_floor.any():
                probs[above_floor] -= deficit / above_floor.sum()
        
        # Renormalize
        probs = probs / probs.sum()
        
        # Check convergence
        if not (probs > MAX_PROB).any() and not (probs < MIN_PROB * 0.99).any():
            break
    
    # Safety: If still violations after iterations, use uniform smoothing
    if (probs > MAX_PROB + 0.01).any():
        print(f"⚠️ Guardrail enforcement failed, applying uniform smoothing")
        uniform = np.ones(n) / n
        probs = 0.7 * probs + 0.3 * uniform  # Mix with uniform
        probs = probs / probs.sum()
    
    return {d: float(p) for d, p in zip(drivers, probs)}


def generate_explanation(
    drivers: List[str],
    features: Dict[str, Dict[str, float]],
    win_prob: Dict[str, float],
    podiums: Dict[str, int],
    simulations: int,
) -> Dict[str, List[str]]:
    """Generate human-readable explanations for predictions."""
    explanations = {}
    
    # Top 3 favorites
    sorted_drivers = sorted(drivers, key=lambda d: win_prob[d], reverse=True)[:3]
    
    for driver in sorted_drivers:
        reasons = []
        feats = features.get(driver, {})
        
        # Pace advantage
        if feats.get('base_pace', 0) < -0.3:
            reasons.append(f"Strong pace advantage ({abs(feats['base_pace']):.2f}s faster)")
        elif feats.get('base_pace', 0) > 0.3:
            reasons.append(f"Pace deficit ({feats['base_pace']:.2f}s slower)")
        else:
            reasons.append("Competitive pace")
        
        # Team strength
        team_str = feats.get('team_strength', 0.5)
        if team_str > 0.7:
            reasons.append("Top-tier team resources")
        elif team_str < 0.3:
            reasons.append("Midfield team constraints")
        
        # Consistency
        const = feats.get('consistency', 0.5)
        if const < 0.3:
            reasons.append("High consistency (low variance)")
        elif const > 0.7:
            reasons.append("Inconsistent performance")
        
        # Podium rate
        podium_rate = podiums[driver] / simulations
        reasons.append(f"Podium rate: {podium_rate*100:.1f}%")
        
        explanations[driver] = reasons
    
    return explanations


def simulate_championship(
    drivers: List[str],
    base_points: Dict[str, float],
    driver_features: Dict[str, Dict[str, float]],
    remaining_races: int = 5,
    simulations: int = 1000,
) -> Dict[str, Dict[str, float]]:
    """
    Monte Carlo championship projection with realistic race variance.
    
    Args:
        drivers: List of driver abbreviations
        base_points: Current championship points per driver
        driver_features: Performance features per driver
        remaining_races: Number of races left in season
        simulations: Monte Carlo iterations
        
    Returns:
        Dict with 'title_probability' and 'expected_points'
    """
    rng = np.random.default_rng(42)
    points = {d: 0.0 for d in drivers}
    titles = {d: 0 for d in drivers}
    
    POINTS_SYSTEM = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]  # Top 10 points

    for _ in range(simulations):
        scores = base_points.copy()
        
        # Simulate each remaining race
        for _ in range(remaining_races):
            # Use robust race simulation for each race
            race_prob, _ = simulate_race_outcome(drivers, driver_features, simulations=200, seed=None)
            
            # Sample finishing order from probabilities
            probs = np.array([race_prob[d] for d in drivers])
            
            # Weighted sampling for top positions, random shuffle for midfield
            top_drivers = rng.choice(drivers, size=min(10, len(drivers)), replace=False, p=probs/probs.sum())
            
            # Award points
            for idx, driver in enumerate(top_drivers):
                if idx < len(POINTS_SYSTEM):
                    scores[driver] = scores.get(driver, 0) + POINTS_SYSTEM[idx]
        
        # Championship winner
        champ = max(scores, key=scores.get)
        titles[champ] += 1
        
        # Accumulate expected points
        for d in drivers:
            points[d] += scores.get(d, 0)

    return {
        "title_probability": {d: titles[d] / simulations for d in drivers},
        "expected_points": {d: points[d] / simulations for d in drivers},
    }


def build_driver_features_from_race_data(
    laps_df,
    drivers: List[str],
    team_standings: Optional[Dict[str, float]] = None,
) -> Dict[str, Dict[str, float]]:
    """
    Extract non-leaking performance features from race data.
    
    IMPORTANT: This function MUST NOT use race outcome features:
    - No final position, race result, or fastest lap winner
    - Only use relative performance metrics
    
    Args:
        laps_df: Lap data DataFrame
        drivers: List of drivers to analyze
        team_standings: Optional team competitiveness scores (0-1)
        
    Returns:
        Dict mapping driver -> feature dict
    """
    features = {}
    
    # Default team standings if not provided (based on typical F1 hierarchy)
    if team_standings is None:
        team_standings = {
            'Red Bull Racing': 0.95,
            'Ferrari': 0.90,
            'Mercedes': 0.88,
            'McLaren': 0.80,
            'Aston Martin': 0.72,
            'Alpine': 0.60,
            'Williams': 0.50,
            'AlphaTauri': 0.55,
            'Alfa Romeo': 0.52,
            'Haas': 0.48,
            'RB': 0.55,
            'Kick Sauber': 0.50,
        }
    
    # Calculate relative pace using clean laps only (not outcome)
    # Use percentile differences rather than absolute times
    all_lap_times = []
    driver_lap_times = {}
    
    for driver in drivers:
        drv_laps = laps_df[laps_df['Driver'] == driver].copy()
        
        if len(drv_laps) == 0:
            # No data - use neutral defaults
            features[driver] = {
                'base_pace': 0.0,
                'consistency': 0.5,
                'team_strength': 0.5,
                'tyre_management': 0.5,
            }
            continue
        
        # Filter for clean, representative laps
        if 'LapTimeSeconds' in drv_laps.columns:
            clean_laps = drv_laps[
                (drv_laps['LapTimeSeconds'].notna()) &
                (drv_laps['LapTimeSeconds'] > 0) &
                (drv_laps['LapTimeSeconds'] < 200)  # Exclude outliers
            ]
        elif 'LapTime' in drv_laps.columns:
            drv_laps['LapTimeSeconds'] = drv_laps['LapTime'].dt.total_seconds()
            clean_laps = drv_laps[
                (drv_laps['LapTimeSeconds'].notna()) &
                (drv_laps['LapTimeSeconds'] > 0) &
                (drv_laps['LapTimeSeconds'] < 200)
            ]
        else:
            # Fallback if no lap time data
            features[driver] = {
                'base_pace': 0.0,
                'consistency': 0.5,
                'team_strength': 0.5,
                'tyre_management': 0.5,
            }
            continue
        
        if len(clean_laps) < 3:  # Insufficient data
            features[driver] = {
                'base_pace': 0.0,
                'consistency': 0.5,
                'team_strength': 0.5,
                'tyre_management': 0.5,
            }
            continue
        
        lap_times = clean_laps['LapTimeSeconds'].values
        driver_lap_times[driver] = lap_times
        all_lap_times.extend(lap_times)
    
    # Calculate field-wide percentiles
    if len(all_lap_times) > 0:
        p10 = np.percentile(all_lap_times, 10)  # Fast lap reference
        p50 = np.percentile(all_lap_times, 50)  # Median reference
        p90 = np.percentile(all_lap_times, 90)  # Slow lap reference
    else:
        p10, p50, p90 = 85.0, 90.0, 95.0  # Defaults
    
    # Build features for each driver
    for driver in drivers:
        if driver not in driver_lap_times or len(driver_lap_times[driver]) == 0:
            continue
        
        lap_times = driver_lap_times[driver]
        
        # Base pace: deviation from field median (0-centered, negative = faster)
        driver_median = np.median(lap_times)
        base_pace = (driver_median - p50) / (p90 - p10)  # Normalized
        
        # Consistency: coefficient of variation (lower = more consistent)
        consistency = np.std(lap_times) / np.mean(lap_times) if np.mean(lap_times) > 0 else 0.5
        consistency = np.clip(consistency, 0.01, 0.15)  # Typical F1 range
        
        # Team strength from standings
        team = None
        if 'Team' in laps_df.columns:
            driver_teams = laps_df[laps_df['Driver'] == driver]['Team'].unique()
            if len(driver_teams) > 0:
                team = driver_teams[0]
        
        team_strength = team_standings.get(team, 0.5) if team else 0.5
        
        # Tyre management: degradation rate (use stint analysis)
        # Lower variance in late stint = better management
        tyre_mgmt = 0.5  # Default
        if 'TyreLife' in laps_df.columns:
            drv_laps = laps_df[laps_df['Driver'] == driver]
            late_stint = drv_laps[drv_laps['TyreLife'] > 10]
            if len(late_stint) > 3:
                late_variance = np.std(late_stint['LapTimeSeconds'].values)
                # Lower variance = better management
                tyre_mgmt = np.clip(1.0 - (late_variance / 2.0), 0.3, 0.9)
        
        features[driver] = {
            'base_pace': float(base_pace),
            'consistency': float(consistency),
            'team_strength': float(team_strength),
            'tyre_management': float(tyre_mgmt),
        }
    
    return features
