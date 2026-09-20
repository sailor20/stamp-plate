# image2 提示词模板

出图阶段一次只喂**一张**参考图。喂两张（内容 + 风格）会稳定返回 `upstream_error`。

**模板索引**：**阶段 2 ★一次成型整票（主产线，默认走这条）** → 3b 主题彩蛋 →
1 基础版式 → 1b 边缘收拾 + 纸纹 → 1c / 1c-2 刺绣边框支线（含遮罩收边）→
1d 边框精化遮罩。

**每个出图 prompt 按五段式拼装**（对应 SKILL.md「决策清单 / Prompt 结构」）：
① 源图保真 ② 邮票方向（纸 / 齿孔 / 倾斜投影 / 纸边宽度）③ 材质 / 图形
（纸纹 / 针脚框 / 彩蛋）④ **排版规格（五区文字，逐区位置+限长+字号）**
⑤ 禁止项。各阶段模板即五段的预制件，按版式取用组合。

---

## 阶段 2 · 一次成型整票（★主产线：纯提示词 + 参数预设，零 Python）

一条提示词直接生成完整邮票：纸、齿孔、针脚框、全部排版文字、邮戳。
调用 `image2 edit_image`：只喂用户这一张参考图、`n=1`、`size 1536x1024`。

**两种等价主模式**：
- **纯提示词**：agent 按五段式直接组一条完整提示词（快速出票）；
- **提示词 + 参数预设**（默认推荐）：先选 `themes/*.json` 现成主题，
  再对模板做**机械替换**——字符串零手误。

**模板唯一真源 = `references/stage2_template.txt`（占位符版）。不要手抄改写**
——手抄改错一处就是自造词。默认组装 = agent 读模板原文 + 主题 JSON，
按下方替换表**机械替换** 13 个占位符，替换后通读一遍，**确认没有 `{{` 残留**。

### 第 1 步 · 选主题参数预设

`themes/*.json`（9 套，覆盖 3b 全部 8 类景色）：
`coastal / hilltown / avenue / meadow / snow / lake / desert / garden`
+ `coastal_cn`（CJK 中文侧串版；**全部 9 套面值单位一律中文：分 / 元**）。
字段 = `key / name / title / series / year / values(候选面值数组，中文单位) /
side_left / side_right / engraver / postmark_name / postmark_date /
eggs(3 条英文) / egg_note / ink`。
自定义景色 = 仿照任一 JSON 只换 B 串，A 串不动；eggs 必须给足 3 条。

### 第 2 步 · 占位符替换表

| 占位符 | 替换为 | 说明 |
|---|---|---|
| `{{FIDELITY_BLOCK}}` | 保真段 F / P / O（预设全文见下） | 布艺输入用 F；照片输入用 P；用户点名「油画化 / 莫奈 / 梵高」用 O |
| `{{ARTWORK_NOUN}}` | `painting` 或 `photograph` | 与保真段同侧：F→painting，P→photograph，O→painting |
| `{{EGG_BLOCK}}` | 彩蛋段三态之一（预设全文见下） | fabric / photo_margin / photo_clean |
| `{{POSTMARK_BLOCK}}` | 邮戳段（预设全文见下） | 信销样=替换；新票=替换成空（第 6 段整段消失） |
| `{{TITLE}}` `{{SERIES}}` `{{YEAR}}` | JSON 同名字段 | B 串，加引号锁死 |
| `{{VALUE}}` | JSON `values` 数组**随机取一** | B 串，加引号锁死；**每次出票换一个**，不沿用上一次的票；单位一律中文（分 / 元） |
| `{{INSCRIPTION}}` | `AIR MAIL` 或 `POST`（按画面内容二选一） | 模板自带词对视为已授权：**仅当飞行器是画面明确主体**（飞机 / 飞艇 / 热气球 / 滑翔机 / 风筝）或明确航空邮政语境 → `AIR MAIL`；**开阔天空、远景飞鸟不构成 AIR MAIL**，普通风景一律 → `POST` |
| `{{SERIAL}}` | 6 位随机数字（每次出票换一个） | 纯数字串无自造词风险（模板里格式为 `No. {{SERIAL}}`） |
| `{{SIDE_LEFT}}` `{{ENGRAVER}}` `{{SIDE_RIGHT}}` | JSON 同名字段 | A 串，不改写、不改拼写 |
| `{{POSTMARK_NAME}}` `{{POSTMARK_DATE}}` | — | **模板正文没有这两个占位符**，只出现在邮戳段文本内部 |

