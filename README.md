# agentsecurity（Git 仓库根目录）

本目录即 **GitHub 同步根目录**；工作区上级说明见仓库外 `../README.md`。

智能体安全相关科研：环境说明、文献笔记、SC1 信号方向性验证代码等。

## 本仓库目录一览

```
repo/
├── src/sc1/           # SC1 Python 包（config / 采样 / 熵 / 漂移 / 可视化 / __main__）
├── data/sc1/          # 合成对话 JSON（Case A/B/C）
├── result/            # 实验输出（如 result/sc1、result/0410）
├── plan/              # 任务计划与执行书
├── guide/             # 环境说明、研究大纲（勿提交 api_key.txt）
├── paper/             # 论文 PDF
├── script/            # 脚本与说明
├── tools/skill/       # 随仓库同步的小型 skill（如 readpaper）
├── requirements-sc1.txt
└── README.md
```

上级工作区另有 **`extern/`**（大体积第三方，不同步），见 `../extern/README.md`。

## SC1（语义熵 + 嵌入漂移）

依赖见 `requirements-sc1.txt`。建议在 **GPU 服务器** 上运行（需下载 Llama-3-8B-Instruct、NLI、SimCSE）。

```bash
conda activate agentsecurity
pip install -r requirements-sc1.txt
cd /path/to/agentsecurity/repo
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

## GitHub 首次推送（本机未安装 `gh` 时需手动）

1. 在 GitHub 新建仓库（建议 **Private**），不要勾选「用 README 初始化」，记下 SSH 或 HTTPS 地址。  
2. 在本仓库根目录执行：

```bash
cd /path/to/agentsecurity/repo
git remote add origin git@github.com:<你的用户名>/<仓库名>.git
# 或 HTTPS：git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git branch -M main
git push -u origin main
```

3. 之后日常：`git pull` 再改代码 → `git add` / `git commit` → `git push`；过里程碑可 `git tag milestone/sc1-pass && git push --tags`。
