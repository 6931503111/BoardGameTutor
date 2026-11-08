import json
import time
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app import app

client=TestClient(app)
cases=[('ek','แล้วใช้กับ Attack ล่ะ',[
    {'role':'user','content':'Nope ใช้ยกเลิก Defuse ได้ไหม'},
    {'role':'assistant','content':'Nope ยกเลิก Defuse ไม่ได้','source_ids':['R1'],'status':'answered'}]),
    ('sf','เมื่อมีคนถามฉันแล้ว ฉันจะถามคำถามกลับไปหาเขาเลยได้หรือเปล่า',[])]
rows=[]
for game_id,question,history in cases:
    started=time.monotonic()
    response=client.post(f'/api/games/{game_id}/ask',json={'question':question,'history':history})
    rows.append({'question':question,'history':history,'http':response.status_code,**response.json(),'seconds':round(time.monotonic()-started,2)})
    Path('state/presentation-final-cases.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print(game_id,response.status_code,response.json().get('status'),response.json().get('method'),flush=True)
