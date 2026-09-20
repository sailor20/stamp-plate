# stamp-plate

> **Turn a landscape photo / fabric-collage artwork into a realistic postage stamp — one image in, one stamp out.**
> 把一张风景图（照片或布艺拼贴作品）做成一枚可以拿在手里的真实感邮票：**一图换一票**。

![stamp-plate demo](demo/param-perf060.jpg)

## 工作原理（一条提示词一次成型）

整枚邮票——纸、齿孔、针脚框、**全部排版文字、邮戳**——由**一条完整提示词**直接生成，
python 不参与主产线。提示词按五段式拼装（模板见 `references/prompts.md` 阶段 2）：

1. **保真** — `KEEP THE ARTWORK pixel for pixel`：景物 / 布片 / 线头一个像素都不动
2. **邮票纸** — 齿孔写成打孔物理过程（`punched clean through, each hole showing the
   grey tabletop through it`）+ 纸边宽度（上下 12% / 左右 9%）+ 微倾斜 + 软投影
3. **材质图形** — laid 纸纤维 + 贴画缘一圈深色虚线跑针框 + 随景色变化的迷你彩蛋
4. **★ 排版规格** — 五区版式逐区给出「字符串加引号 + 位置 + 限长 + 字号比例 + 方向」
5. **禁止项** — `no overlapping or colliding text` 打头

### 五区版式（防叠字的核心）

| 区域 | 内容 | 位置与限长 |
|---|---|---|
| 顶部 | 标题 `THE BLUE BAY` | 顶纸边水平居中，宽字距 |
| 底部 | `POSTA - COASTAL SERIES` + `60¢` + `2026` | 同一行水平居中，面值放大约 1.4× |
| 左 | logo + `LANDSCAPE ISSUE - TEXTILE STUDY` | logo 占左上 1/4；文字限中部 50%，自下而上 |
| 右·上段 | 署名 `ENGRAVED BY A. MOREL` | 仅右上 1/4 区 |
| 右·中段 | `IMPRESSIONIST - POST-IMPRESSIONIST` | 仅中部 50% 区，**与上段间隔 ≥5% 画幅高** |
| 右下 | 圆形邮戳（信销样） | 半透明，只压画面右下角，不碰任何文字 |

### 实测翻车点 → 提示词修法

| 翻车 | 修法 |
|---|---|
| 右侧两段竖排叠字 | 写死 `two separate zones … a clear gap of at least 5 percent of the image height separates them; their zones never touch` |
| 间隔点 `·` 变方框 | 字符串改用连字符：`POSTA - COASTAL SERIES` |
| 模型自造词 / 拼错 | 文字内容给**确切字符串并加引号** |
| 齿孔画成灰团 | 重申 `punched clean through` + 孔透出桌面 |
| 景物被顺手重画 | 保真段放最前 + `copy the artwork pixel for pixel` |

## 可选：本地精排（python，默认不走）

提示词路线反复失败、或需要像素级排版精度时：先按 `references/prompts.md` 阶段 1e
出**无字**源票（纸面 COMPLETELY BLANK），再用 `scripts/stamp_kit.py` 本地排版：

```bash
python scripts/stamp_kit.py --src your-stamp.png --out final.png \
    --margin-v 0.12 --margin-h 0.10

# 五档矩阵预览
python scripts/stamp_kit.py --src your-stamp.png --out matrix.png --sheet
```

四轴质感（本地精排的可调参数）：

| 参数 | 0.0 | 1.0 |
|---|---|---|
| `--stitch` 针法密度 | 稀疏跳针 | 密实连续针脚（沿景物轮廓） |
| `--age` 做旧 | 全新发行 | 泛黄 + 边缘压暗 + foxing 褐斑 |
| `--perf` 齿孔完整度 | 残缺撕裂 | 完整规整（低值沿齿孔行啃出缺口） |
| `--cancel` 邮戳 | 不加 | 角落半透明圆日戳 + 注销线 |

五档预设：`全新发行 Mint` / `标准 Standard` / `信销票 Used` / `古董藏票 Antique` /
`密绣精工 Dense`。

## 仓库结构

```
stamp-plate/
├── SKILL.md               # 完整技能定义：路由 / 工作流 / 五区版式规格 / 质量门 / 翻车点修正表
├── references/prompts.md  # 提示词模板库（★阶段2 一次成型主模板 / 基础 / 边框支线 / 无字源票 / 彩蛋）
├── scripts/stamp_kit.py   # 可选本地精排（Pillow + numpy）
└── demo/                  # 示范图
```

> 完整 examples（各版式成图、矩阵对比、细节放大）随 WorkBuddy 技能包分发，不在此仓库。

## 亮点经验（详见 SKILL.md）

- **齿孔必须写成物理过程**（punched clean through + 孔内阴影 + 纤维毛边），
  否则一眼数字模切
- **文字排版在提示词里完成**：五区版式 + 引号字符串 + 连字符隔点，可做到零叠字零错字
- 保真段必须放最前并写 `pixel for pixel`——排版段在后，模型会趁排版顺手重画画面
- 微倾斜 + 软投影让齿边清晰度从 12.3 → 34.0
- 本地精排的位置用显式参数（`--margin-v/--margin-h`），**不要自动检测**——
  四代检测算法全败于米色亚麻与齿孔干扰

## 环境

主产线只需任意图生图模型（WorkBuddy 中为 image2 MCP：输入单张参考图、
1536×1024、n=1）。可选本地精排：Windows + Python 3.10+，依赖 Pillow、numpy；
邮票字体取自 Windows 系统字体链。

---

*This is a [WorkBuddy](https://www.workbuddy.cn) Skill — designed to be installed and driven by an LLM agent.*
