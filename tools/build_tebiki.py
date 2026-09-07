# -*- coding: utf-8 -*-
"""「こんなときは」の索引と、その手引きページを組み立てる。

索引は、記事の分類ではなく読者の状況で引く。棚を押すと、その状況だけを
まとめた1枚もの(手引き)に着く。紆余曲折や背景は書かない。手順と金額と窓口だけ。

材料は private-notes/genkou/_tebiki-<id>.md。書式はそのファイルの中身を見ること。
出力は sakuin/index.html と sakuin/<id>.html。

2026-09-07、本人の指示で作った。
「項目が多すぎる。カラーの方が良い。それぞれに、それ用の説明記事を入れたい。
　本当に知りたい人はその知識だけが欲しいと思う。紆余曲折なしの記事もいると思う」
"""
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "private-notes" / "genkou"
OUT_DIR = ROOT / "sakuin"
BASE = "https://ozulifememo.github.io/ozu-life-memo"

TITLE = "こんなときは"
DESC = ("家を建てる。親の介護が始まる。市に言いたいことがある。"
        "そういう日が来たときに引くための索引です。状況から、手順と金額と窓口にたどりつけます。")

# 並び順。同じ色が隣り合わないように置いている。
ORDER = [
    "kodomo-umareru", "hikkoshi", "ie-tateru", "hatarakenai", "hitorioya",
    "kuruma-tebanasu", "menkyo", "oya-kaigo", "souzoku", "bosai",
    "risai", "komatta-soudan", "shi-ni-iu",
]

COLORS = {
    "indigo": "#3d5473", "mikan": "#9a6238", "moss": "#566b45", "gold": "#846f42",
    "teal": "#3a6a64", "slate": "#556678", "kakishibu": "#8a5541", "rose": "#7b5060",
}


def bold(s):
    """**…** を <strong> にする。エスケープしてから開く。"""
    s = html.escape(s)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)


def parse(path):
    text = path.read_text(encoding="utf-8")
    head, _, rest = text.partition("---手順---")
    d = {}
    for line in head.strip().splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            d[k.strip()] = v.strip()

    blocks = {}
    cur = "手順"
    buf = []
    for line in rest.splitlines():
        m = re.fullmatch(r"---(.+?)---", line.strip())
        if m:
            blocks[cur] = buf
            cur, buf = m.group(1), []
        else:
            buf.append(line)
    blocks[cur] = buf

    def lines(name):
        return [l.rstrip() for l in blocks.get(name, []) if l.strip()]

    d["steps"] = []
    for l in lines("手順"):
        parts = l.split("|")
        if len(parts) >= 3:
            d["steps"].append((parts[0].strip(), parts[1].strip(), "|".join(parts[2:]).strip()))

    tbl = lines("表")
    d["table"] = None
    if len(tbl) >= 3:
        d["table"] = {
            "caption": tbl[0].strip(),
            "head": [c.strip() for c in tbl[1].split("|")],
            "rows": [[c.strip() for c in r.split("|")] for r in tbl[2:]],
        }
    d["table_note"] = " ".join(lines("表の注"))
    d["miss"] = " ".join(lines("見落とし"))

    d["more"] = []
    for l in lines("もっと"):
        if "|" in l:
            slug, _, why = l.partition("|")
            d["more"].append((slug.strip(), why.strip()))

    d["sources"] = []
    for l in lines("出典"):
        # 注記の括弧は半角・全角どちらも来る(書き手によって揺れる)
        m = re.match(r"-\s*\[(.+?)\]\((.+?)\)\s*(?:[(（](.*)[)）])?\s*$", l)
        if m:
            d["sources"].append((m.group(1), m.group(2), m.group(3) or ""))
    return d


def load_plan():
    """22棚の設計図。手引きと同じidの棚は、その手引きの関連記事として使う。
    残った棚は索引の下に畳んで置く。棚を13に絞っても、記事への入口を減らさないため。"""
    import json
    p = ROOT / "private-notes" / "sakuin-plan.json"
    if not p.exists():
        return {}
    return {g["id"]: g for g in json.loads(p.read_text(encoding="utf-8"))["groups"]}


