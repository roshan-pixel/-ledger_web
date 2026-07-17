from app import app
import json

with app.app_context():
    client = app.test_client()
    resp = client.get('/api/kpi')
    print(json.dumps(resp.get_json(), indent=2))
