# -*- coding: utf-8 -*-
"""記事に「メモうの吹き出し」を入れる/差し替える。

置くものは2種類ある。

- 冒頭の吹き出し(.memou-intro)
  すぐ下の要点ボックスが「事実の圧縮」なのに対し、こちらは「本文の翻訳」。
  制度名・法律名・会計用語を使わず、話し言葉で2〜3文。数字は多くても1つ。

- 途中の踊り場(.memou-aside)
  長い記事の折返しに1回だけ置く合いの手。冒頭と同じ形にすると
  2回目の導入に見えるので、しっぽも名前も付けない帯にしている。1記事1回まで。

使い方:
    python tools/apply_memou.py                 # 台帳どおりに全部反映する
    python tools/apply_memou.py --check         # 判定だけ表示して何も書き換えない
    python tools/apply_memou.py --slug xxx      # 1本だけ反映する

文章は tools/memou-ledger.json に持つ。書き換えるのはそちら。
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
NEWS = ROOT / "eachnews"
LEDGER = ROOT / "tools" / "memou-ledger.json"

# 吹き出しを付ける目安。語彙の難しさではなく、話の層の多さ(=長さ)が
# 読者の負担になっていたため、専門用語の数ではなく字数で測っている。
THRESHOLD_CHARS = 2000

# 踊り場を置く目安。これ未満の記事に入れると本文のリズムが壊れる。
ASIDE_MIN_CHARS = 5000
ASIDE_MIN_HEADS = 5

FACES = {
    "futsuu": "memou.svg",
    "odoroki": "memou-odoroki.svg",
    "naruhodo": "memou-naruhodo.svg",
    "hatena": "memou-hatena.svg",
    "hirameki": "memou-hirameki.svg",
    "nikkori": "memou-nikkori.svg",
    "komatta": "memou-komatta.svg",
    "majime": "memou-majime.svg",
    "atsui": "memou-atsui.svg",
    "muchu": "memou-muchu.svg",
}

INTRO = """    <div class="memou-intro">
      <div class="memou-intro-figure">
        <img src="../assets/img/{svg}" alt="" class="memou-intro-avatar" width="84" height="84" decoding="async">
        <span class="memou-intro-name">メモう</span>
      </div>
      <div class="memou-intro-bubble">
{paras}
      </div>
    </div>

"""

ASIDE = """    <div class="memou-aside">
      <img src="../assets/img/{svg}" alt="" class="memou-aside-avatar" width="54" height="54" decoding="async">
      <p>{text}</p>
    </div>

