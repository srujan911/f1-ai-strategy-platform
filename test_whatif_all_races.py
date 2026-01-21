import requests
import json

# Get all available races
races_response = requests.get('http://localhost:5000/api/races')
races_data = races_response.json()

print("Testing What-If Simulation for All Races\n" + "="*60)

test_params = {
    'deg_multiplier': 1.1,
    'track_temperature': 1.05,
    'traffic_factor': 1.0,
    'safety_car_probability': 0.1,
    'pit_loss': 22.0,
    'inlap_delta': 0.8,
    'outlap_delta': 1.2
}

success_count = 0
failed_races = []

for race in races_data:
    year = race['year']
    # Extract race name from id (e.g., '2025_Australian_Grand_Prix' -> 'Australian_Grand_Prix')
    race_id = race['id']
    gp_name = '_'.join(race_id.split('_')[1:]) if '_' in race_id else race_id
    name = race['name']
    
    try:
        # Test the simulation endpoint
        response = requests.post(
            f'http://localhost:5000/api/strategy/simulate/{year}/{gp_name}',
            json=test_params
        )
        
        if response.status_code == 200:
            data = response.json()
            strategies = data.get('strategies', [])
            recommendation = data.get('recommendation', {})
            metadata = data.get('metadata', {})
            
            print(f"✓ {name}")
            if strategies:
                print(f"  - Strategies: {len(strategies)} available")
                best = strategies[0]
                label = best.get('label', 'N/A')
                num_stops = len(best.get('pit_laps', []))
                total_time = best.get('total_time', 0)
                print(f"  - Top strategy: {label} ({num_stops} stops, {total_time:.0f}s)")
            if recommendation:
                rec_label = recommendation.get('recommended', {}).get('variant', 'N/A')
                rec_stops = len(recommendation.get('recommended', {}).get('pit_laps', []))
                rec_time = recommendation.get('recommended', {}).get('total_time', 0)
                print(f"  - Recommendation: {rec_label} ({rec_stops} stops, {rec_time:.0f}s)")
            success_count += 1
        else:
            print(f"✗ {name} - Status {response.status_code}")
            failed_races.append(name)
    except Exception as e:
        print(f"✗ {name} - Error: {str(e)[:60]}")
        failed_races.append(name)

print("\n" + "="*60)
print(f"Summary: {success_count}/{len(races_data)} races passed")
if failed_races:
    print(f"Failed races: {', '.join(failed_races)}")
