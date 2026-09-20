"""stamp_kit.py — 邮票质感参数化合成器

把四个质感维度做成可调参数，一键切换不同风味：
  stitch   针法密度   0.0 稀疏手缝 ── 1.0 密绣
  age      做旧程度   0.0 全新发行 ── 1.0 泛黄陈旧
  perf     齿孔完整度 0.0 残缺撕裂 ── 1.0 完整规整
  cancel   邮戳       0.0 不加（新票）── 1.0 半透明复古邮戳

另含三组内容增强（与参数无关，按主题配置）：
  · 面值单位（60¢ / 60分 / 60f …）
  · 侧边纹样 logo + 雕刻师署名
  · 主题彩蛋（藏在景物里的小元素）

用法：
    from stamp_kit import Preset, render
    p = Preset(stitch=0.7, age=0.3, perf=0.95, cancel=0.0,
               value="60¢", theme=THEME_COASTAL)
    render("输入.png", "输出.png", p)

命令行：
    python stamp_kit.py --src x.png --out y.png --stitch .7 --age .3 --perf .95 --cancel 0
    python stamp_kit.py --src x.png --preset 全新发行
    python stamp_kit.py --sheet          # 出参数矩阵对比图
"""
from __future__ import annotations

import argparse
import math
import os
from dataclasses import dataclass, field, asdict

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---------------------------------------------------------------- 字体

FDIR = r"C:\Windows\Fonts"
# 邮票字体：细衬线大写（标题/发行行）+ 小号无衬线（次要信息）
F_SERIF = ["BASKVILL.TTF", "GARA.TTF", "constan.ttf", "georgia.ttf"]
F_SANS = ["segoeui.ttf", "bahnschrift.ttf", "GOTHIC.TTF"]
F_SCRIPT = ["Inkfree.ttf", "segoeui.ttf"]
# 界面/标签字体：必须含 CJK，否则中文档位名会渲染成方框（tofu）
F_UI = ["msyh.ttc", "simhei.ttf", "Deng.ttf", "simsun.ttc", "segoeui.ttf"]


def _font(cands, size):
    for c in cands:
        p = os.path.join(FDIR, c)
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _has_glyph(font, ch):
    """检查字体是否真的含某个字形——缺字形会渲染成方框（tofu）。"""
    try:
        return font.getmask(ch).getbbox() is not None
    except Exception:
        return False


def dash(font, alt="-", want="·"):
    """中间点回退：字体缺 U+00B7 时降级为连字符，避免方框。"""
    return want if _has_glyph(font, want) else alt


# ---------------------------------------------------------------- 主题配置

@dataclass
class Theme:
    """一部邮票的主题：文字 + 彩蛋。换景色就换这里。"""
    name: str
    title: str                  # 顶部标题
    series: str                 # 发行行
    year: str
    value: str                  # 面值，含单位
    side_left: str              # 左侧竖排
    side_right: str             # 右侧竖排
    engraver: str               # 雕刻师署名
    egg: str                    # 彩蛋指令（给 image2 的一句话）
    # 墨色：暖炭褐，传统印刷感
    ink: tuple = (92, 80, 68)


THEME_COASTAL = Theme(
    name="海岸",
    title="THE BLUE BAY",
    series="POSTA - COASTAL SERIES",
    year="2026",
    value="60¢",
    side_left="LANDSCAPE ISSUE - TEXTILE STUDY",
    side_right="IMPRESSIONIST - POST-IMPRESSIONIST",
    engraver="ENGRAVED BY A. MOREL",
    egg="a tiny sailing boat on the water, a small shell hidden in the vegetation, "
        "and faint tiny footprints on the sand",
)

THEME_COASTAL_CN = Theme(
    name="海岸·中文面值",
    title="THE BLUE BAY",
    series="POSTA - COASTAL SERIES",
    year="2026",
    value="60分",
    side_left="海岸系列 · 纺织研究",
    side_right="印象派 · 后印象派",
    engraver="雕刻 A. MOREL",
    egg="a tiny sailing boat on the water, a small shell hidden in the vegetation, "
        "and faint tiny footprints on the sand",
)


# ---------------------------------------------------------------- 参数

@dataclass
class Preset:
    stitch: float = 0.70     # 针法密度
    age: float = 0.25        # 做旧程度
    perf: float = 0.95       # 齿孔完整度
    cancel: float = 0.00     # 邮戳强度
    value: str | None = None         # 覆盖面值
    theme: Theme = field(default_factory=lambda: THEME_COASTAL)
    seed: int = 13

    def label(self):
        # 纯 ASCII：验证/演示环境可能没有 CJK 字体，中文前缀会渲染成方框
        return (f"st{self.stitch:.2f} ag{self.age:.2f} "
                f"pf{self.perf:.2f} cx{self.cancel:.2f}")


