#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OZU LIFE MEMO サイト点検スクリプト
====================================

サイト全体を機械的に点検して、崩れている箇所を一覧で出します。
ファイルは一切書き換えません(読むだけ)。安心して何度でも走らせてください。

使い方(PowerShellでリポジトリのフォルダに入ってから):

    python tools/check_site.py              ふつうの点検(ネット接続なし・数秒)
    python tools/check_site.py --urls       出典URLが生きているかも確認(数分かかる)
    python tools/check_site.py --slug ozu-mirai-note   1記事だけ点検
    python tools/check_site.py --json out.json          結果をJSONで保存(Notion照合用)

「エラー」は直した方がよいもの、「警告」は見て判断するものです。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Windowsのコンソールでも日本語が化けないようにする
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# 点検ルールの設定(ここを直せば基準を変えられます)
# ---------------------------------------------------------------------------

# 全ページ共通で入っていないといけない部品
CHROME_REQUIRED = [
    ("data-site-header", "ヘッダーの置き場所"),
    ("data-site-footer", "フッターの置き場所"),
    ("assets/js/site-chrome.js", "共通部品スクリプト"),
]

# 記事ページ(eachnews)だけに必要な部品
#
# 【写真まわりについて / 2026-08-19】
# もともとは全記事の末尾にランダムで写真を出す方式(article-random-photo +
# random-photo.js)だった。これを「記事の内容に合う写真だけを選んで出す」方式
# (article-images.js)へ差し替える改修が入ったため、旧方式の2つは必須から外した。
# 新方式が全記事に行き渡ったら、下の ARTICLE_PHOTO_OPTIONAL を必須へ移すこと。
ARTICLE_REQUIRED = [
    # 部分一致だと source-box-title で通ってしまう(2026-08-29に判明)。囲いの形で探す
    ('class="content-block source-box"', "出典ブロックの装飾クラス"),
    ("article-summary", "冒頭の要点3行ボックス"),
    ("article-readtime", "読了時間の表示(tools/add_readtime.pyで入る)"),
    ("data-site-modal", "お問い合わせモーダル"),
    ("application/ld+json", "構造化データ(検索エンジン向け)"),
    ('rel="canonical"', "正規URL指定"),
    ("og:title", "SNSシェア用タイトル"),
    ("assets/js/news-data.js", "記事台帳スクリプト"),
    ("assets/js/photos-data.js", "写真データスクリプト"),
    ("assets/js/article-related.js", "あわせて読みたいスクリプト"),
    ("assets/js/main.js", "共通スクリプト"),
]

# 写真の新方式。まだ移行中なので、欠けていてもエラーにしない(数だけ数える)。
ARTICLE_PHOTO_OPTIONAL = [
    ("assets/js/article-images.js", "記事写真のひもづけスクリプト"),
]

# 読み物ページ(book / jiyu-kenkyu)に必要な部品
READING_REQUIRED = [
    ("application/ld+json", "構造化データ(検索エンジン向け)"),
    ('rel="canonical"', "正規URL指定"),
    ("og:title", "SNSシェア用タイトル"),
]

# タイトルの末尾に付く、サイト側の決まり文句
# (「記事名｜大洲の自由研究｜ OZU LIFE MEMO」のように二段重ねになる)
# 公開URLのパス部分。404ページなどが絶対パスで書いている
SITE_BASE = "/ozu-life-memo/"

SITE_SUFFIXES = [
    "OZU LIFE MEMO",
    "大洲の自由研究",
    "大洲と読書",
    "大洲ノート",
    "大洲の歴史",
    "大洲検定",
    "大洲のとなり人",
]

# 個人を特定しうる語の一覧は、このリポジトリには置かない。
# リポジトリの外(private-notes/banned-words.py、.gitignore 済み)から読み込む。
# そのファイルが無い環境では匿名性チェックだけを飛ばし、他の点検は通常どおり動く。
BANNED = []
SUSPECT = []
ALLOW = []
_words = Path(__file__).resolve().parent.parent / "private-notes" / "banned-words.py"
if _words.exists():
    _ns = {}
    exec(compile(_words.read_text(encoding="utf-8"), str(_words), "exec"), _ns)
    BANNED = _ns.get("BANNED", [])
    SUSPECT = _ns.get("SUSPECT", [])
    ALLOW = _ns.get("ALLOW", [])      # 当たっても見逃してよい文字列(実在の地名など)

# 敬体(ですます調)の語尾。常体に統一する方針なので混在を警告する
KEITAI = [r"ました。", r"ています。", r"ません。", r"します。", r"です。", r"ます。"]

# 数か月で消えるので出典に使ってはいけないドメイン
FRAGILE_DOMAINS = ["news.yahoo.co.jp"]

# 記事1本あたりの目安
MIN_SOURCES = 2   # 出典は2本以上(本人の明示指示)
MIN_SOURCES_KENKYU = 12   # 自由研究は12本以上が方針(2026-08-19に確立)
MIN_H2 = 2        # 出典欄を除いた見出しの最低数
MIN_STRONG = 1    # 太字の最低数
MAX_KEITAI = 3    # 敬体の語尾がこれを超えたら混在を疑う

