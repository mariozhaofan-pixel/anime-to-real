#!/usr/bin/env python3
"""Side-by-side comparison reel (stand-in for LayerStyle ImageReel + ImageReelComposit).

usage: python make_reel.py out.jpg "原图=a.jpg" "image2.5=b.png" ...
"""
import sys
from PIL import Image, ImageDraw, ImageFont

REEL_HEIGHT = 1024
BORDER = 32
LABEL_H = 72
FONT_PATHS = ["C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"]


def load_font(size):
    for p in FONT_PATHS:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def build(out, items):
    """items: [(label, image_path), ...] -> saves the reel to out."""
    tiles = []
    for label, path in items:
        im = Image.open(path).convert("RGB")
        w = round(im.width * REEL_HEIGHT / im.height)
        tiles.append((label, im.resize((w, REEL_HEIGHT), Image.LANCZOS)))

    width = sum(t.width for _, t in tiles) + BORDER * (len(tiles) + 1)
    height = REEL_HEIGHT + LABEL_H + BORDER * 2
    canvas = Image.new("RGB", (width, height), (245, 245, 245))
    draw = ImageDraw.Draw(canvas)
    font = load_font(36)
    x = BORDER
    for label, tile in tiles:
        canvas.paste(tile, (x, BORDER))
        tw = draw.textlength(label, font=font)
        draw.text((x + (tile.width - tw) / 2, BORDER + REEL_HEIGHT + 16), label, fill=(30, 30, 30), font=font)
        x += tile.width + BORDER
    canvas.save(out, quality=92)
    return out


def main():
    out = build(sys.argv[1], [a.split("=", 1) for a in sys.argv[2:]])
    print(out)


if __name__ == "__main__":
    main()
