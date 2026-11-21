r"""Train a GNN on the synthetic graphs shipped in ``baselines/saved_*``.

The paper compares against GCond / GDEM / GCSR, whose condensation code is not
part of this repository -- but the *synthetic graphs* for Cora and Citeseer are,
under ``baselines/saved_gcond``, ``saved_GCSR`` and ``saved_GDEM``.  This script
runs the authors' own training backend on them, so the numbers are directly
comparable with ``experiment/train_baseline.py`` and ``train_condensed.py``.

Nothing under ``baselines/`` is modified; the official modules are imported by
putting ``baselines/`` and ``experiment/shims`` on ``sys.path`` (the shim only
replaces ``torch_sparse``, which is unavailable on macOS/ARM).

Usage (from Bonsai/):

    PYTHONPATH=. python experiment/train_released_baseline.py \
        --family gcond --dataset cora --budget 0.01 --seeds 5
"""

from __future__ import annotations

import argparse
import csv
import importlib
import sys
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parents[1]
for p in (str(REPO / "experiment" / "shims"), str(REPO / "baselines"), str(REPO)):
    if p not in sys.path:
        sys.path.insert(0, p)

from train_baseline import set_seed  # noqa: E402

FAMILIES = {
    "gcond": ("train_gcond", "saved_gcond"),
    "gcsr": ("train_gcsr", "saved_GCSR"),
    "gdem": ("train_gdem", "saved_GDEM"),
}

FIELDS = ["dataset", "budget", "method", "backbone", "seed", "test_acc", "val_acc",
          "train_time_s", "cond_time_s", "n_nodes", "n_edges", "n_features",
          "logical_KB", "file_bytes", "sel_nodes", "target_nodes", "notes"]


class _NullWriter:
    def add_scalar(self, *args, **kwargs):
        pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", required=True, choices=list(FAMILIES))
    ap.add_argument("--dataset", default="cora")
    ap.add_argument("--budget", required=True, help="S_r, e.g. 0.01")
    ap.add_argument("--model", default="GCN", choices=["GCN", "GAT", "GIN"])
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--nepochs", type=int, default=100)
    ap.add_argument("--data-root", default="datasets")
    ap.add_argument("--synth-root", default=None,
                    help="default: baselines/<family dir>")
    ap.add_argument("--out", default="results/experiment1.csv")
    args = ap.parse_args()

    module_name, default_root = FAMILIES[args.family]
    synth_root = args.synth_root or str(REPO / "baselines" / default_root)
    if not Path(synth_root).exists():
        raise SystemExit(f"no released synthetic graphs at {synth_root}")

    mod = importlib.import_module(module_name)
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

    data = mod.load_dataset(args.dataset.lower(), args.data_root)
    data_syn = mod.load_syn_dataset(args.dataset.lower(), args.budget,
                                    synth_root, data["scaler"])
    splits = mod.get_splits(data["data"].num_nodes)

    syn = data_syn["data"]
    model_type = args.model + "E"          # the authors' edge-weighted variant
    model_class = getattr(mod, model_type)
    nclasses = int(data["data"].y.max().item()) + 1
    hidim = 128

    n_nodes, n_features = syn.x.shape
    n_edges = syn.edge_index.shape[1]
    nnz = int((syn.x != 0).sum().item())
    logical_kb = (nnz + 2 * n_edges) * 2 / 1024
    graph_dir = Path(synth_root) / f"{args.dataset.lower()}-{args.budget}"
    file_bytes = sum(p.stat().st_size for p in graph_dir.glob("*.pt"))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    need_header = not out.exists() or out.stat().st_size == 0

    rows, accs, times = [], [], []
    with out.open("a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if need_header:
            w.writeheader()
        for seed in range(args.seeds):
            set_seed(seed)
            model = model_class(indim=n_features, outdim=nclasses, hidim=hidim).to(device)
            t0 = __import__("time").perf_counter()
            acc = mod.train_backend_pyg(model, args.nepochs, data, data_syn,
                                        splits, _NullWriter())
            dur = __import__("time").perf_counter() - t0
            accs.append(acc * 100)
            times.append(dur)
            row = {
                "dataset": args.dataset,
                "budget": args.budget,
                "method": args.family,
                "backbone": args.model,
                "seed": seed,
                "test_acc": round(acc * 100, 2),
                "val_acc": "",          # the released backend keeps the best
                "train_time_s": round(dur, 3),   # val epoch internally but does not
                "cond_time_s": "",               # expose it; condensation is n/a
                "n_nodes": n_nodes,
                "n_edges": n_edges,
                "n_features": n_features,
                "logical_KB": round(logical_kb, 1),
                "file_bytes": file_bytes,
                "sel_nodes": "",
                "target_nodes": n_nodes,
                "notes": f"released synthetic graph in {graph_dir}",
            }
            w.writerow(row)
            rows.append(row)
            print(f"[{args.family}/{args.model}] {args.dataset} budget={args.budget} "
                  f"seed={seed} test={acc * 100:.2f} ({dur:.2f}s)", flush=True)

    accs = np.array(accs)
    print(f"\n{args.family}/{args.model} {args.dataset} budget={args.budget}: "
          f"test = {accs.mean():.2f} +/- {accs.std():.2f}  (n={len(accs)} seeds)")
    print(f"nodes={n_nodes} edges={n_edges} features={n_features} "
          f"logical={logical_kb:.1f}KB file={file_bytes} -> {out}")


if __name__ == "__main__":
    main()
