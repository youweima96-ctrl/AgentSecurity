"""Sample N LLM responses per turn; primary = samples[0] for history."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Tuple

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from sc1.config import (
    LLM_DEVICE,
    LLM_MAX_NEW_TOKENS,
    LLM_MODEL_NAME,
    LLM_N_SAMPLES,
    LLM_SEEDS,
    LLM_TEMPERATURE,
)


class LLMSampler:
    def __init__(self) -> None:
        self.tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL_NAME, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            LLM_MODEL_NAME,
            torch_dtype=torch.float16,
            device_map=None,
            trust_remote_code=True,
        )
        self.model.to(LLM_DEVICE)
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
        inputs = self.tokenizer(prompt, return_tensors="pt").to(LLM_DEVICE)
        samples: List[str] = []
        t0 = time.time()
        input_len = inputs["input_ids"].shape[1]

        for seed in LLM_SEEDS[:LLM_N_SAMPLES]:
            torch.manual_seed(seed)
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


def _manual_llama3_chat(messages: List[Dict[str, str]]) -> str:
    """Fallback if apply_chat_template is unavailable."""
    prompt = "<|begin_of_text|>"
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        prompt += f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>"
    prompt += "<|start_header_id|>assistant<|end_header_id|>\n\n"
    return prompt
