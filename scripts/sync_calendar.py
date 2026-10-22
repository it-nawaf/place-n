"""Pull booked nights from each apartment's Gathern / Airbnb iCal links into data.json.

Only writes the file when something changed, so the workflow commits only real changes.
"""
import re, sys, time, datetime as dt
from concurrent.futures import ThreadPoolExecutor
from common import load, save, now, stamp, get


def nights(ics):
    """Return the set of booked nights (YYYY-MM-DD) in an iCalendar text, or None if it is not one."""
    if 'BEGIN:VCALENDAR' not in ics:
        return None
    text = re.sub(r'\r?\n[ \t]', '', ics)  # unfold lines
    out = set()
    for ev in re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', text, re.S):
        s = re.search(r'^DTSTART[^:\n]*:(\d{8})', ev, re.M)
        e = re.search(r'^DTEND[^:\n]*:(\d{8})', ev, re.M)
        if not s:
            continue
        d0 = dt.datetime.strptime(s.group(1), '%Y%m%d').date()
        d1 = dt.datetime.strptime(e.group(1), '%Y%m%d').date() if e else d0 + dt.timedelta(days=1)
        d = d0
        while d < d1:
            out.add(d.isoformat())
            d += dt.timedelta(days=1)
    return out


def fresh(url, shift=0):
    """Gathern serves an old cached copy of a calendar link for hours; percent-encoding two
    characters of the file name (same file, new spelling) gets a fresh copy."""
    b = int(time.time() // 120) + shift
    m = re.match(r'(https://[^/]*gathern\.co/.*/)([^/?]+)(\.ics)(.*)$', url)
    if m:
        n = m.group(2); L = len(n); i = b % L; j = (i + 1 + (b // L) % (L - 1)) % L
        url = m.group(1) + ''.join('%%%02X' % ord(c) if k in (i, j) else c for k, c in enumerate(n)) + m.group(3) + m.group(4)
    return url + ('&' if '?' in url else '?') + f'_={b}'


def fetch(url):
    for attempt in range(2):
        try:
            return nights(get(fresh(url, attempt * 7)))
        except Exception as e:  # network error -> retry once
            err = e
            time.sleep(2)
    print('  fetch failed:', url[:60], err, file=sys.stderr)
    return None


def main():
    data = load()
    cutoff = (now().date() - dt.timedelta(days=7)).isoformat()
    jobs = {}
    with ThreadPoolExecutor(8) as pool:
        for a in data['apts']:
            for k in ('ical', 'ical2'):
                u = (a.get(k) or '').strip()
                if u.startswith('https://'):
                    jobs[(a['id'], k)] = pool.submit(fetch, u)
    changed, failed = [], []
    for a in data['apts']:
        res = [jobs[(a['id'], k)].result() for k in ('ical', 'ical2') if (a['id'], k) in jobs]
        if not res:
            continue
        good = [r for r in res if r is not None]
        if not good:
            failed.append(a.get('name') or a['id'])
            continue
        new = sorted(d for d in set().union(*good) if d >= cutoff)
        if new != (a.get('sync') or []):
            a['sync'] = new
            a['syncAt'] = stamp()
            changed.append(a.get('name') or a['id'])
    if changed:
        save(data)
    print('changed:', ', '.join(changed) or 'none')
    if failed:
        print('failed:', ', '.join(failed))
    if failed and len(failed) == len([a for a in data['apts'] if a.get('ical') or a.get('ical2')]):
        sys.exit(1)  # every feed failed: mark the run as failed so it shows in the admin page


if __name__ == '__main__':
    main()