def article_title(slug):
    """news-data.js から題を引く。無ければ記事HTMLの<h1>。"""
    if not hasattr(article_title, "_cache"):
        js = (ROOT / "assets" / "js" / "news-data.js").read_text(encoding="utf-8")
        article_title._cache = dict(
            re.findall(r'slug:\s*"([^"]+)".*?title:\s*"([^"]+)"', js, re.S))
    t = article_title._cache.get(slug)
    if t:
        return t
    p = ROOT / "eachnews" / f"{slug}.html"
    if p.exists():
        m = re.search(r"<h1[^>]*>(.*?)</h1>", p.read_text(encoding="utf-8"), re.S)
        if m:
            return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip()
    return None


PAGE_CSS = """
:root{--tb:#3d5473}
.tb-wrap{max-width:820px;margin:0 auto;padding:0 24px}
.tb-head{border-left:6px solid var(--tb);padding:4px 0 4px 16px;margin:var(--space-6) auto var(--space-4)}
.tb-head h1{font-family:var(--font-serif);font-size:1.6rem;margin:0;line-height:1.45;color:var(--color-text)}
.tb-head p{margin:8px 0 0;color:var(--color-text-muted);font-size:var(--text-sm);line-height:1.8}
.tb-ans{background:var(--color-surface);border:1px solid var(--color-border);
  border-top:4px solid var(--tb);border-radius:var(--radius);padding:24px;margin:var(--space-5) 0}
.tb-ans h2{font-size:.78rem;letter-spacing:.08em;color:var(--tb);margin:0 0 18px;font-weight:700}
.tb-step{display:grid;grid-template-columns:30px 1fr;gap:4px 12px;margin-bottom:20px}
.tb-step:last-child{margin-bottom:0}
.tb-step .n{width:30px;height:30px;border-radius:50%;background:var(--tb);color:#fff;
  font-size:.82rem;font-weight:700;display:grid;place-items:center;grid-row:1/span 2}
.tb-step .t{font-weight:700;font-size:1.03rem;line-height:1.5;align-self:center}
.tb-step .d{color:var(--color-text-muted);font-size:.9rem;line-height:1.9;grid-column:2}
.tb-step .d strong{color:var(--color-text)}
.tb-tablewrap{overflow-x:auto;margin:var(--space-5) 0}
.tb-cap{font-size:1rem;font-weight:700;margin:var(--space-6) 0 6px}
.tb-wrap table{width:100%;border-collapse:collapse;font-size:.88rem;min-width:420px}
.tb-wrap th,.tb-wrap td{border-bottom:1px solid var(--color-border);padding:9px 10px;text-align:left}
.tb-wrap th{background:var(--color-surface-alt);color:var(--color-text-muted);font-size:.78rem;font-weight:700;white-space:nowrap}
.tb-note{color:var(--color-text-muted);font-size:.82rem;line-height:1.85;margin:-6px 0 0}
.tb-miss{background:var(--color-memou-bg);border:1px solid var(--color-memou-border);
  border-radius:var(--radius);padding:16px 20px;margin:var(--space-5) 0}
.tb-miss p{margin:0;font-size:.9rem;line-height:1.9}
.tb-miss strong{color:var(--color-memou-ink)}
.tb-more{margin-top:var(--space-6);padding-top:var(--space-4);border-top:1px solid var(--color-border)}
.tb-more .lb{font-size:.78rem;color:var(--color-text-muted);margin:0 0 10px}
.tb-more a{display:block;background:var(--color-surface);border:1px solid var(--color-border);
  border-left:4px solid var(--tb);border-radius:var(--radius-sm);padding:12px 16px;margin-bottom:8px;
  text-decoration:none;color:var(--color-text);font-weight:700;font-size:.95rem;line-height:1.55}
.tb-more a:hover{border-color:var(--tb)}
.tb-more a span{display:block;font-weight:400;color:var(--color-text-muted);font-size:.82rem;margin-top:3px}
.tb-src{margin-top:var(--space-6);padding-top:var(--space-4);border-top:1px solid var(--color-border)}
.tb-src>summary{font-size:.95rem;font-weight:700;cursor:pointer;list-style:none;
  padding:8px 0;color:var(--color-text)}
.tb-src>summary::-webkit-details-marker{display:none}
.tb-src>summary::before{content:"▸ ";color:var(--tb)}
.tb-src[open]>summary::before{content:"▾ "}
.tb-src>ol{margin-top:10px}
.tb-src ol{margin:0;padding-left:1.4em;color:var(--color-text-muted);font-size:.82rem;line-height:1.9}
.tb-src a{color:var(--color-brand)}
.tb-back{display:inline-block;margin:var(--space-6) 0 0;font-size:var(--text-sm);color:var(--color-brand)}
.tb-caution{color:var(--color-text-muted);font-size:.8rem;line-height:1.85;margin:var(--space-5) 0 0}
@media(max-width:600px){.tb-head h1{font-size:1.3rem}}
"""

