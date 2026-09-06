"""原稿(Markdown)を「大洲の自由研究」のページにする。

`kiji_md.py` の自由研究版。作りは同じで、出来上がる形だけが違う。

    記事(eachnews)    要点3行・メモうの吹き出し・source-box の出典欄
    自由研究          目次・脚注番号つきの出典・シリーズ番号

自由研究は21本あるが、どれも手で作られていた。2026-09-06、11,076字の原稿を
自由研究にしたくなったときに、手で組むしかない状態だったので道具にした。

使い方:

    python tools/kenkyu_md.py private-notes/genkou/<スラッグ>.md
    python tools/kenkyu_md.py private-notes/genkou/<スラッグ>.md --num 22

原稿の形は `kiji_md.py` と同じ。ただし自由研究では次が変わる。

- `category` は使わない(自由研究は1つの区分しかない)
- `---要点---` は目次の下の導入として使う(3行ボックスにはしない)
- 出典は脚注として下に並ぶ。本文から `[^1]` で参照できる

このあと `add_readtime.py` は自由研究を見ない(記事専用)ので、
読了目安は本文の長さから自分で書き込む。
"""

import argparse
import html
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "jiyu-kenkyu"
INDEX = OUT / "index.html"
SITE = "https://ozulifememo.github.io/ozu-life-memo"

# 見た目の定義。既存21本と同じものを使う(ページごとに持つのが今の作法)
JK_STYLE = """  .jk-hero { background: linear-gradient(180deg, var(--color-surface-alt) 0%, transparent 100%); }
  .jk-meta { display:flex; gap:14px; flex-wrap:wrap; margin-top:14px; font-size:.82rem; color:var(--color-text-muted); }
  .jk-meta span { background:var(--color-surface); border:1px solid var(--color-border); border-radius:4px; padding:4px 12px; }
  .jk-toc { background:var(--color-surface); border:1px solid var(--color-border); border-radius:var(--radius); padding:20px 24px; margin:32px 0; }
  .jk-toc h2 { margin-top:0; font-size:1rem; }
  .jk-toc ol { margin:0; padding-left:1.3em; color:var(--color-text-muted); line-height:2; font-size:.92rem; }
  .jk-toc a { color:inherit; }
  .jk-toc a:hover { color:var(--color-brand); }
  .jk-section { max-width:760px; margin:0 auto; }
  .jk-section h2 { color:var(--color-brand); font-size:1.35rem; margin:52px 0 16px; scroll-margin-top:20px; }
  .jk-section h3 { color:var(--color-text); font-size:1.05rem; margin:28px 0 10px; }
  .jk-section p.commentary { margin-bottom:16px; }
  .jk-callout { background:var(--color-surface-alt); border-left:3px solid var(--color-brand); border-radius:4px; padding:14px 18px; margin:20px 0; font-size:.92rem; color:var(--color-text-muted); }
  .jk-quote { border-left:3px solid var(--color-text-faint); background:var(--color-surface); padding:14px 20px; margin:20px 0; font-size:.93rem; line-height:1.9; }
  .jk-quote .src { display:block; margin-top:8px; font-size:.78rem; color:var(--color-text-muted); }
  .jk-code { background:var(--color-surface-alt); border:1px solid var(--color-border); border-radius:var(--radius); padding:16px 18px; margin:20px 0; overflow-x:auto; font-size:.85rem; line-height:1.7; }
  .jk-code code { font-family:"SFMono-Regular",Consolas,"Liberation Mono",Menlo,monospace; white-space:pre; }
  table.jk-table { width:100%; border-collapse:collapse; font-size:.88rem; margin:16px 0; }
  table.jk-table th, table.jk-table td { text-align:left; padding:9px 12px; border-bottom:1px solid var(--color-border); vertical-align:top; }
  table.jk-table th { color:var(--color-text-muted); font-weight:700; font-size:.78rem; }
  .jk-table-wrap { overflow-x:auto; margin:16px 0; }
  .jk-diagram { background:var(--color-surface); border:1px solid var(--color-border); border-radius:var(--radius); padding:16px 8px; overflow-x:auto; margin:24px 0; }
  .jk-diagram svg { display:block; width:100%; height:auto; min-width:720px; }
  .jk-fig-caption { text-align:center; font-size:.82rem; color:var(--color-text-muted); margin-top:10px; }
  .jk-fn { font-size:.7em; vertical-align:super; color:var(--color-brand); text-decoration:none; }
  .jk-footnotes { font-size:.85rem; color:var(--color-text-muted); border-top:1px solid var(--color-border); padding-top:20px; margin-top:56px; }
  .jk-footnotes li { margin-bottom:8px; }
  .jk-series-note { background:var(--color-surface-alt); border-radius:var(--radius); padding:16px 20px; font-size:.85rem; color:var(--color-text-muted); margin:32px auto; max-width:760px; }"""

