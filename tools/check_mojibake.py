# -*- coding: utf-8 -*-
r"""日本語テキストに紛れ込んだ「似ているが違う字」を機械で拾う。

Notionへ日本語を書くときにユニコードエスケープを手で組み立てると、
1文字だけ別の漢字に化ける事故が繰り返し起きている。
実際に出たもの: 咽喉→咽畔 / 枠→果 / 鍛→鍵 / 約→絤 / 肝→胝 / 台風→台頨 / 賢→賫

書いたあと全文を目で読み返すのは現実的でないので、
「ふつうの記事本文にはまず出てこない字」を辞書で持って機械に拾わせる。

    python tools/check_mojibake.py ファイル...
    cat x.txt | python tools/check_mojibake.py
"""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# 実際に化けて出てきた字。増えたらここに足す。
SUSPECT = set("畔頨絤胝痑偿賫喰畧綌怱聢")

# 日本語以外の文字体系(キリル・ハングル・タイ・デーヴァナーガリー・ヘブライ・アラビア)
FOREIGN = re.compile(
    "[Ѐ-ӿ가-힯฀-๿"
    "ऀ-ॿ֐-׿؀-ۿ]"
)

# アクセント付きラテン文字。日本語の本文に出たらまず事故。
LATIN_ODD = re.compile("[À-ɏ]")


def scan(name, text):
    bad = 0
    for i, line in enumerate(text.splitlines(), 1):
        hits = [c for c in line if c in SUSPECT]
        hits += FOREIGN.findall(line)
        hits += LATIN_ODD.findall(line)
        if hits:
            bad += 1
            around = line.strip()
            if len(around) > 90:
                around = around[:90] + "..."
            print("  " + name + ":" + str(i) + "  -> " + "".join(sorted(set(hits))))
            print("      " + around)
    return bad


def main():
    args = sys.argv[1:]
    total = 0
    if not args:
        total += scan("(stdin)", sys.stdin.read())
    else:
        for a in args:
            p = Path(a)
            if not p.exists():
                print("  [!] ファイルが無い: " + a)
                continue
            total += scan(p.name, p.read_text(encoding="utf-8"))
    if total:
        print("")
        print("  あやしい行: " + str(total) + " 件。目で確かめること。")
        sys.exit(1)
    print("  あやしい字は見つからなかった。")


if __name__ == "__main__":
    main()
