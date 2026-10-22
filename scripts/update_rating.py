"""Read each apartment's rating and review count from its Gathern page into data.json."""
import re, sys, json, html
from concurrent.futures import ThreadPoolExecutor
from common import load, save, stamp, get


def unit_id(code):
    page = get(f'https://gathern.co/r/{code}')
    m = re.search(r'/unit/(\d+)', page)
    return m.group(1) if m else None


def num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def parse_rating(page):
    """Find the unit's rating (out of 10) and review count in a Gathern unit page."""
    raw = html.unescape(page).replace('\\"', '"')
    # 1) data embedded by the app
    for rk, ck in (('total_present', 'total_reviews'), ('rate', 'reviews_count'), ('rating', 'reviews_count'), ('rating', 'reviewsCount')):
        r = re.search(r'"%s"\s*:\s*"?([\d.]+)' % rk, raw)
        c = re.search(r'"%s"\s*:\s*"?(\d+)' % ck, raw)
        if r and c and num(r.group(1)) is not None and 0 < num(r.group(1)) <= 10:
            return r.group(1).rstrip('0').rstrip('.') if '.' in r.group(1) else r.group(1), int(c.group(1))
    # 2) visible text such as "9.9 ... (102 تقييم)"
    text = re.sub(r'<[^>]+>', ' ', raw)
    m = re.search(r'\b(10|[1-9](?:\.\d)?)\s*(?:/\s*10)?\s*\(?\s*(\d{1,5})\s*(?:تقييم|تقييمات|reviews?)', text)
    if m:
        return m.group(1), int(m.group(2))
    return None


def one(a):
    code = re.search(r'gathern\.co/r/([^/?#]+)', a.get('gathern') or '')
    if not code:
        return a['id'], None, None
    try:
        unit = a.get('unit') or unit_id(code.group(1))
        if not unit:
            return a['id'], None, None
        res = parse_rating(get(f'https://gathern.co/view/{unit}'))
        return a['id'], unit, res
    except Exception as e:
        print('  failed', a.get('name'), e, file=sys.stderr)
        return a['id'], None, None


def main():
    data = load()
    by = {a['id']: a for a in data['apts']}
    with ThreadPoolExecutor(6) as pool:
        results = list(pool.map(one, data['apts']))
    ok = 0
    for aid, unit, res in results:
        a = by[aid]
        if unit:
            a['unit'] = unit
        if res:
            a['rating'], a['reviews'] = res
            ok += 1
        else:
            print('no rating for', a.get('name'))
    print(f'updated {ok} of {len(results)}')
    if ok == 0:
        sys.exit(1)
    data['site']['rateAt'] = stamp()
    save(data)


if __name__ == '__main__':
    main()