INDEX_CSS = """
.sk-lead{max-width:820px;margin:0 auto var(--space-6);padding:0 24px;
  color:var(--color-text-muted);font-size:var(--text-sm);line-height:1.9}
.sk-grid{max-width:900px;margin:0 auto;padding:0 24px;display:grid;gap:12px;
  grid-template-columns:repeat(auto-fill,minmax(260px,1fr))}
.sk-card{display:block;background:var(--color-surface);border:1px solid var(--color-border);
  border-left:6px solid var(--c);border-radius:var(--radius);padding:16px 18px;text-decoration:none;
  transition:border-color .15s ease,transform .15s ease}
.sk-card:hover{border-color:var(--c);transform:translateY(-2px)}
.sk-card b{display:block;color:var(--color-text);font-size:1rem;line-height:1.5}
.sk-card span{display:block;color:var(--color-text-muted);font-size:.83rem;line-height:1.75;margin-top:6px}
.sk-rest{max-width:900px;margin:var(--space-6) auto 0;padding:0 24px}
.sk-rest>summary{font-size:.95rem;font-weight:700;cursor:pointer;list-style:none;padding:10px 0;
  border-top:1px solid var(--color-border);color:var(--color-text)}
.sk-rest>summary::-webkit-details-marker{display:none}
.sk-rest>summary::before{content:"▸ ";color:var(--color-brand)}
.sk-rest[open]>summary::before{content:"▾ "}
.sk-rest .g{margin:var(--space-4) 0 0}
.sk-rest .g h3{font-size:.95rem;margin:0 0 2px;color:var(--color-brand-dark)}
.sk-rest .g p{margin:0 0 8px;color:var(--color-text-muted);font-size:.82rem;line-height:1.7}
.sk-rest .g ul{list-style:none;margin:0 0 0 2px;padding:0;display:grid;gap:4px}
.sk-rest .g li a{color:var(--color-text);font-size:.88rem;line-height:1.6}
.sk-rest .g li a:hover{color:var(--color-brand)}
.sk-note{max-width:820px;margin:var(--space-5) auto 0;padding:var(--space-5);
  background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius);
  color:var(--color-text-muted);font-size:var(--text-sm);line-height:1.9}
.sk-note p{margin:0 0 10px}
.sk-note p:last-child{margin:0}
"""


def shell(title, desc, url_path, css, body, prefix="../"):
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} ｜ OZU LIFE MEMO</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="icon" href="{prefix}assets/img/favicon-192.png">
<link rel="alternate" type="application/rss+xml" title="OZU LIFE MEMO の更新" href="{prefix}feed.xml">
<link rel="apple-touch-icon" href="{prefix}assets/img/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link data-ozu-fonts rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&amp;family=Shippori+Mincho+B1:wght@600;700&amp;display=swap">
<link rel="stylesheet" href="{prefix}assets/css/style.css">
<meta property="og:type" content="website">
<meta property="og:site_name" content="OZU LIFE MEMO">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:url" content="{BASE}/{url_path}">
<meta property="og:image" content="{BASE}/assets/img/ogp-card.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="{BASE}/{url_path}">
<style>{css.strip()}</style>
</head>
<body>

<div data-site-header data-prefix="{prefix}"></div>

{body}

