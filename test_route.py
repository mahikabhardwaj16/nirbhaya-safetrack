import json
import urllib.request

from app import create_app
app = create_app()

with app.test_client() as client:
    res = client.post('/api/route/compute', json={
        'origin': 'N001',
        'destination': 'N007',
        'departure_time': '22:00',
        'mode': 'all',
        'user_preferences': {'crime': 0.3, 'lighting': 0.2, 'isolation': 0.2, 'crowd': 0.1, 'emergency': 0.1, 'transit': 0.1},
    })
    print(f'Status: {res.status_code}')
    data = json.loads(res.data)
    
    if res.status_code != 200:
        print(f'ERROR: {data}')
    else:
        print('Routes found:')
        for mode in ['fastest', 'safest', 'balanced']:
            if mode in data:
                r = data[mode]
                print(f'  {mode}: dist={r["distance_m"]}m, safety={r["safety_score"]}, segments={len(r["factor_breakdowns"])}')
                if r['factor_breakdowns']:
                    fb = r['factor_breakdowns'][0]
                    print(f'    factors: {json.dumps(fb)}')
        
        print(f'\nHealth: community_feedback_active={json.loads(client.get("/api/health").data)["community_feedback_active"]}')
        print('ALL GOOD')