KANSUJI = "〇一二三四五六七八九"


def kansuji(n: int) -> str:
    """脚注の番号を、既存21本と同じ全角・漢数字の見た目にする"""
    if n < 10:
        return KANSUJI[n]
    if n < 20:
        return "十" + (KANSUJI[n % 10] if n % 10 else "")
    return KANSUJI[n // 10] + "十" + (KANSUJI[n % 10] if n % 10 else "")


def parse(path: Path):
    """原稿を、見出し部分と ---○○--- の区画に分ける(kiji_md.py と同じ形)"""
    text = path.read_text(encoding="utf-8")
    head, _, rest = text.partition("---要点---")
    meta = {}
    for line in head.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    sec = {}
    parts = re.split(r"^---(要点|出典|本文)---$", "---要点---" + rest, flags=re.M)
    for i in range(1, len(parts), 2):
        sec[parts[i]] = parts[i + 1].strip()
    for need in ("slug", "title", "desc"):
        if not meta.get(need):
            sys.exit("エラー: " + path.name + " に " + need + " がない")
    for need in ("要点", "出典", "本文"):
        if need not in sec:
            sys.exit("エラー: " + path.name + " に ---" + need + "--- がない")
    return meta, sec


def inline(t: str) -> str:
    """**太字** と `コード` をHTMLにする。タグは書かせない前提"""
    t = html.escape(t, quote=False)
    kept = []

    def keep(m):
        kept.append(m.group(1))
        return "\x00%d\x00" % (len(kept) - 1)

    t = re.sub(r"`([^`]+?)`", keep, t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\[\^(\d+)\]",
               lambda m: '<a href="#fn%s" class="jk-fn">[%s]</a>'
                         % (m.group(1), kansuji(int(m.group(1)))), t)
    return re.sub(r"\x00(\d+)\x00",
                  lambda m: "<code>" + kept[int(m.group(1))] + "</code>", t)


def build_body(text: str):
    """本文を組む。見出しには目次から飛べるIDを振る"""
    out, heads = [], []
    quote, table, code = [], [], []
    in_code = False
    n = 0

    def flush_quote():
        nonlocal quote
        if not quote:
            return
        cite = None
        if len(quote) > 1 and re.match(r"^(--|—|―|-\s)", quote[-1]):
            cite = re.sub(r"^(--|—|―|-)\s*", "", quote.pop())
        out.append('    <div class="jk-quote">')
        for q in quote:
            out.append("      " + inline(q) + "<br>")
        if cite:
            out.append('      <span class="src">' + inline(cite) + "</span>")
        out.append("    </div>")
        quote = []

    def flush_table():
        nonlocal table
        if not table:
            return
        rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in table]
        rows = [r for r in rows if not all(re.fullmatch(r":?-{2,}:?", c) for c in r)]
        out.append('    <div class="article-table-wrap"><table class="jk-table">')
        for i, r in enumerate(rows):
            tag = "th" if i == 0 else "td"
            out.append("      <tr>" + "".join(
                "<%s>%s</%s>" % (tag, inline(c), tag) for c in r) + "</tr>")
        out.append("    </table></div>")
        table = []

    def flush_code():
        nonlocal code
        while code and not code[0].strip():
            code.pop(0)
        while code and not code[-1].strip():
            code.pop()
        if not code:
            return
        out.append('    <div class="jk-code"><code>'
                   + html.escape("\n".join(code), quote=False)
                   + "</code></div>")
        code = []

    for line in text.splitlines():
        s = line.strip()
        if s.startswith("```"):
            if in_code:
                flush_code()
                in_code = False
            else:
                flush_quote()
                flush_table()
                in_code = True
            continue
        if in_code:
            code.append(line.rstrip())
            continue
        if s.startswith("|") and s.endswith("|") and s.count("|") >= 3:
            flush_quote()
            table.append(s)
            continue
        flush_table()
        if s.startswith(">"):
            quote.append(s.lstrip(">").strip())
            continue
        flush_quote()
        if not s:
            continue
        if s.startswith("## "):
            n += 1
            label = s[3:].strip()
            heads.append(("ch%d" % n, label))
            out.append('    <h2 id="ch%d">%s</h2>' % (n, inline(label)))
            continue
        if s.startswith("### "):
            out.append("    <h3>" + inline(s[4:].strip()) + "</h3>")
            continue
        if s.startswith("- "):
            out.append('    <p class="commentary">・' + inline(s[2:].strip()) + "</p>")
            continue
        out.append('    <p class="commentary">' + inline(s) + "</p>")
    flush_quote()
    flush_table()
    flush_code()
    return "\n".join(out), heads


