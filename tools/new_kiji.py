#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新しい記事の「入れ物」を1コマンドで作る
==================================================================

公開作業(/kokai)のうち、毎回同じで、かつ間違えやすい3つを自動化します。

  1. eachnews/スラッグ.html を、必要な部品が全部そろった形で作る
     (title / og:title / JSON-LD / h1 の4か所に同じタイトルが入る)
  2. assets/js/news-data.js の台帳に1件足す
  3. sitemap.xml に1行足す

使い方(PowerShellでリポジトリのフォルダから):

    python tools/new_kiji.py --slug kanko-rieki-yukue ^
        --title "観光に88%が賛成。じゃあ、もうけは大洲に落ちているのか" ^
        --category shiten ^
        --desc "肱南地区アンケートの自由記述を起点に、観光のお金の流れを検証する。" ^
        --source "大洲市(令和7年度アンケート)ほか" ^
        --tags "観光,財政・税金" ^
        --source-date 2025-12-24

これで「入れ物」ができるので、あとは本文(Notion②の原稿)を
<!-- 本文ここから --> の位置に流し込み、要点3行と出典を埋めて、

    python tools/add_readtime.py
    python tools/check_site.py

を走らせればよい。エラーがゼロになるまで公開しない、はこれまでどおり。

ファイルを壊さないための決まり:
- スラッグが既に存在する場合は何もせずに止まる
- news-data.js / sitemap.xml は該当の1か所にだけ挿入する
"""
import argparse
import datetime
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
BASE_URL = "https://ozulifememo.github.io/ozu-life-memo"

CATEGORY_LABELS = {"ima": "大洲のいま", "kurashi": "大洲の暮らし", "shiten": "大洲の視点"}

TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} ｜ OZU LIFE MEMO</title>
<meta name="description" content="{desc}">
<link rel="icon" href="../assets/img/favicon-192.png">
<link rel="apple-touch-icon" href="../assets/img/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link data-ozu-fonts rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&amp;family=Shippori+Mincho+B1:wght@600;700&amp;display=swap">
<link rel="stylesheet" href="../assets/css/style.css">
<meta property="og:type" content="article">
<meta property="og:site_name" content="OZU LIFE MEMO">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{base}/eachnews/{slug}.html">
<meta property="og:image" content="{base}/assets/img/ogp-card.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="{base}/eachnews/{slug}.html">

<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "NewsArticle",
  "headline": "{title}",
  "description": "{desc}",
  "datePublished": "{date}",
  "dateModified": "{date}",
  "image": "{base}/assets/img/ogp-card.png",
  "author": {{"@type": "Organization", "name": "OZU LIFE MEMO"}},
  "publisher": {{"@type": "Organization", "name": "OZU LIFE MEMO"}},
  "mainEntityOfPage": {{"@type": "WebPage", "@id": "{base}/eachnews/{slug}.html"}}
}}
</script>
</head>

<body>

<div data-site-header data-prefix="../"></div>

<section>
  <div class="wrap">
    <div class="article-layout">
      <div class="article-page" data-slug="{slug}">
    <p class="article-date"><span class="article-cat">{cat_label}</span> ・ 出典: {source_label}</p>
    <h1>{title}</h1>

    <div class="article-summary">
      <p class="article-summary-label">要点</p>
      <ul>
        <li>(要点1: 核心の事実。数字か語を1つ<strong>太字</strong>に)</li>
        <li>(要点2: 裏付けの数字や仕組み)</li>
        <li>(要点3: 読者への意味・実用情報)</li>
      </ul>
    </div>

    <!-- 本文ここから: Notion②の原稿を流し込む。段落は <p class="commentary">、見出しは <h2> -->
    <p class="commentary">(本文)</p>
    <!-- 本文ここまで -->

    <div class="content-block source-box">
      <h2 class="source-box-title">出典・参考にした資料</h2>
      <a class="source-link" href="(URL1)" target="_blank" rel="noopener">(出典1のタイトル・発行元・日付注記)</a>
      <a class="source-link" href="(URL2)" target="_blank" rel="noopener">(出典2のタイトル・発行元・日付注記)</a>
      <p class="source-box-posted">この記事をサイトに掲載した日: {date_jp}</p>
    </div>
    <div class="related-list">
      <h2>同じテーマの記事</h2>
      <ul id="related-list-items"></ul>
    </div>
  </div>
      <aside class="article-sidebar">
        <div class="sidebar-widget">
          <h3 class="sidebar-widget-title">カテゴリで探す</h3>
          <div class="sidebar-widget-links">
            <a href="../news/">大洲のいま</a>
            <a href="../news/">大洲の暮らし</a>
            <a href="../news/">大洲の視点</a>
          </div>
        </div>

        <div class="sidebar-widget">
          <h3 class="sidebar-widget-title">最新記事</h3>
          <ul class="sidebar-latest-list" id="sidebar-latest-list"></ul>
        </div>

        <div class="sidebar-widget">
          <h3 class="sidebar-widget-title">サイトを見てまわる</h3>
          <div class="sidebar-widget-links">
            <a href="../news/">大洲ノート（記事一覧）</a>
            <a href="../monthly/">月間まとめ</a>
            <a href="../map/">大洲の地図</a>
            <a href="../book/">大洲と読書</a>
            <a href="../quiz/">大洲検定</a>
            <a href="../geoguess/">大洲ジオゲッサー</a>
            <a href="../photo/">フリー写真</a>
          </div>
        </div>

        <div class="sidebar-widget sidebar-cta">
          <p>感想やご指摘があれば、お気軽にどうぞ。</p>
          <a href="#" class="form-btn" data-modal-open>お問い合わせ</a>
        </div>
      </aside>
    </div>
  </div>
</section>

<div data-site-footer="article"></div>

<div data-site-modal></div>

<script src="../assets/js/site-chrome.js"></script>
<script src="../assets/js/news-data.js"></script>
<script src="../assets/js/photos-data.js"></script>
<script src="../assets/js/article-related.js"></script>
<script src="../assets/js/main.js"></script>
<script data-goatcounter="https://ozulifememo.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
</body>
</html>
"""


