# stamp-plate

> **Turn a landscape photo / fabric-collage artwork into a realistic postage stamp — one image in, one stamp out.**
> 把一张风景图（照片或布艺拼贴作品）做成一枚可以拿在手里的真实感邮票：**一图换一票**。

![stamp-plate demo](demo/param-perf060.jpg)

## 工作原理（两段式）

让图生图模型写字不可控（实测必然：竖排叠字、间隔点变方框、齿孔画成灰团），
所以**文字与排版全部本地做**：

1. **出图**（image2 / 任意图生图模型）：把基底换成暖象牙打孔邮票纸——齿孔写成
   打孔物理过程、画面贴一圈虚线针脚框、微倾斜 + 软投影；**纸面完全空白**
   （`COMPLETELY BLANK` 负面锁死，尺寸 1536×1024）。
2. **本地合成**（`scripts/stamp_kit.py`）：三段式传统邮票排版（标题 / 发行行·面值·
   年份 / 左右竖排 + 雕刻师署名 + 刺绣 logo）+ 四轴质感 + 做旧 / 残齿 / 邮戳。

## 四轴质感

| 参数 | 0.0 | 1.0 |
|---|---|---|
| `--stitch` 针法密度 | 稀疏跳针 | 密实连续针脚（沿景物轮廓） |
| `--age` 做旧 | 全新发行 | 泛黄 + 边缘压暗 + foxing 褐斑 |
| `--perf` 齿孔完整度 | 残缺撕裂 | 完整规整（低值沿齿孔行啃出缺口） |
| `--cancel` 邮戳 | 不加 | 角落半透明圆日戳 + 注销线 |

五档预设：`全新发行 Mint` / `标准 Standard` / `信销票 Used` / `古董藏票 Antique` /
`密绣精工 Dense`；一键五档矩阵对比 `--sheet`。

## 快速开始

```bash
# 1) 出图：按 references/prompts.md 的四段式模板（阶段 1e 基准版式）
#    任意图生图模型均可，1536x1024，纸面不带任何文字

# 2) 本地合成
python scripts/stamp_kit.py --src your-stamp.png --out final.png \
    --margin-v 0.12 --margin-h 0.10

# 五档矩阵预览
python scripts/stamp_kit.py --src your-stamp.png --out matrix.png --sheet

# 紧凑纸边（6–9%）三件套
python scripts/stamp_kit.py --src x.png --out y.png \
    --margin-v 0.10 --margin-h 0.081 \
    --perf-clear 0.042 --perf-frame "0.020,0.030,0.980,0.972" --no-strip
```

## 仓库结构

```
stamp-plate/
├── SKILL.md               # 完整技能定义：路由 / 工作流 / 输出契约 / 质量门 / 踩坑实录
├── references/prompts.md  # 出图提示词模板库（基础版式 / ★基准版式 / 边框支线 / 彩蛋）
├── scripts/stamp_kit.py   # 参数化合成器（Pillow + numpy）
└── demo/                  # 示范图
```

> 完整 examples（各版式成图、矩阵对比、细节放大）随 WorkBuddy 技能包分发，不在此仓库。

## 亮点经验（详见 SKILL.md）

- **齿孔必须写成物理过程**（punched clean through + 孔内阴影 + 纤维毛边），
  否则一眼数字模切
- **出图阶段纸面 COMPLETELY BLANK**：模型一次成型的字必然翻车
- 排版位置用显式参数（`--margin-v/--margin-h`），**不要自动检测**——四代检测
  算法全败于米色亚麻与齿孔干扰
- 微倾斜 + 软投影让齿边清晰度从 12.3 → 34.0
- 残齿啃咬必须定位到齿孔行（`--perf-frame`），否则啃错位置

## 环境

Windows + Python 3.10+，依赖 Pillow、numpy；邮票字体取自 Windows 系统字体链。

---

*This is a [WorkBuddy](https://www.workbuddy.cn) Skill — designed to be installed and driven by an LLM agent.*
