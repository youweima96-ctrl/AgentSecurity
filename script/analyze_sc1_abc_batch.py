#!/usr/bin/env python3
"""
SC1 ABC 批量实验聚合分析

用法：
    python script/analyze_sc1_abc_batch.py <batch_dir>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


LEGACY_CHECKS = [
    "5.1_case_a_H_slope_positive",
    "5.2_case_b_H_std_lt_case_a",
    "5.3_case_c_D_peak_at_turn_6_exact",
    "5.3_case_c_D_peak_turn_relaxed_5_to_7",
    "5.4_case_b_D_mean_lt_case_a",
]

U_CHECKS = [
    "6.1_case_a_U_split_diff_positive",
    "6.2_case_b_U_std_lt_case_a",
    "6.4_case_b_U_mean_lt_case_a",
]


def _mean(vals: List[float]) -> Optional[float]:
    return sum(vals) / len(vals) if vals else None


def _std(vals: List[float]) -> Optional[float]:
    if len(vals) < 2:
        return None
    m = _mean(vals)
    assert m is not None
    return (sum((v - m) ** 2 for v in vals) / (len(vals) - 1)) ** 0.5


def _fmt(v: Any, precision: int = 4) -> str:
    if v is None:
        return "N/A"
    if isinstance(v, float):
        return f"{v:+.{precision}f}"
    return str(v)


def _fmt_temp(v: Optional[float]) -> str:
    if v is None:
        return "N/A"
    return f"{v:.2f}"


def _safe_vals(runs: List[Dict[str, Any]], key: str) -> List[float]:
    out: List[float] = []
    for r in runs:
        v = r.get(key)
        if isinstance(v, (int, float)):
            out.append(float(v))
    return out


def _bool(v: Optional[bool]) -> str:
    if v is None:
        return "-"
    return "PASS" if v else "FAIL"


def _pass_stats_for_check(runs: List[Dict[str, Any]], check_key: str) -> tuple[int, int]:
    available = 0
    passed = 0
    for r in runs:
        checks = r.get("checks", {})
        if check_key in checks:
            available += 1
            if checks.get(check_key) is True:
                passed += 1
    return available, passed


def load_run(run_dir: Path) -> Optional[Dict[str, Any]]:
    quant_path = run_dir / "sc1_quantitative.json"
    if not quant_path.exists():
        return None
    with open(quant_path, "r", encoding="utf-8") as f:
        quant = json.load(f)

    case_map: Dict[str, Dict[str, Any]] = {}
    for cid in ("case_a", "case_b", "case_c"):
        p = run_dir / f"{cid}_signals.json"
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                case_map[cid] = json.load(f)

    a_summary = case_map.get("case_a", {}).get("summary", {})
    b_summary = case_map.get("case_b", {}).get("summary", {})
    checks = quant.get("checks", {})
    timing = quant.get("phase6_timing_case_b", {})
    run_context = quant.get("run_context", {})

    temp = None
    name = run_dir.name
    if name.startswith("t") and "_run" in name:
        try:
            tt = int(name.split("_")[0][1:])
            temp = tt / 100.0
        except ValueError:
            temp = None
    if temp is None:
        try:
            temp = float(run_context.get("llm_temperature"))
        except (TypeError, ValueError):
            temp = None

    return {
        "run_id": run_dir.name,
        "temperature": temp,
        "run_label": run_context.get("run_label"),
        "checks": checks,
        "H_split_diff_case_a": a_summary.get("H_split_diff"),
        "H_mean_case_a": a_summary.get("H_mean"),
        "U_selected_mode_case_a": a_summary.get("U_selected_mode") or run_context.get("uncertainty_mode"),
        "U_split_diff_case_a": a_summary.get("U_selected_split_diff"),
        "U_mean_case_a": a_summary.get("U_selected_mean"),
        "U_mean_case_b": b_summary.get("U_selected_mean"),
        "D_mean_case_a": a_summary.get("D_mean"),
        "D_mean_case_b": b_summary.get("D_mean"),
        "D_max_turn_case_c": quant.get("D_max_turn_case_c"),
        "all_pass_legacy_relaxed": quant.get("all_pass_with_relaxed_d_peak"),
        "all_pass_u_relaxed": quant.get("all_pass_u_selected_with_relaxed_d_peak"),
        "per_turn_sec_incl_sampling": timing.get("per_turn_signal_plus_sampling_sec"),
    }


def print_run_table(runs: List[Dict[str, Any]]) -> None:
    header = (
        f"{'run':<14} {'temp':>5} "
        f"{'5.1':>5} {'5.2':>5} {'5.3r':>5} {'5.4':>5} "
        f"{'6.1':>5} {'6.2':>5} {'6.4':>5} "
        f"{'HsplitA':>8} {'UsplitA':>8} {'Umode':>10} "
        f"{'pass5':>6} {'pass6':>6}"
    )
    print(header)
    print("-" * len(header))
    for r in runs:
        c = r["checks"]
        print(
            f"{r['run_id']:<14} {_fmt_temp(r.get('temperature')):>5} "
            f"{_bool(c.get('5.1_case_a_H_slope_positive')):>5} "
            f"{_bool(c.get('5.2_case_b_H_std_lt_case_a')):>5} "
            f"{_bool(c.get('5.3_case_c_D_peak_turn_relaxed_5_to_7')):>5} "
            f"{_bool(c.get('5.4_case_b_D_mean_lt_case_a')):>5} "
            f"{_bool(c.get('6.1_case_a_U_split_diff_positive')):>5} "
            f"{_bool(c.get('6.2_case_b_U_std_lt_case_a')):>5} "
            f"{_bool(c.get('6.4_case_b_U_mean_lt_case_a')):>5} "
            f"{_fmt(r.get('H_split_diff_case_a'), 3):>8} "
            f"{_fmt(r.get('U_split_diff_case_a'), 3):>8} "
            f"{str(r.get('U_selected_mode_case_a', 'N/A')):>10} "
            f"{_bool(r.get('all_pass_legacy_relaxed')):>6} "
            f"{_bool(r.get('all_pass_u_relaxed')):>6}"
        )


def print_pass_rates(runs: List[Dict[str, Any]]) -> None:
    n = len(runs)
    print(f"\n{'═' * 64}")
    print(f"  聚合统计 (N={n})")
    print(f"{'═' * 64}")
    all_keys = LEGACY_CHECKS + U_CHECKS
    for ck in all_keys:
        avail, ok = _pass_stats_for_check(runs, ck)
        if avail == 0:
            print(f"  {ck:<40} N/A")
        else:
            pct = ok / avail * 100.0
            print(f"  {ck:<40} {ok:>2}/{avail:<2} ({pct:>5.1f}%)")

    n_legacy_avail = sum(1 for r in runs if r.get("all_pass_legacy_relaxed") is not None)
    n_legacy = sum(1 for r in runs if r.get("all_pass_legacy_relaxed") is True)
    n_u_avail = sum(1 for r in runs if r.get("all_pass_u_relaxed") is not None)
    n_u = sum(1 for r in runs if r.get("all_pass_u_relaxed") is True)
    print(f"\n  Overall legacy (relaxed 5.3): {n_legacy}/{n} ({(n_legacy / n * 100.0) if n else 0:.1f}%)")
    if n_u_avail:
        print(f"  Overall U-selected (relaxed 5.3): {n_u}/{n_u_avail} ({(n_u / n_u_avail * 100.0):.1f}%)")
    else:
        print("  Overall U-selected (relaxed 5.3): N/A")

    hs = _safe_vals(runs, "H_split_diff_case_a")
    us = _safe_vals(runs, "U_split_diff_case_a")
    pt = _safe_vals(runs, "per_turn_sec_incl_sampling")
    print("\n  split_diff case_a:")
    print(f"    H_split mean={_fmt(_mean(hs), 4)} std={_fmt(_std(hs), 4)}")
    print(f"    U_split mean={_fmt(_mean(us), 4)} std={_fmt(_std(us), 4)}")
    if pt:
        print(f"\n  每轮时延(含sampling): mean={_fmt(_mean(pt), 2)} max={_fmt(max(pt), 2)}")
        ok = sum(1 for v in pt if v <= 15.0)
        print(f"  ≤15s/turn 达标: {ok}/{len(pt)}")
    print(f"{'═' * 64}\n")


def main() -> None:
    if len(sys.argv) < 2:
        print(f"用法: {sys.argv[0]} <batch_dir>")
        sys.exit(1)
    batch_dir = Path(sys.argv[1]).resolve()
    if not batch_dir.is_dir():
        print(f"[ERROR] 目录不存在: {batch_dir}")
        sys.exit(1)

    run_dirs = sorted(
        d for d in batch_dir.iterdir() if d.is_dir() and (d / "sc1_quantitative.json").exists()
    )
    if not run_dirs:
        print(f"[WARN] {batch_dir} 下没有找到有效 run")
        sys.exit(0)

    runs: List[Dict[str, Any]] = []
    for d in run_dirs:
        item = load_run(d)
        if item is not None:
            runs.append(item)

    print(f"\n已加载 {len(runs)} 个 run（目录共 {len(run_dirs)} 个）\n")
    print_run_table(runs)
    print_pass_rates(runs)

    out_path = batch_dir / "aggregate_results_abc.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(runs, f, indent=2, ensure_ascii=False)
    print(f"聚合 JSON 已保存至: {out_path}")


if __name__ == "__main__":
    main()

