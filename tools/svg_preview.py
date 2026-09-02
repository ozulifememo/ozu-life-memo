# -*- coding: utf-8 -*-
"""記事用SVG(自作の限られた語彙)をPNGにして目視確認するための簡易レンダラ。
usage: python render_preview.py <svg> [<out.png>]"""
import re
import sys
from PIL import Image, ImageDraw, ImageFont

path = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else path.rsplit(".", 1)[0] + "_preview.png"
svg = open(path, encoding="utf-8").read()
vb = re.search(r'viewBox="0 0 (\d+\.?\d*) (\d+\.?\d*)"', svg)
W, H = float(vb.group(1)), float(vb.group(2))
S = 1.6
img = Image.new("RGB", (int(W * S), int(H * S)), "white")
dr = ImageDraw.Draw(img, "RGBA")
FONT = "C:/Windows/Fonts/msgothic.ttc"

def font(a):
    size = float(a.get("font-size", 12))
    return ImageFont.truetype(FONT, int(size * S))

def col(c, op=1.0):
    m = {
        "var(--color-brand)": (26, 111, 176),
        "var(--color-text)": (40, 40, 40),
        "var(--color-text-muted)": (110, 110, 110),
        "var(--color-surface)": (250, 250, 248),
        "var(--color-surface-alt)": (240, 240, 236),
        "var(--color-border)": (210, 210, 205),
        "currentColor": (40, 40, 40),
    }
    if c in m:
        r, g, b = m[c]
    elif c.startswith("#"):
        c = c.lstrip("#")
        if len(c) == 3:
            c = "".join(ch * 2 for ch in c)
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    else:
        r, g, b = (0, 0, 0)
    return (r, g, b, int(255 * op))

events = []
for m in re.finditer(r"<(path|circle|rect|line)([^>]*?)/?>", svg):
    events.append((m.start(), m.group(1), m.group(2), None))
for m in re.finditer(r"<text([^>]*)>(.*?)</text>", svg, re.S):
    events.append((m.start(), "text", m.group(1), m.group(2)))
events.sort()
for _, tag, attrs, inner in events:
    a = dict(re.findall(r'([\w-]+)="([^"]*)"', attrs))
    fo = float(a.get("fill-opacity", a.get("opacity", 1)))
    so = float(a.get("stroke-opacity", a.get("opacity", 1)))
    if tag == "path":
        nums = [float(x) for x in re.findall(r"-?[\d.]+", a["d"])]
        pts = [(x * S, y * S) for x, y in zip(nums[::2], nums[1::2])]
        if len(pts) < 2:
            continue
        if a.get("fill", "none") != "none" and len(pts) > 2:
            dr.polygon(pts, fill=col(a["fill"], fo))
        if a.get("stroke", "none") != "none":
            dr.line(pts, fill=col(a["stroke"], so), width=max(1, int(float(a.get("stroke-width", 1)) * S)))
    elif tag == "circle":
        cx, cy, r = float(a["cx"]) * S, float(a["cy"]) * S, float(a["r"]) * S
        box = [cx - r, cy - r, cx + r, cy + r]
        if a.get("fill", "none") != "none":
            dr.ellipse(box, fill=col(a["fill"], fo))
        if a.get("stroke", "none") != "none":
            dr.ellipse(box, outline=col(a["stroke"], so), width=max(1, int(float(a.get("stroke-width", 1)) * S)))
    elif tag == "rect":
        x, y = float(a.get("x", 0)) * S, float(a.get("y", 0)) * S
        w, h = float(a["width"]) * S, float(a["height"]) * S
        if a.get("fill", "none") != "none":
            dr.rectangle([x, y, x + w, y + h], fill=col(a["fill"], fo))
        if a.get("stroke", "none") != "none":
            dr.rectangle([x, y, x + w, y + h], outline=col(a["stroke"], so), width=max(1, int(float(a.get("stroke-width", 1)) * S)))
    elif tag == "line":
        pts = [(float(a["x1"]) * S, float(a["y1"]) * S), (float(a["x2"]) * S, float(a["y2"]) * S)]
        dr.line(pts, fill=col(a.get("stroke", "#000"), so), width=max(1, int(float(a.get("stroke-width", 1)) * S)))
    else:
        txt = re.sub(r"<[^>]+>", "", inner or "").strip()
        if not txt:
            continue
        x, y = float(a["x"]) * S, float(a["y"]) * S
        f = font(a)
        w = dr.textlength(txt, font=f)
        anc = a.get("text-anchor", "start")
        if anc == "end":
            x -= w
        elif anc == "middle":
            x -= w / 2
        opacity = float(a.get("fill-opacity", 1))
        dr.text((x, y - f.size * 0.85), txt, font=f, fill=col(a.get("fill", "#000"), opacity))
img.save(out)
print("saved:", out, int(W), "x", int(H))
