#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notion②の本文と、サイトのHTMLがズレていないか調べる
==================================================================

2026-09-04に、次の2つが同じ日に見つかった。どちらも「たまたま」見つかった。

  1. サイト側で出典を直したのに、Notion②が古いまま(20本)
  2. Notionへの書き込みで文字が化けた(3本)。数字まで変わっていた
     例: 「約１億8,500万円」→「約1冄4,500万円」

点検スクリプト(check_site.py)はHTMLしか見ないので、Notion側は
機械が一度も見ていなかった。だからこの道具を作った。

CLAUDE.md の方針:
  「新しいルールを言われたら、まず検査として足せないかを考える」

## 使い方

Notionの本文はMCP経由でしか取れないので、この道具は2段構えになっている。

  1) 比べる材料を作る(ローカルだけで完結)

        python tools/notion_diff.py prepare              # 全記事
        python tools/notion_diff.py prepare --slug xxx   # 1本だけ

     → tools/_notion_diff/<スラッグ>.md  … HTMLから作った「正しい本文」
       tools/_notion_diff/_index.json    … 字数・出典数・末尾・数字の一覧

  2) Notionの本文を取ってきて、同じ場所に <スラッグ>.notion.md として置く
     (クロコが notion-fetch した内容を書き出す)

  3) 突き合わせる

        python tools/notion_diff.py check                # 置いてある分を全部
        python tools/notion_diff.py check --slug xxx     # 1本だけ

## 何を見るか

  ずれ    … 行単位の差分(本文が違う)
  化け    … Notion側にだけ現れる文字(冄・熀・戰 のような字)
  数字    … 数字を出現順に総当たりで照合。1個でも違えばエラー
  切れ    … 末尾の一文が一致するか(本文が途中で終わっていないか)
  出典    … リンクの本数と、URLそのものが一致するか

