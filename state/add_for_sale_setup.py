"""Thai transcription checked against the setup table on rulebook page 3."""
from backend.app import Game, read_games, write_game

game = next(game for game in read_games() if game['n'].lower() == 'for sale')
title = 'เงินเริ่มเกมและการเตรียมเกม (คู่มือหน้า 3)'
content = '''ฉบับอ้างอิง: For Sale — IELLO EN V2 กติกาหลัก หน้า 2–3
แจกเงินเริ่มต้นให้ผู้เล่นแต่ละคนตามจำนวนผู้เล่น ธนบัตรแต่ละใบมีมูลค่า $1,000 เป็นหน่วยเงินในเกมตามคู่มือ:
- เล่น 3 คน: คนละ 28 ใบ รวม $28,000
- เล่น 4 คน: คนละ 21 ใบ รวม $21,000
- เล่น 5 คน: คนละ 16 ใบ รวม $16,000
- เล่น 6 คน: คนละ 14 ใบ รวม $14,000
ผู้เล่นเก็บธนบัตรคว่ำหน้าได้
แยกไพ่บ้าน ไพ่เช็ค และธนบัตร สับกองบ้านและกองเช็คแยกกัน ถ้าเล่น 4 คน ให้นำไพ่บนสุด 2 ใบของกองบ้านและกองเช็คแต่ละกองออกโดยไม่ดู
สุ่มผู้เริ่มเล่นรอบแรก จำนวนเงินเริ่มต้นนี้ใช้กับฉบับที่อ้างอิง หากใช้ฉบับอื่นต้องตรวจคู่มือฉบับนั้น'''
game['r'] = [rule for rule in game['r'] if rule[0] != title] + [[title, content]]
write_game(Game(**game))
print('Added setup information checked against the pictured table; no canned answer added.')
