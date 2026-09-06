# -*- coding: utf-8 -*-
"""応答を終える前に、いま手を入れたページを自動で点検するためのフック。

Claude Code の Stop フックから呼ばれる。
「完了と言う前に点検スクリプトを走らせる」というルールは前から文章では
書いてあったが、走らせるかどうかがクロコ側の判断に委ねられていた。
このファイルは、その判断を仕組みに置き換えるためのもの。

終了コードの意味(Claude Code の決まり):
  0 … 問題なし。そのまま応答を終えてよい
  2 … 問題あり。標準エラーの内容がクロコに戻され、直すまで終われない
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def ashiato(problems: int, warns: int, payload: dict) -> None:
    """応答を終えるたびに、作業の足跡を tools/ashiato.json に残す。

    なぜ要るか。運営者が6〜7回、別々のタイミングで同じことを言っている。

        「会話が途中で終わっているか、不安になるときがある。
         やり切ってないことを確認したい」

    6〜7回言われたということは、記憶の問題ではなく、仕組みが無いということ。
    このプロジェクトには「一度言ったのに直っていない原因は、注意の回数ではなく、
    そのルールが機械に書かれているかどうかだった」という実測(2026-08-29)がある。

    チャットの一覧を見ても、どれが終わっていてどれが途中かは分からない。
    だが「最後にいつ、何を触って、そのとき手が入ったままだったか」は機械で残せる。
    フックは応答のたびに必ず動くので、ここに置くのがいちばん確実である。

    残すのは20件まで。増やしても読まないので、増やさない。
    """
    import datetime
    log = REPO / "tools" / "ashiato.json"
    # git status だと、Windowsの改行コードの噛み合わせで300件以上が
    # 「変更あり」に見える。中身は1文字も変わっていない。
    # だから --numstat で「本当に行が増減したファイル」だけを数える。
    dirty = []
    try:
        r = subprocess.run(["git", "-c", "core.safecrlf=false", "diff", "--numstat"],
                           cwd=str(REPO), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=20)
        for line in r.stdout.splitlines():
            c = line.split("	")
            if len(c) == 3 and (c[0] not in ("0", "-") or c[1] not in ("0", "-")):
                dirty.append(c[2])
        r = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"],
                           cwd=str(REPO), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=20)
        dirty += [l.strip() for l in r.stdout.splitlines() if l.strip()]
    except Exception:
        dirty = []
    try:
        r = subprocess.run(["git", "log", "-1", "--format=%h %s"], cwd=str(REPO),
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=20)
        last = r.stdout.strip()
    except Exception:
        last = ""

    # どのチャットかは session_id で分かる。頭8文字だけ残す(全部は要らない)
    sid = str(payload.get("session_id") or "")[:8] or "?"

    rec = {
        "いつ": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "どのチャット": sid,
        "手が入ったままのファイル": len(dirty),
        "その例": dirty[:5],
        "最後のコミット": last,
        "エラー": problems,
        "警告": warns,
    }
    try:
        old = json.loads(log.read_text(encoding="utf-8")) if log.exists() else []
        if not isinstance(old, list):
            old = []
    except Exception:
        old = []
    old.append(rec)
    try:
        log.write_text(json.dumps(old[-20:], ensure_ascii=False, indent=1) + "\n",
                       encoding="utf-8")
    except Exception:
        pass                                    # 足跡が残せなくても、点検は止めない


def main() -> int:
    # Windowsのコンソール文字コードに引きずられないよう、出力はUTF-8に固定する
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    # フックへの入力(JSON)。読めなくても点検は続ける
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        payload = {}

    # すでにこのフックで一度止めている場合は、無限ループを避けて通す
    if payload.get("stop_hook_active"):
        return 0

    out = Path(tempfile.gettempdir()) / "ozu_hook_check.json"
    try:
        subprocess.run(
            [sys.executable, "tools/check_site.py", "--changed", "--json", str(out)],
            cwd=str(REPO), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=180,
        )
    except Exception as e:                      # 点検自体が動かないときは黙って通す
        print(f"点検スクリプトを起動できませんでした: {e}", file=sys.stderr)
        return 0

    if not out.exists():                        # 変更ページが無いときはJSONが出ない
        ashiato(0, 0, payload)
        return 0

    try:
        result = json.loads(out.read_text(encoding="utf-8"))
    except Exception:
        return 0
    finally:
        out.unlink(missing_ok=True)

    # 止めるのはエラー(事実・構造の問題)だけ。警告(文章の好み)では止めない。
    #
    # 2026-08-29までは警告でも止めていた。すると「検査を通すため」に文章を
    # いじる圧力が生まれ、控えめな言い方が断定に変わる事故が実際に起きた。
    # 検査は下限を守るためのもので、文章を機械の好みに寄せるためのものではない。
    errors = result.get("errors", [])
    warnings = result.get("warnings", [])
    if warnings and not errors:
        # 見せるだけ。判断は書き手に任せる
        print("参考: いま編集したページに、文章の目安から外れている箇所があります。", file=sys.stderr)
        print("      直すかどうかは記事の質で判断すること。機械の目安に合わせて質を落とさない。", file=sys.stderr)
        for it in warnings[:10]:
            print(f"        {it['path']}  [{it['kind']}] {it['message']}", file=sys.stderr)
        ashiato(0, len(warnings), payload)
        return 0
    problems = errors
    if not problems:
        ashiato(0, len(warnings), payload)
        return 0

    lines = [
        "いま編集したページに、壊れている箇所があります(事実・構造の問題)。",
        "これは文章の好みではなく、読者に実害が出るものなので直してから完了すること。",
        "",
    ]
    for it in problems[:20]:
        lines.append(f"  {it['path']}")
        lines.append(f"    [{it['kind']}] {it['message']}")
        if it.get("detail"):
            lines.append(it["detail"])
    if len(problems) > 20:
        lines.append(f"  ほか{len(problems) - 20}件。python tools/check_site.py --changed で全部見られます")

    print("\n".join(lines), file=sys.stderr)
    ashiato(len(problems), len(warnings), payload)
    return 2


if __name__ == "__main__":
    sys.exit(main())
