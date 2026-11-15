"""Read-only checks. Run before opening the demonstration."""
import json
import os
import sys
from pathlib import Path

import httpx

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

checks = []
client = httpx.Client(timeout=10)
def check(name, url):
    try:
        response = client.get(url)
        response.raise_for_status()
        checks.append({'name':name,'ok':True})
        return response
    except httpx.HTTPError as error:
        checks.append({'name':name,'ok':False,'detail':str(error)})

check('หน้าเว็บ', 'http://127.0.0.1:5500')
backend = check('Backend', 'http://127.0.0.1:8000/api/health')
tags = check('Ollama', 'http://127.0.0.1:11434/api/tags')
if tags:
    names = {item['name'] for item in tags.json().get('models',[])}
    active = backend.json() if backend else {}
    models = [active.get('assistant_model', os.environ.get('BGT_ASSISTANT_MODEL','qwen3.5:4b')),
              active.get('embedding_model', os.environ.get('BGT_EMBED_MODEL','embeddinggemma'))]
    for model in models:
        checks.append({'name':'โมเดล '+model,'ok':model in names or model+':latest' in names})
games = []
if backend:
    response = check('ฐานข้อมูลเกม', 'http://127.0.0.1:8000/api/games')
    if response:
        for game in response.json():
            games.append({'name':game['n'],'rules':len(game.get('r',[])),
                          'manual_characters':len(game.get('source_text') or ''),
                          'edition':game.get('edition') or 'ยังไม่ระบุฉบับ',
                          'quiz':len(game.get('qz',[]))})
report = {'services':checks,'games':games,
          'note':'ตรวจบริการและความครบของข้อมูลเท่านั้น ไม่ใช่การรับรองความถูกต้องของคำตอบ AI ทุกคำถาม'}
root = Path(__file__).resolve().parents[1]
(root/'state').mkdir(exist_ok=True)
(root/'state'/'presentation-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
for item in checks:
    print(('พร้อม' if item['ok'] else 'ต้องแก้')+' — '+item['name'])
for game in games:
    print(f"{game['name']}: {game['rules']} กฎ, คู่มือ {game['manual_characters']:,} ตัวอักษร, {game['quiz']} ข้อสอบ; {game['edition']}")
print(report['note'])
sys.exit(0 if all(item['ok'] for item in checks) else 1)