<div data-site-footer data-prefix="{prefix}"></div>
<script src="{prefix}assets/js/site-chrome.js" defer></script>
</body>
</html>
"""


def render_tebiki(d):
    c = COLORS.get(d.get("color", "indigo"), COLORS["indigo"])
    b = [f'<section style="padding-top:var(--space-5);padding-bottom:0;">',
         '<div class="tb-wrap">',
         f'  <div class="tb-head" style="--tb:{c}">',
         f'    <h1>{html.escape(d["label"])}</h1>',
         f'    <p>{html.escape(d["lead"])}</p>',
         '  </div>',
         f'  <div class="tb-ans" style="--tb:{c}">',
         '    <h2>やることは、この順番</h2>']
    for n, t, dd in d["steps"]:
        b += ['    <div class="tb-step">',
              f'      <div class="n">{html.escape(n)}</div>',
              f'      <div class="t">{bold(t)}</div>',
              f'      <div class="d">{bold(dd)}</div>',
              '    </div>']
    b.append('  </div>')

    if d["table"]:
        t = d["table"]
        b.append(f'  <p class="tb-cap">{html.escape(t["caption"])}</p>')
        b.append('  <div class="tb-tablewrap"><table>')
        b.append('    <tr>' + "".join(f"<th>{bold(x)}</th>" for x in t["head"]) + '</tr>')
        for r in t["rows"]:
            b.append('    <tr>' + "".join(f"<td>{bold(x)}</td>" for x in r) + '</tr>')
        b.append('  </table></div>')
        if d["table_note"]:
            b.append(f'  <p class="tb-note">{bold(d["table_note"])}</p>')

    if d["miss"]:
        b += [f'  <div class="tb-miss"><p><strong>見落とされやすいもの。</strong> {bold(d["miss"])}</p></div>']

    extra = list(d["more"])
    g = PLAN.get(d["id"])
    if g:
        have = {s for s, _ in extra}
        extra += [(i["slug"], i["why"]) for i in g["items"] if i["slug"] not in have]
    more = [(s, w, article_title(s)) for s, w in extra]
    more = [(s, w, t) for s, w, t in more if t and (ROOT / "eachnews" / f"{s}.html").exists()]
    if more:
        b += [f'  <div class="tb-more" style="--tb:{c}">', '    <p class="lb">もっと知りたい人へ</p>']
        for s, w, t in more:
            b.append(f'    <a href="../eachnews/{s}.html">{html.escape(t)}<span>{html.escape(w)}</span></a>')
        b.append('  </div>')

    b += ['  <details class="tb-src">',
          f'    <summary>このページの出典 {len(d["sources"])}本</summary>', '    <ol>']
    for name, url, note in d["sources"]:
        note_html = f"({html.escape(note)})" if note else ""
        b.append(f'      <li><a href="{html.escape(url)}" target="_blank" rel="noopener">'
                 f'{html.escape(name)}</a>{note_html}</li>')
    b += ['    </ol>', '  </details>',
          '  <p class="tb-caution">金額と制度は変わる。実際の手続きは、必ず窓口か公式の資料で確かめてほしい。'
          'このページは公開されている法令・告示・統計・市議会の会議録から作っている。</p>',
          '  <a class="tb-back" href="./">← こんなときは の一覧へ</a>',
          '</div>', '</section>']
    return "\n".join(b)


def update_sitemap(ids):
    """sitemap.xml の手引きページの行を入れ替える。何度走らせても同じ形になる。"""
    p = ROOT / "sitemap.xml"
    if not p.exists():
        return
    xml = p.read_text(encoding="utf-8")
    # いまある手引きの行を一度全部消してから入れ直す(消えた棚を残さないため)
    xml = re.sub(r"[ \t]*<url><loc>[^<]*/sakuin/[^<]+\.html</loc>.*?</url>\n", "", xml)
    today = __import__("datetime").date.today().isoformat()
    rows = "".join(
        f"  <url><loc>{BASE}/sakuin/{i}.html</loc>"
        f"<lastmod>{today}</lastmod><priority>0.6</priority></url>\n" for i in ids)
    xml = xml.replace("</urlset>", rows + "</urlset>")
    p.write_text(xml, encoding="utf-8")


PLAN = {}


def main():
    global PLAN
    PLAN = load_plan()
    OUT_DIR.mkdir(exist_ok=True)
    sheets = []
    missing = []
    for tid in ORDER:
        p = SRC_DIR / f"_tebiki-{tid}.md"
        if not p.exists():
            missing.append(tid)
            continue
        d = parse(p)
        d["id"] = d.get("id") or tid
        sheets.append(d)
        (OUT_DIR / f"{tid}.html").write_text(
            shell(d["label"], d["lead"], f"sakuin/{tid}.html", PAGE_CSS, render_tebiki(d)),
            encoding="utf-8")

    cards = ['<section style="padding-top:var(--space-5);">', '<div class="sk-grid">']
    for d in sheets:
        c = COLORS.get(d.get("color", "indigo"), COLORS["indigo"])
        cards.append(f'  <a class="sk-card" style="--c:{c}" href="{d["id"]}.html">'
                     f'<b>{html.escape(d["label"])}</b><span>{html.escape(d["lead"])}</span></a>')
    cards += ['</div>', '</section>']

    used = {d["id"] for d in sheets}
    rest = [g for gid, g in PLAN.items() if gid not in used]
    rest_html = ""
    if rest:
        r = ['<section style="padding-top:0;padding-bottom:0;">',
             '<details class="sk-rest">',
             f'  <summary>そのほかの{len(rest)}の状況から、記事で探す</summary>']
        for g in rest:
            r += ['  <div class="g">', f'    <h3>{html.escape(g["label"])}</h3>',
                  f'    <p>{html.escape(g["lead"])}</p>', '    <ul>']
            for i in g["items"]:
                t = article_title(i["slug"])
                d_ = {"news": "eachnews", "kenkyu": "jiyu-kenkyu", "book": "book"}[i["kind"]]
                if t and (ROOT / d_ / f'{i["slug"]}.html').exists():
                    r.append(f'      <li><a href="../{d_}/{i["slug"]}.html">{html.escape(t)}</a></li>')
            r += ['    </ul>', '  </div>']
        r += ['</details>', '</section>']
        rest_html = "\n".join(r)

    note = f"""<section style="padding-top:var(--space-4);">
  <div class="sk-note">
    <p><strong>この索引について</strong></p>
    <p>「大洲市民が知っておくべきこと」を並べたページではない。そういうものは、たぶん読む理由がないからだ。</p>
    <p>補助や制度は、当てはまる人が少ないのが普通だ。でも当てはまった人にとっては100%の話で、
    たいていは<strong>その日に初めて探し始める</strong>。だから知識ではなく、状況から引ける形にした。
    それぞれのページには、紆余曲折を書いていない。<strong>手順と金額と窓口だけ</strong>を置いている。</p>
    <p>当てはまる棚が無いときは、<a href="../news/">大洲ノート</a>で記事の一覧から探せる。
    制度や金額は変わるので、実際の手続きは必ず窓口や公式の資料で確かめてほしい。</p>
  </div>
</section>"""

    hero = f"""<section class="page-hero" style="padding-bottom:0;">
  <div class="wrap">
    <h1>{TITLE}</h1>
    <p>家を建てる。親の介護が始まる。市に言いたいことがある。<br>
    そういう日が来たときに引くための索引。{len(sheets)}の状況から、手順と金額と窓口にたどりつける。</p>
  </div>
</section>"""

    (OUT_DIR / "index.html").write_text(
        shell(TITLE, DESC, "sakuin/", INDEX_CSS,
              hero + "\n" + "\n".join(cards) + "\n" + rest_html + "\n" + note),
        encoding="utf-8")

    update_sitemap([d["id"] for d in sheets])

    print(f"  手引き {len(sheets)} 枚 / 索引 1 枚を書いた → sakuin/")
    for d in sheets:
        print(f"    {d['id']:<16} {d['label']}  (手順{len(d['steps'])} 出典{len(d['sources'])})")
    if missing:
        print(f"  まだ原稿が無い: {', '.join(missing)}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
