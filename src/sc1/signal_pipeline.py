"""End-to-end: sample → H(t) → D(t)."""

from __future__ import annotations

import time
from typing import Any, Dict, List

from sc1.drift_calculator import DriftCalculator
from sc1.entropy_calculator import EntropyCalculator
from sc1.llm_sampler import LLMSampler


def _h_split_diff_second_minus_first(h_values: List[float]) -> float:
    """mean(H, t=6–10) − mean(H, t=1–5), 0-indexed halves; SC1 plan item 5.1."""
    if len(h_values) < 10:
        return 0.0
    first = sum(h_values[:5]) / 5.0
    second = sum(h_values[5:10]) / 5.0
    return round(second - first, 6)


class SignalPipeline:
    def __init__(self) -> None:
        print("Loading LLM sampler...")
        self.sampler = LLMSampler()
        print("Loading entropy calculator (NLI)...")
        self.entropy_calc = EntropyCalculator()
        print("Loading drift calculator (SimCSE)...")
        self.drift_calc = DriftCalculator()
        print("All models loaded.")

    def run(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        case_id = str(conversation["case_id"])
        turns = conversation["turns"]
        print(f"\n=== Processing {case_id} ===")

        sampling_result = self.sampler.run_conversation(turns)
        primary_responses = [t["primary_response"] for t in sampling_result["turns"]]
        all_samples = [t["samples"] for t in sampling_result["turns"]]
        sampling_total_sec = round(
            sum(float(t["sampling_time_sec"]) for t in sampling_result["turns"]),
            3,
        )

        t_h0 = time.perf_counter()
        h_values: List[float] = []
        for t_idx, samples in enumerate(all_samples):
            print(f"  Computing H(t={t_idx + 1})...")
            h_values.append(self.entropy_calc.compute_entropy(samples))
        entropy_compute_sec = round(time.perf_counter() - t_h0, 3)

        t_d0 = time.perf_counter()
        drift_raw = self.drift_calc.compute_drift_sequence(primary_responses)
        d_values = [0.0 if v is None else float(v) for v in drift_raw]
        drift_compute_sec = round(time.perf_counter() - t_d0, 3)

        turn_results: List[Dict[str, Any]] = []
        for i, turn_data in enumerate(sampling_result["turns"]):
            turn_results.append(
                {
                    "turn": turn_data["turn"],
                    "user": turn_data["user"],
                    "primary_response": turn_data["primary_response"],
                    "H": h_values[i],
                    "D": d_values[i],
                    "samples": turn_data["samples"],
                    "sampling_time_sec": turn_data["sampling_time_sec"],
                }
            )

        signal_compute_sec = round(entropy_compute_sec + drift_compute_sec, 3)
        return {
            "case_id": case_id,
            "description": conversation.get("description", ""),
            "expected_signals": conversation.get("expected_signals", {}),
            "turns": turn_results,
            "timing": {
                "sampling_total_sec": sampling_total_sec,
                "entropy_compute_sec": entropy_compute_sec,
                "drift_compute_sec": drift_compute_sec,
                "signal_compute_sec": signal_compute_sec,
            },
            "summary": {
                "H_sequence": h_values,
                "D_sequence": d_values,
                "H_mean": round(sum(h_values) / len(h_values), 4) if h_values else 0.0,
                "H_slope": self._linear_slope(h_values),
                "H_split_diff": _h_split_diff_second_minus_first(h_values),
                "D_mean": round(sum(d_values) / len(d_values), 4) if d_values else 0.0,
                "D_max_turn": int(d_values.index(max(d_values)) + 1) if d_values else 0,
            },
        }

    @staticmethod
    def _linear_slope(values: List[float]) -> float:
        n = len(values)
        if n < 2:
            return 0.0
        x_mean = (n - 1) / 2.0
        y_mean = sum(values) / n
        num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        den = sum((i - x_mean) ** 2 for i in range(n))
        return round(num / den, 6) if den else 0.0
