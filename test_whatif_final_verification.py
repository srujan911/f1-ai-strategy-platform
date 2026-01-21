import requests
import json

print("F1 AI Strategy Platform - What-If Simulation Verification Report")
print("="*70)

# Get all races
races_response = requests.get('http://localhost:5000/api/races')
races_data = races_response.json()

base_params = {
    'deg_multiplier': 1.1,
    'track_temperature': 1.05,
    'traffic_factor': 1.0,
    'safety_car_probability': 0.1,
    'pit_loss': 22.0,
    'inlap_delta': 0.8,
    'outlap_delta': 1.2
}

# Collect statistics
stats = {
    'total_races': len(races_data),
    'successful_races': 0,
    'failed_races': [],
    'pit_stop_distribution': {},
    'min_time': float('inf'),
    'max_time': 0,
    'avg_strategies': 0,
    'total_strategies': 0
}

print(f"\nTesting {len(races_data)} races for what-if simulation...")
print("-"*70)

for i, race in enumerate(races_data, 1):
    year = race['year']
    race_id = race['id']
    gp_name = '_'.join(race_id.split('_')[1:])
    name = race['name']
    
    try:
        response = requests.post(
            f'http://localhost:5000/api/strategy/simulate/{year}/{gp_name}',
            json=base_params,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            strategies = data.get('strategies', [])
            recommendation = data.get('recommendation', {})
            rec_data = recommendation.get('recommended', {})
            
            if strategies and rec_data:
                pit_stops = len(rec_data.get('pit_laps', []))
                total_time = rec_data.get('total_time', 0)
                
                # Update statistics
                stats['successful_races'] += 1
                stats['total_strategies'] += len(strategies)
                stats['min_time'] = min(stats['min_time'], total_time)
                stats['max_time'] = max(stats['max_time'], total_time)
                
                # Track pit stop distribution
                pit_key = f"{pit_stops}-stop"
                stats['pit_stop_distribution'][pit_key] = stats['pit_stop_distribution'].get(pit_key, 0) + 1
                
                print(f"✓ ({i:2d}/48) {name[:40]:40} | {pit_stops}-stop | {total_time:6.0f}s")
            else:
                stats['failed_races'].append(name)
                print(f"✗ ({i:2d}/48) {name[:40]:40} | Incomplete response")
        else:
            stats['failed_races'].append(name)
            print(f"✗ ({i:2d}/48) {name[:40]:40} | HTTP {response.status_code}")
    except Exception as e:
        stats['failed_races'].append(name)
        print(f"✗ ({i:2d}/48) {name[:40]:40} | Error: {str(e)[:30]}")

# Calculate averages
stats['avg_strategies'] = stats['total_strategies'] / max(stats['successful_races'], 1)

print("\n" + "="*70)
print("WHAT-IF SIMULATION RESULTS SUMMARY")
print("="*70)

print(f"\nSuccess Rate:")
print(f"   Total races tested: {stats['total_races']}")
print(f"   Successful simulations: {stats['successful_races']}/{stats['total_races']} ({100*stats['successful_races']/stats['total_races']:.1f}%)")
print(f"   Failed races: {len(stats['failed_races'])}")

print(f"\nStrategy Distribution:")
print(f"   Total strategies generated: {stats['total_strategies']}")
print(f"   Average strategies per race: {stats['avg_strategies']:.1f}")

print(f"\nPit Stop Distribution:")
for stops in sorted(stats['pit_stop_distribution'].keys()):
    count = stats['pit_stop_distribution'][stops]
    percentage = 100 * count / stats['successful_races']
    print(f"   {stops}: {count} races ({percentage:.1f}%)")

print(f"\nRace Time Statistics:")
print(f"   Shortest race: {stats['min_time']:.0f}s")
print(f"   Longest race: {stats['max_time']:.0f}s")
print(f"   Time range: {stats['max_time'] - stats['min_time']:.0f}s")

print(f"\nSimulation Parameters Used:")
for key, value in base_params.items():
    print(f"   {key}: {value}")

print("\n" + "="*70)
print("WHAT-IF SIMULATION SYSTEM VERIFICATION COMPLETE")
print("="*70)

if stats['successful_races'] == stats['total_races']:
    print("[SUCCESS] All races simulating successfully!")
elif stats['successful_races'] > stats['total_races'] * 0.95:
    print("[SUCCESS] Excellent coverage - 95%+ of races working")
elif stats['successful_races'] > stats['total_races'] * 0.80:
    print("[SUCCESS] Good coverage - 80%+ of races working")
else:
    print(f"[WARNING] Coverage below 80% - {stats['successful_races']} races working")
    if stats['failed_races']:
        print(f"\nFailed races: {', '.join(stats['failed_races'][:5])}")
        if len(stats['failed_races']) > 5:
            print(f"... and {len(stats['failed_races']) - 5} more")
