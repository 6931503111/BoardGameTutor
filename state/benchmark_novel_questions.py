"""Real-model paraphrase/follow-up audit; saved answers require human inspection."""
import json
import os
import time
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app import app, read_games

os.environ['BGT_ASSISTANT_MODEL'] = 'qwen3.5:4b'
client = TestClient(app)
games = read_games()
sale = next(game['id'] for game in games if game['n'].lower() == 'for sale')
cases = [
    ('ww', 'บทผู้หยั่งรู้สามารถตรวจบทบาทได้หลายคนในคืนเดียวหรือเปล่า', []),
    ('mm', 'ถ้าการ์ดกองกลางเป็น 5 ฉันลง 1 ได้หรือเปล่า', []),
    ('ek', 'ถ้าเพื่อนใช้ Defuse ฉันหยุดเขาด้วย Nope ได้หรือเปล่า', []),
    ('ek', 'แล้วใช้กับ Attack ล่ะ', [
        {'role':'user', 'content':'Nope ใช้ยกเลิก Defuse ได้ไหม'},
        {'role':'assistant', 'content':'Nope ยกเลิก Defuse ไม่ได้', 'source_ids':['R1'], 'status':'answered'}]),
    ('sf', 'เมื่อมีคนถามฉันแล้ว ฉันจะถามคำถามกลับไปหาเขาเลยได้หรือเปล่า', []),
    ('tb', 'ถ้าฉันเผลอพูดคำบนหน้าผากตัวเอง ฉันยังคุยในรอบนั้นต่อได้หรือเปล่า', []),
    (sale, 'ถอนตัวหลังวางธนบัตรไปห้าใบ จะได้กลับมาสองใบใช่หรือเปล่า', []),
    ('ek', 'ทำแบบนี้ได้ไหม', []),
    ('ww', 'ตัวละครนักเป่าขลุ่ยชนะอย่างไร', []),
]
results = []
for game_id, question, history in cases:
    start = time.monotonic()
    try:
        response = client.post(f'/api/games/{game_id}/ask', json={'question':question,'history':history})
        result = {'game_id':game_id,'question':question,'history':history,'http':response.status_code,**response.json()}
    except Exception as error:
        result = {'game_id':game_id,'question':question,'error':type(error).__name__}
    result['seconds'] = round(time.monotonic()-start,2)
    results.append(result)
    Path('state/presentation-novel-audit.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({key:value for key,value in result.items() if key != 'sources'},ensure_ascii=True),flush=True)
