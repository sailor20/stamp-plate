"""compose_sources.py — 多张参考图本地预合成一张（image2 单图输入的解法）

为什么需要：image2 一次只接受**一张**参考图，喂两张（内容 + 风格）会稳定
返回 upstream_error。所以：
  · 风格参考**必须写成文字**（写进提示词，逐条描述），不要指望模型从第二张图学风格；
  · 如果确实要同时给模型看多张**内容**图（如全景的两半、同一个景的多视角），
    先用本脚本拼成一张再喂。

布局:
  h     横向并排（等高）         默认 2–3 张
  v     纵向堆叠（等宽）
  grid  2×2 网格（等格子）       4 张
  auto  2–3 张 → h；4 张 → grid

用法:
  python compose_sources.py a.png b.png -o combined.png
  python compose_sources.py a.png b.png c.png --layout v --gap 12
"""
from __future__ import annotations

import argparse
import os

from PIL import Image

BG = (128, 128, 128)          # 接缝底色：中性灰，不被当成画面内容
MAX_SIDE = 2048               # 输出长边上限（超过就整体缩）


def _fit(im, size):
    return im.resize(size, Image.LANCZOS)


def compose_h(ims, gap):
    h = min(im.height for im in ims)
    ims = [_fit(im, (round(im.width * h / im.height), h)) for im in ims]
    W = sum(im.width for im in ims) + gap * (len(ims) - 1)
    out = Image.new("RGB", (W, h), BG)
    x = 0
    for im in ims:
        out.paste(im, (x, 0))
        x += im.width + gap
    return out


def compose_v(ims, gap):
    w = min(im.width for im in ims)
    ims = [_fit(im, (w, round(im.height * w / im.width))) for im in ims]
    H = sum(im.height for im in ims) + gap * (len(ims) - 1)
    out = Image.new("RGB", (w, H), BG)
    y = 0
    for im in ims:
        out.paste(im, (0, y))
        y += im.height + gap
    return out


def compose_grid(ims, gap):
    cw = min(im.width for im in ims)
    ch = min(im.height for im in ims)
    cell = (cw, ch)
    ims = [_fit(im, cell) for im in ims]
    W = cw * 2 + gap
    H = ch * 2 + gap
    out = Image.new("RGB", (W, H), BG)
    out.paste(ims[0], (0, 0))
    out.paste(ims[1], (cw + gap, 0))
    out.paste(ims[2], (0, ch + gap))
    out.paste(ims[3], (cw + gap, ch + gap))
    return out


def main():
    ap = argparse.ArgumentParser(description="多张参考图预合成一张")
    ap.add_argument("images", nargs="+", help="2–4 张输入图")
    ap.add_argument("-o", "--out", required=True, help="输出 PNG 路径")
    ap.add_argument("--layout", choices=["auto", "h", "v", "grid"], default="auto")
    ap.add_argument("--gap", type=int, default=8, help="接缝宽（px），0 = 无缝硬拼")
    a = ap.parse_args()

    n = len(a.images)
    if not 2 <= n <= 4:
        raise SystemExit("需要 2–4 张输入图；>4 张请分批或先自行裁剪")

    layout = a.layout
    if layout == "auto":
        layout = "grid" if n == 4 else "h"
    if layout == "grid" and n != 4:
        raise SystemExit("grid 布局需要正好 4 张图")
    if layout == "h" and n == 4:
        layout = "grid"

    ims = [Image.open(p).convert("RGB") for p in a.images]
    if layout == "h":
        out = compose_h(ims, a.gap)
    elif layout == "v":
        out = compose_v(ims, a.gap)
    else:
        out = compose_grid(ims, a.gap)

    # 长边上限
    if max(out.size) > MAX_SIDE:
        s = MAX_SIDE / max(out.size)
        out = out.resize((round(out.width * s), round(out.height * s)), Image.LANCZOS)

    d = os.path.dirname(os.path.abspath(a.out))
    if d:
        os.makedirs(d, exist_ok=True)
    out.save(a.out, "PNG")
    print("saved:", a.out, out.size, "| layout:", layout,
          "| 记住：风格参考必须写成文字，不要指望模型从第二张图学风格")


if __name__ == "__main__":
    main()
