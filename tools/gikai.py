#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大洲市議会の会議録を検索する
==================================================================

大洲市議会の会議録は、平成20年ごろから全文が市のサイトに公開されています。
新聞記事より情報量が多く、しかも消えません。「あの件、当時どうだったの?」を
調べるときの一番の資料です(松下寿の記事はこれで書けました)。

このスクリプトは、その会議録を年度をまたいで一気に検索します。

    # 使い方(PowerShellで、このリポジトリのフォルダから)
    python tools/gikai.py 松下寿                     # 全期間から探す
    python tools/gikai.py 新幹線 --from 2020         # 2020年以降だけ
    python tools/gikai.py 空き家 --width 800         # 前後800字ずつ見る
    python tools/gikai.py 給食費 --list              # ヒットした会議の一覧だけ

一度取ってきた会議録はローカルに保存(キャッシュ)するので、2回目以降は一瞬です。
保存先は tools/_gikai_cache/ で、.gitignore 済み(GitHubには上げません)。

【なぜGitHubに置かないか】
会議録は市が公開している資料ですが、まるごと複製して公開リポジトリに置くのは
筋が悪く、容量も無駄です。このPCの中にキャッシュしておけば、検索は十分速い。
"""
import argparse
import datetime
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
CACHE = REPO / "tools" / "_gikai_cache"
BASE = "https://www.city.ozu.ehime.jp/kaigiroku/"
UA = "Mozilla/5.0 (compatible; OZU-LIFE-MEMO-research/1.0)"

# 平成21年→H21、令和2年→R02 のようにフォルダ名が変わる
#
# 2019年の扱いに注意(2026-08-31に実測して判明)。
# 改元は2019年5月1日なので、暦の上では6月・9月・12月の定例会は令和元年にあたる。
# ところが市のサイトは、2019年ぶんを4回とも H31 フォルダに置いている。
# R01 というフォルダは存在しない。ここを R01 で探していたため、
# 2019年の会議録16本がまるごと検索から漏れていた(復興計画が確定した年だった)。
def folder_for(year: int) -> str:
    if year <= 2019:            # 2019年は令和元年だが、市のサイトでは H31
        return f"H{year - 1988:02d}"
    return f"R{year - 2018:02d}"  # 2020年(令和2年)から R02


def candidates(y_from: int, y_to: int):
    for year in range(y_from, y_to + 1):
        folder = folder_for(year)
        for mm in ("03", "06", "09", "12"):
            for n in ("1", "2", "3", "4", "5"):
                yield year, f"{folder}/{year}{mm}teirei-{n}.html"


def fetch(rel: str) -> str | None:
    """会議録1ページを取る。キャッシュがあればそれを使う。"""
    cached = CACHE / rel.replace("/", "_")
    if cached.exists():
        return cached.read_text(encoding="utf-8", errors="replace")

    req = urllib.request.Request(BASE + rel, headers={"User-Agent": UA})
    try:
        raw = urllib.request.urlopen(req, timeout=45).read()
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return None

    # 古いページはeuc-jp、新しいものはutf-8。中身を見て判定する
    text = None
    for enc in ("utf-8", "euc-jp", "cp932"):
        try:
            t = raw.decode(enc)
        except UnicodeDecodeError:
            continue
        if "議長" in t or "定例会" in t:
            text = t
            break
    if text is None:
        text = raw.decode("utf-8", errors="replace")

    CACHE.mkdir(parents=True, exist_ok=True)
    cached.write_text(text, encoding="utf-8")
    time.sleep(0.3)  # 市のサーバーに負荷をかけない
    return text


def plain(html: str) -> str:
    html = re.sub(r"<script\b.*?</script>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<style\b.*?</style>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text)


def label(rel: str) -> str:
    m = re.search(r"/(\d{4})(\d{2})teirei-(\d)", rel)
    if not m:
        return rel
    y, mm, n = m.group(1), int(m.group(2)), m.group(3)
    return f"{y}年{mm}月定例会 {n}日目"


def main():
    ap = argparse.ArgumentParser(description="大洲市議会の会議録を検索する")
    ap.add_argument("keyword", help="探したい言葉")
    ap.add_argument("--from", dest="y_from", type=int, default=2008, help="開始年(既定2008)")
    ap.add_argument("--to", dest="y_to", type=int, default=datetime.date.today().year)
    ap.add_argument("--width", type=int, default=400, help="前後に表示する文字数(既定400)")
    ap.add_argument("--max", type=int, default=3, help="1つの会議録で表示する最大ヒット数")
    ap.add_argument("--list", action="store_true", help="ヒットした会議の一覧だけ出す")
    args = ap.parse_args()

    kw = args.keyword
    hits = 0
    print(f"「{kw}」を{args.y_from}〜{args.y_to}年の会議録から探します...\n")

    for _year, rel in candidates(args.y_from, args.y_to):
        html = fetch(rel)
        if not html:
            continue
        text = plain(html)
        if kw not in text:
            continue
        hits += 1
        url = BASE + rel
        print(f"■ {label(rel)}")
        print(f"  {url}")
        if not args.list:
            for i, m in enumerate(re.finditer(re.escape(kw), text)):
                if i >= args.max:
                    print(f"  （ほかにもヒットあり。--max を増やすと見られます）")
                    break
                s = max(0, m.start() - args.width)
                e = m.start() + args.width
                print(f"  …{text[s:e]}…")
                print()
        print()

    if hits == 0:
        print("見つかりませんでした。言い回しを変えてみてください")
        print("（例: 「パナソニック」で出なければ「松下」、「新幹線」なら「鉄道」も試す）")
    else:
        print(f"{hits}件の会議録にありました。")
        print("記事の出典に使うときは、上のURLをそのまま貼れます。")


if __name__ == "__main__":
    main()
