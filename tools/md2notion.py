# -*- coding: utf-8 -*-
"""下書きのMarkdownの表を、Notionの仕様どおりの書き方に組み替える。

記事はHTMLから起こせる(html2notion.py)が、まだ公開していない下書きは
Markdownのまま手元にある。その表の書き方を揃えるための道具。

【使う前に知っておくこと】
**Markdownのパイプ表(| A | B |)でも、Notionは表に変換してくれる。**
だから「パイプ表のままでは読めない」ということはない。
2026-08-31に、パイプ表で登録済みのページを notion-fetch で読んで確認した。
<table header-row="true"> として返ってきた。

つまりこのスクリプトは**必須ではない**。仕様どおりの形にしておけば
Notion側の変換に頼らずに済む、というだけの違いである。
急いで既存のページを組み替える必要はない。

(この道具は、パイプ表が表にならないと思い込んで作った。
 その思い込みは間違いだった。経緯は引き継ぎに残してある。)

パイプ表を <table header-row="true"> に組み替える。
表以外はそのままなので、何度掛けても壊れない(すでに <table> になっている
ところには手を出さない)。

使い方:
  python tools/md2notion.py <Markdownのパス>          # 標準出力に出す
  python tools/md2notion.py <パス> -o <出力先>         # ファイルに書く
"""
import argparse
import re
import sys
from pathlib import Path

SEP = re.compile(r"^\s*\|[\s:|-]+\|\s*$")     # |---|---| のような区切り行


def cells_of(line: str) -> list:
    """| A | B | の1行を、セルの一覧にする"""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def convert(md: str) -> str:
    out = []
    lines = md.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        # 表の始まりは「| で始まる行」が2行以上続くところ
        if line.lstrip().startswith("|") and i + 1 < len(lines) \
                and lines[i + 1].lstrip().startswith("|"):
            block = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                block.append(lines[i])
                i += 1
            rows = [cells_of(b) for b in block if not SEP.match(b)]
            # 区切り行があれば1行目が見出し
            header = any(SEP.match(b) for b in block)
            width = max(len(r) for r in rows)
            out.append('<table header-row="%s">' % ("true" if header else "false"))
            for r in rows:
                r = r + [""] * (width - len(r))
                out.append("\t<tr>")
                out += ["\t\t<td>" + c + "</td>" for c in r]
                out.append("\t</tr>")
            out.append("</table>")
            continue
        out.append(line)
        i += 1
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="下書きMarkdownをNotionに貼れる形にする")
    ap.add_argument("path")
    ap.add_argument("-o", "--out", help="出力先(省略すると標準出力)")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    md = Path(a.path).read_text(encoding="utf-8")
    res = convert(md)
    if a.out:
        Path(a.out).write_text(res, encoding="utf-8", newline="\n")
        n = res.count('<table header-row=')
        print("表 %d 個を <table> に組み替えました: %s" % (n, a.out))
    else:
        print(res)


if __name__ == "__main__":
    main()
