# -*- coding: utf-8 -*-
"""Notion②の原稿(.md)から、記事HTMLを組み立てる。

これまで公開作業でやっていた「Notionの本文を手でHTMLに直す」を機械にやらせる。
手作業だと <strong> の付け忘れ、source-box クラスの付け忘れ、
タイトルの4か所同期漏れが毎回どこかで起きていたため。

入力ファイルの形(private-notes/genkou/スラッグ.md):

    slug: xxxx
    title: 記事タイトル
    category: shiten | kurashi | ima
    desc: meta description の1文
    source: 冒頭と台帳に出す出典の表示名
    tags: 政治・行政,財政・税金
    source_date: 2023-12-01
    ---要点---
    - 1行目
    - 2行目
    - 3行目
    ---出典---
    - [表示名](URL)（注記）
    ---本文---
    ## 見出し
    段落。**太字**が使える。

    **箇条書きの見出し**
    - 項目
    - 項目

使い方:
    python tools/kiji_md.py private-notes/genkou/xxxx.md
    python tools/kiji_md.py private-notes/genkou/*.md
"""
import html
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent


def parse(path):
    raw = path.read_text(encoding="utf-8")
    parts = re.split(r"^---(要点|出典|本文)---$", raw, flags=re.M)
    head = parts[0]
    sec = {}
    for i in range(1, len(parts), 2):
        sec[parts[i]] = parts[i + 1].strip()

    meta = {}
    for line in head.strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    for need in ("slug", "title", "category", "desc", "source"):
        if not meta.get(need):
            sys.exit("エラー: " + path.name + " に " + need + " がない")
    for need in ("要点", "出典", "本文"):
        if need not in sec:
            sys.exit("エラー: " + path.name + " に ---" + need + "--- がない")
    return meta, sec


def inline(t):
    """**太字** と 「」内の強調をHTMLにする。タグは書かせない前提でエスケープ済み。"""
    t = html.escape(t, quote=False)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)


def build_body(text):
    out = []
    buf = []          # 箇条書きの受け皿
    list_title = None

    def flush_list():
        nonlocal buf, list_title
        if not buf:
            return
        out.append('    <div class="fact-list">')
        if list_title:
            out.append("      <p class=\"fact-list-title\">" + inline(list_title) + "</p>")
        out.append("      <ul>")
        for b in buf:
            out.append("        <li>" + inline(b) + "</li>")
        out.append("      </ul>")
        out.append("    </div>")
        out.append("")
        buf, list_title = [], None

    lines = text.splitlines()
    for i, line in enumerate(lines):
        s = line.strip()
        if not s:
            flush_list()
            continue
        if s.startswith("## "):
            flush_list()
            out.append("    <h2>" + inline(s[3:].strip()) + "</h2>")
            continue
        if s.startswith("- "):
            # 直前の段落が箇条書きの見出しなら、それを取り込む
            if not buf and out and out[-1].startswith("    <p") and re.fullmatch(
                r"\s*<p class=\"commentary\"><strong>.+</strong></p>", out[-1]
            ):
                list_title = re.sub(r"</?[^>]+>", "", out.pop()).strip()
            buf.append(s[2:].strip())
            continue
        flush_list()
        out.append("    <p class=\"commentary\">" + inline(s) + "</p>")
    flush_list()
    return "\n".join(out).rstrip() + "\n"


def build_sources(text):
    rows = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("- "):
            continue
        m = re.match(r"- \[(.+?)\]\((\S+?)\)(.*)$", s)
        if not m:
            sys.exit("エラー: 出典の書き方が違う -> " + s)
        label = (m.group(1) + m.group(3)).strip()
        rows.append(
            '      <a class="source-link" href="' + m.group(2)
            + '" target="_blank" rel="noopener">' + html.escape(label, quote=False) + "</a>"
        )
    if len(rows) < 2:
        sys.exit("エラー: 出典が2本未満")
    return "\n".join(rows), len(rows)


def build_summary(text, n_sources):
    items = [l.strip()[2:].strip() for l in text.splitlines() if l.strip().startswith("- ")]
    if len(items) != 3:
        sys.exit("エラー: 要点は3行ちょうどにする(いまは" + str(len(items)) + "行)")
    li = "\n".join("        <li>" + inline(x) + "</li>" for x in items)
    return (
        '    <div class="article-summary">\n'
        '      <p class="article-summary-label">3行でいうと'
        '<span class="article-summary-sources">調べた資料 ' + str(n_sources) + "本</span></p>\n"
        "      <ul>\n" + li + "\n      </ul>\n"
        "    </div>\n"
    )


def one(path):
    meta, sec = parse(path)
    slug = meta["slug"]
    target = ROOT / "eachnews" / (slug + ".html")

    if not target.exists():
        cmd = [
            sys.executable, str(ROOT / "tools" / "new_kiji.py"),
            "--slug", slug, "--title", meta["title"],
            "--category", meta["category"], "--desc", meta["desc"],
            "--source", meta["source"],
        ]
        if meta.get("tags"):
            cmd += ["--tags", meta["tags"]]
        if meta.get("source_date"):
            cmd += ["--source-date", meta["source_date"]]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0:
            sys.exit("new_kiji.py が失敗: " + (r.stderr or r.stdout))

    doc = target.read_text(encoding="utf-8")
    src_html, n = build_sources(sec["出典"])

    # 要点ボックスと本文をまとめて差し替える。目印は「要点ボックスの始まり」と
    # 「出典欄の始まり」の2つだけにしてある。<!-- 本文ここから --> を目印にすると
    # 一度差し替えた時点で目印が消えてしまい、2回目以降が黙って空振りするため。
    block = re.compile(
        r'[ \t]*<div class="article-summary">.*?'
        r'(?=[ \t]*<div class="content-block source-box">)',
        re.S,
    )
    if not block.search(doc):
        sys.exit("エラー: " + slug + ".html に要点ボックスか出典欄が見つからない")
    doc = block.sub(
        lambda _: build_summary(sec["要点"], n) + build_body(sec["本文"]) + "\n",
        doc, count=1,
    )
    doc = re.sub(
        r'(<h2 class="source-box-title">出典・参考にした資料</h2>\n).*?(?=\n?[ \t]*<p class="source-box-posted")',
        lambda m: m.group(1) + src_html,
        doc, count=1, flags=re.S,
    )
    target.write_text(doc, encoding="utf-8")
    print("  " + slug + "  (出典" + str(n) + "本)")


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit("使い方: python tools/kiji_md.py 原稿.md ...")
    for a in args:
        one(Path(a))
    print("できた。このあと add_readtime.py と check_site.py を走らせること。")


if __name__ == "__main__":
    main()