**模式开关的零 Python 等价操作**：照片输入 = P 保真段 + `photograph` +
彩蛋段选 photo 态；新票 = 邮戳段替换成空；叠字补强 = 提示词末尾追加
STRICT 段（预设全文见下）；油画化 = O 保真段 + `painting`（egg 段措辞里
photograph 同步改为 painted artwork）。
**经典元素四件已写死在模板正文**（顶部铭文占位 `{{INSCRIPTION}}` /
底部雕刻信息条 + 序列号 `{{SERIAL}}` / 边框右下盖销波线）——随替换自动
带入，无需额外操作；盖销波线是版面固有设计，与可选的圆形邮戳互不影响。

### 第 3 步 · 分段文本预设（逐字照抄，`<尖括号>` 处填 JSON 值）

**【保真段 F · 布艺输入】**

```
1. KEEP THE ARTWORK — CRITICAL: do not move, redraw or restyle the landscape,
   the cloth patches or the threads. Copy the artwork pixel for pixel into the
   centre of the stamp. The stamp is only the paper and lettering around it.
```

**【保真段 P · 照片输入】**（默认措辞会把照片布艺化，照片必须换这段）

```
1. KEEP THE PHOTOGRAPH — CRITICAL: do not move, redraw, restyle or re-light
   the photograph. It is a PRINTED PHOTOGRAPH mounted at the centre of the
   stamp: do NOT turn it into a fabric collage and do NOT add cloth patches,
   embroidery, stitches or threads inside it. Copy the image pixel for pixel.
   The stamp is only the paper and lettering around it.
```

**【保真段 O · 油画化主体】**（用户点名「油画化 / 莫奈 / 梵高」才用。
两个要点：**必须点名谁负责哪块**——只写 fusing Monet and Van Gogh 两个
标签并联，模型会把整张统一成中间态，既无莫奈的光也无梵高的力，正确写法
= 同一支笔在不同对象上的不同笔势；**过渡句必写**——否则画面某个高度会
出现两风硬接的分界）

```
1. THE ARTWORK — repaint the photograph as an OIL PAINTING in the fused style
   of Monet and Van Gogh. Keep the composition, the horizon and every element
   of the scene exactly where they are, but render the scene with oil paint on
   canvas. One continuous painting in two hands: the SKY and the WATER are
   MONET — short broken strokes of juxtaposed colour, optical mixing, soft
   edges, airy light, quietly flowing; the CLOUDS, the HEADLAND and the
   FOREGROUND vegetation are VAN GOGH — thick impasto swirls, strokes
   following the form of what they paint, visible paint ridges with small
   shadows, a few dark contour lines, gold against blue. The foreground
   brushwork is the boldest and most sculpted; the water keeps finer broken
   dabs. Transitions between the two hands are gradual — one continuous
   painting, not two styles pasted together.
```

**【彩蛋段 · 三态】**（`<e1> <e2> <e3>` = JSON `eggs` 三条，逐字填入）

fabric 态（布艺输入，画内同技法彩蛋）：

```
5. HIDDEN DETAILS: add ONLY three tiny hidden details worked in the same
   fabric-and-thread technique as the artwork, each no bigger than two or
   three stitches across: <e1>; <e2>; <e3>.
   Genuinely tiny, discoverable only on close inspection.
```

photo_margin 态（照片输入但保留彩蛋，画在纸边下角、不碰照片）：

```
5. HIDDEN DETAILS: three tiny stitched motifs worked ON THE BLANK PAPER
   margin at the lower corners — never on the photograph itself: <e1>; <e2>;
   <e3>. Each no bigger than two or three stitches across.
```

photo_clean 态（照片输入、无彩蛋）：

```
5. NO HIDDEN DETAILS: keep the photograph itself completely clean — no
   added motifs, stitches or objects on the image area.
```

**【邮戳段】**（新票整段不要）

```
6. POSTMARK: a round semi-transparent cancellation postmark at the lower
   right, overlapping ONLY the artwork's lower-right corner and the paper
   just below it — it must NOT touch any lettering. A fine circle, the name
   "<postmark_name>" in small capitals, three wavy cancellation
   lines, and the date "<postmark_date>".
```

