# -*- coding: utf-8 -*-
"""レビュー卓に足した「自分が思いついた案」を、本物のブラウザで動かして確かめる。"""
import sys, pathlib
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

    # 記事案の画面へ
    pg.evaluate("F.kind='idea';sync('#fKind','k','idea');refresh()")
    pg.wait_for_timeout(600)
    check("記事案の表が出る", pg.is_visible("#itWrap"))
    check("＋ボタンがある", pg.is_visible("#itAdd"))
    check("最初は0件", pg.inner_text("#itMine") == "0", pg.inner_text("#itMine"))
    check("空の案内が出る", "まだありません" in pg.inner_text("tr.mygrp"))

    # 1件足す
    pg.click("#itAdd")
    pg.wait_for_timeout(400)
    check("行が1つ増えた", pg.locator("tr.r.mine").count() == 1)
    check("数が1になった", pg.inner_text("#itMine") == "1", pg.inner_text("#itMine"))
    check("題の欄に入力できる状態", pg.evaluate("document.activeElement.className") == "myIn",
          pg.evaluate("document.activeElement.className"))

    pg.locator("tr.r.mine .myIn").type("大洲の床屋の値段を全部並べる", delay=5)
    pg.locator("tr.r.mine textarea").type("散髪代って店で違うの？ 妻に聞かれた", delay=5)
    pg.wait_for_timeout(900)

    mid = pg.evaluate("Object.keys(MY)[0]")
    check("題が保存された", "床屋" in pg.evaluate("MY['%s'].t" % mid), pg.evaluate("MY['%s'].t" % mid))
    check("中身が保存された", "散髪代" in pg.evaluate("MY['%s'].m" % mid))
    check("クロコ未読になっている", pg.inner_text("tr.r.mine .myState") == "クロコ未読",
          pg.inner_text("tr.r.mine .myState"))

    # もう1件足すと、新しいほうが上に来る
    pg.click("#itAdd")
    pg.wait_for_timeout(400)
    pg.locator("tr.r.mine .myIn").first.type("あとから書いた案", delay=5)
    pg.wait_for_timeout(900)
    check("2件になった", pg.inner_text("#itMine") == "2", pg.inner_text("#itMine"))
    check("新しいほうが上", "あとから" in pg.locator("tr.r.mine .myIn").first.input_value())

    # クロコが返事を書いた形にして、表示を確かめる
    pg.evaluate("MY['%s'].done=true;MY['%s'].re='いい案です。市の許可の一覧から調べられます';"
                "mySaveLocal();renderIdeaTable();paintIdeaCount()" % (mid, mid))
    pg.wait_for_timeout(300)
    txt = pg.inner_text("tr.r.mine[data-mid='%s']" % mid)
    check("クロコの返事が出る", "いい案です" in txt)
    check("見たの印が付く", "クロコが見た" in txt)

    # 書き換えると「未読」に戻る
    pg.locator("tr.r.mine[data-mid='%s'] textarea" % mid).type("追記：値段だけでなく待ち時間も", delay=5)
    pg.wait_for_timeout(900)
    check("直したら未読に戻る",
          pg.inner_text("tr.r.mine[data-mid='%s'] .myState" % mid) == "クロコ未読",
          pg.inner_text("tr.r.mine[data-mid='%s'] .myState" % mid))

    # クロコが出した案のメモ欄は、今までどおり動くか(壊していないかの確認)
    row = pg.locator("tr.r:not(.mine)").first
    slug = row.get_attribute("data-s")
    row.locator("textarea").type("これは元からある案へのメモ", delay=5)
    pg.wait_for_timeout(900)
    check("元の記事案のメモは無事", "元からある" in (pg.evaluate("(S['%s']||{}).m" % slug) or ""),
          (pg.evaluate("(S['%s']||{}).m" % slug) or "")[:20])

    # 探す欄で自分の案も絞れるか
    pg.fill("#itQ", "床屋")
    pg.wait_for_timeout(500)
    check("探すと自分の案も当たる", pg.locator("tr.r.mine").count() == 1,
          pg.locator("tr.r.mine").count())
    pg.fill("#itQ", "")
    pg.wait_for_timeout(500)

    # 消す
    pg.on("dialog", lambda d: d.accept())
    pg.locator("tr.r.mine[data-mid='%s'] .myDel" % mid).click()
    pg.wait_for_timeout(500)
    check("消せた", pg.inner_text("#itMine") == "1", pg.inner_text("#itMine"))

    # 開き直しても残るか
    pg.reload(wait_until="load", timeout=180000)
    pg.wait_for_timeout(2500)
    check("開き直しても残る", pg.evaluate("Object.keys(MY).length") == 1,
          pg.evaluate("Object.keys(MY).length"))

    # 記事を読む画面が壊れていないか
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
