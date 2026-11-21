r"""Measure Bonsai's condensation cost (paper section 4.4) on this machine.

Runs ``main.py`` with the downstream GCN training replaced by a no-op, so the
wall time reported here is *condensation only* (WL representations, decision
tree, Rev-k-NN + CELF, subgraph construction, PPR, class matching, save).

The training time per epoch is taken from ``results/experiment1.csv`` (the
``bonsai`` rows produced by ``run_exp1.sh``), and the graph size is read back
from the saved checkpoint.

Usage (from Bonsai/):

    PYTHONPATH=. python experiment/measure_condensation.py \
        --datasets cora citeseer --budgets 0.005 0.01 0.03
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import io
import sys
import time
from pathlib import Path

import torch

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import main as bonsai_main  # noqa: E402


def _noop_train_model(**kwargs):
    return 0.0


def measure(dataset: str, budget: float, nepochs: int) -> dict:
    bonsai_main.train_model = _noop_train_model
    sys.argv = ["main.py", "--dataset", dataset, "--target_size_frac", str(budget),
                "--nepochs", str(nepochs), "--save"]
    t0 = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        bonsai_main.main()          # tqdm and the Timer banner are noise here
    cond_time = time.perf_counter() - t0

    path = REPO / "saved_ours" / f"{dataset}-{budget}" / "data_m_0.9.pt"
    ck = torch.load(path, map_location="cpu", weights_only=False)
    d = ck["data"]
    nnz = int((d.x != 0).sum().item())
    n_edges = d.edge_index.shape[1]
    return {
        "dataset": dataset,
        "budget": budget,
        "cond_time_s": round(cond_time, 2),
        "nodes": d.num_nodes,
        "edges": n_edges,
        "features": d.x.shape[1],
        "logical_KB": round((nnz + 2 * n_edges) * 2 / 1024, 1),
        "file_bytes": path.stat().st_size,
    }


def training_times(path: Path) -> dict:
    r"""Mean per-epoch training time of the Bonsai GCN cells, in ms."""
    out = {}
    if not path.exists():
        return out
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            if row["method"] != "bonsai" or row["backbone"] != "GCN":
                continue
            key = (row["dataset"], float(row["budget"]))
            out.setdefault(key, []).append(float(row["train_time_s"]))
    return {k: sum(v) / len(v) for k, v in out.items()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", nargs="+", default=["cora", "citeseer"])
    ap.add_argument("--budgets", nargs="+", type=float, default=[0.005, 0.01, 0.03])
    ap.add_argument("--nepochs", type=int, default=100)
    ap.add_argument("--results", default="results/experiment1.csv")
    ap.add_argument("--out", default="results/efficiency.csv")
    args = ap.parse_args()

    train_means = training_times(Path(args.results))
    rows = []
    for ds in args.datasets:
        for b in args.budgets:
            row = measure(ds, b, args.nepochs)
            ttrain = train_means.get((ds, b), float("nan"))
            row["train_time_s_100ep"] = round(ttrain, 2) if ttrain == ttrain else ""
            rows.append(row)
            print(f"{ds:9s} S_r={b:<6} cond={row['cond_time_s']:5.2f}s "
                  f"train(100ep)={row['train_time_s_100ep']:>5} "
                  f"nodes={row['nodes']:5d} logical={row['logical_KB']:6.1f}KB "
                  f"file={row['file_bytes'] / 2**20:.2f}MiB", flush=True)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
