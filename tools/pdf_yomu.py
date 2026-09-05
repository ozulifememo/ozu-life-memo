# -*- coding: utf-8 -*-
"""PDFの出典を、目で読める形にする。

## なぜ要るか

出典のPDFには、文字を取り出せないものがある。2026-09-05に数えたら、
出典に使っているPDF347本のうち13本がそうだった(記事8本に影響)。

  - 紙をスキャンしただけのPDF … 中身が全部画像。文字が1つも入っていない
  - 表を線と字形で描いたPDF   … 画像も文字も無いのに、見ると表が見える

check_numbers.py はこういうPDFから0字しか取れないので、その出典で
裏付けているはずの数字が全部「出典に見つからない」と出る。実際、
図書館の記事は数字32個が未照合のままだった。出典が悪いのではなく、
機械が読めないだけ。**読めないことに気づけないのが一番まずい。**

## 使い方

    python tools/pdf_yomu.py <URLかファイルのパス>            中身を調べる
    python tools/pdf_yomu.py <URLかファイルのパス> --page 3   3ページ目を画像にする
    python tools/pdf_yomu.py <URLかファイルのパス> --all      全ページを画像にする

画像にしたら、その画像を読んで数字を目で拾う。人でも、目のあるエージェント
でもよい。OCRは使わない。**数字を1桁読み違えたら意味が無い仕事**なので、
自信のない機械に任せるより、見て確かめるほうが確実だと判断した。

    python tools/pdf_yomu.py --list    読めないPDFを全部並べる
"""

from __future__ import annotations

import argparse
import html as html_mod
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parent
sys.path.insert(0, str(TOOLS))

import check_site as cs        # noqa: E402
import check_numbers as cn     # noqa: E402

# 出しても読めない大きさでは意味が無い。2倍にすると表の細かい数字が読める
ZOOM = 2.0
# これ未満しか文字が取れなければ「読めないPDF」とみなす
THIN_PDF = 100
OUT = TOOLS / "_pdf_yomu"


def load(target: str) -> tuple:
    """PDFの中身を取ってくる。(バイト列, どこから取ったか)"""
    p = Path(target)
    if p.exists():
        return p.read_bytes(), str(p)

    url = html_mod.unescape(target)
    import requests
    r = requests.get(url, headers=cn.HEADERS, timeout=60)
    if r.status_code != 200:
        raise SystemExit("  取れませんでした: HTTP %d  %s" % (r.status_code, url))
    return r.content, url


def describe(doc) -> tuple:
    """何ページで、文字と画像がどれだけ入っているか"""
    text = "\n".join(page.get_text() for page in doc)
    imgs = sum(len(page.get_images()) for page in doc)
    return text, imgs


def cmd_show(args) -> int:
    import fitz

    body, where = load(args.target)
    with fitz.open(stream=body, filetype="pdf") as doc:
        text, imgs = describe(doc)
        n = len(doc)
        print()
        print("  %s" % where)
        print("  %dページ / 取り出せた文字 %d字 / 画像 %d個 / %.1fMB"
              % (n, len(text.strip()), imgs, len(body) / 1024 / 1024))

        if len(text.strip()) >= THIN_PDF and not (args.page or args.all):
            print()
            print("  このPDFは文字が取り出せます。画像にする必要はありません。")
            print("  先頭:", text.strip()[:200].replace("\n", " "))
            print()
            return 0

        if not (args.page or args.all):
            print()
            if imgs:
                print("  中身が画像です(紙をスキャンしたPDF)。文字は入っていません。")
            else:
                print("  文字も画像も取り出せません(表を線と字形で描いたPDF)。")
            print("  --page <番号> か --all を付けると、画像にして目で読めます。")
            print()
            return 1

        pages = range(n) if args.all else [args.page - 1]
        OUT.mkdir(exist_ok=True)
        stem = Path(where).stem or "pdf"
        made = []
        for i in pages:
            if not 0 <= i < n:
                print("  %dページ目はありません(全%dページ)" % (i + 1, n))
                continue
            pm = doc[i].get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM))
            f = OUT / ("%s_p%02d.png" % (stem, i + 1))
            pm.save(f)
            made.append(f)
        print()
        for f in made:
            print("  %s" % f)
        print()
        print("  この画像を読んで、数字を目で拾ってください。")
        print("  OCRは使っていません。1桁読み違えたら意味が無い仕事なので、")
        print("  自信のない機械に任せるより見て確かめるほうが確実です。")
        print()
    return 0