NAMED = {
    "全新发行": Preset(stitch=0.35, age=0.08, perf=1.00, cancel=0.00),
    "标准": Preset(stitch=0.70, age=0.25, perf=0.95, cancel=0.00),
    "信销票": Preset(stitch=0.70, age=0.55, perf=0.72, cancel=0.85),
    "古董藏票": Preset(stitch=0.85, age=0.92, perf=0.45, cancel=0.55),
    "密绣精工": Preset(stitch=1.00, age=0.15, perf=1.00, cancel=0.00),
}

# 英文别名：无 CJK 字体的环境里预设名与 CLI 参数都可用英文
NAMED_EN = {
    "全新发行": "Mint",
    "标准": "Standard",
    "信销票": "Used",
    "古董藏票": "Antique",
    "密绣精工": "Dense",
}
NAMED_EN_INV = {v: k for k, v in NAMED_EN.items()}


# ---------------------------------------------------------------- 纸面定位

def find_paper(im, thr=None):
    """返回**刺绣/内容区**在画幅中的 bbox（左,上,右,下）。

    判据是「高频纹理能量」——空白纸几乎没有高频细节，而刺绣、亚麻布、油画都很强。
    做法：沿 y / x 求平均高频剖面，**跳过两侧的齿孔峰**后找第一个显著升高处。

    注意：返回值是「内容区」而不是「纸面」。纸边的排版由 typeset() 按纸边宽度算。
    """
    g = np.asarray(im.convert("L"), dtype=np.float32)
    hi = np.abs(g - np.asarray(im.convert("L").filter(ImageFilter.GaussianBlur(6)),
                               dtype=np.float32))
    H, W = hi.shape

    def edge(prof, reverse=False):
        n = len(prof)
        p = prof[::-1] if reverse else prof
        # 跳过最外侧 2% —— 那里是齿孔（本身高频很高，会误导检测）
        skip = max(3, int(n * 0.02))
        inner = p[skip:]
        if len(inner) < 8:
            return 0
        base = float(np.percentile(inner, 25))          # 纸边的基线
        peak = float(np.percentile(inner, 88))          # 内容区的高位
        if peak - base < 1.5:                           # 没有明显内容差异
            return skip
        t = base + (peak - base) * 0.45
        for i, v in enumerate(inner):
            if v > t:
                return skip + i
        return skip

    yt = edge(hi.mean(1), False)
    yb = H - 1 - edge(hi.mean(1), True)
    xl = edge(hi.mean(0), False)
    xr = W - 1 - edge(hi.mean(0), True)
    if xr - xl < W * 0.2 or yb - yt < H * 0.2:
        return (0, 0, W - 1, H - 1)
    return (int(xl), int(yt), int(xr), int(yb))


def strip_type(im, bbox, frac=0.125, side_frac=0.062):
    """抹掉来源图上已有的邮票文字，只保留空白纸——否则本地排版会叠字。

    做法：把留白带用**同一行/列里未被文字占据的纸色**做插值填充，
    这样能保住纸纹与做旧色调，而不是涂一块死白。上下两条带 + 左右两条窄带都处理。
    """
    a = np.asarray(im.convert("RGB"), dtype=np.float32).copy()
    x0, y0, x1, y1 = bbox
    ph, pw = y1 - y0, x1 - x0
    LUM = np.array([0.299, 0.587, 0.114], dtype=np.float32)

    # --- 上下横带：逐行插值 ---
    for (ba, bb) in [(y0, int(y0 + ph * frac)), (int(y1 - ph * frac), y1)]:
        ba, bb = max(0, ba), min(a.shape[0], bb)
        if bb <= ba:
            continue
        strip = a[ba:bb, x0:x1]
        for r in range(strip.shape[0]):
            row = strip[r]
            lum = row @ LUM
            if len(lum) < 8:
                continue
            good = lum >= np.percentile(lum, 62)
            if good.sum() < 4:
                good = np.ones_like(good, dtype=bool)
            idx = np.where(good)[0]
            xs = np.arange(strip.shape[1])
            for ch in range(3):
                strip[r, :, ch] = np.interp(xs, idx, row[idx, ch])
        a[ba:bb, x0:x1] = strip

    # --- 左右竖带：逐列插值（否则侧边竖排小字会与本地排版叠字）---
    for (ba, bb) in [(x0, int(x0 + pw * side_frac)), (int(x1 - pw * side_frac), x1)]:
        ba, bb = max(0, ba), min(a.shape[1], bb)
        if bb <= ba:
            continue
        strip = a[y0:y1, ba:bb]
        for c in range(strip.shape[1]):
            col = strip[:, c]
            lum = col @ LUM
            if len(lum) < 8:
                continue
            good = lum >= np.percentile(lum, 62)
            if good.sum() < 4:
                good = np.ones_like(good, dtype=bool)
            idx = np.where(good)[0]
            ys = np.arange(strip.shape[0])
            for ch in range(3):
                strip[:, c, ch] = np.interp(ys, idx, col[idx, ch])
        a[y0:y1, ba:bb] = strip

    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")


