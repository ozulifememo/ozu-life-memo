# -*- coding: utf-8 -*-
"""記事HTMLを、Notion「③記事一覧」に入れる形(Notion風Markdown)に変換する。

公開手順(/kokai)ではNotion③への登録まで含まれているが、2026-08-26〜28に
別セッションで公開した11本がNotionに無かった。HTMLからNotion原稿を
機械で起こせるようにして、この手順漏れが起きても後から追いつけるようにする。

変換するもの: h2 / p / strong / ul・ol / 出典欄(callout)
捨てるもの: 要点ボックス・読了時間・吹き出し・図(SVG)・「同じテーマの記事」
(要点と読了時間はHTML側の見せ方の部品なのでNotion原稿には入れない、が方針)

使い方:
  python tools/html2notion.py <slug>            # 標準出力にMarkdown
  python tools/html2notion.py <slug> --json     # プロパティも含めてJSON
"""
import argparse
import html as H
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_site as cs                                    # noqa: E402

CAT = {"ima": "大洲のいま", "kurashi": "大洲の暮らし", "shiten": "大洲の視点"}
SITE = "https://ozulifememo.github.io/ozu-life-memo/"
MDLINK = re.compile(r"\[([^]]*)\]\(([^)]+)\)")   # Markdownのリンク [題](URL)
CELL = re.compile(r"<t([hd])\b([^>]*)>(.*?)</t\1>", re.S | re.I)
SPAN = re.compile(r'(rowspan|colspan)\s*=\s*"?(\d+)', re.I)
KANSUJI = "〇一二三四五六七八九"


