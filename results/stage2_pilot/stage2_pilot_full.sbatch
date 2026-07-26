#!/bin/bash
#SBATCH --job-name=dop-s2pilot-full
#SBATCH --partition=boost_usr_prod
#SBATCH --account=AIFAC_P02_548
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=32
#SBATCH --time=01:00:00
#SBATCH --output=/leonardo_work/AIFAC_P02_548/DOPPLER/logs/%x-%j.out
#
# Stage 2 PILOT -- all 10 prediction sets + the follow-up classifier
# PILOT -- pipeline validation on dev subjects; no research conclusions.
# Projected 0.1086 node-hours. One engine init; every prompt file runs
# through it in sequence. Re-submitting skips any file that already has output.
set -euo pipefail
D=/leonardo_work/AIFAC_P02_548/DOPPLER
cd "$D"
source jobs/site_env.sh
source "$D/.venv-vllm-new/bin/activate"
mkdir -p "/leonardo_work/AIFAC_P02_548/DOPPLER/runs/stage2_pilot"
echo "[stage2_pilot_full] node=$(hostname) start=$(date -u +%FT%TZ)"

ARGS=()
for f in "pred_twin_redacted_standard" "pred_twin_redacted_stripped" "pred_twin_named_standard" "pred_twin_named_stripped" "pred_zeroinfo_redacted_standard" "pred_zeroinfo_redacted_stripped" "pred_zeroinfo_named_standard" "pred_zeroinfo_named_stripped" "pred_imposter_redacted_standard" "pred_imposter_redacted_stripped" "classify"; do
  P="/leonardo_work/AIFAC_P02_548/DOPPLER/runs/stage2_pilot/prompts_$f.jsonl"
  O="/leonardo_work/AIFAC_P02_548/DOPPLER/runs/stage2_pilot/completions_$f.jsonl"
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

echo "[stage2_pilot_full] DONE $(date -u +%FT%TZ)"
