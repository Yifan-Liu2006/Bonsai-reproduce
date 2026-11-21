r"""Train a GNN on Full / Random / Herding training graphs.

The three data sources used in experiment 1:

* ``full``    -- train on the original graph with the fixed 56/24/20 split.
* ``random``  -- keep ``n`` randomly selected training nodes and the induced
                 subgraph between them (paper: "induced subgraph spanned by a
                 random selection of nodes").
* ``herding`` -- class-stratified herding selection of ``n`` training nodes
                 (Welling, 2009), then the induced subgraph.

``n`` follows the paper's byte budget. With ``S_r`` and the full-graph byte size

    full_bytes = (n_nodes * d + n_edges * 2) * 2

the dense-float baseline convention (``baselines/README.md``) gives

    n = (sqrt(d^2 + t) - d) / 2,      t = S_r * full_bytes

Run ``experiment/budget_table.py`` first to print these numbers.

Usage (from Bonsai/):

    PYTHONPATH=. python experiment/train_baseline.py \
        --dataset cora --method random --model GCN --budget 0.01 --seeds 5
"""

from __future__ import annotations

import argparse
import copy
import csv
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch_geometric.data import Data

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from model import GAT, GCN, GIN  # noqa: E402  (needs repo root on sys.path)

MODELS = {"GCN": GCN, "GAT": GAT, "GIN": GIN}


# --------------------------------------------------------------------------- #
# data / splits
# --------------------------------------------------------------------------- #
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


def get_splits(nnodes: int) -> dict:
    r"""Identical to Bonsai/main.py (L556-562) and saved_ours/train_bonsai.py."""
    from sklearn.model_selection import train_test_split

    train, test = train_test_split(range(nnodes), test_size=0.2, random_state=42)
    rng = np.random.RandomState(seed=0)
    idx_train = rng.choice(train, size=int(0.7 * len(train)), replace=False)
    idx_val = np.array(sorted(set(range(nnodes)) - set(idx_train.tolist()) - set(test)))
    return {"train": np.asarray(idx_train), "val": idx_val, "test": np.asarray(test)}


# --------------------------------------------------------------------------- #
# graph construction
# --------------------------------------------------------------------------- #
def induced_subgraph(data: Data, nodes) -> Data:
    r"""Induced subgraph on ``nodes`` with re-indexed edges."""
    nodes_t = torch.as_tensor(sorted(set(int(v) for v in nodes)), dtype=torch.long)
    keep_node = torch.zeros(data.num_nodes, dtype=torch.bool)
    keep_node[nodes_t] = True
    src, dst = data.edge_index
    keep_edge = keep_node[src] & keep_node[dst]
    remap = torch.full((data.num_nodes,), -1, dtype=torch.long)
    remap[nodes_t] = torch.arange(nodes_t.numel())
    edge_index = remap[data.edge_index[:, keep_edge]]
    return Data(x=data.x[nodes_t].clone(),
                edge_index=edge_index,
                y=data.y[nodes_t].clone())


def random_select(data: Data, train_idx: np.ndarray, n: int, seed: int) -> np.ndarray:
    rng = np.random.RandomState(seed)
    n = min(n, len(train_idx))
    return rng.choice(train_idx, size=n, replace=False)


def herding_select(x: torch.Tensor, y: torch.Tensor, train_idx: np.ndarray,
                   n: int, nclasses: int) -> np.ndarray:
    r"""Class-stratified herding: greedily pick the sample that keeps the running
    class mean closest to the true class mean (Welling, 2009)."""
    X = x.cpu().numpy().astype(np.float64)
    Y = y.cpu().numpy()
    labels = Y[train_idx]
    counts = np.bincount(labels, minlength=nclasses).astype(np.float64)
    prop = counts / counts.sum() * min(n, len(train_idx))
    quota = np.floor(prop).astype(int)
    short = min(n, len(train_idx)) - int(quota.sum())
    if short > 0:  # largest remainder
        for c in np.argsort(-(prop - quota))[:short]:
            quota[c] += 1

    selected = []
    for c in range(nclasses):
        k = int(quota[c])
        if k <= 0:
            continue
        idx = train_idx[labels == c]
        k = min(k, len(idx))
        if k == 0:
            continue
        Xc = X[idx]
        mu = Xc.mean(axis=0)
        running = np.zeros_like(mu)
        available = np.ones(len(idx), dtype=bool)
        for j in range(k):
            target = (j + 1) * mu - running
            dist2 = ((Xc - target) ** 2).sum(axis=1)
            dist2[~available] = np.inf
            best = int(dist2.argmin())
            selected.append(int(idx[best]))
            running += Xc[best]
            available[best] = False
    return np.asarray(selected, dtype=np.int64)


