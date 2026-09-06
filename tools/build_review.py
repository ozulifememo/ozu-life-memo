# -*- coding: utf-8 -*-
"""OZU 記事レビュー卓 を1枚のHTMLに組み立てる。"""
import re, glob, os, json, io, base64, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _cssscope import scope

HERE  = os.path.dirname(os.path.abspath(__file__))
ROOT  = os.path.abspath(os.path.join(HERE, ".."))
OUT_LOCAL = os.path.join(ROOT, "_review.html")       # パソコンで直接開く用
OUT_ART   = os.path.join(ROOT, "_review-src.html")   # アーティファクトに載せる用(素のまま)

# アーティファクトの外枠と同じものを、ローカル用に自前で被せる
SKELETON = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>:root{color-scheme:light}html,body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>
</head>
<body>
@@CONTENT@@
</body>
</html>
"""

# ---------------------------------------------------------------- メタ
js = open(os.path.join(ROOT, "assets/js/news-data.js"), encoding="utf-8").read()
meta = {}
for blk in re.findall(r"\{\s*slug:.*?\n  \}", js, re.S):
    g = lambda k: (re.search(k + r':\s*"([^"]*)"', blk) or [None, None])[1]
    tg = re.search(r"tags:\s*\[([^\]]*)\]", blk)
    meta[g("slug")] = {
        "title": g("title"), "date": g("date"), "cat": g("category"),
        "tags": re.findall(r'"([^"]+)"', tg.group(1)) if tg else [],
    }
CATJP = {"ima": "大洲のいま", "kurashi": "大洲の暮らし", "shiten": "大洲の視点"}

def plain(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()

def body_of(p):
    s = open(p, encoding="utf-8").read()
    m = re.search(r"<body[^>]*>(.*)</body>", s, re.S)
    b = m.group(1) if m else s
    b = re.sub(r"<script\b.*?</script>", "", b, flags=re.S)
    b = re.sub(r"<div data-site-(header|footer|modal)[^>]*>\s*</div>", "", b)
    b = re.sub(r'<aside class="article-sidebar".*?</aside>', "", b, flags=re.S)
    b = re.sub(r'<div class="related-list".*?</div>', "", b, flags=re.S)
    return b.strip()

rows = []
for kind, d in (("news", "eachnews"), ("jk", "jiyu-kenkyu"), ("book", "book")):
    for p in sorted(glob.glob(os.path.join(ROOT, d, "*.html"))):
        n = os.path.basename(p)
        if n == "index.html":
            continue
        slug = n[:-5]
        draft = slug.startswith("_")
        if draft:
            slug = slug[1:]
        b = body_of(p)
        m = meta.get(slug, {})
        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", b, re.S)
        title = m.get("title") or (plain(h1.group(1)) if h1 else slug)
        date = m.get("date")
        if not date:
            dm = (re.search(r"公開:\s*(\d{4})/(\d{2})/(\d{2})", b)
                  or re.search(r'class="article-date"[^>]*>\s*(\d{4})/(\d{2})/(\d{2})', b))
            date = "-".join(dm.groups()) if dm else ""
        if kind == "jk":
            no = re.search(r"大洲の自由研究\s*#(\d+)", b)
            cat = "自由研究" + (" #" + no.group(1) if no else "")
        elif kind == "book":
            cat = "大洲と読書"
        else:
            cm = re.search(r'class="article-cat">([^<]+)<', b)
            cat = CATJP.get(m.get("cat"), cm.group(1) if cm else "記事")
        rows.append(dict(kind=kind, slug=slug, draft=draft, title=title, date=date,
                         cat=cat, tags=m.get("tags", []),
                         links=len(re.findall(r'<a [^>]*href="https?://', b)),
                         chars=len(plain(b)), body=b))

SLUGS = {r["slug"] for r in rows}
print("記事:", len(rows), "／ 下書き:", sum(1 for r in rows if r["draft"]))

# ---------------------------------------------------------------- 画像
used = set()
for r in rows:
    used |= set(re.findall(r'src="\.\./(assets/img/[^"]+)"', r["body"]))

DATAURI, KEY, tot_before, tot_after, misses = {}, {}, 0, 0, []
for rel in sorted(used):
    full = os.path.join(ROOT, rel)
    if rel.endswith(".svg"):
        if not os.path.exists(full):
            misses.append(rel); continue
        raw = open(full, "rb").read()
        tot_before += len(raw); tot_after += len(raw)
        DATAURI[rel] = "data:image/svg+xml;base64," + base64.b64encode(raw).decode()
        KEY[rel] = "i%d" % len(KEY)
        continue
    thumb = os.path.join(ROOT, "assets/img/thumbs", rel[len("assets/img/"):])
    src = thumb if os.path.exists(thumb) else full
    if not os.path.exists(src):
        misses.append(rel); continue
    tot_before += os.path.getsize(full) if os.path.exists(full) else os.path.getsize(src)
    im = Image.open(src).convert("RGB")
    if im.width > 800:
        im = im.resize((800, round(im.height * 800 / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=70, method=5)
    tot_after += buf.tell()
    DATAURI[rel] = "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()
    KEY[rel] = "i%d" % len(KEY)

print("画像: %d枚  %.1fMB -> %.1fMB" % (len(DATAURI), tot_before/1048576, tot_after/1048576))
if misses:
    print("  !! 見つからない画像:", misses)

# ---------------------------------------------------------------- 本文の書き換え
ART_RE = re.compile(r'href="\.\./(eachnews|jiyu-kenkyu|book)/([a-z0-9\-]+)\.html"')
def fix(body):
    def img(m):
        rel = m.group(1)
        return 'data-im="%s"' % KEY[rel] if rel in KEY else m.group(0)
    body = re.sub(r'src="\.\./(assets/img/[^"]+)"', img, body)
    def art(m):
        return ('href="#" data-go="%s"' % m.group(2)) if m.group(2) in SLUGS else m.group(0)
    body = ART_RE.sub(art, body)
    return body.replace("</script", "<\\/script")

# ---------------------------------------------------------------- 組み立て
site_css = scope(open(os.path.join(ROOT, "assets/css/style.css"), encoding="utf-8").read())
shell = open(os.path.join(HERE, "review-shell.html"), encoding="utf-8").read()

metas = [{k: r[k] for k in ("kind", "slug", "draft", "title", "date", "cat", "tags", "chars", "links")}
         for r in rows]
bodies = "\n".join(
    '<script id="b%d" type="text/plain">%s</script>' % (i, fix(r["body"]))
    for i, r in enumerate(rows))

imgmap = json.dumps({KEY[k]: DATAURI[k] for k in KEY}, separators=(",", ":"))
html = (shell
        .replace("__IMGS__", imgmap)
        .replace("__SITECSS__", site_css)
        .replace("__META__", json.dumps(metas, ensure_ascii=False, separators=(",", ":")))
        .replace("__BODIES__", bodies))

io.open(OUT_ART, "w", encoding="utf-8", newline="\n").write(html)
io.open(OUT_LOCAL, "w", encoding="utf-8", newline="\n").write(SKELETON.replace("@@CONTENT@@", html))
mb = os.path.getsize(OUT_ART) / 1048576
print("書き出し(アーティファクト用): %s  %.2f MB" % (OUT_ART, mb))
print("書き出し(パソコン用)        : %s  %.2f MB" % (OUT_LOCAL, os.path.getsize(OUT_LOCAL) / 1048576))

# ---------------------------------------------------------------- 自己点検
bad = []
if "__SITECSS__" in html or "__META__" in html or "__BODIES__" in html or "__IMGS__" in html:
    bad.append("プレースホルダが残っている")
if mb > 15.0:
    bad.append("16MBの上限に近い (%.1fMB)" % mb)
left = re.findall(r'(?:src|href)="\.\./assets/img/[^"]+"', html)
if left:
    bad.append("data URI にできなかった画像 %d件: %s" % (len(left), left[:3]))
if html.count('type="text/plain"') != len(rows):
    bad.append("本文ブロックの数が合わない")
if "<!doctype" in html.lower() or "<body" in html.lower():
    bad.append("アーティファクト用に doctype/body が混ざっている")
if "[hidden]{display:none!important}" not in html:
    bad.append("hidden を効かせる指定が無い")
if "<!doctype" in html.lower() or "<body" in html.lower():
    bad.append("アーティファクト用に doctype/body が混ざっている")
if "[hidden]{display:none!important}" not in html:
    bad.append("hidden を効かせる指定が無い")
svg = sum(r["body"].count("<svg") for r in rows)
print("インラインSVG(図解):", svg, "個")
# ---------------------------------------------------------------- 指紋
# **記事を直したら、この卓も作り直さないと中身が古いまま残る。**
# 2026-09-05、記事を7本直したのにこの卓が古いままで、本人が開いて気づいた。
# 本人が気づくまで分からない形の事故だったので、機械に移した。
#
# ここで書く指紋を check_site.py が読み、いまの記事と比べる。
# ズレていたら「レビュー卓が作り直されていません」で止まる。
# **数え方は check_site.py の review_fingerprint と同じでなければならない**ので、
# 自前で数えず、あちらの関数をそのまま呼ぶ。
import datetime
sys.path.insert(0, HERE)
import check_site as _cs

fp = _cs.review_fingerprint(_cs.collect_pages())
io.open(os.path.join(HERE, "review-built.json"), "w", encoding="utf-8", newline="").write(
    json.dumps({"fingerprint": fp,
                "built": datetime.date.today().isoformat(),
                "メモ": "レビュー卓に入れた記事本文の指紋。check_site.py がこれと"
                        "いまの記事を比べて、卓が古くなっていたら止める。"
                        "build_review.py が書く。作り直したら publish も忘れないこと"},
               ensure_ascii=False, indent=1))
print("指紋を書きました: tools/review-built.json")

print("点検:", "問題なし" if not bad else bad)
