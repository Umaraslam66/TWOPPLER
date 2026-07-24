#!/bin/bash
#SBATCH --job-name=dop-exp1c
#SBATCH --partition=boost_usr_prod
#SBATCH --account=AIFAC_P02_548
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=32
#SBATCH --time=01:30:00
#SBATCH --output=/leonardo_work/AIFAC_P02_548/DOPPLER/logs/%x-%j.out
#
# adaptive, entropy scorer, random tie-break, 0.05 probability grid, k to 20
# Projected 0.656 node-hours (per-job cap 4.0).
set -euo pipefail
D=/leonardo_work/AIFAC_P02_548/DOPPLER
cd "$D"
source jobs/site_env.sh
source "$D/.venv-vllm-new/bin/activate"
echo "[overnight_exp1c] node=$(hostname) start=$(date -u +%FT%TZ)"
python jobs/adaptive_node_driver.py \
    --pack "$D/runs/adaptive_train/pack_node.json" \
    --outdir "/leonardo_work/AIFAC_P02_548/DOPPLER/runs/overnight/overnight_exp1c" \
    --model-dir "/leonardo_work/AIFAC_P02_548/DOPPLER/models/Gemma-4-31B-it" --tp 4 --max-model-len 2048 \
    --gpu-mem-util 0.92 --temperature 0.0 \
    --scorer entropy --tiebreak random \
    --tiebreak-seed 71 \
    --interest-grid fine \
    --max-reveals 20 \
    --checkpoints 1,2,3,4,5,8,12,16,20

echo "[overnight_exp1c] DONE $(date -u +%FT%TZ)"
