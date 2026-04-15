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
#
# 注意：CUDA 版本选择
#   服务器 CUDA 12.0–12.3 → cu121（默认）
#   服务器 CUDA 12.4+      → 改下方 TORCH_CUDA_TAG 为 cu124
# =============================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_DIR="${REPO_ROOT}/env"
PY_VERSION="3.11"
TORCH_CUDA_TAG="${TORCH_CUDA_TAG:-cu121}"   # 按服务器 CUDA 版本设置

echo "===== [1/5] 创建本地 conda 环境: ${ENV_DIR} ====="
if [ -d "${ENV_DIR}" ]; then
    echo "环境目录已存在，跳过创建。"
else
    conda create -y --prefix "${ENV_DIR}" python="${PY_VERSION}"
fi

echo "===== [2/5] 安装 PyTorch >= 2.6 + torchvision（同版本源，一次对齐）====="
# torch 和 torchvision 必须来自同一个 CUDA tag 的索引，否则会版本冲突。
# 若之前已装过旧版，先卸掉：
conda run --prefix "${ENV_DIR}" pip uninstall -y torch torchvision torchaudio 2>/dev/null || true
conda run --prefix "${ENV_DIR}" pip install \
    "torch>=2.6" torchvision \
    --index-url "https://download.pytorch.org/whl/${TORCH_CUDA_TAG}"

echo "===== [3/5] 安装其余依赖 ====="
conda run --prefix "${ENV_DIR}" pip install -r "${REPO_ROOT}/requirements-sc1.txt"

echo "===== [4/5] 安装 huggingface_hub CLI（用于下载模型和登录）====="
conda run --prefix "${ENV_DIR}" pip install -U huggingface_hub

echo "===== [5/5] 验证关键包版本 ====="
conda run --prefix "${ENV_DIR}" python - <<'PYEOF'
import torch, torchvision, transformers, matplotlib, numpy
print(f"  torch         : {torch.__version__}")
print(f"  CUDA 可用      : {torch.cuda.is_available()}")
print(f"  torchvision   : {torchvision.__version__}")
print(f"  transformers  : {transformers.__version__}")
print(f"  matplotlib    : {matplotlib.__version__}")
print(f"  numpy         : {numpy.__version__}")
assert torch.__version__ >= "2.6", "torch 需要 >= 2.6"
print("  验证通过 ✓")
PYEOF

echo ""
echo "===== 配置完成 ====="
echo ""
echo "下一步：登录 HuggingFace 以访问 Llama-3-8B（需要申请过 Meta 授权）："
echo "  conda activate ${ENV_DIR}"
echo "  python -m huggingface_hub.cli.hf auth login"
echo "  （不要用 huggingface-cli，PATH 里可能有旧包）"
echo ""
echo "然后运行 SC1（默认 GPU 0）："
echo "  conda activate ${ENV_DIR}"
echo "  bash ${REPO_ROOT}/script/run_sc1.sh --gpu 0"
echo ""
echo "切换 CUDA 版本重新安装示例："
echo "  TORCH_CUDA_TAG=cu124 bash ${REPO_ROOT}/script/server_setup.sh"
