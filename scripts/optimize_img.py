"""Shrink apartment photos so they load fast on phones.

Any photo in img/ that is wider/taller than MAX px or heavier than LIMIT bytes is resized
(longest side MAX) and saved as a progressive JPEG. File names stay the same, so data.json
does not change. Safe to run again: photos already small enough are left alone.
"""
import os
from PIL import Image, ImageOps

DIR = 'img'
MAX = 1600
LIMIT = 380 * 1024
QUALITY = 80
THUMBS = os.path.join(DIR, 't')  # small copies for cards and the photo strip
THUMB = 640


def main():
    done = saved = 0
    for name in sorted(os.listdir(DIR)):
        if not name.lower().endswith(('.jpg', '.jpeg')):
            continue
        path = os.path.join(DIR, name)
        before = os.path.getsize(path)
        im = Image.open(path)
        if max(im.size) <= MAX and before <= LIMIT:
            continue
        im = ImageOps.exif_transpose(im).convert('RGB')
        if max(im.size) > MAX:
            im.thumbnail((MAX, MAX), Image.LANCZOS)
        tmp = path + '.tmp'
        im.save(tmp, 'JPEG', quality=QUALITY, optimize=True, progressive=True)
        after = os.path.getsize(tmp)
        if after < before:
            os.replace(tmp, path)
            done += 1
            saved += before - after
        else:
            os.remove(tmp)
    os.makedirs(THUMBS, exist_ok=True)
    made = 0
    names = set()
    for name in sorted(os.listdir(DIR)):
        if not name.lower().endswith(('.jpg', '.jpeg')):
            continue
        names.add(name)
        src, dst = os.path.join(DIR, name), os.path.join(THUMBS, name)
        if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
            continue
        im = ImageOps.exif_transpose(Image.open(src)).convert('RGB')
        im.thumbnail((THUMB, THUMB), Image.LANCZOS)
        im.save(dst, 'JPEG', quality=76, optimize=True, progressive=True)
        made += 1
    for name in os.listdir(THUMBS):  # photo deleted -> drop its small copy
        if name not in names:
            os.remove(os.path.join(THUMBS, name))
    print(f'optimized {done} photos, saved {saved // 1024} KB, made {made} small copies')


if __name__ == '__main__':
    main()
