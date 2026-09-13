# -*- coding: utf-8 -*-
"""月間まとめを、noteとインスタに出せる形で書き出す。

2026-09-13、本人の指示で作った。

> 8 これ、ちゃんとしたい。記事一つ一つではなく、どぱがきというか、
>   キャッチーに全振りして。ノート、インスタに出したい

サイトの記事は深いまま、入口だけキャッチーにする、という役割分担の「入口」側。
サイト内の月間まとめ(assets/js/monthly-data.js)とは別もの。

作るもの(書き出し先は引数で受ける。追跡ファイルにローカルパスを書かないため):
  カード PNG      … インスタ用 1080x1350。1枚に数字1つ。毎月同じ見た目
  note下書き.md   … いちばん驚いた数字から入る文章
  インスタ本文.txt … キャプションとタグ

中身は tools/tsuki-ledger.json に月ごとに書く。数字は公開ずみ記事から
引くこと(カードの数字はぜんぶ、その記事で出典まで確かめてある前提)。

    python tools/make_tsuki.py 2026-09 <書き出し先フォルダ>
"""
import io
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent.parent
LEDGER = REPO / "tools" / "tsuki-ledger.json"

# サイトと同じ色と書体。並んだときに「大洲のやつだ」と分かるように、ここは変えない
BG = "#f6f5f2"
INK = "#16232f"
MUTED = "#5b6673"
SERIF = '"Shippori Mincho B1","Hiragino Mincho ProN","Yu Mincho",serif'
SANS = '"Noto Sans JP","Hiragino Kaku Gothic ProN","Yu Gothic",Meiryo,sans-serif'

CARD_CSS = """
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=Shippori+Mincho+B1:wght@600;700&display=swap">
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { width:1080px; height:1350px; background:%(bg)s; color:%(ink)s;
         font-family:%(sans)s; overflow:hidden; }
  .card { width:100%%; height:100%%; padding:96px 88px 84px;
          display:flex; flex-direction:column; position:relative; }
  .bar { position:absolute; top:0; left:0; right:0; height:14px; background:var(--c); }
  .label { display:inline-block; align-self:flex-start; font-size:34px; font-weight:700;
           letter-spacing:.06em; color:#fff; background:var(--c);
           padding:10px 26px; margin-bottom:24px; }
  .no { position:absolute; top:96px; right:88px; font-family:%(serif)s;
        font-size:34px; color:%(muted)s; letter-spacing:.08em; }
  .bigwrap { flex:1; display:flex; flex-direction:column; justify-content:center; }
  .big { font-family:%(serif)s; font-weight:700; font-size:190px; line-height:1.08;
         letter-spacing:-0.01em; font-feature-settings:"palt" 1; }
  .big .small { font-size:64px; font-weight:700; letter-spacing:.02em; }
  .unit { font-family:%(serif)s; font-weight:700; font-size:56px; margin-top:10px; }
  .line { font-size:44px; line-height:1.75; margin-top:52px; color:%(ink)s;
          font-feature-settings:"palt" 1; }
  .line b { color:var(--c); font-weight:700; }
  .foot { display:flex; justify-content:space-between; align-items:baseline;
          border-top:3px solid #d3d0c7; padding-top:30px; margin-top:56px; }
  .site { font-family:%(serif)s; font-weight:700; font-size:36px; letter-spacing:.10em; }
  .month { font-size:30px; color:%(muted)s; letter-spacing:.08em; }
  /* 表紙と締め */
  .hook .big { font-size:120px; line-height:1.5; }
  .hook .lead { font-size:46px; color:%(muted)s; margin-top:44px; line-height:1.8; }
</style>
""" % {"bg": BG, "ink": INK, "muted": MUTED, "serif": SERIF, "sans": SANS}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def line_html(s):
    """<b>だけ通して、他はエスケープ"""
    s = esc(s)
    return s.replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")


def card_html(month_label, i, total, c):
    big = esc(c["big"])
    unit = ('<div class="unit">%s</div>' % line_html(c["unit"])) if c.get("unit") else ""
    return CARD_CSS + '''
<body style="--c:%s"><div class="card" style="--c:%s">
  <div class="bar"></div>
  <div class="label">%s</div>
  <div class="no">%d / %d</div>
  <div class="bigwrap"><div class="big">%s</div>%s
    <div class="line">%s</div></div>
  <div class="foot"><div class="site">OZU LIFE MEMO</div>
    <div class="month">%sの大洲</div></div>
</div></body>''' % (c["c"], c["c"], esc(c["label"]), i, total, big, unit,
                    line_html(c["line"]), month_label)


