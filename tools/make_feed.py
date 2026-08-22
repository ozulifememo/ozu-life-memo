#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新をお知らせするRSS(feed.xml)を作る
==================================================================

news-data.js の台帳から、新しい記事30本ぶんの feed.xml を作ります。
読者がRSSリーダー(FeedlyやInoreader)に登録すると、SNSを見ていなくても
新しい記事に気づけます。SNSのアルゴリズムに左右されない導線です。

    python tools/make_feed.py

記事を公開したら、add_readtime.py と一緒に走らせてください(何度でも安全)。
"""
import html
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
BASE = "https://ozulifememo.github.io/ozu-life-memo"
JST = timezone(timedelta(hours=9))
MAX_ITEMS = 30

CATEGORY_LABELS = {"ima": "大洲のいま", "kurashi": "大洲の暮らし", "shiten": "大洲の視点"}


def load_entries() -> list[dict]:
    js = (REPO / "assets" / "js" / "news-data.js").read_text(encoding="utf-8")
    m = re.search(r"const OZU_NEWS = \[(.*?)\n\];", js, flags=re.S)
    if not m:
        sys.exit("news-data.js から OZU_NEWS 配列を読めませんでした")
    out = []
    for block in re.findall(r"\{(.*?)\n  \}", m.group(1), flags=re.S):
        def field(name):
            mm = re.search(rf'{name}:\s*"([^"]*)"', block)
            return mm.group(1) if mm else ""
        slug, title, date = field("slug"), field("title"), field("date")
        if not (slug and title and date):
            continue
        tags = re.findall(r'"([^"]+)"', re.search(r"tags:\s*\[(.*?)\]", block, flags=re.S).group(1)) \
            if re.search(r"tags:\s*\[(.*?)\]", block, flags=re.S) else []
        out.append({"slug": slug, "title": title, "date": date,
                    "category": field("category"), "source": field("source"), "tags": tags})
    return out


def summary(slug: str) -> str:
    """記事本文の meta description を紹介文に使う(無ければ空)"""
    p = REPO / "eachnews" / f"{slug}.html"
    if not p.exists():
        return ""
    m = re.search(r'<meta name="description" content="([^"]*)"', p.read_text(encoding="utf-8"))
    return m.group(1) if m else ""


def rfc822(date_str: str) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=9, tzinfo=JST)
    return d.strftime("%a, %d %b %Y %H:%M:%S +0900")


def main():
    entries = load_entries()
    # 掲載日の新しい順。同じ日なら台帳の並び(新しいものが上)を保つ
    entries.sort(key=lambda e: e["date"], reverse=True)
    items = []
    for e in entries[:MAX_ITEMS]:
        url = f"{BASE}/eachnews/{e['slug']}.html"
        desc = summary(e["slug"]) or f"{CATEGORY_LABELS.get(e['category'], '')}の記事です。"
        cats = "".join(f"\n      <category>{html.escape(t)}</category>" for t in e["tags"])
        items.append(
            "    <item>\n"
            f"      <title>{html.escape(e['title'])}</title>\n"
            f"      <link>{url}</link>\n"
            f"      <guid isPermaLink=\"true\">{url}</guid>\n"
            f"      <pubDate>{rfc822(e['date'])}</pubDate>\n"
            f"      <description>{html.escape(desc)}</description>{cats}\n"
            "    </item>"
        )

    now = datetime.now(JST).strftime("%a, %d %b %Y %H:%M:%S +0900")
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "  <channel>\n"
        "    <title>OZU LIFE MEMO</title>\n"
        f"    <link>{BASE}/</link>\n"
        "    <description>愛媛県大洲市の非公式・生活情報サイト。市役所や議会の硬い資料を、1人の市民の目線で読み解いています。</description>\n"
        "    <language>ja</language>\n"
        f"    <lastBuildDate>{now}</lastBuildDate>\n"
        f'    <atom:link href="{BASE}/feed.xml" rel="self" type="application/rss+xml" />\n'
        + "\n".join(items) + "\n"
        "  </channel>\n"
        "</rss>\n"
    )
    (REPO / "feed.xml").write_text(xml, encoding="utf-8")
    print(f"feed.xml を作りました(記事{len(items)}本ぶん / 最新: {entries[0]['title']})")


if __name__ == "__main__":
    main()