# --------------------------------------------------------------------------- #
# training
# --------------------------------------------------------------------------- #
def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


@torch.no_grad()
def accuracy(model: nn.Module, data: Data, idx: torch.Tensor) -> float:
    model.eval()
    out = model(data.x, data.edge_index)
    pred = out[idx].argmax(dim=1)
    return (pred == data.y[idx]).float().mean().item()


def train_once(backbone: str, syn: Data, full: Data, splits: dict,
               nepochs: int, seed: int, device: torch.device) -> dict:
    """Train ``backbone`` on ``syn``; select the epoch by val acc on ``full``."""
    set_seed(seed)
    indim = syn.x.shape[1]
    nclasses = int(full.y.max().item()) + 1
    model = MODELS[backbone](indim, nclasses, hidim=128).to(device)

    opt = optim.Adam(model.parameters())
    loss_fn = nn.CrossEntropyLoss()

    syn = syn.to(device)
    full_d = full.to(device)
    val = torch.as_tensor(splits["val"], device=device)
    test = torch.as_tensor(splits["test"], device=device)
    target = torch.as_tensor(syn.target, device=device)

    best_val, best_state, best_epoch = -1.0, None, 0
    t0 = time.perf_counter()
    for epoch in range(1, nepochs + 1):
        model.train()
        opt.zero_grad()
        out = model(syn.x, syn.edge_index)
        loss = loss_fn(out[target], syn.y[target])
        loss.backward()
        opt.step()
        if epoch % 5 == 0 or epoch == nepochs:
            val_acc = accuracy(model, full_d, val)
            if val_acc > best_val:
                best_val, best_epoch = val_acc, epoch
                best_state = copy.deepcopy(model.state_dict())
    train_time = time.perf_counter() - t0

    if best_state is not None:
        model.load_state_dict(best_state)
    test_acc = accuracy(model, full_d, test)
    return {"test_acc": test_acc * 100, "val_acc": best_val * 100,
            "best_epoch": best_epoch, "train_time_s": train_time}


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", default="cora")
    p.add_argument("--method", required=True, choices=["full", "random", "herding"])
    p.add_argument("--model", default="GCN", choices=list(MODELS))
    p.add_argument("--budget", type=float, default=None,
                   help="S_r, e.g. 0.01; required for random/herding")
    p.add_argument("--n", type=int, default=None,
                   help="override the node budget (default: derived from --budget)")
    p.add_argument("--seeds", type=int, default=5, help="number of training seeds (0..k-1)")
    p.add_argument("--nepochs", type=int, default=100)
    p.add_argument("--select-seed", type=int, default=42,
                   help="seed of the node selection (fixed across training seeds)")
    p.add_argument("--data-root", default="datasets")
    p.add_argument("--out", default="results/experiment1.csv")
    p.add_argument("--graph-dir", default="outputs/condensation")
    p.add_argument("--log-dir", default="outputs/training")
    args = p.parse_args()

    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    data = load_planetoid(args.dataset, args.data_root)
    splits = get_splits(data.num_nodes)
    train_idx = splits["train"]
    nclasses = int(data.y.max().item()) + 1
    n_nodes, d = data.x.shape
    n_edges = data.edge_index.shape[1]
    full_bytes = (n_nodes * d + n_edges * 2) * 2

    cond_time, notes, sel_nodes, syn = 0.0, "", "", None
    if args.method == "full":
        syn = Data(x=data.x.clone(), edge_index=data.edge_index.clone(),
                   y=data.y.clone(), target=torch.as_tensor(train_idx))
        notes = "full graph, train split only"
    else:
        if args.budget is None:
            raise SystemExit("--budget is required for random/herding")
        if args.n is not None:
            n = args.n
        else:
            import math
            n = int((math.sqrt(d ** 2 + args.budget * full_bytes) - d) / 2)
        t0 = time.perf_counter()
        if args.method == "random":
            picked = random_select(data, train_idx, n, args.select_seed)
        else:
            picked = herding_select(data.x, data.y, train_idx, n, nclasses)
        syn = induced_subgraph(data, picked)
        syn.target = torch.arange(syn.num_nodes)
        cond_time = time.perf_counter() - t0
        sel_nodes = len(picked)
        notes = (f"n={n} S_r={args.budget} induced_subgraph "
                 f"selection=seed{args.select_seed}")
        print(f"{args.method}: selected {len(picked)}/{n} nodes "
              f"({syn.num_nodes} nodes, {syn.edge_index.shape[1] // 2} undirected edges)")

    # logical (paper) size of whatever we train on
    if args.method == "full":
        logical_kb = full_bytes / 1024          # dense n*d accounting for the full graph
    else:
        nnz = int((syn.x != 0).sum().item())
        logical_kb = (nnz + 2 * syn.edge_index.shape[1]) * 2 / 1024

    # persist the constructed graph so its real file size can be compared with
    # the Bonsai one (only meaningful for the condensed-size methods)
    file_bytes = ""
    if args.method != "full":
        gdir = Path(args.graph_dir) / f"{args.dataset}-{args.budget}_{args.method}"
        gdir.mkdir(parents=True, exist_ok=True)
        gpath = gdir / "data.pt"
        torch.save({"data": syn.cpu(), "features_used": np.arange(d)}, gpath)
        file_bytes = gpath.stat().st_size

    Path(args.log_dir).mkdir(parents=True, exist_ok=True)
    log_path = (Path(args.log_dir) /
                f"{args.dataset}_{args.budget}_{args.method}_{args.model}.log")

    fields = ["dataset", "budget", "method", "backbone", "seed", "test_acc", "val_acc",
              "train_time_s", "cond_time_s", "n_nodes", "n_edges", "n_features",
              "logical_KB", "file_bytes", "sel_nodes", "target_nodes", "notes"]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    need_header = not out.exists() or out.stat().st_size == 0

    results = []
    with out.open("a", newline="") as fh, log_path.open("a") as log:
        w = csv.DictWriter(fh, fieldnames=fields)
        if need_header:
            w.writeheader()
        for seed in range(args.seeds):
            res = train_once(args.model, syn, data, splits, args.nepochs, seed, device)
            results.append(res)
            row = {
                "dataset": args.dataset,
                "budget": args.budget if args.budget is not None else "full",
                "method": args.method,
                "backbone": args.model,
                "seed": seed,
                "test_acc": round(res["test_acc"], 2),
                "val_acc": round(res["val_acc"], 2),
                "train_time_s": round(res["train_time_s"], 3),
                "cond_time_s": round(cond_time, 3),
                "n_nodes": syn.num_nodes,
                "n_edges": syn.edge_index.shape[1],
                "n_features": d,
                "logical_KB": round(logical_kb, 1),
                "file_bytes": file_bytes,
                "sel_nodes": sel_nodes,
                "target_nodes": int(syn.target.numel()),
                "notes": notes,
            }
            w.writerow(row)
            line = (f"[{args.method}/{args.model}] {args.dataset} "
                    f"budget={row['budget']} seed={seed} "
                    f"test={res['test_acc']:.2f} val={res['val_acc']:.2f} "
                    f"({res['train_time_s']:.2f}s, best epoch {res['best_epoch']})")
            print(line, flush=True)
            log.write(line + "\n")

    accs = np.array([r["test_acc"] for r in results])
    shown_budget = args.budget if args.budget is not None else "full"
    print(f"\n{args.method}/{args.model} {args.dataset} budget={shown_budget}: "
          f"test = {accs.mean():.2f} +/- {accs.std():.2f}  (n={len(accs)} seeds)")
    print(f"nodes={syn.num_nodes} edges={syn.edge_index.shape[1]} "
          f"logical={logical_kb:.1f}KB file={file_bytes} -> {out}")


if __name__ == "__main__":
    main()