def hook_html(month_label, hook, lead, n):
    return CARD_CSS + '''
<body style="--c:#16232f"><div class="card hook" style="--c:#16232f">
  <div class="bar"></div>
  <div class="bigwrap">
    <div class="big">%s</div>
    <div class="lead">%s<br>数字は%d個。ぜんぶ出典つき。</div>
  </div>
  <div class="foot"><div class="site">OZU LIFE MEMO</div>
    <div class="month">%s</div></div>
</div></body>''' % (esc(hook), esc(lead), n, month_label)


def close_html(month_label):
    return CARD_CSS + '''
<body style="--c:#2a5b82"><div class="card hook" style="--c:#2a5b82">
  <div class="bar"></div>
  <div class="bigwrap">
    <div class="big">つづきは、<br>ぜんぶ記事に。</div>
    <div class="lead">どの数字にも出典を付けて、そのまま読める形で置いています。<br>
    「OZU LIFE MEMO」で検索。</div>
  </div>
  <div class="foot"><div class="site">OZU LIFE MEMO</div>
    <div class="month">%sの大洲</div></div>
</div></body>''' % month_label


def month_label_of(ym):
    y, m = ym.split("-")
    return "%s年%d月" % (y, int(m))


def render_pngs(pages, outdir):
    from playwright.sync_api import sync_playwright
    outdir.mkdir(parents=True, exist_ok=True)
    files = []
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page(viewport={"width": 1080, "height": 1350})
        for name, html in pages:
            tmp = outdir / ("_" + name + ".html")
            io.open(tmp, "w", encoding="utf-8").write(html)
            pg.goto(tmp.as_uri(), wait_until="load")
            try:
                pg.wait_for_function("document.fonts.status==='loaded'", timeout=10000)
            except Exception:
                pass  # 回線が無くても素の書体で出す
            pg.wait_for_timeout(250)
            f = outdir / (name + ".png")
            pg.screenshot(path=str(f))
            tmp.unlink()
            files.append(f)
        br.close()
    return files


SITE = "https://ozulifememo.github.io/ozu-life-memo"


def plain_line(s):
    """カード用の<b>をnoteの**に、インスタ用は素の文に"""
    return s.replace("<b>", "**").replace("</b>", "**")


def write_note(mon, label, outdir):
    cards = mon["cards"]
    L = ["# %sの大洲を、数字だけで。" % label, "", mon["note_intro"], "", "---", ""]
    for c in cards:
        big = c["big"] + (c.get("unit") or "")
        L.append("## %s ― %s" % (c["label"], big))
        L.append("")
        L.append(plain_line(c["line"]))
        L.append("")
        L.append("→ くわしくは: %s/eachnews/%s.html" % (SITE, c["slug"]))
        L.append("")
    L += ["---", "", mon["note_outro"], ""]
    f = outdir / "note下書き.md"
    io.open(f, "w", encoding="utf-8", newline="\n").write("\n".join(L))
    return f


def write_caption(mon, label, outdir):
    cards = mon["cards"]
    top = cards[:3]
    L = ["%sの大洲を、数字だけで。" % label, ""]
    for c in top:
        L.append("・%s ― %s" % (c["label"], c["big"] + (c.get("unit") or "")))
    L += ["", "つづきは画像で。%d個ぜんぶに出典を付けて、サイトの記事にしています。" % len(cards),
          "「OZU LIFE MEMO」で検索してください。", "",
          "#大洲市 #大洲 #愛媛 #愛媛県 #南予 #地方財政 #まちのデータ #OZULIFEMEMO"]
    f = outdir / "インスタ本文.txt"
    io.open(f, "w", encoding="utf-8", newline="\n").write("\n".join(L))
    return f


def main():
    if len(sys.argv) < 3:
        print("使い方: python tools/make_tsuki.py 2026-09 <書き出し先フォルダ>")
        return 1
    ym, outdir = sys.argv[1], Path(sys.argv[2])
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    mon = data["months"].get(ym)
    if not mon:
        print("tsuki-ledger.json に %s がありません" % ym)
        return 1
    label = month_label_of(ym)
    cards = mon["cards"]

    pages = [("00-表紙", hook_html(label, mon["hook"], mon["lead"], len(cards)))]
    for i, c in enumerate(cards, 1):
        pages.append(("%02d-%s" % (i, re.sub(r"[\\/:*?\"<>|]", "", c["label"])[:12]),
                      card_html(label, i, len(cards), c)))
    pages.append(("%02d-締め" % (len(cards) + 1), close_html(label)))

    files = render_pngs(pages, outdir)
    for f in files:
        print("  " + f.name)
    print("  カード %d枚 → %s" % (len(files), outdir))
    if mon.get("note_intro"):
        print("  " + write_note(mon, label, outdir).name)
    if mon.get("cards"):
        print("  " + write_caption(mon, label, outdir).name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