"""

INTRO_MARK = re.compile(
    r'[ \t]*<div class="memou-intro">.*?<div class="memou-intro-bubble">.*?</div>\s*</div>[ \t]*\n[ \t]*\n?',
    re.S,
)
ASIDE_MARK = re.compile(
    r'[ \t]*<div class="memou-aside">.*?</div>[ \t]*\n[ \t]*\n?',
    re.S,
)
SUMMARY = re.compile(r'[ \t]*<div class="article-summary">')
H2 = re.compile(r'[ \t]*<h2')


def body_len(html):
    """本文のおおよその文字数。タグ・出典欄・スクリプトを除いて数える。"""
    t = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S)
    t = re.sub(r'<div class="content-block source-box".*', " ", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    return len(re.sub(r"\s+", "", t))


def apply_intro(path, text, face):
    html = INTRO_MARK.sub("", path.read_text(encoding="utf-8"))
    m = SUMMARY.search(html)
    if not m:
        return "要点ボックスが無い"
    paras = [p.strip() for p in text.strip().split("\n") if p.strip()]
    block = INTRO.format(
        svg=FACES.get(face, "memou.svg"),
        paras="\n".join("        <p>" + p + "</p>" for p in paras),
    )
    path.write_text(html[: m.start()] + block + html[m.start():], encoding="utf-8")
    return "ok"


def apply_aside(path, text, face, before=None):
    """折返しの見出しの直前に、帯を1つだけ置く。

    before に見出しの一部を渡すと、その見出しの直前に置く。
    渡さなければ見出しの数の真ん中。

    before を足したのは2026-09-06。踊り場の文は
    「ここまでが○○の話。ここからは△△の話。」という形で、特定の切れ目の
    ために書かれているのに、置き場所が見出しの番号で決まっていたため、
    記事に節を足すと黙って別の切れ目へ滑っていた。
    """
    html = ASIDE_MARK.sub("", path.read_text(encoding="utf-8"))
    heads = [m.start() for m in H2.finditer(html)]
    if len(heads) < ASIDE_MIN_HEADS:
        return "見出しが" + str(len(heads)) + "個しかない"
    at = heads[len(heads) // 2]
    if before:
        # H2 は「<h2」の位置しか掴まないので、見出しの中身は別に読む。
        # 見出しには kaigyo.py が入れた <span class="nb"> が混ざるため、
        # タグを外してから照合する
        hit = []
        for m in H2.finditer(html):
            end = html.find("</h2>", m.start())
            if end < 0:
                continue
            label = re.sub(r"<[^>]+>", "", html[m.start():end])
            if before in label:
                hit.append(m.start())
        if not hit:
            return "before に書いた見出し「" + before + "」が本文にない"
        at = hit[0]
    lines = [x.strip() for x in text.strip().split("\n") if x.strip()]
    block = ASIDE.format(svg=FACES.get(face, "memou.svg"), text="<br>".join(lines))
    path.write_text(html[:at] + block + html[at:], encoding="utf-8")
    return "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="判定だけ表示する")
    ap.add_argument("--slug", help="1本だけ処理する")
    args = ap.parse_args()

    ledger = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else {}
    files = sorted(NEWS.glob("*.html"))

    if args.check:
        need = has = aside_need = 0
        missing = []
        for f in files:
            html = f.read_text(encoding="utf-8")
            n = body_len(html)
            entry = ledger.get(f.stem)
            if entry:
                has += 1
            if n >= THRESHOLD_CHARS:
                need += 1
                if not entry:
                    missing.append((n, f.stem))
            if n >= ASIDE_MIN_CHARS and len(H2.findall(html)) >= ASIDE_MIN_HEADS:
                aside_need += 1
        print("記事 " + str(len(files)) + " 本")
        print("  吹き出しの目安 " + format(THRESHOLD_CHARS, ",") + "字以上 : " + str(need) + " 本")
        print("  実際に台帳にある : " + str(has) + " 本")
        print("  踊り場の目安 " + format(ASIDE_MIN_CHARS, ",") + "字＋見出し"
              + str(ASIDE_MIN_HEADS) + "個 : " + str(aside_need) + " 本")
        if missing:
            print("\n--- 対象だが未作成 (" + str(len(missing)) + "本) ---")
            for n, slug in sorted(missing, reverse=True):
                print("  " + format(n, "6,") + "字  " + slug)
        return

    done = aside_done = ng = 0
    for slug, entry in sorted(ledger.items()):
        if args.slug and slug != args.slug:
            continue
        f = NEWS / (slug + ".html")
        if not f.exists():
            print("  [!] ファイルが無い: " + slug)
            ng += 1
            continue
        r = apply_intro(f, entry["bubble"], entry.get("face", "futsuu"))
        if r != "ok":
            print("  [!] " + slug + ": " + r)
            ng += 1
        else:
            done += 1
        a = entry.get("aside")
        if a:
            r2 = apply_aside(f, a["text"], a.get("face", "futsuu"), a.get("before"))
            if r2 != "ok":
                print("  [!] " + slug + " の踊り場: " + r2)
                ng += 1
            else:
                aside_done += 1
    print("吹き出し " + str(done) + " 本 / 踊り場 " + str(aside_done)
          + " 本 / 問題 " + str(ng) + " 件")


if __name__ == "__main__":
    main()
