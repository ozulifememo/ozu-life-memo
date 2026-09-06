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

## 安上がりに「Notionが古いかどうか」だけ見る方法

本文を丸ごと取ってくると1本1万字を超えるので、ズレの有無だけ知りたいときは
これが速い。**中身を1文字も変えずに確かめられる。**

  notion-update-page の update_content で、
  **old_str と new_str に同じ文字列を入れる**(置き換えても何も変わらない)。

    成功                    … その文字列がある = Notionは最新
    No matches found と出る … 無い = Notionが古い

サイト側の最新版にだけ出てくる特徴的な一節(新しく足した数字など)を
old_str にすると、そのまま「同期できているか」の判定になる。
2026-09-05に20本を突き合わせたとき、この方法で4本が既に最新だと分かった。

## 何を見るか

  ずれ    … 行単位の差分(本文が違う)
  化け    … **サイト219本のどこにも出てこない文字**(冄・熀・戰・繀 のような字)
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
    """出典calloutを除いた本文

    calloutは末尾にあるとは限らない。Notionの古いページは**先頭**に置いている
    ことがある(2026-09-05に実測。61本中かなりの数がそうだった)。
    最初は `split("<callout")[0]` にしていたので、先頭型のページは本文が空と
    判定され、「数字0個」「末尾が違う」という嘘の差分が大量に出た。
    どこにあっても取り除く。
    """
    out = re.sub(r"<callout\b.*?</callout>", "", md, flags=re.S)
    # 閉じタグが無い書き方(末尾で切れている等)にも一応備える
    out = re.sub(r"<callout\b.*$", "", out, flags=re.S)
    return out.strip()


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


_SITE_CHARS = None


def site_charset() -> set:
    """サイトの記事219本で実際に使われている文字の全体集合(1度だけ作る)"""
    global _SITE_CHARS
    if _SITE_CHARS is None:
        cs = set()
        for d in ("eachnews", "jiyu-kenkyu", "book"):
            for f in (REPO / d).glob("*.html"):
                cs |= set(re.sub(r"<[^>]+>", "", f.read_text(encoding="utf-8", errors="replace")))
        _SITE_CHARS = cs
    return _SITE_CHARS


def strip_tags_rough(s: str) -> str:
    """Notion側の書式タグ(<empty-block/> など)を落とす"""
    return re.sub(r"<[^>]+>", "", s)


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

    # 2. 化け
    #
    # 最初は「その記事の正しい本文に無い文字」を全部疑っていたが、それだと
    # Notion特有のタグ(<empty-block/>など)のASCIIや、単に版が違うだけの
    # 普通の漢字まで拾ってしまい、61本で45件の大半が誤検知だった(2026-09-05)。
    #
    # いまは **サイト219本のどこにも出てこない文字** だけを疑う。
    # 日本語の記事に一度も現れない字が入っていたら、まず書き込み時の化けである。
    # この方式に変えたら、61本から本物の11か所(沖縄→沖繀、高知→高睑、炉→瀉など)
    # だけが残った。
    extra = sorted({c for c in strip_tags_rough(gb)
                    if c not in site_charset() and not c.isspace()})
    if extra:
        ng.append(("化け", "サイトのどこにも無い文字が入っています: %s" % " ".join(extra),
                   "       書き込み時の化けです。見た目が近い別の字に変わっています"))

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


_SITE_COUNT = None


def site_charcount():
    """サイトの記事で、その字が何回使われているかの表(1度だけ作る)"""
    global _SITE_COUNT
    if _SITE_COUNT is None:
        import collections
        c = collections.Counter()
        for d in ("eachnews", "jiyu-kenkyu", "book"):
            for f in (REPO / d).glob("*.html"):
                c.update(re.sub(r"<[^>]+>", "",
                                f.read_text(encoding="utf-8", errors="replace")))
        _SITE_COUNT = c
    return _SITE_COUNT


# サイトでこれ以下しか出てこない字を「珍しい」とみなす
RARE = 8
# 化ける前の字はよく使う字のはず。これ以上出てくる字だけを候補にする
COMMON = 20


def hex_neighbors(ch: str) -> list:
    """その字とコードポイントが16進1桁だけ違う字を並べる"""
    n = ord(ch)
    if n > 0xFFFF:
        return []
    out = []
    for pos in range(4):
        shift = pos * 4
        cur = (n >> shift) & 0xF
        for d in range(16):
            if d == cur:
                continue
            m = (n & ~(0xF << shift)) | (d << shift)
            if 0x3000 <= m <= 0x9FFF or 0xFF00 <= m <= 0xFFEF:
                out.append(chr(m))
    return out


def hex_neighbor_suspects(text: str) -> list:
    """「16進を1桁書き間違えた」形の化けを探す。

    サイトに一度も出てこない字を探す方法には穴がある。化けた先が
    サイトでも使う字だと素通りしてしまう。2026-09-05、四国新幹線の記事の
    メモ欄で「綱引き」が「綿引き」になっていた例がそれで、綿はサイトに
    1回だけ出てくるので見つからなかった(綱 U+7DB1 / 綿 U+7DBF)。

    そこで、珍しい字を見つけたら、コードポイントが16進1桁だけ違う字を
    総当たりし、その中にサイトでよく使う字があれば候補として挙げる。
    これは「疑わしい」であって「化けている」ではない。人が読んで決める。
    """
    cnt = site_charcount()
    out = []
    for m in re.finditer(r"[぀-鿿]", text):
        ch = m.group()
        c = cnt.get(ch, 0)
        if c > RARE:
            continue
        for nb in hex_neighbors(ch):
            k = cnt.get(nb, 0)
            if k >= COMMON and k >= max(10 * c, 10):
                j = m.start()
                out.append((ch, c, nb, k,
                            re.sub(r"\s+", " ", text[max(0, j - 20):j + 20])))
                break
    return out


