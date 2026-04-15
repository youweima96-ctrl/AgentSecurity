"""Embedding drift D(t) = 1 - cosine(primary_t, primary_{t-1}) with SimCSE."""

from __future__ import annotations

from typing import List, Optional

import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

from sc1.config import EMBED_DEVICE, EMBED_MODEL_NAME


class DriftCalculator:
    def __init__(self) -> None:
        self.tokenizer = AutoTokenizer.from_pretrained(EMBED_MODEL_NAME)
        self.model = AutoModel.from_pretrained(EMBED_MODEL_NAME).to(EMBED_DEVICE)
        self.model.eval()

    def _encode(self, text: str) -> torch.Tensor:
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        ).to(EMBED_DEVICE)
        with torch.no_grad():
            outputs = self.model(**inputs)
            emb = outputs.last_hidden_state[:, 0, :]
            emb = F.normalize(emb, p=2, dim=1)
        return emb.squeeze(0)

    def compute_drift_sequence(self, responses: List[str]) -> List[Optional[float]]:
        safe = [r if r.strip() else " " for r in responses]
        embeddings = [self._encode(r) for r in safe]
        drift_values: List[Optional[float]] = [None]
        for i in range(1, len(embeddings)):
            cos_sim = float(torch.dot(embeddings[i], embeddings[i - 1]).item())
            drift = 1.0 - cos_sim
            drift = max(0.0, min(1.0, drift))
            drift_values.append(round(drift, 6))
        return drift_values
