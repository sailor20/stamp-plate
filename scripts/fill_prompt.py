"""fill_prompt.py — 从 themes/*.json + stage2_template.txt 生成一次成型提示词

模板（references/stage2_template.txt）里的引号串全部是占位符；换景色只改
themes/*.json 或换 --theme 键，**不要手改模板正文**。字符串分两类：
  A 固定串  side_left / engraver / postmark_name / postmark_date / year
            —— 模板自带、视为已授权，不许模型改动
  B 专名位  title / series / value / side_right / eggs
            —— 随景色或用户重写，填充后即为唯一合法字符串
用法:
  python fill_prompt.py --theme coastal
  python fill_prompt.py --theme snow --out prompt.txt
  python fill_prompt.py --theme lake --photo            # 照片输入分支
  python fill_prompt.py --theme coastal --no-postmark   # 新票（去掉邮戳段）
  python fill_prompt.py --theme coastal --strict        # 末尾追加防叠字 STRICT 段
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TPL_PATH = os.path.join(ROOT, "references", "stage2_template.txt")
THEMES_DIR = os.path.join(ROOT, "themes")

FIDELITY_FABRIC = (
    "1. KEEP THE ARTWORK — CRITICAL: do not move, redraw or restyle the landscape,\n"
    "   the cloth patches or the threads. Copy the artwork pixel for pixel into the\n"
    "   centre of the stamp. The stamp is only the paper and lettering around it."
)
FIDELITY_PHOTO = (
    "1. KEEP THE PHOTOGRAPH — CRITICAL: do not move, redraw, restyle or re-light\n"
    "   the photograph. It is a PRINTED PHOTOGRAPH mounted at the centre of the\n"
    "   stamp: do NOT turn it into a fabric collage and do NOT add cloth patches,\n"
    "   embroidery, stitches or threads inside it. Copy the image pixel for pixel.\n"
    "   The stamp is only the paper and lettering around it."
)

STRICT = (
    'STRICT: the right margin carries TWO separate lines — "{engraver}" ends within\n'
    'the top quarter; "{side_right}" occupies only the middle half. Shrink both to\n'
    "cap-height 1.6 percent of the image height. Visible blank paper must remain\n"
    "between them and between every other pair of lines."
)


def load_theme(key):
    p = key if key.endswith(".json") else os.path.join(THEMES_DIR, key + ".json")
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    d["_path"] = p
    return d


def egg_block(d, mode):
    eggs = list(d.get("eggs", [])) + ["", "", ""]
    e1, e2, e3 = eggs[0], eggs[1], eggs[2]
    if mode == "fabric":
        return (
            "5. HIDDEN DETAILS: add ONLY three tiny hidden details worked in the same\n"
            "   fabric-and-thread technique as the artwork, each no bigger than two or\n"
            f"   three stitches across: {e1}; {e2}; {e3}.\n"
            "   Genuinely tiny, discoverable only on close inspection."
        )
    if mode == "photo_margin":
        return (
            "5. HIDDEN DETAILS: three tiny stitched motifs worked ON THE BLANK PAPER\n"
            "   margin at the lower corners — never on the photograph itself: "
            f"{e1}; {e2};\n   {e3}. Each no bigger than two or three stitches across."
        )
    return (
        "5. NO HIDDEN DETAILS: keep the photograph itself completely clean — no\n"
        "   added motifs, stitches or objects on the image area."
    )


def postmark_block(d, on=True):
    if not on:
        return ""
    return (
        "6. POSTMARK: a round semi-transparent cancellation postmark at the lower\n"
        "   right, overlapping ONLY the artwork's lower-right corner and the paper\n"
        "   just below it — it must NOT touch any lettering. A fine circle, the name\n"
        f"   \"{d['postmark_name']}\" in small capitals, three wavy cancellation\n"
        f"   lines, and the date \"{d['postmark_date']}\"."
    )


def build(d, mode="fabric", postmark=True, strict=False):
    """mode: fabric | photo | photo_eggs"""
    with open(TPL_PATH, encoding="utf-8") as f:
        out = f.read()

    egg_mode = "fabric" if mode == "fabric" else (
        "photo_margin" if mode == "photo_eggs" else "photo_clean")

    reps = {
        "{{FIDELITY_BLOCK}}": FIDELITY_FABRIC if mode == "fabric" else FIDELITY_PHOTO,
        "{{ARTWORK_NOUN}}": "painting" if mode == "fabric" else "photograph",
        "{{EGG_BLOCK}}": egg_block(d, egg_mode),
        "{{POSTMARK_BLOCK}}": postmark_block(d, postmark),
        "{{TITLE}}": d["title"],
        "{{SERIES}}": d["series"],
        "{{VALUE}}": d["value"],
        "{{YEAR}}": d["year"],
        "{{SIDE_LEFT}}": d["side_left"],
        "{{ENGRAVER}}": d["engraver"],
        "{{SIDE_RIGHT}}": d["side_right"],
        "{{POSTMARK_NAME}}": d["postmark_name"],
        "{{POSTMARK_DATE}}": d["postmark_date"],
    }
    for k, v in reps.items():
        out = out.replace(k, v)

    if strict:
        out += "\n\n" + STRICT.format(
            engraver=d["engraver"], side_right=d["side_right"])
    # 清掉多余空行
    while "\n\n\n" in out:
        out = out.replace("\n\n\n", "\n\n")
    return out.rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser(description="生成一次成型整票提示词")
    ap.add_argument("--theme", default="coastal",
                    help="themes/ 下的键（如 coastal/snow/lake）或直接给 JSON 路径")
    ap.add_argument("--photo", action="store_true",
                    help="输入是照片（非布艺作品）：换保真段措辞、去掉画内彩蛋，"
                         "防止模型把照片布艺化")
    ap.add_argument("--photo-eggs", action="store_true",
                    help="照片输入但保留彩蛋（彩蛋改到纸边角落，不碰照片本身）")
    ap.add_argument("--no-postmark", action="store_true",
                    help="新票：去掉第 6 段邮戳")
    ap.add_argument("--strict", action="store_true",
                    help="末尾追加防叠字 STRICT 段（上一次右侧两段竖排叠字时用）")
    ap.add_argument("--out", default=None, help="写入文件（默认打印到 stdout）")
    a = ap.parse_args()

    d = load_theme(a.theme)
    mode = "fabric"
    if a.photo:
        mode = "photo_eggs" if a.photo_eggs else "photo"
    prompt = build(d, mode=mode, postmark=not a.no_postmark, strict=a.strict)

    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(prompt)
        print("saved:", a.out, "| theme:", d.get("key"), "| mode:", mode)
    else:
        sys.stdout.write(prompt)


if __name__ == "__main__":
    main()
