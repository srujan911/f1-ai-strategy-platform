import requests
import json

print("Advanced What-If Simulation Testing\n" + "="*60)

# Test 1: Parameter sensitivity - same race with different parameters
test_params_variations = [
    {
        'name': 'Low Degradation',
        'params': {'deg_multiplier': 0.8, 'track_temperature': 1.0, 'traffic_factor': 1.0, 'safety_car_probability': 0.0, 'pit_loss': 20.0, 'inlap_delta': 0.5, 'outlap_delta': 1.0}
    },
    {
        'name': 'High Degradation',
        'params': {'deg_multiplier': 1.5, 'track_temperature': 1.1, 'traffic_factor': 1.2, 'safety_car_probability': 0.3, 'pit_loss': 25.0, 'inlap_delta': 1.0, 'outlap_delta': 1.5}
    },
    {
        'name': 'Safety Car Scenario',
        'params': {'deg_multiplier': 1.0, 'track_temperature': 1.0, 'traffic_factor': 1.0, 'safety_car_probability': 0.8, 'pit_loss': 22.0, 'inlap_delta': 0.8, 'outlap_delta': 1.2}
    },
    {
        'name': 'High Pit Loss',
        'params': {'deg_multiplier': 1.0, 'track_temperature': 1.0, 'traffic_factor': 1.0, 'safety_car_probability': 0.0, 'pit_loss': 35.0, 'inlap_delta': 0.8, 'outlap_delta': 1.2}
    }
]

print("\n1. Testing Parameter Sensitivity (Monaco)")
print("-" * 60)

for variant in test_params_variations:
    try:
        response = requests.post(
            'http://localhost:5000/api/strategy/simulate/2025/Monaco_Grand_Prix',
            json=variant['params']
        )
        
        if response.status_code == 200:
            data = response.json()
            rec = data.get('recommendation', {}).get('recommended', {})
            
            pit_stops = len(rec.get('pit_laps', []))
            compounds = rec.get('compounds', [])
            total_time = rec.get('total_time', 0)
            
            print(f"✓ {variant['name']}")
            print(f"  - Pit stops: {pit_stops}")
            print(f"  - Compounds: {' → '.join(compounds)}")
            print(f"  - Total time: {total_time:.0f}s")
        else:
            print(f"✗ {variant['name']} - Status {response.status_code}")
    except Exception as e:
        print(f"✗ {variant['name']} - Error: {str(e)[:50]}")

# Test 2: Short circuits vs Long circuits
print("\n2. Testing Different Track Types")
print("-" * 60)

test_tracks = [
    ('Monaco_Grand_Prix', 'Street Circuit (Short)'),
    ('Monza_Formula_1_Grand_Prix', 'Power Circuit (Long)'),
    ('Singapore_Grand_Prix', 'Street Circuit (Long)'),
    ('Azerbaijan_Grand_Prix', 'Street Circuit (Urban)')
]

params = {'deg_multiplier': 1.1, 'track_temperature': 1.05, 'traffic_factor': 1.0, 'safety_car_probability': 0.1, 'pit_loss': 22.0, 'inlap_delta': 0.8, 'outlap_delta': 1.2}

for track, description in test_tracks:
    try:
        response = requests.post(
            f'http://localhost:5000/api/strategy/simulate/2025/{track}',
            json=params
        )
        
        if response.status_code == 200:
            data = response.json()
            rec = data.get('recommendation', {}).get('recommended', {})
            meta = data.get('metadata', {})
            
            pit_stops = len(rec.get('pit_laps', []))
            total_time = rec.get('total_time', 0)
            avg_pit_stops = total_time / meta.get('total_laps', 1) if meta.get('total_laps') else 0
            
            print(f"✓ {description} ({track.replace('_', ' ')})")
            print(f"  - Pit stops: {pit_stops}")
            print(f"  - Total time: {total_time:.0f}s")
            print(f"  - Total laps: {meta.get('total_laps')}")
        else:
            print(f"✗ {description} - Status {response.status_code}")
    except Exception as e:
        print(f"✗ {description} - Error: {str(e)[:50]}")

# Test 3: Verify strategy diversity within same race
print("\n3. Testing Strategy Diversity (Australian GP)")
print("-" * 60)

try:
    response = requests.post(
        'http://localhost:5000/api/strategy/simulate/2025/Australian_Grand_Prix',
        json={'deg_multiplier': 1.1, 'track_temperature': 1.05, 'traffic_factor': 1.0, 'safety_car_probability': 0.1, 'pit_loss': 22.0, 'inlap_delta': 0.8, 'outlap_delta': 1.2}
    )
    
    if response.status_code == 200:
        data = response.json()
        strategies = data.get('strategies', [])
        
        print(f"✓ Total strategies: {len(strategies)}")
        for i, strat in enumerate(strategies[:5], 1):
            label = strat.get('label', 'N/A')
            pit_stops = len(strat.get('pit_laps', []))
            total_time = strat.get('total_time', 0)
            compounds = strat.get('compounds', [])
            
            print(f"  {i}. {label}")
            print(f"     Compounds: {' → '.join(compounds[:3])}")
            print(f"     Time: {total_time:.0f}s")
except Exception as e:
    print(f"✗ Error: {str(e)[:50]}")

print("\n" + "="*60)
print("✅ Advanced testing complete")