# 「取ってつけた呼びかけ」で締めない、というルールは前から文章では書いてあった。
# それでも147本中3本に生き残っていた。文章で頼むのをやめて、機械に持たせる。
NG_PHRASES = [
    (r"知ってほしい", "取ってつけた呼びかけ"),
    (r"知っておいてほしい", "取ってつけた呼びかけ"),
    (r"知っていただきたい", "取ってつけた呼びかけ"),
    (r"考えてみてほしい", "取ってつけた呼びかけ"),
    (r"感じてほしい", "取ってつけた呼びかけ"),
]

# 1文の目安は40〜50字。ここを超えるものは読点でつなぎすぎた長い文になっている。
# 既存記事の実測(2026-08-29)では150字超が17本。そこを上限にした。
MAX_SENTENCE = 150

# 冒頭の要点ボックスは3行(急いでいる読者が3行で帰れる形)
SUMMARY_LINES = 3

# タイトルに残してはいけない、行政資料の目次言葉。
# ただし「〜を中高生でも分かるように読み解く」のように、日常語に翻訳する約束が
# タイトル自体に書いてあるときは成立しているので見逃す。
TITLE_JARGON = ["策定", "財源内訳", "地域移行", "KPI", "CLT",
                "利活用", "推進計画", "基本構想", "実施要綱", "見える化"]
TITLE_JARGON_OK = ["分かる", "わかる", "読み解く", "かみくだ", "やさしく", "とは何か"]

# 予讃線は非電化。「電車」と書くと事実が違う(本人の明示指示)
NONDENKA = ("予讃線", "電車")


# ---------------------------------------------------------------------------
# 小さな道具
# ---------------------------------------------------------------------------

class Report:
    """見つけた問題をためておく入れ物"""

    def __init__(self):
        self.errors = []    # 直した方がよいもの
        self.warns = []     # 見て判断するもの
        self.section_status = {}

    def error(self, path, kind, message, detail=None):
        self.errors.append({"path": path, "kind": kind, "message": message, "detail": detail})

    def warn(self, path, kind, message, detail=None):
        self.warns.append({"path": path, "kind": kind, "message": message, "detail": detail})


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def strip_quotes(text: str) -> str:
    """引用符の中身を取り除く。

    「あの人は「そう思う」と言った」のように入れ子になっていると、
    単純な正規表現では外側が閉じられず除去に失敗する。内側から順に
    消して、変化がなくなるまで繰り返すことで入れ子に対応する。
    """
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r"「[^「」]*」", "", text)
        text = re.sub(r"『[^『』]*』", "", text)
    return text


def strip_tags(html: str) -> str:
    """HTMLタグと、script/styleの中身を取り除いて本文だけにする"""
    html = re.sub(r"<script\b.*?</script>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<style\b.*?</style>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    html = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", html)


def body_only(html: str) -> str:
    """<head>を除いた、実際に読者が読む部分だけを返す"""
    m = re.search(r"<body\b[^>]*>(.*)</body>", html, flags=re.S | re.I)
    return m.group(1) if m else html


def rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def page_type(path: Path) -> str:
    p = rel(path)
    if p.startswith("eachnews/"):
        return "article"
    if p.startswith("book/") and not p.endswith("/index.html"):
        return "book"
    if p.startswith("jiyu-kenkyu/") and not p.endswith("/index.html"):
        return "kenkyu"
    return "page"


def collect_pages() -> list[Path]:
    """点検対象のHTMLを集める(作業用ファイル・worktreeは除く)"""
    pages = []
    for p in REPO.rglob("*.html"):
        rp = p.relative_to(REPO).as_posix()
        # pr/ はSNS展開用の内部素材置き場(gitignore済み、GitHub Pagesに載らない)
        # tools/_gikai_cache/ は会議録のダウンロード置き場(記事ではない)
        if rp.startswith((".claude/", "node_modules/", "docs/", "pr/", "private-notes/", "tools/")):
            continue
        if p.name.startswith("_"):      # _measure.html などの検証用
            continue
        pages.append(p)
    return sorted(pages)


# ---------------------------------------------------------------------------
# 台帳(news-data.js)の読み取り
# ---------------------------------------------------------------------------

def load_registry() -> dict:
    """news-data.js から記事の一覧(slug と title)を取り出す"""
    js_path = REPO / "assets" / "js" / "news-data.js"
    if not js_path.exists():
        return {}
    js = read(js_path)

    records = {}
    current = None
    pattern = re.compile(r'(slug|title|date|category)\s*:\s*"((?:[^"\\]|\\.)*)"')
    for m in pattern.finditer(js):
        key, value = m.group(1), m.group(2)
        value = value.replace('\\"', '"').replace("\\\\", "\\")
        if key == "slug":
            current = {"slug": value}
            records[value] = current
        elif current is not None:
            current[key] = value
    return records


def load_sitemap() -> set:
    """sitemap.xml に載っているURLの一覧"""
    sm = REPO / "sitemap.xml"
    if not sm.exists():
        return set()
    return set(re.findall(r"<loc>\s*(.*?)\s*</loc>", read(sm)))


# ---------------------------------------------------------------------------
# 個々の点検
# ---------------------------------------------------------------------------

