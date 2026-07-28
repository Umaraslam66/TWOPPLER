#!/bin/bash
#SBATCH --job-name=dop-h6d3-gen
#SBATCH --partition=boost_usr_prod
#SBATCH --qos=boost_qos_dbg
#SBATCH --account=AIFAC_P02_548
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=32
#SBATCH --time=00:25:00
#SBATCH --output=/leonardo_work/AIFAC_P02_548/DOPPLER/logs/%x-%j.out
#
# EXPLORATORY H6 D_min = 3 generations, Gemma-4-31B-it (primary model only).
# Usage: sbatch jobs/h6_d3_gen.sbatch chunk_01
# Generation config byte-identical to the H6 run (and so to the confirmatory
# H1 run): temperature 0.0, seed 0, tp 4, max-model-len 8192,
# max_output_tokens 256 carried per prompt row. Only the job name and the run
# directory differ from jobs/h6_gen.sbatch, so sacct bills this arm separately.
# 182 prompts is ~15s of generation behind a ~7 min engine init -- what this
# QOS is for. Cap: 0.2 additional node-hours for this exploratory arm.
set -euo pipefail
CHUNK="${1:?usage: sbatch h6_d3_gen.sbatch chunk_NN}"
D=/leonardo_work/AIFAC_P02_548/DOPPLER
cd "$D"
source jobs/site_env.sh
source "$D/.venv-vllm-new/bin/activate"
RUN="$D/runs/stage2_confirm_h6d3_gen"
mkdir -p "$RUN"
echo "[h6d3-gen] chunk=$CHUNK node=$(hostname) start=$(date -u +%FT%TZ)"

P="$RUN/${CHUNK}.prompts.jsonl"
O="$RUN/completions_${CHUNK}.jsonl"
if [[ -f "$O.summary.json" ]]; then
  echo "[skip] $CHUNK already complete"
  exit 0
fi
python jobs/batch_generate.py \
    --model-dir "$D/models/Gemma-4-31B-it" --tp 4 --max-model-len 8192 \
    --gpu-mem-util 0.92 --temperature 0.0 --seed 0 \
    --prompts "$P" --out "$O"

echo "[h6d3-gen] DONE chunk=$CHUNK $(date -u +%FT%TZ)"