**【STRICT 段 · 叠字补强】**（追加在整条提示词**末尾**）

```
STRICT: the right margin carries TWO separate lines — "<engraver>" ends within
the top quarter; "<side_right>" occupies only the middle half. Shrink both to
cap-height 1.6 percent of the image height. Visible blank paper must remain
between them and between every other pair of lines.
```

### A/B 串角色表（「禁止自造词」的客观判据）

提示词里每个引号串必须逐字来自下表：

| 类 | 字段 | 规则 |
|---|---|---|
| **A 固定串** | `side_left` `engraver` `postmark_name` `postmark_date` `year` `inscription`(二选一) | 模板自带虚构专名（LITO 系列、`ENGRAVED BY A. MOREL`、`14 - IX - 2026`、`AIR MAIL`/`POST`）**视为已授权**：随主题原样用，不随景色改写、不改动拼写；日期间隔点一律连字符 `-`（`·` 会变方框）。**序列编号 = `No.` + 6 位随机数字**，纯数字串不参与 A∪B 判据 |
| **B 专名位** | `title` `series` `values`(随机取一) `side_right` `eggs`（3 条） | 随景色重写，换景只动这一类；重写后同样加引号锁死 |

**多图输入**：永远只喂一张（喂两张稳定 `upstream_error`）。多张素材先用
贴图/画图软件手动拼成一张再喂；风格参考写成文字写进提示词，
不找第二张风格图。

### 质检与修正（目检）

按 SKILL.md「质量门」清单逐项目检：尺寸 ±5% / 纸边上下 ≥10% 硬·左右 ≥8% /
五区占用 / 右侧两段间隔 ≥5%H / 居中 ≤2–3% / 齿孔行波动 ≥18 / 纸纹高频 std ≥6 /
齿孔带入侵 ≤2%；**拼写没有目测捷径**——放大 2× 逐字人工核对（可截图字带）。
面值单位一律中文（`分` / `元`）——中文字符落在雕刻版英文字环境里可能
笔画粘连、变形或缺笔，放大 2× 专门核对 `分`/`元` 字形；判错标准是
数字或单位缺失、错位、错数字（如 60 被画成 90）。
修正走 SKILL.md「失败修正决策树」：局部修复优先（末尾追加 STRICT 段重出），
重出后强制全量目检。

---

## 阶段 1 · 把基底换成邮票纸

以「已做好的布艺拼贴作品」为内容参考：

```
Put the whole fabric-collage artwork onto a REAL POSTAGE STAMP viewed flat from
directly above, filling the frame. The stamp sheet is warm ivory-cream laid
paper, matte and slightly fibrous, gently aged, with a couple of very soft
pale-tan fox marks.

Around all four sides of the stamp sheet, cut a row of PERFORATION HOLES — the
classic punched round scalloped edge. The holes are small, round, evenly spaced
and punched clean through the paper, each with a tiny shadow inside it and a
faintly fuzzy raised paper rim, exactly as a perforating machine cuts. Leave a
few of the perforations slightly irregular or partially torn at the corners so
it looks real rather than a perfect digital die-cut.

Leave a generous CLEAN UNPRINTED MARGIN of bare stamp paper between the
perforated edge and the artwork — wider at the top and bottom than at the sides,
so the stamp proportions read correctly and the perforated edge does not crowd
the artwork.

Beyond the perforated edge the stamp rests on a very slightly darker warm
neutral surface, so the paper reads as a physical object lying on a table.
```

**必加的一句**（不加会加框或重画景物）：

```
CRITICAL: do not move, redraw or restyle the landscape, the cloth patches or the
threads. They must remain EXACTLY as they are. The stamp is only the paper
underneath. No stitched border, no fabric frame, no added trim inside the
perforation.
```

**负面必须排除邮政元素**——一写 text 就会生成面值和国名。实测还要防模型
**擅自把整套排版画上**：一次成型的字必然翻车——竖排两列叠字、字符错形
（间隔点变方框）、齿孔画成灰色椭圆团。出图前必须显式锁死：

