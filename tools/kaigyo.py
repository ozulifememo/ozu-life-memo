# -*- coding: utf-8 -*-
"""題と吹き出しが、変なところで改行されるのを直す。

## なぜCSSだけでは直らないのか

日本語には単語の切れ目に空白が無いので、ブラウザは既定でほぼどこでも改行する。
「大洲」の途中で切れて「大／洲」になるのはそのため。

CSSには `word-break: auto-phrase` という、文節で折り返す指定がある。
サイトの見出しにはもう入れてある。**それでも切れる。**
Chromeにしか無い指定であるうえ、Chromeで見ても
「まさかの来／館者」のような切れ方が実際に起きた(2026-09-05に実測)。

だから、CSSではなく **壊れてはいけない語を、壊れない箱に入れる** ことにした。
`<span class="nb">` の中身は `white-space: nowrap` で改行されない。
これはどのブラウザでも効く。

## 何を箱に入れるか

1. **数字とその単位**  … 「37,931人」が「37,931／人」に切れるのを防ぐ
2. **土地の名前**      … 「大洲」「肱川」「臥龍山荘」など、切れると読めなくなる語

欲張って全部の熟語を囲うと、こんどは行が余って右端がガタガタになる。
**切れると意味が壊れるものだけ**にしてある。

## 使い方

    python tools/kaigyo.py --check    直す場所を数えるだけ(書き換えない)
    python tools/kaigyo.py            全記事の題と3行要約を直す
    python tools/kaigyo.py --selftest この道具が壊れていないか試す
"""

from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 切れると読めなくなる、この土地の名前。長いものから先に当てる
NAMES = [
    "臥龍山荘", "少彦名神社", "如法寺", "冨士山公園", "オズメッセ",
    "鹿野川ダム", "山鳥坂ダム", "野村ダム", "肱川あらし", "大洲まつり",
    "おおず赤煉瓦館", "おはなはん通り", "ぽこぺん横丁", "うかい",
    "大洲城", "大洲市", "大洲藩", "大洲高校", "大洲駅", "大洲",
    "肱川町", "肱川橋", "肱川", "長浜町", "長浜港", "長浜", "河辺",
    "新谷", "五郎", "菅田", "平野", "喜多", "内子", "宇和島", "八幡浜",
    "西予", "伊予", "松山", "今治", "四国中央", "東温", "新居浜", "西条",
    "愛媛県", "愛媛", "南予", "予讃線", "伊予灘", "鹿野川", "北只", "東大洲",
]

# 数字のうしろに来ると、そこで切ってはいけない単位
UNITS = ("人", "冊", "本", "円", "件", "台", "校", "所", "年", "月", "日",
         "％", "%", "パーセント", "ha", "ヘクタール",
         "km", "キロ", "m", "メートル", "時間", "分", "秒", "回", "棟",
         "戸", "世帯", "社", "店", "区画", "議席", "匹", "頭", "歳", "倍", "割",
         "位", "点", "室", "館", "席", "番", "度", "階", "個", "枚", "part")

# 「5万人」の万を単位と見ると「5万／人」で切れてしまう。万億兆千は数の一部として飲み込む
NUM = r"[0-9０-９][0-9０-９,，.．]*(?:[万億兆千][0-9０-９,，.．]*)*"
UNIT_RE = re.compile("(" + NUM + ")(" + "|".join(re.escape(u) for u in UNITS) + ")")
NAME_RE = re.compile("|".join(re.escape(n) for n in NAMES))

MARK = "nb"


def wrap(text: str) -> str:
    """壊れてはいけないところを <span class="nb"> で囲う。

    すでに囲ってあるところ、タグの中身には触らない。
    """
    if not text or "<span class=\"nb\">" in text:
        return text

    # タグは触らない。タグ以外の地の文だけを対象にする
    out, last = [], 0
    for m in re.finditer(r"<[^>]+>", text):
        out.append(_wrap_plain(text[last:m.start()]))
        out.append(m.group())
        last = m.end()
    out.append(_wrap_plain(text[last:]))
    return "".join(out)


def _wrap_plain(s: str) -> str:
    if not s:
        return s
    # 1. 数字と単位。先にやる(「37,931人」の「人」を名前として拾わないため)
    s = UNIT_RE.sub(lambda m: '<span class="%s">%s%s</span>' % (MARK, m.group(1), m.group(2)), s)
    # 2. 土地の名前。すでに囲った箱の中には入れない
    parts, last = [], 0
    for m in re.finditer(r'<span class="%s">.*?</span>' % MARK, s):
        parts.append(NAME_RE.sub(lambda n: '<span class="%s">%s</span>' % (MARK, n.group()),
                                 s[last:m.start()]))
        parts.append(m.group())
        last = m.end()
    parts.append(NAME_RE.sub(lambda n: '<span class="%s">%s</span>' % (MARK, n.group()),
                             s[last:]))
    return "".join(parts)


