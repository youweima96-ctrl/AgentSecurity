"""Semantic entropy via NLI clustering (Kuhn-style pairwise equivalence)."""

from __future__ import annotations

import math
from itertools import combinations
from typing import Dict, List

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from sc1.config import NLI_DEVICE, NLI_ENTAILMENT_THRESHOLD, NLI_MODEL_NAME


class EntropyCalculator:
    def __init__(self) -> None:
        self.tokenizer = AutoTokenizer.from_pretrained(NLI_MODEL_NAME)
        self.model = AutoModelForSequenceClassification.from_pretrained(NLI_MODEL_NAME).to(NLI_DEVICE)
        self.model.eval()
        id2label: Dict[int, str] = {int(k): str(v).lower() for k, v in self.model.config.id2label.items()}
        self._entailment_id = next((i for i, lab in id2label.items() if "entail" in lab), 1)

    def _get_entailment_prob(self, premise: str, hypothesis: str) -> float:
        inputs = self.tokenizer(
            premise,
            hypothesis,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        ).to(NLI_DEVICE)
        with torch.no_grad():
            logits = self.model(**inputs).logits
            probs = torch.softmax(logits, dim=-1).squeeze(0)
        return float(probs[self._entailment_id].item())

    def _are_semantically_equivalent(self, s1: str, s2: str) -> bool:
        p_fwd = self._get_entailment_prob(s1, s2)
        p_bwd = self._get_entailment_prob(s2, s1)
        return p_fwd > NLI_ENTAILMENT_THRESHOLD and p_bwd > NLI_ENTAILMENT_THRESHOLD

    def _cluster_samples(self, samples: List[str]) -> List[int]:
        n = len(samples)
        parent = list(range(n))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: int, y: int) -> None:
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry

        for i, j in combinations(range(n), 2):
            if self._are_semantically_equivalent(samples[i], samples[j]):
                union(i, j)

        roots = [find(i) for i in range(n)]
        unique: Dict[int, int] = {}
        out: List[int] = []
        nxt = 0
        for r in roots:
            if r not in unique:
                unique[r] = nxt
                nxt += 1
            out.append(unique[r])
        return out

    def compute_entropy(self, samples: List[str]) -> float:
        cleaned = [s.strip() for s in samples if s.strip()]
        if len(cleaned) <= 1:
            return 0.0
        cluster_ids = self._cluster_samples(cleaned)
        counts: Dict[int, int] = {}
        for cid in cluster_ids:
            counts[cid] = counts.get(cid, 0) + 1
        n = len(cluster_ids)
        entropy = 0.0
        for c in counts.values():
            p = c / n
            if p > 0:
                entropy -= p * math.log(p)
        return round(entropy, 6)
