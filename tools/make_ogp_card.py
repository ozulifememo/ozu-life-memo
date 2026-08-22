# -*- coding: utf-8 -*-
"""LINE・SNSシェア用の既定カード画像(1200x630)を生成する。
写真がひもづいていないページのog:imageに使う。配色はサイトのトークンと同じ。"""
from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
BG = "#f6f5f2"
NAVY = "#1e435f"
MIKAN = "#9a6238"
MUTED = "#5b6673"

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

# A案ロゴ(題字・明朝)に合わせた意匠(2026-08-21改定):
# 上下とも太罫+細罫の二重、ワードマークは明朝、タグラインの両脇に蜜柑の小さい角
d.rectangle([0, 0, W, 12], fill=NAVY)
d.rectangle([0, 22, W, 25], fill=NAVY)
d.rectangle([0, H - 25, W, H - 22], fill=NAVY)
d.rectangle([0, H - 12, W, H], fill=NAVY)

logo_font = ImageFont.truetype(r"C:\Windows\Fonts\yumindb.ttf", 116)
sub_font = ImageFont.truetype(r"C:\Windows\Fonts\YuGothM.ttc", 42, index=0)

def center_text(y, text, font, fill):
    bbox = d.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    d.text(((W - w) / 2 - bbox[0], y), text, font=font, fill=fill)
    return w

center_text(196, "OZU LIFE MEMO", logo_font, NAVY)

sub = "大洲市の非公式生活情報サイト"
sub_w = center_text(422, sub, sub_font, MUTED)
sq = 14
sx0 = (W - sub_w) / 2 - 44
sx1 = (W + sub_w) / 2 + 30
d.rectangle([sx0, 422 + 18, sx0 + sq, 422 + 18 + sq], fill=MIKAN)
d.rectangle([sx1, 422 + 18, sx1 + sq, 422 + 18 + sq], fill=MIKAN)

import os
out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "img", "ogp-card.png")
img.save(out, "PNG", optimize=True)
print("saved:", out, os.path.getsize(out) // 1024, "KB")
