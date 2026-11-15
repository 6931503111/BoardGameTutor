import json
from pathlib import Path

from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)
first = client.post('/api/games/ek/ask', json={'question': 'Nope ใช้ยกเลิก Defuse ได้ไหม'})
results = [{'turn': 1, 'http': first.status_code, 'response': first.json()}]
if first.status_code == 200:
    result = first.json()
    history = [
        {'role': 'user', 'content': 'Nope ใช้ยกเลิก Defuse ได้ไหม'},
        {'role': 'assistant', 'content': result['answer'], 'status': result['status'],
         'source_ids': [source['id'] for source in result['sources']]},
    ]
    second = client.post('/api/games/ek/ask', json={'question': 'แล้วถ้าใช้ Nope ยกเลิก Nope ของอีกคนล่ะ', 'history': history})
    results.append({'turn': 2, 'http': second.status_code, 'response': second.json()})
Path('state/rule-assistant-smoke.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
for result in results:
    response = result['response']
    print(json.dumps({'turn': result['turn'], 'http': result['http'], 'status': response.get('status'),
                      'answer': response.get('answer', response.get('detail')),
                      'sources': [source['id'] for source in response.get('sources', [])]}, ensure_ascii=True))
