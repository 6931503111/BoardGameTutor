import html
import json
import re
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin
import httpx
from pypdf import PdfReader

root = Path('backend/data/reference_manuals')
client = httpx.Client(timeout=60, follow_redirects=True)
page = client.get('https://www.schmidtspiele.de/details/produkt/mogel-motte.html')
page.raise_for_status()
href = next(html.unescape(link) for link in re.findall(r'href="([^"]+\.pdf[^"]*)"', page.text) if '40862' in link)
url = urljoin('https://www.schmidtspiele.de/', href)
response = client.get(url)
response.raise_for_status()
reader = PdfReader(BytesIO(response.content))
texts = [page.extract_text() or '' for page in reader.pages]
english_pages = [index for index, text in enumerate(texts) if re.search('Guard Bug|How to play|Cheating Moth|Mosquito|Spider', text)]
text = '\n\n'.join(f'[หน้า {index+1}]\n{texts[index]}' for index in english_pages)
if len(text) < 200:
    raise ValueError('English text not found; manual review required')
(root/'mm.pdf').write_bytes(response.content)
(root/'mm.txt').write_text(text, encoding='utf-8')
manifest = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
for entry in manifest:
    if entry['key']=='mm':
        entry.update(url=url, status='downloaded', pages=len(reader.pages), characters=len(text))
        entry.pop('error', None)
(root/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'url':url,'pages':len(reader.pages),'english_pages':english_pages,'characters':len(text)}))
