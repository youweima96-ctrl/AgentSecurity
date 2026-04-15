"""Global SC1 configuration. Paths resolve to repository root."""

from __future__ import annotations

import os
from pathlib import Path

# Repository root = parent of `src/`
_ROOT = Path(__file__).resolve().parents[2]

# ── Models ─────────────────────────────────────────────────
LLM_MODEL_NAME = os.environ.get("SC1_LLM_MODEL", "meta-llama/Meta-Llama-3-8B-Instruct")
LLM_DEVICE = os.environ.get("SC1_LLM_DEVICE", "cuda:0")
LLM_TEMPERATURE = float(os.environ.get("SC1_LLM_TEMPERATURE", "0.8"))
LLM_MAX_NEW_TOKENS = int(os.environ.get("SC1_LLM_MAX_NEW", "256"))
LLM_N_SAMPLES = int(os.environ.get("SC1_LLM_N_SAMPLES", "3"))
LLM_SEEDS = [42, 1337, 7]
if len(LLM_SEEDS) != LLM_N_SAMPLES:
    raise ValueError("LLM_SEEDS length must equal LLM_N_SAMPLES")

NLI_MODEL_NAME = os.environ.get("SC1_NLI_MODEL", "cross-encoder/nli-deberta-v3-large")
NLI_ENTAILMENT_THRESHOLD = float(os.environ.get("SC1_NLI_THRESHOLD", "0.7"))
NLI_DEVICE = os.environ.get("SC1_NLI_DEVICE", "cuda:0")

EMBED_MODEL_NAME = os.environ.get("SC1_EMBED_MODEL", "princeton-nlp/sup-simcse-roberta-base")
EMBED_DEVICE = os.environ.get("SC1_EMBED_DEVICE", "cuda:0")

# ── Paths ─────────────────────────────────────────────────
CONV_DIR = Path(
    os.environ.get("SC1_CONV_DIR", str(_ROOT / "data" / "sc1" / "conversations"))
).resolve()
RESULTS_DIR = Path(os.environ.get("SC1_RESULTS_DIR", str(_ROOT / "result" / "sc1")))

# SC2 target (seconds per turn, informational)
MAX_SECONDS_PER_TURN = float(os.environ.get("SC1_MAX_SEC_PER_TURN", "15.0"))
