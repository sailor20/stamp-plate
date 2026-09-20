---
name: stamp-plate
description: 把用户给的一张风景图（照片或布艺拼贴作品）对应生成一张真实感邮票成片（一图换一票）——暖象牙打孔齿边纸、贴画缘虚线针脚框、传统雕刻时代三段式字体排版、四轴可调质感（针法密度 / 做旧 / 齿孔完整度 / 邮戳）。当用户提到邮票、纪念票、齿孔、postage stamp、首日封、信销票、邮戳，或说「做成邮票样式」「把底层换成邮票」「做一个收藏票」时使用；也适用于任何「纸质物件 + 打孔边 + 传统印刷排版」的版式。关键约束：出图阶段纸面完全空白（文字一律本地排）、一次只喂一张参考图、画面景物像素级不动。
compatibility: 需要 Pillow 与 numpy。出图阶段用 image2 MCP（edit_image）；质感参数与排版在本地合成，确定性可复现。字体取自系统（Windows）。
---

# 邮票画册（stamp-plate）

**一句话定位**：把**一张**用户图（照片 / 布艺拼贴作品）变成**一枚**可以拿在手里的
邮票——画面像素级保真，纸、齿孔与岁月痕迹交给 image2，文字与排版**全部本地做**
（模型写字必然翻车：叠字、错形、齿孔画成灰团）。

## ★ 最终样式基准（用户拍板，2026-09-20）

skill 的**最终交付样式**以 `examples/final-style-reference.png` 为准：

- **画面**：布艺拼贴/油画风景，边缘以**一圈深色虚线跑针框直接贴住画缘**
  （basting 式矩形虚线）。**没有宽亚麻边框带、没有菱形角饰、没有花卉刺绣边。**
- **纸边**：干净暖象牙纸 + 齿孔；微倾斜 + 软投影，浮在灰调桌面上
- **排版**：三段式 + 四轴质感（`st / ag / pf / cx`）
- 「刺绣宽边框 + 菱形角饰」等版式一律视为**可选支线**，默认产线走基准样式；
  基准源票的出图模板见 `references/prompts.md` 阶段 1e
- sheet 标签与 `--preset` 都有英文别名（Mint / Standard / Used / Antique /
  Dense），无 CJK 字体的环境不会渲染出方框

---

## 路由 / 模式

- **默认模式：一图换一票**。用户给一张图 → 对应产出一张成片
  （样例 `examples/one-to-one-output.png`）。五档矩阵 `--sheet` 只是参数预览的
  **可选项**，不是默认交付。
- **特殊模式**：
  - `--sheet` 五档矩阵——用户想对比质感档位时才出
  - 边框精化支线（宽亚麻边框带 + 遮罩环）——仅当用户**明确要求**精致宽边框
  - `coastal_cn` 中文主题——用户要中文面值/侧边时
- **何时问**：①没有源图；②景色与海岸差很远且用户没给主题文案（标题/发行行/
  彩蛋要重写）；③用户要求与基准样式冲突（如要宽边框，确认是否走支线）。
- **何时不问**：参数、面值、年份用主题默认；版式直接走基准；修瑕疵类小改直接做。

## 加载参考

- **所有模式读**：本文件（路由 → 工作流 → 契约 → 质量门）。
- **出图前读**：`references/prompts.md` 阶段 1（基础版式）、1b（边缘收拾 + 纸纹）、
  **1e（★基准版式：虚线针脚框）**。
- **边框支线 / 修补读**：prompts.md 阶段 1c（刺绣边框 + 内部纯油画）、1c-2（细线
  跑针 + 遮罩收边）、1d（边框精化反向遮罩环）。
- **内容与彩蛋读**：本文件「本地合成与排版」的主题/彩蛋节 + prompts.md 阶段 3b。

## 工作流

1. **读取输入**：一张源图。没有 → 问。图上有水印/文字 → 先裁掉（inpaint 会留痕，
   实测横向取样也留痕，不修）。
2. **判断模式**：单张（默认）/ 矩阵 / 边框支线 / 瑕疵修补。
3. **选版式**：默认基准版式（虚线针脚框，prompts 1e）；用户点名才走宽边框支线。
4. **编译 prompt**：按「决策清单 / Prompt 结构」四段式拼装。
5. **生成**：`mcp__image2__edit_image`——**一次只喂一张参考图**（喂两张稳定
   `upstream_error`；要风格参考就把工艺写成文字）、`n=1`（n=2 易撞 120s 代理超时）、
   `size 1536x1024`。524 等 120s 重试；下载 403 直接重试。
