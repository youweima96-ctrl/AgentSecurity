# AgentSecurity（Git / GitHub 根目录）

远程仓库：**https://github.com/youweima96-ctrl/AgentSecurity**

工作区上级说明见 **`../README.md`**。论文与过程文档见 **`../local/`**（不随本仓库同步）。

## 目录一览（同步到 GitHub 的部分）

```
repo/
├── src/sc1/              # SC1：语义熵 H(t) + 嵌入漂移 D(t)
├── data/sc1/             # 合成对话 JSON
├── result/sc1/           # SC1 运行输出（可提交小结果；大体积极地忽略）
├── result/0410/          # 仅 README，指向 ../local/result/0410/
├── paper/                # 仅 README，指向 ../local/paper/
├── plan/                 # 仅 README，指向 ../local/plan/
├── guide/                # 试验环境与基本要求（勿提交 api_key.txt）
├── script/               # 脚本与说明
├── tools/skill/          # 小型 skill（如 readpaper）
├── requirements-sc1.txt
└── README.md
```

## SC1

```bash
conda activate agentsecurity
pip install -r requirements-sc1.txt
cd /path/to/agentsecurity/repo
export PYTHONPATH=src
python -m sc1
```

- 对话：`data/sc1/conversations/*.json`
- 输出：`result/sc1/`
- 设备：默认 `SC1_*_DEVICE=auto`（CUDA → MPS → CPU）；也可显式指定 `SC1_LLM_DEVICE` 等（见 `src/sc1/config.py`）。
- 无本地 8B 时：`SC1_LLM_BACKEND=openai` 且设置 `SC1_OPENAI_API_KEY`（或 `OPENAI_API_KEY`），`SC1_LLM_MODEL` 填 API 模型名；可选 `SC1_OPENAI_BASE_URL`。

### SC1-ABC（大改版一键批跑）

```bash
cd /path/to/agentsecurity/repo
conda activate agentsecurity
bash script/run_sc1_abc_batch.sh --gpu 0 --max-new 96 --samples 8 --repeats 2
```

- 输出目录：`result/sc1_abc_<mmdd>/`
- 自动生成：`summary_legacy.txt`、`summary_abc.txt`、`aggregate_results_abc.json`
- 关键可调项（可做矩阵批跑）：
  - `--temps`：温度列表（逗号分隔）
  - `--modes`：`hybrid,nli_entropy_norm,embed_dispersion,...`
  - `--thresholds`：主阈值列表（逗号分隔）
  - `--repeats`：每个组合重复次数
  - `--samples`：每轮采样数（建议 6~8）
  - `--cases`：自定义 case 文件列表（逗号分隔，默认 A/B/C）

## 安全

勿提交 `guide/api_key.txt` 及任何密钥。

## Git 远程

```bash
git remote add origin https://github.com/youweima96-ctrl/AgentSecurity.git
# 若已存在：git remote set-url origin https://github.com/youweima96-ctrl/AgentSecurity.git
git branch -M main
git push -u origin main
```
