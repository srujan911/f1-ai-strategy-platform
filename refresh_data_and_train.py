#!/usr/bin/env python3
"""
Comprehensive data refresh and model training script.

This script:
1. Clears all old cached data
2. Fetches latest F1 data from fastf1 library (2024-2025 seasons)
3. Preprocesses and prepares the data
4. Trains all models (lap time, tyre degradation)
5. Generates visualization graphs
"""

import os
import shutil
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import fastf1
import matplotlib.pyplot as plt
from datetime import datetime

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.append(str(ROOT_DIR))

from src.data_loader import load_race_data, load_multiple_races
from src.feature_engineering import add_driver_normalization
from src.models.lap_time_model import train_lap_time_model, train_explainable_model
from src.models.tyre_deg_model import fit_tyre_degradation, build_driver_degradation_profiles


def clear_old_data():
    """Clear all old data directories and cache."""
    print("=" * 60)
    print("CLEARING OLD DATA")
    print("=" * 60)
    
    # Clear raw data directories
    raw_data_dir = ROOT_DIR / "data" / "raw"
    if raw_data_dir.exists():
        for item in raw_data_dir.iterdir():
            if item.name != 'fastf1_http_cache.sqlite':  # Preserve cache for initial load
                if item.is_dir():
                    shutil.rmtree(item)
                    print(f"✓ Removed directory: {item}")
                elif item.suffix != '.sqlite':
                    item.unlink()
                    print(f"✓ Removed file: {item}")
    
    # Clear processed data
    processed_dir = ROOT_DIR / "data" / "processed"
    if processed_dir.exists():
        for item in processed_dir.iterdir():
            if item.is_file():
                item.unlink()
                print(f"✓ Removed: {item}")
    
    print("✓ Old data cleared successfully\n")


def setup_fastf1_cache():
    """Setup FastF1 caching."""
    cache_dir = ROOT_DIR / "data" / "raw"
    cache_dir.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(cache_dir))
    print("✓ FastF1 cache enabled\n")


def fetch_latest_data():
    """Fetch latest F1 data from fastf1 library."""
    print("=" * 60)
    print("FETCHING LATEST F1 DATA")
    print("=" * 60)
    
    # Define races to fetch (2024-2025 completed races)
    races_2024 = [
        "Bahrain", "Saudi Arabia", "Australia", "Japan", "China",
        "Miami", "Emilia Romagna", "Monaco", "Canada", "Spain",
        "Austria", "Britain", "Hungary", "Belgium", "Netherlands",
        "Italy", "Azerbaijan", "Singapore", "United States", "Mexico",
        "Brazil", "Abu Dhabi"
    ]
    
    races_2025 = [
        "Bahrain", "Saudi Arabia", "Australia", "Japan", "China",
        "Miami", "Emilia Romagna", "Monaco", "Canada", "Spain"
    ]
    
    all_laps = []
    all_results = []
    
    # Fetch 2024 data
    print("\nFetching 2024 season data...")
    for gp in races_2024:
        try:
            print(f"  Loading {gp}...", end=" ")
            laps, results = load_race_data(2024, gp)
            laps['Year'] = 2024
            laps['GP'] = gp
            all_laps.append(laps)
            all_results.append(results)
            print(f"✓ ({len(laps)} laps)")
        except Exception as e:
            print(f"✗ Error: {str(e)[:50]}")
    
    # Fetch 2025 data
    print("\nFetching 2025 season data...")
    for gp in races_2025:
        try:
            print(f"  Loading {gp}...", end=" ")
            laps, results = load_race_data(2025, gp)
            laps['Year'] = 2025
            laps['GP'] = gp
            all_laps.append(laps)
            all_results.append(results)
            print(f"✓ ({len(laps)} laps)")
        except Exception as e:
            print(f"✗ Error: {str(e)[:50]}")
    
    if all_laps:
        combined_laps = pd.concat(all_laps, ignore_index=True)
        print(f"\n✓ Total laps loaded: {len(combined_laps)}")
        print(f"✓ Unique drivers: {combined_laps['Driver'].nunique()}")
        print(f"✓ Unique teams: {combined_laps['Team'].nunique()}")
        return combined_laps
    else:
        print("✗ No data loaded!")
        return None


