from src.data_loader import load_race_data

races = {
    'Monaco': (2025, '2025-05-25_Monaco_Grand_Prix'),
    'Qatar': (2025, '2025-11-30_Qatar_Grand_Prix')
}

for name, (year, race) in races.items():
    try:
        laps, session = load_race_data(year, race)
        laps['LapTimeSeconds'] = laps['LapTime'].dt.total_seconds()
        
        print(f'\n=== {name} ===')
        print(f'Total laps: {len(laps)}')
        
        # All non-null lap times
        valid_all = laps[laps['LapTime'].notna()].copy()
        valid_all['LapTimeSeconds'] = valid_all['LapTime'].dt.total_seconds()
        print(f'Valid laps (any time): {len(valid_all)}')
        min_time = valid_all['LapTimeSeconds'].min()
        max_time = valid_all['LapTimeSeconds'].max()
        print(f'Time range: {min_time:.2f}s - {max_time:.2f}s')
        
        # With 50-120 filter
        valid_filtered = valid_all[(valid_all['LapTimeSeconds'] > 50) & (valid_all['LapTimeSeconds'] < 120)]
        print(f'Valid laps (50-120s): {len(valid_filtered)}')
        if len(valid_filtered) > 0:
            fastest_filtered = valid_filtered.loc[valid_filtered['LapTimeSeconds'].idxmin()]
            print(f'Fastest (filtered): {fastest_filtered["Driver"]} - {fastest_filtered["LapTimeSeconds"]:.2f}s')
        
        # Without filter
        if len(valid_all) > 0:
            fastest_all = valid_all.loc[valid_all['LapTimeSeconds'].idxmin()]
            print(f'Fastest (no filter): {fastest_all["Driver"]} - {fastest_all["LapTimeSeconds"]:.2f}s')
        
        # Top 5 fastest
        print(f'Top 5 fastest laps:')
        for idx, row in valid_all.nsmallest(5, 'LapTimeSeconds').iterrows():
            print(f'  {row["Driver"]}: {row["LapTimeSeconds"]:.2f}s')
    except Exception as e:
        print(f'{name}: ERROR - {e}')