def cmd_transcribe(args) -> int:
    """画像から目で読み取った中身を、出典キャッシュに戻す。

    読めないPDFを画像にして目で読んでも、そのままでは check_numbers.py は
    次も0字のまま「出典に見つからない」と言い続ける。読んだ結果を
    キャッシュに戻して初めて、照合が通るようになる。

    ただし **誰がいつ目で読んだのかを必ず頭に書く。** 機械が取った文章と
    人が読み取った文章は、当てになる度合いが違う。混ぜたら分からなくなる。
    """
    text = Path(args.transcribe).read_text(encoding="utf-8")
    url = html_mod.unescape(args.target)
    head = ("[この出典は文字を取り出せないPDFです。%s に %s が画像を見て"
            "読み取りました。機械が取った文章ではありません]\n"
            % (args.date, args.by))
    c = cn.cache_path(url)
    old = len(c.read_text(encoding="utf-8")) if c.exists() else 0
    c.parent.mkdir(exist_ok=True)
    c.write_text(cn.normalize(head + text), encoding="utf-8")
    print()
    print("  %s" % url)
    print("  キャッシュを %d字 → %d字 にしました" % (old, len(c.read_text(encoding="utf-8"))))
    print("  %s" % c)
    print()
    return 0


def cmd_list(args) -> int:
    """出典に使っているPDFのうち、中身が取れないものを並べる"""
    from collections import defaultdict
    used = defaultdict(list)
    for p in cs.collect_pages():
        if cs.page_type(p) not in ("article", "kenkyu", "book"):
            continue
        for u in cs.source_urls(p, cs.read(p)):
            u = html_mod.unescape(u)
            if u.lower().endswith(".pdf"):
                used[u].append(cs.rel(p))

    bad = []
    for u, arts in used.items():
        c = cn.cache_path(u)
        if not c.exists():
            continue
        n = len(c.read_text(encoding="utf-8"))
        if n < THIN_PDF:
            bad.append((n, u, arts))
    bad.sort()

    print()
    print("  出典に使っているPDF %d本 / うち中身が取れないもの %d本"
          % (len(used), len(bad)))
    arts = sorted({a for _, _, v in bad for a in v})
    print("  影響を受ける記事 %d本" % len(arts))
    print()
    for n, u, v in bad:
        print("  %4d字  %s" % (n, u))
        print("          %s" % ", ".join(v))
    if bad:
        print()
        print("  python tools/pdf_yomu.py <URL> --all で画像にして読めます。")
    print()
    return 1 if bad else 0


def selftest() -> int:
    """道具が壊れていないか、その場で作ったPDFで試す"""
    import fitz
    print()
    print("  自己診断: その場でPDFを作って、読めるか試します...")
    print()
    ok = True

    # 1. 文字の入ったPDFは、文字が取れること
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), "845 886 309")
    body = doc.tobytes()
    doc.close()
    with fitz.open(stream=body, filetype="pdf") as d:
        text, imgs = describe(d)
    a = "845" in text
    print("    [%s] 文字の入ったPDFから文字が取れる" % ("OK " if a else "NG "))
    ok = ok and a

    # 2. 画像にできること(文字が取れないPDFのための逃げ道)
    with fitz.open(stream=body, filetype="pdf") as d:
        pm = d[0].get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM))
    b = pm.width > 100 and pm.height > 100
    print("    [%s] ページを画像にできる(%dx%d)" % ("OK " if b else "NG ",
                                                   pm.width, pm.height))
    ok = ok and b

    # 3. 空のPDFを「読めない」と判定できること
    doc = fitz.open()
    doc.new_page()
    empty = doc.tobytes()
    doc.close()
    with fitz.open(stream=empty, filetype="pdf") as d:
        text2, imgs2 = describe(d)
    c = len(text2.strip()) < THIN_PDF
    print("    [%s] 中身の無いPDFを「読めない」と判定する" % ("OK " if c else "NG "))
    ok = ok and c

    print()
    print("  自己診断%s" % ("OK。" if ok else "に失敗しました。"))
    print()
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(
        description="文字の取り出せないPDFの出典を、画像にして目で読めるようにする")
    ap.add_argument("target", nargs="?", help="PDFのURL、またはファイルのパス")
    ap.add_argument("--page", type=int, help="このページだけ画像にする(1から数える)")
    ap.add_argument("--all", action="store_true", help="全ページを画像にする")
    ap.add_argument("--list", action="store_true", help="読めないPDFを全部並べる")
    ap.add_argument("--transcribe", metavar="FILE",
                    help="目で読み取った中身(テキストファイル)を出典キャッシュに戻す")
    ap.add_argument("--by", default="opus", help="誰が読み取ったか")
    ap.add_argument("--date", default="", help="いつ読み取ったか(既定は今日)")
    ap.add_argument("--selftest", action="store_true", help="この道具を試す")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if not args.date:
        import datetime
        args.date = datetime.date.today().isoformat()
    if args.selftest:
        return selftest()
    if args.transcribe:
        if not args.target:
            print("  読み取り元のURLも指定してください")
            return 1
        return cmd_transcribe(args)
    if args.list:
        return cmd_list(args)
    if not args.target:
        ap.print_help()
        return 0
    return cmd_show(args)


if __name__ == "__main__":
    sys.exit(main())
