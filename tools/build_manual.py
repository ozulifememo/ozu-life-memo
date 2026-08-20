#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
運用マニュアルを、デスクトップで読める1枚のHTMLに書き出します。

    python tools/build_manual.py

デスクトップに次の2つを作ります(既にあれば上書き)。

  ・OZU LIFE MEMO 運用マニュアル.html   … 全章をまとめた本体
  ・クロコのスキル早見表.html            … スキルだけの1枚もの

外部ライブラリは使いません(pip不要)。マニュアルを直したら、また走らせれば
最新版に作り直されます。

※ このHTMLには個人情報が含まれます。ネットに上げないでください。
"""

from __future__ import annotations

import html
import re
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
MANUAL_DIR = REPO / "docs" / "manual"
SKILL_DIR = REPO / ".claude" / "skills"
DESKTOP = Path.home() / "Desktop"

# 章を並べる順番(ファイル名の先頭の数字順。付録は最後)
def chapter_order(p: Path):
    m = re.match(r"^(\d+)", p.stem)
    return (0, int(m.group(1))) if m else (1, 0)


# ---------------------------------------------------------------------------
# Markdown → HTML(必要な範囲だけの自前変換)
# ---------------------------------------------------------------------------

def inline(text: str) -> str:
    """行の中の装飾(太字・コード・リンク)を変換する"""
    # まずHTMLとして危ない文字を無害化する
    out = html.escape(text, quote=False)

    # `コード`
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    # **太字**
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    # [表示テキスト](リンク先)
    def link(m):
        label, href = m.group(1), m.group(2)
        if href.endswith(".md"):          # 章どうしのリンクはページ内ジャンプにする
            href = "#" + re.sub(r"\.md$", "", href)
        return f'<a href="{href}">{label}</a>'
    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, out)
    # [[メモリ名]] は外部ファイルなのでリンクにせず、そのまま目立たせる
    out = re.sub(r"\[\[([^\]]+)\]\]", r'<span class="memo">\1</span>', out)
    return out


def md_to_html(md: str) -> str:
    lines = md.split("\n")
    out, i = [], 0
    in_code = False
    code_buf = []            # コードブロックの中身を一時的にためる
    list_stack = []          # "ul" / "ol" の入れ子

    def close_lists(to=0):
        while len(list_stack) > to:
            out.append(f"</{list_stack.pop()}>")

    while i < len(lines):
        line = lines[i]

        # コードブロック(<code>の直後に改行を入れると空行に見えるのでまとめて出す)
        if line.strip().startswith("```"):
            if in_code:
                out.append("<pre><code>" + "\n".join(code_buf) + "</code></pre>")
                code_buf = []
                in_code = False
            else:
                close_lists()
                code_buf = []
                in_code = True
            i += 1
            continue
        if in_code:
            code_buf.append(html.escape(line, quote=False))
            i += 1
            continue

        stripped = line.strip()

        # 空行
        if not stripped:
            close_lists()
            i += 1
            continue

        # 見出し
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            close_lists()
            level = len(m.group(1))
            out.append(f"<h{level}>{inline(m.group(2))}</h{level}>")
            i += 1
            continue

        # 区切り線
        if re.match(r"^-{3,}$|^\*{3,}$", stripped):
            close_lists()
            out.append("<hr>")
            i += 1
            continue

        # 表(| で始まり、次の行が区切り行)
        if stripped.startswith("|") and i + 1 < len(lines) and \
           re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            close_lists()
            def cells(row):
                row = row.strip()
                if row.startswith("|"):
                    row = row[1:]
                if row.endswith("|"):
                    row = row[:-1]
                # \| はセル区切りではなく文字としてのパイプ
                parts = re.split(r"(?<!\\)\|", row)
                return [c.strip().replace("\\|", "|") for c in parts]

            head = cells(stripped)
            out.append('<div class="table-wrap"><table><thead><tr>')
            out.extend(f"<th>{inline(c)}</th>" for c in head)
            out.append("</tr></thead><tbody>")
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = cells(lines[i])
                row += [""] * (len(head) - len(row))
                out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row[:len(head)]) + "</tr>")
                i += 1
            out.append("</tbody></table></div>")
            continue

        # 引用
        if stripped.startswith(">"):
            close_lists()
            quote = [re.sub(r"^>\s?", "", lines[i].strip())]
            i += 1
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(re.sub(r"^>\s?", "", lines[i].strip()))
                i += 1
            out.append(f"<blockquote>{inline(' '.join(quote))}</blockquote>")
            continue

        # 箇条書き・番号付き
        m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", line)
        if m:
            indent = len(m.group(1))
            kind = "ol" if m.group(2)[0].isdigit() else "ul"
            depth = indent // 2 + 1
            while len(list_stack) > depth:
                out.append(f"</{list_stack.pop()}>")
            if len(list_stack) < depth:
                out.append(f"<{kind}>")
                list_stack.append(kind)
            body = [m.group(3)]
            # 次の行がインデントされた continuation なら繋げる
            j = i + 1
            while j < len(lines) and lines[j].strip() and \
                  not re.match(r"^(\s*)([-*]|\d+\.)\s+", lines[j]) and \
                  lines[j].startswith(" " * (indent + 2)):
                body.append(lines[j].strip())
                j += 1
            out.append(f"<li>{inline(' '.join(body))}</li>")
            i = j
            continue

        # ふつうの段落(続く行をまとめる)
        close_lists()
        para = [stripped]
        j = i + 1
        while j < len(lines):
            nxt = lines[j].strip()
            if not nxt or nxt.startswith(("#", "|", ">", "```")) or \
               re.match(r"^(\s*)([-*]|\d+\.)\s+", lines[j]) or \
               re.match(r"^-{3,}$", nxt):
                break
            para.append(nxt)
            j += 1
        out.append(f"<p>{inline(' '.join(para))}</p>")
        i = j

    close_lists()
    if in_code:      # 閉じ忘れの``` があった場合の保険
        out.append("<pre><code>" + "\n".join(code_buf) + "</code></pre>")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# 見た目
# ---------------------------------------------------------------------------

CSS = """
:root{
  --bg:#faf9f7; --card:#fff; --text:#23231f; --muted:#6b6b64;
  --border:#e5e2db; --accent:#2f6fd0; --accent-soft:#eaf1fc;
  --warn-bg:#fff4e5; --warn-border:#f0c88a; --code-bg:#f3f1ec;
}
@media (prefers-color-scheme:dark){
  :root{
    --bg:#1a1a19; --card:#232322; --text:#e9e8e4; --muted:#a0a099;
    --border:#38372f; --accent:#7aa9f0; --accent-soft:#22304a;
    --warn-bg:#3a2f1c; --warn-border:#6b5320; --code-bg:#2c2b28;
  }
}
*{box-sizing:border-box}
body{
  margin:0; background:var(--bg); color:var(--text);
  font-family:"Hiragino Sans","Yu Gothic UI","Yu Gothic","Meiryo","Segoe UI",sans-serif;
  line-height:1.85; font-size:15.5px; display:flex;
}
nav{
  width:290px; flex:0 0 290px; height:100vh; position:sticky; top:0;
  overflow-y:auto; border-right:1px solid var(--border);
  padding:26px 18px; background:var(--card);
}
nav .brand{font-weight:700; font-size:15px; margin-bottom:4px}
nav .stamp{font-size:11.5px; color:var(--muted); margin-bottom:20px}
nav a{
  display:block; padding:7px 10px; border-radius:7px; font-size:13.5px;
  color:var(--text); text-decoration:none; margin-bottom:2px;
}
nav a:hover{background:var(--accent-soft); color:var(--accent)}
nav a.top{font-weight:700; background:var(--accent-soft); color:var(--accent); margin-bottom:12px}
main{flex:1; min-width:0; padding:44px 56px; max-width:940px}
h1{font-size:27px; margin:0 0 6px; letter-spacing:.01em}
h2{
  font-size:20px; margin:44px 0 14px; padding-bottom:8px;
  border-bottom:2px solid var(--border);
}
h3{font-size:16.5px; margin:28px 0 10px; color:var(--accent)}
h4{font-size:15px; margin:20px 0 8px; color:var(--muted)}
p{margin:0 0 13px}
ul,ol{margin:0 0 13px; padding-left:24px}
li{margin-bottom:5px}
code{
  background:var(--code-bg); padding:2px 6px; border-radius:4px;
  font-family:"Consolas","SF Mono",monospace; font-size:.88em;
}
pre{
  background:var(--code-bg); padding:14px 16px; border-radius:9px;
  overflow-x:auto; border:1px solid var(--border); margin:0 0 15px;
}
pre code{background:none; padding:0; font-size:13px; line-height:1.65}
.table-wrap{overflow-x:auto; margin:0 0 16px}
table{border-collapse:collapse; width:100%; font-size:14px}
th,td{border:1px solid var(--border); padding:8px 11px; text-align:left; vertical-align:top}
th{background:var(--accent-soft); font-weight:600; white-space:nowrap}
blockquote{
  margin:0 0 15px; padding:11px 16px; background:var(--warn-bg);
  border-left:4px solid var(--warn-border); border-radius:0 7px 7px 0;
}
blockquote p{margin:0}
hr{border:none; border-top:1px solid var(--border); margin:30px 0}
a{color:var(--accent)}
.memo{color:var(--muted); font-size:.9em}
.chapter{
  background:var(--card); border:1px solid var(--border); border-radius:13px;
  padding:30px 34px; margin-bottom:26px; scroll-margin-top:16px;
}
.chapter > h1{
  font-size:22px; border-bottom:2px solid var(--accent);
  padding-bottom:10px; margin-bottom:18px;
}
.cover{
  background:linear-gradient(135deg,var(--accent-soft),var(--card));
  border:1px solid var(--border); border-radius:13px;
  padding:34px 36px; margin-bottom:26px;
}
.cover h1{font-size:29px}
.cover .sub{color:var(--muted); font-size:14px; margin-top:6px}
.notice{
  margin-top:18px; padding:12px 16px; background:var(--warn-bg);
  border:1px solid var(--warn-border); border-radius:9px; font-size:13.5px;
}
@media print{
  body{display:block; font-size:10.5pt}
  nav{display:none}
  main{max-width:none; padding:0}
  .chapter{break-inside:auto; page-break-inside:auto; border:none; padding:0; margin-bottom:20px}
  .chapter > h1{page-break-before:always}
  .cover{border:none}
}
@media (max-width:860px){
  body{display:block}
  nav{width:auto; height:auto; position:static; border-right:none;
      border-bottom:1px solid var(--border)}
  main{padding:24px 18px}
}
"""


def page(title: str, body: str, extra_css: str = "") -> str:
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>{CSS}{extra_css}</style>
</head>
<body>
{body}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# 本体マニュアル
# ---------------------------------------------------------------------------

def build_manual() -> Path:
    files = sorted(MANUAL_DIR.glob("*.md"), key=chapter_order)
    if not files:
        raise SystemExit(f"マニュアルが見つかりません: {MANUAL_DIR}")

    nav = ['<div class="brand">OZU LIFE MEMO 運用マニュアル</div>',
           f'<div class="stamp">{datetime.now():%Y-%m-%d %H:%M} 時点</div>',
           '<a class="top" href="#top">表紙にもどる</a>']
    body = [f'''<div class="cover" id="top">
<h1>OZU LIFE MEMO 運用マニュアル</h1>
<div class="sub">{datetime.now():%Y年%m月%d日} 時点 ／ 全{len(files)}章</div>
<div class="notice">このファイルには運営者本人の個人情報が含まれます。
ネット上にアップロードしないでください。<br>
リポジトリの <code>docs/manual/</code> が原本です。直したら
<code>python tools/build_manual.py</code> で作り直せます。</div>
</div>''']

    for f in files:
        anchor = f.stem
        # 見出しの1行目を章タイトルとして使う
        text = f.read_text(encoding="utf-8")
        m = re.search(r"^#\s+(.*)$", text, re.M)
        title = m.group(1).strip() if m else f.stem
        nav.append(f'<a href="#{anchor}">{html.escape(title)}</a>')
        body.append(f'<section class="chapter" id="{anchor}">\n{md_to_html(text)}\n</section>')

    out = DESKTOP / "OZU LIFE MEMO 運用マニュアル.html"
    out.write_text(
        page("OZU LIFE MEMO 運用マニュアル",
             "<nav>" + "\n".join(nav) + "</nav>\n<main>" + "\n".join(body) + "</main>"),
        encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# スキル早見表(1枚もの)
# ---------------------------------------------------------------------------

SHEET_CSS = """
body{display:block}
main{max-width:1000px; margin:0 auto; padding:38px 30px}
.lede{font-size:15px; color:var(--muted); margin-bottom:26px}
.cards{display:grid; grid-template-columns:repeat(auto-fit,minmax(310px,1fr)); gap:16px; margin-bottom:30px}
.card{background:var(--card); border:1px solid var(--border); border-radius:12px; padding:20px 22px}
.card .cmd{
  font-family:"Consolas","SF Mono",monospace; font-size:19px; font-weight:700;
  color:var(--accent); display:block; margin-bottom:4px;
}
.card .when{font-weight:600; font-size:14.5px; margin-bottom:9px}
.card .desc{font-size:13.5px; color:var(--muted); line-height:1.75; margin:0}
.card ul{margin:10px 0 0; padding-left:19px; font-size:13px}
.card li{margin-bottom:3px}
.step{background:var(--card); border:1px solid var(--border); border-radius:12px; padding:22px 26px; margin-bottom:16px}
.step h2{margin-top:0; border:none; padding:0; font-size:17px}
@media print{
  main{padding:0}
  .cards{grid-template-columns:1fr 1fr}
  .card,.step{break-inside:avoid}
}
"""


def build_skill_sheet() -> Path:
    # 実際のスキルファイルから名前と説明を読む(手書きとズレないように)
    skills = {}
    for sk in sorted(SKILL_DIR.glob("*/SKILL.md")):
        t = sk.read_text(encoding="utf-8")
        fm = re.match(r"^---\n(.*?)\n---\n", t, re.S)
        if not fm:
            continue
        name = re.search(r"^name:\s*(.+)$", fm.group(1), re.M)
        desc = re.search(r"^description:\s*(.+)$", fm.group(1), re.M)
        if name and desc:
            skills[name.group(1).strip()] = desc.group(1).strip()

    # 早見表に載せる補足(運営者向けのかみくだいた説明)
    detail = {
        "kiji": ("記事を書く・書き直すとき", [
            "常体・太字・段落の濃さ・見出しの立て方を全部思い出す",
            "出典2本以上、数字は出典PDFで裏取り、という基準で書く",
            "書いたあと自動で点検スクリプトを走らせる",
        ]),
        "tenken": ("サイトが崩れていないか確かめたいとき", [
            "170ページを数秒で点検(ファイルは書き換えない)",
            "エラーがゼロなら、もう見なくてよい",
            "他のチャットが動いていないかも先に確認する",
        ]),
        "kokai": ("書いた記事を実際に公開するとき", [
            "HTML作成→台帳→sitemap→Notion→コミットの順をなぞる",
            "点検でエラーがゼロになるまで公開しない",
            "pushの前に必ず確認を取る",
        ]),
        "getsuji": ("月に一度の定期点検", [
            "サイトが生きているか(Pagesが勝手にOFFになる事故が2回)",
            "出典URLが死んでいないか",
            "Googleに載っているか",
        ]),
    }

    # 実際の作業の順番に並べる(アルファベット順だと使う順と合わないため)
    order = ["kiji", "tenken", "kokai", "getsuji"]
    skills = dict(sorted(skills.items(),
                         key=lambda kv: (order.index(kv[0]) if kv[0] in order else 99, kv[0])))

    cards = []
    for name, desc in skills.items():
        when, bullets = detail.get(name, ("", []))
        li = "".join(f"<li>{html.escape(b)}</li>" for b in bullets)
        cards.append(f'''<div class="card">
<span class="cmd">/{html.escape(name)}</span>
<div class="when">{html.escape(when)}</div>
<p class="desc">{html.escape(desc)}</p>
{f"<ul>{li}</ul>" if li else ""}
</div>''')

    body = f'''<main>
<h1>クロコのスキル早見表</h1>
<p class="lede">チャットで <code>/名前</code> と打つだけで、クロコがその作業のルールを
全部思い出してから動きます。{datetime.now():%Y年%m月%d日} 時点。</p>

<div class="cards">
{"".join(cards)}
</div>

<div class="step">
<h2>これは何のためにあるのか</h2>
<p>これまで「一度言ったルールが、しばらくすると守られなくなる」ということが
何度も起きていました。チャットが変わるとクロコの記憶が引き継がれないからです。</p>
<p>スキルは、その手順書をファイルとして残しておく仕組みです。
<strong>一度言ったことを、二度言わなくて済むようにするためのもの</strong>です。</p>
</div>

<div class="step">
<h2>新しいルールを覚えさせたいとき</h2>
<p>「これからはこうして」と決めたことがあれば、その場でクロコに
<strong>「これをスキルに追加して」</strong>と言ってください。次のチャットから守られます。</p>
<p>口で言うだけだと、そのチャットが終わった時点で忘れます。</p>
</div>

<div class="step">
<h2>点検スクリプト(スキルとは別物)</h2>
<p>スキルが「クロコへの手順書」なのに対し、点検スクリプトは
<strong>ご自身で打てる道具</strong>です。</p>
<pre><code>cd (このリポジトリのフォルダ)
python tools/check_site.py</code></pre>
<p>数秒でサイト170ページを点検します。ファイルは書き換えません。
エラーがゼロなら、それは本当にゼロです。</p>
<p>「点検器そのものが壊れていないか」を確かめたいときは
<code>python tools/check_site.py --selftest</code> を打ってください。
わざと壊したページを作って、ちゃんと見つけられるか試します。</p>
</div>

<div class="step">
<h2>置き場所</h2>
<div class="table-wrap"><table>
<thead><tr><th>もの</th><th>場所</th></tr></thead>
<tbody>
<tr><td>スキル本体</td><td><code>ozu-life-memo\\.claude\\skills\\</code></td></tr>
<tr><td>点検スクリプト</td><td><code>ozu-life-memo\\tools\\check_site.py</code></td></tr>
<tr><td>点検スクリプトの説明</td><td><code>ozu-life-memo\\tools\\README.md</code></td></tr>
<tr><td>運用マニュアル(原本)</td><td><code>ozu-life-memo\\docs\\manual\\</code></td></tr>
<tr><td>運用マニュアル(読む用)</td><td>デスクトップの「OZU LIFE MEMO 運用マニュアル.html」</td></tr>
</tbody>
</table></div>
</div>
</main>'''

    out = DESKTOP / "クロコのスキル早見表.html"
    out.write_text(page("クロコのスキル早見表", body, SHEET_CSS), encoding="utf-8")
    return out


if __name__ == "__main__":
    m = build_manual()
    s = build_skill_sheet()
    print(f"\n  作成しました:\n    {m}\n    {s}\n")
