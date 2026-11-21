r"""Build the report figures from results/*.csv, in Chinese and English.

    PYTHONPATH=. python experiment/plot_results.py          # both languages
    PYTHONPATH=. python experiment/plot_results.py --lang zh

Outputs (results/figures/):
    fig1_accuracy_vs_budget_{zh,en}.png   experiment 1
    fig2_cross_arch_{zh,en}.png           experiment 2
    fig3_ablation_{zh,en}.png             experiment 3
    fig4_budget_accounting_{zh,en}.png    the "what does 1% mean" slide
"""

from __future__ import annotations

import argparse
import csv
import os
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(REPO / ".cache" / "matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

CJK_CANDIDATES = ["PingFang SC", "Hiragino Sans GB", "Heiti SC", "Songti SC",
                  "Arial Unicode MS", "Noto Sans CJK SC", "Microsoft YaHei", "SimHei"]

C_RANDOM = "#8a8a8a"
C_HERDING = "#e08a1e"
C_BONSAI = "#1f6fb4"
C_BONSAI_L = "#7fb2dd"
C_NOPPR = "#c94f4f"
C_RAND = "#7a5fa8"
C_FULL = "#333333"
FULL_NODES = {"cora": 2708, "citeseer": 3327}  # Planetoid, fixed

TEXTS = {
    "zh": {
        "fig1": "图 1  准确率 vs 存储预算（GCN）",
        "fig1_x": "存储预算 $S_r$（相对原图的字节比，%）",
        "fig1_y": "测试准确率（%）",
        "random": "随机选点",
        "herding": "Herding",
        "bonsai": "Bonsai",
        "full": "全图（Full）",
        "sat_cora": "1% 与 3% 的凝缩图相同",
        "sat_citeseer": "三档预算的凝缩图相同",
        "fig2": "图 2  同一份凝缩图 × 三种架构",
        "fig2_x": "存储预算 $S_r$（%）",
        "fig2_y": "测试准确率（%）",
        "fig3": "图 3  消融实验（Cora，5 seeds）",
        "fig3a": "(a) 准确率",
        "fig3b": "(b) 凝缩图逻辑大小",
        "fig3_y": "测试准确率（%）",
        "fig3_x": "存储预算 $S_r$（%）",
        "fig3_kb": "逻辑大小（KB）",
        "v_bonsai": "Bonsai",
        "v_rand": "随机 Exemplar",
        "v_noppr": "去 PPR",
        "v_both": "随机 + 去 PPR",
        "fig3_note": "1% 上三个变体与 Bonsai 的图完全相同（预算已饱和），故不画。",
        "fig4": "图 4  “1%” 的两种口径",
        "fig4_a": "Cora",
        "fig4_b": "Citeseer",
        "i_full": "原图\n（逻辑，int 记账）",
        "i_logic": "Bonsai 凝缩图\n（逻辑，论文口径）",
        "i_file": "Bonsai 凝缩图\n（实际文件，PyG 落盘）",
        "fig4_y": "存储大小（KB，对数轴）",
        "fig4_note": "保留节点 {kept}/{total} = {pct:.1f}%   逻辑 {kb:.1f} KB  vs  实际 {fmb:.2f} MB",
        "seeds": "5 seeds，误差棒为 ±1 std",
    },
    "en": {
        "fig1": "Fig. 1  Accuracy vs storage budget (GCN)",
        "fig1_x": "Storage budget $S_r$ (bytes relative to the full graph, %)",
        "fig1_y": "Test accuracy (%)",
        "random": "Random",
        "herding": "Herding",
        "bonsai": "Bonsai",
        "full": "Full graph",
        "sat_cora": "1% and 3% give the same graph",
        "sat_citeseer": "all three budgets give the same graph",
        "fig2": "Fig. 2  One condensed graph, three architectures",
        "fig2_x": "Storage budget $S_r$ (%)",
        "fig2_y": "Test accuracy (%)",
        "fig3": "Fig. 3  Ablation study (Cora, 5 seeds)",
        "fig3a": "(a) accuracy",
        "fig3b": "(b) condensed-graph logical size",
        "fig3_y": "Test accuracy (%)",
        "fig3_x": "Storage budget $S_r$ (%)",
        "fig3_kb": "logical size (KB)",
        "v_bonsai": "Bonsai",
        "v_rand": "random exemplars",
        "v_noppr": "no PPR",
        "v_both": "random + no PPR",
        "fig3_note": "At 1% all variants equal Bonsai byte-for-byte (budget saturated), hence omitted.",
        "fig4": 'Fig. 4  Two readings of "1%"',
        "fig4_a": "Cora",
        "fig4_b": "Citeseer",
        "i_full": "full graph\n(logical, int accounting)",
        "i_logic": "Bonsai graph\n(logical, paper's rule)",
        "i_file": "Bonsai graph\n(actual file on disk)",
        "fig4_y": "storage size (KB, log scale)",
        "fig4_note": "nodes kept {kept}/{total} = {pct:.1f}%   logical {kb:.1f} KB  vs  file {fmb:.2f} MB",
        "seeds": "5 seeds, error bars = ±1 std",
    },
}


# --------------------------------------------------------------------------- #
# data
# --------------------------------------------------------------------------- #
def read_csv(path: Path) -> list[dict]:
    if not path.exists() or path.stat().st_size == 0:
        print(f"  (missing) {path}")
        return []
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def budget_value(raw: str):
    if raw in ("", "full", "None", "none"):
        return None
    return float(raw)


def agg(rows: list[dict], dataset: str, budget: float | None,
        method: str, backbone: str = "GCN") -> tuple[float, float, int, dict]:
    accs = []
    extra = {}
    for r in rows:
        if r["dataset"] != dataset or r["method"] != method or r["backbone"] != backbone:
            continue
        if budget_value(r["budget"]) != budget:
            continue
        accs.append(float(r["test_acc"]))
        extra = r
    if not accs:
        return (float("nan"), 0.0, 0, {})
    mean = sum(accs) / len(accs)
    var = sum((a - mean) ** 2 for a in accs) / (len(accs) - 1) if len(accs) > 1 else 0.0
    return (mean, var ** 0.5, len(accs), extra)


def setup_style(lang: str) -> None:
    if lang == "zh":
        available = {f.name for f in font_manager.fontManager.ttflist}
        font = next((c for c in CJK_CANDIDATES if c in available), None)
        if font is None:
            raise SystemExit(
                "no CJK font found; install one (e.g. `pip install matplotlib` + "
                "a CJK font) or run with --lang en"
            )
        plt.rcParams["font.sans-serif"] = [font, "DejaVu Sans"]
        print(f"  font: {font}")
    else:
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
    plt.rcParams.update({
        "axes.unicode_minus": False,
        "figure.dpi": 120,
        "savefig.dpi": 200,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "font.size": 10,
        "axes.titlesize": 12,
        "legend.frameon": False,
    })


# --------------------------------------------------------------------------- #
# figures
# --------------------------------------------------------------------------- #
def fig1(exp1, budgets, out: Path, t: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
    series = [("random", t["random"], C_RANDOM, "o"),
              ("herding", t["herding"], C_HERDING, "s"),
              ("bonsai", t["bonsai"], C_BONSAI, "D")]
    for ax, ds in zip(axes, ["cora", "citeseer"]):
        full_mean, full_std, _, _ = agg(exp1, ds, None, "full")
        if full_mean == full_mean:
            ax.axhline(full_mean, color=C_FULL, ls="--", lw=1.2, label=t["full"])
            ax.axhspan(full_mean - full_std, full_mean + full_std, color=C_FULL, alpha=0.08)
        for method, label, color, marker in series:
            xs, ys, es = [], [], []
            for b in budgets:
                m, s, n, _ = agg(exp1, ds, b, method)
                if n:
                    xs.append(b * 100)
                    ys.append(m)
                    es.append(s)
            ax.errorbar(xs, ys, yerr=es, marker=marker, color=color, lw=1.8,
                        capsize=3, label=label)
        ax.set_title(ds.capitalize())
        ax.set_xlabel(t["fig1_x"])
        ax.set_xticks([b * 100 for b in budgets])
        ax.set_xticklabels([f"{b * 100:g}" for b in budgets])
    axes[0].set_ylabel(t["fig1_y"])
    axes[0].annotate(t["sat_cora"], xy=(2.6, 84.4), xytext=(1.1, 77.0),
                     fontsize=8.5, color="#444444",
                     arrowprops=dict(arrowstyle="->", color="#777777", lw=0.8))
    axes[1].annotate(t["sat_citeseer"], xy=(2.0, 74.3), xytext=(0.9, 66.0),
                     fontsize=8.5, color="#444444",
                     arrowprops=dict(arrowstyle="->", color="#777777", lw=0.8))
    axes[0].legend(loc="lower right", fontsize=9)
    fig.suptitle(t["fig1"], y=1.02)
    fig.text(0.99, -0.02, t["seeds"], ha="right", fontsize=8, color="#666666")
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)


def fig2(exp2, exp1, full_ref, budgets, out: Path, t: dict) -> None:
    arches = [("GCN", C_BONSAI), ("GAT", C_RAND), ("GIN", C_HERDING)]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
    width = 0.26
    for ax, ds in zip(axes, ["cora", "citeseer"]):
        for i, (arch, color) in enumerate(arches):
            xs, ys, es = [], [], []
            for j, b in enumerate(budgets):
                m, s, n, _ = agg(exp2, ds, b, "bonsai", arch)
                if n:
                    xs.append(j + (i - 1) * width)
                    ys.append(m)
                    es.append(s)
            ax.bar(xs, ys, width, yerr=es, capsize=3, color=color, label=arch,
                   edgecolor="white", linewidth=0.6)
            # full-graph reference for this architecture
            if arch == "GCN":
                fm, fs, n, _ = agg(exp1, ds, None, "full", "GCN")
            else:
                fm, fs, n, _ = agg(full_ref, ds, None, "full", arch)
            if fm == fm:
                ax.axhline(fm, color=color, ls=":", lw=1.0, alpha=0.9)
        ax.set_xticks(range(len(budgets)))
        ax.set_xticklabels([f"{b * 100:g}" for b in budgets])
        ax.set_xlabel(t["fig2_x"])
        ax.set_title(ds.capitalize())
        ax.set_ylim(50, 92)
    axes[0].set_ylabel(t["fig2_y"])
    axes[0].legend(ncol=3, loc="lower right", fontsize=9)
    fig.suptitle(t["fig2"], y=1.02)
    fig.text(0.99, -0.02, "bars = Bonsai; dotted = full graph", ha="right",
             fontsize=8, color="#666666")
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)