def source_urls(path, html) -> list:
    """そのページの出典URLを取り出す。書き方がページ種別で違う。

    記事(eachnews)・読書(book) … class="source-link" のリンク
    自由研究(jiyu-kenkyu)       … 脚注の <a href>(source-linkを使っていない)
    """
    body = body_only(html)
    if page_type(path) == "kenkyu":
        urls = re.findall(r'<a\s[^>]*href="(https?://[^"]+)"', body)
        return [u for u in dict.fromkeys(urls) if "ozulifememo" not in u]
    urls = re.findall(r'class="source-link"\s+href="(https?://[^"]+)"', body)
    return list(dict.fromkeys(urls))


def check_structure(path, html, rep):
    """必要な部品が揃っているか"""
    kind = page_type(path)
    required = list(CHROME_REQUIRED)
    if kind == "article":
        required += ARTICLE_REQUIRED
    elif kind in ("book", "kenkyu"):
        required += READING_REQUIRED

    for needle, label in required:
        if needle not in html:
            rep.error(rel(path), "構造", f"{label} が見当たりません", f"       探した文字列: {needle}")


def check_tag_balance(path, html, rep):
    """タグの開き閉じが合っているか"""
    body = body_only(html)
    # HTMLコメントの中のタグは、画面には出ないので数えない。
    # new_kiji.py が置く「段落は <p class="commentary">、見出しは <h2>」という
    # 書き置きを数えてしまい、本文が正しいのにエラーが出ていた(2026-08-31)。
    body = re.sub(r"<!--.*?-->", " ", body, flags=re.S)
    for tag in ("div", "h2", "strong", "section", "p"):
        opens = len(re.findall(rf"<{tag}\b", body, flags=re.I))
        closes = len(re.findall(rf"</{tag}>", body, flags=re.I))
        if opens != closes:
            rep.error(
                rel(path), "タグ",
                f"<{tag}> の開き{opens}個 と 閉じ{closes}個 が合っていません",
                "       レイアウトが崩れる原因になります",
            )


def check_titles(path, html, registry, rep):
    """タイトルが4か所(title / og:title / JSON-LD / h1)と台帳で一致しているか"""
    if page_type(path) not in ("article", "book", "kenkyu"):
        return

    def grab(pattern, flags=0):
        m = re.search(pattern, html, flags)
        return m.group(1).strip() if m else None

    suffix = "｜ OZU LIFE MEMO"

    def norm(s):
        """比較用にタイトルをそろえる。
        og:title は &quot; 、JSON-LD は \\" のように書き方が違うだけで
        中身は同じことが多いので、エスケープを元に戻してから比べる。"""
        if s is None:
            return None
        s = re.sub(r"<[^>]+>", "", s)
        # 「記事名｜大洲の自由研究｜ OZU LIFE MEMO」のように接尾辞が
        # 二段重ねになっていることがあるので、無くなるまで繰り返し取り除く
        changed = True
        while changed:
            changed = False
            for suffix in SITE_SUFFIXES:
                new = re.sub(rf"\s*[｜|]\s*{re.escape(suffix)}\s*$", "", s)
                if new != s:
                    s, changed = new, True
        # JSONのエスケープを戻す
        s = s.replace('\\"', '"').replace("\\\\", "\\").replace("\\/", "/")
        # HTMLの実体参照を戻す
        for ent, ch in [("&quot;", '"'), ("&#39;", "'"), ("&apos;", "'"),
                        ("&lt;", "<"), ("&gt;", ">"), ("&nbsp;", " "), ("&amp;", "&")]:
            s = s.replace(ent, ch)
        # 見た目が同じで区別しても意味のない記号をそろえる
        s = s.translate(str.maketrans('“”‘’＂＇', '""\'\'"\''))
        return re.sub(r"\s+", "", s).strip()

    t_title = norm(grab(r"<title>(.*?)</title>", re.S | re.I))
    t_og = norm(grab(r'<meta\s+property="og:title"\s+content="(.*?)"', re.S | re.I))
    t_ld = norm(grab(r'"headline"\s*:\s*"((?:[^"\\]|\\.)*)"', re.S))
    t_h1 = norm(grab(r"<h1[^>]*>(.*?)</h1>", re.S | re.I))

    found = {"<title>": t_title, "og:title": t_og, "JSON-LD": t_ld, "<h1>": t_h1}
    present = {k: v for k, v in found.items() if v}
    if len(set(present.values())) > 1:
        detail = "\n".join(f"       {k:10s}: {v}" for k, v in present.items())
        rep.error(rel(path), "タイトル", "ページ内でタイトルが食い違っています", detail)

    # 台帳(news-data.js)との照合は記事ページのみ
    if page_type(path) == "article":
        slug = path.stem
        rec = registry.get(slug)
        if rec is None:
            rep.error(rel(path), "台帳", "news-data.js にこの記事が登録されていません",
                      "       記事一覧・トップページに出てきません")
        else:
            reg_title = norm(rec.get("title"))
            if reg_title and t_h1 and reg_title != t_h1:
                rep.error(
                    rel(path), "タイトル", "記事本文と news-data.js のタイトルが違います",
                    f"       記事(h1) : {grab(r'<h1[^>]*>(.*?)</h1>', re.S | re.I)}\n"
                    f"       台帳     : {rec.get('title')}",
                )