def build_footnotes(text: str) -> str:
    rows = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("- "):
            continue
        m = re.match(r"- \[(.+?)\]\((\S+?)\)(.*)$", s)
        if not m:
            continue
        title, url, tail = m.group(1), m.group(2), m.group(3).strip()
        rows.append('        <li id="fn%d"><a href="%s" target="_blank" rel="noopener">%s</a>%s</li>'
                    % (len(rows) + 1, html.escape(url, quote=True),
                       inline(title), inline(tail)))
    return "\n".join(rows), len(rows)


def next_number() -> int:
    nums = [int(m) for f in OUT.glob("*.html")
            for m in re.findall(r"大洲の自由研究 #(\d+)",
                                f.read_text(encoding="utf-8", errors="replace"))]
    return (max(nums) + 1) if nums else 1


def readtime(body_html: str) -> str:
    n = len(re.sub(r"\s", "", re.sub(r"<[^>]+>", "", body_html)))
    lo = max(5, round(n / 600 / 5) * 5)
    return "%d〜%d分" % (lo, lo + 5)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("md")
    ap.add_argument("--num", type=int, help="シリーズ番号(省略すると次の番号)")
    args = ap.parse_args()

    src = Path(args.md)
    if not src.is_absolute():
        src = ROOT / args.md
    meta, sec = parse(src)
    slug = meta["slug"]
    num = args.num or next_number()

    body, heads = build_body(sec["本文"])
    notes, n_src = build_footnotes(sec["出典"])
    lead = " ".join(re.sub(r"^- ", "", l).strip()
                    for l in sec["要点"].splitlines() if l.strip())
    lead = re.sub(r"\*\*(.+?)\*\*", r"\1", lead)
    today = meta.get("source_date") or date.today().isoformat()
    url = SITE + "/jiyu-kenkyu/" + slug + ".html"
    toc = "\n".join('        <li><a href="#%s">%s</a></li>'
                    % (i, re.sub(r"\*\*(.+?)\*\*", r"\1", h)) for i, h in heads)

    page = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(meta['title'])} ｜ 大洲の自由研究 ｜ OZU LIFE MEMO</title>
