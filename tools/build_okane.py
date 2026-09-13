# -*- coding: utf-8 -*-
"""連載「大洲のお金の教科書」の入口ページを作る。

2026-09-12に作った。本人の依頼はこうだった。

> 税金、経済、市役所の経営、国、県の税金、町の運営方法の違い、南予地方局ってなんだよ。
> 少しずれると、学校は小中学校は大洲市の財源？高校は県の財源？
> 市の税金はどこに使われているか。図とか表とかをたくさん出して。
> 大洲市の施設名をめっちゃ使っていい。
> 「体系的！！！」なものにしてほしい。1つ1つの記事でも見れるけど、
> 最初から見たら、もっとつながりが見えるようにしてほしい。

**なぜ記事そのものは eachnews/ に置くのか。**
このサイトの道具(add_readtime / apply_memou / make_feed / kiji_md / build_review ほか
10本)は eachnews を前提に書かれている。新しい置き場所を作ると、そのすべてを
直すことになり、記事268本に影響が出る。だから記事は eachnews/ に置き、
**入口だけを okane/ に作る。**索引ページ「こんなときは」(sakuin/)と同じ形である。

連載が増えたら SERIES に足して、もう一度走らせる。
書き上がった回は "done": True にする。まだのものは「準備中」と出る。

    python tools/build_okane.py
"""
import io
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "okane" / "index.html"

TITLE = "大洲のお金の教科書"
LEAD = ("税金は誰が集めて、どこへ行って、何に使われるのか。"
        "国と県と市の分かれ目から、大洲市の決算まで、順に読める形にした。<br>"
        "1回ずつでも読めるが、最初から読むと全部つながる。")

# color は札の左に入る色。サイトのタグ色から採っている
SERIES = [
    {"n": 1, "slug": "okane-01-dare-ga-atsumeru", "c": "#3d5473",
     "title": "税金は誰が集めているのか",
     "lead": "国税・県税・市税の分かれ目。なぜこの税は国で、この税は市なのか。大洲で払う税を全部並べた。",
     "done": True},
    {"n": 2, "slug": "okane-02-chokusetsu-kansetsu", "c": "#8a5541",
     "title": "直接税と間接税",
     "lead": "払う人と納める人が違う税がある。大洲でたばこを買うと、そのお金は大洲市に入る。",
     "done": True},
    {"n": 3, "slug": "okane-03-tsukaimichi", "c": "#3a6a64",
     "title": "その税は何に使えるのか",
     "lead": "普通税と目的税。一般財源と特定財源。お金に色が付いているものと、付いていないもの。",
     "done": True},
    {"n": 4, "slug": "okane-04-kuni-ken-shi", "c": "#566b45",
     "title": "国・県・市は何を分担しているのか",
     "lead": "小中学校は市、高校は県。ただし先生の給料は、どちらも県が払っている。",
     "done": True},
    {"n": 5, "slug": "okane-05-nanyo-chihokyoku", "c": "#846f42",
     "title": "南予地方局とは何なのか",
     "lead": "平成20年、県の地方局が5つから3つに減った。大洲市は中予を求めたが、宇和島の南予になった。",
     "done": True},
    {"n": 6, "slug": "okane-06-kubarinaosi", "c": "#9a6238",
     "title": "集めたお金は、どう配り直されるのか",
     "lead": "地方交付税、国庫支出金、県支出金。そしてふるさと納税だけが逆を向いている。",
     "done": True},
    {"n": 7, "slug": "okane-07-shiyakusho-keiei", "c": "#556678",
     "title": "市役所は、どう経営されているのか",
     "lead": "予算・決算・監査の1年。誰が決めて、誰が確かめるのか。議会は何をする場所なのか。",
     "done": True},
    {"n": 8, "slug": "okane-08-doko-ni-tsukau", "c": "#7b5060",
     "title": "自由に使えたお金で、市は何をしたのか",
     "lead": "経常収支比率99.7％。毎年の残りは4,349万5千円。それでも49億7,612万円が動いた。",
     "done": True},
    {"n": 9, "slug": "okane-09-dare-ga-yaru", "c": "#3a6a64",
     "title": "市がやっていない仕事は、誰がやるのか",
     "lead": "消防もし尿も、大洲市はやっていない。組合・指定管理・委託で、市役所の外に34億円。",
     "done": True},
    {"n": 10, "slug": "okane-10-ozu-no-tsucho", "c": "#3d5473",
     "title": "大洲の通帳",
     "lead": "入ってくるお金と出ていくお金を、1枚にまとめる。この連載の答え合わせ。",
     "done": False},
]