def check_tables(path, html, rep):
    """記事内の<table>がスクロール用の囲いに入っているか。

    囲いが無い表は、スマホ幅で中身が入り切らないときにページ全体を
    横に突き破る(2026-08-20のブラウザ点検で9記事が実際にはみ出していた)。
    記事の表は <div style="overflow-x:auto;"> で包むのがこのサイトの決まり。
    共通クラス .article-table-wrap も同じ役割なので、こちらでもよい。
    """
    if page_type(path) not in ("article", "book", "kenkyu"):
        return
    body = body_only(html)
    for m in re.finditer(r"<table\b", body):
        before = body[max(0, m.start() - 250):m.start()]
        if "overflow-x" not in before and "article-table-wrap" not in before:
            line = html[:html.find(body) + m.start()].count("\n") + 1
            rep.error(rel(path), "表", f"スクロール用の囲いが無い表があります({line}行目付近)",
                      "       スマホで表がページ幅を突き破る原因になります。\n"
                      '       <div class="article-table-wrap"> で表を包んでください')
            break   # 1ファイル1件で十分


def check_anonymity(path, html, rep):
    """本文に個人が特定できる語が入っていないか"""
    text = strip_tags(body_only(html))

    for pattern, why in BANNED:
        for m in re.finditer(pattern, text):
            around = text[max(0, m.start() - 30): m.end() + 30]
            rep.error(rel(path), "匿名性", f"「{m.group(0)}」が本文にあります({why})",
                      f"       …{around}…")
            break   # 1ファイル1件で十分

    for pattern, why in SUSPECT:
        for m in re.finditer(pattern, text):
            around = text[max(0, m.start() - 30): m.end() + 30]
            rep.warn(rel(path), "匿名性", f"「{m.group(0)}」が本文にあります({why})",
                     f"       …{around}…")
            break


def check_mojibake(path, html, rep):
    """文字化けの痕跡がないか"""
    for m in re.finditer(r"[�]", html):
        around = html[max(0, m.start() - 40): m.end() + 40].replace("\n", " ")
        rep.error(rel(path), "文字化け", "文字化け記号が含まれています", f"       …{around}…")
        break
    # 実体参照の書き損じ(&amp;amp; のような二重エスケープ)
    if "&amp;amp;" in html:
        rep.warn(rel(path), "文字化け", "二重エスケープ(&amp;amp;)が含まれています")


def check_style(path, html, rep, show_headings=False):
    """note風スタイルの最低ラインを満たしているか"""
    kind = page_type(path)
    if kind not in ("article", "book", "kenkyu"):
        return

    body = body_only(html)

    # 出典欄の見出しは数えない
    h2_all = re.findall(r"<h2[^>]*>(.*?)</h2>", body, flags=re.S | re.I)
    h2_count = len([h for h in h2_all if "出典" not in h and "参考" not in h])
    strong_count = len(re.findall(r"<strong\b", body, flags=re.I))
    source_count = len(re.findall(r'class="source-link"', body))

    if kind == "kenkyu":
        n = len(source_urls(path, html))
        if n < MIN_SOURCES_KENKYU:
            rep.warn(rel(path), "出典", f"出典が{n}本です(自由研究は{MIN_SOURCES_KENKYU}本以上が方針)",
                     "       自由研究は調べ物の記録なので、記事より厚い裏取りを求めている")

    if kind == "article":
        if source_count < MIN_SOURCES:
            rep.error(rel(path), "出典", f"出典が{source_count}本しかありません(2本以上)",
                      "       1本だけだと、その1本が間違っていたら記事ごと崩れます")
        if h2_count < MIN_H2:
            rep.warn(rel(path), "スタイル", f"見出し(h2)が{h2_count}個しかありません")
        if strong_count < MIN_STRONG:
            rep.warn(rel(path), "スタイル", "太字(strong)が1つも使われていません")

    # 文体の統一。eachnews(大洲ノート)は常体、book(大洲と読書)は敬体が
    # それぞれの作法なので、常体チェックは eachnews だけに掛ける。
    if kind == "article":
        text = strip_tags(body)
        text = strip_quotes(text)   # 引用の中は数えない(人のコメントは敬体のまま)
        hits = sum(len(re.findall(k, text)) for k in KEITAI)
        if hits > MAX_KEITAI:
            rep.warn(rel(path), "文体", f"敬体(ですます調)の語尾が{hits}箇所あります",
                     "       大洲ノートは常体(〜だ/〜である)に統一する方針です")

    # 疑問形の見出しは「そこで答えを書く」という約束なので、答えが
    # 書かれているかを人が見る必要がある。ただし件数が多く毎回出すと
    # うるさいので、--headings を付けたときだけ一覧にする。
    if show_headings:
        for h in h2_all:
            plain = re.sub(r"<[^>]+>", "", h).strip()
            if re.search(r"(のか[?？]?|だろうか|でしょうか|[?？])$", plain):
                rep.warn(rel(path), "見出し", f"疑問形の見出し「{plain}」",
                         "       直後の段落が実際に答えになっているか、目で確認してください")


