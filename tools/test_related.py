# -*- coding: utf-8 -*-
"""関連記事の出し方を、本物のブラウザで確かめる。"""
import sys, pathlib
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SITE = pathlib.Path(__file__).resolve().parent.parent
import tempfile, os
SHOT = pathlib.Path(tempfile.gettempdir()) / "ozu-related-shots"
os.makedirs(SHOT, exist_ok=True)
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


PAGES = ["gouu-bosai", "akiya-taisaku-keikaku", "michi-ijihi", "ozu-shakyo-kessan",
         "ozu-okashi-shigure", "bukatsu-chiiki-ido"]

with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={"width": 1280, "height": 900})
    pg.on("pageerror", lambda e: errs.append(str(e)))
    # アクセス解析(gc.zgo.at)はプロトコル相対のURLなので、file:// で開くと必ず失敗する。
    # 本物のサイト(https)では読めるので、ここでは数えない。
    pg.on("console", lambda m: errs.append("console:" + m.text)
          if (m.type == "error" and "ERR_FILE_NOT_FOUND" not in m.text) else None)

    seen = {}
    for slug in PAGES:
        pg.goto((SITE / "eachnews" / (slug + ".html")).as_uri(), wait_until="load")
        pg.wait_for_timeout(700)
        items = pg.eval_on_selector_all(
            "#related-list-items li",
            "els=>els.map(e=>({why:(e.querySelector('.rwhy')||{}).textContent||'',"
            "title:(e.querySelector('a')||{}).textContent||'',"
            "href:(e.querySelector('a')||{}).getAttribute('href')||''}))")
        print("\n[%s]" % slug)
        for it in items:
            print("   %-8s %s" % (it["why"], it["title"][:44]))
        check("  6本出る", len(items) == 6, len(items))
        check("  理由の言葉が全部に付く", all(i["why"] for i in items))
        check("  リンクが1つ上の階層から始まる",
              all(i["href"].startswith("../") for i in items),
              [i["href"] for i in items][:2])
        check("  自分自身は入っていない", all(slug + ".html" not in i["href"] for i in items))
        seen[slug] = [i["href"] for i in items]

    # 記事ごとに顔ぶれが違うか(これが今回の目的)
    import itertools
    worst = 0
    for a, b in itertools.combinations(PAGES, 2):
        same = len(set(seen[a]) & set(seen[b]))
        worst = max(worst, same)
    check("どの2本を比べても顔ぶれが3本以上かぶらない", worst < 3, "最大かぶり %d本" % worst)

    # リンク先が実在するか
    import os
    missing = []
    for slug, hrefs in seen.items():
        for h in hrefs:
            t = (SITE / "eachnews" / h).resolve()
            if not t.exists():
                missing.append(h)
    check("リンク先のファイルが実在する", not missing, missing[:3])

    # 理由の言葉が、行き先の記事の本文に本当に出てくるか(でっち上げの防止)
    import re
    bad = []
    for slug in PAGES:
        pg.goto((SITE / "eachnews" / (slug + ".html")).as_uri(), wait_until="load")
        pg.wait_for_timeout(500)
        items = pg.eval_on_selector_all(
            "#related-list-items li",
            "els=>els.map(e=>[(e.querySelector('.rwhy')||{}).textContent||'',"
            "(e.querySelector('a')||{}).getAttribute('href')||''])")
        src = open(SITE / "eachnews" / (slug + ".html"), encoding="utf-8").read()
        for why, href in items:
            dst = open((SITE / "eachnews" / href).resolve(), encoding="utf-8").read()
            if why and (why not in src or why not in dst):
                bad.append((slug, why, href))
    check("理由の言葉が、両方の記事の本文に実在する", not bad, bad[:3])

    # 画面の見え方(狭い画面で横に溢れないか)
    sp = br.new_page(viewport={"width": 390, "height": 844})
    sp.goto((SITE / "eachnews" / "gouu-bosai.html").as_uri(), wait_until="load")
    sp.wait_for_timeout(600)
    check("狭い画面で横スクロールしない",
          sp.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"),
          sp.evaluate("document.documentElement.scrollWidth"))
    sp.locator("#related-list-items").scroll_into_view_if_needed()
    sp.screenshot(path=str(SHOT / "related-390.png"))
    pg.goto((SITE / "eachnews" / "gouu-bosai.html").as_uri(), wait_until="load")
    pg.wait_for_timeout(600)
    pg.locator("#related-list-items").scroll_into_view_if_needed()
    pg.screenshot(path=str(SHOT / "related-1280.png"))

    br.close()

print()
if errs:
    print("ページのエラー:")
    for e in errs[:8]:
        print("  ", e[:200])
print("OK %d / NG %d / エラー %d" % (ok, fail, len(errs)))
sys.exit(1 if fail else 0)