# ---------------------------------------------------------------- 效果层

def layer_stitch(im, bbox, amount, seed=13):
    """针法密度：沿**刺绣主体自己的轮廓**叠加针脚。

    amount 越高针脚越密、越长、越实。只描景物的边，不要沿整张邮票打一圈——
    那会变成明信片式的花边。景物轮廓用「非纸色像素」的 bbox 估计。
    """
    if amount <= 0.01:
        return im
    W, H = im.size
    a = np.asarray(im.convert("RGB"), dtype=np.float32)
    lum = a @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    # 景物 = 明显比纸暗或明显有色的像素
    mx, mn = a.max(2), a.min(2)
    sat = (mx - mn) / np.maximum(mx, 1.0)
    body = (lum < 176) | (sat > 0.30)
    x0, y0, x1, y1 = bbox
    x0, y0 = max(x0, 0), max(y0, 0)
    x1, y1 = min(x1, W - 1), min(y1, H - 1)
    sub = body[y0:y1, x0:x1]
    # 取景物的实际边界（能排除大面积空白纸）
    cf, rf = sub.mean(0), sub.mean(1)
    ci = np.where(cf > 0.10)[0]
    ri = np.where(rf > 0.10)[0]
    if len(ci) < 10 or len(ri) < 10:
        return im
    bx0, bx1 = x0 + int(ci.min()), x0 + int(ci.max())
    by0, by1 = y0 + int(ri.min()), y0 + int(ri.max())

    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    rng = np.random.default_rng(seed)
    gap = max(4, int(22 - 13 * amount))
    col = (78, 66, 54, int(90 + 130 * amount))
    edges = [
        (bx0, by0, bx1, by0), (bx1, by1, bx0, by1),
        (bx0, by0, bx0, by1), (bx1, by0, bx1, by1),
    ]
    for (ax, ay, bx, by) in edges:
        n = max(4, int(math.hypot(bx - ax, by - ay) / gap))
        for i in range(n):
            if rng.random() > 0.30 + 0.70 * amount:      # 密度低时大量跳针
                continue
            t0, t1 = i / n, (i + 0.55) / n
            sx, sy = ax + (bx - ax) * t0, ay + (by - ay) * t0
            ex, ey = ax + (bx - ax) * t1, ay + (by - ay) * t1
            j = rng.normal(0, 1.2, 2)
            d.line([sx + j[0], sy + j[1], ex + j[0], ey + j[1]], fill=col, width=3)
    lay = lay.filter(ImageFilter.GaussianBlur(0.45))
    out = im.convert("RGBA")
    out.alpha_composite(lay)
    return out.convert("RGB")


def layer_age(im, bbox, amount, seed=13):
    """做旧：整纸暖黄化 + 边缘偏深 + 随机 foxing 黄褐斑点。"""
    if amount <= 0.01:
        return im
    a = np.asarray(im.convert("RGB"), dtype=np.float32)
    H, W, _ = a.shape
    x0, y0, x1, y1 = bbox
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx = max((x1 - x0) / 2, 1)
    ry = max((y1 - y0) / 2, 1)
    yy, xx = np.mgrid[0:H, 0:W]
    # 归一化到纸面坐标系下的径向距离（0 中心 → 1 边缘）
    rad = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    rad = np.clip(rad, 0, 1.4)
    # 边缘偏深：rad 越大越压暗
    edge = np.clip((rad - 0.62) / 0.78, 0, 1)
    # 整体暖黄化
    tint = np.array([1.012, 0.995, 0.958], dtype=np.float32)
    a *= 1.0 + (tint - 1.0)[None, None, :] * (amount * 2.2)
    # 边缘压暗
    a -= (edge * amount * 22.0)[:, :, None]
    # foxing 斑点
    rng = np.random.default_rng(seed + 5)
    blobs = Image.new("L", (W, H), 0)
    db = ImageDraw.Draw(blobs)
    for _ in range(int(9 + 22 * amount)):
        bx = rng.uniform(x0, x1)
        by = rng.uniform(y0, y1)
        r = rng.uniform(3, 7 + 13 * amount)
        db.ellipse([bx - r, by - r, bx + r, by + r],
                   fill=int(60 + 120 * amount))
    blobs = blobs.filter(ImageFilter.GaussianBlur(5))
    bm = (np.asarray(blobs, dtype=np.float32) / 255.0)[:, :, None]
    spot = np.array([196, 152, 104], dtype=np.float32)
    a = a * (1 - bm * 0.42) + spot[None, None, :] * (bm * 0.42)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")


