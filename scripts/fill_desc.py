"""Fill empty apartment descriptions from each unit's Gathern page (never overwrites a description)."""
import re, sys, json, html
from common import load, save, get


def find_desc(page):
    raw = html.unescape(page)
    best = ''
    for m in re.finditer(r'"(?:description|desc|unit_description|chalet_description)"\s*:\s*"((?:[^"\\]|\\.)*)"', raw):
        try:
            s = json.loads('"' + m.group(1) + '"')
        except Exception:
            continue
        if re.search(r'[؀-ۿ]', s) and len(s) > len(best):
            best = s
    if not best:
        m = re.search(r'<meta[^>]+(?:name|property)="(?:og:)?description"[^>]+content="([^"]+)"', page)
        if m:
            best = html.unescape(m.group(1))
    return best.strip()


def main():
    data = load()
    n = 0
    for a in data['apts']:
        if a.get('desc') or not a.get('unit'):
            continue
        try:
            d = find_desc(get(f"https://gathern.co/view/{a['unit']}"))
        except Exception as e:
            print('failed', a.get('name'), e)
            continue
        print(a.get('name'), '->', d[:80].replace('\n', ' '))
        if len(d) > 40:
            a['desc'] = d
            n += 1
    print('filled', n)
    if n:
        save(data)


if __name__ == '__main__':
    main()
