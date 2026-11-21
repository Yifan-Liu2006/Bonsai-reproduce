#!/usr/bin/env bash
# Experiment 2: cross-architecture generalization on the *same* condensed graph.
# Never re-condense per architecture.
#
#   PY=../pytorch_env/bin/python bash experiment/run_exp2.sh
set -euo pipefail

PY="${PY:-python}"
DATASETS="${DATASETS:-cora citeseer}"
BUDGETS="${BUDGETS:-0.005 0.01 0.03}"
SEEDS="${SEEDS:-5}"
MODELS="${MODELS:-GCN GAT GIN}"
NEPOCHS="${NEPOCHS:-100}"

cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD"
mkdir -p results outputs/training

for ds in $DATASETS; do
  for tf in $BUDGETS; do
    graph="saved_ours/${ds}-${tf}/data_m_0.9.pt"
    if [ ! -f "$graph" ]; then
      echo "!! missing $graph -- run experiment/run_exp1.sh first" >&2
      exit 1
    fi
    for model in $MODELS; do
      echo "--- bonsai/${model} ${ds} ${tf}"
      "$PY" experiment/train_condensed.py --dataset "$ds" --budget "$tf" \
        --graph "$graph" --method bonsai --model "$model" \
        --seeds "$SEEDS" --nepochs "$NEPOCHS" --out results/experiment2.csv
    done
  done
done

"$PY" experiment/collect_results.py --inputs results/experiment2.csv