def fig3(exp3, budgets, out: Path, t: dict) -> None:
    variants = [("bonsai", t["v_bonsai"], C_BONSAI),
                ("bonsai_random_exemplar", t["v_rand"], C_BONSAI_L),
                ("bonsai_no_ppr", t["v_noppr"], C_NOPPR),
                ("bonsai_random_no_ppr", t["v_both"], C_RAND)]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))
    width = 0.2
    for i, (method, label, color) in enumerate(variants):
        xs, ys, es, kbs = [], [], [], []
        for j, b in enumerate(budgets):
            m, s, n, extra = agg(exp3, "cora", b, method)
            if n:
                xs.append(j + (i - 1.5) * width)
                ys.append(m)
                es.append(s)
                kbs.append(float(extra.get("logical_KB", "nan")))
        ax1.bar(xs, ys, width, yerr=es, capsize=3, color=color, label=label,
                edgecolor="white", linewidth=0.6)
        ax2.bar([x for x in xs], kbs, width, color=color, edgecolor="white",
                linewidth=0.6)
        for x, kb in zip(xs, kbs):
            ax2.text(x, kb + 0.6, f"{kb:.1f}", ha="center", fontsize=7, color="#333333")
    for ax in (ax1, ax2):
        ax.set_xticks(range(len(budgets)))
        ax.set_xticklabels([f"{b * 100:g}" for b in budgets])
        ax.set_xlabel(t["fig3_x"])
    ax1.set_ylabel(t["fig3_y"])
    ax1.set_ylim(70, 84.5)
    ax1.set_title(t["fig3a"])
    ax1.legend(loc="lower right", fontsize=8.5)
    ax2.set_ylabel(t["fig3_kb"])
    ax2.set_title(t["fig3b"])
    fig.suptitle(t["fig3"], y=1.02)
    fig.text(0.99, -0.03, t["fig3_note"], ha="right", fontsize=8, color="#666666")
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)


