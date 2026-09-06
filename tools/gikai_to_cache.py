"""会議録の出典を、手元のキャッシュから照合用キャッシュに写す。

なぜ要るか。

大洲市のサイトは自動アクセスを弾く。記事が市議会の会議録を出典に挙げていると、
`check_numbers.py` がそれを取りに行って 403 で弾かれ、「出典が取れず」になる。
その出典で裏付けた数字が、まとめて「出典に無い」と出てしまう。

だが会議録は `tools/_gikai_cache/` に307回分そろっている。`gikai.py` が使うために
落としてあるもので、中身は同じである。取りに行かずに、ここから写せばよい。

ファイル名とURLは1対1で対応している。

    tools/_gikai_cache/H27_201503teirei-4.html
    https://www.city.ozu.ehime.jp/kaigiroku/H27/201503teirei-4.html

使い方:

    python tools/gikai_to_cache.py                 追跡中の記事ぜんぶを見て、
                                                   足りない会議録を写す
    python tools/gikai_to_cache.py --slug ozu-ukai-kanransha
    python tools/gikai_to_cache.py --dry-run       写さずに、何をするかだけ出す

2026-09-06に作った。うかいの記事と野佐来の記事で、同じ403に2回続けて
当たったので道具にした。
"""

import argparse
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GIKAI = ROOT / "tools" / "_gikai_cache"
CACHE = ROOT / "tools" / "_source_cache"

# https://www.city.ozu.ehime.jp/kaigiroku/R04/202212teirei-4.html
KAIGIROKU = re.compile(
    r"https?://www\.city\.ozu\.ehime\.jp/kaigiroku/([A-Za-z0-9]+)/([^\"'\s<>]+\.html)")


def cache_path(url: str) -> Path:
    """check_numbers.py と同じ決め方でキャッシュのファイル名を作る"""
    return CACHE / (hashlib.sha1(url.encode("utf-8")).hexdigest() + ".txt")


def to_text(html_text: str) -> str:
    """会議録のHTMLから本文だけ取り出す。整形はしない(照合は字面だけ見る)"""
    t = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", html_text)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"),
                 ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'")):
        t = t.replace(a, b)
    return re.sub(r"[ \t　]+", " ", t)


def article_files(slug=None):
    for d in ("eachnews", "jiyu-kenkyu", "book"):
        for p in sorted((ROOT / d).glob("*.html")):
            if slug is None or p.stem == slug:
                yield p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", help="この記事だけ見る")
    ap.add_argument("--dry-run", action="store_true", help="写さずに一覧だけ出す")
    args = ap.parse_args()

    if not GIKAI.is_dir():
        print("  会議録のキャッシュ(tools/_gikai_cache/)がありません")
        return 1
    CACHE.mkdir(exist_ok=True)

    urls = {}
    for p in article_files(args.slug):
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in KAIGIROKU.finditer(text):
            urls.setdefault(m.group(0), []).append(p.stem)

    if not urls:
        print("\n  会議録を出典にしている記事はありませんでした\n")
        return 0

    wrote, already, missing = 0, 0, []
    for url, used_by in sorted(urls.items()):
        m = KAIGIROKU.match(url)
        src = GIKAI / (m.group(1) + "_" + m.group(2))
        dst = cache_path(url)
        if dst.exists() and dst.stat().st_size > 0:
            already += 1
            continue
        if not src.exists():
            missing.append((url, used_by[0]))
            continue
        if args.dry_run:
            print("  写す: %-58s ← %s" % (url[-58:], src.name))
        else:
            dst.write_text(to_text(src.read_text(encoding="utf-8", errors="replace")),
                           encoding="utf-8")
        wrote += 1

    print("\n  会議録の出典 %d本" % len(urls))
    print("    もう照合できる  : %d本" % already)
    print("    %s: %d本" % ("写すつもり    " if args.dry_run else "手元から写した", wrote))
    if missing:
        print("    手元にも無い    : %d本" % len(missing))
        for url, who in missing[:8]:
            print("      %s  (%s)" % (url, who))
        print("      ※ gikai.py のキャッシュの範囲(平成20年3月〜)の外かもしれません")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