6. **出图质检**：纸边 9–14%（量亮度 >200 的 bbox）、高频 std ≥6、齿孔行波动 ≥18
   （见「强制输出契约」）；不过 → 按「质量门 → 失败修正」回炉。
7. **本地合成**：`stamp_kit.py` 排版 + 四轴质感（margin 与出图设定一致；紧凑纸边
   开三件套）。
8. **返回输出**：按「输出格式」交付成片 + 参数记录。

## 输入边界与保留

- **图片角色**：输入图 = **画面内容源**。它的构图、笔触、布片就是成品的画面本体。
- **保留等级**：
  - **L0 像素级不动**——景物/布片/线头：`CRITICAL: do not move, redraw or restyle
    the landscape, the cloth patches or the threads. The stamp is only the paper
    underneath. No stitched border, no fabric frame, no added trim inside the
    perforation.` 不加这句，模型会顺手加边框或重画景物。
  - **L1 结构保留**——遮罩作业时齿孔行与画面必须 diff ≈ 0（不透明区逐像素保留）。
  - **L2 可重绘**——空白纸面（strip_type 用同行纸色插值抹旧字，保住纸纹与做旧色）。
- **禁止复制**：输入图自带的文字 / 水印 / 签名**一律裁掉，不要修**；出图阶段
  纸面必须 `COMPLETELY BLANK`（见契约），禁止把任何排版交给模型画。

## 强制输出契约

- **比例 / 尺寸**：出图 `1536x1024`；成片同尺寸。纸边（出图时要求，排版参数跟随）：
  上下 **12–14%**、左右 **9–10%**。
- **必须出现**：
  - **齿孔 = 打孔物理过程**（只写 perforated edge 会得到完美数字模切，一眼假）：
    ```text
    a row of PERFORATION HOLES — the classic punched round scalloped edge. The holes
    are small, round, evenly spaced and punched clean through the paper, each with a
    tiny shadow inside it and a faintly fuzzy raised paper rim, exactly as a
    perforating machine cuts. Leave a few of the perforations slightly irregular or
    partially torn at the corners.
    ```
  - **贴画缘虚线针脚框**（基准版式）；微倾斜 1–2° + 软投影（实测齿边清晰度
    从 12.3 提到 34.0）；三段式排版；面值**必须带单位**（`60¢` / `60分` / `60f`）。
- **禁止出现**：出图阶段的任何文字 / 数字 / 邮政元素（负面：
  `text, letters, numbers, postal markings, postmark, cancellation marks,
  denomination, country name, currency, watermark, logo`）；基准样式下无宽亚麻
  边框带 / 菱形角饰 / 花卉刺绣边。
- **排版 / 文字**：全部由 `stamp_kit.py` 本地完成；墨色单一暖炭褐 `RGB(92,80,68)`；
  文字给确切字符串并加引号。
- **留白 / 边缘 / 材质**：纸边内不许齿孔挤住景物；纸纹要有纤维感
  （高频 std **6–7** 合格，≈3 是塑料感；齿孔行波动 **≥18**，低于 15 齿花不清）。

## 决策清单 / Prompt 结构（四段式）

每次出图按四段拼装（完整模板在 `references/prompts.md`）：

1. **源图保真**——景物不动段（L0 原文照抄）。
2. **邮票方向**——纸 + 齿孔 + 倾斜投影 + 纸边宽度（契约里的原文）。
3. **材质 / 图形 / 字体**——纸纹纤维段、虚线针脚框段（1e）、彩蛋段（显式声明
   极小尺寸）、边缘收拾段（见下）。
4. **禁止项**——`The stamp paper must arrive COMPLETELY BLANK ...` + AVOID 列表。

**边缘要方整，但不能变成裁切边**（改法不是 torn→cut，会丢手工感；是缩幅度 + 减量，
线头要单独点名减量）：

```text
Keep it hand-torn and frayed, but make it TIDIER and MORE CONTAINED — a squarer,
more rectangular overall footprint with only modest irregularity: the fabric edge
should roughly follow a rectangle, with gentle wavering of a centimetre or so
rather than large jutting lobes. Corner areas especially should be more squared
off. Keep the subtle fraying, the loose fibres and a few stray threads, but
reduce their quantity and length considerably.
```

**纸张真实度提升写法**：

```text
a genuine fine wove / laid paper TEXTURE at close range across the entire sheet,
including the blank margins and the areas behind the type — a very fine even mesh
of small fibres and faint laid lines
```
配 `a hairline broken fibre edge — tiny fibrous rough spots and a faint pale sliver
of the paper's thickness where it has been punched`。

