#!/usr/bin/env bash
# =============================================================
# SC1 运行脚本（在服务器上执行）
# 用法：bash script/run_sc1.sh [--gpu <id>]
#
# 常用环境变量（可在此修改默认值，也可 export 后再运行）：
#   SC1_LLM_DEVICE      默认 auto（CUDA 优先）
#   SC1_NLI_DEVICE      默认 auto
#   SC1_EMBED_DEVICE    默认 auto
#   SC1_LLM_N_SAMPLES   默认 3
#   SC1_LLM_TEMPERATURE 默认 0.8
# =============================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GPU_ID="0"

# 解析参数
while [[ $# -gt 0 ]]; do
    case "$1" in
        --gpu) GPU_ID="$2"; shift 2 ;;
        *) echo "未知参数: $1"; exit 1 ;;
    esac
done

export PYTHONPATH="${REPO_ROOT}/src"
export SC1_LLM_DEVICE="cuda:${GPU_ID}"
export SC1_NLI_DEVICE="cuda:${GPU_ID}"
export SC1_EMBED_DEVICE="cuda:${GPU_ID}"

# 若有多张卡且想分开放，例如 NLI 放 cuda:1：
# export SC1_NLI_DEVICE="cuda:1"
# export SC1_EMBED_DEVICE="cuda:1"

echo "=============================="
echo "REPO   : ${REPO_ROOT}"
echo "LLM    : ${SC1_LLM_DEVICE}"
echo "NLI    : ${SC1_NLI_DEVICE}"
echo "EMBED  : ${SC1_EMBED_DEVICE}"
echo "=============================="

cd "${REPO_ROOT}"
python -m sc1