def check_phrasing(path, html, rep):
    """文章の作法。これまで文章のルールとしてしか無く、守られ方がまちまちだったもの"""
    kind = page_type(path)
    if kind not in ("article", "book"):
        return

    body = body_only(html)
    text = strip_tags(body)
    # 呼びかけの判定は、引用された他人の文章を除いた地の文だけで行う
    jibun = strip_quotes(text)

    # 取ってつけた呼びかけ
    for pattern, why in NG_PHRASES:
        m = re.search(pattern, jibun)
        if m:
            around = jibun[max(0, m.start() - 35): m.end() + 20]
            around = " ".join(around.split())
            rep.warn(rel(path), "表現", f"「{m.group(0)}」があります({why})",
                     f"       …{around}…\n"
                     "       本人が実際に感じたことで締める。呼びかけで締めない")
            break

    # 長すぎる1文
    worst, worst_len = "", 0
    for m in re.finditer(r"<p(?:\s[^>]*)?>(.*?)</p>", body, flags=re.S | re.I):
        para = strip_tags(m.group(1))
        for sent in re.split(r"(?<=。)", para):
            sent = sent.strip()
            # 句点で終わらないものは「文」ではない(時刻表や箇条書きの行)ので数えない
            if not sent.endswith("。"):
                continue
            if len(sent) > worst_len:
                worst, worst_len = sent, len(sent)
    if worst_len > MAX_SENTENCE:
        rep.warn(rel(path), "文章", f"1文が{worst_len}字あります(目安40〜50字)",
                 f"       {worst[:60]}…\n"
                 "       読点でつながず、途中で切って2文に分けてください")

    # 要点ボックスの行数
    m = re.search(r'<div class="article-summary".*?</ul>', body, flags=re.S)
    if m:
        lines = len(re.findall(r"<li", m.group(0)))
        if lines != SUMMARY_LINES:
            rep.warn(rel(path), "要点", f"冒頭の要点が{lines}行あります(3行が基本)",
                     "       核心の事実 / 裏付けの数字 / 読者への意味、の3行")

    # 予讃線は非電化
    if NONDENKA[0] in text and NONDENKA[1] in text:
        rep.warn(rel(path), "事実", "予讃線の記事に「電車」があります",
                 "       大洲を通る予讃線は非電化。「列車」が正しい")

    # タイトルに行政用語が残っていないか
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, flags=re.S)
    if h1 and kind == "article":
        title = strip_tags(h1.group(1)).strip()
        if not any(ok in title for ok in TITLE_JARGON_OK):
            for word in TITLE_JARGON:
                if word in title:
                    rep.warn(rel(path), "タイトル",
                             f"タイトルに行政用語「{word}」があります",
                             f"       {title}\n"
                             "       主語を制度ではなく読者の生活の出来事にする")
                    break


def check_links(path, html, rep):
    """画像とページ内リンクの行き先が実在するか"""
    body = body_only(html)
    # <script>の中はJavaScriptのテンプレート(${...})なので見ない
    body = re.sub(r"<script\b.*?</script>", " ", body, flags=re.S | re.I)

    def resolve(ref: str):
        ref = ref.split("#")[0].split("?")[0]
        if not ref:
            return None
        if ref.startswith(SITE_BASE):                 # 公開URLと同じ絶対パス
            return REPO / ref[len(SITE_BASE):]
        if ref.startswith("/"):
            return None                               # サイト外の絶対パス。見ない
        return path.parent / ref

    for tag, attr, label in (("img", "src", "画像"), ("a", "href", "リンク")):
        for ref in re.findall(rf'<{tag}[^>]+{attr}="([^"]+)"', body, flags=re.I):
            if ref.startswith(("http", "data:", "mailto:", "tel:", "#", "javascript:")):
                continue
            if "${" in ref or "' +" in ref or '" +' in ref:
                continue                              # 組み立て途中の文字列
            target = resolve(ref)
            if target is None:
                continue
            if not target.exists():
                rep.error(rel(path), label, f"{label}の行き先がありません: {ref}",
                          "       読者にはリンク切れ・画像切れとして見えます")


def check_title_numbers(path, html, rep):
    """タイトルに出した数字が、本文にもあるか

    タイトルだけ直して本文を直し忘れる(またはその逆)と、読者は
    「見出しの数字が本文にない」という一番不信感の出る形で気づく。
    """
    if page_type(path) != "article":
        return
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, flags=re.S)
    if not m:
        return
    title = strip_tags(m.group(1))
    body = strip_tags(body_only(html)).replace(",", "")
    for num in re.findall(r"\d[\d,]*(?:\.\d+)?", title):
        if num.replace(",", "") not in body:
            rep.error(rel(path), "タイトル",
                      f"タイトルの数字「{num}」が本文にありません",
                      f"       {title}\n"
                      "       タイトルだけ直して本文を直し忘れていないか確認してください")
            break


def check_sources(path, html, rep):
    """出典リンクの質(消えやすいドメインを使っていないか)"""
    for url in source_urls(path, html):
        # ウェブアーカイブ版は元URLを含むが、保存済みなので消えない。除外する。
        if url.startswith("https://web.archive.org/") or url.startswith("http://web.archive.org/"):
            continue
        for dom in FRAGILE_DOMAINS:
            if dom in url:
                rep.error(rel(path), "出典", f"消えやすいURLを出典にしています({dom})",
                          f"       {url}\n       官公庁・大学・企業の公式発表に差し替えてください")


