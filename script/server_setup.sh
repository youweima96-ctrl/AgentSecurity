#!/usr/bin/env bash
# =============================================================
# SC1 服务器一键环境配置脚本
# 用法：
#   git clone https://github.com/youweima96-ctrl/AgentSecurity.git
#   cd AgentSecurity
#   bash script/server_setup.sh
#
# 环境目录：./env（即仓库根目录下，不写入全局 conda envs）
# 激活方式：conda activate ./env
# =============================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_DIR="${REPO_ROOT}/env"
PY_VERSION="3.11"

echo "===== [1/4] 创建本地 conda 环境: ${ENV_DIR} ====="
if [ -d "${ENV_DIR}" ]; then
    echo "环境目录已存在，跳过创建。"
else
    conda create -y --prefix "${ENV_DIR}" python="${PY_VERSION}"
fi

echo "===== [2/4] 安装 PyTorch（CUDA 12.1）====="
# 若服务器 CUDA 版本不同，将 cu121 改成对应版本，例如 cu118 / cu124
conda run --prefix "${ENV_DIR}" pip install --upgrade pip

conda run --prefix "${ENV_DIR}" pip install \
    torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu121

echo "===== [3/4] 安装其余依赖 ====="
conda run --prefix "${ENV_DIR}" pip install -r "${REPO_ROOT}/requirements-sc1.txt"

echo "===== [4/4] 安装 huggingface_hub CLI（用于下载模型和登录）====="
conda run --prefix "${ENV_DIR}" pip install huggingface_hub

echo ""
echo "===== 配置完成 ====="
echo ""
echo "下一步：登录 HuggingFace 以访问 Llama-3-8B（需要申请过 Meta 授权）："
echo "  conda activate ${ENV_DIR}"
echo "  huggingface-cli login"
echo ""
echo "然后运行 SC1："
echo "  conda activate ${ENV_DIR}"
echo "  bash ${REPO_ROOT}/script/run_sc1.sh"