```
The stamp paper must arrive COMPLETELY BLANK: no title, no words, no letters,
no numbers, no typography of any kind anywhere on it — all type is added later
in a separate typesetting step.

AVOID: text, letters, numbers, postal markings, postmark, cancellation marks,
denomination, country name, currency, watermark, logo, hard black shadow,
changing the artwork, changing the landscape, adding a textile border.
```

---

## 阶段 1b · 边缘收拾方整 + 纸纹加强

```
1. TIDY THE EMBROIDERED EDGE. Keep it hand-torn and frayed, but make it TIDIER
   and MORE CONTAINED — a squarer, more rectangular overall footprint with only
   modest irregularity: the fabric edge should roughly follow a rectangle, with
   gentle wavering of a centimetre or so rather than large jutting lobes. Corner
   areas especially should be more squared off. Keep the subtle fraying, the
   loose fibres and a few stray threads, but reduce their quantity and length
   considerably.

2. MAKE THE STAMP PAPER MORE REALISTIC. A genuine fine wove / laid paper TEXTURE
   at close range — a very fine, faint mesh of laid lines or a subtle fibrous
   grain, visible across the whole sheet including the blank margin. A faint,
   uneven natural tone variation across the sheet: slightly lighter in the middle
   and very marginally warmer toward the edges, as real aged paper oxidises. A
   very slight physical thickness — a hairline pale edge on one side of the
   perforations so the paper reads as a real cut sheet.

3. PERFECT THE PERFORATION. Round holes of perfectly consistent diameter and
   even spacing, punched cleanly through, each showing a soft inner shadow and a
   very faintly fuzzy, slightly rounded paper rim where the fibers were cut.
```

---

## 阶段 1c · 刺绣边框 + 内部纯油画（主体边框版式）

**用途**：把画面的**边框**做成刺绣（而不是让整幅都布艺化），
边框内部的画面保持纯油画、不含任何刺绣元素。

**第一步 · 重做边框**（输入 = 一张「纯油画 + 素麻边框」的图，如 `deco-fusion-bay-c.png`）：

```
Rework ONLY the embroidered border. Keep the LANDSCAPE PAINTING INSIDE
COMPLETELY UNCHANGED — every brushstroke, colour and detail stays exactly as it is.

CRITICAL: the landscape inside is an OIL PAINTING — pure brushwork on canvas.
There must be NO fabric, NO cloth patches, NO embroidery, NO stitches, NO threads,
and NO textile texture anywhere inside the picture area. Only the BORDER is
embroidered.

Give the artwork a MODERATE, EVEN hand-embroidered border, roughly 8 to 9 percent
of the image width on the left and right, and 11 to 12 percent at the top and
bottom — a balanced frame that is clearly visible but does not dominate. The
border is a simple natural-linen ground with ONE clean band of even running
stitches following the frame, a single line of small cross-stitches spaced along
it, and small corner squares worked in cross-stitch. Keep the embroidery
restrained and functional — a quiet stitched edge, not ornate trim.

The inner edge where the embroidery meets the painting is a gently wavering
hand-worked line of thread, not a machine-straight seam. The outer edge is
squarer and more contained — roughly rectangular with only modest hand-made
irregularity.

Stitch colour: a single muted sage-olive thread, quiet and natural, one to two
stops below poster brightness, so it does not compete with the painting.

AVOID: changing the landscape, restyling the painting, any embroidery or fabric
texture inside the picture, ornate floral embroidery, cartoon, illustration,
glowing or neon colours, glossy varnish, hard black shadows, modern graphic
design, text or lettering.
```

**第二步 · 装进邮票结构**（把上一步的成图当输入；**纸边必须写宽**）：

> ⚠️ **这一步最容易失败**：只写 `do not change the embroidery` 时，模型会把刺绣
> 整个丢掉、退化成「油画印在邮票纸上」。必须改用 **outpainting 措辞**，并且
> **正面点名要保留什么**（写明布底、跑针、线色），而不能只写「不要改」。