def preprocess_data(laps_df):
    """Preprocess and feature engineer the data."""
    print("\n" + "=" * 60)
    print("PREPROCESSING DATA")
    print("=" * 60)
    
    # Add normalized lap times
    laps_df = add_driver_normalization(laps_df)
    
    # Encode compounds
    laps_df['CompoundEncoded'] = laps_df['Compound'].map({
        "SOFT": 0, "MEDIUM": 1, "HARD": 2,
        "INTERMEDIATE": 3, "WET": 4
    })
    
    # Remove NaN values
    laps_df = laps_df.dropna(subset=['CompoundEncoded', 'NormalizedLapTime', 'LapTimeSeconds'])
    
    print(f"✓ Data preprocessed: {len(laps_df)} rows")
    print(f"✓ Unique drivers: {laps_df['Driver'].nunique()}")
    print(f"✓ Data ready for modeling")
    
    return laps_df


def train_models(laps_df):
    """Train all models."""
    print("\n" + "=" * 60)
    print("TRAINING MODELS")
    print("=" * 60)
    
    # Prepare features for lap time model
    print("\n1. Training Lap Time Model...")
    try:
        X = laps_df[['LapNumber', 'TyreLife', 'Stint', 'CompoundEncoded']].copy()
        y = laps_df['NormalizedLapTime'].copy()
        
        # Remove any remaining NaN values
        mask = ~(X.isna().any(axis=1) | y.isna())
        X = X[mask]
        y = y[mask]
        
        if len(X) > 10 and len(y) > 10:
            lap_model, lap_mae = train_lap_time_model(X, y)
            print(f"   ✓ Lap Time Model trained")
            print(f"   ✓ Mean Absolute Error: {lap_mae:.4f} seconds")
            
            # Also train explainable model
            explainable_model, explainable_mae = train_explainable_model(X, y)
            print(f"   ✓ Explainable Model trained")
            print(f"   ✓ MAE: {explainable_mae:.4f} seconds")
        else:
            print(f"   ✗ Insufficient data for training")
            lap_model, explainable_model = None, None
    except Exception as e:
        print(f"   ✗ Error training lap time model: {e}")
        lap_model, explainable_model = None, None
    
    # Train tyre degradation model
    print("\n2. Training Tyre Degradation Model...")
    try:
        # Group by driver and build degradation profiles
        deg_profiles = build_driver_degradation_profiles(laps_df)
        print(f"   ✓ Degradation profiles built for {len(deg_profiles)} drivers")
        
        # Fit degradation curves
        for driver in laps_df['Driver'].unique()[:5]:  # Sample of drivers
            driver_laps = laps_df[laps_df['Driver'] == driver]
            if len(driver_laps) > 3:
                try:
                    model = fit_tyre_degradation(driver_laps)
                    print(f"   ✓ {driver}: degradation model trained")
                except:
                    pass
    except Exception as e:
        print(f"   ✗ Error training degradation model: {e}")
    
    return lap_model, explainable_model


