# -*- coding: utf-8 -*-
"""Notionに入れた本文が、手元の原稿と1文字も違わないかを確かめる。

【なぜ要るか】
Notionに日本語を書き込むとき、`\\uXXXX` のエスケープを手で組み立てると漢字が
別の似た字に化ける。2026-08-31の1日だけで15件起きた(「窮屈」→「窐屈」、
「腑」→「腐」、「直線」→「直異」など)。生の文字を書けば起きないが、
**書けたかどうかは照合しないと分からない。**

【よくある落とし穴】
「Notionから読み返して見比べる」だけでは足りない。読み返した本文を自分で
打ち直してファイルにすると、そこで同じ打ち間違いをして一致してしまう。
**打ち直しが1文字でも入る方法は、検査になっていない。**

そこでこのスクリプトは、セッションの会話ログ(JSONL)に記録されている
`notion-fetch` の生の返り値を直接取り出す。人の手を通らないので穴がない。

【使い方】
1. 確かめたいページを `notion-fetch` で取る(会話ログに残る)
2. 手元の原稿を「正」として、これを走らせる

    python tools/notion_verify.py <スラッグ> <原稿のパス>

【出るもの】
違いがあれば、その位置・前後の文脈・両方のコードポイント(U+XXXX)。
無ければ「1文字も違いなし」。

タグ(<table> など)・空白・NotionがつけるURLの自動リンク化・`\\[` の
エスケープは、仕様上かならず出る差なので落としてから比べる。
それ以外は一切ならさない。
"""
import argparse
import glob
import io
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def logs_dir() -> Path:
    """このプロジェクトの会話ログが置かれている場所"""
    key = str(REPO).replace(":", "-").replace("\\", "-").replace("/", "-").lower()
    return Path.home() / ".claude" / "projects" / ("c" + key[1:] if key[1:2] == "-" else key)


def walk_text(obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "text" and isinstance(v, str):
                out.append(v)
            else:
                walk_text(v, out)
    elif isinstance(obj, list):
        for v in obj:
            walk_text(v, out)


def fetched_body(marker: str):
    """会話ログから、notion-fetch が返したページ本文を取り出す。

    **かならず、いちばん新しい取得を使う。** ここを間違えると危ない。
    ページを直したあとに照合しても、直す前の古い取得を拾ってしまえば
    「1文字も違いなし」と出てしまい、検査になっていない。
    だから行のタイムスタンプで並べ替えて、最後のものを採る。
    いつ取得したものかも呼び出し元に返して、画面に出す。
    """
    base = logs_dir()
    files = glob.glob(str(base / "*.jsonl")) + glob.glob(str(base / "*" / "subagents" / "*.jsonl"))
    found = []
    for p in files:
        for line in io.open(p, encoding="utf-8", errors="replace"):
            if marker not in line:
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            out = []
            walk_text(o, out)
            for t in out:
                if "<page url=" in t and "</content>" in t and marker in t:
                    found.append((o.get("timestamp") or "", os.path.basename(p), t))
    if not found:
        return None
    found.sort(key=lambda x: x[0])       # 取得した時刻の順
    stamp, src, t = found[-1]
    print("  もとにした取得: %s（%s）／候補 %d 件のうち、いちばん新しいもの"
          % (stamp or "時刻不明", src, len(found)))
    t = t.strip()
    if t.startswith("{"):
        try:
            o2 = json.loads(t)
            if isinstance(o2, dict) and isinstance(o2.get("text"), str):
                t = o2["text"]
        except Exception:
            pass
    body = t[t.index("<content>") + len("<content>"):t.rindex("</content>")]
    return body[1:] if body.startswith("\n") else body


def norm(s: str) -> str:
    """仕様上かならず出る差だけを落とす。中身の文字はいじらない"""
    s = re.sub(r"\[([^\[\]]+)\]\(\1\)", r"\1", s)   # NotionのURL自動リンク化 [u](u) → u
    s = re.sub(r"<[^>]*>", "", s)                   # <table><tr><td> などのタグ
    s = s.replace("\\", "")                         # Notionがつける \[ \] のエスケープ
    return re.sub(r"\s+", "", s)                    # 空白・タブ・改行


def resync(a: str, b: str, i: int):
    """字が抜けた・増えたときの、ずれを吸収する。合わせられたら True を返す。

    合わせる目印は、はじめ30字で探し、見つからなければ12字で探す。
    壊れが近くに2つあると、30字の中に次の壊れが入ってしまって合わせられない。
    (実際、これで「本当は2箇所」が20件に見えた)
    """
    for width in (30, 12):
        for shift in range(1, 80):
            if a[i + shift:i + shift + width] == b[i:i + width]:
                return a[:i] + a[i + shift:], b, True
            if b[i + shift:i + shift + width] == a[i:i + width]:
                return a, b[:i] + b[i + shift:], True
    return a, b, False


def compare(a_raw: str, b_raw: str) -> int:
    a, b = norm(a_raw), norm(b_raw)
    print("  原稿   : %6d字 → 比べるのは %d字" % (len(a_raw), len(a)))
    print("  Notion : %6d字 → 比べるのは %d字" % (len(b_raw), len(b)))
    n, i = 0, 0
    while i < min(len(a), len(b)):
        if a[i] != b[i]:
            n += 1
            ca, cb = a[i], b[i]
            print("\n  --- 違い %d つめ(%d文字目)" % (n, i))
            print("    原稿   : %r U+%04X %s" % (ca, ord(ca), unicodedata.name(ca, "?")))
            print("    Notion : %r U+%04X %s" % (cb, ord(cb), unicodedata.name(cb, "?")))
            print("    原稿   : …%s[%s]%s…" % (a[max(0, i - 30):i], ca, a[i + 1:i + 31]))
            print("    Notion : …%s[%s]%s…" % (b[max(0, i - 30):i], cb, b[i + 1:i + 31]))
            if n >= 20:
                print("  (20件で打ち切り)")
                break
            # 1文字だけの置き換えなら、ずれていない。そのまま次へ。
            # (これを見ないと、後ろの文を削って無理に合わせにいってしまい、
            #  差が連鎖して「本当は2箇所」が20件に見える)
            if a[i + 1:i + 31] == b[i + 1:i + 31]:
                i += 1
                continue
            # ずれを吸収して、後ろも見られるようにする
            a, b, ok = resync(a, b, i)
            if not ok:
                i += 1
            continue
        i += 1
    if len(a) != len(b):
        print("\n  長さが違う: 原稿 %d / Notion %d" % (len(a), len(b)))
        print("    原稿の末尾   : %s" % a[-70:])
        print("    Notionの末尾 : %s" % b[-70:])
        n += 1
    return n


def main():
    ap = argparse.ArgumentParser(description="Notionの本文と手元の原稿を1文字ずつ照合する")
    ap.add_argument("marker", help="そのページを見分ける語(スラッグなど)")
    ap.add_argument("source", help="手元の原稿(こちらを「正」とする)")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    body = fetched_body(a.marker)
    if body is None:
        print("会話ログに、そのページの notion-fetch の結果が見つかりません。")
        print("先に notion-fetch で取ってから、もう一度走らせてください。")
        print("(探した場所: %s)" % logs_dir())
        sys.exit(1)

    src = Path(a.source).read_text(encoding="utf-8")
    print("照合: %s" % a.marker)
    n = compare(src, body)
    print("=" * 56)
    print("  違い %d件" % n if n else "  1文字も違いなし")
    sys.exit(1 if n else 0)


if __name__ == "__main__":
    main()
