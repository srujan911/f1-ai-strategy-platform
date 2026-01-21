import fastf1

# Direct FastF1 check
session_monaco = fastf1.get_session(2025, 'Monaco', 'R')
session_monaco.load()
laps_monaco = session_monaco.laps

# Clean approach
laps_clean = laps_monaco[laps_monaco['IsAccurate'] == True].copy()
laps_clean = laps_clean.dropna(subset=['LapTime', 'Driver'])
laps_clean = laps_clean[['Driver', 'Team', 'LapTime', 'LapNumber', 'Compound', 'TyreLife', 'Stint', 'IsAccurate', 'IsPersonalBest']]
laps_clean['LapTimeSeconds'] = laps_clean['LapTime'].dt.total_seconds()

fastest = laps_clean.loc[laps_clean['LapTimeSeconds'].idxmin()]
print('Monaco Fastest:', fastest['Driver'], fastest['LapTimeSeconds'])

# Qatar
session_qatar = fastf1.get_session(2025, 'Qatar', 'R')
session_qatar.load()
laps_qatar = session_qatar.laps

laps_clean_q = laps_qatar[laps_qatar['IsAccurate'] == True].copy()
laps_clean_q = laps_clean_q.dropna(subset=['LapTime', 'Driver'])
laps_clean_q = laps_clean_q[['Driver', 'Team', 'LapTime', 'LapNumber', 'Compound', 'TyreLife', 'Stint', 'IsAccurate', 'IsPersonalBest']]
laps_clean_q['LapTimeSeconds'] = laps_clean_q['LapTime'].dt.total_seconds()

fastest_q = laps_clean_q.loc[laps_clean_q['LapTimeSeconds'].idxmin()]
print('Qatar Fastest:', fastest_q['Driver'], fastest_q['LapTimeSeconds'])
