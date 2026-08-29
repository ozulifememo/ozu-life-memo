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
        return 0
    problems = errors
    if not problems:
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
    return 2


if __name__ == "__main__":
    sys.exit(main())