def git_changed_pages() -> set:
    """gitから見て、いま手を入れているHTMLのパスを集める(フック用)"""
    import subprocess
    try:
        out = subprocess.run(["git", "status", "--porcelain"], cwd=str(REPO),
                             capture_output=True, text=True, encoding="utf-8",
                             timeout=20).stdout
    except Exception:
        return set()
    paths = set()
    for line in out.splitlines():
        if len(line) < 4:
            continue
        name = line[3:].strip().strip('"')
        if " -> " in name:          # リネームは移動先だけ見る
            name = name.split(" -> ")[-1]
        if name.endswith(".html"):
            paths.add(name)
    return paths


def check_repo_anonymity(rep):
    """リポジトリに入っている全テキストファイルに、個人が特定できる語が無いか。

    記事本文の検査(check_anonymity)は本文しか見ない。2026-08-29、道具が
    書き出した台帳(JSON)に名字が入ったままコミット・pushしてしまった。
    公開されるのは記事だけではない。git が追跡している全ファイルを見る。
    """
    import subprocess
    if not BANNED:
        return
    try:
        out = subprocess.run(["git", "ls-files"], cwd=str(REPO), capture_output=True,
                             text=True, encoding="utf-8", timeout=30).stdout
    except Exception:
        return
    skip_ext = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".ico", ".pdf",
                ".woff", ".woff2", ".ttf", ".xlsx", ".zip")
    for f in out.split("\n"):
        if not f or f.lower().endswith(skip_ext):
            continue
        path = REPO / f
        if page_type(path) in ("article", "book", "kenkyu"):
            continue                      # 記事本文は check_anonymity が見ている
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pattern, why in BANNED:
            for m in re.finditer(pattern, text):
                around = text[max(0, m.start() - 30): m.end() + 30]
                if any(a in around for a in ALLOW):
                    continue
                rep.error(f, "匿名性", f"「{m.group(0)}」が記事以外のファイルにあります({why})",
                          "       …" + " ".join(around.split()) + "…\n"
                          "       道具が書き出すファイルも公開されます")
                break


def check_registry_orphans(registry, pages, rep):
    """台帳にあるのにファイルが無い / ファイルがあるのに台帳に無い"""
    on_disk = {p.stem for p in pages if page_type(p) == "article"}
    for slug in registry:
        if slug not in on_disk:
            rep.error("assets/js/news-data.js", "台帳",
                      f"台帳にある「{slug}」のHTMLファイルがありません",
                      "       記事一覧からリンク切れになります")


def check_sitemap(pages, sitemap, rep):
    """sitemap.xml に載っていない公開ページがないか"""
    if not sitemap:
        return
    base = "https://ozulifememo.github.io/ozu-life-memo/"
    listed = {u.replace(base, "") for u in sitemap}
    for p in pages:
        r = rel(p)
        if page_type(p) not in ("article", "book", "kenkyu"):
            continue
        if r not in listed and r.replace("index.html", "") not in listed:
            rep.warn(r, "sitemap", "sitemap.xml に登録されていません",
                     "       Googleに見つけてもらえない可能性があります")


def check_urls(pages, rep, limit=None):
    """出典URLが生きているか実際に確認する(--urls のときだけ)"""
    import urllib.request
    import urllib.error

    urls = defaultdict(list)
    for p in pages:
        html = read(p)
        for url in source_urls(p, html):
            urls[url].append(rel(p))

    items = sorted(urls.items())
    if limit:
        items = items[:limit]

    print(f"\n  出典URL {len(items)}件の疎通を確認します(1件ずつ、少し時間がかかります)")
    dead = 0
    for i, (url, where) in enumerate(items, 1):
        if i % 20 == 0:
            print(f"    {i}/{len(items)} 件...")
        req = urllib.request.Request(url, method="HEAD", headers={
            "User-Agent": "Mozilla/5.0 (compatible; OzuLifeMemoLinkCheck/1.0)"
        })
        try:
            with urllib.request.urlopen(req, timeout=15) as res:
                code = res.status
        except urllib.error.HTTPError as e:
            code = e.code
        except Exception as e:
            code = f"接続失敗({type(e).__name__})"

        if isinstance(code, int) and code >= 400:
            dead += 1
            for w in where:
                rep.error(w, "リンク", f"出典URLが {code} を返します", f"       {url}")
        elif not isinstance(code, int):
            for w in where:
                rep.warn(w, "リンク", f"出典URLに接続できませんでした", f"       {url} / {code}")
        time.sleep(0.4)   # レート制限を避ける
    print(f"    完了。生きていないURL: {dead}件")


# ---------------------------------------------------------------------------
# 出力
# ---------------------------------------------------------------------------

