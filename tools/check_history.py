# -*- coding: utf-8 -*-
"""git の履歴に、個人が特定できる語が残っていないかを見る。

なぜ要るか(2026-09-06)。
check_site.py の匿名性の検査は「いま追跡しているファイル」しか見ない。
だが GitHub はリポジトリが Public なら履歴も公開する。過去にコミットして
あとで消した記事も、消す前の版も、コミットメッセージも、いまも誰でも読める。

実際にこの日、履歴に次の2つが残っていることが分かった。

  - 旧アカウント名の入ったURL（記事の og:url に35本ぶん）
  - 運営者の名字（台帳・道具・月間まとめのページなど11版）

どちらも当時その場では直してあり、いまのファイルには1件も無い。
残っているのは履歴だけである。だから「いまを見る検査」では永久に見つからない。

使い方:

    python tools/check_history.py          # 全部見る
    python tools/check_history.py --quick  # コミットメッセージと直近だけ

禁止語は private-notes/banned-words.py（gitignore済み）から読む。
"""
import argparse
import io
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent.parent
SKIP_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".pdf", ".woff",
            ".woff2", ".ttf", ".xlsx", ".zip", ".svg")


def load_words():
    ns = {}
    src = REPO / "private-notes" / "banned-words.py"
    if not src.exists():
        print("  private-notes/banned-words.py が無いので、検査できません。")
        sys.exit(2)
    exec(compile(io.open(src, encoding="utf-8").read(), str(src), "exec"), ns)
    return ns.get("BANNED", []), ns.get("ALLOW", [])


def run(args):
    return subprocess.run(args, cwd=str(REPO), capture_output=True,
                          encoding="utf-8", errors="replace").stdout or ""


def scan(text, banned, allow):
    """当たった語を (語, 理由, 前後) で返す。1パターン1件でよい。"""
    out = []
    for pattern, why in banned:
        for m in re.finditer(pattern, text):
            around = text[max(0, m.start() - 45): m.end() + 45]
            if any(a in around for a in allow):
                continue
            out.append((m.group(0), why, " ".join(around.split())))
            break
    return out


def main():
    ap = argparse.ArgumentParser(description="git の履歴の匿名性を見る")
    ap.add_argument("--quick", action="store_true",
                    help="コミットメッセージと、いま追跡しているファイルだけ")
    args = ap.parse_args()

    banned, allow = load_words()
    print("=" * 70)
    print("  git の履歴の匿名性")
    print("  禁止パターン %d 個 / 見逃し語 %d 個" % (len(banned), len(allow)))
    print("=" * 70)

    by_word = Counter()
    by_file = defaultdict(set)
    samples = {}

    # 1. コミットメッセージ
    msgs = run(["git", "log", "--all", "--format=%H%x01%s%x02%b%x03"])
    n_commit = 0
    for blob in msgs.split("\x03"):
        if not blob.strip():
            continue
        n_commit += 1
        h, rest = blob.split("\x01", 1) if "\x01" in blob else ("?", blob)
        for word, why, around in scan(rest, banned, allow):
            by_word[(word, why)] += 1
            by_file["(コミットメッセージ)"].add(h.strip()[:8])
            samples.setdefault((word, why), around)
    print("\n  コミットメッセージ %d 個を見ました" % n_commit)

    # 2. ブランチ・タグ
    for word, why, around in scan(run(["git", "branch", "-a"]) + run(["git", "tag"]),
                                  banned, allow):
        by_word[(word, why)] += 1
        by_file["(ブランチ・タグ名)"].add("-")
        samples.setdefault((word, why), around)

    # 3. 履歴に入っている全ファイルの全版
    if not args.quick:
        objs = run(["git", "rev-list", "--objects", "--all"])
        seen = set()
        n_obj = 0
        for line in objs.split("\n"):
            parts = line.split(" ", 1)
            if len(parts) != 2:
                continue
            sha, name = parts[0], parts[1].strip()
            if not name or name.lower().endswith(SKIP_EXT) or sha in seen:
                continue
            seen.add(sha)
            body = run(["git", "cat-file", "-p", sha])
            if not body:
                continue
            n_obj += 1
            for word, why, around in scan(body, banned, allow):
                by_word[(word, why)] += 1
                by_file[name].add(sha[:8])
                samples.setdefault((word, why), around)
        print("  履歴に入っているファイル %d 版を見ました" % n_obj)

    print()
    print("-" * 70)
    if not by_word:
        print("  履歴に、個人が特定できる語は見つかりませんでした。")
        print("-" * 70)
        return 0

    print("  ★ 見つかりました")
    print("-" * 70)
    print("\n  どの語が、いくつの版に残っているか")
    for (word, why), n in by_word.most_common():
        print("    %-24s %4d 版   (%s)" % (word, n, why))
        print("        例: …%s…" % samples[(word, why)][:110])

    print("\n  どこに残っているか  (%d か所 / %d 版)"
          % (len(by_file), sum(len(v) for v in by_file.values())))
    for name, shas in sorted(by_file.items(), key=lambda x: -len(x[1]))[:25]:
        print("    %-52s %3d 版" % (name[:52], len(shas)))
    if len(by_file) > 25:
        print("    ... ほか %d か所" % (len(by_file) - 25))

    print()
    print("-" * 70)
    print("  いまのファイルを直しても、履歴は消えません。")
    print("  リポジトリが Public なら、履歴も誰でも読めます。")
    print("  消すには履歴を書き換える必要があり、これは本人の判断が要ります。")
    print("-" * 70)
    return 1


if __name__ == "__main__":
    sys.exit(main())
