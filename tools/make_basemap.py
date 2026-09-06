# -*- coding: utf-8 -*-
"""大洲市の白地図(SVGパス)を、国土数値情報から作る道具。

自由研究の図解で使う「共通の大洲市白地図」の元データを生成する。
記事ごとに手で地図を描くと形がバラバラになるので、
実データ(行政区域・河川)から一度だけパスを作り、全記事で使い回す。

元データ(tools/_basemap_cache/ に置く。無ければ自動で取り直す):
  - N03-2000 行政区域(2000年10月1日時点) … 合併前の旧4市町村の境界
  - N03-2023 行政区域(2023年1月1日時点) … いまの大洲市の輪郭
  - W05-06   河川(2006年度)              … 肱川の流路

出力: tools/_basemap_cache/ozu_basemap.json
  {"viewBox": "0 0 1000 H", "proj": {...},
   "old4": {"大洲市": [path...], "長浜町": [...], "肱川町": [...], "河辺村": [...]},
   "city": [path...], "hijikawa": [polyline path...]}

使い方:
  python tools/make_basemap.py            # JSONを生成
  python tools/make_basemap.py --preview  # 目視確認用の _basemap_preview.html も出す

座標をviewBoxに変換したいとき(記事側で点を打つとき)は、このファイルの
lonlat_to_xy() と同じ式を使うこと。JSONの "proj" に係数が入っている。
"""
import io
import json
import math
import sys
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "_basemap_cache"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0 Safari/537.36"

SOURCES = {
    "n03_2000.zip": "https://nlftp.mlit.go.jp/ksj/gml/data/N03/N03-2000/N03-001001_38_GML.zip",
    "n03_2023.zip": "https://nlftp.mlit.go.jp/ksj/gml/data/N03/N03-2023/N03-20230101_38_GML.zip",
    "w05.zip":      "https://nlftp.mlit.go.jp/ksj/gml/data/W05/W05-06/W05-06_38_GML.zip",
}

# 旧4市町村(2000年時点)の行政区域コード
OLD4 = {"38207": "大洲市", "38421": "長浜町", "38424": "肱川町", "38425": "河辺村"}


def ensure_downloads():
    CACHE.mkdir(exist_ok=True)
    for name, url in SOURCES.items():
        p = CACHE / name
        if p.exists() and p.stat().st_size > 100000:
            continue
        print(f"ダウンロード中: {url}")
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        p.write_bytes(urllib.request.urlopen(req).read())


def read_shp(zip_path: Path, member_prefix: str):
    """zipの中のshapefileを読み、(fields, records, shapes)を返す"""
    import shapefile
    z = zipfile.ZipFile(zip_path)
    names = z.namelist()
    base = next(n[:-4] for n in names if n.endswith(".shp") and member_prefix in n)
    r = shapefile.Reader(
        shp=io.BytesIO(z.read(base + ".shp")),
        dbf=io.BytesIO(z.read(base + ".dbf")),
        shx=io.BytesIO(z.read(base + ".shx")),
        encoding="cp932",
    )
    return r


def simplify(points, tol):
    """Douglas-Peucker。tolは座標系(度)での許容誤差"""
    if len(points) < 3:
        return points
    # 再帰だと深くなりすぎるのでスタック方式
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        ax, ay = points[a]
        bx, by = points[b]
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy)
        worst, wi = -1.0, -1
        for i in range(a + 1, b):
            px, py = points[i]
            if norm < 1e-12:
                # 閉じた輪郭は始点=終点で基準線がつぶれるので、点からの距離で測る
                d = math.hypot(px - ax, py - ay)
            else:
                d = abs(dx * (ay - py) - dy * (ax - px)) / norm
            if d > worst:
                worst, wi = d, i
        if worst > tol:
            keep[wi] = True
            stack.append((a, wi))
            stack.append((wi, b))
    return [p for p, k in zip(points, keep) if k]


