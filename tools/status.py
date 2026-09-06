#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OZU LIFE MEMO 現在地スクリプト
================================

「いま何が残っているんだっけ」を、記憶ではなく実物から数え直して1画面に出します。
ファイルは一切書き換えません(読むだけ)。何度でも走らせて大丈夫です。

    python tools/status.py           ふつうに見る(点検も走るので10秒ほど)
    python tools/status.py --quick   点検を省いて即出す
    python tools/status.py --json    JSONで出す

【なぜこれがあるか】
チャットを何本も並行して走らせていると、「どこまで進んだか」が人とクロコで
ずれます。ずれる原因は、進捗が『誰かが書いたメモ』にしか無いからです。
メモは書いた瞬間から古くなります。

だからこのスクリプトは、数えられるものは毎回その場で数え直します。
数えられないもの(Notionの下書き本数など)だけ tools/status-state.json に
「値」と「いつ確認したか」の形で置き、古くなったら ? を付けて知らせます。

CLAUDE.md の「ルールは文章ではなく機械に置く」と同じ考え方の、進捗版です。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
TOOLS = REPO / "tools"
STATE = TOOLS / "status-state.json"

sys.path.insert(0, str(TOOLS))
import check_site as cs            # noqa: E402
import ledger as lg                # noqa: E402

TODAY = date.today()


# ---------------------------------------------------------------------------
# 小道具
# ---------------------------------------------------------------------------

def days_since(d: str | None) -> int | None:
    """YYYY-MM-DD から今日までの日数。読めなければ None"""
    if not d:
        return None
    try:
        return (TODAY - datetime.strptime(d[:10], "%Y-%m-%d").date()).days
    except ValueError:
        return None


def days_until(d: str | None) -> int | None:
    n = days_since(d)
    return None if n is None else -n


def ago(d: str | None) -> str:
    """「2026-08-31(2日前)」の形にする"""
    n = days_since(d)
    if n is None:
        return str(d or "不明")
    if n == 0:
        return f"{d}(今日)"
    if n == 1:
        return f"{d}(昨日)"
    return f"{d}({n}日前)"


def git(*args: str) -> str:
    try:
        r = subprocess.run(["git", *args], cwd=str(REPO), capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=30)
        return r.stdout.strip()
    except Exception:
        return ""


def js_text(name: str) -> str:
    p = REPO / "assets" / "js" / name
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


def block(text: str, start_marker: str) -> str:
    """const XXX = { ... }; の中身をざっくり切り出す(かっこの深さで数える)"""
    i = text.find(start_marker)
    if i < 0:
        return ""
    i += len(start_marker)
    depth, out = 1, []
    for ch in text[i:]:
        if ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
            if depth == 0:
                break
        out.append(ch)
    return "".join(out)


def strip_comments(s: str) -> str:
    return "\n".join(ln for ln in s.splitlines() if not ln.strip().startswith("//"))


# ---------------------------------------------------------------------------
# 数える
# ---------------------------------------------------------------------------

def count_site_check(quick: bool) -> dict:
    """check_site.py を走らせてエラー・警告の数をもらう"""
    if quick:
        return {"skipped": True}
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "chk.json"
        try:
            subprocess.run([sys.executable, str(TOOLS / "check_site.py"), "--json", str(out)],
                           cwd=str(REPO), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=600)
            d = json.loads(out.read_text(encoding="utf-8"))
        except Exception as e:
            return {"skipped": True, "失敗": str(e)}
    return {
        "skipped": False,
        "ページ数": d.get("pages_checked", 0),
        "エラー": len(d.get("errors", [])),
        "警告": len(d.get("warnings", [])),
    }


def count_ledger() -> dict:
    """点検台帳から、確認の効き具合を段階ごとに数える

    有効   … 確認したときの本文が、いまの本文と同じ(その確認はいまも効いている)
    失効   … 確認したあとに本文が変わった(確認し直しが要る)
    本文不明 … 記録はあるが、確認時の本文が残っていない(Notionからの取り込みなど)
    なし   … 一度も記録がない
    """
    data = lg.load()
    arts = lg.all_articles()
    levels = ("machine", "numbers", "human")
    out = {lv: {"有効": 0, "本文不明": 0, "なし": 0} for lv in levels}
    stale = 0
    for slug, path in arts.items():
        art = data["articles"].get(slug)
        if not art or not art["checks"]:
            for lv in levels:
                out[lv]["なし"] += 1
            continue
        _, fresh, st, unknown = lg.status_of(art, path)
        stale += len(st)
        ok = {lv for lv, _ in fresh}
        unk = {lv for lv, _ in unknown}
        for lv in levels:
            if lv in ok:
                out[lv]["有効"] += 1
            elif lv in unk:
                out[lv]["本文不明"] += 1
            else:
                out[lv]["なし"] += 1
    return {"総数": len(arts), "失効": stale, "段階": out}


