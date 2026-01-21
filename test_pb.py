from src.data_loader import load_race_data

races = {
    'Monaco': (2025, '2025-05-25_Monaco_Grand_Prix'),
    'Qatar': (2025, '2025-11-30_Qatar_Grand_Prix')
}

for name, (year, race) in races.items():
    try:
        laps, session = load_race_data(year, race)
        print(f'\n=== {name} ===')
        print('Columns:', laps.columns.tolist())
        
        # Check personal best laps
        pb_laps = laps[laps['IsPersonalBest'] == True]
        print('Personal best laps:', len(pb_laps))
        
        if len(pb_laps) > 0:
            pb_laps_copy = pb_laps.copy()
            pb_laps_copy['LapTimeSeconds'] = pb_laps_copy['LapTime'].dt.total_seconds()
            fastest_pb = pb_laps_copy.loc[pb_laps_copy['LapTimeSeconds'].idxmin()]
            print('Fastest personal best:', fastest_pb['Driver'], '-', round(fastest_pb['LapTimeSeconds'], 2), 's')
    except Exception as e:
        print(name + ': ERROR - ' + str(e))
