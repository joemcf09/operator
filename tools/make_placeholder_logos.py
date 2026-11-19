"""Generate original placeholder wordmarks for operators that have no logo in the pack.

These are deliberately NOT reproductions of anyone's trademark: a geometric mark with the
operator's initials, the name set in a neutral grotesque, and a colour chosen deterministically
from a fixed palette by hashing the name. They exist so the interface reads as a finished
product; the moment a properly licensed asset is dropped into static/operators/ with a matching
filename it takes precedence.

Run from the project root:  python tools/make_placeholder_logos.py
"""
import hashlib
import json
import os
import re
import sys
import unicodedata

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
OUT = os.path.join(HERE, "static", "operators")

W, H = 360, 120
MARK = 96                      # mark box size
PAD = 12

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]
FONT_CONDENSED = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
] + FONT_CANDIDATES

# Deliberately generic, evenly spaced palette — not brand colours.
PALETTE = [
    (28, 63, 122), (18, 92, 88), (122, 41, 47), (60, 55, 110), (32, 84, 48),
    (140, 84, 20), (36, 76, 108), (96, 44, 96), (52, 66, 76), (110, 62, 34),
    (24, 100, 118), (86, 34, 66), (44, 82, 34), (74, 60, 128), (128, 68, 60),
]


def slug(name):
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", n.lower()).strip("-")


def _font(paths, size):
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


STOPWORDS = {"the", "of", "and", "air", "airlines", "airline", "airways", "aviation", "group",
             "capital", "cargo", "aircraft", "international", "company", "holdings", "partners",
             "leasing", "management", "asset", "global", "express", "airport"}


def initials(name):
    words = [w for w in re.split(r"[^A-Za-z0-9]+", name) if w]
    strong = [w for w in words if w.lower() not in STOPWORDS] or words
    if len(strong) == 1:
        w = strong[0]
        caps = re.findall(r"[A-Z]", w[1:])          # AerCap -> AC, easyJet -> EJ
        if caps:
            return (w[0] + caps[0]).upper()
        return w[0].upper()
    return "".join(w[0] for w in strong[:3]).upper()


def wrap(name, font, draw, max_w, max_lines=3):
    words = name.split()
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
            if len(lines) == max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines and len(" ".join(lines)) < len(name):
        # ran out of room: keep it honest with an ellipsis
        while lines and draw.textlength(lines[-1] + "…", font=font) > max_w:
            lines[-1] = lines[-1][:-1]
        lines[-1] += "…"
    return lines


def make(name, path):
    h = int(hashlib.sha256(name.encode()).hexdigest(), 16)
    colour = PALETTE[h % len(PALETTE)]
    shape = (h >> 8) % 4
    img = Image.new("RGBA", (W * 2, H * 2), (0, 0, 0, 0))     # 2x for smooth edges
    d = ImageDraw.Draw(img)
    s = 2
    mx0, my0 = PAD * s, ((H - MARK) // 2) * s
    mx1, my1 = mx0 + MARK * s, my0 + MARK * s
    if shape == 0:
        d.rounded_rectangle([mx0, my0, mx1, my1], radius=14 * s, fill=colour)
    elif shape == 1:
        d.ellipse([mx0, my0, mx1, my1], fill=colour)
    elif shape == 2:
        d.rounded_rectangle([mx0, my0, mx1, my1], radius=6 * s, fill=colour)
        d.polygon([(mx1 - 34 * s, my1), (mx1, my1 - 34 * s), (mx1, my1)], fill=(255, 255, 255, 55))
    else:
        d.rounded_rectangle([mx0, my0, mx1, my1], radius=48 * s, fill=colour)
        d.rounded_rectangle([mx0 + 10 * s, my0 + 10 * s, mx1 - 10 * s, my1 - 10 * s],
                            radius=40 * s, outline=(255, 255, 255, 70), width=2 * s)

    ini = initials(name)
    size = 46 if len(ini) <= 2 else 36
    f_ini = _font(FONT_CANDIDATES, size * s)
    bb = d.textbbox((0, 0), ini, font=f_ini)
    d.text(((mx0 + mx1) / 2 - (bb[2] - bb[0]) / 2 - bb[0], (my0 + my1) / 2 - (bb[3] - bb[1]) / 2 - bb[1]),
           ini, font=f_ini, fill=(255, 255, 255, 255))

    tx = mx1 + 16 * s
    max_w = W * s - tx - PAD * s
    for size, maxl in ((26, 2), (23, 2), (21, 2), (19, 3), (17, 3), (15, 3)):
        f = _font(FONT_CONDENSED if size <= 21 else FONT_CANDIDATES, size * s)
        lines = wrap(name.upper(), f, d, max_w, maxl)
        if all(d.textlength(l, font=f) <= max_w for l in lines) and "…" not in "".join(lines):
            break
    lh = int(size * 1.22 * s)
    total = lh * len(lines)
    y = H * s / 2 - total / 2
    for l in lines:
        d.text((tx, y), l, font=f, fill=(38, 46, 56, 255))
        y += lh
    d.rectangle([tx, H * s / 2 + total / 2 + 6 * s, tx + 44 * s, H * s / 2 + total / 2 + 9 * s], fill=colour)

    img = img.resize((W, H), Image.LANCZOS)
    img.save(path, optimize=True)


def main():
    from data import (LESSORS, ACMI_CUSTOMERS, OPERATORS, COMPETITORS, CARGO_COMPETITORS,
                      CARGO_CARRIERS, BROKERS, CHARTER_COMPETITORS, OPERATOR_LOGOS)
    names = []
    for group, items in (("Lessor", [l["name"] for l in LESSORS]),
                         ("ACMI customer", [c["name"] for c in ACMI_CUSTOMERS]),
                         ("Ferry client / operator", list(OPERATORS)),
                         ("Cargo carrier", [c["name"] for c in CARGO_CARRIERS]),
                         ("Charter broker", [b["name"] for b in BROKERS if b["name"] != "Direct client"]),
                         ("Competing operator", sorted(set(COMPETITORS) | set(CARGO_COMPETITORS) | set(CHARTER_COMPETITORS)))):
        for n in items:
            if n in OPERATOR_LOGOS or any(x[1] == n for x in names):
                continue
            names.append((group, n))
    os.makedirs(OUT, exist_ok=True)
    src_path = os.path.join(OUT, "sources.json")
    sources = json.load(open(src_path, encoding="utf-8")) if os.path.exists(src_path) else []
    known = {s.get("operator") for s in sources}
    mapping = {}
    for group, n in names:
        f = slug(n) + ".png"
        make(n, os.path.join(OUT, f))
        mapping[n] = slug(n)
        if n not in known:
            sources.append(dict(operator=n, file=f, kind="placeholder", license="Original artwork",
                                license_url="", artist="Generated for Operator", source_page="",
                                note=f"Placeholder wordmark for a {group.lower()}; not the operator's trademark."))
    json.dump(sources, open(src_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    # merge, never overwrite: earlier placeholders must survive a later run
    map_path = os.path.join(HERE, "placeholder_logos.json")
    existing = json.load(open(map_path, encoding="utf-8")) if os.path.exists(map_path) else {}
    existing.update(mapping)
    with open(map_path, "w", encoding="utf-8") as fh:
        json.dump(existing, fh, indent=1, ensure_ascii=False)
    print(f"generated {len(names)} placeholder wordmarks into {OUT}")


if __name__ == "__main__":
    main()
