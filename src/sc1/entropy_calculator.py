"""Semantic uncertainty metrics via NLI pairwise equivalence."""

from __future__ import annotations

import math
from itertools import combinations
from typing import Any, Dict, List

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

    def _are_semantically_equivalent(self, s1: str, s2: str, threshold: float) -> bool:
        p_fwd = self._get_entailment_prob(s1, s2)
        p_bwd = self._get_entailment_prob(s2, s1)
        return p_fwd > threshold and p_bwd > threshold

    def _cluster_samples(self, samples: List[str], threshold: float) -> List[int]:
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
            if self._are_semantically_equivalent(samples[i], samples[j], threshold):
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

    @staticmethod
    def _entropy_from_cluster_ids(cluster_ids: List[int]) -> float:
        if len(cluster_ids) <= 1:
            return 0.0
        counts: Dict[int, int] = {}
        for cid in cluster_ids:
            counts[cid] = counts.get(cid, 0) + 1
        n = len(cluster_ids)
        entropy = 0.0
        for c in counts.values():
            p = c / n
            if p > 0:
                entropy -= p * math.log(p)
        return float(entropy)

    @staticmethod
    def _build_edges(
        n: int,
        pair_stats: List[Dict[str, Any]],
        threshold: float,
    ) -> List[int]:
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

        for item in pair_stats:
            if item["min_bidirectional"] > threshold:
                union(int(item["i"]), int(item["j"]))
        return [find(i) for i in range(n)]

    def _pairwise_stats(self, samples: List[str]) -> List[Dict[str, Any]]:
        stats: List[Dict[str, Any]] = []
        for i, j in combinations(range(len(samples)), 2):
            p_fwd = self._get_entailment_prob(samples[i], samples[j])
            p_bwd = self._get_entailment_prob(samples[j], samples[i])
            stats.append(
                {
                    "i": i,
                    "j": j,
                    "p_fwd": p_fwd,
                    "p_bwd": p_bwd,
                    "min_bidirectional": min(p_fwd, p_bwd),
                }
            )
        return stats

    @staticmethod
    def _cluster_ids_from_roots(roots: List[int]) -> List[int]:
        unique: Dict[int, int] = {}
        out: List[int] = []
        nxt = 0
        for r in roots:
            if r not in unique:
                unique[r] = nxt
                nxt += 1
            out.append(unique[r])
        return out

    def _metrics_at_threshold(
        self,
        n_samples: int,
        pair_stats: List[Dict[str, Any]],
        threshold: float,
    ) -> Dict[str, Any]:
        roots = self._build_edges(n_samples, pair_stats, threshold=threshold)
        cluster_ids = self._cluster_ids_from_roots(roots)
        entropy = self._entropy_from_cluster_ids(cluster_ids)
        max_entropy = math.log(n_samples) if n_samples > 1 else 1.0
        entropy_norm = (entropy / max_entropy) if max_entropy > 0 else 0.0
        n_pairs = len(pair_stats)
        n_disagree = sum(1 for p in pair_stats if p["min_bidirectional"] <= threshold)
        disagreement = (n_disagree / n_pairs) if n_pairs else 0.0
        return {
            "threshold": round(float(threshold), 4),
            "entropy": round(entropy, 6),
            "entropy_normalized": round(float(entropy_norm), 6),
            "cluster_count": len(set(cluster_ids)),
            "cluster_ids": cluster_ids,
            "disagreement_ratio": round(float(disagreement), 6),
        }

    def compute_turn_metrics(
        self,
        samples: List[str],
        threshold: float,
        sweep_thresholds: List[float] | None = None,
    ) -> Dict[str, Any]:
        cleaned = [s.strip() for s in samples if s.strip()]
        if len(cleaned) <= 1:
            return {
                "n_samples": len(cleaned),
                "threshold_main": threshold,
                "entropy": 0.0,
                "entropy_normalized": 0.0,
                "cluster_count": 1 if cleaned else 0,
                "cluster_ids": [0] if cleaned else [],
                "disagreement_ratio": 0.0,
                "threshold_sweep": [],
                "pairwise_stats": [],
            }

        pair_stats = self._pairwise_stats(cleaned)
        main = self._metrics_at_threshold(
            n_samples=len(cleaned),
            pair_stats=pair_stats,
            threshold=threshold,
        )

        sweep: List[Dict[str, Any]] = []
        for t in (sweep_thresholds or []):
            sweep.append(
                self._metrics_at_threshold(
                    n_samples=len(cleaned),
                    pair_stats=pair_stats,
                    threshold=float(t),
                )
            )

        return {
            "n_samples": len(cleaned),
            "threshold_main": round(float(threshold), 4),
            "entropy": main["entropy"],
            "entropy_normalized": main["entropy_normalized"],
            "cluster_count": main["cluster_count"],
            "cluster_ids": main["cluster_ids"],
            "disagreement_ratio": main["disagreement_ratio"],
            "threshold_sweep": sweep,
            "pairwise_stats": pair_stats,
        }

    def compute_entropy(self, samples: List[str]) -> float:
        # Backward-compatible interface.
        m = self.compute_turn_metrics(samples, threshold=NLI_ENTAILMENT_THRESHOLD)
        return float(m["entropy"])
