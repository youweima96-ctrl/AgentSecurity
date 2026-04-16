"""End-to-end: sample → H(t) → D(t)."""

from __future__ import annotations

import time
from typing import Any, Dict, List

from sc1.config import (
    NLI_ENTAILMENT_THRESHOLD,
    NLI_THRESHOLD_SWEEP,
    SAVE_DEBUG_SIGNALS,
    UNCERTAINTY_MODE,
    U_WEIGHT_DISAGR,
    U_WEIGHT_DISP,
    U_WEIGHT_NLI,
)
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
        h_norm_values: List[float] = []
        u_disp_values: List[float] = []
        u_disagr_values: List[float] = []
        u_hybrid_values: List[float] = []
        u_selected_values: List[float] = []
        turn_uncertainty_debug: List[Dict[str, Any]] = []
        for t_idx, samples in enumerate(all_samples):
            print(f"  Computing H(t={t_idx + 1})...")
            ent = self.entropy_calc.compute_turn_metrics(
                samples=samples,
                threshold=NLI_ENTAILMENT_THRESHOLD,
                sweep_thresholds=NLI_THRESHOLD_SWEEP,
            )
            h = float(ent["entropy"])
            h_norm = float(ent["entropy_normalized"])
            disagr = float(ent["disagreement_ratio"])
            disp = self.drift_calc.compute_sample_dispersion(samples)
            hybrid = round(
                U_WEIGHT_NLI * h_norm + U_WEIGHT_DISP * disp + U_WEIGHT_DISAGR * disagr,
                6,
            )
            selected = self._select_uncertainty_value(
                mode=UNCERTAINTY_MODE,
                h_entropy=h,
                h_norm=h_norm,
                disp=disp,
                disagr=disagr,
                hybrid=hybrid,
            )
            h_values.append(h)
            h_norm_values.append(h_norm)
            u_disp_values.append(disp)
            u_disagr_values.append(disagr)
            u_hybrid_values.append(hybrid)
            u_selected_values.append(selected)
            turn_uncertainty_debug.append(ent)
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
                    "H_entropy_normalized": h_norm_values[i],
                    "U_embed_dispersion": u_disp_values[i],
                    "U_disagreement": u_disagr_values[i],
                    "U_hybrid": u_hybrid_values[i],
                    "U_selected": u_selected_values[i],
                    "samples": turn_data["samples"],
                    "sampling_time_sec": turn_data["sampling_time_sec"],
                }
            )

        signal_compute_sec = round(entropy_compute_sec + drift_compute_sec, 3)
        payload = {
            "mode": UNCERTAINTY_MODE,
            "nli_threshold_main": NLI_ENTAILMENT_THRESHOLD,
            "nli_threshold_sweep": NLI_THRESHOLD_SWEEP,
            "hybrid_weights": {
                "nli_entropy_norm": U_WEIGHT_NLI,
                "embed_dispersion": U_WEIGHT_DISP,
                "disagreement": U_WEIGHT_DISAGR,
            },
        }
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
            "uncertainty_config": payload,
            "summary": {
                "H_sequence": h_values,
                "H_entropy_norm_sequence": h_norm_values,
                "U_embed_dispersion_sequence": u_disp_values,
                "U_disagreement_sequence": u_disagr_values,
                "U_hybrid_sequence": u_hybrid_values,
                "U_selected_mode": UNCERTAINTY_MODE,
                "U_selected_sequence": u_selected_values,
                "D_sequence": d_values,
                "H_mean": round(sum(h_values) / len(h_values), 4) if h_values else 0.0,
                "H_slope": self._linear_slope(h_values),
                "H_split_diff": _h_split_diff_second_minus_first(h_values),
                "U_selected_mean": round(sum(u_selected_values) / len(u_selected_values), 4)
                if u_selected_values
                else 0.0,
                "U_selected_slope": self._linear_slope(u_selected_values),
                "U_selected_split_diff": _h_split_diff_second_minus_first(u_selected_values),
                "D_mean": round(sum(d_values) / len(d_values), 4) if d_values else 0.0,
                "D_max_turn": int(d_values.index(max(d_values)) + 1) if d_values else 0,
            },
            "debug": {
                "turn_uncertainty_details": turn_uncertainty_debug,
            }
            if SAVE_DEBUG_SIGNALS
            else {},
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

    @staticmethod
    def _select_uncertainty_value(
        mode: str,
        h_entropy: float,
        h_norm: float,
        disp: float,
        disagr: float,
        hybrid: float,
    ) -> float:
        m = mode.strip().lower()
        if m == "nli_entropy":
            return round(h_entropy, 6)
        if m == "nli_entropy_norm":
            return round(h_norm, 6)
        if m == "embed_dispersion":
            return round(disp, 6)
        if m == "disagreement":
            return round(disagr, 6)
        # default: hybrid
        if m not in ("hybrid",):
            return round(hybrid, 6)
        # hybrid defaults to normalized entropy (avoid scale mismatch) + other uncertainties
        return round(hybrid, 6)