def print_report(rep, pages, registry, elapsed):
    line = "=" * 68
    print()
    print(line)
    print(" OZU LIFE MEMO サイト点検")
    print(f" {datetime.now():%Y-%m-%d %H:%M}  /  対象 {len(pages)}ページ・記事{len(registry)}本"
          f"  /  {elapsed:.1f}秒")
    print(line)

    # 種類ごとの集計
    by_kind = defaultdict(lambda: [0, 0])
    for e in rep.errors:
        by_kind[e["kind"]][0] += 1
    for w in rep.warns:
        by_kind[w["kind"]][1] += 1

    order = ["構造", "タグ", "表", "タイトル", "台帳", "匿名性", "文字化け", "出典", "スタイル", "文体", "見出し", "sitemap", "リンク"]
    print()
    for kind in order:
        if kind not in by_kind and kind not in ("構造", "タイトル", "匿名性", "文字化け", "出典"):
            continue
        err, warn = by_kind.get(kind, (0, 0))
        if err:
            mark = f"エラー {err}件"
        elif warn:
            mark = f"警告 {warn}件"
        else:
            mark = "OK"
        dots = "." * max(2, 26 - len(kind) * 2)
        print(f"  【{kind}】{dots} {mark}")

    def dump(items, title, mark):
        if not items:
            return
        print()
        print("-" * 68)
        print(f" {mark} {title} ({len(items)}件)")
        print("-" * 68)
        grouped = defaultdict(list)
        for it in items:
            grouped[it["path"]].append(it)
        for path in sorted(grouped):
            print(f"\n{path}")
            for it in grouped[path]:
                print(f"  [{it['kind']}] {it['message']}")
                if it.get("detail"):
                    print(it["detail"])

    dump(rep.errors, "直した方がよいもの", "[NG]")
    dump(rep.warns, "見て判断するもの", "[! ]")

    print()
    print(line)
    if not rep.errors and not rep.warns:
        print(" 結果: 問題なし。きれいな状態です。")
    else:
        print(f" 結果: エラー {len(rep.errors)}件 / 警告 {len(rep.warns)}件")
        if not rep.errors:
            print("       エラーはゼロです。警告は直さなくても壊れません。")
    print(line)
    print()


# ---------------------------------------------------------------------------
# 自己診断(この点検スクリプト自体が壊れていないか確かめる)
# ---------------------------------------------------------------------------

BROKEN_SAMPLE = """<!DOCTYPE html>
<html lang="ja"><head>
<title>基本計画策定のタイトル ｜ OZU LIFE MEMO</title>
<link rel="canonical" href="x">
<meta property="og:title" content="基本計画策定のタイトル ｜ OZU LIFE MEMO">
<script type="application/ld+json">{"headline":"基本計画策定のタイトル"}</script>
</head><body>
<div data-site-header data-prefix="../"></div>
<h1>基本計画策定のタイトル</h1>
<div class="content-block">
  <a class="source-link" href="https://news.yahoo.co.jp/articles/xxxx" target="_blank">消えやすい出典</a>
</div>
<p>この記事にはダミー禁止語が入っています。文字化けもあります: �</p>
<p>予讃線の電車のことを、大洲に住んでいる人にも知ってほしい。</p>
<p><img src="../assets/img/この画像はない.jpg" alt="壊れた画像"></p>
<p><a href="../eachnews/このページはない.html">壊れたリンク</a></p>
<p>そしてこの一文は、読点でつなぎ続けることで、どこまでも長くなり、主語も述語も遠く離れ、読んでいる途中で何の話だったのか分からなくなり、それでもまだ終わらず、さらに例を並べ、括弧を挟み、注釈を足し、結局のところ二百字を超えてしまい、読み手はもう一度先頭に戻らなければならず、それでも意味が取れないまま次の段落へ進むことになる、そういう悪い見本として置いてある、とても長い一文である。</p>
<table><tr><td>スクロール用の囲いが無い表</td></tr></table>
<div>閉じていないdiv
<div data-site-footer="article"></div><div data-site-modal></div>
<script src="../assets/js/site-chrome.js"></script>
<script src="../assets/js/news-data.js"></script>
<script src="../assets/js/main.js"></script>
</body></html>
"""

BROKEN_REGISTRY = """const OZU_NEWS = [
  { slug: "broken", date: "2026-08-19", title: "台帳側のタイトル", category: "ima" },
  { slug: "yukue-fumei", date: "2026-08-19", title: "HTMLが存在しない記事", category: "ima" },
];
"""

# わざと壊したページから、必ず見つかってほしい項目
EXPECTED = [
    ("構造", "source-box"),
    ("構造", "要点3行"),
    ("構造", "読了時間"),
    ("構造", "photos-data.js"),
    ("構造", "article-related.js"),
    ("タグ", "div"),
    ("表", "囲い"),
    ("タイトル", "news-data.js"),
    ("匿名性", "ダミー禁止語"),
    ("文字化け", "文字化け"),
    ("出典", "1本"),
    ("出典", "news.yahoo.co.jp"),
    ("表現", "知ってほしい"),
    ("文章", "1文が"),
    ("事実", "電車"),
    ("タイトル", "策定"),
    ("画像", "行き先がありません"),
    ("リンク", "行き先がありません"),
    ("台帳", "yukue-fumei"),
]