def count_promises() -> int:
    n = 0
    for p in cs.collect_pages():
        if cs.page_type(p) not in ("article", "book", "kenkyu"):
            continue
        text = cs.strip_tags(cs.body_only(cs.read(p)))
        for sent in text.split("。"):
            if any(ph in sent for ph in cs.PROMISE_PHRASES):
                n += 1
    return n


def count_git() -> dict:
    porcelain = git("status", "--porcelain")
    dirty = [ln for ln in porcelain.splitlines() if ln.strip()]

    # 中身が変わっていないものは数えない。
    # git は改行コード(CRLF/LF)の判定が変わっただけのファイルも
    # modified として並べる。2026-09-06、それが334件出て、
    # 実際の差分は0追加0削除だった。「未コミット334件」と出ると、
    # 次に見た人は別チャットが作業中だと思って手を止めてしまう。
    numstat = git("diff", "--numstat")
    changed = set()
    for ln in numstat.splitlines():
        cols = ln.split("\t")
        if len(cols) == 3 and (cols[0] != "0" or cols[1] != "0"):
            changed.add(cols[2])
    kept = []
    for ln in dirty:
        st, name = ln[:2], ln[3:].strip().strip('"')
        # 未追跡(??)と、ステージ済み(左側が空白でない)は、そのまま数える
        if st.startswith("??") or st[0] not in " ":
            kept.append(ln)
        elif name in changed:
            kept.append(ln)
    dirty = kept
    ahead = git("rev-list", "--count", "origin/main..HEAD")
    behind = git("rev-list", "--count", "HEAD..origin/main")
    last = git("log", "-1", "--format=%cs %s")
    return {
        "未コミット": len(dirty),
        "未push": int(ahead) if ahead.isdigit() else None,
        "未取り込み": int(behind) if behind.isdigit() else None,
        "最終コミット日": last[:10] if last else None,
        "最終コミット": last[11:] if len(last) > 11 else "",
    }


def count_articles() -> dict:
    """記事データと写真の紐づけを、JSファイルから直接数える"""
    news = js_text("news-data.js")
    imgs = js_text("article-images.js")

    slugs, dates = [], []
    import re
    for m in re.finditer(r'slug:\s*"([a-z0-9\-]+)"', news):
        slugs.append(m.group(1))
    for m in re.finditer(r'date:\s*"(\d{4}-\d{2}-\d{2})"', news):
        dates.append(m.group(1))

    body = strip_comments(block(imgs, "const OZU_ARTICLE_IMAGES = {"))
    have_photo = set(re.findall(r'"([a-z0-9\-]+)"\s*:', body))

    wanted_body = strip_comments(block(imgs, "const OZU_ARTICLE_PHOTO_WANTED = ["))
    in_theme = set(re.findall(r'"([a-z0-9\-]+)"', wanted_body))

    # 写真が要らないと決めた記事(数字と制度だけで被写体が無いもの)は、
    # 「テーマ未登録」に数えない。数えると毎回宿題に出続けてしまう。
    no_photo_body = strip_comments(block(imgs, "const OZU_ARTICLE_NO_PHOTO = {"))
    no_photo = set(re.findall(r'"([a-z0-9\-]+)"\s*:', no_photo_body))

    known = set(slugs)
    with_photo = len(have_photo & known)
    waiting = len([s for s in slugs if s not in have_photo and s in in_theme])
    orphan = len([s for s in slugs
                  if s not in have_photo and s not in in_theme and s not in no_photo])

    lib = js_text("photos-data.js")
    photos = len(re.findall(r"\{\s*file:", lib))

    月別 = {}
    for d in dates:
        月別[d[:7]] = 月別.get(d[:7], 0) + 1

    return {
        "本数": len(slugs),
        "最新": max(dates) if dates else None,
        "月別": 月別,
        "写真あり": with_photo,
        "写真待ち": waiting,
        "テーマ未登録": orphan,
        "手持ちの写真": photos,
    }


def count_monthly(月別記事数: dict) -> dict:
    """月間まとめの抜けを探す

    記事が1本も無い月は、まとめが無いのが正しい(2026-06がそれ)。
    「記事があるのにまとめが無い月」だけを抜けとして数える。
    """
    import re
    text = js_text("monthly-data.js")
    months = sorted(set(re.findall(r'month:\s*"(\d{4}-\d{2})"', text)))
    if not months:
        return {"最新": None, "抜け": []}
    gaps = sorted(ym for ym, n in 月別記事数.items()
                  if n > 0 and ym not in months and ym < TODAY.strftime("%Y-%m"))
    return {"最新": months[-1], "抜け": gaps}


def load_state() -> dict:
    if not STATE.exists():
        return {}
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# 表示
# ---------------------------------------------------------------------------

