"""3×2 plots: cases × (H, D)."""

from __future__ import annotations

import os
from typing import Any, Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np

from sc1.config import RESULTS_DIR


def plot_sc1_signals(results: List[Dict[str, Any]], save_path: str | None = None) -> str:
    fig = plt.figure(figsize=(14, 12))
    gs = gridspec.GridSpec(3, 2, hspace=0.5, wspace=0.3)

    case_labels = {
        "case_a": "Case A: Gradual Jailbreak Escalation",
        "case_b": "Case B: Normal Conversation (Cooking)",
        "case_c": "Case C: Sudden Topic Jump at Turn 6",
    }
    case_colors = {"case_a": "#E74C3C", "case_b": "#27AE60", "case_c": "#3498DB"}

    for row, result in enumerate(results):
        case_id = result["case_id"]
        h_seq = result["summary"]["H_sequence"]
        d_seq = result["summary"]["D_sequence"]
        turns = list(range(1, len(h_seq) + 1))
        color = case_colors.get(case_id, "black")
        label = case_labels.get(case_id, case_id)

        ax_h = fig.add_subplot(gs[row, 0])
        ax_h.plot(turns, h_seq, marker="o", color=color, linewidth=2, markersize=6)
        ax_h.axhline(
            y=float(np.mean(h_seq)),
            color=color,
            linestyle="--",
            alpha=0.5,
            label=f"mean={float(np.mean(h_seq)):.3f}",
        )
        ax_h.set_ylim(-0.05, 1.2)
        ax_h.set_xlabel("Turn", fontsize=10)
        ax_h.set_ylabel("Semantic Entropy H(t)", fontsize=10)
        ax_h.set_title(f"{label}\nH(t)", fontsize=9)
        ax_h.set_xticks(turns)
        ax_h.legend(fontsize=8)
        ax_h.grid(alpha=0.3)
        if case_id == "case_a":
            ax_h.axvline(x=6, color="gray", linestyle=":", alpha=0.7)
            ax_h.text(6.1, 0.9, "jailbreak\nstart", fontsize=7, color="gray")

        ax_d = fig.add_subplot(gs[row, 1])
        ax_d.plot(turns, d_seq, marker="s", color=color, linewidth=2, markersize=6)
        ax_d.axhline(
            y=float(np.mean(d_seq)),
            color=color,
            linestyle="--",
            alpha=0.5,
            label=f"mean={float(np.mean(d_seq)):.3f}",
        )
        ax_d.set_ylim(-0.05, 1.1)
        ax_d.set_xlabel("Turn", fontsize=10)
        ax_d.set_ylabel("Embedding Drift D(t)", fontsize=10)
        ax_d.set_title("D(t)", fontsize=9)
        ax_d.set_xticks(turns)
        ax_d.legend(fontsize=8)
        ax_d.grid(alpha=0.3)
        if case_id == "case_c":
            ax_d.axvline(x=6, color="gray", linestyle=":", alpha=0.7)
            ax_d.text(6.1, 0.9, "topic\njump", fontsize=7, color="gray")
            if len(d_seq) >= 6:
                ax_d.plot([6], [d_seq[5]], marker="*", color="red", markersize=15, zorder=5)

    plt.suptitle(
        "SC1: Signal Directionality Validation\nSemantic Entropy H(t) and Embedding Drift D(t)",
        fontsize=13,
        fontweight="bold",
    )
    save_path = save_path or str(RESULTS_DIR / "sc1_plots.png")
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nPlot saved to: {save_path}")
    return save_path
