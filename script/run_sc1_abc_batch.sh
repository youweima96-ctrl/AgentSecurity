#!/usr/bin/env bash
# =============================================================
# SC1 ABC 大改批量实验脚本（支持多轮多种类矩阵）
#
# 用法：
#   bash script/run_sc1_abc_batch.sh \
#     [--gpu <id>] [--max-new <tokens>] [--samples <n>] [--repeats <n>] \
#     [--temps "0.60,0.65,..."] \
#     [--modes "hybrid,nli_entropy_norm,embed_dispersion"] \
#     [--thresholds "0.65,0.70,0.75"] \
#     [--sweep "0.60,0.70,0.80"] [--cases "a.json,b.json,c.json"] \
#     [--out <batch_dir>]
# =============================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GPU_ID="0"
MAX_NEW="${SC1_LLM_MAX_NEW:-96}"
N_SAMPLES="${SC1_LLM_N_SAMPLES:-8}"
REPEATS="${SC1_BATCH_REPEATS:-2}"
MODES_CSV="${SC1_UNCERTAINTY_MODES:-hybrid,nli_entropy_norm,embed_dispersion}"
THRESHOLDS_CSV="${SC1_NLI_THRESHOLD_LIST:-0.70}"
TEMPS_CSV="${SC1_TEMPERATURE_LIST:-0.60,0.65,0.70,0.75,0.80,0.85,0.90,0.95,1.00,1.05}"
NLI_SWEEP="${SC1_NLI_THRESHOLD_SWEEP:-0.60,0.70,0.80}"
CASE_FILES="${SC1_CASE_FILES:-}"
U_W_NLI="${SC1_U_WEIGHT_NLI:-0.4}"
U_W_DISP="${SC1_U_WEIGHT_DISP:-0.4}"
U_W_DISAGR="${SC1_U_WEIGHT_DISAGR:-0.2}"
RUN_TAG="$(date +%m%d)"
BATCH_ROOT_DEFAULT="${REPO_ROOT}/result/sc1_abc_${RUN_TAG}"
BATCH_ROOT="${BATCH_ROOT_DEFAULT}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --gpu) GPU_ID="$2"; shift 2 ;;
        --max-new) MAX_NEW="$2"; shift 2 ;;
        --samples) N_SAMPLES="$2"; shift 2 ;;
        --repeats) REPEATS="$2"; shift 2 ;;
        --temps) TEMPS_CSV="$2"; shift 2 ;;
        --modes) MODES_CSV="$2"; shift 2 ;;
        --thresholds) THRESHOLDS_CSV="$2"; shift 2 ;;
        --sweep) NLI_SWEEP="$2"; shift 2 ;;
        --cases) CASE_FILES="$2"; shift 2 ;;
        --out) BATCH_ROOT="$2"; shift 2 ;;
        *) echo "[ERROR] 未知参数: $1"; exit 1 ;;
    esac
done

