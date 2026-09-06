# -*- coding: utf-8 -*-
"""全HTMLの<head>にWebフォントの読み込みを入れる(何度実行してもよい)。"""
import io, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARK = "data-ozu-fonts"
BLOCK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '<link ' + MARK + ' rel="stylesheet" '
    'href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700'
    '&amp;family=Shippori+Mincho+B1:wght@600;700&amp;display=swap">\n'
)

targets = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in (".git", ".claude", "node_modules")]
    for fn in filenames:
        if fn.endswith(".html"):
            targets.append(os.path.join(dirpath, fn))

added = skipped = nohead = 0
for path in sorted(targets):
    s = io.open(path, encoding="utf-8").read()
    if MARK in s:
        skipped += 1
        continue
    # style.css の読み込み行の直前に入れる
    m = re.search(r'^[ \t]*<link rel="stylesheet" href="[^"]*style\.css">', s, re.M)
    if not m:
        nohead += 1
        print("  head不明:", os.path.relpath(path, ROOT))
        continue
    indent = re.match(r'^[ \t]*', m.group(0)).group(0)
    block = "".join(indent + line + "\n" for line in BLOCK.strip().split("\n"))
    s = s[:m.start()] + block + s[m.start():]
    io.open(path, "w", encoding="utf-8", newline="").write(s)
    added += 1

print("追加 %d / 既にあり %d / style.css行が見つからない %d (全%d件)" % (added, skipped, nohead, len(targets)))
