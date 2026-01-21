import requests
import json
import time

# Wait for server to be ready
time.sleep(2)

params = {
    'deg_multiplier': 1.1, 
    'track_temperature': 1.05, 
    'traffic_factor': 1.0, 
    'safety_car_probability': 0.1, 
    'pit_loss': 22.0, 
    'inlap_delta': 0.8, 
    'outlap_delta': 1.2
}

try:
    r = requests.post('http://localhost:5000/api/strategy/simulate/2025/Australian_Grand_Prix', json=params, timeout=30)
    print('Status:', r.status_code)
    
    if r.status_code == 200:
        data = r.json()
        print('\n✅ Response received successfully!')
        print('Response keys:', list(data.keys()))
        
        if 'strategies' in data:
            print(f"\nStrategies count: {len(data['strategies'])}")
            if data['strategies']:
                strat = data['strategies'][0]
                print('First strategy keys:', list(strat.keys()))
                print('First strategy sample:')
                print(f"  - Label: {strat.get('label')}")
                print(f"  - Variant: {strat.get('variant')}")
                print(f"  - Pit laps: {strat.get('pit_laps')}")
                print(f"  - Compounds: {strat.get('compounds')}")
                print(f"  - Total time: {strat.get('total_time')}")
        
        if 'recommendation' in data:
            rec = data['recommendation']
            print(f"\nRecommendation keys: {list(rec.keys())}")
            if 'recommended' in rec:
                print(f"Recommended: {rec['recommended'].get('compounds')} - {rec['recommended'].get('pit_laps')}")
                print(f"Confidence: {rec.get('confidence', 'N/A')}")
            
            if 'explanation' in rec:
                print(f"Explanation points: {len(rec['explanation'])}")
    else:
        print('Error response:')
        print(r.text)
        
except requests.exceptions.ConnectionError as e:
    print('❌ Connection failed - server not responding')
    print(str(e)[:100])
except Exception as e:
    print(f'❌ Error: {e}')
