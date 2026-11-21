#!/usr/bin/env bash
# Experiment 1: condensation quality (Full / Random / Herding / Bonsai) x seeds.
#
#   PY=../pytorch_env/bin/python bash experiment/run_exp1.sh
#
# Override through the environment, e.g.
#   DATASETS="cora" BUDGETS="0.01" SEEDS=3 bash experiment/run_exp1.sh
set -euo pipefail

PY="${PY:-python}"
DATASETS="${DATASETS:-cora citeseer}"
BUDGETS="${BUDGETS:-0.005 0.01 0.03}"
SEEDS="${SEEDS:-5}"
MODELS="${MODELS:-GCN}"
NEPOCHS="${NEPOCHS:-100}"

cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD"
mkdir -p results outputs/condensation outputs/training

for ds in $DATASETS; do
  # Full graph is budget-independent: train it exactly once per dataset.
  for model in $MODELS; do
    echo "=== full/${model} ${ds}"
    "$PY" experiment/train_baseline.py --dataset "$ds" --method full \
      --model "$model" --seeds "$SEEDS" --nepochs "$NEPOCHS" \
      --out results/experiment1.csv
  done

  for tf in $BUDGETS; do
    graph="saved_ours/${ds}-${tf}/data_m_0.9.pt"
    if [ ! -f "$graph" ]; then
      echo "=== condense ${ds} ${tf}"
      time "$PY" main.py --dataset "$ds" --target_size_frac "$tf" \
        --nepochs "$NEPOCHS" --save
    else
      echo "=== reuse ${graph}"
    fi

    for model in $MODELS; do
      for method in random herding; do
        echo "--- ${method}/${model} ${ds} ${tf}"
        "$PY" experiment/train_baseline.py --dataset "$ds" --method "$method" \
          --model "$model" --seeds "$SEEDS" --nepochs "$NEPOCHS" \
          --budget "$tf" --out results/experiment1.csv
      done

      echo "--- bonsai/${model} ${ds} ${tf}"
      "$PY" experiment/train_condensed.py --dataset "$ds" --budget "$tf" \
        --graph "$graph" --method bonsai --model "$model" \
        --seeds "$SEEDS" --nepochs "$NEPOCHS" --out results/experiment1.csv
    done
  done
done

"$PY" experiment/budget_table.py --datasets $DATASETS --budgets $BUDGETS
"$PY" experiment/collect_results.py --inputs results/experiment1.csv
