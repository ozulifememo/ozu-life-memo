#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OZU LIFE MEMO ブラウザ実機点検スクリプト
==========================================

check_site.py が「HTMLの文字列」を見るのに対して、こちらは実際にブラウザ
(Chromium)で全ページを開いて「表示された結果」を点検します。

見つけられるもの(check_site.pyでは見つけられないもの):
- 画像が読み込めず壊れて見える箇所(404など)
- 文字や表が画面幅からはみ出す箇所(スマホ2種+PCの3画面幅で確認)
- ブラウザのコンソールに出るJavaScriptエラー
- スマホで指では押しづらい小さなボタン(24px未満)

使い方(初回のみ: pip install playwright && playwright install chromium):

    python tools/check_browser.py

数分かかります。ローカルサーバーは自動で立てて、終わったら自動で止めます。
ファイルは一切書き換えません。

【重要】アクセス解析(GoatCounter)への通信は必ずブロックしています。
これが無いと、点検のたびに約500ページビューが本物のアクセス統計に
記録されてしまいます。ブロックの副作用として、全ページのコンソールに
「Failed to load resource: net::ERR_FAILED」が1件ずつ出ますが、
これは点検側の痕跡なので無視して構いません(集計からも除外済み)。
"""

import asyncio
import socket
import subprocess
import sys
import time
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Playwrightが入っていません。次を実行してください:")
    print("  pip install playwright")
    print("  playwright install chromium")
    sys.exit(1)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
PORT = 8137
BASE = f"http://127.0.0.1:{PORT}/"
SKIP_DIRS = {".claude", ".git", "docs", "private-notes", "node_modules", "tools"}

# アクセス解析を汚さないためのブロック対象
BLOCK_HOSTS = ("goatcounter.com", "gc.zgo.at", "zgo.at")

VIEWPORTS = {
    "スマホ(375px)": dict(viewport={"width": 375, "height": 812}, device_scale_factor=2,
                          is_mobile=True, has_touch=True),
    "小型スマホ(320px)": dict(viewport={"width": 320, "height": 690}, device_scale_factor=2,
                              is_mobile=True, has_touch=True),
    "PC(1366px)": dict(viewport={"width": 1366, "height": 900}),
}

CHECK_JS = r"""
(isMobile) => {
  const out = {};
  out.brokenImgs = [...document.images]
    .filter(i => i.complete && i.naturalWidth === 0 && i.getAttribute('src'))
    .map(i => i.getAttribute('src'));
  const de = document.documentElement;
  const cw = de.clientWidth;
  out.hOverflow = de.scrollWidth > cw + 1;
  out.offenders = [];
  if (out.hOverflow) {
    const seen = new Set();
    for (const el of document.querySelectorAll('body *')) {
      const r = el.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) continue;
      const st = getComputedStyle(el);
      if (st.display === 'none' || st.visibility === 'hidden') continue;
      if (r.right > cw + 2 || r.left < -2) {
        let p = el.parentElement, skip = false;
        while (p) { if (seen.has(p)) { skip = true; break; } p = p.parentElement; }
        if (skip) continue;
        seen.add(el);
        const cls = (typeof el.className === 'string' ? el.className : '').trim().split(/\s+/).slice(0,2).join('.');
        out.offenders.push(el.tagName.toLowerCase() + (cls ? '.'+cls : ''));
        if (out.offenders.length >= 5) break;
      }
    }
  }
  out.smallTargets = [];
  if (isMobile) {
    const sels = 'button, .cta-btn, .news-tab, .tag-chip, .home-tab, .map-tab, .poster-btn, .form-btn, .nav-toggle, .modal-close';
    for (const el of document.querySelectorAll(sels)) {
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) continue;
      const st = getComputedStyle(el);
      if (st.display === 'none' || st.visibility === 'hidden') continue;
      if (r.width < 24 || r.height < 24) {
        const cls = (typeof el.className === 'string' ? el.className : '').trim().split(/\s+/).slice(0,2).join('.');
        out.smallTargets.push(el.tagName.toLowerCase() + (cls ? '.'+cls : '') +
                              ` (${Math.round(r.width)}x${Math.round(r.height)}px)`);
        if (out.smallTargets.length >= 5) break;
      }
    }
  }
  return out;
}
"""


def list_pages():
    pages = []
    for p in REPO.rglob("*.html"):
        rel = p.relative_to(REPO)
        if rel.parts[0] in SKIP_DIRS or p.name.startswith("_"):
            continue
        pages.append(str(rel).replace("\\", "/"))
    return sorted(pages)


async def check_page(context, url_path, is_mobile, sem, findings):
    async with sem:
        page = await context.new_page()
        console_errors = []
        page_errors = []
        bad_responses = []

        page.on("console", lambda m: console_errors.append(m.text[:150])
                if m.type == "error" and "ERR_FAILED" not in m.text else None)
        page.on("pageerror", lambda e: page_errors.append(str(e)[:150]))
        page.on("response", lambda r: bad_responses.append((r.status, r.url[-80:]))
                if r.status >= 400 else None)

        issues = []
        try:
            await page.goto(BASE + url_path, wait_until="load", timeout=30000)
            # 遅延読み込み画像を発火させるため最下部まで送ってから測る
            await page.evaluate("""async () => {
                document.documentElement.style.scrollBehavior = 'auto';
                const step = window.innerHeight;
                for (let y = 0; y <= document.documentElement.scrollHeight; y += step) {
                    window.scrollTo(0, y);
                    await new Promise(r => setTimeout(r, 40));
                }
                window.scrollTo(0, 0);
            }""")
            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            c = await page.evaluate(CHECK_JS, is_mobile)
            if c["brokenImgs"]:
                issues.append(f"壊れた画像: {c['brokenImgs'][:3]}")
            if c["hOverflow"]:
                issues.append(f"横はみ出し: {c['offenders']}")
            if c["smallTargets"]:
                issues.append(f"小さすぎるボタン: {c['smallTargets']}")
        except Exception as e:
            issues.append(f"ページを開けませんでした: {str(e)[:120]}")
        # 404.htmlだけは特別。GitHub Pagesはどの階層のURLでもこの1枚を返すので、
        # 読み込み先を /ozu-life-memo/... という絶対パスで書いてある。
        # この点検用サーバーはリポジトリの直下を「/」として配るため、
        # ローカルでだけ404になる。本番では200で返ることを確認済みなので無視する。
        if url_path == "404.html":
            bad_responses = [r for r in bad_responses if "/ozu-life-memo/" not in str(r)]
            console_errors = [] if not bad_responses else console_errors

        if page_errors:
            issues.append(f"JSエラー: {page_errors[:2]}")
        if console_errors:
            issues.append(f"コンソールエラー: {console_errors[:2]}")
        if bad_responses:
            issues.append(f"404など: {bad_responses[:3]}")
        if issues:
            findings.append((url_path, issues))
        await page.close()


def port_open() -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", PORT)) == 0


async def main():
    pages = list_pages()
    print(f"\n  ブラウザ点検: {len(pages)}ページ × {len(VIEWPORTS)}画面幅")
    print("  (アクセス解析への通信はブロックしています)\n")

    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1",
         "--directory", str(REPO)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        if port_open():
            break
        time.sleep(0.1)

    total_findings = 0
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            for vp_name, vp_opts in VIEWPORTS.items():
                context = await browser.new_context(**vp_opts)
                await context.route(
                    "**/*",
                    lambda route: route.abort()
                    if any(h in route.request.url for h in BLOCK_HOSTS)
                    else route.continue_())
                sem = asyncio.Semaphore(6)
                findings = []
                is_mobile = "スマホ" in vp_name
                await asyncio.gather(*[
                    check_page(context, pg, is_mobile, sem, findings) for pg in pages])
                await context.close()

                if findings:
                    print(f"  【{vp_name}】問題 {len(findings)}ページ")
                    for path, issues in sorted(findings):
                        print(f"    {path}")
                        for i in issues:
                            print(f"      - {i}")
                else:
                    print(f"  【{vp_name}】問題なし ({len(pages)}ページ)")
                total_findings += len(findings)
            await browser.close()
    finally:
        server.terminate()

    print()
    if total_findings == 0:
        print("  結果: 全画面幅で問題なし。\n")
        return 0
    print(f"  結果: 問題のあるページが延べ {total_findings}件。上の一覧を確認してください。\n")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
