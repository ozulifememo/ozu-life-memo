# -*- coding: utf-8 -*-
"""下書きのMarkdownを、Notionに貼れる形(Notion-flavored Markdown)に直す。

記事はHTMLから起こせる(html2notion.py)が、まだ公開していない下書きは
Markdownのまま手元にある。それをNotionに入れるとき、**Markdownのパイプ表は
表にならない**。Notion-flavored Markdown の仕様に、パイプ表は無いからだ。
そのまま文字列として貼り付くだけで、読めない。

2026-08-31に実測して分かった。すでに登録してあった記事のページで
「| ランク | 点数 | 判定内容 |」という文字列がそのままマッチした。

このスクリプトは、パイプ表を <table header-row="true"> に組み替える。
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
