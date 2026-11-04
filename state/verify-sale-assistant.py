import json
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app import app, read_games

game = next(game for game in read_games() if game['n'].lower() == 'for sale')
client = TestClient(app)
results = []
for question in ['ถ้าเงินประมูลบ้านล่าสุด 4000 เราสามารถเสนอ 300 ได้ไหม', 'ถ้าเงินไม่พอขอเงินคนอื่นมาได้ไหม']:
    response = client.post(f"/api/games/{game['id']}/ask", json={'question': question})
    results.append({'question': question, 'http': response.status_code, 'response': response.json()})
    print(json.dumps(results[-1], ensure_ascii=True), flush=True)
Path('state/sale-assistant-smoke.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