W = 68
WEEK = "月火水木金土日"


def vw(s: str) -> int:
    """画面上の見た目の幅(日本語は2つぶん)"""
    import unicodedata
    return sum(2 if unicodedata.east_asian_width(c) in "WFA" else 1 for c in s)


def pad(s: str, n: int) -> str:
    return s + " " * max(1, n - vw(s))


def head(title: str, note: str = "") -> None:
    print()
    print("─" * W)
    print(f" {title}" + (f"    {note}" if note else ""))
    print("─" * W)


def row(label: str, value: str, flag: str = " ") -> None:
    print(f"  {flag} {pad(label, 24)}{value}")


def render(s: dict) -> None:
    print()
    print("=" * W)
    print(f" OZU LIFE MEMO  いまの現在地      "
          f"{TODAY.isoformat()}({WEEK[TODAY.weekday()]}) {datetime.now():%H:%M}")
    print("=" * W)

    # --- サイトの健康 -----------------------------------------------------
    chk, led, g = s["点検"], s["台帳"], s["git"]
    bad = bool(chk.get("エラー")) or led["失効"] or g["未push"] or g["未コミット"]
    head("サイトの健康", "→ " + ("見るところがあります" if bad else "問題なし"))
    if chk.get("skipped"):
        row("点検", "省略しました(--quick)")
    else:
        row("点検", f"エラー {chk['エラー']} / 警告 {chk['警告']}   ({chk['ページ数']}ページ)",
            "!" if chk["エラー"] else " ")
    row("台帳", f"確認が無効になった記事 {led['失効']}本", "!" if led["失効"] else " ")
    row("未コミット", f"{g['未コミット']}件", "!" if g["未コミット"] else " ")
    row("未push", f"{g['未push']}件", "!" if g["未push"] else " ")
    row("最終コミット", ago(g["最終コミット日"]) + "  " + g["最終コミット"][:24])

    # --- 記事 -------------------------------------------------------------
    a, mon = s["記事"], s["月間まとめ"]
    head("記事", f"サイト{a['本数']}本 / 点検の対象は{led['総数']}本(自由研究・読書を含む)")
    row("最新の記事", ago(a["最新"]))
    row("写真", f"あり {a['写真あり']} / 撮影待ち {a['写真待ち']}"
        + (f" / テーマ未登録 {a['テーマ未登録']}" if a["テーマ未登録"] else "")
        + f"   (手持ち {a['手持ちの写真']}枚)",
        "!" if a["テーマ未登録"] else " ")
    if mon["抜け"]:
        row("月間まとめ", "抜けています: " + " ".join(mon["抜け"]), "!")
    else:
        row("月間まとめ", f"最新 {mon['最新']}")

    # --- 確認の効き具合 ---------------------------------------------------
    head("確認の効き具合", f"{led['総数']}本ぶん")
    for key, label in (("machine", "機械点検"), ("numbers", "数字と出典の照合"),
                       ("human", "人が読んで裏取り")):
        d = led["段階"][key]
        parts = [f"有効 {d['有効']}"]
        if d["本文不明"]:
            parts.append(f"本文不明 {d['本文不明']}")
        if d["なし"]:
            parts.append(f"記録なし {d['なし']}")
        row(label, " / ".join(parts), "!" if d["なし"] and key != "human" else " ")
    if led["段階"]["human"]["なし"]:
        print("      「人が読んで裏取り」は手作業なので、記録なしが多いのは普通です")

    # --- 宿題(機械が数えた) -----------------------------------------------
    head("宿題(機械が数えたもの)")
    row("追記の約束", f"{s['約束']}件"
        + "    → python tools/check_site.py --promises")

    # --- 宿題(手で置いたもの) ---------------------------------------------
    items = s["state"].get("手で数えるもの", [])
    if items:
        head("宿題(手で置いたもの)", "? = 情報が古い。数え直しが要ります")
        for it in items:
            n = days_since(it.get("確認日"))
            old = n is not None and n > int(it.get("有効日数", 7))
            note = it.get("メモ", "")
            row(it["名前"], pad(it["値"], 14) + (f"({n}日前に確認)" if n is not None else ""),
                "?" if old else " ")
            if note:
                print(f"      {note}")

    # --- 期限 -------------------------------------------------------------
    dues = s["state"].get("期限のあるもの", [])
    if dues:
        head("期限のあるもの")
        for d in sorted(dues, key=lambda x: x.get("見る日", "9999")):
            n = days_until(d.get("見る日"))
            when = "いま" if n is None else ("過ぎています" if n < 0 else f"あと{n}日")
            row(d["名前"], f"{d.get('見る日', '')}  {when}", "!" if (n is not None and n <= 0) else " ")
            print(f"      {d.get('すること', '')}")

    # --- 手をつけないと決めたもの -----------------------------------------
    holds = s["state"].get("手をつけないと決めたもの", [])
    if holds:
        head("手をつけないと決めたもの", "(言われるまで触らない)")
        for h in holds:
            row(h["名前"], h.get("決めた日", ""))

    # --- 作業の足跡 -------------------------------------------------------
    # 運営者が6〜7回、別々のタイミングで同じことを言っている。
    #   「会話が途中で終わっているか、不安になるときがある」
    # チャットの一覧を見ても、どれが終わってどれが途中かは分からない。
    # だが Stop フック(hook_check.py)が応答のたびに足跡を残しているので、
    # 「最後にいつ、何を触って、そのとき手が入ったままだったか」は分かる。
    ashi = REPO / "tools" / "ashiato.json"
    if ashi.exists():
        try:
            log = json.loads(ashi.read_text(encoding="utf-8"))
        except Exception:
            log = []
        if log:
            head("最近の作業", "(チャットごとの足跡。手を動かすたびに自動で残る)")
            # チャットごとに、いちばん新しい足跡だけを見る
            byses = {}
            for r in log:
                byses[r.get("どのチャット", "?")] = r
            recent = sorted(byses.values(), key=lambda r: r.get("いつ", ""), reverse=True)
            for r in recent[:5]:
                nokori = r.get("手が入ったままのファイル", 0)
                err = r.get("エラー", 0)
                mark = "!" if (nokori or err) else " "
                sid = r.get("どのチャット", "?")
                if nokori or err:
                    tail = []
                    if nokori:
                        tail.append(f"手が入ったまま{nokori}件")
                    if err:
                        tail.append(f"エラー{err}件")
                    note = "  ← " + "・".join(tail)
                else:
                    note = "  きれいに終わっている"
                row(f"{r.get('いつ','?')}  [{sid}]", note, mark)
                if nokori and r.get("その例"):
                    for f in r["その例"][:3]:
                        print(f"        {f}")
            print(f"\n    足跡は直近{len(log)}回ぶん tools/ashiato.json にあります")
            print("    「あのチャット、やり切ったっけ?」はここを見る")

    # --- 次の一手 ---------------------------------------------------------
    todo = suggest(s)
    if todo:
        head("今週やるならこの順")
        for i, t in enumerate(todo, 1):
            print(f"  {i}. {t}")
    print()