### 支线：刺绣边框版式（仅用户点名时）

三句话分工写清（边框是主体 / 画面纯油画零刺绣 / 内缘手缝不规则线），
完整模板 prompts.md 1c。边框粗细四档：

| 档位 | 边框占比 | 刺绣做法 | 适合 |
|---|---|---|---|
| 宽边重绣 | 左右 ~14%、上下 ~13% | 花卉缎面绣 + 卷草纹 | 边框当主体，画面是窗口 |
| **细线自由跑针** | **左右 ~11%、上下 ~11%** | **单股细线 + 2–3mm 短跑针，疏而透、自由游走** | **最像手工布艺原味** |
| 适中边框 | 左右 ~9%、上下 ~11% | 单行跑针 + 散点十字 | 最均衡，稳妥首选 |
| 窄边满绣 | 左右 ~9.5% | 满地针 + 小花卉（无露底） | 画面要更大，边框做浓 |

- **边框饱和度必须低于画面**（实测 0.21–0.24 vs 0.16–0.18 最协调），
  线色从所在布片提亮、分段分色（锚点：底布 RGB(211,198,178) / 天空
  RGB(120,148,182) / 水面 RGB(142,156,171) / 草坡 RGB(147,135,96)）。
- **细线跑针四个必写要素**：`SINGLE STRAND of very fine pale thread` /
  `SMALL, SHORT RUNNING STITCHES (2–3 mm, separated)` / `SCATTERED and AIRY` /
  `WANDERS FREELY`；三个不要：`Do NOT draw a continuous even band, do NOT use
  satin stitch, do NOT use cross-stitch, do NOT fill the linen`。
- **三条硬约束**（缺任一条重出）：①只作用外框，主体内部零刺绣；②主体与针区
  **0 间距**（`the painting grows to fill the whole inner area ... MEETS THE
  STITCHED BORDER DIRECTLY with zero gap`）。**教训：用户说「A 和 B 0 间距」时
  先看截图现状——现状已有间隔 = 目标态请求（去掉间隔），不是抱怨；曾理解反
  多花一整轮**；③密度全程均匀（`Keep the density EVEN across the whole border`）。
- **0 间距实现 = 两轮遮罩收边**：环形遮罩（外矩形越入针区 0.3–0.5% −
  画面内缩 1.2% 重叠）→ 第一轮填画面延伸（`one continuous painting, no seam`），
  常见单边欠填（实测右边欠 2.4%）→ 量实际 bbox 第二轮窄环收边；保护 diff ≈ 0
  验证。本地合成时 `--stitch` 压到 0–0.35。
- **装进邮票结构时的坑**：只写 `do not change` 会丢刺绣、齿孔可能切在亚麻上
  （纸边归零）。必须 outpainting 措辞 + 正面点名保留物 + 显式宽纸边要求
  （prompts.md 1c 第二步）。
- **边框精化（反向遮罩环）**：保留外圈齿孔框（到齿孔行外缘）+ 画面（内缩 1%
  重叠带），重绘纸边 + 亚麻带；单边几何修正用 L 形遮罩。**几何指令用图内锚点
  别给抽象百分比**（「底边距 7%」被执行成 5.5%，「12.5%」又过头；改「底边距 =
  顶边距同宽 + 声明底带窄一档有意」一次到位）。画面/亚麻 bbox **不要自动检测**
  （亮度阈值 / 饱和度 bbox / lum 连续段三代全败），**2% 网格叠图目视读数**是
  唯一可靠手段。模板 prompts.md 1d。

---

## 本地合成与排版（stamp_kit，不要交给模型）

**排版与质感必须本地做**——模型写字字形、拼写、位置都不可控；本地确定性、可复现。

```bash
python scripts/stamp_kit.py --src 成图.png --out 输出.png \
    --stitch .7 --age .25 --perf .95 --cancel 0
```

| 参数 | 0.0 | 1.0 | 效果 |
|---|---|---|---|
| `--stitch` 针法密度 | 稀疏跳针的手缝 | 密实的连续针脚 | 沿**景物轮廓**加针脚，不沿整张纸打圈 |
| `--age` 做旧程度 | 全新发行 | 泛黄陈旧 | 纸色暖黄化 + 边缘压暗 + foxing 褐斑 |
| `--perf` 齿孔完整度 | 残缺撕裂、缺角 | 完整规整 | 低值时用背景色在纸边啃出缺口（只做"破坏"，源图齿孔由出图定） |
| `--cancel` 邮戳 | 不加（新票） | 浓重旧戳 | 角落半透明圆日戳 + 地名日期 + 波浪注销线 |