def run_selftest() -> int:
    """わざと壊したページを作って、ちゃんと検知できるか確かめる。

    「点検してOKだった」が信用できるのは、この自己診断が通るときだけです。
    サイトの作りを変えたあとは、これを走らせて点検器が生きているか確認してください。
    """
    global REPO
    import tempfile

    print("\n  自己診断: わざと壊したページを作って、検知できるか試します...")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "eachnews").mkdir(parents=True)
        (root / "assets" / "js").mkdir(parents=True)
        (root / "eachnews" / "broken.html").write_text(BROKEN_SAMPLE, encoding="utf-8")
        (root / "assets" / "js" / "news-data.js").write_text(BROKEN_REGISTRY, encoding="utf-8")

        real_repo = REPO
        REPO = root
        try:
            pages = collect_pages()
            registry = load_registry()
            rep = Report()
            for p in pages:
                html = read(p)
                check_structure(p, html, rep)
                check_tag_balance(p, html, rep)
                check_tables(p, html, rep)
                check_titles(p, html, registry, rep)
                check_anonymity(p, html, rep)
                check_mojibake(p, html, rep)
                check_style(p, html, rep)
                check_phrasing(p, html, rep)
                check_links(p, html, rep)
                check_title_numbers(p, html, rep)
                check_sources(p, html, rep)
            check_registry_orphans(registry, pages, rep)
        finally:
            REPO = real_repo

    found = rep.errors + rep.warns
    missed = []
    for kind, needle in EXPECTED:
        hit = any(f["kind"] == kind and (needle in f["message"] or needle in (f.get("detail") or ""))
                  for f in found)
        mark = "OK " if hit else "NG "
        print(f"    [{mark}] {kind}: {needle}")
        if not hit:
            missed.append((kind, needle))

    print()
    if missed:
        print(f"  自己診断に失敗しました。{len(missed)}項目が検知できていません。")
        print("  点検スクリプトが壊れている可能性があります。OKという結果を信用しないでください。")
        return 1
    print(f"  自己診断OK。{len(EXPECTED)}項目すべて検知できました。点検結果は信用して大丈夫です。\n")
    return 0


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="OZU LIFE MEMO サイト点検スクリプト")
    ap.add_argument("--urls", action="store_true", help="出典URLの疎通も確認する(時間がかかる)")
    ap.add_argument("--url-limit", type=int, default=None, help="確認するURLの数を制限する")
    ap.add_argument("--slug", help="この記事だけ点検する(例: --slug ozu-mirai-note)")
    ap.add_argument("--headings", action="store_true",
                    help="疑問形の見出しを一覧にする(答えが書けているか目視するとき用)")
    ap.add_argument("--changed", action="store_true",
                    help="gitで変更のあったページだけ点検する(フックが使う)")
    ap.add_argument("--json", metavar="FILE", help="結果をJSONファイルに保存する")
    ap.add_argument("--selftest", action="store_true",
                    help="点検スクリプト自体が正しく動くか自己診断する")
    args = ap.parse_args()

    if args.selftest:
        return run_selftest()

    started = time.time()

    pages = collect_pages()
    registry = load_registry()
    sitemap = load_sitemap()

    if args.slug:
        pages = [p for p in pages if p.stem == args.slug]
        if not pages:
            print(f"「{args.slug}」というページが見つかりませんでした。")
            return 1

    if args.changed:
        changed = git_changed_pages()
        pages = [p for p in pages if rel(p) in changed]
        if not pages:
            print("\n  いま手を入れたページはありません。点検をとばします。\n")
            return 0

    rep = Report()

    for p in pages:
        html = read(p)
        check_structure(p, html, rep)
        check_tag_balance(p, html, rep)
        check_tables(p, html, rep)
        check_titles(p, html, registry, rep)
        check_anonymity(p, html, rep)
        check_mojibake(p, html, rep)
        check_style(p, html, rep, show_headings=args.headings)
        check_phrasing(p, html, rep)
        check_links(p, html, rep)
        check_title_numbers(p, html, rep)
        check_sources(p, html, rep)

    if not args.slug and not args.changed:
        check_registry_orphans(registry, pages, rep)
        check_repo_anonymity(rep)
    if not args.slug:
        check_sitemap(pages, sitemap, rep)

    if args.urls:
        check_urls(pages, rep, args.url_limit)

    elapsed = time.time() - started
    print_report(rep, pages, registry, elapsed)

    if args.json:
        # Notionとの突き合わせに使えるように、記事の中身の要約も一緒に出す
        articles = {}
        for p in pages:
            if page_type(p) != "article":
                continue
            html = read(p)
            body = body_only(html)
            articles[p.stem] = {
                "path": rel(p),
                "title": (re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S) or [None, ""])[1].strip(),
                "h2": [re.sub(r"<[^>]+>", "", h).strip()
                       for h in re.findall(r"<h2[^>]*>(.*?)</h2>", body, re.S)],
                "strong_count": len(re.findall(r"<strong\b", body)),
                "sources": re.findall(r'class="source-link"\s+href="([^"]+)"', body),
            }
        out = {
            "generated": datetime.now().isoformat(timespec="seconds"),
            "pages_checked": len(pages),
            "errors": rep.errors,
            "warnings": rep.warns,
            "articles": articles,
        }
        Path(args.json).write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  JSONを保存しました: {args.json}\n")

    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
