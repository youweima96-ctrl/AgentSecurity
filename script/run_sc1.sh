#!/usr/bin/env bash
# =============================================================
# SC1 运行脚本（在服务器上执行）
# 用法：bash script/run_sc1.sh [--gpu <id>]
#
# 常用环境变量（export 后再运行可覆盖默认值）：
#   SC1_LLM_MODEL       LLM 模型名（默认 meta-llama/Meta-Llama-3-8B-Instruct）
#   SC1_LLM_DEVICE      GPU（默认 auto，即 cuda:0 / mps / cpu）
#   SC1_NLI_DEVICE      默认同 SC1_LLM_DEVICE
#   SC1_EMBED_DEVICE    默认同 SC1_LLM_DEVICE
#   SC1_LLM_N_SAMPLES   默认 3
#   SC1_LLM_TEMPERATURE 默认 0.8
#
# 示例：用 GPU 1
#   bash script/run_sc1.sh --gpu 1
#
# 示例：临时换模型
#   SC1_LLM_MODEL=Qwen/Qwen2.5-7B-Instruct bash script/run_sc1.sh --gpu 0
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

# 若有多张卡且想分开放，例如 NLI/Embed 放另一张：
# export SC1_NLI_DEVICE="cuda:1"
# export SC1_EMBED_DEVICE="cuda:1"

LLM_SHOW="${SC1_LLM_MODEL:-meta-llama/Meta-Llama-3-8B-Instruct (config default)}"

echo "=============================="
echo "REPO   : ${REPO_ROOT}"
echo "PYTHON : $(which python)"
echo "LLM    : ${LLM_SHOW} @ ${SC1_LLM_DEVICE}"
echo "NLI    : ${SC1_NLI_DEVICE}"
echo "EMBED  : ${SC1_EMBED_DEVICE}"
echo "RESULT : ${REPO_ROOT}/result/sc1/"
echo "=============================="

cd "${REPO_ROOT}"
python -m sc1
