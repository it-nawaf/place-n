"""Temporary: save long Arabic text pieces from two Gathern unit pages, to find their descriptions."""
import re, json, html, os
from common import get
os.makedirs('debug', exist_ok=True)
for name, unit, code in (('203', '216360', 'eb7Mdf'), ('208', '205837', 'w1rJdY')):
    out = []
    for url in (f'https://gathern.co/view/{unit}', f'https://gathern.co/r/{code}'):
        try:
            raw = html.unescape(get(url)).replace('\\n', '\n').replace('\\"', '"')
        except Exception as e:
            out.append(f'ERR {url} {e}'); continue
        out.append(f'=== {url} len={len(raw)}')
        for m in re.finditer(r'[؀-ۿ][^"<>{}]{60,}', raw):
            s = m.group(0).strip()
            if s not in out:
                out.append(s)
    open(f'debug/{name}.txt', 'w', encoding='utf-8').write('\n---\n'.join(out))
