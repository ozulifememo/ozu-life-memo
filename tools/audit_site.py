# -*- coding: utf-8 -*-
"""サイト全体の総点検。check_site.py が見ていない層を見る。

check_site.py は「記事のルール」を見る。こちらは「ウェブサイトとしての
作法」を見る。検索エンジン・SNS・読み上げ・回線の遅い読者に向けた部分。

  メタ情報   … canonical が自分のURLを指しているか / og:image が実在するか /
               JSON-LD が壊れていないか / viewport / lang / description
  画像       … alt が無い / 大きすぎる(500KB超) / 存在しない
  見出し     … h1 が1つか / 見出しの段飛ばし(h2 の次に h4 など)
  リンク     … 「こちら」だけのリンク文 / ページ内アンカー(#id)の行き先
  台帳       … news-data.js の重複・未来の日付・カテゴリ
  sitemap    … 全ページが載っているか / 存在しないページが載っていないか
  feed.xml   … 最新記事が入っているか / XMLとして壊れていないか
  重さ       … 1ページの合計サイズ(HTML+画像)

読むだけで、何も書き換えない。

使い方:
  python tools/audit_site.py
  python tools/audit_site.py --json 結果.json
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_site as cs                                    # noqa: E402

REPO = cs.REPO
BASE = "https://ozulifememo.github.io/ozu-life-memo/"
BIG_IMAGE = 500 * 1024
VAGUE_LINK = ("こちら", "ここ", "リンク", "詳細", "click here", "here")


class Rep:
    def __init__(self):
        self.items = []

    def add(self, level, path, kind, msg, detail=None):
        self.items.append({"level": level, "path": path, "kind": kind,
                           "message": msg, "detail": detail})

    def err(self, *a, **k):
        self.add("error", *a, **k)

    def warn(self, *a, **k):
        self.add("warn", *a, **k)


def grab(pattern, html, flags=re.S | re.I):
    m = re.search(pattern, html, flags)
    return m.group(1).strip() if m else None


def check_meta(p, html, rep):
    r = cs.rel(p)
    if '<html lang="ja"' not in html and "<html lang='ja'" not in html:
        rep.warn(r, "メタ", "<html lang=\"ja\"> がありません(読み上げ・翻訳の判定に使われる)")
    if "viewport" not in html:
        rep.err(r, "メタ", "viewport が無い(スマホで縮小表示になる)")
    desc = grab(r'<meta\s+name="description"\s+content="([^"]*)"', html)
    if desc is None:
        rep.warn(r, "メタ", "description が無い(検索結果の説明文が勝手に切り出される)")
    elif len(desc) < 30:
        rep.warn(r, "メタ", f"description が短すぎる({len(desc)}字)")

    canon = grab(r'<link\s+rel="canonical"\s+href="([^"]+)"', html)
    if canon:
        expect = BASE + r
        if r.endswith("index.html"):
            expect2 = BASE + r[:-len("index.html")]
        else:
            expect2 = None
        if canon not in (expect, expect2):
            rep.err(r, "メタ", "canonical が自分のURLと違う",
                    f"       書いてある: {canon}\n       正しい: {expect2 or expect}")

    og = grab(r'<meta\s+property="og:image"\s+content="([^"]+)"', html)
    if og:
        if og.startswith(BASE):
            f = REPO / og[len(BASE):].split("?")[0]
            if not f.exists():
                rep.err(r, "メタ", f"og:image の画像が無い: {og[len(BASE):]}",
                        "       LINE・Xでシェアしたとき画像が出ない")
        elif not og.startswith("http"):
            rep.warn(r, "メタ", "og:image が相対パス(SNSでは絶対URLでないと拾われない)")
    elif cs.page_type(p) in ("article", "book", "kenkyu"):
        rep.warn(r, "メタ", "og:image が無い(シェア時に画像が出ない)")

    for m in re.finditer(r'<script\s+type="application/ld\+json"[^>]*>(.*?)</script>',
                         html, flags=re.S | re.I):
        try:
            json.loads(m.group(1))
        except Exception as e:
            rep.err(r, "メタ", f"JSON-LD が壊れている({e.__class__.__name__})",
                    "       検索エンジンが構造化データを読めない")


def check_images(p, html, rep):
    r = cs.rel(p)
    body = cs.body_only(html)
    body = re.sub(r"<script\b.*?</script>", " ", body, flags=re.S | re.I)
    total = 0
    noalt = 0
    for tag in re.findall(r"<img\b[^>]*>", body, flags=re.I):
        src = grab(r'src="([^"]+)"', tag)
        if not src or "${" in src:
            continue
        if not re.search(r'\balt=', tag):
            noalt += 1
        if src.startswith(("http", "data:")):
            continue
        f = (p.parent / src.split("?")[0]).resolve()
        if f.exists():
            size = f.stat().st_size
            total += size
            if size > BIG_IMAGE:
                rep.warn(r, "画像", f"重い画像 {size // 1024}KB: {src}",
                         "       回線の遅い読者に効く。thumbs/ 方式か圧縮を")
    if noalt:
        rep.warn(r, "画像", f"alt の無い画像が{noalt}枚(読み上げで飛ばされる)")
    return total


def check_headings(p, html, rep):
    r = cs.rel(p)
    body = cs.body_only(html)
    h1 = len(re.findall(r"<h1\b", body, flags=re.I))
    if cs.page_type(p) in ("article", "book", "kenkyu") and h1 != 1:
        rep.warn(r, "見出し", f"h1 が{h1}個(1つが基本)")
    levels = [int(x) for x in re.findall(r"<h([1-6])\b", body, flags=re.I)]
    prev = 0
    for lv in levels:
        if prev and lv > prev + 1:
            rep.warn(r, "見出し", f"見出しが h{prev} から h{lv} に飛んでいる",
                     "       読み上げソフトが階層を見失う")
            break
        prev = lv


def check_links(p, html, rep):
    r = cs.rel(p)
    body = cs.body_only(html)
    body = re.sub(r"<script\b.*?</script>", " ", body, flags=re.S | re.I)
    ids = set(re.findall(r'\sid="([^"]+)"', html))
    vague = 0
    for m in re.finditer(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>', body, flags=re.S | re.I):
        href, text = m.group(1), cs.strip_tags(m.group(2)).strip()
        if href.startswith("#") and len(href) > 1 and href[1:] not in ids:
            rep.err(r, "リンク", f"ページ内アンカー {href} の行き先が無い")
        if text in VAGUE_LINK:
            vague += 1
    if vague:
        rep.warn(r, "リンク", f"「こちら」などのリンク文が{vague}件(何に飛ぶか分からない)")


def check_registry(rep):
    js = cs.read(REPO / "assets" / "js" / "news-data.js")
    slugs = re.findall(r'slug:\s*"([^"]+)"', js)
    dates = re.findall(r'date:\s*"([^"]+)"', js)
    dup = [s for s, n in Counter(slugs).items() if n > 1]
    for s in dup:
        rep.err("assets/js/news-data.js", "台帳", f"スラッグが重複: {s}")
    from datetime import date
    today = date.today().isoformat()
    for d in dates:
        if d > today:
            rep.warn("assets/js/news-data.js", "台帳", f"未来の日付がある: {d}")
    return len(slugs)


def check_sitemap(pages, rep):
    sm = REPO / "sitemap.xml"
    try:
        root = ET.parse(sm).getroot()
    except Exception as e:
        rep.err("sitemap.xml", "sitemap", f"XMLとして壊れている({e.__class__.__name__})")
        return
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [u.text.strip() for u in root.findall(".//s:loc", ns)]
    listed = set(urls)
    for u in urls:
        if not u.startswith(BASE):
            rep.err("sitemap.xml", "sitemap", f"別サイトのURLが載っている: {u}")
            continue
        relp = u[len(BASE):]
        f = REPO / (relp if relp else "index.html")
        if f.is_dir():
            f = f / "index.html"
        if not f.exists():
            rep.err("sitemap.xml", "sitemap", f"存在しないページが載っている: {relp}",
                    "       Googleが404を記録する")
    dup = [u for u, n in Counter(urls).items() if n > 1]
    for u in dup:
        rep.warn("sitemap.xml", "sitemap", f"重複: {u}")


def check_feed(rep):
    f = REPO / "feed.xml"
    if not f.exists():
        rep.warn("feed.xml", "RSS", "feed.xml が無い")
        return
    try:
        root = ET.parse(f).getroot()
    except Exception as e:
        rep.err("feed.xml", "RSS", f"XMLとして壊れている({e.__class__.__name__})")
        return
    links = [e.text for e in root.iter("link") if e.text]
    js = cs.read(REPO / "assets" / "js" / "news-data.js")
    items = re.findall(r'slug:\s*"([^"]+)",\s*date:\s*"([^"]+)"', js)
    items.sort(key=lambda x: x[1], reverse=True)
    newest = [s for s, _ in items[:5]]
    missing = [s for s in newest if not any(s in l for l in links)]
    if missing:
        rep.warn("feed.xml", "RSS", f"最新記事がRSSに入っていない: {', '.join(missing)}",
                 "       python tools/make_feed.py で作り直す")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    rep = Rep()
    pages = cs.collect_pages()
    weights = {}
    for p in pages:
        html = cs.read(p)
        check_meta(p, html, rep)
        w = check_images(p, html, rep) + len(html.encode("utf-8"))
        weights[cs.rel(p)] = w
        check_headings(p, html, rep)
        check_links(p, html, rep)
    n = check_registry(rep)
    check_sitemap(pages, rep)
    check_feed(rep)

    heavy = sorted(weights.items(), key=lambda kv: -kv[1])[:5]
    errs = [i for i in rep.items if i["level"] == "error"]
    warns = [i for i in rep.items if i["level"] == "warn"]

    print("\n" + "=" * 68)
    print(f" サイト総点検  /  {len(pages)}ページ・台帳{n}本")
    print("=" * 68)
    by = defaultdict(lambda: [0, 0])
    for i in rep.items:
        by[i["kind"]][0 if i["level"] == "error" else 1] += 1
    for k in ("メタ", "画像", "見出し", "リンク", "台帳", "sitemap", "RSS"):
        e, w = by.get(k, [0, 0])
        print(f"  【{k}】{'.' * (22 - len(k) * 2)} " +
              ("OK" if not e and not w else f"エラー{e} / 警告{w}"))
    print()
    print("  重いページ(HTML+画像):")
    for r, w in heavy:
        print(f"    {w // 1024:5d}KB  {r}")
    print()
    if errs:
        print("-" * 68 + "\n 直した方がよいもの\n" + "-" * 68)
        for i in errs:
            print(f"\n{i['path']}\n  [{i['kind']}] {i['message']}")
            if i["detail"]:
                print(i["detail"])
    if warns:
        print("\n" + "-" * 68 + "\n 見て判断するもの\n" + "-" * 68)
        grouped = defaultdict(list)
        for i in warns:
            grouped[(i["kind"], i["message"].split("(")[0].split(":")[0])].append(i["path"])
        for (kind, msg), paths in sorted(grouped.items(), key=lambda kv: -len(kv[1])):
            print(f"\n  [{kind}] {msg}  …{len(paths)}ページ")
            for pth in paths[:6]:
                print(f"      {pth}")
            if len(paths) > 6:
                print(f"      ほか{len(paths) - 6}ページ")
    print("\n" + "=" * 68)
    print(f" 結果: エラー {len(errs)}件 / 警告 {len(warns)}件")
    print("=" * 68 + "\n")

    if args.json:
        Path(args.json).write_text(json.dumps(rep.items, ensure_ascii=False, indent=2),
                                   encoding="utf-8")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