def fig4(budget_rows, out: Path, t: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for ax, ds in zip(axes, ["cora", "citeseer"]):
        row = next((r for r in budget_rows
                    if r["dataset"] == ds and abs(float(r["budget"]) - 0.01) < 1e-9), None)
        if row is None:
            continue
        full_kb = float(row["full_bytes"]) / 1024
        logic_kb = float(row["bonsai_logical_KB"])
        file_kb = float(row["bonsai_file_bytes"]) / 1024
        kept = int(row["bonsai_nodes"])
        total = FULL_NODES[ds]
        labels = [t["i_full"], t["i_logic"], t["i_file"]]
        values = [full_kb, logic_kb, file_kb]
        colors = ["#555555", C_BONSAI, C_HERDING]
        bars = ax.bar(range(3), values, color=colors, width=0.6,
                      edgecolor="white", linewidth=0.6)
        ax.set_yscale("log")
        ax.set_ylim(min(values) / 3, max(values) * 4)
        for b, v in zip(bars, values):
            ax.text(b.get_x() + b.get_width() / 2, v * 1.15,
                    f"{v:,.1f} KB" if v < 1024 else f"{v / 1024:,.2f} MB",
                    ha="center", fontsize=9)
        ax.set_xticks(range(3))
        ax.set_xticklabels(labels, fontsize=8.5)
        ax.set_title(ds.capitalize())
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
        ax.set_xlabel(t["fig4_note"].format(
            kept=kept, total=total, pct=100 * kept / total,
            kb=logic_kb, fmb=file_kb / 1024), fontsize=8.5, labelpad=8)
    axes[0].set_ylabel(t["fig4_y"])
    fig.suptitle(t["fig4"], y=1.02)
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", choices=["zh", "en", "both"], default="both")
    ap.add_argument("--out-dir", default="results/figures")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    exp1 = read_csv(REPO / "results/experiment1.csv")
    exp2 = read_csv(REPO / "results/experiment2.csv")
    exp3 = read_csv(REPO / "results/experiment3.csv")
    full_ref = read_csv(REPO / "results/full_reference.csv")
    budget_rows = read_csv(REPO / "results/budget_table.csv")
    budgets = [0.005, 0.01, 0.03]

    langs = ["zh", "en"] if args.lang == "both" else [args.lang]
    for lang in langs:
        print(f"[{lang}]")
        setup_style(lang)
        t = TEXTS[lang]
        suffix = f"_{lang}.png"
        fig1(exp1, budgets, out_dir / f"fig1_accuracy_vs_budget{suffix}", t)
        fig2(exp2, exp1, full_ref, budgets, out_dir / f"fig2_cross_arch{suffix}", t)
        fig3(exp3, [0.001, 0.002, 0.005], out_dir / f"fig3_ablation{suffix}", t)
        fig4(budget_rows, out_dir / f"fig4_budget_accounting{suffix}", t)
        print(f"  wrote 4 figures to {out_dir}")

    for p in sorted(out_dir.glob("*.png")):
        print(f"  {p}  ({p.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()