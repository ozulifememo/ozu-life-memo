# -*- coding: utf-8 -*-
"""点検台帳。どの記事を、いつ、誰が、どのレベルで確認したかを記録する。

なぜ作ったか(2026-08-29):
本人から「何回どのレベルでチェックしたか覚えていて、また聞かれたら
『もう確認したよ』と答えてほしい」と言われた。**これを記憶でやってはいけない。**
記憶は会話をまたぐと薄れるし、薄れたことに本人も気づけない。ファイルにする。

この台帳の肝は「確認したかどうか」ではなく **「確認したあとに本文が変わって
いないか」** を見ているところ。確認済みの記事を書き直したら、その確認は
無効になる。人はそれを忘れる。だから本文のハッシュを一緒に記録して、
変わっていたら「確認済み(ただしその後に本文が変わった)」と出す。

レベルの意味:
  machine … check_site.py の機械点検(構造・匿名性・文体・表現など)
  numbers … check_numbers.py の数字と出典の照合
  human   … 人かAIが本文と出典を実際に読んで裏取りした(一番重い)
  publish … 公開した

使い方:
  python tools/ledger.py show                     # 全体の状況
  python tools/ledger.py show ozu-shakyo-kessan   # 1記事の履歴
  python tools/ledger.py stale                    # 確認後に本文が変わった記事
  python tools/ledger.py todo                     # 一度も確認していない記事
  python tools/ledger.py record <slug> --level human --by opus --note "..."
  python tools/ledger.py import-numbers 結果.json  # 数字照合の結果を取り込む
  python tools/ledger.py import-site              # 機械点検を走らせて全記事に記録
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_site as cs                                    # noqa: E402

LEDGER = Path(__file__).resolve().parent / "check-ledger.json"

LEVELS = {
    "machine": "機械点検",
    "numbers": "数字と出典の照合",
    "human":   "人が読んで裏取り",
    "publish": "公開",
}


# ---------------------------------------------------------------------------
# 台帳の読み書き
# ---------------------------------------------------------------------------

def load() -> dict:
    if LEDGER.exists():
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    return {"articles": {}}


def save(data: dict) -> None:
    # slugの順に並べておく。差分が読みやすくなる
    data["articles"] = dict(sorted(data["articles"].items()))
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")


def body_hash(path: Path) -> str:
    """記事の中身のハッシュ。見せ方だけの変化では変わらないようにする"""
    body = cs.body_only(cs.read(path))
    # 読了時間は tools/add_readtime.py が自動で書き換えるので中身の変化と見なさない
    body = re.sub(r'<[^>]*class="[^"]*article-readtime[^"]*"[^>]*>.*?</[^>]+>', " ",
                  body, flags=re.S)
    text = re.sub(r"\s+", "", cs.strip_tags(body))
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def all_articles() -> dict:
    return {p.stem: p for p in cs.collect_pages()
            if cs.page_type(p) in ("article", "kenkyu", "book")}


def add_check(data, slug, path, level, by, result, note=None,
              when=None, hash_=..., ):
    """確認を1件記録する。

    when   … 記録する日付(省略すると今日)
    hash_  … 確認したときの本文のハッシュ。省略すると「いまの本文」を使う。
             None を渡すと「確認時の本文は不明」という意味になる(過去の記録の
             取り込み用)。不明のものは、あとで有効とも無効とも判定しない。
    """
    art = data["articles"].setdefault(slug, {"path": cs.rel(path), "checks": []})
    art["path"] = cs.rel(path)
    entry = {
        "date": when or date.today().isoformat(),
        "level": level,
        "by": by,
        "result": result,
        "hash": body_hash(path) if hash_ is ... else hash_,
    }
    if note:
        entry["note"] = note

    # 同じ日・同じレベル・同じ道具の記録は上書きする(台帳が膨らむのを防ぐ)
    art["checks"] = [c for c in art["checks"]
                     if not (c["date"] == entry["date"] and c["level"] == level
                             and c["by"] == by)]
    art["checks"].append(entry)
    art["checks"].sort(key=lambda c: (c["date"], c["level"]))
    return entry


# ---------------------------------------------------------------------------
# 表示
# ---------------------------------------------------------------------------

def status_of(art, path):
    """いまの本文と、記録された確認とのズレを返す。

    fresh   … 確認したときの本文が、いまの本文と同じ(確認は有効)
    stale   … 確認したあとに本文が変わった(確認はもう無効)
    unknown … 確認時の本文が記録されていない(過去のNotionからの取り込みなど)
    """
    now = body_hash(path)
    levels = {}
    for c in art["checks"]:
        levels.setdefault(c["level"], []).append(c)
    fresh, stale, unknown = [], [], []
    for level, items in levels.items():
        newest = max(items, key=lambda c: c["date"])
        h = newest.get("hash")
        if h is None:
            unknown.append((level, newest))
        elif h == now:
            fresh.append((level, newest))
        else:
            stale.append((level, newest))
    return now, fresh, stale, unknown


def cmd_show(args):
    data = load()
    arts = all_articles()

    if args.slug:
        if args.slug not in arts:
            print(f"「{args.slug}」という記事はありません")
            return 1
        path = arts[args.slug]
        art = data["articles"].get(args.slug)
        print(f"\n  {args.slug}  ({cs.rel(path)})")
        if not art or not art["checks"]:
            print("\n  記録はまだありません。一度も確認していない扱いです。\n")
            return 0
        now, fresh, stale, unknown = status_of(art, path)
        print(f"  いまの本文: {now}")
        print(f"  確認の記録: {len(art['checks'])}回\n")
        for c in art["checks"]:
            mark = "?" if c.get("hash") is None else ("○" if c["hash"] == now else "×")
            line = (f"    {mark} {c['date']}  {LEVELS.get(c['level'], c['level']):<18s}"
                    f" {c['by']:<18s} {c['result']}")
            print(line)
            if c.get("note"):
                print(f"        メモ: {c['note']}")
        print()
        if stale:
            names = "、".join(LEVELS.get(l, l) for l, _ in stale)
            print(f"  注意: {names} は、確認したあとに本文が変わっています。")
            print("        この確認はもう有効ではありません。")
        if unknown:
            names = "、".join(LEVELS.get(l, l) for l, _ in unknown)
            print(f"  注意: {names} は、確認したときの本文が記録されていません。")
            print("        いまの本文に対して有効かどうかは判定できません。")
        if not stale and not unknown:
            print("  すべての確認が、いまの本文に対して有効です。")
        print()
        return 0

    # 全体サマリ
    counts = {k: 0 for k in LEVELS}
    unknown_counts = {k: 0 for k in LEVELS}
    stale_n = 0
    none_n = 0
    for slug, path in arts.items():
        art = data["articles"].get(slug)
        if not art or not art["checks"]:
            none_n += 1
            continue
        _, fresh, stale, unknown = status_of(art, path)
        for level, _ in fresh:
            counts[level] = counts.get(level, 0) + 1
        for level, _ in unknown:
            unknown_counts[level] = unknown_counts.get(level, 0) + 1
        if stale:
            stale_n += 1

    print(f"\n  記事 {len(arts)}本 の点検状況\n")
    print("                        いまの本文に対して   確認時の本文が")
    print("                        有効な確認あり       不明")
    for k, label in LEVELS.items():
        print(f"    {label:<18s} {counts.get(k, 0):5d}本         "
              f"{unknown_counts.get(k, 0):4d}本")
    print()
    print(f"    一度も記録が無い              {none_n:3d}本   (ledger.py todo)")
    print(f"    確認後に本文が変わった        {stale_n:3d}本   (ledger.py stale)")
    print()
    return 0


def cmd_stale(args):
    data = load()
    arts = all_articles()
    rows = []
    for slug, path in arts.items():
        art = data["articles"].get(slug)
        if not art or not art["checks"]:
            continue
        _, fresh, stale, _u = status_of(art, path)
        for level, c in stale:
            rows.append((slug, level, c["date"], c["by"]))
    if not rows:
        print("\n  確認後に本文が変わった記事はありません。\n")
        return 0
    print(f"\n  確認したあとに本文が変わった記事 {len(rows)}件")
    print("  (この確認はもう有効ではないので、確認し直しが要ります)\n")
    for slug, level, d, by in sorted(rows):
        print(f"    {slug:<42s} {LEVELS.get(level, level):<18s} {d} {by}")
    print()
    return 0


def cmd_todo(args):
    data = load()
    arts = all_articles()
    level = args.level
    rows = []
    for slug, path in sorted(arts.items()):
        art = data["articles"].get(slug)
        if not art:
            rows.append(slug)
            continue
        _, fresh, _s, _u = status_of(art, path)
        if level not in [l for l, _ in fresh]:
            rows.append(slug)
    print(f"\n  「{LEVELS.get(level, level)}」の有効な記録が無い記事 {len(rows)}本\n")
    for slug in rows:
        print(f"    {slug}")
    print()
    return 0


# ---------------------------------------------------------------------------
# 記録する
# ---------------------------------------------------------------------------

def cmd_record(args):
    data = load()
    arts = all_articles()
    if args.slug not in arts:
        print(f"「{args.slug}」という記事はありません")
        return 1
    e = add_check(data, args.slug, arts[args.slug], args.level, args.by,
                  args.result or LEVELS.get(args.level, args.level), args.note)
    save(data)
    print(f"  記録しました: {args.slug}  {e['date']}  "
          f"{LEVELS.get(args.level, args.level)}  {args.by}")
    return 0


def cmd_import_numbers(args):
    data = load()
    arts = all_articles()
    results = json.loads(Path(args.file).read_text(encoding="utf-8"))
    n = 0
    for r in results:
        slug = Path(r["path"]).stem
        if slug not in arts:
            continue
        if r.get("no_source_text"):
            result = f"照合できず(出典の本文が取れなかった。出典{r['sources']}本)"
        else:
            result = (f"数字{r['numbers']}個中 {len(r['missing'])}個が出典に見つからず"
                      f"(出典{r['fetched']}/{r['sources']}本)")
        note = None
        if r["missing"]:
            note = "要確認: " + "、".join(m["raw"] for m in r["missing"][:6])
        add_check(data, slug, arts[slug], "numbers", "check_numbers.py", result, note)
        n += 1
    save(data)
    print(f"  {n}本ぶんの数字照合を台帳に取り込みました")
    return 0


def cmd_import_notion(args):
    """Notionの「ガチ完了」「内容ダブルチェック済み」「本人確認OK」を取り込む。

    渡すJSONは、Notionの③記事一覧に対して
      SELECT スラッグ AS slug, ガチ完了 AS gachi, 内容ダブルチェック済み AS dbl,
             本人確認OK AS honnin, 本人評価 AS hyoka, 公開日 AS pub
    を実行した結果。**過去の確認なので、確認時の本文は不明として記録する。**
    """
    data = load()
    arts = all_articles()
    rows = json.loads(Path(args.file).read_text(encoding="utf-8"))
    if isinstance(rows, dict):
        rows = rows.get("results", [])

    n, miss = 0, []
    for r in rows:
        slug = (r.get("slug") or "").strip()
        if slug not in arts:
            miss.append(slug)
            continue
        when = (r.get("pub") or "")[:10] or None
        marks = []
        if r.get("gachi") == "__YES__":
            marks.append("ガチ完了")
        if r.get("dbl") == "__YES__":
            marks.append("内容ダブルチェック済み")
        if r.get("honnin") == "__YES__":
            marks.append("本人確認OK")
        if not marks:
            continue
        note = "Notionのチェック欄から取り込み。確認したときの本文は記録されていない"
        if r.get("hyoka"):
            note += f" / 本人評価: {r['hyoka']}"
        add_check(data, slug, arts[slug], "human", "notion:" + "+".join(marks),
                  "・".join(marks), note, when=when, hash_=None)
        n += 1
    save(data)
    print(f"  {n}本ぶんの人による確認を台帳に取り込みました")
    if miss:
        print(f"  サイトに無いスラッグ {len(miss)}件: {'、'.join(x for x in miss if x)}")
    return 0


def cmd_import_site(args):
    """check_site.py を走らせて、その結果を全記事に記録する"""
    out = Path(__file__).resolve().parent / "_site_result.json"
    subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "check_site.py"),
                    "--json", str(out)],
                   cwd=str(cs.REPO), capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
    if not out.exists():
        print("  check_site.py の結果が取れませんでした")
        return 1
    site = json.loads(out.read_text(encoding="utf-8"))
    out.unlink(missing_ok=True)

    bad = {}
    for it in site.get("errors", []) + site.get("warnings", []):
        bad.setdefault(it["path"], []).append(f"{it['kind']}:{it['message']}")

    data = load()
    arts = all_articles()
    for slug, path in arts.items():
        rel = cs.rel(path)
        problems = bad.get(rel)
        result = "問題なし" if not problems else "／".join(problems[:3])
        add_check(data, slug, path, "machine", "check_site.py", result)
    save(data)
    print(f"  {len(arts)}本ぶんの機械点検を台帳に取り込みました"
          f"(問題あり {len(bad)}本)")
    return 0


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="点検台帳")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("show", help="状況を見る")
    p.add_argument("slug", nargs="?")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("stale", help="確認後に本文が変わった記事")
    p.set_defaults(func=cmd_stale)

    p = sub.add_parser("todo", help="そのレベルの確認がまだの記事")
    p.add_argument("--level", default="human", choices=list(LEVELS))
    p.set_defaults(func=cmd_todo)

    p = sub.add_parser("record", help="確認したことを記録する")
    p.add_argument("slug")
    p.add_argument("--level", required=True, choices=list(LEVELS))
    p.add_argument("--by", required=True, help="誰が(opus / fable / harada など)")
    p.add_argument("--result", help="結果の要約")
    p.add_argument("--note", help="メモ")
    p.set_defaults(func=cmd_record)

    p = sub.add_parser("import-numbers", help="数字照合の結果を取り込む")
    p.add_argument("file")
    p.set_defaults(func=cmd_import_numbers)

    p = sub.add_parser("import-notion", help="Notionのチェック欄を取り込む")
    p.add_argument("file")
    p.set_defaults(func=cmd_import_notion)

    p = sub.add_parser("import-site", help="機械点検を走らせて記録する")
    p.set_defaults(func=cmd_import_site)

    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
