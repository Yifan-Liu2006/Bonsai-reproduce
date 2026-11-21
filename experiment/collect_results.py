r"""Aggregate the per-run CSVs written by train_baseline.py / train_condensed.py.

For every (dataset, budget, method, backbone) group it reports mean ± std of the
test accuracy over seeds, and writes one summary CSV next to the input.

Usage (from Bonsai/):

    PYTHONPATH=. python experiment/collect_results.py \
        --inputs results/experiment1.csv results/experiment2.csv
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

METHOD_ORDER = ["full", "random", "herding", "bonsai",
                "bonsai_rand_exemplar", "bonsai_no_ppr"]
BACKBONE_ORDER = ["GCN", "GAT", "GIN"]


def budget_key(value: str):
    if value in ("", "full", "None", "none"):
        return (0, 0.0)
    try:
        return (1, float(value))
    except ValueError:
        return (2, 0.0)


def fmt_budget(value: str) -> str:
    if value in ("", "full", "None", "none"):
        return "full"
    try:
        return f"{float(value) * 100:g}%"
    except ValueError:
        return value


def load(path: Path) -> list[dict]:
    with path.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        r["test_acc"] = float(r["test_acc"])
        for k in ("n_nodes", "n_edges", "n_features", "logical_KB"):
            try:
                r[k] = float(r[k])
            except (KeyError, ValueError, TypeError):
                r[k] = float("nan")
    return rows


def summarise(rows: list[dict], path: Path) -> None:
    # drop exact duplicates (same dataset/budget/method/backbone/seed) but keep
    # the first occurrence, so a re-run does not silently inflate the sample size
    seen_keys = set()
    unique, dropped = [], 0
    for r in rows:
        key = (r["dataset"], r["budget"], r["method"], r["backbone"], r["seed"])
        if key in seen_keys:
            dropped += 1
            continue
        seen_keys.add(key)
        unique.append(r)
    if dropped:
        print(f"!! dropped {dropped} duplicate runs from {path.name} "
              f"(same dataset/budget/method/backbone/seed)")
    rows = unique

    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        groups[(r["dataset"], r["budget"], r["method"], r["backbone"])].append(r)

    summary = []
    for (ds, budget, method, backbone), items in groups.items():
        accs = np.array([it["test_acc"] for it in items])
        first = items[0]
        summary.append({
            "dataset": ds,
            "budget": budget,
            "method": method,
            "backbone": backbone,
            "n_seeds": len(accs),
            "test_acc_mean": round(float(accs.mean()), 2),
            "test_acc_std": round(float(accs.std(ddof=1)) if len(accs) > 1 else 0.0, 2),
            "test_acc_min": round(float(accs.min()), 2),
            "test_acc_max": round(float(accs.max()), 2),
            "n_nodes": int(first["n_nodes"]),
            "n_edges": int(first["n_edges"]),
            "n_features": int(first["n_features"]),
            "logical_KB": round(first["logical_KB"], 1),
            "file_bytes": first.get("file_bytes", ""),
        })

    summary.sort(key=lambda r: (r["dataset"],
                                budget_key(r["budget"]),
                                METHOD_ORDER.index(r["method"]) if r["method"] in METHOD_ORDER else 99,
                                BACKBONE_ORDER.index(r["backbone"]) if r["backbone"] in BACKBONE_ORDER else 99))

    out = path.parent / f"summary_{path.stem}.csv"
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)

    print(f"\n## {path.name}: {len(rows)} runs, {len(summary)} groups -> {out}")
    header = ("| dataset | budget | method | GNN | n | test acc | nodes | edges | feats |"
              " logical KB |")
    print(header)
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in summary:
        print(f"| {r['dataset']} | {fmt_budget(r['budget'])} | {r['method']} | "
              f"{r['backbone']} | {r['n_seeds']} | {r['test_acc_mean']:.2f} ± "
              f"{r['test_acc_std']:.2f} | {r['n_nodes']} | {r['n_edges']} | "
              f"{r['n_features']} | {r['logical_KB']:.1f} |")

    # missing seeds inside an otherwise complete group
    few = [r for r in summary if r["n_seeds"] < 3]
    if few:
        print(f"note: {len(few)} groups have < 3 seeds "
              f"(e.g. {few[0]['dataset']}/{fmt_budget(few[0]['budget'])}/"
              f"{few[0]['method']}/{few[0]['backbone']})")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--inputs", nargs="+",
                   default=["results/experiment1.csv",
                            "results/experiment2.csv",
                            "results/experiment3.csv"])
    args = p.parse_args()

    any_found = False
    for name in args.inputs:
        path = Path(name)
        if not path.exists() or path.stat().st_size == 0:
            print(f"skip {path} (missing or empty)")
            continue
        any_found = True
        summarise(load(path), path)
    if not any_found:
        raise SystemExit("no result CSV found -- run experiment/run_exp1.sh first")


if __name__ == "__main__":
    main()