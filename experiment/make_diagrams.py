r"""Draw the two diagrams the report template asks for.

  docs/figures/fig2_1_pipeline.png  pipeline of the paper's method (redrawn)
  docs/figures/fig3_1_route.png     our reproduction workflow

Both are drawn by us (not copied from the paper), which is why the captions say
"本组据论文 §3 重绘".

Run:  PYTHONPATH=. python experiment/make_diagrams.py
"""

from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(REPO / ".cache" / "matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

OUT = REPO / "docs" / "figures"
INK = "#252525"
RED = "#A20000"
TEAL = "#287D79"
GREY = "#6f6f6f"
FILL = "#f4f2ec"
FILL_KEY = "#fdf1ee"
FILL_OUT = "#eef4f3"


def pick_font() -> str:
    names = {f.name for f in font_manager.fontManager.ttflist}
    for cand in ("PingFang SC", "Hiragino Sans GB", "Heiti SC", "Arial Unicode MS"):
        if cand in names:
            return cand
    return "DejaVu Sans"


def box(ax, x, y, w, h, title, sub="", fill=FILL, edge=INK, title_size=11):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02",
                                linewidth=1.0, edgecolor=edge, facecolor=fill))
    ax.text(x + w / 2, y + h * 0.62, title, ha="center", va="center",
            fontsize=title_size, color=edge, weight="bold")
    if sub:
        ax.text(x + w / 2, y + h * 0.28, sub, ha="center", va="center",
                fontsize=8.2, color=GREY)


def arrow(ax, x1, y1, x2, y2, color=INK):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=12, linewidth=1.0, color=color))


def pipeline(font: str) -> None:
    plt.rcParams["font.sans-serif"] = [font, "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(12.4, 3.5))
    ax.set_xlim(0, 12.4)
    ax.set_ylim(0, 3.5)
    ax.axis("off")

    stages = [
        ("输入", "图 G、字节预算 b", FILL_OUT, TEAL, "训练图 + 预算"),
        ("① 计算树 → WL 表示", "一步邻居聚合得到 a_v\n距离 d = ||a_v − a_u||₂", FILL, INK, "§2.1–3.1"),
        ("② Rev-k-NN + 覆盖贪心", "φ(T_v)=|Rev-k-NN(T_v)|/|T|\n贪心最大化 φ(A)，1−1/e", FILL_KEY, RED, "§3.1–3.2"),
        ("③ 建图与剪枝", "诱导子图（根+1-hop+ego 边）\nPPR 删点、类别对齐", FILL, INK, "§3.3"),
        ("输出", "凝缩图 G_s（≤ b）", FILL_OUT, TEAL, "用于训练下游 GNN"),
    ]
    w, h, gap = 2.18, 1.5, 0.38
    x = 0.22
    centers = []
    for title, sub, fill, edge, section in stages:
        box(ax, x, 1.12, w, h, title, sub, fill=fill, edge=edge, title_size=9.6)
        ax.text(x + w / 2, 2.78, section, ha="center", va="center", fontsize=8, color=GREY)
        centers.append((x, x + w))
        x += w + gap
    for i in range(len(stages) - 1):
        arrow(ax, centers[i][1] + 0.03, 1.87, centers[i + 1][0] - 0.03, 1.87)
    ax.text(6.2, 0.62, "全过程不使用下游模型的梯度；选点依据是“计算树被多少其他树当作近邻”，而非梯度匹配。",
            ha="center", va="center", fontsize=9, color=GREY)
    fig.tight_layout()
    fig.savefig(OUT / "fig2_1_pipeline.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def route(font: str) -> None:
    plt.rcParams["font.sans-serif"] = [font, "DejaVu Sans"]
    fig, ax = plt.subplots(figsize=(9.6, 7.4))
    ax.set_xlim(0, 9.6)
    ax.set_ylim(0, 7.4)
    ax.axis("off")

    steps = [
        ("① 环境与数据准备", "macOS/CPU · Python 3.13 · PyG 2.8\nCora / Citeseer（Planetoid 原始文件）", TEAL, FILL_OUT),
        ("② 预算校准", "S_r → 字节 t → 基线节点数 n\nCora 1% = 13 个节点", INK, FILL),
        ("③ 凝缩（6 张图 + 消融变体 + k 扫描）", "官方 main.py · 固定随机种子 · 单次约 0.7–1.0 s", RED, FILL_KEY),
        ("④ 训练与评估（350 次）", "实验一 100 · 实验二 90 · 实验三 80 · k 扫描 60 · 全图 20", INK, FILL),
        ("⑤ 汇总与作图", "results/*.csv → summary_*.csv → 4 张图", TEAL, FILL_OUT),
    ]
    y = 6.15
    for title, sub, edge, fill in steps:
        box(ax, 0.55, y, 8.5, 1.02, title, sub, fill=fill, edge=edge, title_size=11)
        if y > 0.9:
            arrow(ax, 4.8, y - 0.06, 4.8, y - 0.34)
        y -= 1.38

    ax.add_patch(FancyBboxPatch((0.55, 0.28), 8.5, 0.78, boxstyle="round,pad=0.012,rounding_size=0.02",
                                linewidth=1.0, edgecolor=GREY, facecolor="white", linestyle="--"))
    ax.text(4.8, 0.78, "工程改造 4 项：torch_sparse 可选化 · weights_only · 决策树固定种子 · 数据镜像下载",
            ha="center", va="center", fontsize=9, color=GREY)
    ax.text(4.8, 0.46, "（改造前后的数值等价性在第 4.7 节逐项说明）",
            ha="center", va="center", fontsize=8, color=GREY)
    fig.tight_layout()
    fig.savefig(OUT / "fig3_1_route.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    font = pick_font()
    print("font:", font)
    pipeline(font)
    route(font)
    for p in sorted(OUT.glob("*.png")):
        print(f"  {p}  ({p.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()