```
Extend the canvas outward to turn this into a real POSTAGE STAMP viewed flat from
directly above. Do NOT regenerate the image — simply ADD a surrounding area around
the existing embroidered artwork, exactly like an outpainting extension.

KEEP THE EXISTING ARTWORK COMPLETELY UNCHANGED: its oatmeal linen border cloth, its
fine pale running-stitch embroidery wandering across the border, its colours and its
oil-painted landscape in the middle. Copy them over pixel for pixel.

Around the artwork, extend out a WIDE, GENEROUS frame of bare warm ivory-cream laid
stamp paper. The blank paper margin between the embroidered edge and the perforated
edge must be WIDE: approximately 12 to 14 percent of the total image height at the
TOP and BOTTOM, and approximately 9 to 10 percent of the total image width at the
LEFT and RIGHT.

Around all four sides, cut a row of PERFORATION HOLES ... (同阶段 1 的齿孔段)

CRITICAL: the embroidered textile is a finished physical object lying ON the stamp
paper. Do not move it, do not redraw it, do not restyle it, do not add any trim,
new border or additional stitching.

AVOID: regenerating or restyling the artwork, losing the embroidery, replacing the
stitched border with blank paper, narrowing the paper margin, any new stitching,
text, letters, numbers, postal markings, logo, hard black shadow.
```

> 这一步的**纸边宽度是成败关键**。只留 3–5% 的纸边，本地排版时
> `strip_type` 会连刺绣一起抹掉、文字压到刺绣上，整张废掉。
> 出图后量纸面 bbox（亮度 >200）确认四周留白在 9–14%。

### 边框粗细三档

| 档位 | 占比 | 刺绣写法关键词 | 适合 |
|---|---|---|---|
| 宽边重绣 | 左右 14–16%、上下 13% | `DENSE, RICH... rows of even running stitches, bands of satin stitch, a repeating small cross-stitch pattern, and a restrained botanical vine motif` | 边框当主体 |
| 细线自由跑针 | 左右 11%、上下 11–12% | 见下节「细线跑针」的完整写法 | **最接近手工布艺原味** |
| 适中边框 | 左右 8–9%、上下 11–12% | `ONE clean band of even running stitches, a single line of small cross-stitches, small corner squares in cross-stitch` | 默认推荐 |
| 窄边满绣 | 左右 9–10% | `SOLIDLY COVERED with embroidery, worked edge to edge with no bare linen showing: saturated fill stitch, fine counted-thread darning, a dense seed stitch` + `tiny stitched flowers, little leaves and small berries` | 画面要更大 |

配色一律：`muted sage green, faded olive, dusty pale blue, warm ochre` +
`one to two stops below poster brightness, dusty rather than vivid`。

### 1c-2 · 细线跑针（最像手工布艺的那一档）

**特征**：单股极细的浅色线，**一小段一小段的短跑针**（每段 2–3 mm，彼此分离），
疏而透、不密，像随手涂鸦一样**在整个边框上游走**，偶尔留有线头。
不是缎面绣，不是十字绣，不是连续匀称的一圈。

**三条硬约束**（缺任一条都会失败）：
1. **只作用于外轮廓边框**，主体内部零刺绣
2. **主体撑满边框内区，与针区 0 间距** —— 针脚直接贴画面边缘，中间无素麻带
3. **密度全程均匀**，不能局部过密

**推荐做法：遮罩环形收边（比整图重写可控得多）**。
量出画面矩形与针区内缘 → 构建环形遮罩（外缘越入针区 0.3–0.5%，
内缘缩进画面 1.2%）→ inpaint 填环 → 量实际 bbox → 残余细缝做第二轮窄环。

```
The masked band to repaint is the ring between the oil painting and the stitched
linen border. Fill that ENTIRE ring by EXTENDING THE OIL PAINTING outward on all
four sides, so the painting grows to fill the whole inner area of the linen border
and its new edge MEETS THE STITCHED BORDER DIRECTLY with zero gap — no bare linen
left between the painting and the stitching. The stitches must sit right against
the painted edge.

Continue the same bay scene naturally and seamlessly: more swirling sky with the
same clouds at the top, more open sea toward the left and right, more grassy
foreground with the same shrubs at the bottom. Use the SAME thick impasto oil
brushwork, the SAME palette and the SAME light as the existing painting — one
continuous painting, no visible seam where the old edge was.

EVERYTHING outside the ring must stay pixel-identical: the fine pale
running-stitch embroidery on the oatmeal linen border, the linen ground itself,
the blank warm ivory stamp paper margin, and the perforated edge. Do not redraw,
restyle or move any of them.

AVOID: changing the stitching or the linen, shrinking the painting, leaving any
bare linen ring inside the stitched border, hard black shadows, text, letters,
postal markings.
```