if [[ "${BATCH_ROOT}" != /* ]]; then
    BATCH_ROOT="${REPO_ROOT}/${BATCH_ROOT}"
fi

export PYTHONPATH="${REPO_ROOT}/src"
export SC1_LLM_DEVICE="cuda:${GPU_ID}"
export SC1_NLI_DEVICE="cuda:${GPU_ID}"
export SC1_EMBED_DEVICE="cuda:${GPU_ID}"
export SC1_LLM_MAX_NEW="${MAX_NEW}"
export SC1_LLM_N_SAMPLES="${N_SAMPLES}"
export SC1_NLI_THRESHOLD_SWEEP="${NLI_SWEEP}"
export SC1_U_WEIGHT_NLI="${U_W_NLI}"
export SC1_U_WEIGHT_DISP="${U_W_DISP}"
export SC1_U_WEIGHT_DISAGR="${U_W_DISAGR}"
export SC1_SAVE_DEBUG_SIGNALS="${SC1_SAVE_DEBUG_SIGNALS:-1}"
if [[ -n "${CASE_FILES}" ]]; then
    export SC1_CASE_FILES="${CASE_FILES}"
fi

PYTHON="${REPO_ROOT}/env/bin/python"
if [[ ! -x "${PYTHON}" ]]; then
    PYTHON="$(which python)"
fi

IFS=',' read -r -a TEMPERATURES <<< "${TEMPS_CSV}"
IFS=',' read -r -a MODES <<< "${MODES_CSV}"
IFS=',' read -r -a THRESHOLDS <<< "${THRESHOLDS_CSV}"

N_TOTAL=$(( ${#TEMPERATURES[@]} * ${#MODES[@]} * ${#THRESHOLDS[@]} * REPEATS ))

echo "=============================="
echo "SC1 ABC 批量实验"
echo "  REPO            : ${REPO_ROOT}"
echo "  PYTHON          : ${PYTHON}"
echo "  GPU             : cuda:${GPU_ID}"
echo "  MAX_NEW         : ${MAX_NEW}"
echo "  N_SAMPLES       : ${N_SAMPLES}"
echo "  REPEATS         : ${REPEATS}"
echo "  TEMPS           : ${TEMPS_CSV}"
echo "  MODES           : ${MODES_CSV}"
echo "  THRESHOLDS      : ${THRESHOLDS_CSV}"
echo "  NLI_SWEEP       : ${NLI_SWEEP}"
echo "  CASE_FILES      : ${CASE_FILES:-<default ABC>}"
echo "  U_WEIGHTS       : nli=${U_W_NLI}, disp=${U_W_DISP}, disagr=${U_W_DISAGR}"
echo "  TOTAL RUNS      : ${N_TOTAL}"
echo "  OUTPUT          : ${BATCH_ROOT}"
echo "=============================="
echo ""

mkdir -p "${BATCH_ROOT}"
FAILED_RUNS=()
RUN_IDX=0

for MODE in "${MODES[@]}"; do
    MODE="$(echo "${MODE}" | xargs)"
    [[ -z "${MODE}" ]] && continue
    for TH in "${THRESHOLDS[@]}"; do
        TH="$(echo "${TH}" | xargs)"
        [[ -z "${TH}" ]] && continue
        TH_TAG="$(printf "%03d" "$(echo "${TH} * 100 / 1" | bc)")"
        for REP in $(seq 1 "${REPEATS}"); do
            for TEMP in "${TEMPERATURES[@]}"; do
                TEMP="$(echo "${TEMP}" | xargs)"
                [[ -z "${TEMP}" ]] && continue
                RUN_IDX=$((RUN_IDX + 1))
                TT="$(printf "%03d" "$(echo "${TEMP} * 100 / 1" | bc)")"
                RUN_NAME="m${MODE}_th${TH_TAG}_t${TT}_r${REP}_run${RUN_IDX}"
                RUN_DIR="${BATCH_ROOT}/${RUN_NAME}"
                mkdir -p "${RUN_DIR}"
                LOG_FILE="${RUN_DIR}/run.log"
                RUN_LABEL="mode=${MODE};th=${TH};temp=${TEMP};rep=${REP};idx=${RUN_IDX}"

                echo "----------------------------------------------"
                echo "  [${RUN_IDX}/${N_TOTAL}] ${RUN_LABEL}"
                echo "  -> ${RUN_DIR}"
                echo "----------------------------------------------"
                if SC1_UNCERTAINTY_MODE="${MODE}" \
                   SC1_NLI_THRESHOLD="${TH}" \
                   SC1_LLM_TEMPERATURE="${TEMP}" \
                   SC1_RUN_LABEL="${RUN_LABEL}" \
                   SC1_RESULTS_DIR="${RUN_DIR}" \
                   "${PYTHON}" -m sc1 2>&1 | tee "${LOG_FILE}"; then
                    echo "  [OK] ${RUN_NAME}"
                else
                    echo "  [FAIL] ${RUN_NAME}，日志: ${LOG_FILE}"
                    FAILED_RUNS+=("${RUN_NAME}")
                fi
                echo ""
            done
        done
    done
done

echo "=============================="
echo "全部 run 结束，开始聚合分析..."
echo "=============================="

if [[ -f "${REPO_ROOT}/script/analyze_sc1_batch_0416.py" ]]; then
    "${PYTHON}" "${REPO_ROOT}/script/analyze_sc1_batch_0416.py" "${BATCH_ROOT}" \
        | tee "${BATCH_ROOT}/summary_legacy.txt"
fi

if [[ -f "${REPO_ROOT}/script/analyze_sc1_abc_batch.py" ]]; then
    "${PYTHON}" "${REPO_ROOT}/script/analyze_sc1_abc_batch.py" "${BATCH_ROOT}" \
        | tee "${BATCH_ROOT}/summary_abc.txt"
fi

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

