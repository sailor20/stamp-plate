"""qc_stamp.py — 一次成型整票的可复现质检（SKILL.md 质量门的算法化）

把 SKILL.md 里的判据写死成算法，全部数值可复现、可进脚本流水线：
  墨迹判据   lum < 195 且 8 < R-B < 62（暖炭褐专色；亮度阈值会被齿孔骗过）
  尺寸       目标 1536x1024，容差 --size-tol（默认 ±5%）
  纸边       上下为**硬约束** ≥ --min-v（默认 10%）；左右为**下限** ≥ --min-h（默认 8%）
  五区占用   顶 / 底 / 左 / 右上 / 右中 各区必须检出墨迹
  右侧间隔   右边两段竖排之间最大空白 ≥ 5% 画幅高（叠字事故区）
  居中       顶/底横排只看中央 64% 宽、左右竖排只看内容行区间——
             质心偏离纸面中线 ≤ --max-offset（%），右栏无 ≥2%H 分隔时不硬验
  齿孔行波动 沿齿孔行扫一行亮度的 std ≥ 18（四边各测）
  纸纹       空白纸区高频 std（去低频后）≥ 6，低于 3 基本是塑料
  齿孔带入侵 纸边最外一条齿孔带（~3.5% 薄环）内墨迹占比 ≤ 2%

拼写**没有像素判据**——用 --bands 导出放大字带逐字人工核对。
用法:
  python qc_stamp.py stamp.png
  python qc_stamp.py stamp.png --bands bands_out --json qc.json
  python qc_stamp.py stamp.png --paper-frame 0.03,0.05,0.97,0.96
退出码: 全过 0；有 FAIL 1。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

def find_paper(im, thr=None, paper_bbox=None):
    """返回**刺绣/内容区**的 bbox（左,上,右,下）。

    paper_bbox 给定时先裁出纸面再找内容（把桌面/阴影挡在检测外），
    返回坐标仍换算回整图坐标。

    判据是「高频纹理能量」——空白纸几乎没有高频细节，而刺绣、亚麻布、油画都很强。
    做法：沿 y / x 求平均高频剖面，**跳过两侧的齿孔峰**后找第一个显著升高处。

    注意：返回值是「内容区」而不是「纸面」。纸面用 find_paper_sheet()。
    （自 stamp_kit.py 移植——精排路线移除后 qc 自包含）
    """
    if paper_bbox is not None:
        px0, py0, px1, py1 = paper_bbox
        bx = find_paper(im.crop(paper_bbox))
        return (bx[0] + px0, bx[1] + py0, bx[2] + px0, bx[3] + py0)
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


def find_paper_sheet(im, min_cover=0.35):
    """估计**邮票纸**在画幅中的 bbox（含纸边与齿孔带的整张纸）。

    邮票「浮在桌面上」且带 1.5° 倾斜——画布边 ≠ 纸边，从画布边取比例会排到
    桌面或齿孔上。按「纸是亮且低饱和的大块区域，桌面更暗」切出行/列跨度。
    返回 (x0,y0,x1,y1)；不可信时返回 None（调用方退回 margin 假设比例，
    或由用户 --paper-frame 显式给框——可控 > 聪明）。
    （自 stamp_kit.py 移植——精排路线移除后 qc 自包含）
    """
    a = np.asarray(im.convert("RGB"), dtype=np.float32)
    lum = a @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    H, W = lum.shape
    r = max(2, int(min(H, W) * 0.02))
    ring = np.concatenate([lum[:r, :].ravel(), lum[-r:, :].ravel(),
                           lum[:, :r].ravel(), lum[:, -r:].ravel()])
    thr = float(np.median(ring)) + 10.0          # 桌面中位数 + 台阶
    bright = lum > thr
    colf, rowf = bright.mean(0), bright.mean(1)

    def span(frac, t=0.45):
        idx = np.where(frac > t)[0]
        if len(idx) < 8:
            return None
        return int(idx[0]), int(idx[-1])

    cs, rs = span(colf), span(rowf)
    if not cs or not rs:
        return None
    x0, y0, x1, y1 = cs[0], rs[0], cs[1], rs[1]
    if (x1 - x0) < W * min_cover or (y1 - y0) < H * min_cover:
        return None
    # 完整性只验**四条边带**——不能验整框覆盖率：画面内容本身比纸暗，
    # 主体一大就会把整框覆盖率拉爆（合成图实测 0.5 → 误判失败）
    bh, bw = y1 - y0, x1 - x0
    bands = (bright[y0:y0 + int(bh * 0.22), x0:x1],
             bright[y1 - int(bh * 0.22):y1, x0:x1],
             bright[y0:y1, x0:x0 + int(bw * 0.22)],
             bright[y0:y1, x1 - int(bw * 0.22):x1])
    if float(np.mean([b.mean() for b in bands])) < 0.45:
        return None
    return (x0 + 2, y0 + 2, x1 - 2, y1 - 2)


def ink_mask(a):
    """暖炭褐墨迹判据：偏暗、微暖（R 略大于 B）。齿孔里的桌面灰 R-B≈0 不会误报。"""
    lum = a @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    rb = a[:, :, 0].astype(np.float32) - a[:, :, 2].astype(np.float32)
    return (lum < 195) & (rb > 8) & (rb < 62)


def _largest_internal_gap(rows):
    """rows: 1D bool（每行是否有墨）。返回首末 True 之间最大的连续 False 段长度。"""
    idx = np.where(rows)[0]
    if len(idx) < 2:
        return 0, None
    gaps = np.diff(idx)
    k = int(np.argmax(gaps))
    return int(gaps[k] - 1), (int(idx[k]), int(idx[k + 1]))


def _centric(pts, lo, hi):
    """质心相对区间中点的偏移比例（0=正中）。pts 为坐标数组。"""
    if len(pts) == 0:
        return None
    c = float(np.mean(pts))
    return abs(c - (lo + hi) / 2) / max(hi - lo, 1)


class QC:
    def __init__(self):
        self.items = []

    def add(self, name, ok, detail, level="check"):
        """level: check(计入退出码) / info"""
        status = ("INFO" if level == "info" else ("PASS" if ok else "FAIL"))
        self.items.append((status, name, detail))
        return ok

    @property
    def fails(self):
        return sum(1 for s, _, _ in self.items if s == "FAIL")

    def text(self):
        lines = []
        for s, n, d in self.items:
            lines.append(f"[{s}] {n}: {d}")
        lines.append("-" * 56)
        lines.append(f"FAIL {self.fails} 项" if self.fails else "全部通过")
        return "\n".join(lines)


def _content_central(im, paper):
    """内容 bbox：高频剖面 + **最长连续段**——把纸边上的细文字带从内容里剔除。

    直接用 find_paper 会把标题/发行行当成内容起点（成图纸边里本来就有文字），
    纸边测量被吃掉。文字带与画面之间隔着整条空白纸边，连续段天然落选。
    """
    x0, y0, x1, y1 = paper
    sub = im.crop(paper)
    g = np.asarray(sub.convert("L"), dtype=np.float32)
    hi = np.abs(g - np.asarray(sub.convert("L").filter(ImageFilter.GaussianBlur(6)),
                               dtype=np.float32))
    Hs, Ws = hi.shape

    def prof_run(prof, axis_len):
        skip = max(3, int(axis_len * 0.02))       # 跳过齿孔峰
        p = prof[skip:]
        k = max(3, int(axis_len * 0.004) | 1)     # 平滑掉逐列/逐行抖动
        p = np.convolve(p, np.full(k, 1.0 / k), mode="same")
        base = float(np.percentile(p, 10))    # 纸底噪声锚：纸边合计 ≥16% 轴长，p10 必在纸上
        peak = float(np.percentile(p, 90))
        if peak - base < 1.5:
            return None
        # 阈值锚定 p10 + 绝对下限。两个实测教训：
        # ① 画面可占轴长 76%，p25/p50 会落进画面分布里（实测 X 剖面 p25=7.2
        #    就是画面本身），百分比「纸底锚」整体失效；
        # ② 画面内部幅值（8–11）比竖排文字列（12–27）还低，
        #    任何「峰值的 45%」类阈值都会把画面整段切掉。
        t = base + max(3.0, (peak - base) * 0.30)
        idx = np.where(p > t)[0]
        if len(idx) < 8:
            return None
        runs, s, prev = [], idx[0], idx[0]
        tol = max(4, int(axis_len * 0.01))        # 允许 ~1% 缺口
        for i in idx[1:]:
            if i - prev > tol:
                runs.append((s, prev))
                s = i
            prev = i
        runs.append((s, prev))
        a_, b_ = max(runs, key=lambda r: r[1] - r[0])
        return skip + int(a_), skip + int(b_)

    cx = prof_run(hi.mean(0), Ws)
    cy = prof_run(hi.mean(1), Hs)
    if not cx or not cy:
        return paper
    return (x0 + cx[0], y0 + cy[0], x0 + cx[1], y0 + cy[1])


def main():
    ap = argparse.ArgumentParser(description="邮票一次成片可复现质检")
    ap.add_argument("src", help="成片 PNG")
    ap.add_argument("--size", default="1536x1024", help="目标尺寸 WxH")
    ap.add_argument("--size-tol", type=float, default=0.05, help="尺寸容差（比例）")
    ap.add_argument("--min-v", type=float, default=0.10, help="上下纸边硬约束")
    ap.add_argument("--min-h", type=float, default=0.08, help="左右纸边下限")
    ap.add_argument("--max-offset", type=float, default=2.0, help="居中偏移上限（%%）")
    ap.add_argument("--perf-min", type=float, default=18.0, help="齿孔行波动下限")
    ap.add_argument("--tex-min", type=float, default=6.0, help="纸纹高频 std 下限")
    ap.add_argument("--paper-frame", default=None,
                    help="纸面矩形（画幅比例 fx0,fy0,fx1,fy1），检测失败时手动指定")
    ap.add_argument("--bands", default=None, help="导出放大字带到此目录（拼写核对用）")
    ap.add_argument("--json", default=None, help="结果另存 JSON")
    a = ap.parse_args()

    im = Image.open(a.src).convert("RGB")
    W, H = im.size
    arr = np.asarray(im, dtype=np.float32)
    M = ink_mask(arr)
    qc = QC()

    # ---- 尺寸（H：实测出过 3 种尺寸，加容差） ----
    ew, eh = (int(v) for v in a.size.lower().split("x"))
    ok = abs(W - ew) / ew <= a.size_tol and abs(H - eh) / eh <= a.size_tol
    qc.add("尺寸", ok, f"{W}x{H}（目标 {ew}x{eh}，容差 ±{a.size_tol:.0%}）")

    # ---- 纸面 / 内容 bbox ----
    paper = None
    if a.paper_frame:
        fx = tuple(float(v) for v in a.paper_frame.split(","))
        paper = (int(fx[0] * W), int(fx[1] * H), int(fx[2] * W), int(fx[3] * H))
    else:
        paper = find_paper_sheet(im)
    content = _content_central(im, paper) if paper else find_paper(im)

    if paper is None:
        qc.add("纸面检测", False,
               "自动检测失败，纸边/五区/齿孔检查跳过；用 --paper-frame 重跑", "info")
        print(qc.text())
        sys.exit(1 if qc.fails else 0)

    px0, py0, px1, py1 = paper
    cx0, cy0, cx1, cy1 = content
    # 防空带：内容 bbox 贴住纸边时切片为空会出 nan
    cx0 = min(max(cx0, px0 + 3), px1 - 4)
    cx1 = max(min(cx1, px1 - 3), px0 + 4)
    cy0 = min(max(cy0, py0 + 3), py1 - 4)
    cy1 = max(min(cy1, py1 - 3), py0 + 4)
    pw, ph = px1 - px0, py1 - py0

    # ---- 纸边（H：上下硬约束 / 左右下限） ----
    mt = (cy0 - py0) / ph
    mb = (py1 - cy1) / ph
    ml = (cx0 - px0) / pw
    mr = (px1 - cx1) / pw
    qc.add("上纸边", mt >= a.min_v, f"{mt:.1%}（硬约束 ≥{a.min_v:.0%}）")
    qc.add("下纸边", mb >= a.min_v, f"{mb:.1%}（硬约束 ≥{a.min_v:.0%}）")
    qc.add("左纸边", ml >= a.min_h, f"{ml:.1%}（下限 ≥{a.min_h:.0%}）")
    qc.add("右纸边", mr >= a.min_h, f"{mr:.1%}（下限 ≥{a.min_h:.0%}）")

    # ---- 分区 ----
    top = (slice(py0, cy0), slice(px0, px1))
    bot = (slice(cy1, py1), slice(px0, px1))
    lft = (slice(py0, py1), slice(px0, cx0))
    rgt = (slice(py0, py1), slice(cx1, px1))

    # ---- 五区占用 ----
    for nm, zn, floor in (("顶部标题带", top, 0.001), ("底部发行行带", bot, 0.001),
                          ("左竖排带", lft, 0.0005), ("右竖排带", rgt, 0.0005)):
        cov = float(M[zn].mean())
        qc.add(f"五区·{nm}", floor <= cov <= 0.35,
               f"墨迹覆盖 {cov:.2%}（预期 {floor:.2%}–35%）")

    # ---- 右侧两段间隔 ≥5%H（叠字事故区） ----
    # 行区间截到「内容底 +3%」：再往下是底部发行行带，会混进来当第二簇——
    # 实测旧版把发行行尾巴当成了中段，中段居中误报 29.85%
    rgt_cut = min(py1 - 4, cy1 + int(ph * 0.03))
    rrows = M[(slice(py0, rgt_cut), slice(cx1, px1))].any(axis=1)
    gap_px, span = _largest_internal_gap(rrows)
    real_split = gap_px >= 0.02 * ph
    ok = gap_px >= 0.05 * H and rrows.any()
    where = f"（两簇行区间 {span}）" if span else ""
    qc.add("右侧两段间隔", ok, f"最大空白 {gap_px}px = {gap_px / H:.1%}H，要求 ≥5%H {where}")

    # ---- 居中 ----
    # 横排带只看中央 64% 宽：外圈 18% 是竖排轨道（logo/署名也落在上带），
    # 不剔除会被侧栏墨迹拖偏。
    # ⚠ np.where 对切片数组返回「切片内相对坐标」，必须加回偏移转绝对值
    #   再与纸面中线比——旧版直接比，全部居中项都在报假偏移
    inw = int(pw * 0.18)
    ys, xs = np.where(M[(slice(py0, cy0), slice(px0 + inw, px1 - inw))])
    off = _centric(xs + px0 + inw, px0, px1) if len(xs) else None
    qc.add("顶部居中", off is not None and off <= a.max_offset / 100,
           f"偏移 {off:.2%}" if off is not None else "未检出墨迹")
    ys, xs = np.where(M[(slice(cy1, py1), slice(px0 + inw, px1 - inw))])
    off = _centric(xs + px0 + inw, px0, px1) if len(xs) else None
    qc.add("底部居中", off is not None and off <= a.max_offset / 100,
           f"偏移 {off:.2%}" if off is not None else "未检出墨迹")
    # 竖排带只看「内容行区间」：上带里的 logo/标题尾巴剔除后，竖排文字
    # 本就垂直居中于纸面
    ys, xs = np.where(M[(slice(cy0, cy1), slice(px0, cx0))])
    off = _centric(ys + cy0, py0, py1) if len(ys) else None
    qc.add("左竖排居中", off is not None and off <= (a.max_offset + 1) / 100,
           f"纵向偏移 {off:.2%}" if off is not None else "未检出墨迹")
    # 右侧只验中段簇（上段署名本来就偏上）；无 ≥2%H 真分隔时不硬分簇
    if real_split and span:
        mid = slice(span[1], None)
        ys2 = np.where(rrows[mid])[0] + span[1] + py0
        off = _centric(ys2, py0, py1)
        qc.add("右竖排中段居中", off is not None and off <= (a.max_offset + 1) / 100,
               f"纵向偏移 {off:.2%}" if off is not None else "未检出")
    else:
        qc.add("右竖排中段居中", True, "右栏无 ≥2%H 分隔（单簇连续墨迹），中段居中不适用",
               "info")

    # ---- 齿孔行波动 + 齿孔带文字入侵 ----
    band = max(3, int(0.035 * min(pw, ph)))
    g = np.asarray(im.convert("L"), dtype=np.float32)
    perfs = {}
    for nm, row_or_col in (
            ("上", g[py0 + band // 2, px0:px1]),
            ("下", g[py1 - band // 2, px0:px1]),
            ("左", g[py0:py1, px0 + band // 2]),
            ("右", g[py0:py1, px1 - band // 2])):
        perfs[nm] = float(np.std(row_or_col))
    worst = min(perfs.values())
    qc.add("齿孔行波动", worst >= a.perf_min,
           f"四边 std {[f'{k}{v:.0f}' for k, v in perfs.items()]}，最低 {worst:.0f}（≥{a.perf_min:.0f}）")
    # 齿孔带入侵只看「纸边最外一条齿孔带」薄环：旧版误用整个 margin 区，
    # 标题/发行行墨迹（本该在纸边带内侧）被误判入侵 14%+
    for nm, zn in (("上", (slice(py0, py0 + band), slice(px0, px1))),
                   ("下", (slice(py1 - band, py1), slice(px0, px1))),
                   ("左", (slice(py0, py1), slice(px0, px0 + band))),
                   ("右", (slice(py0, py1), slice(px1 - band, px1)))):
        cov = float(M[zn].mean())
        qc.add(f"齿孔带入侵·{nm}", cov <= 0.02, f"墨迹 {cov:.2%}（≤2%）", "check")

    # ---- 纸纹高频 std（四条纸边浅条各测，取最干净的一条） ----
    # 纸是同一张：任何单条都可能被标题/发行行/竖排的「反锯齿半墨边缘」
    # 污染（实测上条被标题抬到 12.0 假 PASS），取 min 就是取到真纸面；
    # 浅条深度 ≤40px，物理上碰不到画面（内容检测偏小时也不误吞画面）
    depth = min(mt * ph, mb * ph, ml * pw, mr * pw)
    tex_h = max(8, min(int(depth * 0.35), 40))
    cw, ch = int(pw * 0.15), int(ph * 0.15)

    def _strip_std(sl):
        sarr = g[sl]
        blur = np.asarray(Image.fromarray(sarr.astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(6)), dtype=np.float32)
        resid = np.abs(sarr - blur)
        msk = ~(M[sl] | (sarr < 210))       # 半墨边缘像素一并排除
        if msk.sum() <= 50:
            return None
        return float(resid[msk].std())

    strips = (
        (slice(py0 + band + 2, py0 + band + 2 + tex_h), slice(px0 + cw, px1 - cw)),
        (slice(py1 - band - 2 - tex_h, py1 - band - 2), slice(px0 + cw, px1 - cw)),
        (slice(py0 + ch, py1 - ch), slice(px0 + band + 2, px0 + band + 2 + tex_h)),
        (slice(py0 + ch, py1 - ch), slice(px1 - band - 2 - tex_h, px1 - band - 2)),
    )
    stds = [s for s in (_strip_std(sl) for sl in strips) if s is not None]
    std = min(stds) if stds else -1.0
    qc.add("纸纹高频std", std >= a.tex_min,
           (f"{std:.1f}（四边取最小；≥{a.tex_min:.0f}，≈3 以下基本是塑料）" if std >= 0
            else "干净纸区不足，无法测纸纹"))

    # ---- 导出放大字带（拼写人工核对） ----
    if a.bands:
        os.makedirs(a.bands, exist_ok=True)
        crops = {
            "top": im.crop((px0, py0, px1, cy0)),
            "bottom": im.crop((px0, cy1, px1, py1)),
            "left": im.crop((px0, py0, cx0, py1)),
            "right": im.crop((cx1, py0, px1, py1)),
        }
        for nm, c in crops.items():
            c = c.resize((c.width * 2, c.height * 2), Image.LANCZOS)
            c.save(os.path.join(a.bands, f"band_{nm}.png"))
        qc.add("字带导出", True, f"{os.path.abspath(a.bands)}（4 条，2×，逐字核对拼写）", "info")

    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump([{"status": s, "check": n, "detail": d} for s, n, d in qc.items],
                      f, ensure_ascii=False, indent=1)

    print(qc.text())
    sys.exit(1 if qc.fails else 0)


if __name__ == "__main__":
    main()
