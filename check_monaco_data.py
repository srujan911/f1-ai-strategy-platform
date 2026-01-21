from src.data_loader import load_race_data

# Load 2025 Monaco
laps, session = load_race_data(2025, 'Monaco Grand Prix')

print('=== 2025 Monaco Race Data ===')
print(f'Total laps in dataset: {len(laps)}')
print(f'Unique drivers: {laps["Driver"].nunique()}')
print(f'Unique compounds: {laps["Compound"].unique()}')
print(f'Lap time range: {laps["LapTime"].min()} to {laps["LapTime"].max()}')

# Check for data quality
print(f'\nNull LapTimes: {laps["LapTime"].isna().sum()}')
print(f'Null TyreLife: {laps["TyreLife"].isna().sum()}')

# Check average lap times by compound
print('\nCompound breakdown:')
for compound in ['SOFT', 'MEDIUM', 'HARD']:
    subset = laps[laps['Compound'] == compound]
    if len(subset) > 0:
        avg_time = subset['LapTime'].dt.total_seconds().mean()
        max_tyre_life = subset['TyreLife'].max()
        print(f'{compound}: {len(subset)} laps, avg {avg_time:.1f}s, max tyre life {max_tyre_life}')

# Compare with 2024 Monaco
print('\n' + '='*50)
laps_2024, session_2024 = load_race_data(2024, 'Monaco Grand Prix')
print('=== 2024 Monaco Race Data ===')
print(f'Total laps: {len(laps_2024)}')
print(f'Unique drivers: {laps_2024["Driver"].nunique()}')
print(f'Unique compounds: {laps_2024["Compound"].unique()}')
