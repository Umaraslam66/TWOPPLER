#!/bin/bash
#SBATCH --job-name=dop-h6-classify
#SBATCH --partition=boost_usr_prod
#SBATCH --qos=boost_qos_dbg
#SBATCH --account=AIFAC_P02_548
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=4
#SBATCH --cpus-per-task=32
#SBATCH --time=00:20:00
#SBATCH --output=/leonardo_work/AIFAC_P02_548/DOPPLER/logs/%x-%j.out
#
# H6 follow-up classifier over the 89 CONFIRMATORY survivors' GROUNDING turns.
# Gemma-4-31B-it under the frozen RUBRIC_V1 (Amendment 2 B2.1), same decode
# settings as the dev classify pass: temperature 0.0, seed 0, tp 4.
# Usage: sbatch jobs/h6_classify_gen.sbatch pass1
# QOS: boost_qos_dbg (priority 80, MaxWall 00:30:00, MaxJobsPU 2). This pass is
# a ~6-minute inference run -- engine init plus about two minutes of generation
# for 5,287 short prompts -- so it is inside the debug QOS by design, not
# squeezed into it. Under the normal QOS (priority 40) it sat behind ~4,635
# pending jobs with no estimated start.
# Passes 2 and 3 are the B4.3 retries; they carry only the turns that failed
# to parse, and use identical settings.
# Cap: 3 node-hours for the whole closeout GPU phase, H6 generation included.
set -euo pipefail
PASS="${1:?usage: sbatch h6_classify_gen.sbatch passN}"
D=/leonardo_work/AIFAC_P02_548/DOPPLER
cd "$D"
source jobs/site_env.sh
source "$D/.venv-vllm-new/bin/activate"
RUN="$D/runs/stage2_confirm_h6"
mkdir -p "$RUN"
echo "[h6-classify] pass=$PASS node=$(hostname) start=$(date -u +%FT%TZ)"

P="$RUN/${PASS}.prompts.jsonl"
O="$RUN/completions_${PASS}.jsonl"
if [[ -f "$O.summary.json" ]]; then
  echo "[skip] $PASS already complete"
  exit 0
fi
python jobs/batch_generate.py \
    --model-dir "$D/models/Gemma-4-31B-it" --tp 4 --max-model-len 8192 \
    --gpu-mem-util 0.92 --temperature 0.0 --seed 0 \
    --prompts "$P" --out "$O"

echo "[h6-classify] DONE pass=$PASS $(date -u +%FT%TZ)"
