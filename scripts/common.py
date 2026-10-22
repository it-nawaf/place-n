"""Shared helpers for the place.n data scripts."""
import json, urllib.request, datetime as dt

DATA = 'data.json'
RIYADH = dt.timezone(dt.timedelta(hours=3))
MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'


def load():
    with open(DATA, encoding='utf-8') as f:
        return json.load(f)


def save(d):
    with open(DATA, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
        f.write('\n')


def now():
    return dt.datetime.now(RIYADH)


def stamp():
    n = now()
    h = n.hour % 12 or 12
    return f"{n.day} {MONTHS[n.month - 1]}، {h}:{n.minute:02d} {'ص' if n.hour < 12 else 'م'}"


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'ar,en;q=0.8', 'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', 'replace')
