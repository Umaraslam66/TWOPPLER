#!/bin/bash
#SBATCH --job-name=dop-confirm-ad1
#SBATCH --partition=boost_usr_prod
#SBATCH --account=AIFAC_P02_548
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=32
#SBATCH --time=03:30:00
#SBATCH --output=/leonardo_work/AIFAC_P02_548/DOPPLER/logs/%x-%j.out
#
# Stage 1E CONFIRM run -- adaptive arm, shard 1 of 4 (EV-variance scorer)
# Frozen by PREREGISTRATION_AMENDMENT_1_ADDENDUM_A.md section A.
# Production queue (boost_usr_prod), NOT the debug QOS.
# Projected 1.022 node-hours. Resumable: resubmitting continues.
set -euo pipefail
D=/leonardo_work/AIFAC_P02_548/DOPPLER
cd "$D"
source jobs/site_env.sh
source "$D/.venv-vllm-new/bin/activate"
mkdir -p "/leonardo_work/AIFAC_P02_548/DOPPLER/runs/stage1e_confirm/adaptive_s1"
echo "[confirm_adaptive_s1] node=$(hostname) start=$(date -u +%FT%TZ)"
python jobs/adaptive_node_driver.py \
    --pack "/leonardo_work/AIFAC_P02_548/DOPPLER/runs/stage1e_confirm/pack_node_s1.json" \
    --outdir "/leonardo_work/AIFAC_P02_548/DOPPLER/runs/stage1e_confirm/adaptive_s1" \
    --model-dir "/leonardo_work/AIFAC_P02_548/DOPPLER/models/Gemma-4-31B-it" --tp 4 --max-model-len 2048 \
    --gpu-mem-util 0.92 --temperature 0.0 \
    --scorer ev_variance --tiebreak random \
    --tiebreak-seed 71 \
    --interest-grid standard \
    --max-reveals 20 \
    --checkpoints 1,2,4,8,12,16,20

echo "[confirm_adaptive_s1] DONE $(date -u +%FT%TZ)"
