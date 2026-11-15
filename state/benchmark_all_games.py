"""Live, game-scoped presentation audit. HTTP success is not scored as accuracy."""
import asyncio
import json
import re
import time
from pathlib import Path

from fastapi.testclient import TestClient
from backend.app import app, read_games
from backend.rule_assistant import knowledge
from backend.semantic_search import embeddings

cases = {
    'ek': [('Nope ใช้ยกเลิก Defuse ได้ไหม', r'ไม่ได้|ไม่สามารถ|ยกเว้น'), ('โดน Attack แล้วใช้ Skip หนึ่งใบ ยังต้องเล่นอีกกี่ตา', r'1|หนึ่ง')],
    'mm': [('แมลงยามสามารถโกงได้ไหม', r'ไม่ได้|ห้าม|ไม่สามารถ'), ('ไพ่บนกองเป็นเลข 5 ลงเลขอะไรได้บ้าง', r'1|หนึ่ง')],
    'sf': [('ถามคนที่เพิ่งถามเรากลับทันทีได้ไหม', r'ไม่ได้|ห้าม|ไม่สามารถ'), ('สายลับเดาสถานที่ผิดใครชนะ', r'ไม่ใช่สายลับ|คนอื่น|ชาว|ผู้เล่นอื่น|Non')],
    'tb': [('หลุดคำต้องห้ามแล้วยังพูดต่อได้ไหม', r'ไม่ได้|เงียบ|หยุดพูด|ห้าม'), ('หมดเวลาแล้วทายคำได้กี่ครั้ง', r'1|หนึ่ง')],
    'ww': [('ผู้หยั่งรู้ดูได้กี่คนต่อคืน', r'1|หนึ่ง'), ('หมาป่าเหลือ 2 คน ชาวบ้านเหลือ 2 คน ฝ่ายไหนชนะ', r'^(?:ฝ่าย)?หมาป่า.{0,25}ชนะ')],
    'for-sale': [('ล่าสุดประมูล 4000 เราเสนอ 3000 ได้ไหม', r'ไม่ได้'), ('บอกผ่านประมูลจะได้เงินคืนเท่าไร', r'ครึ่ง|half')],
}
client = TestClient(app)
results = []
for game in read_games():
    key = 'for-sale' if game['n'].lower()=='for sale' else game['id']
    for question, expected in cases.get(key, []):
        started = time.monotonic()
        try:
            response = client.post(f"/api/games/{game['id']}/ask", json={'question':question})
            data = response.json()
            result = {'game':game['n'], 'game_id':game['id'], 'question':question,
                      'http':response.status_code, 'status':data.get('status'), 'answer':data.get('answer',data.get('detail')),
                      'source_ids':[source['id'] for source in data.get('sources',[])],
                      'expected_pattern':expected,
                      'text_check':bool(data.get('status') in {'answered','partial'} and re.search(expected,data.get('answer',''),re.I)),
                      'seconds':round(time.monotonic()-started,2)}
        except Exception as error:
            result={'game':game['n'],'question':question,'error':type(error).__name__,'seconds':round(time.monotonic()-started,2)}
        results.append(result)
        Path('state/presentation-live-audit.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(result,ensure_ascii=True),flush=True)
