#!/bin/bash
#SBATCH --job-name=dop-s2p3-gate
#SBATCH --partition=boost_usr_prod
#SBATCH --account=AIFAC_P02_548
#SBATCH --qos=boost_qos_dbg
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=32
#SBATCH --time=00:20:00
#SBATCH --output=/leonardo_work/AIFAC_P02_548/DOPPLER/logs/%x-%j.out
#
# Stage 2 PILOT -- PHASE 1: build-time zero-information gate
# PILOT -- pipeline validation on dev subjects; no research conclusions.
# Projected 0.0633 node-hours. One engine init; every prompt file runs
# through it in sequence. Re-submitting skips any file that already has output.
set -euo pipefail
D=/leonardo_work/AIFAC_P02_548/DOPPLER
cd "$D"
source jobs/site_env.sh
source "$D/.venv-vllm-new/bin/activate"
mkdir -p "/leonardo_work/AIFAC_P02_548/DOPPLER/runs/stage2_pilot3"
echo "[stage2_pilot3_gate] node=$(hostname) start=$(date -u +%FT%TZ)"

ARGS=()
for f in "gate"; do
  P="/leonardo_work/AIFAC_P02_548/DOPPLER/runs/stage2_pilot3/prompts_$f.jsonl"
  O="/leonardo_work/AIFAC_P02_548/DOPPLER/runs/stage2_pilot3/completions_$f.jsonl"
  if [[ -f "$O.summary.json" ]]; then
    echo "[skip] $f already complete"
  else
    ARGS+=(--prompts "$P" --out "$O")
  fi
done
if [[ ${#ARGS[@]} -eq 0 ]]; then
  echo "all prompt files complete; nothing to do."
  exit 0
fi
python jobs/batch_generate.py \
    --model-dir "/leonardo_work/AIFAC_P02_548/DOPPLER/models/Gemma-4-31B-it" --tp 4 --max-model-len 8192 \
    --gpu-mem-util 0.92 --temperature 0.0 \
    "${ARGS[@]}"

echo "[stage2_pilot3_gate] DONE $(date -u +%FT%TZ)"
