#!/usr/bin/env bash
# Experiment 4: sensitivity to k, the kNN parameter of Rev-k-NN
# (paper: Fig. 6c / section 4.5).  main.py already exposes --k; we only need to
# keep one graph per k, so each run is copied out of saved_ours/ first.
#
#   PY=../pytorch_env/bin/python bash experiment/run_exp4.sh
set -euo pipefail

PY="${PY:-python}"
DATASET="${DATASET:-cora}"
BUDGET="${BUDGET:-0.01}"
KS="${KS:-1 3 5 10}"
SEEDS="${SEEDS:-5}"
NEPOCHS="${NEPOCHS:-100}"
OUT="${OUT:-results/experiment4.csv}"

cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD"
mkdir -p results outputs/k_sweep outputs/training

for k in $KS; do
  echo "=== k=${k}: condense ${DATASET} ${BUDGET}"
  "$PY" main.py --dataset "$DATASET" --target_size_frac "$BUDGET" \
    --k "$k" --nepochs 1 --save

  dir="outputs/k_sweep/${DATASET}-${BUDGET}_k${k}"
  mkdir -p "$dir"
  cp "saved_ours/${DATASET}-${BUDGET}/data_m_0.9.pt" "$dir/"

  echo "--- train bonsai_k${k}"
  "$PY" experiment/train_condensed.py --dataset "$DATASET" --budget "$BUDGET" \
    --graph "$dir/data_m_0.9.pt" --method "bonsai_k${k}" --model GCN \
    --seeds "$SEEDS" --nepochs "$NEPOCHS" --out "$OUT"
done

# restore the canonical k=5 checkpoint in saved_ours/
cp "outputs/k_sweep/${DATASET}-${BUDGET}_k5/data_m_0.9.pt" \
   "saved_ours/${DATASET}-${BUDGET}/data_m_0.9.pt" 2>/dev/null || true

"$PY" experiment/collect_results.py --inputs "$OUT"
