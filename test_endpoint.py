import requests
import json

params = {'deg_multiplier': 1.1}

print("=" * 60)
print("Testing /api/strategy/simulate endpoint")
print("=" * 60)

try:
    print("Sending POST request to http://127.0.0.1:5000/api/strategy/simulate/2025/Australian_Grand_Prix")
    print(f"Parameters: {json.dumps(params)}\n")
    
    response = requests.post(
        'http://127.0.0.1:5000/api/strategy/simulate/2025/Australian_Grand_Prix',
        json=params,
        timeout=120  # Long timeout to wait for processing
    )
    
    print(f"✓ Response received!")
    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    
    data = response.json()
    print(f"\nResponse structure:")
    print(f"  - strategies: {len(data.get('strategies', []))} items")
    print(f"  - recommendation: {'present' if 'recommendation' in data else 'missing'}")
    print(f"  - metadata: {'present' if 'metadata' in data else 'missing'}")
    
    if data.get('strategies'):
        print(f"\nFirst strategy details:")
        s = data['strategies'][0]
        for key, value in s.items():
            if isinstance(value, (list, dict)):
                print(f"    {key}: {type(value).__name__} with {len(value) if hasattr(value, '__len__') else '?'} items")
            else:
                print(f"    {key}: {value}")
    
    if data.get('recommendation'):
        rec = data['recommendation']
        print(f"\nRecommendation details:")
        print(f"    confidence: {rec.get('confidence', 'N/A')}")
        print(f"    explanation: {len(rec.get('explanation', []))} points")
        if rec.get('recommended'):
            r = rec['recommended']
            print(f"    recommended compounds: {r.get('compounds')}")
            print(f"    recommended pit_laps: {r.get('pit_laps')}")
    
    print("\n✓ Everything looks good!")
    
except requests.exceptions.Timeout:
    print("✗ Request timed out after 120 seconds")
    print("  The simulation endpoint is taking too long to respond")
except requests.exceptions.ConnectionError as e:
    print("✗ Connection error:")
    print(f"  {str(e)[:200]}")
except json.JSONDecodeError:
    print("✗ Response is not valid JSON")
    print(f"Response text: {response.text[:500]}")
except Exception as e:
    print(f"✗ Error: {type(e).__name__}")
    print(f"  {str(e)[:200]}")

print("=" * 60)
