#!/usr/bin/env bash
# Experiment 3: ablations on Cora -- random exemplars vs no PPR.
#
#   PY=../pytorch_env/bin/python bash experiment/run_exp3.sh
#
# Notes
#  * 1% is a no-op for both ablations: the budget already covers every training
#    node, so any exemplar ordering yields the same graph (verified byte-wise).
#    The informative budgets are <= 0.5%, where the graph is actually compressed.
#  * the random-exemplar graph comes out ~19% larger at the same S_r (randomly
#    ordered nodes have cheaper neighbourhoods before PPR), so a size-matched
#    point (S_r=0.08%) is added for a fair comparison.
set -euo pipefail

PY="${PY:-python}"
DATASET="${DATASET:-cora}"
BUDGETS="${BUDGETS:-0.001 0.002 0.005 0.01}"
MATCHED_BUDGET="${MATCHED_BUDGET:-0.0008}"
SEEDS="${SEEDS:-5}"
MODEL="${MODEL:-GCN}"

cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD"
mkdir -p results outputs/condensation outputs/training

for tf in $BUDGETS; do
  graph="saved_ours/${DATASET}-${tf}/data_m_0.9.pt"
  [ -f "$graph" ] || { echo "=== condense ${DATASET} ${tf}"; "$PY" main.py \
      --dataset "$DATASET" --target_size_frac "$tf" --nepochs 1 --save; }

  echo "--- bonsai ${tf}"
  "$PY" experiment/train_condensed.py --dataset "$DATASET" --budget "$tf" \
    --graph "$graph" --method bonsai --model "$MODEL" --seeds "$SEEDS" \
    --out results/experiment3.csv

  for variant in random_exemplar no_ppr; do
    vgraph="outputs/${variant}/${DATASET}-${tf}/data_m_0.9.pt"
    if [ ! -f "$vgraph" ]; then
      echo "=== ${variant} ${DATASET} ${tf}"
      "$PY" "experiment/main_${variant}.py" --dataset "$DATASET" \
        --target_size_frac "$tf" --nepochs 1 --save
    fi
    echo "--- bonsai_${variant} ${tf}"
    "$PY" experiment/train_condensed.py --dataset "$DATASET" --budget "$tf" \
      --graph "$vgraph" --method "bonsai_${variant}" --model "$MODEL" \
      --seeds "$SEEDS" --out results/experiment3.csv
  done
done

echo "=== size-matched random exemplar (S_r=${MATCHED_BUDGET})"
mgraph="outputs/random_exemplar/${DATASET}-${MATCHED_BUDGET}/data_m_0.9.pt"
if [ ! -f "$mgraph" ]; then
  "$PY" experiment/main_random_exemplar.py --dataset "$DATASET" \
    --target_size_frac "$MATCHED_BUDGET" --nepochs 1 --save
fi
"$PY" experiment/train_condensed.py --dataset "$DATASET" --budget "$MATCHED_BUDGET" \
  --graph "$mgraph" --method bonsai_rand_exemplar --model "$MODEL" \
  --seeds "$SEEDS" --out results/experiment3.csv

"$PY" experiment/collect_results.py --inputs results/experiment3.csv
