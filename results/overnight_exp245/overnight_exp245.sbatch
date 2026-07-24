#!/bin/bash
#SBATCH --job-name=dop-exp245
#SBATCH --partition=boost_usr_prod
#SBATCH --account=AIFAC_P02_548
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=32
#SBATCH --time=01:00:00
#SBATCH --output=/leonardo_work/AIFAC_P02_548/DOPPLER/logs/%x-%j.out
#
# frozen derivation order, extended random checkpoints, nearest-neighbour imposter
# Projected 0.300 node-hours (per-job cap 4.0).
set -euo pipefail
D=/leonardo_work/AIFAC_P02_548/DOPPLER
cd "$D"
source jobs/site_env.sh
source "$D/.venv-vllm-new/bin/activate"
echo "[overnight_exp245] node=$(hostname) start=$(date -u +%FT%TZ)"
python jobs/batch_generate.py \
    --model-dir "/leonardo_work/AIFAC_P02_548/DOPPLER/models/Gemma-4-31B-it" --tp 4 --max-model-len 2048 \
    --gpu-mem-util 0.92 --temperature 0.0 \
    --prompts "/leonardo_work/AIFAC_P02_548/DOPPLER/runs/overnight/overnight_exp245/prompts_static.jsonl" \
    --out "/leonardo_work/AIFAC_P02_548/DOPPLER/runs/overnight/overnight_exp245/completions_static.jsonl"

echo "[overnight_exp245] DONE $(date -u +%FT%TZ)"
