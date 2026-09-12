# -*- coding: utf-8 -*-
"""公開済みの記事の題を、まとめて差し替える。

2026-09-12に作った。題を横1行に収める仕組みを入れたあと、
それでも2行になる41本の題が残った。字を詰めても入らないので、
題そのものを短くするしかなかった。本人の許可を得てまとめて差し替える。

**題を変えたら、そろえる場所が5つある。**どれか1つでも忘れると
check_site.py の検査「タイトル」が止める。

    記事HTML  <title> / og:title / JSON-LDのheadline / <h1>
    台帳      assets/js/news-data.js の title

<h1> には改行の箱(<span class="nb">)が入っているので、
いったん素の題に戻す。そのあと kaigyo.py を走らせ直すこと。

使い方:

    python tools/rename_titles.py <差し替え表.json>
    python tools/rename_titles.py <差し替え表.json> --check   # 見るだけ

差し替え表は [{"slug": "...", "old": "いまの題", "new": "新しい題"}, ...] の形。
"""
import argparse
import io
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent.parent
DIRS = ("eachnews", "jiyu-kenkyu", "book")


def find_html(slug):
    for d in DIRS:
        p = REPO / d / (slug + ".html")
        if p.exists():
            return p
    return None


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s)


def rename_one(rec, check):
    slug, old, new = rec["slug"], rec["old"], rec["new"]
    p = find_html(slug)
    if not p:
        return None, "HTMLがありません"
    html = io.open(p, encoding="utf-8").read()

    # h1 は改行の箱が入っているので、タグを外して見比べる
    m = re.search(r"(<h1[^>]*>)(.*?)(</h1>)", html, re.S)
    if not m or strip_tags(m.group(2)).strip() != old:
        return None, "h1がいまの題と合いません: %r" % (strip_tags(m.group(2)).strip() if m else None)

    n_plain = html.count(old)     # title / og:title / headline のぶん
    if n_plain < 3:
        return None, "題が%d か所にしかありません(3か所あるはず)" % n_plain

    out = html.replace(old, new)
    m2 = re.search(r"(<h1[^>]*>)(.*?)(</h1>)", out, re.S)
    out = out[:m2.start()] + m2.group(1) + new + m2.group(3) + out[m2.end():]

    if strip_tags(out).count(old):
        return None, "古い題が残りました"
    if not check:
        io.open(p, "w", encoding="utf-8", newline="\n").write(out)
    return n_plain + 1, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("table")
    ap.add_argument("--check", action="store_true", help="書き換えずに見るだけ")
    args = ap.parse_args()

    recs = json.loads(io.open(args.table, encoding="utf-8").read())
    js_path = REPO / "assets" / "js" / "news-data.js"
    js = io.open(js_path, encoding="utf-8").read()

    ok = ng = 0
    for r in recs:
        n, err = rename_one(r, args.check)
        if err:
            print("  NG  %-32s %s" % (r["slug"], err))
            ng += 1
            continue
        # 台帳。題は1か所だけのはず
        c = js.count('"%s"' % r["old"])
        if c != 1:
            print("  NG  %-32s 台帳に題が%d か所(1か所のはず)" % (r["slug"], c))
            ng += 1
            continue
        js = js.replace('"%s"' % r["old"], '"%s"' % r["new"])
        print("  OK  %-32s HTML %d か所 + 台帳  %d字→%d字"
              % (r["slug"], n, len(r["old"]), len(r["new"])))
        ok += 1

    if not args.check and ok:
        io.open(js_path, "w", encoding="utf-8", newline="\n").write(js)

    print()
    print("  直した %d本 / 直せなかった %d本" % (ok, ng))
    if not args.check:
        print("  このあと必ず: kaigyo.py → add_readtime.py → make_feed.py → check_site.py")
    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(main())
