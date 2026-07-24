# Why MoE failed on Leonardo — post-mortem (read-only)

Investigated 2026-07-24. All evidence is on Leonardo under
`/leonardo_work/AIFAC_P02_548/mirror-sim/` (the `mirror-sim` project). This is the
only MoE attempt in the 548 space; no Mixtral/DeepSeek/OLMoE anywhere.

## What was tried
- Model: **Qwen3-30B-A3B-Instruct-2507** (MoE: 30B total, 3B active), served with
  **vLLM 0.11.0** (pip wheel), **torch 2.8.0** (bundles CUDA 12.8 libs),
  **triton 3.4.0**, **transformers 5.14.1**, **nccl 2.27.3**. TP=4 on one 4×A100 node.
- Env was a hand-built pip venv (`.venv-vllm`) plus a forced **CUDA 13.2 userspace
  compat lib** injected via `LD_LIBRARY_PATH` (see `scripts/gen_job.sh` and
  `tools/cuda-compat-13/`), because the stock driver is older than the wheel's CUDA.

## Exact error evidence
1. First stumble (old tokenizer, a different venv): `logs/qwen-smoke-50089114.out:31`
   `AttributeError: Qwen2Tokenizer has no attribute all_special_tokens_extended`.
   Fixed by moving to `.venv-vllm` (transformers 5.14.1). Not the real blocker.
2. Real blocker: `logs/qwen-smoke-50090042.out:256-260` and `:1240`. Model loaded,
   torch.compile ran, then the first forward pass hit the expert-routing kernel:
   `torch.ops._moe_C.topk_softmax(...)` →
   `AttributeError: '_OpNamespace' '_moe_C' object has no attribute 'topk_softmax'`
   → `RuntimeError: Worker failed ... topk_softmax`. Engine died.
3. Contrast — **dense works on the same stack**: dense **Qwen3-32B** smoke generated
   tokens fine (`logs/qwen-smoke32-50090821.out:160`) and a full 227-prompt gen run
   succeeded at ~750–1240 tok/s (`logs/qwen-dyn-50093906.out:156-159`, outputs in
   `results/task2/*.csv`). So CUDA/driver/A100s are fundamentally OK.

## Root cause verdict (confidence: HIGH on what, MEDIUM on why)
vLLM's MoE custom-op library `_moe_C` did not register its ops in this process. The
file `.venv-vllm/.../vllm/_moe_C.abi3.so` **exists** (141 MB) but its `topk_softmax`
op is absent at runtime — i.e. the prebuilt MoE extension silently failed to load
under this improvised CUDA-13.2-compat-on-old-driver setup, while the main `_C`
extension (used by dense models) loaded fine. This is a **software-stack / packaging
problem**, not cluster hardware and not a batch-script typo. Dense never touches
`_moe_C`, which is exactly why only MoE broke. (Corroborating: bash history shows the
user's other project ran vLLM via a Singularity container with `enforce_eager=1` and
`VLLM_USE_STANDALONE_COMPILE=0` — the fragile raw-pip+compat-shim path is what broke
here.)

## Cheaply fixable?
Plausibly (looks like an op-loading/compat mismatch, not a hard limit) — but not
guaranteed, and dense-first is already decided, so no action recommended.