def cmd_props(args) -> int:
    """Notionの「プロパティ欄」の化けを探す

    本文だけ見ていると見つからない化けが実際にあった(2026-09-05、
    クロコ裏取りメモの中で「喜茂別町」が「喊茅別町」になっていた)。
    メモ欄は誰も読み返さないので、化けたまま何か月も残る。

    入力は JSON の配列。1件は {"slug":..., "field":..., "text":...}。
    判定はこの道具の本文点検と同じ「サイト219本のどこにも出てこない文字」。
    """
    import json as _json
    rows = _json.loads(Path(args.file).read_text(encoding="utf-8"))
    cs = site_charset()
    hit = 0
    for r in rows:
        t = r.get("text") or ""
        for m in re.finditer(r"[^\s]", t):
            c = m.group()
            if c in cs:
                continue
            j = m.start()
            print("%s / %s : %r  … %s" % (
                r.get("slug"), r.get("field"), c,
                re.sub(r"\s+", " ", t[max(0, j - 25):j + 25])))
            hit += 1
    print("---")
    print("%d件を点検 / サイトに無い文字 %d個" % (len(rows), hit))

    # 「化けた先もサイトで使う字」の型。これは疑いであって断定ではない
    print()
    print("[参考] コードポイントが16進1桁違いで、よく使う字に化けている疑い")
    print("       (珍しい字が挙がるだけのこともある。読んで判断すること)")
    n2 = 0
    seen = set()
    for r in rows:
        for ch, c, nb, k, ctx in hex_neighbor_suspects(r.get("text") or ""):
            key = (r.get("slug"), ch, ctx)
            if key in seen:
                continue
            seen.add(key)
            print("  %s / %s : %s(%d回) → %s(%d回) かも … %s"
                  % (r.get("slug"), r.get("field"), ch, c, nb, k, ctx))
            n2 += 1
    print("  疑い %d個" % n2)
    return 1 if hit else 0


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
        # 「化け」は、サイトのどこにも出てこない字でないと検知できない。
        # 「牲」のような普通の字はサイトのどこかで使われているので不可。
        # 実際に起きた化け(沖縄→沖繀)を、そのままテストに使う。
        ("化け", base.replace("総務92人", "総繀92人")),
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

    # calloutが先頭にあるNotionページを、誤検知しないか。
    # 2026-09-05、ここを見落として61本ぶんの嘘の差分を出した。
    head, tail = base.split("<callout", 1)
    flipped = "<callout" + tail + "\n" + head.rstrip()
    same = not compare("test", base, flipped)
    print("    [%s] 出典calloutが先頭にあっても誤検知しない" % ("OK " if same else "NG "))
    ok = ok and same

    # プロパティ欄の点検。本文がきれいでもメモ欄が化けていた実例がある
    # (2026-09-05、クロコ裏取りメモの「喜茂別町」→「喊茅別町」)。
    import tempfile
    import json as _j
    import argparse as _a
    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8",
                                     delete=False) as fh:
        _j.dump([{"slug": "t", "field": "メモ", "text": "全国の良い事例(真庭市・喊茅別町)"},
                 {"slug": "t", "field": "メモ", "text": "全国の良い事例(真庭市・喜茂別町)"}],
                fh, ensure_ascii=False)
        tmp = fh.name
    buf, sys.stdout = sys.stdout, io.StringIO()
    try:
        rc = cmd_props(_a.Namespace(file=tmp))
        out = sys.stdout.getvalue()
    finally:
        sys.stdout = buf
        Path(tmp).unlink(missing_ok=True)
    # 化けた側だけが出て、正しい側は出ないこと
    pgood = rc == 1 and "喊" in out and "喜茂別" not in out
    print("    [%s] プロパティ欄の化けを検知し、正しい方は誤検知しない"
          % ("OK " if pgood else "NG "))
    ok = ok and pgood

    # 「化けた先もサイトで使う字だった」型。字の珍しさだけでは見つからない。
    # 2026-09-05、綱引き→綿引き(綱 U+7DB1 / 綿 U+7DBF)がこれで、綿はサイトに
    # 1回出てくるので素通りしていた。16進1桁違いの総当たりで捕まえる。
    hits = [h[0] for h in hex_neighbor_suspects("規格の綿引きと維持費")]
    clean2 = hex_neighbor_suspects("規格の綱引きと維持費")
    ngood = "綿" in hits and not clean2
    print("    [%s] 16進1桁違いの化けを見つけ、正しい方は挙げない"
          % ("OK " if ngood else "NG "))
    ok = ok and ngood

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

    p5 = sub.add_parser("props", help="Notionのプロパティ欄(メモなど)の化けを探す")
    p5.add_argument("file", help="[{slug,field,text},...] のJSON")
    p5.set_defaults(func=cmd_props)

    p4 = sub.add_parser("selftest", help="この道具自体が壊れていないか試す")
    p4.set_defaults(func=lambda a: selftest())

    args = ap.parse_args()
    if not args.cmd:
        ap.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