def layer_perf(im, bbox, amount, seed=13, perf_frame=None):
    """齿孔完整度：沿纸边打孔。amount 越低，残缺/撕裂越多。

    注意：合成器**不改动源图本身的齿孔**（那由 image2 出图时定），
    这一层只负责在 amount 低时「破坏」齿孔——补打缺口、啃掉纸边，
    做出残票/信销票的破损感。amount=1 时基本不动源图。

    perf_frame = 齿孔行所在矩形，**占画幅比例** (fx0, fy0, fx1, fy1)。
    不传则退回用 bbox 边缘——但「宽纸边」版式下 bbox 是内容区边缘，
    距真正的齿孔行还有一条纸边，啃错位置；量出齿孔行中心后务必传入。
    """
    if amount >= 0.995:
        return im
    W, H = im.size
    a = np.asarray(im.convert("RGB"), dtype=np.float32).copy()
    x0, y0, x1, y1 = bbox
    if perf_frame:
        x0 = int(perf_frame[0] * W)
        y0 = int(perf_frame[1] * H)
        x1 = int(perf_frame[2] * W)
        y1 = int(perf_frame[3] * H)
    rng = np.random.default_rng(seed + 11)
    r = max(3, int((x1 - x0) * 0.0068))
    pitch = int(r * 3.5)
    # 背景色（啃咬填充色）取「框架内侧」的干净纸色：孔与内容之间的净纸
    ins = 18
    bg = a[min(y0 + ins, H - 10):min(y0 + ins + 9, H - 1),
           min(x0 + ins, W - 10):min(x0 + ins + 9, W - 1)]
    bgc = (bg.reshape(-1, 3).mean(0) if bg.size
           else np.array([180, 172, 162], dtype=np.float32))

    # 破损 = 用背景色在纸边上啃出缺口（缺孔、撕裂、缺角）
    dam = Image.new("L", (W, H), 0)
    dd = ImageDraw.Draw(dam)
    p_break = (1 - amount) * 0.85           # 每个孔位被破坏的概率

    def bite(cx, cy, rr, depth):
        """从纸边往里啃一块，depth 控制进深"""
        dd.ellipse([cx - rr, cy - rr * depth, cx + rr, cy + rr * depth], fill=255)

    for x in range(int(x0 + r), int(x1) - r + 1, pitch):
        for (cx, cy, sgn) in ((x, y0, -1), (x, y1, 1)):
            if rng.random() < p_break:
                # 只破坏「齿」那一点，不要啃成大块——保持齿孔节奏可读
                rr = rng.uniform(r * 0.55, r * 1.5)
                dp = rng.uniform(0.7, 1.7)
                bite(cx + rng.normal(0, 1.2), cy + sgn * rr * 0.45, rr, dp)
    for y in range(int(y0 + r), int(y1) - r + 1, pitch):
        for (cx, cy, sgn) in ((x0, y, -1), (x1, y, 1)):
            if rng.random() < p_break:
                rr = rng.uniform(r * 0.55, r * 1.5)
                dp = rng.uniform(0.7, 1.7)
                bite(cx + sgn * rr * 0.45, cy + rng.normal(0, 1.2), rr, dp)

    # 缺角：amount 低时四角被啃掉
    if amount < 0.9:
        for (cx, cy) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
            if rng.random() < (1 - amount) * 0.9:
                rr = rng.uniform(r * 1.8, r * 3.6)
                dd.ellipse([cx - rr * 1.1, cy - rr * 1.1,
                            cx + rr * 1.1, cy + rr * 1.1], fill=255)

    dm = np.asarray(dam.filter(ImageFilter.GaussianBlur(1.0)),
                    dtype=np.float32) / 255.0
    dm = np.clip(dm * 1.4, 0, 1)[:, :, None]
    a = a * (1 - dm) + bgc[None, None, :] * dm
    # 断面留一点纤维亮边
    fib = np.asarray(dam.filter(ImageFilter.GaussianBlur(2.4)),
                     dtype=np.float32) / 255.0
    fib = np.clip(fib - dm[:, :, 0], 0, 1)[:, :, None]
    a += fib * 14.0
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")


