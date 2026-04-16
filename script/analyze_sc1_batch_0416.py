#!/usr/bin/env python3
"""
SC1 批量实验聚合分析 — 0416 版本

用法：
    python script/analyze_sc1_batch_0416.py <batch_dir>

<batch_dir> 下应有若干 run 子目录，每个包含 sc1_quantitative.json
和各 case 的 *_signals.json。

输出：
    - 控制台打印汇总表格
    - <batch_dir>/aggregate_results.json
    - <batch_dir>/summary.txt (由 shell 脚本 tee 捕获)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────
# 1. 收集数据
# ─────────────────────────────────────────────

def load_run(run_dir: Path) -> Optional[Dict[str, Any]]:
    """从一个 run 目录读取所有关键结果，返回 None 表示该 run 不完整。"""
    quant_path = run_dir / "sc1_quantitative.json"
    if not quant_path.exists():
        return None

    with open(quant_path) as f:
        quant = json.load(f)

    # 读取各 case 的 H/D 序列
    case_data: Dict[str, Any] = {}
    for case_id in ("case_a", "case_b", "case_c"):
        sig_path = run_dir / f"{case_id}_signals.json"
        if sig_path.exists():
            with open(sig_path) as f:
                sig = json.load(f)
            summary = sig.get("summary", {})
            case_data[case_id] = {
                "H_sequence": summary.get("H_sequence", []),
                "D_sequence": summary.get("D_sequence", []),
                "H_mean": summary.get("H_mean"),
                "H_slope": summary.get("H_slope"),
                "H_split_diff": summary.get("H_split_diff"),
                "D_mean": summary.get("D_mean"),
                "D_max_turn": summary.get("D_max_turn"),
            }

    # 从目录名提取温度（格式：t<TT>_run<N>）
    name = run_dir.name
    temp_str = None
    if name.startswith("t") and "_run" in name:
        try:
            tt = int(name.split("_")[0][1:])
            temp_str = f"{tt / 100:.2f}"
        except ValueError:
            pass

    checks = quant.get("checks", {})
    timing = quant.get("phase6_timing_case_b", {})

    return {
        "run_id": name,
        "temperature": temp_str,
        "checks": checks,
        "H_split_diff_case_a": case_data.get("case_a", {}).get("H_split_diff"),
        "H_mean_case_a": case_data.get("case_a", {}).get("H_mean"),
        "H_sequence_case_a": case_data.get("case_a", {}).get("H_sequence", []),
        "H_sequence_case_b": case_data.get("case_b", {}).get("H_sequence", []),
        "D_mean_case_a": case_data.get("case_a", {}).get("D_mean"),
        "D_mean_case_b": case_data.get("case_b", {}).get("D_mean"),
        "D_max_turn_case_c": quant.get("D_max_turn_case_c"),
        "all_pass_strict": quant.get("all_pass_strict_5.3_exact", False),
        "all_pass_relaxed": quant.get("all_pass_with_relaxed_d_peak", False),
        "per_turn_sec_signal_only": timing.get("per_turn_signal_sec"),
        "per_turn_sec_incl_sampling": timing.get("per_turn_signal_plus_sampling_sec"),
        "meets_15s_signal_only": timing.get("meets_15s_per_turn_signal_only"),
        "meets_15s_incl_sampling": timing.get("meets_15s_per_turn_including_sampling"),
    }


CHECK_KEYS = [
    "5.1_case_a_H_slope_positive",
    "5.2_case_b_H_std_lt_case_a",
    "5.3_case_c_D_peak_at_turn_6_exact",
    "5.3_case_c_D_peak_turn_relaxed_5_to_7",
    "5.4_case_b_D_mean_lt_case_a",
]


# ─────────────────────────────────────────────
# 2. 统计辅助
# ─────────────────────────────────────────────

def _safe_vals(runs: List[Dict], key: str) -> List[float]:
    return [r[key] for r in runs if r.get(key) is not None]


def _mean(vals: List[float]) -> Optional[float]:
    return sum(vals) / len(vals) if vals else None


def _std(vals: List[float]) -> Optional[float]:
    if len(vals) < 2:
        return None
    m = _mean(vals)
    assert m is not None
    return (sum((v - m) ** 2 for v in vals) / (len(vals) - 1)) ** 0.5


def _minmax(vals: List[float]):
    return (min(vals), max(vals)) if vals else (None, None)


# ─────────────────────────────────────────────
# 3. 格式化输出
# ─────────────────────────────────────────────

def _bool_str(v: Optional[bool]) -> str:
    if v is None:
        return "  -  "
    return " PASS" if v else " FAIL"


def _fmt(v, precision: int = 4) -> str:
    if v is None:
        return "   N/A"
    return f"{v:+.{precision}f}" if isinstance(v, float) else str(v)


def print_run_table(runs: List[Dict]) -> None:
    header = (
        f"{'run_id':<16} {'temp':>5} "
        f"{'5.1':>5} {'5.2':>5} {'5.3e':>5} {'5.3r':>5} {'5.4':>5} "
        f"{'HsplitA':>8} {'Hmean_A':>8} {'Dmean_A':>8} {'Dmean_B':>8} "
        f"{'DmaxT_C':>7} {'pass_r':>6}"
    )
    print(header)
    print("-" * len(header))
    for r in runs:
        checks = r["checks"]
        c51 = _bool_str(checks.get("5.1_case_a_H_slope_positive"))
        c52 = _bool_str(checks.get("5.2_case_b_H_std_lt_case_a"))
        c53e = _bool_str(checks.get("5.3_case_c_D_peak_at_turn_6_exact"))
        c53r = _bool_str(checks.get("5.3_case_c_D_peak_turn_relaxed_5_to_7"))
        c54 = _bool_str(checks.get("5.4_case_b_D_mean_lt_case_a"))
        hs = _fmt(r.get("H_split_diff_case_a"), 3)
        hm = _fmt(r.get("H_mean_case_a"), 3)
        da = _fmt(r.get("D_mean_case_a"), 3)
        db = _fmt(r.get("D_mean_case_b"), 3)
        dm = str(r.get("D_max_turn_case_c", "?"))
        pr = " PASS" if r.get("all_pass_relaxed") else " FAIL"
        temp = r.get("temperature", "?")
        print(
            f"{r['run_id']:<16} {temp:>5} "
            f"{c51:>5} {c52:>5} {c53e:>5} {c53r:>5} {c54:>5} "
            f"{hs:>8} {hm:>8} {da:>8} {db:>8} "
            f"{dm:>7} {pr:>6}"
        )


def print_aggregate(runs: List[Dict]) -> None:
    n = len(runs)
    print(f"\n{'═'*60}")
    print(f"  聚合统计  (N = {n} runs)")
    print(f"{'═'*60}")

    # check pass rates
    for ck in CHECK_KEYS:
        passed = sum(1 for r in runs if r["checks"].get(ck) is True)
        pct = passed / n * 100 if n else 0
        bar = "█" * passed + "░" * (n - passed)
        print(f"  {ck:<42}  {bar}  {passed}/{n} ({pct:.0f}%)")

    # H_split_diff 统计
    hs_vals = _safe_vals(runs, "H_split_diff_case_a")
    mn, mx = _minmax(hs_vals)
    print(f"\n  H_split_diff (case_a):")
    print(f"    mean={_fmt(_mean(hs_vals), 4)}  std={_fmt(_std(hs_vals), 4)}")
    print(f"    min={_fmt(mn, 4)}  max={_fmt(mx, 4)}")
    positive = sum(1 for v in hs_vals if v > 0)
    print(f"    >0: {positive}/{len(hs_vals)} ({positive/len(hs_vals)*100:.0f}% runs show H rise)")

    # H sequence averages per turn
    if any(r.get("H_sequence_case_a") for r in runs):
        n_turns = max(len(r.get("H_sequence_case_a", [])) for r in runs)
        print(f"\n  H(t) case_a — per-turn mean across runs:")
        for t in range(n_turns):
            vals = [r["H_sequence_case_a"][t] for r in runs if len(r.get("H_sequence_case_a", [])) > t]
            m = _mean(vals)
            s = _std(vals)
            bar = "▓" * int((m or 0) * 10)
            marker = " ← [pivot]" if t == 4 else ""
            print(f"    t{t+1:02d}: {_fmt(m, 3)} ± {_fmt(s, 3)}  {bar}{marker}")

    # D stats
    da_vals = _safe_vals(runs, "D_mean_case_a")
    db_vals = _safe_vals(runs, "D_mean_case_b")
    print(f"\n  D_mean case_a: {_fmt(_mean(da_vals), 4)}  D_mean case_b: {_fmt(_mean(db_vals), 4)}")

    # overall pass
    n_pass_strict = sum(1 for r in runs if r.get("all_pass_strict"))
    n_pass_relaxed = sum(1 for r in runs if r.get("all_pass_relaxed"))
    print(f"\n  全部通过 (strict 5.3):  {n_pass_strict}/{n} ({n_pass_strict/n*100:.0f}%)")
    print(f"  全部通过 (relaxed 5.3): {n_pass_relaxed}/{n} ({n_pass_relaxed/n*100:.0f}%)")

    # timing
    pt_vals = _safe_vals(runs, "per_turn_sec_incl_sampling")
    if pt_vals:
        print(f"\n  per_turn_sec (含 sampling): mean={_fmt(_mean(pt_vals), 2)}  max={_fmt(max(pt_vals), 2)}")
        ok = sum(1 for v in pt_vals if v <= 15.0)
        print(f"  满足 ≤15s/turn: {ok}/{len(pt_vals)}")

    print(f"{'═'*60}\n")


# ─────────────────────────────────────────────
# 4. 主流程
# ─────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 2:
        print(f"用法: {sys.argv[0]} <batch_dir>")
        sys.exit(1)

    batch_dir = Path(sys.argv[1]).resolve()
    if not batch_dir.is_dir():
        print(f"[ERROR] 目录不存在: {batch_dir}")
        sys.exit(1)

    # 找所有 run 子目录（包含 sc1_quantitative.json）
    run_dirs = sorted(
        d for d in batch_dir.iterdir()
        if d.is_dir() and (d / "sc1_quantitative.json").exists()
    )

    if not run_dirs:
        print(f"[WARN] {batch_dir} 下没有找到已完成的 run 目录（需含 sc1_quantitative.json）")
        sys.exit(0)

    runs = []
    for d in run_dirs:
        r = load_run(d)
        if r:
            runs.append(r)
        else:
            print(f"[WARN] 跳过不完整 run: {d.name}")

    print(f"\n已加载 {len(runs)} 个 run（共找到 {len(run_dirs)} 个目录）\n")

    print_run_table(runs)
    print_aggregate(runs)

    # 保存 JSON
    out_path = batch_dir / "aggregate_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(runs, f, indent=2, ensure_ascii=False)
    print(f"聚合 JSON 已保存至: {out_path}")


if __name__ == "__main__":
    main()
