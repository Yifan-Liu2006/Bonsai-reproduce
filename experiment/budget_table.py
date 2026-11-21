r"""Print the byte budget and the number of nodes that fit in it.

Follows the paper's definition (Sec. 4.1):

    S_r = size of condensed dataset in bytes / size of full dataset in bytes

The size of a *full* graph is computed exactly like ``Bonsai/main.py:size()``:

    (n_nodes * n_features * 1 + n_edges * 2) * 2        # int features -> 2 bytes

For the dense-float baselines (Random / Herding) the official convention in
``Bonsai/baselines/README.md`` is:

    size(n) = 4*n^2 + 4*n*d   ->   n = (sqrt(d^2 + t) - d) / 2

which is the number of nodes a baseline is allowed to keep at budget ``t``.

Usage (from the Bonsai/ directory):

    PYTHONPATH=. python experiment/budget_table.py \
        --datasets cora citeseer --budgets 0.005 0.01 0.03
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import torch

REPO_ROOT = Path(__file__).resolve().parents[1]


def full_size_bytes(n_nodes: int, n_edges: int, n_features: int) -> int:
    r"""Same accounting as Bonsai/main.py:size(dtype="int")."""
    return (n_nodes * n_features + n_edges * 2) * 2


def nodes_for_budget(n_features: int, budget_bytes: float) -> int:
    r"""n = (sqrt(d^2 + t) - d) / 2  (baselines/README.md)."""
    return int((math.sqrt(n_features ** 2 + budget_bytes) - n_features) / 2)


def load_planetoid(dataset: str, root: str):
    from torch_geometric.datasets import Planetoid

    raw = Path(root) / dataset / "raw" / f"ind.{dataset}.x"
    if not raw.exists():
        raise RuntimeError(
            f"missing raw files for {dataset} at {raw.parent}\n"
            "download them with:\n"
            f"  mkdir -p {raw.parent} && cd {raw.parent} && "
            "for f in x tx allx y ty ally graph test.index; do "
            f"curl -sSLO https://cdn.jsdelivr.net/gh/kimiyoung/planetoid@master/data/ind.{dataset}.$f; done"
        )
    return Planetoid(root=root, name=dataset)._data


def condensed_stats(path: Path) -> dict:
    r"""Logical (paper) size and real file size of a saved condensed graph."""
    if not path.exists():
        return {}
    ck = torch.load(path, map_location="cpu", weights_only=False)
    d = ck["data"] if isinstance(ck, dict) else ck
    n_nodes, n_features = d.x.shape
    n_edges = d.edge_index.shape[1]
    nnz = int((d.x != 0).sum().item())
    return {
        "bonsai_nodes": n_nodes,
        "bonsai_edges": n_edges,
        "bonsai_features": n_features,
        "bonsai_target_nodes": int(d.target.sum().item()) if hasattr(d, "target") else "",
        "bonsai_logical_KB": (nnz + 2 * n_edges) * 2 / 1024,
        "bonsai_file_bytes": path.stat().st_size,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--datasets", nargs="+", default=["cora", "citeseer"])
    p.add_argument("--budgets", nargs="+", type=float, default=[0.005, 0.01, 0.03])
    p.add_argument("--data-root", default="datasets")
    p.add_argument("--cond-root", default="saved_ours")
    p.add_argument("--out", default="results/budget_table.csv")
    args = p.parse_args()

    rows = []
    for ds in args.datasets:
        try:
            data = load_planetoid(ds, args.data_root)
        except RuntimeError as exc:
            print(f"[skip] {ds}: {exc}", flush=True)
            continue
        n_nodes, n_features = data.x.shape
        n_edges = data.edge_index.shape[1]
        full = full_size_bytes(n_nodes, n_edges, n_features)
        print(f"\n{ds}: nodes={n_nodes} edges={n_edges} features={n_features} "
              f"full={full:,} B ({full / 2**20:.2f} MiB)")
        for frac in args.budgets:
            t = frac * full
            n = nodes_for_budget(n_features, t)
            path = Path(args.cond_root) / f"{ds}-{frac}" / "data_m_0.9.pt"
            stats = condensed_stats(path)
            row = {
                "dataset": ds,
                "budget": frac,
                "full_bytes": full,
                "d": n_features,
                "budget_bytes": round(t),
                "planned_n": n,
            }
            row.update(stats)
            rows.append(row)
            extra = ""
            if stats:
                extra = (f" | bonsai: nodes={stats['bonsai_nodes']} "
                         f"edges={stats['bonsai_edges']} f={stats['bonsai_features']} "
                         f"logical={stats['bonsai_logical_KB']:.1f}KB "
                         f"file={stats['bonsai_file_bytes'] / 2**20:.2f}MiB")
            print(f"  Sr={frac:<6} t={t:>9,.0f} B  n={n:<4}{extra}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["dataset", "budget", "full_bytes", "d", "budget_bytes", "planned_n",
              "bonsai_nodes", "bonsai_edges", "bonsai_features", "bonsai_target_nodes",
              "bonsai_logical_KB", "bonsai_file_bytes"]
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)
    print(f"\nwrote {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()