def layer_cancel(im, bbox, amount, theme=None, seed=13):
    """邮戳：角落半透明复古圆形日戳 + 地名 + 日期。amount 0 则不加。"""
    if amount <= 0.01:
        return im
    W, H = im.size
    x0, y0, x1, y1 = bbox
    S = int((x1 - x0) * 0.235)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    alpha = int(96 + 70 * amount)
    ink = (68, 60, 72, alpha)          # 略带紫的旧墨
    lw = max(2, int(S * 0.011))

    box = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    db = ImageDraw.Draw(box)
    db.ellipse([lw, lw, S - lw, S - lw], outline=ink, width=lw)
    db.ellipse([S * .155, S * .155, S * .845, S * .845], outline=ink, width=max(1, lw - 1))
    # 中心地名与日期
    f1 = _font(F_SANS, int(S * 0.093))
    f2 = _font(F_SANS, int(S * 0.082))
    db.text((S * 0.5, S * 0.335), "PORTO COSTIERA", font=f1, fill=ink, anchor="mm")
    db.text((S * 0.5, S * 0.685), "14 · IX · 2026", font=f2, fill=ink, anchor="mm")
    # 上下弧内的短字（真邮戳常沿弧排）
    f3 = _font(F_SANS, int(S * 0.068))
    db.text((S * 0.5, S * 0.16), "POSTE", font=f3, fill=ink, anchor="mm")
    db.text((S * 0.5, S * 0.855), "COSTIERA", font=f3, fill=ink, anchor="mm")
    # 波浪注销线（在双圈内）
    for i in range(6):
        yy = S * (0.44 + i * 0.045)
        db.arc([S * 0.24, yy - S * 0.042, S * 0.76, yy + S * 0.042],
               200, 340, fill=ink, width=max(1, lw - 1))

    # 邮戳有"盖不实"的残缺：用噪声吃掉一部分墨
    rng = np.random.default_rng(seed + 23)
    n = np.asarray(Image.fromarray(
        (rng.random((S, S)) * 255).astype(np.uint8), "L"
    ).filter(ImageFilter.GaussianBlur(1.1)), dtype=np.float32) / 255.0
    cut = np.clip(1.0 - (n - 0.42) * 2.2, 0, 1)
    al = np.asarray(box.split()[3], dtype=np.float32) * cut
    box.putalpha(Image.fromarray(np.clip(al, 0, 255).astype(np.uint8), "L"))

    box = box.rotate(rng.uniform(-15, -6), resample=Image.BICUBIC, expand=True)
    # 落在右下角，略压出纸外（真实的戳不会工整地待在纸内）
    px = int(x1 - box.width * 0.80)
    py = int(y1 - box.height * 0.76)
    lay.alpha_composite(box, (px, py))
    # 少数情况下补一道边戳（穿过纸边的注销线）
    if amount > 0.7:
        seg = Image.new("RGBA", (int((x1 - x0) * 0.34), int(S * 0.20)), (0, 0, 0, 0))
        ds = ImageDraw.Draw(seg)
        for i in range(5):
            ds.arc([-S * .1 + i * S * .07, 0, S * .12 + i * S * .07, seg.height],
                   250, 70, fill=ink, width=max(1, lw - 1))
        seg = seg.rotate(rng.uniform(-10, -2), resample=Image.BICUBIC, expand=True)
        lay.alpha_composite(seg, (int(x0 - seg.width * 0.10),
                                  int(y0 + (y1 - y0) * 0.26)))
    out = im.convert("RGBA")
    out.alpha_composite(lay)
    return out.convert("RGB")


# ---------------------------------------------------------------- 排版

