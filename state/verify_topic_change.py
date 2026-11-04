import json
import os
import time
from pathlib import Path
import httpx

client=httpx.Client(base_url='http://127.0.0.1:8000',timeout=180)
game=next(game for game in client.get('/api/games').json() if game['n'].lower()=='for sale')
history=[{'role':'user','content':'บอกผ่านประมูลจะได้เงินคืนเท่าไร'},
         {'role':'assistant','content':game['verified_qa'][0]['answer'],'source_ids':['R1'],'status':'answered'}]
cases=[(game['id'],'เงินเริ่มเกมจะมีกี่เท่าไหร่',history),
       (game['id'],'แล้วเงินตอนเริ่มเกมมีเท่าไหร่',history),
       (game['id'],'ถ้าเล่น 4 คนล่ะ',[
           {'role':'user','content':'เงินเริ่มเกมจะมีเท่าไหร่'},
           {'role':'assistant','content':'เงินเริ่มต้นตามจำนวนผู้เล่น เล่น 3 คนคนละ 28000 เล่น 4 คนคนละ 21000 เล่น 5 คนคนละ 16000 เล่น 6 คนคนละ 14000','source_ids':['R3'],'status':'answered'}]),
       ('ek','แล้วใช้กับ Attack ล่ะ',[
           {'role':'user','content':'Nope ใช้ยกเลิก Defuse ได้ไหม'},
           {'role':'assistant','content':'Nope ยกเลิก Defuse ไม่ได้','source_ids':['R1'],'status':'answered'}])]
if os.environ.get('BGT_TOPIC_CHECK_FINAL'):
    cases=[cases[0],cases[3]]
rows=[]
for game_id,question,conversation in cases:
    started=time.monotonic()
    response=client.post(f'/api/games/{game_id}/ask',json={'question':question,'history':conversation})
    data=response.json()
    rows.append({'question':question,'history':conversation,'http':response.status_code,**data,'seconds':round(time.monotonic()-started,2)})
    Path('state/topic-change-verification.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({key:value for key,value in rows[-1].items() if key not in ['sources','history']},ensure_ascii=True),flush=True)
