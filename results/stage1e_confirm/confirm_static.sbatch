#!/bin/bash
#SBATCH --job-name=dop-confirm-static
#SBATCH --partition=boost_usr_prod
#SBATCH --account=AIFAC_P02_548
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=32
#SBATCH --time=04:00:00
#SBATCH --output=/leonardo_work/AIFAC_P02_548/DOPPLER/logs/%x-%j.out
#
# Stage 1E CONFIRM run -- static arms (baseline, random, fixed, imposter)
# Frozen by PREREGISTRATION_AMENDMENT_1_ADDENDUM_A.md section A.
# Production queue (boost_usr_prod), NOT the debug QOS.
# Projected 1.424 node-hours. Resumable: resubmitting continues.
set -euo pipefail
D=/leonardo_work/AIFAC_P02_548/DOPPLER
cd "$D"
source jobs/site_env.sh
source "$D/.venv-vllm-new/bin/activate"
mkdir -p "/leonardo_work/AIFAC_P02_548/DOPPLER/runs/stage1e_confirm"
echo "[confirm_static] node=$(hostname) start=$(date -u +%FT%TZ)"

ARGS=()
for c in $(seq 0 3); do
  P="/leonardo_work/AIFAC_P02_548/DOPPLER/runs/stage1e_confirm/prompts_static_$c.jsonl"
  O="/leonardo_work/AIFAC_P02_548/DOPPLER/runs/stage1e_confirm/completions_static_$c.jsonl"
  if [[ -f "$O.summary.json" ]]; then
    echo "[confirm_static] chunk $c already complete, skipping"
  else
    ARGS+=(--prompts "$P" --out "$O")
  fi
done
if [[ ${#ARGS[@]} -eq 0 ]]; then
  echo "[confirm_static] all chunks complete; nothing to do."
  exit 0
fi
python jobs/batch_generate.py \
    --model-dir "/leonardo_work/AIFAC_P02_548/DOPPLER/models/Gemma-4-31B-it" --tp 4 --max-model-len 2048 \
    --gpu-mem-util 0.92 --temperature 0.0 \
    "${ARGS[@]}"

echo "[confirm_static] DONE $(date -u +%FT%TZ)"
