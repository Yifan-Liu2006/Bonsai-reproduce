r"""Train a GNN on an already-condensed graph (Bonsai or an ablation variant).

Bonsai's own training entry (``saved_ours/train_bonsai.py``) trains once and
never reports the accuracy, which makes it unusable for a 5-seed table.  This
script reuses the *same* training backend as ``experiment/train_baseline.py``
so that every cell of a table is produced by identical code, and appends rows
with the same CSV schema.

Usage (from Bonsai/):

    PYTHONPATH=. python experiment/train_condensed.py \
        --dataset cora --budget 0.01 \
        --graph saved_ours/cora-0.01/data_m_0.9.pt \
        --method bonsai --model GCN --seeds 5
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

# shared with the baseline script on purpose: one backend -> comparable numbers
from train_baseline import get_splits, load_planetoid, train_once  # noqa: E402

FIELDS = ["dataset", "budget", "method", "backbone", "seed", "test_acc", "val_acc",
          "train_time_s", "cond_time_s", "n_nodes", "n_edges", "n_features",
          "logical_KB", "file_bytes", "sel_nodes", "target_nodes", "notes"]


def load_condensed(path: Path):
    ck = torch.load(path, map_location="cpu", weights_only=False)
    if isinstance(ck, dict) and "data" in ck:
        syn = ck["data"]
        features_used = ck.get("features_used")
    else:
        syn, features_used = ck, None
    return syn, features_used


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", default="cora")
    p.add_argument("--budget", type=float, required=True, help="S_r, e.g. 0.01")
    p.add_argument("--graph", required=True, help="path to data_m_0.9.pt")
    p.add_argument("--method", default="bonsai",
                   help="label written to the CSV (bonsai / bonsai_no_ppr / ...)")
    p.add_argument("--model", default="GCN", choices=["GCN", "GAT", "GIN"])
    p.add_argument("--seeds", type=int, default=5)
    p.add_argument("--nepochs", type=int, default=100)
    p.add_argument("--cond-time", type=float, default=None,
                   help="optional condensation wall time (recorded in the CSV)")
    p.add_argument("--data-root", default="datasets")
    p.add_argument("--out", default="results/experiment1.csv")
    p.add_argument("--log-dir", default="outputs/training")
    args = p.parse_args()

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    graph_path = Path(args.graph)
    if not graph_path.exists():
        raise SystemExit(f"condensed graph not found: {graph_path}")

    syn, features_used = load_condensed(graph_path)
    data = load_planetoid(args.dataset, args.data_root)
    splits = get_splits(data.num_nodes)

    # the condensed graph only kept a subset of the feature columns, so the
    # evaluation graph must use the same columns
    if features_used is not None and len(features_used) < data.x.shape[1]:
        cols = torch.as_tensor(np.asarray(features_used), dtype=torch.long)
        data.x = data.x[:, cols]
        print(f"feature slice: {len(features_used)}/{len(cols)} -> "
              f"eval graph x={tuple(data.x.shape)}")

    assert syn.num_nodes == syn.num_nodes  # noqa: PLR0124  (guard for empty graphs)
    if not hasattr(syn, "target") or syn.target is None:
        raise SystemExit("condensed graph has no 'target' field")

    n_edges = syn.edge_index.shape[1]
    nnz = int((syn.x != 0).sum().item())
    logical_kb = (nnz + 2 * n_edges) * 2 / 1024
    file_bytes = graph_path.stat().st_size

    Path(args.log_dir).mkdir(parents=True, exist_ok=True)
    log_path = Path(args.log_dir) / f"{args.dataset}_{args.budget}_{args.method}_{args.model}.log"
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    need_header = not out.exists() or out.stat().st_size == 0

    results = []
    with out.open("a", newline="") as fh, log_path.open("a") as log:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if need_header:
            w.writeheader()
        for seed in range(args.seeds):
            res = train_once(args.model, syn, data, splits, args.nepochs, seed, device)
            results.append(res)
            row = {
                "dataset": args.dataset,
                "budget": args.budget,
                "method": args.method,
                "backbone": args.model,
                "seed": seed,
                "test_acc": round(res["test_acc"], 2),
                "val_acc": round(res["val_acc"], 2),
                "train_time_s": round(res["train_time_s"], 3),
                "cond_time_s": "" if args.cond_time is None else round(args.cond_time, 3),
                "n_nodes": syn.num_nodes,
                "n_edges": n_edges,
                "n_features": syn.x.shape[1],
                "logical_KB": round(logical_kb, 1),
                "file_bytes": file_bytes,
                "sel_nodes": "",
                "target_nodes": int(syn.target.sum().item()),
                "notes": f"graph={graph_path}",
            }
            w.writerow(row)
            line = (f"[{args.method}/{args.model}] {args.dataset} budget={args.budget} "
                    f"seed={seed} test={res['test_acc']:.2f} val={res['val_acc']:.2f} "
                    f"({res['train_time_s']:.2f}s, best epoch {res['best_epoch']})")
            print(line, flush=True)
            log.write(line + "\n")

    accs = np.array([r["test_acc"] for r in results])
    print(f"\n{args.method}/{args.model} {args.dataset} budget={args.budget}: "
          f"test = {accs.mean():.2f} +/- {accs.std():.2f}  (n={len(accs)} seeds)")
    print(f"nodes={syn.num_nodes} edges={n_edges} features={syn.x.shape[1]} "
          f"logical={logical_kb:.1f}KB file={file_bytes} -> {out}")


if __name__ == "__main__":
    main()