# 直す場所。題と、要点3行と、メモうの吹き出し。
# 本文には入れない(長い段落に入れると、かえって行が余る)
TARGETS = (
    (r"(<h1[^>]*>)(.*?)(</h1>)", "題"),
    (r'(<li>)(.*?)(</li>)', "要点3行"),
    (r'(<div class="memou-intro-bubble">.*?)(</div>)', None),   # 中の<p>だけ別処理
)


def fix_html(html: str) -> tuple:
    """1本ぶん。(直した本文, 直した場所の数)"""
    n = [0]

    def h1(m):
        got = wrap(m.group(2))
        if got != m.group(2):
            n[0] += 1
        return m.group(1) + got + m.group(3)

    html = re.sub(r"(<h1[^>]*>)(.*?)(</h1>)", h1, html, flags=re.S)

    # 要点3行のところだけ
    def box(m):
        inner = re.sub(r"(<li>)(.*?)(</li>)",
                       lambda x: x.group(1) + _count(wrap(x.group(2)), x.group(2), n) + x.group(3),
                       m.group(2), flags=re.S)
        return m.group(1) + inner + m.group(3)

    html = re.sub(r'(<div class="article-summary"[^>]*>)(.*?)(</div>)', box, html, flags=re.S)

    # メモうの吹き出し
    def bub(m):
        inner = re.sub(r"(<p>)(.*?)(</p>)",
                       lambda x: x.group(1) + _count(wrap(x.group(2)), x.group(2), n) + x.group(3),
                       m.group(2), flags=re.S)
        return m.group(1) + inner + m.group(3)

    html = re.sub(r'(<div class="memou-intro-bubble">)(.*?)(</div>)', bub, html, flags=re.S)
    return html, n[0]


def _count(got, before, n):
    if got != before:
        n[0] += 1
    return got


def pages():
    for d in ("eachnews", "jiyu-kenkyu", "book"):
        for p in sorted((ROOT / d).glob("*.html")):
            if p.name != "index.html":
                yield p


def selftest() -> int:
    print()
    print("  自己診断: わざと切れる形を作って、囲えるか試します...")
    print()
    cases = [
        ("住民票の人口は37,931人。地区別に見る大洲", ["37,931人", "大洲"]),
        ("大洲城・臥龍山荘、まさかの来館者5万人", ["大洲城", "臥龍山荘", "5万人"]),
        ("ＪＲは赤字、人口は減る。大洲の列車とバスはどうなる？", ["大洲"]),
        ("64億円の文化会館、入札に1社も来なかった", ["64億円", "1社"]),
    ]
    ok = True
    for src, want in cases:
        got = wrap(src)
        miss = [w for w in want
                if ('<span class="nb">%s' % w) not in got and
                   ('>%s<' % w) not in got.replace('<span class="nb">', ">")]
        good = not miss
        print("    [%s] %s" % ("OK " if good else "NG ", src[:34]))
        if not good:
            print("         囲えていない: %s" % miss)
            print("         結果: %s" % got[:150])
        ok = ok and good
    # 壊してはいけないもの
    for src in ("<a href=\"x\">大洲</a>", '<span class="nb">大洲</span>'):
        got = wrap(src)
        good = got.count('class="nb"') <= 1 and "href" not in got.replace('href="x"', "")
        print("    [%s] 二重に囲わない: %s" % ("OK " if good else "NG ", src[:40]))
        ok = ok and good
    print()
    print("  自己診断%s" % ("OK。" if ok else "に失敗しました。"))
    print()
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="題と吹き出しの改行を直す")
    ap.add_argument("--check", action="store_true", help="数えるだけ。書き換えない")
    ap.add_argument("--slug", help="この記事だけ")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if args.selftest:
        return selftest()

    total, files = 0, 0
    for p in pages():
        if args.slug and p.stem != args.slug:
            continue
        s = io.open(p, encoding="utf-8").read()
        got, n = fix_html(s)
        if n and got != s:
            files += 1
            total += n
            if not args.check:
                io.open(p, "w", encoding="utf-8", newline="").write(got)
    print()
    print("  %s: 記事 %d本 / 囲った場所 %d か所"
          % ("数えただけ" if args.check else "直した", files, total))
    if args.check:
        print("  (--check を外すと書き換えます)")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