> 线色要从所在布片提亮，不要全边框一个色：帆布区 `pale straw`、
> 水面上方 `pale dusty blue`、草坡前 `pale bone`。主色 `off-white / bone / cream`。
> 单轮遮罩常见**单边欠填 1–2.4%**——量实际画面 bbox 后对残余细缝再做一轮窄环，
> 内矩形与上一版逐像素 diff ≈ 0 可确认遮罩保护生效。
>
> 实测配色锚点（亚麻底布采样）：底布 RGB(211,198,178) lum 200.4 sat 0.161；
> 天空布片 RGB(120,148,182) sat 0.375；水面布片 RGB(142,156,171) sat 0.246；
> 草坡布片 RGB(147,135,96) sat 0.359。
> **边框整体饱和度必须低于画面**（实测 0.21–0.24 vs 画面 0.16–0.18 之间取平衡，
> 边框略高但靠细线降低视觉重量），否则边框抢主体。

---

## 阶段 1d · 边框精化（在成图上重画边框与纸边）

**用途**：成图已可用的前提下，把边框做得更精致（细描边 / 圆角 / 四角装饰纹样）、
把纸边压窄让排版更紧凑。**配遮罩使用**：PNG 透明 = 重绘、不透明 = 保留；
保留外圈齿孔框（到齿孔行外缘）与画面（内缩 1% 重叠带），只重绘中间环带。

**全环精化**（重画纸边 + 亚麻边框带）：

```
Repaint ONLY the masked ring between the perforated edge and the artwork — the
blank stamp paper margin and the embroidered linen border band. EVERYTHING else
must stay pixel-identical: the perforated edge with its punched holes, the blank
paper beyond it, and the oil painting in the middle.

Refine the linen border so it reads as a finer, more collectible stamp frame:
a THIN elegant double outline following the frame, GENTLY ROUNDED corners, and a
small diamond-shaped stitched ornament at each of the four corners. Keep the
hand-embroidered linen character — oatmeal linen ground, fine pale running
stitches — but make the band tidier and more even.

Geometry of the paper margins: the bottom paper margin should be the SAME WIDTH
as the top paper margin, and the right margin the SAME WIDTH as the left margin,
so the four margins read even and compact. The bottom linen band being one step
narrower than the others is intentional — do not widen it back.

AVOID: changing or redrawing the perforated edge, changing the artwork, new
text, postal markings, hard black shadows.
```

**L 形单边微调**（只动底带 / 右带，其余全保留）：遮罩只盖要改的 L 形区域，
prompt 换成（以底边为例）：

```
Repaint ONLY the masked band along the BOTTOM. Make the bottom paper margin wider
so it matches the top margin in width, by moving the bottom edge of the linen
border band slightly upward. The linen band, its stitches and the paper must keep
the same style as elsewhere in the image. Everything outside the mask stays
pixel-identical.

AVOID: touching the artwork, the perforated edge, or any other margin.
```

**三条硬经验**：

1. **几何指令给图内锚点**：「底边距 7%」会被执行成 5.5%，改口「12.5%」又过头
   （底边亚麻带只剩 15–26px）。改用「底边距 = 顶边距同宽、右边距 = 左边距同宽」
   + 声明底带窄一档是有意的——一次到位。
2. **量几何用 2% 网格叠图目视读数**：亮度阈值 / 饱和度 bbox / lum<205 连续段
   三代自动检测，全被齿孔暗点或浅色亚麻骗过。
3. **遮罩验证**：受保护区（齿孔框 + 画面）与上一版逐像素 diff 应 ≈ 0
   （本例三次全 0.000），才算真保护。

---

## 阶段 3 · 三段式字体排版

> 下块为海岸主题的**写死示范**；实际组装走阶段 2 主产线——
> 面值等 B 串一律来自主题 JSON（面值从 `values` 随机取一），不要照抄示范里的 "60"。