数字の照合がいちばん大事。このサイトは数字が価値なので、
静かに1桁変わるのがいちばん怖い。
"""
from __future__ import annotations

import argparse
import difflib
import io
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
WORK = HERE / "_notion_diff"

# 数字。全角も半角も、カンマ・小数点つきも拾う
NUM = re.compile(r"[0-9０-９][0-9０-９,，\.．]*")
# リンク [題](URL)
LINK = re.compile(r"\]\((https?://[^)]+)\)")


def norm_num(s: str) -> str:
    """全角の数字を半角にそろえる(比較用)。カンマは落とす"""
    z = "０１２３４５６７８９，．"
    h = "0123456789,."
    for a, b in zip(z, h):
        s = s.replace(a, b)
    return s.replace(",", "").rstrip(".")


def numbers(text: str) -> list:
    """本文に出てくる数字を、出現順に並べる"""
    return [norm_num(m.group(0)) for m in NUM.finditer(text)]


def body_of(md: str) -> str:
    """出典calloutを除いた本文"""
    return md.split("<callout")[0].rstrip()


def links_of(md: str) -> list:
    return LINK.findall(md)


def last_line(md: str) -> str:
    lines = [L for L in body_of(md).split("\n") if L.strip()]
    return lines[-1] if lines else ""


def article_slugs() -> list:
    """サイトにある記事のスラッグ(eachnews のみ。②の対象)"""
    return sorted(p.stem for p in (REPO / "eachnews").glob("*.html"))


def build(slug: str) -> dict:
    """HTMLから「正しい本文」を作る"""
    r = subprocess.run([sys.executable, str(HERE / "html2notion.py"), slug, "--json"],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError("html2notion.py が失敗しました: %s\n%s" % (slug, r.stderr[:300]))
    return json.loads(r.stdout)


def cmd_prepare(args) -> int:
    WORK.mkdir(exist_ok=True)
    slugs = [args.slug] if args.slug else article_slugs()
    index = {}
    for s in slugs:
        try:
            d = build(s)
        except Exception as e:
            print("  [飛ばした] %s (%s)" % (s, e))
            continue
        md = d["markdown"]
        (WORK / (s + ".md")).write_text(md, encoding="utf-8", newline="")
        index[s] = {
            "title": d["title"],
            "字数": len(md),
            "出典": d["n_sources"],
            "末尾": last_line(md),
            "数字の数": len(numbers(body_of(md))),
        }
    (WORK / "_index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8", newline="")
    print("\n  %d本ぶんの「正しい本文」を %s に作りました" % (len(index), WORK))
    print("  次に、Notionの本文を <スラッグ>.notion.md として同じ場所に置いてください。")
    return 0


def compare(slug: str, want: str, got: str) -> list:
    """1本ぶんの突き合わせ。見つけた問題を並べて返す"""
    ng = []

    wb, gb = body_of(want), body_of(got)

    # 1. 数字(いちばん大事)
    wn, gn = numbers(wb), numbers(gb)
    if wn != gn:
        # どこで食い違ったか、最初の1つを示す
        for i, (a, b) in enumerate(zip(wn, gn)):
            if a != b:
                ctx = ""
                m = list(NUM.finditer(gb))
                if i < len(m):
                    j = m[i].start()
                    ctx = re.sub(r"\s+", " ", gb[max(0, j - 40):j + 40])
                ng.append(("数字", "%d個目が違います: 正 %s / Notion %s" % (i + 1, a, b),
                           "       …%s…" % ctx))
                break
        else:
            ng.append(("数字", "個数が違います: 正 %d個 / Notion %d個" % (len(wn), len(gn)), ""))

    # 2. 化け(Notion側にだけ出る文字)
    extra = sorted(set(gb) - set(wb))
    # 空白や記号のゆれは無視
    extra = [c for c in extra if not c.isspace() and c not in "　"]
    if extra:
        ng.append(("化け", "Notion側にだけある文字: %s" % " ".join(extra),
                   "       元の本文に無い字が入っています。書き込み時の化けの疑いがあります"))

    # 3. 切れ
    if last_line(want) != last_line(got):
        ng.append(("切れ", "末尾の一文が違います",
                   "       正 : %s\n       Notion: %s" % (last_line(want)[-50:], last_line(got)[-50:])))

    # 4. 出典
    wl, gl = links_of(want), links_of(got)
    if len(wl) != len(gl):
        ng.append(("出典", "リンクの本数が違います: 正 %d本 / Notion %d本" % (len(wl), len(gl)), ""))
    else:
        for a, b in zip(wl, gl):
            if a != b:
                ng.append(("出典", "URLが違います", "       正 : %s\n       Notion: %s" % (a, b)))
                break

    # 5. 行単位の差分(上のどれにも当たらない文章の違い)
    if not ng:
        wl2 = [L for L in wb.split("\n") if L.strip()]
        gl2 = [L for L in gb.split("\n") if L.strip()]
        if wl2 != gl2:
            d = list(difflib.unified_diff(wl2, gl2, lineterm="", n=0))
            ng.append(("ずれ", "本文が違います(数字と出典は一致)",
                       "\n".join("       " + x for x in d[2:8])))
    return ng


def cmd_check(args) -> int:
    if not WORK.exists():
        print("  先に prepare を走らせてください")
        return 1
    slugs = [args.slug] if args.slug else sorted(
        p.name[:-len(".notion.md")] for p in WORK.glob("*.notion.md"))
    if not slugs:
        print("  Notion側の本文(<スラッグ>.notion.md)が1つも置かれていません")
        return 1

    total_ng = 0
    checked = 0
    for s in slugs:
        w, g = WORK / (s + ".md"), WORK / (s + ".notion.md")
        if not w.exists():
            print("  [飛ばした] %s … 正しい本文がありません(prepare してください)" % s)
            continue
        if not g.exists():
            print("  [飛ばした] %s … Notionの本文が置かれていません" % s)
            continue
        checked += 1
        ng = compare(s, w.read_text(encoding="utf-8"), g.read_text(encoding="utf-8"))
        if not ng:
            print("  [OK ] %s" % s)
            continue
        total_ng += len(ng)
        print("  [NG ] %s" % s)
        for kind, msg, detail in ng:
            print("     [%s] %s" % (kind, msg))
            if detail:
                print(detail)

    print()
    print("=" * 68)
    if total_ng:
        print(" %d本を見て、%d件の食い違いが見つかりました" % (checked, total_ng))
        print(" 数字と化けは、直さないと記事の中身が嘘になります")
    else:
        print(" %d本すべて、Notionとサイトの中身が一致しています" % checked)
    print("=" * 68)
    return 1 if total_ng else 0


def cmd_missing(args) -> int:
    """②に登録されていない記事を出す(スラッグの一覧を渡してもらう方式)"""
    if not args.registered:
        print("  ②に登録済みのスラッグを並べたテキストを --registered で渡してください")
        return 1
    have = set(Path(args.registered).read_text(encoding="utf-8").split())
    miss = [s for s in article_slugs() if s not in have]
    print("\n  サイトの記事 %d本 / ②に登録済み %d本" % (len(article_slugs()), len(have)))
    if miss:
        print("  ②に未登録: %d本" % len(miss))
        for s in miss:
            print("     " + s)
    else:
        print("  未登録はありません")
    extra = sorted(have - set(article_slugs()))
    if extra:
        print("  ②にあるがサイトに無い(自由研究など): %d本" % len(extra))
    return 0


def selftest() -> int:
    """この道具が本当に食い違いを見つけられるか、わざと壊して試す"""
    print("\n  自己診断: わざと壊した本文を作って、検知できるか試します...")
    base = ("大洲市の職員は640人である。\n"
            "総務92人、税務19人、土木43人。\n"
            "約１億8,500万円がかかっている。\n"
            "これで終わりである。\n"
            "<callout icon=\"📎\" color=\"blue_bg\">\n"
            "\t[出典A](https://example.com/a)\n"
            "\t[出典B](https://example.com/b)\n"
            "</callout>")
    cases = [
        ("数字", base.replace("約１億8,500万円", "約1冄4,500万円")),
        ("化け", base.replace("総務92人", "総牲92人")),
        ("切れ", base.replace("これで終わりである。\n", "")),
        ("出典", base.replace("https://example.com/b", "https://example.com/c")),
        # 「ずれ」は最後の砦なので、他の検査に引っかからない壊し方で試す。
        # 新しい字を足さず・数字を変えず・末尾でもない行から、句点だけ落とす。
        ("ずれ", base.replace("土木43人。\n", "土木43人\n")),
    ]
    ok = True
    for want_kind, broken in cases:
        kinds = [k for k, _, _ in compare("test", base, broken)]
        hit = want_kind in kinds
        print("    [%s] %s を検知%s" % ("OK " if hit else "NG ", want_kind,
                                        "" if hit else " ← できていない"))
        ok = ok and hit
    # 壊していないものを誤検知しないか
    clean = not compare("test", base, base)
    print("    [%s] 同じ本文を誤検知しない" % ("OK " if clean else "NG "))
    ok = ok and clean
    print()
    if ok:
        print("  自己診断OK。この道具の結果は信用して大丈夫です。\n")
        return 0
    print("  自己診断に失敗しました。結果を信用しないでください。\n")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Notion②とサイトのHTMLがズレていないか調べる")
    sub = ap.add_subparsers(dest="cmd")

    p1 = sub.add_parser("prepare", help="HTMLから「正しい本文」を作る(ローカルだけ)")
    p1.add_argument("--slug")
    p1.set_defaults(func=cmd_prepare)

    p2 = sub.add_parser("check", help="Notionの本文と突き合わせる")
    p2.add_argument("--slug")
    p2.set_defaults(func=cmd_check)

    p3 = sub.add_parser("missing", help="②に登録されていない記事を出す")
    p3.add_argument("--registered", help="登録済みスラッグを並べたテキスト")
    p3.set_defaults(func=cmd_missing)

    p4 = sub.add_parser("selftest", help="この道具自体が壊れていないか試す")
    p4.set_defaults(func=lambda a: selftest())

    args = ap.parse_args()
    if not args.cmd:
        ap.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