def suggest(s: dict) -> list[str]:
    """数字から機械的に組み立てる。思いつきではなく、上の数字の言い換え"""
    out = []
    chk, led, g, a = s["点検"], s["台帳"], s["git"], s["記事"]

    if not chk.get("skipped") and chk.get("エラー"):
        out.append(f"点検のエラー{chk['エラー']}件を直す(python tools/check_site.py)")
    if led["失効"]:
        out.append(f"確認が無効になった{led['失効']}本を確認し直す(python tools/ledger.py stale)")
    if g["未コミット"]:
        out.append(f"手が入ったままの{g['未コミット']}件を、コミットするか戻す")
    if g["未push"]:
        out.append(f"未pushの{g['未push']}件を push する(本人の確認が要る)")
    if led["段階"]["numbers"]["なし"]:
        out.append(f"数字照合の記録がない{led['段階']['numbers']['なし']}本を照合する"
                   "(python tools/check_numbers.py)")

    for it in s["state"].get("手で数えるもの", []):
        n = days_since(it.get("確認日"))
        if n is not None and n > int(it.get("有効日数", 7)):
            out.append(f"「{it['名前']}」を数え直す({it.get('調べ方', '')})")

    for d in s["state"].get("期限のあるもの", []):
        n = days_until(d.get("見る日"))
        if n is not None and n <= 0:
            out.append(f"{d['名前']}: {d.get('すること', '')}")

    if a["テーマ未登録"]:
        out.append(f"撮影テーマに入っていない{a['テーマ未登録']}本を、テーマに割り振る")

    n = days_since(a["最新"])
    if n is not None and n >= 14:
        out.append(f"記事が{n}日出ていない。Notionの下書きから1本出す")

    return out[:5]


# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="OZU LIFE MEMO 現在地スクリプト")
    ap.add_argument("--quick", action="store_true", help="点検を省いて速く出す")
    ap.add_argument("--json", action="store_true", help="JSONで出す")
    args = ap.parse_args()

    s = {
        "日付": TODAY.isoformat(),
        "点検": count_site_check(args.quick),
        "台帳": count_ledger(),
        "約束": count_promises(),
        "git": count_git(),
        "記事": count_articles(),
        "state": load_state(),
    }
    # 月間まとめの抜けは「記事があった月」だけを見る。記事0本の月は無くて正しい
    s["月間まとめ"] = count_monthly(s["記事"]["月別"])

    if args.json:
        s.pop("state", None)
        print(json.dumps(s, ensure_ascii=False, indent=2))
    else:
        render(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