<meta name="description" content="{html.escape(meta['desc'], quote=True)}">
<link rel="icon" href="../assets/img/favicon-192.png">
<link rel="alternate" type="application/rss+xml" title="OZU LIFE MEMO の更新" href="../feed.xml">
<link rel="apple-touch-icon" href="../assets/img/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link data-ozu-fonts rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&amp;family=Shippori+Mincho+B1:wght@600;700&amp;display=swap">
<link rel="stylesheet" href="../assets/css/style.css">
<meta property="og:type" content="article">
<meta property="og:site_name" content="OZU LIFE MEMO">
<meta property="og:title" content="{html.escape(meta['title'], quote=True)} ｜ 大洲の自由研究">
<meta property="og:description" content="{html.escape(meta['desc'], quote=True)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}/assets/img/ogp-card.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="{url}">
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{html.escape(meta['title'], quote=True)}",
  "description": "{html.escape(meta['desc'], quote=True)}",
  "datePublished": "{today}",
  "dateModified": "{today}",
  "image": "{SITE}/assets/img/ogp-card.png",
  "author": {{"@type": "Organization", "name": "OZU LIFE MEMO"}},
  "publisher": {{"@type": "Organization", "name": "OZU LIFE MEMO"}},
  "mainEntityOfPage": {{"@type": "WebPage", "@id": "{url}"}}
}}
</script>
<style>
{JK_STYLE}
</style>
</head>
<body>

<div data-site-header data-prefix="../"></div>

<section class="jk-hero">
  <div class="wrap" style="max-width:820px;">
    <p style="font-size:.8rem;letter-spacing:.06em;color:var(--color-brand);font-weight:700;margin-bottom:10px;">大洲の自由研究 #{num:02d}</p>
    <h1 style="font-size:clamp(1.6rem,4vw,2.1rem);line-height:1.5;">{inline(meta['title'])}</h1>
    <p style="color:var(--color-text-muted);margin-top:14px;">
      {html.escape(lead)}
    </p>
    <div class="jk-meta">
      <span>読了目安 {readtime(body)}</span>
      <span>公開: {today.replace('-', '/')}</span>
      <span>調べた資料 {n_src}本</span>
    </div>
  </div>
</section>

<section>
  <div class="wrap jk-section">

    <div class="jk-toc">
      <h2>目次</h2>
      <ol>
{toc}
      </ol>
    </div>

{body}

    <div class="jk-footnotes">
      <p style="font-weight:700;color:var(--color-text);margin-bottom:10px;">出典</p>
      <ol>
{notes}
      </ol>
    </div>

    <div class="jk-series-note">
      この記事は「大洲の自由研究」シリーズの{num}本目です。通常の<a href="../news/">大洲ノート</a>より
      長く、専門的な内容を含みます。<a href="index.html">シリーズ一覧はこちら</a>。
    </div>

  </div>
</section>

<div data-site-footer></div>
<div data-site-modal></div>
<script src="../assets/js/site-chrome.js"></script>
<script src="../assets/js/main.js"></script>
<script data-goatcounter="https://ozulifememo.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
</body>
</html>
"""
    dst = OUT / (slug + ".html")
    dst.write_text(page, encoding="utf-8")

    # 一覧ページにも1件足す
    idx = INDEX.read_text(encoding="utf-8")
    if slug + ".html" not in idx:
        card = ('      <div class="jk-card">\n'
                '        <span class="jk-num">#%d</span>\n'
                '        <h3><a href="%s.html">%s</a></h3>\n'
                '        <p>%s</p>\n'
                '        <div class="jk-badges"><span>読了%s</span><span>%s</span></div>\n'
                '      </div>\n'
                % (num, slug, html.escape(meta["title"]), html.escape(meta["desc"]),
                   readtime(body), today.replace("-", "/")))
        last = idx.rfind("      </div>\n    </div>")
        if last < 0:
            print("  ! 一覧ページの差し込み位置が分からなかった。手で足すこと")
        else:
            end = idx.index("\n", last) + 1
            idx = idx[:end] + card + idx[end:]
            INDEX.write_text(idx, encoding="utf-8")

    print("  %s  #%d  見出し%d個 / 出典%d本 / 読了%s"
          % (slug, num, len(heads), n_src, readtime(body)))
    print("できた。このあと check_site.py と make_feed.py を走らせること。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