**五档预设**（`--preset`，中英文均可）：

| 预设 | 针 / 旧 / 齿 / 戳 | 定位 |
|---|---|---|
| `全新发行` Mint | 0.35 / 0.08 / 1.00 / 0.00 | 干净发行感，细齿完整 |
| `标准` Standard | 0.70 / 0.25 / 0.95 / 0.00 | 默认，适度手作感 |
| `信销票` Used | 0.70 / 0.55 / 0.72 / 0.85 | 盖过戳的旧票，故事感最强 |
| `古董藏票` Antique | 0.85 / 0.92 / 0.45 / 0.55 | 泛黄残破，藏家气质 |
| `密绣精工` Dense | 1.00 / 0.15 / 1.00 / 0.00 | 针脚最重要，纸面干净 |

矩阵：`--sheet`（标签 = `中文 / English [st.. ag.. pf.. cx..]`，无 CJK 字体也不 tofu）。

**三段式排版**（真邮票的固定套路，只加一行标题会显得假）：

| 位置 | 内容 | 字体 |
|---|---|---|
| 顶部居中 | 标题（如 `THE BLUE BAY`） | 细衬线大写 + **宽字距**（字号 ×0.34） |
| 底部居中 | 发行行 · 面值 · 年份 | 衬线小字，面值放大 1.75× |
| 左侧竖排 | 系列 · 工艺 + 小刺绣纹样 logo（画幅宽 2.6%） | 小号无衬线 |
| 右侧竖排 | 风格 + 雕刻师署名（手写体 `ENGRAVED BY A. MOREL`） | 小号无衬线 + 手写体 |

- 墨色只用一个（暖炭褐 `RGB(92,80,68)`）；字体指定「年代 + 工艺」不指定字体名
  （`mid-century engraved stamps` + `letterpress-flat and slightly uneven from the
  old press`）。
- **主题配置**在 `stamp_kit.py` 顶部 `Theme` 数据类：`title / series / year /
  value / side_left / side_right / engraver / egg`。已有 `THEME_COASTAL`（英文）
  与 `THEME_COASTAL_CN`（中文面值 60分）两套模板。
- **主题彩蛋**：景物里藏 1–3 个**极小、同工艺**元素（`no bigger than two or three
  stitches across`），不写尺寸会被做成显眼主体。换景色换彩蛋：海岸=帆船·贝壳·
  脚印；山城=小旗·暖光·小猫；林荫=蘑菇·鸟·秋千；田野=稻草人·干草·野兔；
  雪景=雪人·足迹·冰凌；湖河=小舟·芦苇·垂钓（对照表 prompts.md 3b）。

**排版位置 = 显式参数，别自动检测**（亮度阈值→自适应分位→亮+低纹理→高频剖面
四代全败；纸面渐变被缩成窄带、米色亚麻被当纸。可控 > 聪明）：
`--margin-v`（上下）/ `--margin-h`（左右），默认 0.12 / 0.10，**与出图纸边设定一致**。

**紧凑纸边（6–9%）三件套**——默认流程三处不适配，必须**同时**开：

```bash
python scripts/stamp_kit.py --src x.png --out y.png \
    --margin-v 0.10 --margin-h 0.081 \
    --perf-clear 0.042 --perf-frame "0.020,0.030,0.980,0.972" --no-strip
```

| 参数 | 作用 | 不开的后果 |
|---|---|---|
| `--no-strip` | 源图纯净时跳过 strip_type | 12.5% 抹除带越过窄纸边吃进画面顶边（实测 159→196px） |
| `--perf-clear 0.04x` | 文字带中线避让齿孔带，字号按净空高度算 | 标题 / 底行压在齿孔上 |
| `--perf-frame "fx0,fy0,fx1,fy1"` | 残齿啃咬沿齿孔行矩形定位 | 啃在内容区 bbox 边缘而非真齿孔行 |

`--perf-frame` 四值 = 齿孔行中心矩形的画幅比例，2% 网格目视读数
（实测 1536×1024 → `0.020,0.030,0.980,0.972`）。
**竖排双轨道宽度预算**：右两条竖排条各占 `字号 × 1.45` 宽，净空带
（`min(ml,mr) − pl_`）≥ 两条之和，否则叠字（实测 31px 不够、43px 才够）；
不够先加 `--margin-h`，其次降字号。

