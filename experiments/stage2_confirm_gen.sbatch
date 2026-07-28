#!/bin/bash
#SBATCH --job-name=dop-s2confirm-gen
#SBATCH --partition=boost_usr_prod
#SBATCH --account=AIFAC_P02_548
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=32
#SBATCH --time=01:30:00
#SBATCH --output=/leonardo_work/AIFAC_P02_548/DOPPLER/logs/%x-%j.out
#
# Stage 2 CONFIRMATORY generations, Gemma-4-31B-it, one prompt chunk per job.
# Usage: sbatch stage2_confirm_gen.sbatch chunk_01
# Chunks are independent whole-subject blocks (render_manifest.json), so jobs
# run in parallel per the owner's GO. Re-submitting skips a finished chunk.
# Caps: 8 node-hours total for the confirmatory run; billing from sacct after
# every chunk, failed attempts included.
set -euo pipefail
CHUNK="${1:?usage: sbatch stage2_confirm_gen.sbatch chunk_NN}"
D=/leonardo_work/AIFAC_P02_548/DOPPLER
cd "$D"
source jobs/site_env.sh
source "$D/.venv-vllm-new/bin/activate"
RUN="$D/runs/stage2_confirm"
mkdir -p "$RUN"
echo "[s2confirm-gen] chunk=$CHUNK node=$(hostname) start=$(date -u +%FT%TZ)"

P="$RUN/${CHUNK}.prompts.jsonl"
O="$RUN/completions_${CHUNK}.jsonl"
if [[ -f "$O.summary.json" ]]; then
  echo "[skip] $CHUNK already complete"
  exit 0
fi
python jobs/batch_generate.py \
    --model-dir "$D/models/Gemma-4-31B-it" --tp 4 --max-model-len 8192 \
    --gpu-mem-util 0.92 --temperature 0.0 \
    --prompts "$P" --out "$O"

echo "[s2confirm-gen] DONE chunk=$CHUNK $(date -u +%FT%TZ)"