def generate_visualizations(laps_df):
    """Generate visualization graphs."""
    print("\n" + "=" * 60)
    print("GENERATING VISUALIZATIONS")
    print("=" * 60)
    
    viz_dir = ROOT_DIR / "visualizations"
    viz_dir.mkdir(exist_ok=True)
    
    try:
        # 1. Lap time distribution by compound
        print("\n1. Generating lap time by compound graph...")
        fig, ax = plt.subplots(figsize=(12, 6))
        for compound in laps_df['Compound'].unique():
            compound_data = laps_df[laps_df['Compound'] == compound]['LapTimeSeconds'].dropna()
            if len(compound_data) > 0:
                ax.hist(compound_data, alpha=0.6, label=compound, bins=30)
        ax.set_xlabel('Lap Time (seconds)')
        ax.set_ylabel('Frequency')
        ax.set_title('Lap Time Distribution by Tyre Compound')
        ax.legend()
        plt.tight_layout()
        plt.savefig(viz_dir / 'lap_times_by_compound.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("   ✓ Saved: lap_times_by_compound.png")
        
        # 2. Tyre degradation curves
        print("\n2. Generating tyre degradation curves...")
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        compounds = laps_df['Compound'].unique()[:4]
        
        for idx, compound in enumerate(compounds):
            ax = axes[idx // 2, idx % 2]
            compound_data = laps_df[laps_df['Compound'] == compound]
            
            for driver in compound_data['Driver'].unique()[:3]:
                driver_compound = compound_data[compound_data['Driver'] == driver]
                driver_compound = driver_compound.sort_values('TyreLife')
                if len(driver_compound) > 2:
                    ax.plot(driver_compound['TyreLife'], 
                           driver_compound['LapTimeSeconds'],
                           marker='o', alpha=0.6, label=driver)
            
            ax.set_xlabel('Tyre Life (laps)')
            ax.set_ylabel('Lap Time (seconds)')
            ax.set_title(f'{compound} Tyre Degradation')
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(viz_dir / 'tyre_degradation_curves.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("   ✓ Saved: tyre_degradation_curves.png")
        
        # 3. Driver performance comparison
        print("\n3. Generating driver performance comparison...")
        fig, ax = plt.subplots(figsize=(14, 6))
        driver_stats = laps_df.groupby('Driver')['LapTimeSeconds'].agg(['mean', 'std', 'count'])
        driver_stats = driver_stats[driver_stats['count'] >= 10].sort_values('mean')
        
        top_drivers = driver_stats.head(15)
        ax.barh(range(len(top_drivers)), top_drivers['mean'])
        ax.set_yticks(range(len(top_drivers)))
        ax.set_yticklabels(top_drivers.index)
        ax.set_xlabel('Average Lap Time (seconds)')
        ax.set_title('Top 15 Drivers by Average Lap Time (min 10 laps)')
        plt.tight_layout()
        plt.savefig(viz_dir / 'driver_performance.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("   ✓ Saved: driver_performance.png")
        
        # 4. Stint analysis
        print("\n4. Generating stint analysis...")
        fig, ax = plt.subplots(figsize=(12, 6))
        stint_stats = laps_df.groupby('Stint')['LapTimeSeconds'].agg(['mean', 'std', 'count'])
        stint_stats = stint_stats[stint_stats['count'] >= 5]
        
        ax.errorbar(stint_stats.index, stint_stats['mean'], 
                   yerr=stint_stats['std'], marker='o', capsize=5, capthick=2)
        ax.set_xlabel('Stint Number')
        ax.set_ylabel('Average Lap Time (seconds)')
        ax.set_title('Lap Time Performance Across Stints')
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(viz_dir / 'stint_analysis.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("   ✓ Saved: stint_analysis.png")
        
        print(f"\n✓ All visualizations saved to: {viz_dir}")
        
    except Exception as e:
        print(f"✗ Error generating visualizations: {e}")


def save_processed_data(laps_df):
    """Save processed data for future use."""
    print("\n" + "=" * 60)
    print("SAVING PROCESSED DATA")
    print("=" * 60)
    
    processed_dir = ROOT_DIR / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = processed_dir / f"combined_laps_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    laps_df.to_csv(output_file, index=False)
    print(f"✓ Saved processed data: {output_file}")
    
    # Also save a latest version
    latest_file = processed_dir / "combined_laps_latest.csv"
    laps_df.to_csv(latest_file, index=False)
    print(f"✓ Saved latest version: {latest_file}")


def main():
    """Execute the full pipeline."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "F1 DATA REFRESH & MODEL TRAINING" + " " * 16 + "║")
    print("║" + " " * 15 + f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}" + " " * 22 + "║")
    print("╚" + "=" * 58 + "╝\n")
    
    try:
        # Step 1: Clear old data
        clear_old_data()
        
        # Step 2: Setup FastF1 cache
        setup_fastf1_cache()
        
        # Step 3: Fetch latest data
        laps_df = fetch_latest_data()
        if laps_df is None or len(laps_df) == 0:
            print("✗ No data loaded. Exiting.")
            return
        
        # Step 4: Preprocess data
        laps_df = preprocess_data(laps_df)
        
        # Step 5: Train models
        train_models(laps_df)
        
        # Step 6: Generate visualizations
        generate_visualizations(laps_df)
        
        # Step 7: Save processed data
        save_processed_data(laps_df)
        
        print("\n" + "=" * 60)
        print("✓ PIPELINE COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print(f"✓ Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\nYou can now run: python server.py")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n✗ PIPELINE FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
