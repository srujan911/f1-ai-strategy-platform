import requests
import json

races = [
    ('2025-05-25_Monaco_Grand_Prix', 'Monaco'),
    ('2025-11-30_Qatar_Grand_Prix', 'Qatar')
]

for gp_name, label in races:
    try:
        r = requests.get(f'http://localhost:5000/api/race/2025/{gp_name}')
        data = r.json()
        fl = data['fastest_lap']
        print(f'{label}: {fl["driver"]} - {fl["time"]:.2f}s')
    except Exception as e:
        print(f'{label}: ERROR - {e}')
