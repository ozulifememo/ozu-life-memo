# -*- coding: utf-8 -*-
"""レビュー卓の記事案に足した「★お気に入り」を、本物のブラウザで動かして確かめる。

2026-09-13、本人の指示。

> 記事案に、星マークのお気に入りをつけたい、
> お気に入りにしているものから優先的に記事にしていく

◯✕とは別の軸である。◯は「書いてよい」、★は「これを先に書いてほしい」。
だから★は判定が無くても付けられるし、付けたら消えずに残らないといけない。
(判定もメモも無い行は捨てる作りになっていたので、そこを直してある)

    python tools/test_review_star.py
"""
import sys
import pathlib
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SITE = pathlib.Path(__file__).resolve().parent.parent
URL = (SITE / "_review.html").as_uri()
ok = fail = 0
errs = []


def check(name, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print("  OK  ", name, extra)
    else:
        fail += 1
        print("  NG  ", name, extra)


with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={"width": 1280, "height": 900})
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)
    pg.goto(URL, wait_until="load", timeout=180000)
    pg.wait_for_timeout(2500)

    pg.evaluate("F.kind='idea';sync('#fKind','k','idea');refresh()")
    pg.wait_for_timeout(600)

    # ---- 見た目があるか
    check("★の列が出る", pg.locator("#itTable th.st").count() == 1)
    check("★だけの釦がある", pg.is_visible("#itFavOnly"))
    check("最初は★0件", pg.inner_text("#itFav") == "0", pg.inner_text("#itFav"))
    check("行ごとに☆がある", pg.locator("tr.r:not(.mine) .itStar").count() > 0,
          pg.locator("tr.r:not(.mine) .itStar").count())

    # ---- クロコが出した案に★を付ける
    row = pg.locator("tr.r:not(.mine)").first
    slug = row.get_attribute("data-s")
    row.locator(".itStar").click()
    pg.wait_for_timeout(500)
    check("☆が★になった", pg.locator("tr.r[data-s='%s'] .itStar" % slug).inner_text() == "★",
          pg.locator("tr.r[data-s='%s'] .itStar" % slug).inner_text())
    check("釦に印が付く", "on" in (pg.locator("tr.r[data-s='%s'] .itStar" % slug)
                              .get_attribute("class") or ""))
    check("行に印が付く", "fav" in (pg.locator("tr.r[data-s='%s']" % slug)
                              .get_attribute("class") or ""))
    check("控えに残る", pg.evaluate("!!(S['%s']||{}).f" % slug))
    check("数が1になった", pg.inner_text("#itFav") == "1", pg.inner_text("#itFav"))

    # ★だけの行は、判定もメモも無い。捨てられずに残るか(いちばん壊れやすいところ)
    check("判定は空のまま", (pg.evaluate("(S['%s']||{}).v" % slug) or "") == "",
          repr(pg.evaluate("(S['%s']||{}).v" % slug)))

    # ---- 自分の案にも付く
    pg.click("#itAdd")
    pg.wait_for_timeout(400)
    pg.locator("tr.r.mine .myIn").first.type("★のテスト用に書いた案", delay=5)
    pg.wait_for_timeout(900)
    mid = pg.evaluate("Object.keys(MY)[0]")
    pg.locator("tr.r.mine[data-mid='%s'] .itStar" % mid).click()
    pg.wait_for_timeout(500)
    check("自分の案にも★が付く", pg.evaluate("!!MY['%s'].f" % mid))
    check("数が2になった(合算)", pg.inner_text("#itFav") == "2", pg.inner_text("#itFav"))
    check("★を付けても未読のまま",
          pg.inner_text("tr.r.mine[data-mid='%s'] .myState" % mid) == "クロコ未読",
          pg.inner_text("tr.r.mine[data-mid='%s'] .myState" % mid))

    # ---- ★だけで絞る
    allrows = pg.locator("tr.r").count()
    pg.click("#itFavOnly")
    pg.wait_for_timeout(500)
    check("★だけで絞れた", pg.locator("tr.r").count() == 2, pg.locator("tr.r").count())
    check("釦が押された形になる", "on" in (pg.locator("#itFavOnly").get_attribute("class") or ""))
    check("★無しの行は消える", pg.locator("tr.r").count() < allrows,
          "%d → %d" % (allrows, pg.locator("tr.r").count()))
    pg.click("#itFavOnly")
    pg.wait_for_timeout(500)
    check("もう一度押すと戻る", pg.locator("tr.r").count() == allrows,
          pg.locator("tr.r").count())

    # ---- まとまりの中で、★が上に来るか
    #      3つ以上ある「まとまり」を選んで、いちばん下に★を付けて並べ直す
    target = pg.evaluate("""() => {
      const cnt = {};
      for (let i = 0; i < N; i++) if (A[i].kind === 'idea') cnt[A[i].cat] = (cnt[A[i].cat]||0)+1;
      const cat = Object.keys(cnt).find(c => cnt[c] >= 3);
      if (!cat) return null;
      const list = [];
      for (let i = 0; i < N; i++) if (A[i].kind === 'idea' && A[i].cat === cat) list.push(A[i].slug);
      return {cat: cat, last: list[list.length - 1], first: list[0]};
    }""")
    check("3件以上のまとまりがある", target is not None, (target or {}).get("cat"))
    if target:
        pg.locator("tr.r[data-s='%s'] .itStar" % target["last"]).click()
        pg.wait_for_timeout(500)
        pg.evaluate("renderIdeaTable()")
        pg.wait_for_timeout(400)
        # そのまとまりの表示順を取り出して、★付きが★無しより前に並んでいるかを見る。
        # 「★を付けたものが1位」ではないことに注意。同じまとまりに★が2つあれば
        # もとの順が保たれるので、位置ではなく**順序の規則**のほうを検査する。
        seq = pg.evaluate("""(cat) => {
          const rows = [...document.querySelectorAll('#itBody tr')];
          const gi = rows.findIndex(r => r.classList.contains('grp')
                                      && !r.classList.contains('mygrp')
                                      && r.textContent.trim() === cat);
          const out = [];
          for (let i = gi + 1; i < rows.length; i++) {
            if (rows[i].classList.contains('grp')) break;
            if (rows[i].dataset.s) out.push([rows[i].dataset.s,
                                             rows[i].classList.contains('fav')]);
          }
          return out;
        }""", target["cat"])
        favs = [s for s, f in seq if f]
        lastfav = max([k for k, (s, f) in enumerate(seq) if f], default=-1)
        firstplain = min([k for k, (s, f) in enumerate(seq) if not f], default=len(seq))
        check("★を付けたものが、そのまとまりに入っている", target["last"] in favs,
              "%s / ★=%s" % (target["last"], favs))
        check("★付きが★無しより前に並ぶ", lastfav < firstplain,
              "★の最後=%d / ★無しの最初=%d" % (lastfav, firstplain))

    # ---- 自分の案は★付きが上
    pg.click("#itAdd")
    pg.wait_for_timeout(400)
    pg.locator("tr.r.mine .myIn").first.type("あとから書いた星なしの案", delay=5)
    pg.wait_for_timeout(900)
    pg.evaluate("renderIdeaTable()")
    pg.wait_for_timeout(300)
    check("自分の案も★が上",
          pg.locator("tr.r.mine").first.get_attribute("data-mid") == mid,
          pg.locator("tr.r.mine").first.get_attribute("data-mid"))

    # ---- ◯✕とメモを壊していないか
    row2 = pg.locator("tr.r:not(.mine)").nth(1)
    slug2 = row2.get_attribute("data-s")
    row2.locator(".itB[data-v='ok']").click()
    pg.wait_for_timeout(500)
    check("◯がまだ効く", pg.evaluate("(S['%s']||{}).v" % slug2) == "ok",
          pg.evaluate("(S['%s']||{}).v" % slug2))
    row2.locator("textarea").type("★を足したあとのメモ", delay=5)
    pg.wait_for_timeout(900)
    check("メモがまだ効く", "★を足した" in (pg.evaluate("(S['%s']||{}).m" % slug2) or ""))

    # ---- 開き直しても★が残るか
    pg.reload(wait_until="load", timeout=180000)
    pg.wait_for_timeout(2500)
    pg.evaluate("F.kind='idea';sync('#fKind','k','idea');refresh()")
    pg.wait_for_timeout(600)
    check("開き直しても★が残る", pg.evaluate("!!(S['%s']||{}).f" % slug))
    check("自分の案の★も残る", pg.evaluate("!!MY['%s'].f" % mid))
    check("数も戻る", pg.inner_text("#itFav") == "3", pg.inner_text("#itFav"))

    # ---- ★を外せるか
    pg.locator("tr.r[data-s='%s'] .itStar" % slug).click()
    pg.wait_for_timeout(500)
    check("★を外せる", not pg.evaluate("!!(S['%s']||{}).f" % slug))
    check("☆に戻る", pg.locator("tr.r[data-s='%s'] .itStar" % slug).inner_text() == "☆",
          pg.locator("tr.r[data-s='%s'] .itStar" % slug).inner_text())
    check("数が減る", pg.inner_text("#itFav") == "2", pg.inner_text("#itFav"))

    # ---- 記事の画面が壊れていないか
    pg.evaluate("F.kind='';sync('#fKind','k','');refresh()")
    pg.wait_for_timeout(500)
    check("記事の画面に戻れる", pg.is_visible("#paper") and not pg.is_visible("#itWrap"))

    br.close()

print()
if errs:
    print("ページのエラー:")
    for e in errs[:10]:
        print("  ", e[:200])
print("OK %d / NG %d / エラー %d" % (ok, fail, len(errs)))
sys.exit(1 if (fail or errs) else 0)