**脚本自动处理两件事**：①strip_type 抹掉来源图自带文字（同行纸色插值，保纸纹）；
②左右竖排走双轨道（外轨正文 / 内轨 logo·署名，净高内自动降字号居中）。

## 质量门

- [ ] 齿孔是**打孔**的，不是印刷的（孔内有阴影、孔缘有纤维；灰团 = 出图翻车）
- [ ] **纸边留白占 9–14%**（量亮度 >200 bbox）；紧凑 6–9% 必须三件套齐
- [ ] **`--margin-v/--margin-h` 与出图纸边设定一致**，四边文字都落在纸边内
- [ ] 留白边比齿孔宽，齿孔没有挤住景物
- [ ] 景物与来源图一致，没有被重画或加框
- [ ] 基准版式：虚线针脚框贴画缘；无宽亚麻边框带 / 菱形角饰（除非用户点名支线）
- [ ] 边框支线：内缘手缝不规则线、画面内部零刺绣、边框饱和度低于画面、
      细线版短跑针疏而透、0 间距
- [ ] 面值带单位；三段式齐全，无叠字、无拼写错误
- [ ] 左右竖排与署名在两条平行轨道上，互不重叠
- [ ] 残齿啃咬落在齿孔行上，未伤及边框与画面
- [ ] 墨色统一，无阴影字/描边字/渐变字；彩蛋确实极小
- [ ] 纸张有纤维感（高频 std ≥6；齿孔行波动 ≥18）
- **失败修正（每类一次到位的修法）**：
  - 纸边不足 / 单边几何不对 → L 形遮罩 + 图内锚点（别给抽象百分比）
  - 遮罩修补后保护 diff ≠ 0 → **立即弃用重做**（该模式偶发不守遮罩，v8d 实证）
  - 几何读数 → 2% 网格叠图目视（阈值自动检测三代全败，别再试）
  - 竖排叠字 → 加 `--margin-h` 或降字号（先验算净空带 ≥ 两条轨道宽）
  - 出图 524 → 等 120s 重试；403 → 直接重试；**始终 n=1**
  - 模型擅自画字 / 齿孔成灰团 → 强化 COMPLETELY BLANK 段重出

## 输出格式

```markdown
## 成片
- 文件：<out>.png（1536×1024，一图换一票）
- 版式：基准虚线针脚框（或用户指定支线）
- 参数：st0.70 ag0.25 pf0.95 cx0.00（或预设名）

## 质检
- 纸边：T x% B x% L x% R x%（合格 9–14%）
- 高频 std：x.x（≥6）；齿孔行波动：xx（≥18）
- 质量门：全部通过（例外逐条说明）

## 可选
- 五档矩阵：<sheet>.png（仅用户要参数预览时）
```

## 文件

```
stamp-plate/
├── SKILL.md
├── scripts/
│   └── stamp_kit.py          参数化合成器：四轴参数 + 主题排版 + 彩蛋
├── references/
│   └── prompts.md            image2 各阶段提示词模板（1 基础 / 1b 边缘纸纹 /
│                             1c 刺绣边框 / 1c-2 细线跑针遮罩收边 / 1d 边框精化 /
│                             1e ★基准版式 / 3 排版 / 3b 彩蛋）
└── examples/
    ├── final-style-reference.png     ★最终样式基准（虚线针脚框版五档矩阵）
    ├── one-to-one-output.png         一图换一票样例（同时是一次成型翻车实证）
    ├── source-stamp.png              出图阶段的成品（作为合成器输入）
    ├── preset-matrix.png             五档预设对比图
    ├── example-coastal-with-eggs.png 海岸主题 + 三处彩蛋
    ├── example-sewn-border.png       刺绣边框 + 内部纯油画的成图
    ├── sewn-border-variants.png      边框粗细三档对比
    ├── example-fine-stitch.png       细线跑针版成图
    ├── fine-stitch-edge-detail.png   细线版针脚贴画缘（0 间距）放大细节
    ├── border-four-compare.png       边框四档横向对比
    ├── fine-stitch-variants.png      细线版三档对比
    ├── source-fine-stitch.png        细线版带齿孔源票（合成器输入范例）
    ├── preset-matrix-fine.png        细线版五档预设矩阵
    ├── source-fine-frame.png         边框精化版源票（圆角细描边 + 四角纹样）
    ├── example-fine-frame-plate.png  边框精化版收藏级成片（三件套参数）
    ├── preset-matrix-fine-frame.png  边框精化版五档预设矩阵
    └── paper-and-perf-details.png    纸张与齿孔的放大细节
```
