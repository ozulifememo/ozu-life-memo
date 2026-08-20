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

# 上下の題字罫(サイトヘッダーの藍の線と同じ意匠)
d.rectangle([0, 0, W, 14], fill=NAVY)
d.rectangle([0, H - 14, W, H], fill=NAVY)

logo_font = ImageFont.truetype(r"C:\Windows\Fonts\YuGothB.ttc", 108, index=0)
sub_font = ImageFont.truetype(r"C:\Windows\Fonts\YuGothM.ttc", 42, index=0)

def center_text(y, text, font, fill):
    bbox = d.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    d.text(((W - w) / 2 - bbox[0], y), text, font=font, fill=fill)
    return bbox[3] - bbox[1]

center_text(212, "OZU LIFE MEMO", logo_font, NAVY)

# 蜜柑色の短い罫
d.rectangle([(W - 72) / 2, 388, (W + 72) / 2, 396], fill=MIKAN)

center_text(432, "大洲市の非公式生活情報サイト", sub_font, MUTED)

out = r"c:\Users\ihfff\Desktop\ozu-life-memo\assets\img\ogp-card.png"
img.save(out, "PNG", optimize=True)
import os
print("saved:", out, os.path.getsize(out) // 1024, "KB")
