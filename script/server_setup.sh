#!/usr/bin/env bash
# =============================================================
# SC1 服务器一键环境配置脚本
# 用法：
#   git clone https://github.com/youweima96-ctrl/AgentSecurity.git
#   cd AgentSecurity
#   bash script/server_setup.sh
# =============================================================
set -euo pipefail

CONDA_ENV="agentsecurity"
PY_VERSION="3.11"

echo "===== [1/4] 创建 conda 环境: ${CONDA_ENV} ====="
if conda env list | grep -qw "${CONDA_ENV}"; then
    echo "环境已存在，跳过创建。"
else
    conda create -y -n "${CONDA_ENV}" python="${PY_VERSION}"
fi

echo "===== [2/4] 激活环境并安装 PyTorch（CUDA 12.1）====="
# 若服务器 CUDA 版本不同，将 cu121 改成对应版本，例如 cu118 / cu124
conda run -n "${CONDA_ENV}" pip install --upgrade pip

conda run -n "${CONDA_ENV}" pip install \
    torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu121

echo "===== [3/4] 安装其余依赖 ====="
conda run -n "${CONDA_ENV}" pip install -r requirements-sc1.txt

echo "===== [4/4] 安装 huggingface_hub CLI（可选，用于提前下载模型）====="
conda run -n "${CONDA_ENV}" pip install huggingface_hub

echo ""
echo "===== 配置完成 ====="
echo ""
echo "下一步：登录 HuggingFace 以访问 Llama-3-8B（需要申请过 Meta 授权）："
echo "  conda activate ${CONDA_ENV}"
echo "  huggingface-cli login"
echo ""
echo "然后运行 SC1："
echo "  cd $(pwd)"
echo "  conda activate ${CONDA_ENV}"
echo "  export PYTHONPATH=src"
echo "  python -m sc1"
