#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
記事の読了時間(「約◯分で読める」)を計算して、冒頭のカテゴリ行に入れる
==================================================================

対象は eachnews/ の全記事。本文の文字数から機械的に計算するので、
記事を書き直したあとにもう一度走らせれば数字が更新されます(何度でも安全)。

    python tools/add_readtime.py

日本語の読む速さはおよそ500〜600字/分と言われるので、550字/分で計算し、
1分未満は「約1分」に切り上げています。
"""
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
CHARS_PER_MIN = 550


def visible_chars(html: str) -> int:
    m = re.search(r"<body\b[^>]*>(.*)</body>", html, flags=re.S | re.I)
    body = m.group(1) if m else html
    body = re.sub(r"<script\b.*?</script>", " ", body, flags=re.S | re.I)
    body = re.sub(r"<style\b.*?</style>", " ", body, flags=re.S | re.I)
    # 出典欄と「同じテーマの記事」は読了時間に数えない(本文ではないため)
    body = re.sub(r'<div class="content-block source-box".*', " ", body, flags=re.S)
    text = re.sub(r"<[^>]+>", "", body)
    text = re.sub(r"\s+", "", text)
    return len(text)


def main():
    changed = 0
    for p in sorted((REPO / "eachnews").glob("*.html")):
        html = p.read_text(encoding="utf-8")
        minutes = max(1, round(visible_chars(html) / CHARS_PER_MIN))
        tag = f'<span class="article-readtime">約{minutes}分で読める</span>'

        if 'class="article-readtime"' in html:
            new = re.sub(r'<span class="article-readtime">[^<]*</span>', tag, html)
        else:
            # カテゴリ行(<p class="article-date">…</p>)の末尾に足す
            new = re.sub(
                r'(<p class="article-date">.*?)(</p>)',
                lambda m: m.group(1) + " ・ " + tag + m.group(2),
                html,
                count=1,
                flags=re.S,
            )
        if new != html:
            p.write_text(new, encoding="utf-8")
            changed += 1
    print(f"読了時間を書き込んだ記事: {changed}件")


if __name__ == "__main__":
    main()
