#!/usr/bin/env bash
# =============================================================
# SC1 批量实验脚本 — 0416 版本
#
# 用法：
#   bash script/run_sc1_batch_0416.sh [--gpu <id>] [--max-new <tokens>]
#
# 说明：
#   一次跑 10 组实验，温度从 0.60 梯度到 1.05 (含)。
#   每组结果保存到独立子目录:
#     result/sc1_0416/t<TT>_run<N>/
#   （TT = 温度 × 100 取整，N = 1-based 序号）
#
#   全部跑完后自动调用 analyze_sc1_batch_0416.py 生成汇总。
#
# 常用覆盖变量：
#   SC1_LLM_MODEL        默认 meta-llama/Meta-Llama-3-8B-Instruct
#   SC1_LLM_N_SAMPLES    默认 3
#   SC1_LLM_DEVICE_MAP   设 auto 可跨多 GPU（缓解 OOM）
#
# 示例：
#   bash script/run_sc1_batch_0416.sh --gpu 1 --max-new 96
# =============================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GPU_ID="0"
MAX_NEW="${SC1_LLM_MAX_NEW:-96}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --gpu)      GPU_ID="$2";  shift 2 ;;
        --max-new)  MAX_NEW="$2"; shift 2 ;;
        *) echo "[ERROR] 未知参数: $1"; exit 1 ;;
    esac
done

export PYTHONPATH="${REPO_ROOT}/src"
export SC1_LLM_DEVICE="cuda:${GPU_ID}"
export SC1_NLI_DEVICE="cuda:${GPU_ID}"
export SC1_EMBED_DEVICE="cuda:${GPU_ID}"
export SC1_LLM_MAX_NEW="${MAX_NEW}"

BATCH_ROOT="${REPO_ROOT}/result/sc1_0416"
PYTHON="${REPO_ROOT}/env/bin/python"
if [[ ! -x "${PYTHON}" ]]; then
    PYTHON="$(which python)"
fi

# 10 组温度梯度 (0.60 ~ 1.05，步长 0.05)
TEMPERATURES=(0.60 0.65 0.70 0.75 0.80 0.85 0.90 0.95 1.00 1.05)

echo "=============================="
echo "批量实验 SC1 0416"
echo "  REPO    : ${REPO_ROOT}"
echo "  PYTHON  : ${PYTHON}"
echo "  GPU     : cuda:${GPU_ID}"
echo "  MAX_NEW : ${MAX_NEW}"
echo "  RUNS    : ${#TEMPERATURES[@]}"
echo "  OUTPUT  : ${BATCH_ROOT}"
echo "=============================="
echo ""

mkdir -p "${BATCH_ROOT}"

FAILED_RUNS=()

for i in "${!TEMPERATURES[@]}"; do
    TEMP="${TEMPERATURES[$i]}"
    RUN_IDX=$(( i + 1 ))
    # e.g. t080_run1
    TT=$(printf "%03d" "$(echo "${TEMP} * 100 / 1" | bc)")
    RUN_DIR="${BATCH_ROOT}/t${TT}_run${RUN_IDX}"
    mkdir -p "${RUN_DIR}"

    LOG_FILE="${RUN_DIR}/run.log"

    echo "----------------------------------------------"
    echo "  [${RUN_IDX}/${#TEMPERATURES[@]}]  temp=${TEMP}  →  ${RUN_DIR}"
    echo "----------------------------------------------"

    # 每组实验单独设置 TEMPERATURE 和 RESULTS_DIR
    if SC1_LLM_TEMPERATURE="${TEMP}" \
       SC1_RESULTS_DIR="${RUN_DIR}" \
       "${PYTHON}" -m sc1 2>&1 | tee "${LOG_FILE}"; then
        echo "  [OK] run ${RUN_IDX} (temp=${TEMP}) 完成"
    else
        echo "  [FAIL] run ${RUN_IDX} (temp=${TEMP}) 失败，已记录日志至 ${LOG_FILE}"
        FAILED_RUNS+=("t${TT}_run${RUN_IDX}")
    fi
    echo ""
done

# ── 汇总分析 ──────────────────────────────────────────────
echo "=============================="
echo "全部 ${#TEMPERATURES[@]} 组完成，开始聚合分析..."
echo "=============================="

ANALYZE_SCRIPT="${REPO_ROOT}/script/analyze_sc1_batch_0416.py"
if [[ -f "${ANALYZE_SCRIPT}" ]]; then
    "${PYTHON}" "${ANALYZE_SCRIPT}" "${BATCH_ROOT}" | tee "${BATCH_ROOT}/summary.txt"
    echo ""
    echo "汇总结果已保存至 ${BATCH_ROOT}/summary.txt"
else
    echo "[WARN] 分析脚本 ${ANALYZE_SCRIPT} 不存在，跳过"
fi

# ── 报告失败 ─────────────────────────────────────────────
if [[ ${#FAILED_RUNS[@]} -gt 0 ]]; then
    echo ""
    echo "[WARN] 以下 run 失败："
    for r in "${FAILED_RUNS[@]}"; do
        echo "  - ${r}"
    done
    exit 1
fi

echo ""
echo "全部实验成功完成。"