def kansuji(n: int) -> str:
    """Notionのプロパティ欄は数量を漢数字で書く(矢印や算用数字が化けた実例あり)"""
    if n < 10:
        return KANSUJI[n]
    if n < 20:
        return "十" + (KANSUJI[n - 10] if n > 10 else "")
    return KANSUJI[n // 10] + "十" + (KANSUJI[n % 10] if n % 10 else "")


def inline(s: str) -> str:
    """段落の中のタグをMarkdownに"""
    s = re.sub(r"<strong\b[^>]*>(.*?)</strong>", r"**\1**", s, flags=re.S)
    s = re.sub(r"<b\b[^>]*>(.*?)</b>", r"**\1**", s, flags=re.S)
    s = re.sub(r"<em\b[^>]*>(.*?)</em>", r"*\1*", s, flags=re.S)
    s = re.sub(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', lambda m: f"[{m.group(2)}]({m.group(1)})", s, flags=re.S)
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = H.unescape(s)
    return " ".join(s.split())


def table_grid(inner: str) -> list:
    """HTMLの表を、行ごとのセルの一覧にする。

    自由研究の表は rowspan / colspan でセルを結合していることがある。
    Markdownの表は結合できないので、結合の続きは空セルで埋めて列数を揃える。

    揃えないと、行ごとにセル数が違ってNotion側で列が丸ごと落ちる。
    2026-08-31、人口47年の記事の「自然減と社会減の内訳」で、
    rowspanを使っていた3列目(差引)が消えて2列の表になった。
    """
    grid = []
    carry = {}                     # 列番号 -> あと何行、上のセルが続くか
    for r in re.findall(r"<tr\b[^>]*>(.*?)</tr>", inner, re.S):
        row, cells, ci, col = [], CELL.findall(r), 0, 0
        while col < 64:            # 表が壊れていても止まるようにする
            if carry.get(col, 0) > 0:
                carry[col] -= 1
                row.append("")     # 上のセルから続いている場所
                col += 1
                continue
            if ci >= len(cells):
                break
            _, attrs, body = cells[ci]
            ci += 1
            spans = {k.lower(): int(v) for k, v in SPAN.findall(attrs)}
            start = col
            row.append(inline(body))
            col += 1
            for _ in range(spans.get("colspan", 1) - 1):
                row.append("")
                col += 1
            if spans.get("rowspan", 1) > 1:
                carry[start] = spans["rowspan"] - 1
        grid.append(row)
    width = max((len(r) for r in grid), default=0)
    for r in grid:
        r.extend([""] * (width - len(r)))
    return grid


def convert(slug: str, subdir: str = "eachnews") -> dict:
    # 記事(eachnews/)だけでなく、大洲の自由研究(jiyu-kenkyu/)や
    # 大洲と読書(book/)からも起こせるようにしてある。
    # 自由研究・読書は news-data.js の台帳に載らないので、そこは空で返る。
    p = cs.REPO / subdir / f"{slug}.html"
    html = cs.read(p)
    reg = cs.load_registry().get(slug, {"slug": slug, "title": "", "category": ""})

    # 本文は <div class="article-page"> から <aside>(サイドバー) の手前まで。
    # ヘッダー・フッター・サイドバー・お問い合わせは記事ではないので最初から外す
    start = html.find('<div class="article-page"')
    if start < 0:
        # 自由研究(jiyu-kenkyu/)はサイドバーが無く、本文は <div class="wrap jk-section">。
        # 読書(book/)も article-page を持たないことがあるので、wrap まで落とす
        for marker in ('<div class="wrap jk-section"', '<div class="wrap"'):
            start = html.find(marker)
            if start >= 0:
                break
    end = html.find("<aside", start)
    body = html[start:end if end > 0 else None]

    # 自由研究の脚注参照 <a href="#fn3" class="jk-fn">[３]</a> は、
    # リンクにすると [[３]](#fn3) と壊れる。ただの番号として残す
    body = re.sub(r'<a\b[^>]*class="jk-fn"[^>]*>(.*?)</a>', r"\1", body, flags=re.S)

    # 出典欄を先に取り出しておき、本文からは除く。
    # 形は <div class="content-block source-box"> の中に <a class="source-link"> が並ぶ
    src_m = re.search(r'<div class="content-block source-box">.*?</div>', body, re.S)
    sources = []
    posted = ""
    if src_m:
        box = src_m.group(0)
        # 掲載日の書き方は「2026/08/28」と「2026年8月26日」の2通りある
        pm = re.search(r'<p class="source-box-posted">.*?(\d{4})[/年](\d{1,2})[/月](\d{1,2}).*?</p>', box, re.S)
        if pm:
            posted = f"{int(pm.group(1))}年{int(pm.group(2))}月{int(pm.group(3))}日"
            box = box[:pm.start()] + box[pm.end():]
        for a in re.finditer(r'<a class="source-link"\s+href="([^"]+)"[^>]*>(.*?)</a>(.*?)(?=<a class="source-link"|</div>)',
                             box, re.S):
            url = H.unescape(a.group(1))
            label = inline(a.group(2))
            rest = inline(a.group(3))
            sources.append((label, url, rest))
        body = body[:src_m.start()] + body[src_m.end():]

    # 自由研究(jiyu-kenkyu/)の出典は、番号付きの脚注 <div class="jk-footnotes">。
    # 1つの脚注にリンクが複数入ったり、リンクが無いものもあるので、
    # 記事の source-box とは別に、行ごとまるごとMarkdown化する
    footnotes = []
    fn_m = re.search(r'<div class="jk-footnotes">.*?</ol>\s*</div>', body, re.S)
    if fn_m:
        for li in re.finditer(r'<li\b[^>]*id="fn(\d+)"[^>]*>(.*?)</li>', fn_m.group(0), re.S):
            footnotes.append((li.group(1), inline(li.group(2))))
        body = body[:fn_m.start()] + body[fn_m.end():]

    # 捨てる部品(要点・読了時間・吹き出し・図はHTML側の見せ方の部品)
    for pat in (r'<div class="article-summary".*?</ul>\s*</div>',
                r'<div class="memou-intro">.*?</div>\s*</div>',
                r"<svg\b.*?</svg>", r"<figure\b.*?</figure>", r"<script\b.*?</script>",
                r"<nav\b.*?</nav>",
                # 自由研究の目次(ページ内リンク)もHTML側の部品。Notion原稿には入れない
                r'<div class="jk-toc">.*?</ol>\s*</div>'):
        body = re.sub(pat, " ", body, flags=re.S | re.I)
    # 記事の帯(カテゴリ・出典名・読了時間)は本文ではない
    body = re.sub(r"<p\b[^>]*>(?:(?!</p>).)*分で読める(?:(?!</p>).)*</p>", " ", body, flags=re.S)

    # 台帳(news-data.js)の、この記事の出典名と情報源日付
    js = cs.read(cs.REPO / "assets" / "js" / "news-data.js")
    em = re.search(r'\{[^{}]*slug:\s*"%s"[^{}]*\}' % re.escape(slug), js, re.S)
    entry = em.group(0) if em else ""
    def field(k):
        mm = re.search(k + r':\s*"([^"]*)"', entry)
        return mm.group(1) if mm else ""
    reg = dict(reg, source=field("source"), sourceDate=field("sourceDate"))
    # 「同じテーマの記事」以降は捨てる
    cut = re.search(r"<h2[^>]*>\s*同じテーマの記事", body)
    if cut:
        body = body[:cut.start()]

    out = []
    for m in re.finditer(r"<(h2|h3|p|ul|ol|blockquote|table)\b[^>]*>(.*?)</\1>", body, re.S | re.I):
        tag, inner = m.group(1).lower(), m.group(2)
        if tag == "h2":
            t = inline(inner)
            if t and "出典" not in t:
                out.append(f"## {t}")
        elif tag == "h3":
            out.append(f"### {inline(inner)}")
        elif tag == "p":
            t = inline(inner)
            if t:
                out.append(t)
        elif tag in ("ul", "ol"):
            items = [inline(li) for li in re.findall(r"<li\b[^>]*>(.*?)</li>", inner, re.S)]
            mark = "-" if tag == "ul" else "1."
            out.append("\n".join(f"{mark} {it}" for it in items if it))
        elif tag == "blockquote":
            out.append("> " + inline(inner))
        elif tag == "table":
            lines = []
            for i, cells in enumerate(table_grid(inner)):
                lines.append("| " + " | ".join(cells) + " |")
                if i == 0:
                    lines.append("|" + "---|" * len(cells))
            out.append("\n".join(lines))

    md = "\n".join(out)
    if sources:
        rows = []
        for label, url, rest in sources:
            # Notionの出典は各リンクに日付注記を付ける決まり。HTML側に無ければ、
            # 記事を掲載した日を「その時点で確認した」注記として付ける
            if rest:
                note = f"({rest})"
            elif posted and not re.search(r"\d{4}年|令和|平成|閲覧", label):
                note = f"({posted}時点)"
            else:
                note = ""
            rows.append(f"\t[{label}]({url}){note}")
        md += "\n<callout icon=\"📎\" color=\"blue_bg\">\n\t**出典・参考にした資料**\n" + "\n".join(rows) + "\n</callout>"
    if footnotes:
        # 脚注の中の相対リンク(../eachnews/xxx.html や同じ階層の yyy.html)は、
        # Notionで開けるようにサイトの絶対URLへ直す
        def abslink(m):
            label, href = m.group(1), m.group(2)
            if not re.match(r"https?:|#", href):
                href = SITE + re.sub(r"^\.\./", "", href) if href.startswith("../") \
                    else f"{SITE}{subdir}/{href}"
            return f"[{label}]({href})"
        rows = ["\t%s. %s" % (n, MDLINK.sub(abslink, t)) for n, t in footnotes]
        md += "\n<callout icon=\"📎\" color=\"blue_bg\">\n\t**出典・参考にした資料**\n" + "\n".join(rows) + "\n</callout>"

    desc = (re.search(r'name="description" content="([^"]*)"', html) or [None, ""])[1]
    # 台帳に載らないページ(自由研究・読書)は、HTML自身のJSON-LDから題と日付を拾う
    if not reg.get("title"):
        hm = re.search(r'"headline"\s*:\s*"([^"]*)"', html) or re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
        reg["title"] = inline(hm.group(1)) if hm else slug
    if not reg.get("date"):
        dm = re.search(r'"datePublished"\s*:\s*"(\d{4})-(\d{2})-(\d{2})', html)
        if dm:
            reg["date"] = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"
    # 出典の要約(プロパティ用)。主な出典の名前+「ほか計N本」
    main = re.sub(r"ほか$", "", reg.get("source", "")).strip()
    n_src = len(sources) or len(footnotes)
    src_summary = f"{main}ほか計{kansuji(n_src)}本" if n_src else main
    return {
        "slug": slug,
        "title": reg["title"],
        "category": CAT.get(reg.get("category", ""), "大洲の視点"),
        "date": reg.get("date", ""),
        "sourceDate": reg.get("sourceDate", ""),
        "source_summary": src_summary,
        "ref_url": sources[0][1] if sources else
                   (re.search(r"\((https?://[^)]+)\)", footnotes[0][1]) or [None, ""])[1] if footnotes else "",
        "desc": H.unescape(desc),
        "n_sources": n_src,
        "url": f"{SITE}{subdir}/{slug}.html",
        "markdown": md,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--dir", default="eachnews",
                    help="HTMLの置き場。eachnews(既定) / jiyu-kenkyu / book")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    r = convert(a.slug, a.dir)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print(r["markdown"])


if __name__ == "__main__":
    main()