def load_tags(news_js: str) -> list:
    m = re.search(r"const OZU_TAGS = \[(.*?)\];", news_js, flags=re.S)
    if not m:
        return []
    return re.findall(r'"([^"]+)"', m.group(1))


def main():
    ap = argparse.ArgumentParser(description="新しい記事の入れ物(HTML+台帳+sitemap)を作る")
    ap.add_argument("--slug", required=True, help="ファイル名(英小文字・数字・ハイフン)")
    ap.add_argument("--title", required=True, help="記事タイトル(4か所に同じものが入る)")
    ap.add_argument("--category", required=True, choices=sorted(CATEGORY_LABELS))
    ap.add_argument("--desc", required=True, help="meta description(記事の1文説明)")
    ap.add_argument("--source", required=True, help="冒頭と台帳に出す出典の表示名")
    ap.add_argument("--tags", default="", help="カンマ区切り。OZU_TAGSにある語だけ")
    ap.add_argument("--date", default=None, help="掲載日 YYYY-MM-DD(省略時は今日)")
    ap.add_argument("--source-date", default=None, help="出典の日付 YYYY-MM-DD(あれば)")
    args = ap.parse_args()

    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", args.slug):
        sys.exit(f"エラー: スラッグ '{args.slug}' は英小文字・数字・ハイフンのみにしてください")

    date = args.date or datetime.date.today().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        sys.exit("エラー: --date は YYYY-MM-DD 形式で")
    date_jp = date.replace("-", "/")

    html_path = REPO / "eachnews" / f"{args.slug}.html"
    news_path = REPO / "assets" / "js" / "news-data.js"
    sitemap_path = REPO / "sitemap.xml"

    news_js = news_path.read_text(encoding="utf-8")
    sitemap = sitemap_path.read_text(encoding="utf-8")

    # 既にあるものを上書き・二重登録しない
    if html_path.exists():
        sys.exit(f"エラー: {html_path.name} は既にあります。何も変更していません")
    if f'slug: "{args.slug}"' in news_js:
        sys.exit(f"エラー: news-data.js に {args.slug} が既にあります。何も変更していません")
    if f"/eachnews/{args.slug}.html" in sitemap:
        sys.exit(f"エラー: sitemap.xml に {args.slug} が既にあります。何も変更していません")

    valid_tags = load_tags(news_js)
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    bad = [t for t in tags if t not in valid_tags]
    if bad:
        sys.exit(f"エラー: タグ {bad} はOZU_TAGSにありません。使えるのは: {valid_tags}")
    if not tags:
        print("注意: タグが空です。公開までに必ず1〜2個付けてください(kokaiのルール)")

    source_label = args.source
    if args.source_date:
        source_label += f"（情報源日付: {args.source_date}）"

    # 1. HTML
    html_path.write_text(
        TEMPLATE.format(
            title=args.title, desc=args.desc, slug=args.slug, base=BASE_URL,
            date=date, date_jp=date_jp,
            cat_label=CATEGORY_LABELS[args.category], source_label=source_label,
        ),
        encoding="utf-8",
    )

    # 2. 台帳(news-data.js)。配列の先頭に足す
    tags_js = ", ".join(f'"{t}"' for t in tags)
    entry_lines = [
        "  {",
        f'    slug: "{args.slug}",',
        f'    date: "{date}",',
        f'    title: "{args.title}",',
        f'    category: "{args.category}",',
        f'    source: "{args.source}",',
    ]
    if args.source_date:
        entry_lines.append(f'    sourceDate: "{args.source_date}",')
    entry_lines.append(f"    tags: [{tags_js}],")
    entry_lines.append("  },")
    entry = "\n".join(entry_lines)
    marker = "const OZU_NEWS = ["
    if marker not in news_js:
        sys.exit("エラー: news-data.js に OZU_NEWS 配列が見つかりません")
    news_path.write_text(news_js.replace(marker, marker + "\n" + entry, 1), encoding="utf-8")

    # 3. sitemap.xml。</urlset> の直前に足す
    loc = (f"  <url><loc>{BASE_URL}/eachnews/{args.slug}.html</loc>"
           f"<lastmod>{date}</lastmod><priority>0.6</priority></url>\n")
    if "</urlset>" not in sitemap:
        sys.exit("エラー: sitemap.xml に </urlset> が見つかりません")
    sitemap_path.write_text(sitemap.replace("</urlset>", loc + "</urlset>", 1), encoding="utf-8")

    print(f"作成: eachnews/{args.slug}.html(台帳とsitemapにも登録済み)")
    print("次にやること:")
    print("  1. 本文をNotion②から流し込む(<!-- 本文ここから --> の位置)")
    print("  2. 要点3行と出典(2本以上・日付注記つき)を埋める")
    print("  3. python tools/add_readtime.py")
    print("  4. python tools/check_site.py  (エラー0まで公開しない)")


if __name__ == "__main__":
    main()
