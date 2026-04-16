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

    def _encode_many(self, texts: List[str]) -> torch.Tensor:
        if not texts:
            return torch.empty((0, 1), device=EMBED_DEVICE)
        inputs = self.tokenizer(
            texts,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        ).to(EMBED_DEVICE)
        with torch.no_grad():
            outputs = self.model(**inputs)
            emb = outputs.last_hidden_state[:, 0, :]
            emb = F.normalize(emb, p=2, dim=1)
        return emb

    def compute_drift_sequence(self, responses: List[str]) -> List[Optional[float]]:
        safe = [r if r.strip() else " " for r in responses]
        embeddings = self._encode_many(safe)
        drift_values: List[Optional[float]] = [None]
        for i in range(1, int(embeddings.shape[0])):
            cos_sim = float(torch.dot(embeddings[i], embeddings[i - 1]).item())
            drift = 1.0 - cos_sim
            drift = max(0.0, min(1.0, drift))
            drift_values.append(round(drift, 6))
        return drift_values

    def compute_sample_dispersion(self, samples: List[str]) -> float:
        """Mean pairwise cosine distance within samples, normalized to [0, 1]."""
        safe = [s.strip() for s in samples if s.strip()]
        if len(safe) <= 1:
            return 0.0
        emb = self._encode_many(safe)
        sim = torch.matmul(emb, emb.T)
        n = int(sim.shape[0])
        if n <= 1:
            return 0.0
        upper = torch.triu_indices(n, n, offset=1)
        pair_sims = sim[upper[0], upper[1]]
        pair_dists = 1.0 - pair_sims
        val = float(torch.clamp(pair_dists.mean(), min=0.0, max=1.0).item())
        return round(val, 6)
