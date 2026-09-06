# -*- coding: utf-8 -*-
"""既存の記事に、書き足した分を差し込む。

なぜ作ったか(2026-09-06)。
短い記事を厚くするとき、これまでは毎回その場かぎりのスクリプトを書いて
HTMLに差し込んでいた。差し込む場所を間違える、出典の本数を直し忘れる、
という事故が起きやすい(実際に「調べた資料 N本」の直し忘れが何度もあった)。
同じことを何度もやるなら道具にする。

使い方:

    python tools/apply_kahitsu.py <スラッグ>
    python tools/apply_kahitsu.py <スラッグ> --check   # 差し込まずに中身だけ見る

読むのは private-notes/genkou/<スラッグ>-add.md。形はこう。

    ---足す出典---
    - [タイトル](URL)（何がここに載っているか）
    ---足す本文---
    ## 見出し
    本文。**太字**、「> 引用」、Markdownの表が使える。

差し込む場所は、出典欄(source-box)の直前。つまり本文のいちばん後ろ。
「調べた資料 N本」は、差し込んだあとの出典リンクの実数に直す。
"""
import argparse
import io
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kiji_md  # build_body / inline を借りる

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent.parent
DIRS = ("eachnews", "jiyu-kenkyu", "book")


def find_html(slug):
    for d in DIRS:
        p = REPO / d / (slug + ".html")
        if p.exists():
            return p
    sys.exit("エラー: %s.html が見つかりません" % slug)


def parse(md_path):
    t = io.open(md_path, encoding="utf-8").read()
    if "---足す本文---" not in t:
        sys.exit("エラー: ---足す本文--- がありません: %s" % md_path)
    head, body = t.split("---足す本文---", 1)
    srcs = []
    if "---足す出典---" in head:
        for line in head.split("---足す出典---", 1)[1].splitlines():
            line = line.strip()
            m = re.match(r"^-\s*\[(.+?)\]\((\S+?)\)\s*(?:[（(](.*)[）)])?\s*$", line)
            if m:
                label, url, note = m.group(1), m.group(2), (m.group(3) or "")
                srcs.append((label, url, note))
    return srcs, body.strip()


def main():
    ap = argparse.ArgumentParser(description="記事に書き足した分を差し込む")
    ap.add_argument("slug")
    ap.add_argument("--check", action="store_true", help="差し込まずに中身を見る")
    args = ap.parse_args()

    md = REPO / "private-notes" / "genkou" / (args.slug + "-add.md")
    if not md.exists():
        sys.exit("エラー: %s がありません" % md)
    html_path = find_html(args.slug)
    srcs, body_md = parse(md)

    body_html = kiji_md.build_body(body_md)
    n_h2 = body_html.count("<h2>")
    n_chars = len(re.sub(r"\s", "", re.sub(r"<[^>]+>", "", body_html)))

    print("  %s" % html_path.relative_to(REPO))
    print("    足す本文  %d字 / 見出し %d個" % (n_chars, n_h2))
    print("    足す出典  %d本" % len(srcs))
    for label, url, note in srcs:
        print("      - %s" % label[:60])
    if args.check:
        print("\n  --check なので書き換えていません")
        return 0

    s = io.open(html_path, encoding="utf-8").read()

    anchor = '    <div class="content-block source-box">'
    if s.count(anchor) != 1:
        anchor = '<div class="content-block source-box">'
    if s.count(anchor) != 1:
        sys.exit("エラー: 出典欄の位置が見つかりません")
    s = s.replace(anchor, body_html + "\n" + anchor)

    if srcs:
        posted = '      <p class="source-box-posted">'
        if s.count(posted) != 1:
            posted = '<p class="source-box-posted">'
        if s.count(posted) != 1:
            sys.exit("エラー: 掲載日の行が見つかりません")
        rows = []
        for label, url, note in srcs:
            text = label + ("　— " + note if note else "")
            rows.append('<a class="source-link" href="%s" target="_blank" '
                        'rel="noopener">%s</a>' % (url, text))
        s = s.replace(posted, "\n      ".join(rows) + "\n      " + posted)

    actual = len(re.findall(r'class="source-link"', s))
    m = re.search(r"調べた資料\s*(\d+)本", s)
    if m:
        s = s.replace(m.group(0), "調べた資料 %d本" % actual)
        print("    出典の数え直し  %s本 → %d本" % (m.group(1), actual))

    io.open(html_path, "w", encoding="utf-8", newline="").write(s)
    print("\n  差し込みました。このあと apply_memou.py / kaigyo.py /")
    print("  add_readtime.py / check_site.py を走らせること")
    return 0


if __name__ == "__main__":
    sys.exit(main())
