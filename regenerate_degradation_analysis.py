#!/usr/bin/env python3
"""
Script to regenerate tyre degradation analysis for all races with corrected models.
This ensures all race data uses the proper compound baselines.
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent
sys.path.append(str(ROOT_DIR))

from src.data_loader import load_race_data
from src.models.tyre_deg_model import fit_tyre_degradation, create_degradation_model
import fastf1

def analyze_race(year: int, gp_name: str):
    """Analyze degradation for a single race."""
    print(f"\n{'='*60}")
    print(f"Analyzing {year} {gp_name}")
    print(f"{'='*60}")
    
    try:
        laps, session = load_race_data(year, gp_name)
        
        # Get compounds in race
        compounds = sorted(set([str(c) for c in laps['Compound'].unique() if pd.notna(c)]))
        print(f"Compounds found: {compounds}")
        
        # Fit models for each compound
        models = {}
        for compound in compounds:
            compound_laps = laps[laps['Compound'] == compound].copy()
            compound_laps = compound_laps[
                (compound_laps['LapTime'].notna()) & 
                (compound_laps['TyreLife'].notna()) &
                (compound_laps['TyreLife'] > 0)
            ].copy()
            
            if len(compound_laps) >= 5:
                coefs = fit_tyre_degradation(compound_laps, compound, min_samples=5)
                if coefs is not None:
                    models[compound] = {
                        'coeffs': coefs,
                        'model': create_degradation_model(coefs),
                        'laps': len(compound_laps)
                    }
                    print(f"  {compound}: {len(compound_laps)} laps, coeffs={coefs}")
        
        # Create visualization
        if models:
            fig, ax = plt.subplots(figsize=(12, 7))
            
            max_tyre_life = laps[laps['TyreLife'].notna()]['TyreLife'].max()
            x_range = np.linspace(0, max_tyre_life, 50)
            
            colors = {'SOFT': 'red', 'MEDIUM': 'gold', 'HARD': 'white', 
                     'C4': 'red', 'C3': 'gold', 'C2': 'white', 'C1': 'silver'}
            
            for compound, data in sorted(models.items()):
                y_pred = [float(data['model'](x, compound=compound)) for x in x_range]
                color = colors.get(compound, 'cyan')
                ax.plot(x_range, y_pred, label=compound, linewidth=2.5, color=color)
            
            ax.set_xlabel('Tyre Life (Laps)', fontsize=12)
            ax.set_ylabel('Lap Time Increase (seconds)', fontsize=12)
            ax.set_title(f'Tyre Degradation Analysis - {year} {gp_name}', fontsize=14, fontweight='bold')
            ax.legend(fontsize=11, loc='best')
            ax.grid(True, alpha=0.3)
            
            # Save figure
            output_dir = ROOT_DIR / 'visualizations' / 'degradation_analysis'
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_file = output_dir / f'{year}_{gp_name.replace(" ", "_")}_degradation.png'
            plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='#1a1a2e')
            plt.close()
            
            print(f"✓ Saved graph: {output_file}")
            
            # Verify compound ordering (SOFT < MEDIUM < HARD)
            sample_life = 10
            times = {}
            for compound in compounds:
                if compound in models:
                    times[compound] = models[compound]['model'](sample_life, compound=compound)
            
            print(f"\n  Lap times at tyre life={sample_life}:")
            for compound in sorted(times.keys()):
                print(f"    {compound}: {times[compound]:.2f}s")
            
            # Check if ordering is correct
            if 'SOFT' in times and 'MEDIUM' in times and 'HARD' in times:
                if times['SOFT'] < times['MEDIUM'] < times['HARD']:
                    print("  ✓ Correct ordering: SOFT < MEDIUM < HARD")
                else:
                    print(f"  ⚠ Warning: Ordering incorrect! {times}")
        
        return True
    except Exception as e:
        print(f"✗ Error analyzing {year} {gp_name}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Analyze all races."""
    print("\n" + "="*60)
    print("TYRE DEGRADATION ANALYSIS - ALL RACES")
    print("="*60)
    
    # Get schedule for both years
    races_by_year = {}
    for year in [2025, 2024]:
        try:
            sched = fastf1.get_event_schedule(year)
            races_by_year[year] = []
            for _, event in sched.iterrows():
                event_name = event.get('EventName', '')
                round_no = event.get('RoundNumber', 0)
                if event_name and pd.notna(round_no) and round_no > 0:
                    races_by_year[year].append((round_no, event_name))
        except Exception as e:
            print(f"Error fetching schedule for {year}: {e}")
    
    total = 0
    success = 0
    
    # Analyze races in order
    for year in [2025, 2024]:
        if year in races_by_year:
            for round_no, gp_name in sorted(races_by_year[year]):
                total += 1
                if analyze_race(year, gp_name):
                    success += 1
    
    print(f"\n{'='*60}")
    print(f"ANALYSIS COMPLETE: {success}/{total} races analyzed successfully")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
