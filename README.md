# agentsecurity

智能体安全相关科研仓库：环境说明、文献笔记、SC1 信号方向性验证代码等。

## SC1（语义熵 + 嵌入漂移）

依赖见 `requirements-sc1.txt`。建议在 **GPU 服务器** 上运行（需下载 Llama-3-8B-Instruct、NLI、SimCSE）。

```bash
conda activate agentsecurity
pip install -r requirements-sc1.txt
cd /path/to/agentsecurity
export PYTHONPATH=src
python -m sc1
```

- 对话数据：`data/sc1/conversations/*.json`
- 输出：`result/sc1/`（`case_*_signals.json`、`sc1_plots.png`、`sc1_quantitative.json`）

设备可通过环境变量覆盖，例如：`SC1_LLM_DEVICE=cuda:0`、`SC1_NLI_DEVICE=cuda:1`（多卡时）。

## 安全说明

请勿将 `guide/api_key.txt` 或任何密钥提交到 Git；仓库已用 `.gitignore` 排除该文件。大型第三方目录 `tools/Auto-claude-code-research-in-sleep/` 与二进制 `tools/aris` 默认忽略，需在本地单独克隆或下载。

## 文档

- 环境与服务器：`guide/试验环境与基本要求.md`
- SC1 计划：`plan/sc1_plan.md`
- SC1 执行细节：`plan/sc1_execution_brief.md`
