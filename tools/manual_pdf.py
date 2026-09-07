"""運用マニュアルのHTMLを、そのままPDFにする。

`build_manual.py` が作ったデスクトップのHTMLを開いて、印刷の形で書き出す。

なぜHTMLから作るか。
以前は `docs/manual/build-pdf.js` が章の一覧を**手打ちで持っていた**ので、
章を足したり名前を変えたりするたびにズレた（実際、2026-09-06に章を
組み直したら、消した章を指したまま動かなくなっていた）。
**組み上がったHTMLから作れば、章が増えても勝手に付いてくる。**

HTMLの側に印刷用のCSSが入っているので、PDFでは
左の目次が消えて、章ごとに改ページされる。

使い方:

    python tools/build_manual.py     まずHTMLを作る
    python tools/manual_pdf.py       それをPDFにする

出来上がりはデスクトップに置く。
"""

import pathlib
import sys


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    desktop = pathlib.Path.home() / "Desktop"
    src = desktop / "OZU LIFE MEMO 運用マニュアル.html"
    dst = desktop / "OZU LIFE MEMO 運用マニュアル.pdf"

    if not src.exists():
        print("  HTMLがありません。先に python tools/build_manual.py を走らせてください")
        print("  探した場所:", src)
        return 1

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  playwright が入っていません。pip install playwright で入ります")
        return 1

    print("  HTMLを開いています…")
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page()
        pg.goto(src.as_uri())
        pg.wait_for_timeout(2000)          # 表と目次が組み上がるのを待つ
        pg.emulate_media(media="print")    # 印刷用のCSSを効かせる
        pg.pdf(
            path=str(dst),
            format="A4",
            print_background=True,
            margin={"top": "16mm", "bottom": "18mm", "left": "14mm", "right": "14mm"},
            display_header_footer=True,
            header_template='<div style="font-size:8px;width:100%;padding:0 14mm;'
                            'color:#888;text-align:right">OZU LIFE MEMO 運用マニュアル</div>',
            footer_template='<div style="font-size:8px;width:100%;padding:0 14mm;'
                            'color:#888;text-align:center">'
                            '<span class="pageNumber"></span> / '
                            '<span class="totalPages"></span></div>',
        )
        b.close()

    mb = dst.stat().st_size / 1048576
    print(f"\n  できました: {dst}")
    print(f"  {mb:.1f} MB")
    print("\n  ★このPDFには運営者本人の個人情報が入っています。")
    print("    ネット上にアップロードしないでください。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