# 第8回で確定させたこと(2026-09-13)
#   経常収支比率の公式値は 99.7%。分子=経常経費充当一般財源等計 16,043,377千円、
#   分母=経常一般財源等 16,047,572千円 + 臨時財政対策債 39,300千円 = 16,086,872千円。
#   決算カードに並ぶ「99.1」は歳入の(一般財源計)行の構成比であって、経常収支比率ではない。
#   市町村別決算状況調 001061669.xlsx の列29「経常収支比率」が 99.7、
#   列32「減収補塡債(特例分)及び臨時財政対策債を経常一般財源等から除いた経常収支比率」が 100。
#   毎年の残りは 43,495千円(4,349万5千円)。それでも投資的経費は 4,976,122千円 動いた。
#   理由は地方財政法5条。借金してよいのは建てるときと災害のときだけなので、
#   経常収支比率は「建てられるか」を測っていない。
#
# 連載の外にある、関わりの深い記事。入口の下に置く
RELATED = [
    ("ozu-kofuzei-hikizan", "交付税94億円は、引き算1本で決まっていた"),
    ("ozu-shiminzei-yukue", "あなたが納めた市民税10万円は、どこへ行ったのか"),
    ("kessan-nihongo", "決算の日本語は、なぜこんなに読めないのか"),
]

HEAD = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} ｜ OZU LIFE MEMO</title>
<meta name="description" content="{desc}">
<link rel="icon" href="../assets/img/favicon-192.png">
<link rel="alternate" type="application/rss+xml" title="OZU LIFE MEMO の更新" href="../feed.xml">
<link rel="apple-touch-icon" href="../assets/img/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link data-ozu-fonts rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&amp;family=Shippori+Mincho+B1:wght@600;700&amp;display=swap">
<link rel="stylesheet" href="../assets/css/style.css">
<meta property="og:type" content="website">
<meta property="og:site_name" content="OZU LIFE MEMO">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="https://ozulifememo.github.io/ozu-life-memo/okane/">
<meta property="og:image" content="https://ozulifememo.github.io/ozu-life-memo/assets/img/ogp-card.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="https://ozulifememo.github.io/ozu-life-memo/okane/">
</head>

<body>

<div data-site-header data-prefix="../"></div>

<section class="page-hero" style="padding-bottom:0;">
  <div class="wrap">
    <h1>{title}</h1>
    <p>{lead}</p>
  </div>
</section>
<section style="padding-top:var(--space-5);">
<div class="wrap">
<ol class="kk-list">
"""

FOOT = """</ol>
</div>
</section>
<section style="padding-top:0;">
<div class="wrap">
  <h2 class="section-title">連載の外の、関わりの深い記事</h2>
  <ul class="related-list-plain">
{related}
  </ul>
</div>
</section>

<div data-site-footer></div>
<div data-site-modal></div>

<script src="../assets/js/site-chrome.js"></script>
<script src="../assets/js/main.js"></script>
<script data-goatcounter="https://ozulifememo.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
</body>
</html>
"""


def main():
    rows = []
    done = 0
    for s in SERIES:
        p = REPO / "eachnews" / (s["slug"] + ".html")
        live = s["done"] and p.exists()
        if live:
            done += 1
            # 題は記事のほうが正。書き換えたときにズレないように読みにいく
            h1 = re.search(r"<h1[^>]*>(.*?)</h1>", io.open(p, encoding="utf-8").read(), re.S)
            t = re.sub(r"<[^>]+>", "", h1.group(1)).strip() if h1 else s["title"]
            rows.append(
                '  <li class="kk-item" style="--c:{c}">'
                '<a href="../eachnews/{slug}.html">'
                '<span class="kk-no">第{n}回</span>'
                '<b>{t}</b><span class="kk-lead">{lead}</span></a></li>'.format(
                    c=s["c"], slug=s["slug"], n=s["n"], t=t, lead=s["lead"]))
        else:
            rows.append(
                '  <li class="kk-item kk-yet" style="--c:{c}">'
                '<span class="kk-no">第{n}回</span>'
                '<b>{t}</b><span class="kk-lead">{lead}</span>'
                '<span class="kk-soon">準備中</span></li>'.format(
                    c=s["c"], n=s["n"], t=s["title"], lead=s["lead"]))

    rel = []
    for slug, t in RELATED:
        if (REPO / "eachnews" / (slug + ".html")).exists():
            rel.append('    <li><a href="../eachnews/%s.html">%s</a></li>' % (slug, t))

    desc = "税金は誰が集めて、どこへ行って、何に使われるのか。国と県と市の分かれ目から大洲市の決算まで、10回で順に読む。"
    html = (HEAD.format(title=TITLE, desc=desc, lead=LEAD)
            + "\n".join(rows) + "\n"
            + FOOT.format(related="\n".join(rel)))
    OUT.parent.mkdir(exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(html)
    print("  書き出し: %s" % OUT.relative_to(REPO))
    print("  全%d回のうち、公開ずみ %d回 / 準備中 %d回" % (len(SERIES), done, len(SERIES) - done))
    print("  連載の外の記事 %d本" % len(rel))


if __name__ == "__main__":
    main()
