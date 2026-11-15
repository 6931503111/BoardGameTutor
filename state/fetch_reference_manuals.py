"""Download reference material only. Does not modify the game database."""
import html
import json
import re
from pathlib import Path
from io import BytesIO

import httpx
from pypdf import PdfReader

root = Path('backend/data/reference_manuals')
root.mkdir(parents=True, exist_ok=True)
client = httpx.Client(timeout=60, follow_redirects=True)
page = client.get('https://www.explodingkittens.com/pages/rules-kittens')
page.raise_for_status()
links = sorted(set(html.unescape(link.replace('\\/', '/')) for link in re.findall(r'https[^\s<>"\']+\.pdf[^\s<>"\']*', page.text)))
english = next((link for link in links if re.search(r'English|_EN_|-EN-|/EN\.', link, re.I)), None)
entries = [
    {'key': 'sf', 'title': 'Spyfall — Cryptozoic base game', 'landing': 'https://cryptozoic.com/products/spyfall-game', 'url': 'https://cdn.shopify.com/s/files/1/0464/6961/1676/files/Spyfall1_Rules_compressed.pdf?v=1721920618'},
    {'key': 'mm', 'title': 'Mogel Motte — Schmidt Spiele', 'landing': 'https://www.schmidtspiele.de/details/produkt/mogel-motte.html', 'url': 'https://www.schmidtspiele.de/files/Produkte/4/40862%20-%20Mogel%20Motte/40862_MogelMotte.pdf'},
    {'key': 'for-sale', 'title': 'For Sale — IELLO EN V2', 'landing': 'https://iellogames.com/wp-content/uploads/2020/07/For-Sale_Rulebook_EN_V2.pdf', 'url': 'https://iellogames.com/wp-content/uploads/2020/07/For-Sale_Rulebook_EN_V2.pdf'},
    {'key': 'tb', 'title': 'คำต้องห้าม — คู่มือห้องสมุด มทร.รัตนโกสินทร์', 'landing': 'https://lib.rmutr.ac.th/wp-content/uploads/2025/08/wordgame_librmutr.pdf', 'url': 'https://lib.rmutr.ac.th/wp-content/uploads/2025/08/wordgame_librmutr.pdf'},
]
if english:
    entries.append({'key': 'ek', 'title': 'Exploding Kittens — Original Edition, English', 'landing': 'https://www.explodingkittens.com/pages/rules-kittens', 'url': english})
else:
    print('EK PDF candidates:', json.dumps(links, ensure_ascii=True), flush=True)
results = []
for entry in entries:
    try:
        response = client.get(entry['url'])
        response.raise_for_status()
        if not response.content.startswith(b'%PDF-'):
            raise ValueError('Not a PDF')
        (root / (entry['key'] + '.pdf')).write_bytes(response.content)
        reader = PdfReader(BytesIO(response.content))
        text = '\n\n'.join(f'[หน้า {index}]\n{page.extract_text() or ""}' for index, page in enumerate(reader.pages, 1))
        (root / (entry['key'] + '.txt')).write_text(text, encoding='utf-8')
        results.append({**entry, 'pages': len(reader.pages), 'characters': len(text), 'status': 'downloaded'})
    except Exception as error:
        results.append({**entry, 'status': 'failed', 'error': str(error)})
    print(json.dumps({k: results[-1][k] for k in ('key', 'status')}, ensure_ascii=True), flush=True)
(root / 'manifest.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
