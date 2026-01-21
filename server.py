"""
F1 AI Strategy Platform - Flask Server
Professional web application for F1 race strategy analysis and prediction.
"""

from flask import Flask, render_template, jsonify, request
import numpy as np
import pandas as pd
from pathlib import Path
import sys

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.append(str(ROOT_DIR))

from src.data_loader import load_race_data, load_multiple_races
from src.feature_engineering import add_driver_normalization, preprocess_laps
from src.models.tyre_deg_model import (
    fit_tyre_degradation,
    create_degradation_model,
    build_driver_degradation_profiles,
)
from src.models.lap_time_model import (
    train_lap_time_model,
    train_explainable_model,
    predict_future_laps,
)
from src.strategy.pit_strategy import (
    optimize_pit_strategy,
    simulate_race_strategy,
    run_strategy_simulation,
)
from src.strategy.recommendation import recommend_strategy
from src.strategy.simulation_engine import evaluate_strategies, summarize_top_strategies
from src.analysis.multi_race_analysis import compare_tracks
from src.prediction._2026_strategy import (
    predict_team_strategies,
    predict_degradation_trends,
    predict_pit_timing_windows
)
from src.prediction.outcome_simulator import (
    simulate_race_outcome,
    simulate_championship,
    build_driver_features_from_race_data,
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'f1-ai-strategy-platform-2026'

# Cache for race data - clear on server restart to ensure fresh accurate data
RACE_DATA_CACHE = {}
print("Server starting - race data cache cleared")


def _clean_race_name(gp_name: str) -> str:
    """Remove date prefix from race name (e.g., '2025-05-25_Monaco_Grand_Prix' -> 'Monaco Grand Prix')."""
    # Handle format like "2025-05-25_Monaco_Grand_Prix" or "YYYY-MM-DD_EventName"
    if '_' in gp_name and len(gp_name) > 10:  # Has date prefix
        parts = gp_name.split('_', 1)  # Split on first underscore
        if len(parts[0]) == 10 and parts[0][4] == '-':  # Looks like YYYY-MM-DD
            # Return the rest, replacing underscores with spaces
            return parts[1].replace('_', ' ')
    # If no date prefix, just replace underscores with spaces
    return gp_name.replace('_', ' ')


def _get_cached_race(year: int, gp_name: str):
    """Load race data with caching and ensure LapTimeSeconds exists."""
    # Clean the race name (remove date prefix)
    clean_gp_name = _clean_race_name(gp_name)
    
    cache_key = f"{year}_{gp_name}"
    if cache_key not in RACE_DATA_CACHE:
        laps, session = load_race_data(int(year), clean_gp_name)
        RACE_DATA_CACHE[cache_key] = (laps, session)
    else:
        laps, session = RACE_DATA_CACHE[cache_key]

    laps_copy = laps.copy()
    if "LapTimeSeconds" not in laps_copy.columns and "LapTime" in laps_copy.columns:
        laps_copy["LapTimeSeconds"] = laps_copy["LapTime"].dt.total_seconds()

    return laps_copy, session


def _get_total_laps(laps: pd.DataFrame, session) -> int:
    """Safely determine race distance.

    Prefer session results lap counts; fall back to per-driver lap maxima median; clamp to a sane bound (<200).
    """
    total = None
    try:
        if hasattr(session, "results") and "Laps" in session.results.columns:
            total = session.results["Laps"].max()
    except Exception:
        total = None

    if total is None or pd.isna(total):
        # Use per-driver max lap to avoid inflated totals; take median to resist outliers
        try:
            per_driver = laps.groupby("Driver")["LapNumber"].max()
            # keep only plausible race distances (<150 laps) to avoid corrupt rows
            per_driver = per_driver[per_driver < 150]
            if len(per_driver) > 0:
                total = per_driver.median()
        except Exception:
            total = None

    if total is None or pd.isna(total):
        total = laps["LapNumber"].max() if "LapNumber" in laps.columns else 0

    total_int = int(total) if not pd.isna(total) else 0
    return max(1, min(total_int, 150))


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html')

@app.route('/test-whatif')
def test_whatif():
    """Test page for what-if simulation."""
    return render_template('test_whatif.html')


@app.route('/api/races')
def get_available_races():
    """Get list of available races from FastF1 schedule for accuracy."""
    races = []
    seen_races = set()  # Track normalized race names per year
    
    # Get official schedules from FastF1 for 2024 and 2025
    for year in [2025, 2024]:
        try:
            import fastf1
            sched = fastf1.get_event_schedule(year)
            for _, event in sched.iterrows():
                event_name = event.get('EventName', '')
                round_no = int(event.get('RoundNumber', 0)) if pd.notna(event.get('RoundNumber')) else 0
                
                if not event_name or round_no == 0:
                    continue
                
                # Normalize race name for deduplication
                normalized_name = f"{year}_{event_name.lower().strip()}"
                
                # Skip duplicates
                if normalized_name in seen_races:
                    continue
                
                seen_races.add(normalized_name)
                
                race_id = f"{year}_{event_name.replace(' ', '_')}"
                display_name = f"{round_no:02d} - {event_name}"
                
                races.append({
                    'year': str(year),
                    'name': display_name,
                    'id': race_id
                })
        except Exception as e:
            print(f"Error fetching schedule for {year}: {e}")
            continue
    
    # Sort by year (descending) then round number
    races.sort(key=lambda x: (-int(x['year']), x['name']))
    
    return jsonify(races)


@app.route('/api/race/<year>/<gp_name>')
def get_race_data(year, gp_name):
    """Load and return race data with accurate statistics."""
    try:
        laps, session = _get_cached_race(int(year), gp_name)
        
        # Get accurate race distance from session
        race_distance = _get_total_laps(laps, session)
        
        # Filter for valid lap times (accurate and plausible)
        valid_laps = laps[laps['LapTime'].notna()].copy()
        if 'IsAccurate' in valid_laps.columns:
            valid_laps = valid_laps[valid_laps['IsAccurate'] == True]
        
        # Convert LapTime to seconds for validation and finding minimum
        valid_laps['LapTimeSeconds'] = valid_laps['LapTime'].dt.total_seconds()
        
        # Find fastest lap - find the absolute minimum lap time from all valid laps
        fastest_lap_data = {
            'time': None,
            'driver': None
        }
        
        if len(valid_laps) > 0:
            # Find the fastest lap overall (minimum LapTime)
            fastest_idx = valid_laps['LapTimeSeconds'].idxmin()
            fastest_lap_data['time'] = float(valid_laps.loc[fastest_idx, 'LapTimeSeconds'])
            fastest_lap_data['driver'] = valid_laps.loc[fastest_idx, 'Driver']
        
        # Compute basic stats
        stats = {
            'total_laps': race_distance,
            'drivers': sorted(laps['Driver'].unique().tolist()),
            'compounds': sorted(set([str(c) for c in laps['Compound'].unique() if pd.notna(c)])),
            'fastest_lap': fastest_lap_data,
            'circuit': gp_name,
            'year': year
        }
        
        return jsonify(stats)
    
    except Exception as e:
        print(f"Error in get_race_data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 404


@app.route('/api/tyre-degradation/<year>/<gp_name>')
def get_tyre_degradation(year, gp_name):
    """Calculate and return tyre degradation curves for all compounds."""
    try:
        laps_copy, session = _get_cached_race(int(year), gp_name)
        
        # Calculate degradation for each compound
        degradation_data = {}
        compounds = laps_copy['Compound'].dropna().unique()
        
        print(f"\n=== Analyzing compounds: {compounds} ===")
        
        for compound in compounds:
            compound_laps = laps_copy[laps_copy['Compound'] == compound].copy()
            
            # Filter for valid lap times and tyre life data
            compound_laps = compound_laps[
                (compound_laps['LapTimeSeconds'].notna()) & 
                (compound_laps['TyreLife'].notna()) &
                (compound_laps['TyreLife'] > 0)
            ].copy()
            
            print(f"Compound {compound}: {len(compound_laps)} valid laps")
            
            if len(compound_laps) >= 5:  # Reduced threshold
                try:
                    coefs = fit_tyre_degradation(compound_laps, compound, min_samples=5)
                    
                    if coefs is not None and len(coefs) > 0:
                        model = create_degradation_model(coefs)
                        max_life = float(compound_laps['TyreLife'].max())
                        x_range = np.linspace(0, max_life, 50)
                        # Pass compound to model for proper baseline offset
                        y_pred = [float(model(x, compound=compound)) for x in x_range]
                        
                        degradation_data[str(compound)] = {
                            'x': x_range.tolist(),
                            'y': y_pred,
                            'coefficients': coefs.tolist()
                        }
                        print(f"✓ Successfully modeled {compound}")
                except Exception as e:
                    print(f"Error processing compound {compound}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
        
        if not degradation_data:
            print("No valid degradation data available")
            return jsonify({'error': 'No valid degradation data available'}), 404
        
        print(f"Returning data for {len(degradation_data)} compounds")
        return jsonify(degradation_data)
    
    except Exception as e:
        print(f"Tyre degradation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/tyre-degradation/driver/<year>/<gp_name>')
def get_driver_degradation(year, gp_name):
    """Return per-driver degradation profiles and style classification."""
    try:
        laps_copy, _ = _get_cached_race(int(year), gp_name)
        profiles = build_driver_degradation_profiles(laps_copy)
        return jsonify(profiles)
    except Exception as e:
        print(f"Driver degradation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/driver-comparison', methods=['POST'])
def driver_comparison():
    """Compare tyre degradation and stint pace between two drivers."""
    payload = request.get_json(silent=True) or {}
    year = payload.get('year')
    gp_name = payload.get('gp_name')
    driver_a = payload.get('driver_a')
    driver_b = payload.get('driver_b')

    if not all([year, gp_name, driver_a, driver_b]):
        return jsonify({'error': 'Missing parameters'}), 400

    try:
        laps, _ = _get_cached_race(int(year), gp_name)
        comparison = {}
        for driver in [driver_a, driver_b]:
            driver_laps = laps[laps['Driver'] == driver].copy()
            if 'LapTimeSeconds' not in driver_laps.columns:
                driver_laps['LapTimeSeconds'] = driver_laps['LapTime'].dt.total_seconds()

            avg_pace = float(driver_laps['LapTimeSeconds'].mean()) if len(driver_laps) else None
            degr = None
            if len(driver_laps) >= 5:
                # Filter for valid data (no NaN values)
                valid_data = driver_laps.dropna(subset=['TyreLife', 'LapTimeSeconds'])
                if len(valid_data) >= 5:
                    try:
                        # Convert to numpy arrays of floats
                        tyrelife = valid_data['TyreLife'].values.astype(float)
                        laptimes = valid_data['LapTimeSeconds'].values.astype(float)
                        # Remove any remaining NaNs
                        mask = ~(np.isnan(tyrelife) | np.isnan(laptimes))
                        if mask.sum() >= 5:
                            coeffs = np.polyfit(tyrelife[mask], laptimes[mask], deg=1)
                            degr = coeffs.tolist()
                    except Exception:
                        degr = None

            comparison[driver] = {
                'average_pace': avg_pace,
                'degradation_slope': degr,
                'stint_count': int(driver_laps['Stint'].nunique()) if len(driver_laps) else 0,
            }

        delta = None
        if comparison[driver_a]['average_pace'] and comparison[driver_b]['average_pace']:
            delta = comparison[driver_a]['average_pace'] - comparison[driver_b]['average_pace']

        return jsonify({'drivers': comparison, 'pace_delta': delta})
    except Exception as e:
        print(f"Driver comparison error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/lap-time-prediction/<year>/<gp_name>')
def get_lap_time_prediction(year, gp_name):
    """Train lap time model and return predictions."""
    try:
        laps, session = _get_cached_race(int(year), gp_name)
        
        # Preprocess and train
        laps_normalized = add_driver_normalization(laps.copy())
        X, y = preprocess_laps(laps_normalized)
        
        if len(X) > 0:
            model, mae = train_lap_time_model(X, y)
            
            return jsonify({
                'mae': float(mae),
                'num_samples': len(X),
                'message': f'Model trained with MAE: {mae:.3f}s'
            })
        else:
            return jsonify({'error': 'Insufficient data for training'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/lap-time-forecast/<year>/<gp_name>', methods=['POST'])
def get_lap_time_forecast(year, gp_name):
    """Predict next laps with confidence intervals using enhanced feature set."""
    payload = request.get_json(silent=True) or {}
    horizon = int(payload.get('horizon', 5))
    track_temp = float(payload.get('track_temperature', 1.0))
    traffic_factor = float(payload.get('traffic_factor', 1.0))

    try:
        laps, session = _get_cached_race(int(year), gp_name)
        df = add_driver_normalization(laps.copy())
        df['CompoundEncoded'] = df['Compound'].map({
            'SOFT': 0, 'MEDIUM': 1, 'HARD': 2, 'INTERMEDIATE': 3, 'WET': 4
        })
        df = df.dropna(subset=['CompoundEncoded', 'NormalizedLapTime'])

        total_laps = _get_total_laps(df, session)
        df['FuelLoadProxy'] = 1 - (df['LapNumber'] / total_laps)
        df['TrackTemp'] = track_temp
        df['CleanAir'] = 1 / traffic_factor if traffic_factor > 0 else 1.0

        feature_cols = ['LapNumber', 'TyreLife', 'Stint', 'CompoundEncoded', 'FuelLoadProxy', 'TrackTemp', 'CleanAir']
        X = df[feature_cols]
        y = df['NormalizedLapTime']

        if len(X) == 0:
            return jsonify({'error': 'Insufficient data'}), 400

        model_info = train_explainable_model(X, y)
        model = model_info['model']
        mae = model_info['mae']
        importances = model_info['importances']

        last_row = X.iloc[-1]
        forecast = predict_future_laps(model, last_row, horizon=horizon)

        return jsonify({
            'mae': float(mae),
            'feature_importance': {col: float(val) for col, val in zip(feature_cols, importances)},
            'forecast': forecast,
            'horizon': horizon,
        })
    except Exception as e:
        print(f"Lap time forecast error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/explainability/<year>/<gp_name>')
def get_explainability(year, gp_name):
    """Return explainability artifacts for models and strategies."""
    try:
        laps, session = _get_cached_race(int(year), gp_name)
        df = add_driver_normalization(laps.copy())
        df['CompoundEncoded'] = df['Compound'].map({
            'SOFT': 0, 'MEDIUM': 1, 'HARD': 2, 'INTERMEDIATE': 3, 'WET': 4
        })
        df = df.dropna(subset=['CompoundEncoded', 'NormalizedLapTime'])

        total_laps = _get_total_laps(df, session)
        df['FuelLoadProxy'] = 1 - (df['LapNumber'] / total_laps)
        df['TrackTemp'] = 1.0
        df['CleanAir'] = 1.0

        X = df[['LapNumber', 'TyreLife', 'Stint', 'CompoundEncoded', 'FuelLoadProxy', 'TrackTemp', 'CleanAir']]
        y = df['NormalizedLapTime']

        model_info = train_explainable_model(X, y)
        importances = {col: float(val) for col, val in zip(X.columns, model_info['importances'])}

        # Build quick strategy explanation
        laps_copy, session = _get_cached_race(int(year), gp_name)
        deg_models = {}
        compounds = laps_copy['Compound'].dropna().unique()
        for compound in compounds:
            compound_laps = laps_copy[laps_copy['Compound'] == compound].copy()
            compound_laps = compound_laps[
                (compound_laps['LapTimeSeconds'].notna()) &
                (compound_laps['TyreLife'].notna()) &
                (compound_laps['TyreLife'] > 0)
            ]
            if len(compound_laps) >= 5:
                coefs = fit_tyre_degradation(compound_laps, compound, min_samples=5)
                if coefs is not None and len(coefs) > 0:
                    deg_models[str(compound)] = create_degradation_model(coefs)

        total_laps = _get_total_laps(laps_copy, session)
        valid_times = laps_copy[laps_copy['LapTimeSeconds'].notna()]['LapTimeSeconds']
        base_lap_time = float(valid_times.quantile(0.1)) if len(valid_times) > 0 else 90.0

        results = evaluate_strategies(
            total_laps=total_laps,
            degradation_models=deg_models,
            base_lap_time=base_lap_time,
            compounds=list(deg_models.keys()),
            starting_compound=str(compounds[0]) if len(compounds) else 'MEDIUM',
            pit_loss=22.0,
            what_if={},
            circuit_name=gp_name,
        )
        recommendation = recommend_strategy(results, {'pit_loss': 22.0})

        return jsonify({
            'feature_importance': importances,
            'strategy_explanation': recommendation,
            'assumptions': {
                'pit_loss': 22.0,
                'fuel_correction_per_lap': 0.06,
                'degradation_model': 'quadratic per compound',
            }
        })
    except Exception as e:
        print(f"Explainability error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/outcomes/<year>/<gp_name>')
def get_outcomes(year, gp_name):
    """
    Predict race win probabilities using robust Monte Carlo simulation.
    
    FIXED ISSUES:
    - ✅ No data leakage (uses relative performance, not race results)
    - ✅ Realistic uncertainty (pit stops, safety cars, reliability)
    - ✅ Handles sparse/2026 data with smoothed priors
    - ✅ Safety guardrails prevent 100% probabilities
    - ✅ Explainable predictions with contributing factors
    """
    try:
        laps, _ = _get_cached_race(int(year), gp_name)
        drivers = sorted(laps['Driver'].unique().tolist())
        
        print(f"\n=== Race Outcome Prediction: {year} {gp_name} ===")
        print(f"Drivers found: {len(drivers)}")
        
        # Extract non-leaking performance features
        driver_features = build_driver_features_from_race_data(laps, drivers)
        
        # Debug: Check feature extraction
        features_with_data = sum(1 for d in drivers if driver_features.get(d, {}).get('base_pace') != 0.0)
        print(f"Features extracted for {features_with_data}/{len(drivers)} drivers")
        
        # Run robust Monte Carlo simulation
        win_prob, explanation = simulate_race_outcome(
            drivers=drivers,
            driver_features=driver_features,
            simulations=2000,
        )
        
        # Championship simulation (use current points = 0 for single race)
        base_points = {d: 0.0 for d in drivers}
        championship = simulate_championship(
            drivers=drivers,
            base_points=base_points,
            driver_features=driver_features,
            remaining_races=1,
            simulations=500,
        )
        
        # Log predictions for debugging
        sorted_probs = sorted(win_prob.items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"Top 5 predictions:")
        for drv, prob in sorted_probs:
            print(f"  {drv}: {prob*100:.1f}%")
        
        # Check for probability collapse (safety validation)
        max_prob = max(win_prob.values())
        if max_prob > 0.70:
            print(f"⚠️ WARNING: High max probability detected ({max_prob*100:.1f}%) - guardrails applied")
        
        return jsonify({
            'win_probability': win_prob,
            'championship': championship,
            'drivers': drivers,
            'explanation': explanation,
            'metadata': {
                'simulations': 2000,
                'features_available': features_with_data,
                'total_drivers': len(drivers),
            }
        })
    except Exception as e:
        print(f"Outcome simulation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/pit-strategy/<year>/<gp_name>')
def get_pit_strategy(year, gp_name):
    """Optimize pit strategy for the race."""
    try:
        laps_copy, session = _get_cached_race(int(year), gp_name)
        
        # Get degradation models
        deg_models = {}
        compounds = laps_copy['Compound'].dropna().unique()
        
        print(f"\n=== Building pit strategy for compounds: {compounds} ===")
        
        for compound in compounds:
            compound_laps = laps_copy[laps_copy['Compound'] == compound].copy()
            
            # Filter for valid data
            compound_laps = compound_laps[
                (compound_laps['LapTimeSeconds'].notna()) & 
                (compound_laps['TyreLife'].notna()) &
                (compound_laps['TyreLife'] > 0)
            ].copy()
            
            print(f"Compound {compound}: {len(compound_laps)} valid laps")
            
            if len(compound_laps) >= 5:  # Reduced threshold
                try:
                    coefs = fit_tyre_degradation(compound_laps, compound, min_samples=5)
                    if coefs is not None and len(coefs) > 0:
                        deg_models[str(compound)] = create_degradation_model(coefs)
                        print(f"✓ Model created for {compound}")
                except Exception as e:
                    print(f"Error creating model for {compound}: {e}")
                    continue
        
        if not deg_models:
            print("Could not create any degradation models")
            return jsonify({'error': 'Could not create degradation models - insufficient valid lap data'}), 400
        
        # Optimize strategy
        total_laps = _get_total_laps(laps_copy, session)
        
        # Calculate average base lap time from fastest laps
        valid_times = laps_copy[laps_copy['LapTimeSeconds'].notna()]['LapTimeSeconds']
        base_lap_time = float(valid_times.quantile(0.1)) if len(valid_times) > 0 else 90.0
        
        print(f"Total laps: {total_laps}, Base lap time: {base_lap_time:.2f}s")
        
        try:
            strategy = optimize_pit_strategy(
                total_laps=total_laps,
                degradation_models=deg_models,
                pit_loss=22.0
            )
            
            print(f"Strategy: {strategy}")
            
            # Simulate race - get first available degradation model
            first_compound = list(deg_models.keys())[0] if deg_models else 'MEDIUM'
            lap_times = simulate_race_strategy(
                total_laps=total_laps,
                pit_strategy=strategy,
                degradation_model=deg_models[first_compound],
                base_lap_time=base_lap_time
            )
            
            return jsonify({
                'pit_laps': [int(x) for x in strategy['pits']],
                'compounds': [str(x) for x in strategy['compounds']],
                'total_time': float(sum(lap_times)),
                'lap_times': [float(t) for t in lap_times],
                'num_stops': len(strategy['pits'])
            })
        except Exception as e:
            print(f"Strategy optimization error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Strategy optimization failed: {str(e)}'}), 500
    
    except Exception as e:
        print(f"Pit strategy error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/strategy/simulate/<year>/<gp_name>', methods=['POST'])
def simulate_strategy(year, gp_name):
    """Advanced multi-stop simulation with what-if controls."""
    import time
    try:
        print(f"\n[SIMULATE] Starting {year}/{gp_name}")
        t0 = time.time()
        
        laps_copy, session = _get_cached_race(int(year), gp_name)
        print(f"[SIMULATE] Loaded race data: {time.time()-t0:.2f}s")
        
        payload = request.get_json(silent=True) or {}

        what_if = {
            'deg_multiplier': float(payload.get('deg_multiplier', 1.0)),
            'track_temperature': float(payload.get('track_temperature', 1.0)),
            'traffic_factor': float(payload.get('traffic_factor', 1.0)),
            'safety_car_probability': float(payload.get('safety_car_probability', 0.0)),
            'inlap_delta': float(payload.get('inlap_delta', 0.8)),
            'outlap_delta': float(payload.get('outlap_delta', 1.2)),
        }
        pit_loss = float(payload.get('pit_loss', 22.0))

        # Build degradation models by compound
        deg_models = {}
        compounds = laps_copy['Compound'].dropna().unique()
        for compound in compounds:
            compound_laps = laps_copy[laps_copy['Compound'] == compound].copy()
            compound_laps = compound_laps[
                (compound_laps['LapTimeSeconds'].notna()) &
                (compound_laps['TyreLife'].notna()) &
                (compound_laps['TyreLife'] > 0)
            ]
            if len(compound_laps) >= 5:
                coefs = fit_tyre_degradation(compound_laps, compound, min_samples=5)
                if coefs is not None and len(coefs) > 0:
                    deg_models[str(compound)] = create_degradation_model(coefs)
        
        print(f"[SIMULATE] Built degradation models: {time.time()-t0:.2f}s")

        if not deg_models:
            return jsonify({'error': 'No degradation models available'}), 400

        total_laps = _get_total_laps(laps_copy, session)
        valid_times = laps_copy[laps_copy['LapTimeSeconds'].notna()]['LapTimeSeconds']
        base_lap_time = float(valid_times.quantile(0.1)) if len(valid_times) > 0 else 90.0

        print(f"[SIMULATE] Starting strategy evaluation...")
        results = evaluate_strategies(
            total_laps=total_laps,
            degradation_models=deg_models,
            base_lap_time=base_lap_time,
            compounds=list(deg_models.keys()),
            starting_compound=str(compounds[0]) if len(compounds) else 'MEDIUM',
            pit_loss=pit_loss,
            what_if=what_if,
            circuit_name=gp_name,
        )
        
        print(f"[SIMULATE] Strategy evaluation done: {time.time()-t0:.2f}s ({len(results)} strategies)")

        summaries = summarize_top_strategies(results, top_k=5)
        recommendation = recommend_strategy(results, {**what_if, 'pit_loss': pit_loss})

        print(f"[SIMULATE] Complete: {time.time()-t0:.2f}s")
        return jsonify({
            'strategies': summaries,
            'recommendation': recommendation,
            'metadata': {
                'base_lap_time': base_lap_time,
                'total_laps': total_laps,
                'pit_loss': pit_loss,
            }
        })
    except Exception as e:
        print(f"Strategy simulation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/2026-predictions')
def get_2026_predictions():
    """Get 2026 season predictions."""
    try:
        team_strategies = predict_team_strategies(season=2026)
        degradation_trends = predict_degradation_trends(season=2026)
        
        return jsonify({
            'teams': team_strategies,
            'degradation_trends': degradation_trends
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/circuit-windows/<circuit>')
def get_circuit_windows(circuit):
    """Get pit timing windows for a specific circuit."""
    try:
        windows = predict_pit_timing_windows(circuit)
        return jsonify(windows)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/multi-race-analysis')
def multi_race_analysis():
    """Compare multiple races."""
    years = request.args.getlist('years[]')
    gps = request.args.getlist('gps[]')
    
    try:
        if not years or not gps or len(years) != len(gps):
            return jsonify({'error': 'Invalid parameters'}), 400
        
        races_data = []
        for year, gp in zip(years, gps):
            try:
                laps, session = load_race_data(int(year), gp)
                races_data.append(laps)
            except Exception:
                continue
        
        if len(races_data) < 2:
            return jsonify({'error': 'Need at least 2 races for comparison'}), 400
        
        comparison = compare_tracks(races_data)
        
        return jsonify({
            'avg_lap_times': {str(k): float(v) for k, v in comparison['avg_lap_times'].items()},
            'compound_usage': {str(k): int(v) for k, v in comparison['compound_usage'].items()},
            'message': 'Comparison complete'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("🏎️  F1 AI Strategy Platform - Professional Dashboard")
    print("=" * 60)
    print("\n✅ Server starting on http://localhost:5000")
    print("✅ Open your browser and navigate to the URL above")
    print("\n" + "=" * 60 + "\n")
    
    # Disable Flask auto-reloader to avoid endless restart loops on Windows
    app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)
