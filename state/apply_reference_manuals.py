"""Preserve all game content; add missing, inspected reference material only."""
import json
import sqlite3
from pathlib import Path
from backend.app import DATABASE_PATH, Game, read_games, write_game

root = Path('backend/data/reference_manuals')
manifest = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
backup = Path('backend/data/games_before_presentation.sqlite3')
if not backup.exists():
    with sqlite3.connect(DATABASE_PATH) as source, sqlite3.connect(backup) as target:
        source.backup(target)
thai_notes = '''[หน้า 2]
บันทึกสรุปที่ตรวจจากภาพคู่มือ ไม่ใช่ข้อความ OCR ดิบ
เริ่มโดยจัดผู้เล่นล้อมวง ใส่ที่คาดหัว และให้ผู้อื่นใส่คำโดยเจ้าของคำไม่เห็น การเล่นมีทั้งเดี่ยวและทีม ควรตกลงรูปแบบและเวลารอบให้ตรงกันก่อนเริ่ม

[หน้า 3]
แบบเดี่ยว: เมื่อพูดคำของตนเองให้เอาการ์ดออกและหยุดพูดจนจบรอบ ผู้ที่ล่อให้ผู้อื่นพูดคำได้เก็บคะแนน Kill และทำได้หลายครั้ง เมื่อหมดเวลา ผู้รอดได้คะแนนเพิ่ม และมีโอกาสทายคำของตนเองหนึ่งครั้งเพื่อรับคะแนนอีกส่วน เล่นต่อด้วยคำใหม่จนครบห้ารอบ
แบบทีม: แบ่งเป็นสองหรือสามทีม กระจายที่คาดหัวเท่า ๆ กัน ผู้เล่นรวมไม่เกินหกคน แต่ละทีมต้องไม่เห็นคำของทีมตนเอง การล่อและการคิดคะแนนพิจารณาเป็นทีม เมื่อหมดเวลานับคำที่ยังเหลือ และให้ทีมทายคำได้ครั้งเดียว จากนั้นเปลี่ยนคำแล้วเล่นต่อ

[หน้า 4]
แบบเดี่ยวให้รอดหนึ่งคะแนน ทายถูกหนึ่งคะแนน และ Kill หนึ่งคะแนนต่อคนที่ล่อสำเร็จ แบบทีมคิดหนึ่งคะแนนต่อคำที่เหลือ ต่อคำที่ทายถูก และต่อคำที่ล่อทีมอื่นสำเร็จ
ผู้ที่หลุดคำยังช่วยสังเกตจับผิดได้ แต่ไม่มีสิทธิ์พูดก่อนจบรอบ ถ้าหลายคนล่อด้วยคำถามเหมือนหรือใกล้กัน คะแนน Kill เป็นของคนเริ่มล่อก่อน
คำพ้องเสียงหรือพยางค์ควบกล้ำเดียวกันนับเป็นคำต้องห้าม ถ้าต้องการสื่อความหมายอื่นต้องออกเสียงเต็มคำให้ชัด เช่น ตัวอย่างในคู่มือแยกคำโดดออกจากคำเต็มอย่างขับรถหรือรดน้ำ ระยะเวลารอบปรับตามความเหมาะสมได้
'''
mapping = {'ek':'ek','sf':'sf','mm':'mm','tb':'tb'}
updates = []
for game in read_games():
    key = 'for-sale' if game['n'].lower() == 'for sale' else mapping.get(game['id'])
    if not key or game.get('source_text'):
        continue
    entry = next((entry for entry in manifest if entry['key']==key and entry['status']=='downloaded'), None)
    if entry is None:
        continue
    text = thai_notes if key == 'tb' else (root/(key+'.txt')).read_text(encoding='utf-8')
    if len(text) < 100:
        continue
    game.update(source_text=text, source_url=entry['landing'], edition=entry['title'],
                source_type='reviewed_notes' if key == 'tb' else 'manual')
    write_game(Game(**game))
    updates.append({'name':game['n'],'characters':len(text),'edition':game['edition']})
print(json.dumps({'backup':str(backup),'updated':updates},ensure_ascii=True))