def typeset(im, bbox, theme, value=None, margin_v=0.12, margin_h=0.10, perf_clear=0.0):
    """把邮票文字排进留白：顶部标题 / 底部发行行·面值·年份 / 左右竖排。

    margin_v / margin_h = **空白纸边占画幅的比例**（上下的 / 左右的），
    与出图阶段的设定保持一致即可（默认上下 12%、左右 10%）。
    排版位置按此比例算，不做图像自动检测——更稳、可复现。

    perf_clear = 纸边最外侧被齿孔行占据的比例（如 0.04）。
    文字带中线与竖排轨道都移进「齿孔外缘 → 亚麻边」的净空区，
    字号也按净空高度算——紧凑纸边（6–9%）时必开，否则标题压在齿孔上。
    """
    W, H = im.size
    x0, y0, x1, y1 = bbox                     # bbox = 刺绣/内容区（仅供 strip_type 用）
    pw, ph = x1 - x0, y1 - y0
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    ink = theme.ink + (255,)

    # 纸边排版位置按**固定比例**算，不做图像检测。
    # 理由：纸边宽度是出图阶段就定好的（见 SKILL.md「纸边宽度决定文字能不能排上去」），
    # 自动检测在「宽纸边 + 刺绣边框」这种版式上不稳定（刺绣纹理会被误判成内容）。
    # 齿孔本身还要占掉一点，所以再乘 SAFE 留出余量。
    SAFE = 0.86
    mv = (margin_v or 0.12)
    mh = (margin_h or 0.10)
    mt = max(8, int(H * mv * SAFE))
    mb = mt
    ml = max(8, int(W * mh * SAFE))
    mr = ml
    # 齿孔带避让：纸边最外侧 perf_clear 比例被齿孔占据，
    # 文字带中线移到「齿孔外缘 → 内容边」净空区的中点，字号按净空高度算
    pt_ = int(H * perf_clear)
    pl_ = int(W * perf_clear)
    cy_top = (pt_ + mt) * 0.50                # 上纸边净空带中线
    cy_bot = H - 1 - (pt_ + mb) * 0.50        # 下纸边净空带中线
    avail_w = W - 2 * ml                      # 横排文字可用宽度

    top_band = max(10, mt - pt_)
    side_band = max(10, min(ml, mr) - pl_)
    fs_title = max(11, int(top_band * 0.42))
    fs_small = max(9, int(top_band * 0.30))

    def spaced(s, font, gap, cx, cy, fill):
        """宽字距居中绘制——邮票大写的标志性排法"""
        ws = [d.textlength(c, font=font) for c in s]
        tot = sum(ws) + gap * max(len(s) - 1, 0)
        x = cx - tot / 2
        for c, w in zip(s, ws):
            d.text((x, cy), c, font=font, fill=fill, anchor="lm")
            x += w + gap

    # 顶部标题
    fT = _font(F_SERIF, fs_title)
    while d.textlength(theme.title, font=fT) * 1.34 > avail_w and fT.size > 12:
        fT = _font(F_SERIF, fT.size - 1)
    gapT = max(1, int(fT.size * 0.34))
    spaced(theme.title, fT, gapT, W / 2, cy_top, ink)

    # 底部：发行行 · 面值 · 年份
    fS = _font(F_SERIF, fs_small)
    fV = _font(F_SERIF, int(fs_small * 1.75))
    v = value or theme.value
    series = theme.series.replace("·", dash(fS))
    year = theme.year.replace("·", dash(fS))
    # 底部发行行排在「下纸边带」的中线，不贴齿孔
    yb = cy_bot
    w_ser = d.textlength(series, font=fS)
    w_val = d.textlength(v, font=fV)
    w_yr = d.textlength(year, font=fS)
    # 分隔点**画出来**而不是排出来：衬线字体常缺 U+00B7 字形，会显成方框
    r_dot = max(1, int(fs_small * 0.085))
    sep = int(fs_small * 0.52)
    tot = w_ser + sep * 4 + r_dot * 4 + w_val + w_yr
    # 纸边太窄时整体收缩字号，保证发行行不越界
    guard = avail_w * 0.98
    while tot > guard and fs_small > 8:
        fs_small -= 1
        fS = _font(F_SERIF, fs_small)
        fV = _font(F_SERIF, int(fs_small * 1.75))
        w_ser = d.textlength(series, font=fS)
        w_val = d.textlength(v, font=fV)
        w_yr = d.textlength(year, font=fS)
        r_dot = max(1, int(fs_small * 0.085))
        sep = int(fs_small * 0.52)
        tot = w_ser + sep * 4 + r_dot * 4 + w_val + w_yr
    x = W / 2 - tot / 2
    ymd = yb

    def put_dot(cx):
        d.ellipse([cx - r_dot, ymd - r_dot, cx + r_dot, ymd + r_dot], fill=ink)

    d.text((x, yb), series, font=fS, fill=ink, anchor="lm")
    x += w_ser + sep
    put_dot(x + r_dot)
    x += r_dot * 2 + sep
    d.text((x, yb), v, font=fV, fill=ink, anchor="lm")
    x += w_val + sep
    put_dot(x + r_dot)
    x += r_dot * 2 + sep
    d.text((x, yb), year, font=fS, fill=ink, anchor="lm")

    # 左右竖排（旋转 90°）
    # 竖排字号同时受「左右留白宽度」与「可用净高」双重约束
    fs_side = max(9, min(int(fs_small * 0.86), int(side_band * 0.62)))

    def vertical(s, font, cx, cy, ink_):
        tmp = Image.new("RGBA", (int(d.textlength(s, font=font)) + 8, int(font.size * 1.45)),
                        (0, 0, 0, 0))
        td = ImageDraw.Draw(tmp)
        td.text((4, tmp.height / 2), s, font=font, fill=ink_, anchor="lm")
        for ang, xoff in ((90, x0 + pw * 0.030), (-90, x1 - pw * 0.030)):
            r = tmp.rotate(ang, expand=True)
            lay.alpha_composite(r, (int(xoff - r.width / 2), int(cy - r.height / 2)))
        return

    fSide0 = _font(F_SANS, fs_side)

    # 竖排可用净高：整纸高扣掉上下两条纸边带
    avail_h = max(20, H - mt - mb - 8)
    side_share = 0.26          # logo / 署名在净高里占掉的份额

    def fit_side(s, base_font):
        """竖排文字按可用高度自动收字号，过长就缩，避免与上下横排重叠。"""
        f = base_font
        for _ in range(14):
            need = d.textlength(s, font=f) * (1 + side_share)
            if need <= avail_h or f.size <= 9:
                return f
            f = _font(F_SANS, f.size - 1)
        return f

    sl = theme.side_left.replace("·", dash(fSide0))
    sr = theme.side_right.replace("·", dash(fSide0))
    fSideL, fSideR = fit_side(sl, fSide0), fit_side(sr, fSide0)

    def vstrip(s, font, pad=8):
        tmp = Image.new("RGBA", (int(d.textlength(s, font=font)) + pad,
                                 int(font.size * 1.45)), (0, 0, 0, 0))
        td = ImageDraw.Draw(tmp)
        td.text((pad // 2, tmp.height / 2), s, font=font, fill=ink, anchor="lm")
        return tmp

    # 竖排垂直居中在画幅中部
    vc_y = H / 2

    # 左/右各留两条平行轨道（按纸边净空区分），避免同一窄条里叠字
    clean_l = pl_
    wid_l = max(6, ml - pl_)
    track_out = clean_l + wid_l * 0.30
    track_in = clean_l + wid_l * 0.76
    track_out_r = clean_l + wid_l * 0.30      # 右侧镜像（距右边）
    track_in_r = clean_l + wid_l * 0.76

    # 左侧文字（外侧轨道）
    rL = vstrip(sl, fSideL).rotate(90, expand=True)
    lay.alpha_composite(rL, (int(track_out - rL.width / 2), int(vc_y - rL.height / 2)))

    # 小刺绣纹样 logo（左侧内侧轨道，位于上纸边带）
    ls = max(8, int(pw * 0.026))
    L = Image.new("RGBA", (ls * 2, ls * 2), (0, 0, 0, 0))
    dl = ImageDraw.Draw(L)
    s = ls // 2
    dl.rectangle([s - 1, s - 1, s + 2, s + 2], outline=ink, width=1)
    for (ax, ay, bx, by) in [(0, 0, 2 * s - 1, 2 * s - 1), (2 * s - 1, 0, 0, 2 * s - 1)]:
        dl.line([ax, ay, bx, by], fill=ink, width=1)
    for i in range(4):
        dl.line([s + 5 + i * 3, s - 3, s + 5 + i * 3, s + 4], fill=ink, width=1)
    Lr = L.rotate(90, expand=True)
    logo_y = cy_top
    lay.alpha_composite(Lr, (int(track_in - Lr.width / 2), int(logo_y)))

    # 右侧文字（外侧轨道，与左侧同一 y）+ 内侧雕刻师署名
    rR = vstrip(sr, fSideR).rotate(-90, expand=True)
    lay.alpha_composite(rR, (int((W - 1) - track_out_r - rR.width / 2),
                             int(vc_y - rR.height / 2)))

    fEng = _font(F_SCRIPT, max(9, int(fSideR.size * 0.80)))
    eng = theme.engraver
    e_have = avail_h * 0.9                        # 署名能用的净高
    for _ in range(14):
        if d.textlength(eng, font=fEng) <= e_have or fEng.size <= 9:
            break
        fEng = _font(F_SCRIPT, fEng.size - 1)
    rE = vstrip(eng, fEng, pad=6).rotate(-90, expand=True)
    lay.alpha_composite(rE, (int((W - 1) - track_in_r - rE.width / 2), int(logo_y)))
    return lay


def apply_type(im, lay):
    out = im.convert("RGBA")
    out.alpha_composite(lay)
    return out.convert("RGB")


# ---------------------------------------------------------------- 主流程

def render(src, out, p: Preset, typeset_on=True, margin_v=0.12, margin_h=0.10,
           perf_clear=0.0, strip=True, perf_frame=None):
    im = Image.open(src).convert("RGB")
    bbox = find_paper(im)
    if typeset_on and strip:
        im = strip_type(im, bbox)          # 先抹掉来源图自带的文字，避免叠字
    im = layer_age(im, bbox, p.age, p.seed)
    im = layer_perf(im, bbox, p.perf, p.seed, perf_frame=perf_frame)
    im = layer_stitch(im, bbox, p.stitch, p.seed)
    if typeset_on:
        im = apply_type(im, typeset(im, bbox, p.theme, p.value,
                                    margin_v=margin_v, margin_h=margin_h,
                                    perf_clear=perf_clear))
    im = layer_cancel(im, bbox, p.cancel, p.theme, p.seed)
    if out:
        d = os.path.dirname(os.path.abspath(out))
        if d:
            os.makedirs(d, exist_ok=True)
        im.save(out, "PNG")
        print("saved:", out, "|", p.label())
    return im


def sheet(src, out, presets=None, W=560, margin_v=0.12, margin_h=0.10,
          perf_clear=0.0, strip=True, perf_frame=None):
    """参数矩阵对比图"""
    presets = presets or list(NAMED.items())
    tiles = []
    for name, p in presets:
        im = render(src, None, p, margin_v=margin_v, margin_h=margin_h,
                    perf_clear=perf_clear, strip=strip, perf_frame=perf_frame)
        h = int(im.height * W / im.width)
        en = NAMED_EN.get(name, "")
        cap = f"{name} / {en}   [{p.label()}]" if en else f"{name}   [{p.label()}]"
        tiles.append((im.resize((W, h), Image.LANCZOS), cap))
    th = tiles[0][0].height
    PAD, LBL = 14, 30
    cols = min(2, len(tiles))
    rows = (len(tiles) + cols - 1) // cols
    sheet_im = Image.new("RGB", (cols * W + (cols + 1) * PAD,
                                 rows * (th + LBL) + (rows + 1) * PAD), (247, 248, 250))
    d = ImageDraw.Draw(sheet_im)
    f = _font(F_UI, max(15, int(W * 0.030)))
    for i, (t, lb) in enumerate(tiles):
        r, c = divmod(i, cols)
        x = PAD + c * (W + PAD)
        y = PAD + r * (th + LBL + PAD)
        sheet_im.paste(t, (x, y))
        d.text((x + 6, y + th + 6), lb, font=f, fill=(35, 39, 44))
    sheet_im.save(out)
    print("saved:", out, sheet_im.size)
    return sheet_im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="output/stamp/stamp-v2-b.png")
    ap.add_argument("--out", default=None)
    ap.add_argument("--preset", choices=list(NAMED.keys()) + list(NAMED_EN_INV.keys()))
    ap.add_argument("--stitch", type=float)
    ap.add_argument("--age", type=float)
    ap.add_argument("--perf", type=float)
    ap.add_argument("--cancel", type=float)
    ap.add_argument("--value", default=None)
    ap.add_argument("--theme", default="coastal",
                    choices=["coastal", "coastal_cn"])
    ap.add_argument("--sheet", action="store_true")
    ap.add_argument("--no-type", action="store_true")
    ap.add_argument("--margin-v", type=float, default=0.12,
                    help="上下空白纸边占画幅比例（与出图设定一致）")
    ap.add_argument("--margin-h", type=float, default=0.10,
                    help="左右空白纸边占画幅比例（与出图设定一致）")
    ap.add_argument("--perf-clear", type=float, default=0.0,
                    help="纸边最外侧被齿孔行占据的比例（文字避让齿孔带，紧凑纸边必开）")
    ap.add_argument("--no-strip", action="store_true",
                    help="跳过 strip_type（源图自带排版文字时才需要；纯净出图必须跳过，"
                         "否则 12.5%% 抹除带会吃掉窄纸边内的画面边缘）")
    ap.add_argument("--perf-frame", default=None,
                    help="齿孔行所在矩形，占画幅比例 fx0,fy0,fx1,fy1（残齿啃咬定位用）")
    a = ap.parse_args()

    perf_frame = None
    if a.perf_frame:
        perf_frame = tuple(float(v) for v in a.perf_frame.split(","))

    theme = THEME_COASTAL_CN if a.theme == "coastal_cn" else THEME_COASTAL
    key = NAMED_EN_INV.get(a.preset, a.preset)
    p = NAMED[key] if key else Preset(theme=theme)
    p.theme = theme
    if a.value:
        p.value = a.value
    for k in ("stitch", "age", "perf", "cancel"):
        v = getattr(a, k)
        if v is not None:
            setattr(p, k, v)

    if a.sheet:
        sheet(a.src, a.out or "output/stamp/stamp-param-sheet.png",
              margin_v=a.margin_v, margin_h=a.margin_h,
              perf_clear=a.perf_clear, strip=not a.no_strip,
              perf_frame=perf_frame)
        return
    render(a.src, a.out or "output/stamp/stamp-custom.png", p, not a.no_type,
           margin_v=a.margin_v, margin_h=a.margin_h,
           perf_clear=a.perf_clear, strip=not a.no_strip,
           perf_frame=perf_frame)


if __name__ == "__main__":
    main()
