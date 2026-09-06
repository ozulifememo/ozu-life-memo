# -*- coding: utf-8 -*-
"""大洲市のコンビニ勢力図(SVG)を作る。

tools/_basemap_cache/ozu_basemap.json(白地図)と
tools/_basemap_cache/conveni_geo.json(23店の座標)から
assets/img/ozu-conveni-map.svg を書き出す。

座標は国土地理院のジオコーディング(msearch.gsi.go.jp)で取ったもの。
番地まで分かる20店は正確、いしづち徳森店と肱川の2店は大字までの概算。

    python tools/make_conveni_map.py
"""
import json, io, sys
sys.stdout.reconfigure(encoding="utf-8")
BM = json.load(io.open("tools/_basemap_cache/ozu_basemap.json", encoding="utf-8"))
GEO = json.load(io.open("tools/_basemap_cache/conveni_geo.json", encoding="utf-8"))
P = BM["proj"]

def xy(lon, lat):
    return (P["pad"] + (lon - P["lon0"]) * P["kx"],
            P["pad"] + (P["lat1"] - lat) * P["ky"])

COL = {"ローソン": "#1f6fb4", "セブン": "#e8622a", "ファミマ": "#2f9e6e", "その他": "#8a8a8a"}
o = []
o.append('<svg viewBox="%s" role="img" aria-label="大洲市のコンビニ23店の分布図" '
         'xmlns="http://www.w3.org/2000/svg" style="width:100%%;height:auto;display:block">' % BM["viewBox"])
o.append('<rect width="100%" height="100%" fill="#f7f5f0"/>')
# 旧4市町村
tint = {"大洲市": "#e9e4d8", "長浜町": "#e2e7dd", "肱川町": "#e6e2ea", "河辺村": "#efe6de"}
for nm, paths in BM["old4"].items():
    for d in paths:
        o.append('<path d="%s" fill="%s" stroke="#c3bcae" stroke-width="1.6"/>' % (d, tint.get(nm, "#eee")))
# 肱川
for d in BM["hijikawa"]:
    o.append('<path d="%s" fill="none" stroke="#8fb4d4" stroke-width="2.2" stroke-linecap="round"/>' % d)
# 市の輪郭
for d in BM["city"]:
    o.append('<path d="%s" fill="none" stroke="#8c8578" stroke-width="2.4"/>' % d)
# 地域名
for nm, lon, lat in [("旧大洲市", 132.478, 33.478), ("旧長浜町", 132.455, 33.585),
                     ("旧肱川町", 132.655, 33.505), ("旧河辺村", 132.760, 33.545)]:
    x, y = xy(lon, lat)
    o.append('<text x="%.1f" y="%.1f" font-size="21" fill="#7a7263" font-weight="700">%s</text>' % (x, y, nm))
# 店
for g in GEO:
    if not g["lon"]:
        continue
    x, y = xy(g["lon"], g["lat"])
    o.append('<circle cx="%.1f" cy="%.1f" r="8.5" fill="%s" stroke="#fff" stroke-width="2.2"/>'
             % (x, y, COL[g["chain"]]))
# 凡例
lx, ly = 700, 120
o.append('<rect x="%d" y="%d" width="330" height="150" fill="#fff" stroke="#d6d0c4" rx="8"/>' % (lx-14, ly-30))
for i, (k, n) in enumerate([("ローソン", 10), ("セブン", 5), ("ファミマ", 5), ("その他", 3)]):
    yy = ly + i * 32
    o.append('<circle cx="%d" cy="%d" r="8.5" fill="%s" stroke="#fff" stroke-width="2"/>' % (lx, yy-5, COL[k]))
    o.append('<text x="%d" y="%d" font-size="20" fill="#3a352c">%s　%d店</text>' % (lx+20, yy+2, k, n))
o.append('</svg>')
svg = "\n".join(o)
io.open("assets/img/ozu-conveni-map.svg", "w", encoding="utf-8", newline="").write(svg)
print("SVG %d 文字 / 点 %d" % (len(svg), sum(1 for g in GEO if g["lon"])))