def main():
    ensure_downloads()

    # --- 旧4市町村(2000年) ---
    r2000 = read_shp(CACHE / "n03_2000.zip", "AdministrativeBoundary")
    old_polys = {name: [] for name in OLD4.values()}
    for sr in r2000.iterShapeRecords():
        code = str(sr.record[6]).strip()
        if code in OLD4:
            shp = sr.shape
            parts = list(shp.parts) + [len(shp.points)]
            for i in range(len(parts) - 1):
                ring = shp.points[parts[i]:parts[i + 1]]
                old_polys[OLD4[code]].append(ring)

    # --- いまの大洲市(2023年) ---
    gj = json.loads(next((CACHE / "n03_2023.zip").parent.glob("**/n03_2023_extract.json"), Path("x")).read_text(encoding="utf-8")) if False else None
    z = zipfile.ZipFile(CACHE / "n03_2023.zip")
    gname = next(n for n in z.namelist() if n.endswith(".geojson"))
    gj = json.loads(z.read(gname).decode("utf-8"))
    city_polys = []
    for f in gj["features"]:
        if f["properties"].get("N03_004") == "大洲市":
            geom = f["geometry"]
            rings = []
            if geom["type"] == "Polygon":
                rings = [geom["coordinates"][0]]
            elif geom["type"] == "MultiPolygon":
                rings = [p[0] for p in geom["coordinates"]]
            city_polys.extend([[(x, y) for x, y in ring] for ring in rings])

    # --- 肱川(本川のみ) ---
    w05 = read_shp(CACHE / "w05.zip", "Stream")
    river_lines = []
    for sr in w05.iterShapeRecords():
        # W05_004=河川名(本川「肱川」だけ拾う)、W05_001=水系コード(肱川水系=8808xx)
        if str(sr.record[3]).strip() == "肱川" and str(sr.record[0]).startswith("8808"):
            river_lines.append(sr.shape.points)

    # --- 投影(正距円筒・縦横比補正) ---
    all_pts = [p for polys in old_polys.values() for ring in polys for p in ring]
    lons = [p[0] for p in all_pts]
    lats = [p[1] for p in all_pts]
    lon0, lon1 = min(lons), max(lons)
    lat0, lat1 = min(lats), max(lats)
    mid = math.radians((lat0 + lat1) / 2)
    W = 1000.0
    kx = W / (lon1 - lon0)
    ky = kx / math.cos(mid)  # 1度あたりの縦の伸び
    H = (lat1 - lat0) * ky
    pad = 20.0

    def xy(lon, lat):
        return (pad + (lon - lon0) * kx, pad + (lat1 - lat) * ky)

    tol = (lon1 - lon0) / 1000.0  # 約1px相当

    def to_path(rings, close=True):
        out = []
        for ring in rings:
            pts = simplify([tuple(p) for p in ring], tol)
            if len(pts) < (3 if close else 2):
                continue
            d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in (xy(*p) for p in pts))
            if close:
                d += " Z"
            out.append(d)
        return out

    data = {
        "viewBox": f"0 0 {W + 2 * pad:.0f} {H + 2 * pad:.0f}",
        "proj": {"lon0": lon0, "lat1": lat1, "kx": kx, "ky": ky, "pad": pad,
                 "note": "x = pad + (lon - lon0) * kx / y = pad + (lat1 - lat) * ky"},
        "old4": {name: to_path(polys) for name, polys in old_polys.items()},
        "city": to_path(city_polys),
        "hijikawa": to_path(river_lines, close=False),
    }
    out = CACHE / "ozu_basemap.json"
    out.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    n_pts = sum(d.count("L") for paths in data["old4"].values() for d in paths)
    print(f"書き出した: {out}")
    print(f"  旧4市町村のリング数: " + ", ".join(f"{k}={len(v)}" for k, v in data['old4'].items()))
    print(f"  いまの市の輪郭リング数: {len(data['city'])} / 肱川の線分数: {len(data['hijikawa'])} / 頂点合計(旧4): {n_pts}")

    if "--preview" in sys.argv:
        svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{data["viewBox"]}" style="background:#fff">']
        colors = {"大洲市": "#c9dff0", "長浜町": "#f0d9c9", "肱川町": "#d9f0c9", "河辺村": "#e8c9f0"}
        for name, paths in data["old4"].items():
            for d in paths:
                svg.append(f'<path d="{d}" fill="{colors[name]}" stroke="#888" stroke-width="1"/>')
        for d in data["city"]:
            svg.append(f'<path d="{d}" fill="none" stroke="#000" stroke-width="2"/>')
        for d in data["hijikawa"]:
            svg.append(f'<path d="{d}" fill="none" stroke="#3a7bd5" stroke-width="2"/>')
        svg.append("</svg>")
        prev = HERE.parent / "_basemap_preview.html"
        prev.write_text("\n".join(svg), encoding="utf-8")
        print(f"目視確認用: {prev}")


if __name__ == "__main__":
    main()
