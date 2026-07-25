#!/bin/bash
#SBATCH --job-name=dop-exp3
#SBATCH --partition=boost_usr_prod
#SBATCH --account=AIFAC_P02_548
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=32
#SBATCH --time=04:00:00
#SBATCH --output=/leonardo_work/AIFAC_P02_548/DOPPLER/logs/%x-%j.out
#
# selection ladder: expected information gain on TIPI targets vs self-uncertainty
# Projected 2.817 node-hours (per-job cap 4.0).
set -euo pipefail
D=/leonardo_work/AIFAC_P02_548/DOPPLER
cd "$D"
source jobs/site_env.sh
source "$D/.venv-vllm-new/bin/activate"
echo "[overnight_exp3] node=$(hostname) start=$(date -u +%FT%TZ)"
python jobs/eig_node_driver.py \
    --pack "/leonardo_work/AIFAC_P02_548/DOPPLER/runs/overnight/overnight_exp3/pack_node_exp3.json" \
    --outdir "/leonardo_work/AIFAC_P02_548/DOPPLER/runs/overnight/overnight_exp3" \
    --model-dir "/leonardo_work/AIFAC_P02_548/DOPPLER/models/Gemma-4-31B-it" --tp 4 --max-model-len 3072 \
    --gpu-mem-util 0.92 --temperature 0.0 \
    --max-reveals 20 \
    --checkpoints 1,2,3,4,5,8,12,16,20 \
    --top-n 5 \
    --hypotheticals 1,3,5 \
    --tiebreak-seed 71 \
    --smoke-n 200 --min-parse-rate 0.95 --fallback-persons 40

echo "[overnight_exp3] DONE $(date -u +%FT%TZ)"
