"""Sample N LLM responses per turn; primary = samples[0] for history."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Tuple

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from sc1.config import (
    LLM_BACKEND,
    LLM_DEVICE,
    LLM_DEVICE_MAP,
    LLM_MAX_NEW_TOKENS,
    LLM_MODEL_NAME,
    LLM_N_SAMPLES,
    LLM_SEEDS,
    LLM_TEMPERATURE,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
)


def _llm_weight_dtype() -> torch.dtype:
    if LLM_DEVICE.startswith("cuda") or LLM_DEVICE == "mps":
        return torch.float16
    return torch.float32


class _HuggingFaceLLMSampler:
    def __init__(self) -> None:
        self.tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL_NAME, trust_remote_code=True)
        dtype = _llm_weight_dtype()

        use_device_map = LLM_DEVICE_MAP == "auto"
        self.model = AutoModelForCausalLM.from_pretrained(
            LLM_MODEL_NAME,
            dtype=dtype,
            device_map="auto" if use_device_map else None,
            trust_remote_code=True,
        )
        if not use_device_map:
            self.model.to(LLM_DEVICE)
        self._device = None if use_device_map else LLM_DEVICE
        self.model.eval()
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id

    def _build_prompt(self, history: List[Dict[str, str]], user_message: str) -> str:
        messages = list(history) + [{"role": "user", "content": user_message}]
        if hasattr(self.tokenizer, "apply_chat_template"):
            return self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        return _manual_llama3_chat(messages)

    def sample_n(
        self,
        history: List[Dict[str, str]],
        user_message: str,
    ) -> Tuple[List[str], float]:
        prompt = self._build_prompt(history, user_message)
        target = self._device or next(self.model.parameters()).device
        inputs = self.tokenizer(prompt, return_tensors="pt").to(target)
        samples: List[str] = []
        t0 = time.time()
        input_len = inputs["input_ids"].shape[1]
        seed_offset = int(os.environ.get("SC1_SEED_OFFSET", "0") or 0)

        for idx, seed in enumerate(LLM_SEEDS[:LLM_N_SAMPLES]):
            actual_seed = int(seed_offset + seed + idx * 100003)
            torch.manual_seed(actual_seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(actual_seed)
            with torch.no_grad():
                output_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=LLM_MAX_NEW_TOKENS,
                    temperature=LLM_TEMPERATURE,
                    do_sample=True,
                    pad_token_id=self.tokenizer.pad_token_id,
                )
            new_tokens = output_ids[0, input_len:]
            response = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
            samples.append(response.strip())

        return samples, time.time() - t0

    def run_conversation(self, turns: List[Dict[str, Any]]) -> Dict[str, Any]:
        history: List[Dict[str, str]] = []
        results: List[Dict[str, Any]] = []

        for turn_data in turns:
            turn_idx = int(turn_data["turn"])
            user_msg = str(turn_data["user"])
            samples, elapsed = self.sample_n(history, user_msg)
            primary = samples[0]
            results.append(
                {
                    "turn": turn_idx,
                    "user": user_msg,
                    "primary_response": primary,
                    "samples": samples,
                    "sampling_time_sec": round(elapsed, 2),
                }
            )
            history.append({"role": "user", "content": user_msg})
            history.append({"role": "assistant", "content": primary})

        return {"turns": results}


class _OpenAIHttpLLMSampler:
    """OpenAI-compatible ``/v1/chat/completions`` (no extra Python deps)."""

    def __init__(self) -> None:
        if not OPENAI_API_KEY:
            raise ValueError(
                "SC1_LLM_BACKEND=openai requires SC1_OPENAI_API_KEY or OPENAI_API_KEY in the environment."
            )
        self._url = f"{OPENAI_BASE_URL}/chat/completions"
        self._model = LLM_MODEL_NAME

    def _complete(self, messages: List[Dict[str, str]], seed: int) -> str:
        body: Dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": LLM_TEMPERATURE,
            "max_tokens": LLM_MAX_NEW_TOKENS,
        }
        # Optional: some providers accept ``seed`` for reproducibility (omit if they 400).
        if os.environ.get("SC1_OPENAI_SEND_SEED", "").strip() in ("1", "true", "yes"):
            body["seed"] = int(seed)
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            self._url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI HTTP {e.code}: {detail}") from e

        try:
            return str(payload["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"Unexpected chat/completions response: {payload!r}") from e

    def sample_n(
        self,
        history: List[Dict[str, str]],
        user_message: str,
    ) -> Tuple[List[str], float]:
        messages = list(history) + [{"role": "user", "content": user_message}]
        samples: List[str] = []
        t0 = time.time()
        seed_offset = int(os.environ.get("SC1_SEED_OFFSET", "0") or 0)
        for idx, seed in enumerate(LLM_SEEDS[:LLM_N_SAMPLES]):
            actual_seed = int(seed_offset + seed + idx * 100003)
            samples.append(self._complete(messages, actual_seed))
        return samples, time.time() - t0

    def run_conversation(self, turns: List[Dict[str, Any]]) -> Dict[str, Any]:
        history: List[Dict[str, str]] = []
        results: List[Dict[str, Any]] = []

        for turn_data in turns:
            turn_idx = int(turn_data["turn"])
            user_msg = str(turn_data["user"])
            samples, elapsed = self.sample_n(history, user_msg)
            primary = samples[0]
            results.append(
                {
                    "turn": turn_idx,
                    "user": user_msg,
                    "primary_response": primary,
                    "samples": samples,
                    "sampling_time_sec": round(elapsed, 2),
                }
            )
            history.append({"role": "user", "content": user_msg})
            history.append({"role": "assistant", "content": primary})

        return {"turns": results}


class LLMSampler:
    """Dispatches to HuggingFace local weights or OpenAI-compatible HTTP API."""

    def __init__(self) -> None:
        if LLM_BACKEND in ("openai", "api", "http"):
            print("Using OpenAI-compatible HTTP API for LLM sampling...")
            self._impl: Any = _OpenAIHttpLLMSampler()
        else:
            print("Loading local HuggingFace LLM for sampling...")
            self._impl = _HuggingFaceLLMSampler()

    def run_conversation(self, turns: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self._impl.run_conversation(turns)


def _manual_llama3_chat(messages: List[Dict[str, str]]) -> str:
    """Fallback if apply_chat_template is unavailable (matches execution brief tokens)."""
    prompt = "<|begin_of_text|>"
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        prompt += f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>"
    prompt += "<|start_header_id|>assistant<|end_header_id|>\n\n"
    return prompt