```
ADD AUTHENTIC STAMP TYPOGRAPHY. This is now a real postage stamp design and it
must be TYPESET like one, in the traditional dignified style of mid-century
engraved stamps. Use only classic print letterforms — a fine old-style or
transitional SERIF in capitals with generous letter-spacing, and a small
condensed sans-serif in small capitals for secondary text. The type is printed
in a single muted dark ink (a soft charcoal-sepia, around RGB 92,80,68),
letterpress-flat and slightly uneven from the old press, never bold, never
modern, never a display face.

· Along the TOP margin, above the artwork, centred: "THE BLUE BAY" — spaced
  capitals, small and fine.
· Along the BOTTOM margin, below the artwork, centred: the issuing line
  "POSTA · COASTAL SERIES", a numeral value "60", and a small year "2026".
· Running up the LEFT margin vertically and down the RIGHT margin vertically, in
  very small capitals: the series line and the style line.

The typography must sit in the blank margin, in the paper, and must NOT overlap
the artwork. Keep the type small and quiet — printed into the stamp as part of
its design, not added afterwards.
```

四条经验：

- **文字必须给确切字符串并加引号**。只写 "add the title" 模型会自己编词甚至拼错。
- **字体指定"年代 + 工艺"，不指定字体名**：
  `mid-century engraved stamps` + `letterpress-flat and slightly uneven from the
  old press` 才出得了微微压印的质感。
- **四边都用上**。只用底部一行会显得空；真邮票是把留白填满的。
- 负面排除：`modern or decorative fonts, script or handwriting, bold heavy type,
  drop shadows on text, glowing or embossed text, gradient ink, text overlapping
  the artwork`。

---

## 阶段 3b · 主题彩蛋

**尺寸必须显式声明**，否则模型会把它做成显眼主体。

```
Add ONLY three tiny hidden details, worked in the SAME embroidery and
cloth-collage technique, placed discreetly inside the landscape and kept very
small so they do not disturb the composition:

1. On the open water of the bay, a TINY SAILBOAT — a small pale triangle of cloth
   for the sail and a sliver of dark thread for the hull, no bigger than two or
   three stitches across.
2. Hidden among the dry grass and scrub in the lower right foreground, a SMALL
   SHELL — a little fan or spiral of pale stitched thread, just a few millimetres
   across, easy to miss at first glance.
3. On the pale sandy patch at the bottom left, three or four VERY FAINT TINY
   FOOTPRINTS in fine thread, small and half-erased.

CRITICAL: all three details must be made in the same hand-stitched
fabric-collage language as the rest of the picture — cloth, thread and stitches
only, no photorealistic objects, no illustration, no cartoon. They must be
genuinely TINY and subtle, discoverable only on close inspection.
```

### 换主题：彩蛋对照表

> 9 套内置主题的彩蛋已写进 `themes/*.json` 的 `eggs` 字段，替换
> `{{EGG_BLOCK}}` 占位符时自动带入——只有**自定义景色**才需要
> 从下表挑选后写进自己的 JSON。

换景色时把三条替换掉，**主题与彩蛋要对应**：

| 景色 | 彩蛋建议 |
|---|---|
| 海岸 / 海湾 | 微小帆船 · 贝壳 · 沙上脚印 |
| 山城 / 村镇 | 屋顶上的小旗 · 窗里的一点暖光 · 一只小猫 |
| 林荫道 | 落叶里的小蘑菇 · 一只鸟 · 树杈上的秋千 |
| 田野 / 草原 | 田埂上的稻草人 · 一捆干草 · 一只野兔 |
| 雪景 | 雪人 · 一行动物足迹 · 屋檐冰凌 |
| 湖 / 河 | 一叶小舟 · 水边的芦苇 · 垂钓的人影 |
| 沙漠 | 一具小兽骨 · 沙丘上的风纹 · 一株极小的花 |
| 花园 | 一只蜜蜂 · 半埋的花铲 · 掉落的花瓣 |

---

## 换风格速查

同一套骨架换个纸与齿，就成了另一种票：

| 目标 | 替换关键词 |
|---|---|
| 古董毛边纸票 | `deckle-edged handmade rag paper, soft feathered fibres, uncut edges` |
| 蜡纸 / 描图纸票 | `translucent vellum tracing paper, faint grid, soft crinkle` |
| 亚麻布面票 | `fine linen-backed stamp paper, visible weave under the print` |
| 金箔纪念票 | `matte gold foil stamp, embossed relief, unburnished antique gold` |
| 航空邮票 | `airmail stamp, blue and red striped border, heavier paper` |
| 首日封小全张 | `souvenir sheet, wide margin, engraved plate number in the corner` |
