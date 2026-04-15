"""Global SC1 configuration. Paths resolve to repository root."""

from __future__ import annotations

import os
from pathlib import Path

import torch

# Repository root = parent of `src/`
_ROOT = Path(__file__).resolve().parents[2]


def resolve_torch_device(requested: str) -> str:
    """Map ``auto`` / unavailable CUDA to a usable device (cuda → mps → cpu)."""
    r = (requested or "auto").strip()
    rl = r.lower()
    if rl == "auto":
        if torch.cuda.is_available():
            return "cuda:0"
        if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
            return "mps"
        return "cpu"
    if rl.startswith("cuda") and not torch.cuda.is_available():
        if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
            return "mps"
        return "cpu"
    if rl == "mps" and not (
        getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available()
    ):
        return "cpu"
    return r


# ── Models ─────────────────────────────────────────────────
# hf: local Transformers; openai: Chat Completions API (set SC1_OPENAI_API_KEY).
LLM_BACKEND = os.environ.get("SC1_LLM_BACKEND", "hf").strip().lower()
LLM_MODEL_NAME = os.environ.get("SC1_LLM_MODEL", "meta-llama/Meta-Llama-3-8B-Instruct")
LLM_DEVICE = resolve_torch_device(os.environ.get("SC1_LLM_DEVICE", "auto"))
LLM_TEMPERATURE = float(os.environ.get("SC1_LLM_TEMPERATURE", "0.8"))
LLM_MAX_NEW_TOKENS = int(os.environ.get("SC1_LLM_MAX_NEW", "256"))
LLM_N_SAMPLES = int(os.environ.get("SC1_LLM_N_SAMPLES", "3"))
# Seed pool — extended so any N_SAMPLES ≤ 8 works without code changes.
_SEED_POOL = [42, 1337, 7, 99, 2024, 314, 777, 12345]
if LLM_N_SAMPLES < 1 or LLM_N_SAMPLES > len(_SEED_POOL):
    raise ValueError(f"SC1_LLM_N_SAMPLES must be between 1 and {len(_SEED_POOL)}, got {LLM_N_SAMPLES}")
LLM_SEEDS = _SEED_POOL[:LLM_N_SAMPLES]

# device_map mode for LLM: "none" = single-card .to(device); "auto" = Accelerate multi-GPU
LLM_DEVICE_MAP = os.environ.get("SC1_LLM_DEVICE_MAP", "none").strip().lower()

# OpenAI-compatible HTTP API (used when LLM_BACKEND == openai)
OPENAI_BASE_URL = os.environ.get("SC1_OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
OPENAI_API_KEY = os.environ.get("SC1_OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY", "")

NLI_MODEL_NAME = os.environ.get("SC1_NLI_MODEL", "cross-encoder/nli-deberta-v3-large")
NLI_ENTAILMENT_THRESHOLD = float(os.environ.get("SC1_NLI_THRESHOLD", "0.7"))
NLI_DEVICE = resolve_torch_device(os.environ.get("SC1_NLI_DEVICE", "auto"))

EMBED_MODEL_NAME = os.environ.get("SC1_EMBED_MODEL", "princeton-nlp/sup-simcse-roberta-base")
EMBED_DEVICE = resolve_torch_device(os.environ.get("SC1_EMBED_DEVICE", "auto"))

# ── Paths ─────────────────────────────────────────────────
CONV_DIR = Path(
    os.environ.get("SC1_CONV_DIR", str(_ROOT / "data" / "sc1" / "conversations"))
).resolve()
RESULTS_DIR = Path(os.environ.get("SC1_RESULTS_DIR", str(_ROOT / "result" / "sc1")))

# SC2 target (seconds per turn, informational)
MAX_SECONDS_PER_TURN = float(os.environ.get("SC1_MAX_SEC_PER_TURN", "15.0"))
