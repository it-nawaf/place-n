"""Make a share-ready page for every apartment: place-n.com/<number>/

Each page is index.html with its own title, description and preview image, so a link
sent on WhatsApp shows that apartment's photo and name. The script also crops a
800x800 preview image (og/<number>.jpg) from the apartment's cover photo.
"""
import os, re, json, shutil, html
from common import load

SITE = 'https://place-n.com/'
TYPES = {1: 'غرفة وصالة', 2: 'غرفتين وصالة', 3: 'ثلاث غرف وصالة'}
LIST = 'pages.json'  # folders this script made, so removed apartments get cleaned up


def slug(a):
    m = re.findall(r'\d+', a.get('name') or '')
    return m[-1] if m else a['id']


def cover(a):
    p = (a.get('photos') or [{}])[0]
    if p.get('f'):
        return p['f']
    if p.get('a'):
        return f"img/{p['a']}.jpg"
    return None


def preview(src, dest):
    """Crop the cover photo to 800x800 for link previews. Returns True when made."""
    try:
        from PIL import Image
    except ImportError:
        return False
    if not src or not os.path.exists(src):
        return False
    if os.path.exists(dest) and os.path.getmtime(dest) >= os.path.getmtime(src) and os.path.getmtime(dest) >= os.path.getmtime(__file__):
        return True
    im = Image.open(src).convert('RGB')
    w, h = im.size
    tw, th = 800, 800
    s = max(tw / w, th / h)
    im = im.resize((round(w * s), round(h * s)), Image.LANCZOS)
    l, t = (im.width - tw) // 2, (im.height - th) // 2
    im.crop((l, t, l + tw, t + th)).save(dest, 'JPEG', quality=82, optimize=True)
    return True


def meta(title, desc, url, image):
    e = lambda s: html.escape(s, quote=True)
    return ('<!--og--><meta name="description" content="%s">'
            '<meta property="og:site_name" content="place.n">'
            '<meta property="og:title" content="%s"><meta property="og:description" content="%s">'
            '<meta property="og:type" content="website"><meta property="og:url" content="%s">'
            '<meta property="og:image" content="%s"><meta property="og:image:width" content="800"><meta property="og:image:height" content="800">'
            '<meta property="og:locale" content="ar_SA"><meta name="twitter:card" content="summary">'
            '<link rel="canonical" href="%s"><!--/og-->') % (e(desc), e(title), e(desc), e(url), e(image), e(url))


def main():
    data = load()
    tpl = open('index.html', encoding='utf-8').read()
    os.makedirs('og', exist_ok=True)
    made = []
    for a in data['apts']:
        if not a.get('name'):
            continue
        s = slug(a)
        if s in made:
            continue  # two apartments with the same number: the first one keeps the link
        kind = TYPES.get(int(a.get('rooms') or 0), '')
        where = '، '.join(x for x in (a.get('district'), a.get('city')) if x)
        bits = [x for x in (kind, where) if x]
        if a.get('rating'):
            bits.append(f"★ {a['rating']}" + (f" ({a['reviews']} تقييم)" if a.get('reviews') else ''))
        desc = ' · '.join(bits) + ' — شاهد التواريخ المتاحة واحجز عبر جاذر إن.'
        img = SITE + 'og-square.jpg?v=3'
        if preview(cover(a), f'og/{s}.jpg'):
            img = f'{SITE}og/{s}.jpg?v=3'
        title = f"{a['name']} | place.n"
        page = re.sub(r'<!--og-->.*?<!--/og-->', lambda m: meta(title, desc, f'{SITE}{s}', img), tpl, count=1, flags=re.S)
        page = re.sub(r'<title>.*?</title>', f'<title>{html.escape(title)}</title>', page, count=1, flags=re.S)
        os.makedirs(s, exist_ok=True)
        with open(f'{s}/index.html', 'w', encoding='utf-8') as f:
            f.write(page)
        made.append(s)
    # remove pages of apartments that no longer exist
    old = json.load(open(LIST)) if os.path.exists(LIST) else []
    for s in old:
        if s not in made and re.fullmatch(r'[\w-]+', s) and os.path.isdir(s):
            shutil.rmtree(s)
            if os.path.exists(f'og/{s}.jpg'):
                os.remove(f'og/{s}.jpg')
    json.dump(sorted(made), open(LIST, 'w'), indent=0)
    print('pages:', len(made))


if __name__ == '__main__':
    main()
