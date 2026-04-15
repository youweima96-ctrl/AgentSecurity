# ARIS 常用 Skill 含义与运行说明

本文档面向本工作区使用 [Auto-claude-code-research-in-sleep](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep)（ARIS）时的**日常查阅**：说明常用 **Skill** 的含义，以及 **在 Cursor 中如何通过 `@` 引用 SKILL**。（本工作区**不包含 aris CLI**；若你需要等价能力，请自行安装上游发布或使用 Claude Code。）

Skill 源码与元数据（默认放在**工作区** `extern/tools/`，不同步 Git）位于：

`extern/tools/Auto-claude-code-research-in-sleep/skills/<skill-name>/SKILL.md`

若你仍克隆在 `repo/tools/` 下，则把下文路径中的 `extern/tools` 替换为 `repo/tools` 即可。

下文「Skill 名」对应目录名 `<skill-name>`。

---

## 1. 工作流总览（三条主线）

ARIS 将科研过程拆成可组合的工作流，常见串联关系如下：

```
Workflow 1  idea-discovery
    └─ research-lit → idea-creator → novelty-check → research-review → research-refine-pipeline
         （文献）      （脑暴）        （查新）         （深度审稿）      （方法细化 + 实验规划）

Workflow 1.5  experiment-bridge
    └─ 读取 refine-logs/EXPERIMENT_PLAN.md 等 → 实现代码 → 结合 run-experiment 部署与收结果

Workflow 2  auto-review-loop
    └─ 多轮：外部审稿（如 Codex）→ 修改 → 再审，直至达标或达最大轮数

Workflow 3  paper-writing
    └─ paper-plan → paper-figure → paper-write → paper-compile → auto-paper-improvement-loop

端到端（超大） research-pipeline
    └─ idea-discovery → 实现与实验 → auto-review-loop → 接近可投稿状态
```

**说明**：编排类 Skill 内部会用「子 Skill」；在 **Claude Code** 里表现为 `/子技能名`，在 **Cursor** 里需用 `@.../子技能/SKILL.md` 显式引用（见第 4 节）。

---

## 2. 常用 Skill 含义一览

### 2.1 编排级（一整条流水线）

| Skill 名 | 含义（一句话） |
|----------|------------------|
| **idea-discovery** | 从大致方向到可验证 idea：串联文献调研 → 脑暴 → 查新 → 审稿 → 方法细化与实验规划；产出如 `IDEA_REPORT.md`、`refine-logs/FINAL_PROPOSAL.md`、`refine-logs/EXPERIMENT_PLAN.md`。 |
| **experiment-bridge** | 在 idea 阶段与审稿阶段之间：根据实验计划实现代码、（可选）交叉模型审代码、部署 `run-experiment`、收集初步结果。 |
| **auto-review-loop** | 自主多轮研究审稿循环：通过 MCP 外部审稿 → 落地修改 → 再评，状态可写入 `REVIEW_STATE.json`、`AUTO_REVIEW.md`。 |
| **paper-writing** | 从叙事材料到论文目录：大纲 → 图表 → LaTeX 写作 → 编译 PDF → 自动润色循环。 |
| **research-pipeline** | 全流程：idea-discovery → 实现与跑实验 → auto-review-loop，面向「从方向到接近投稿」的端到端自动化。 |

### 2.2 idea-discovery 链路上的子 Skill

| Skill 名 | 含义（一句话） |
|----------|------------------|
| **research-lit** | 检索与梳理文献、相关工作，可结合 Web/arXiv/本地论文库或 Zotero/Obsidian MCP。 |
| **idea-creator** | 在给定方向下生成、排序可发表级研究点子。 |
| **novelty-check** | 对照近期文献检验点子是否已被覆盖。 |
| **research-review** | 通过 Codex MCP 调用外部强模型做深度、批判性审稿。 |
| **research-refine** | 把模糊方向收敛为更清晰的问题与方案表述（常与 experiment-plan 组合）。 |
| **research-refine-pipeline** | 一次串联：`research-refine` + `experiment-plan`，得到最终提案 + 实验路线图。 |
| **experiment-plan** | 把成熟方法/提案变成「主张—证据—运行顺序—算力」对齐的实验计划（常为 `refine-logs/EXPERIMENT_PLAN.md`）。 |

### 2.3 实验与写作常用子 Skill

| Skill 名 | 含义（一句话） |
|----------|------------------|
| **run-experiment** | 在本地/远程/Vast.ai/Modal 等环境部署并运行训练或实验（依赖项目 `CLAUDE.md` 中的环境说明）。 |
| **monitor-experiment** | 监控长时间实验进度与资源（与跑实验配合）。 |
| **paper-plan** | 由材料生成结构化论文大纲与主张—证据矩阵。 |
| **paper-figure** | 生成论文级图表与表格脚本。 |
| **paper-write** | 撰写 LaTeX 正文。 |
| **paper-compile** | 编译得到 PDF。 |
| **auto-paper-improvement-loop** | 对已有 `paper/` 目录做多轮审稿 → 修改 → 重编译。 |
| **analyze-results** | 分析实验日志与指标，支撑结论文本。 |
| **result-to-claim** | 把结果整理成可与论文主张对齐的表述。 |

### 2.4 其他（按需）

| Skill 名 | 含义（一句话） |
|----------|------------------|
| **rebuttal** | 辅助 rebuttal 与审稿意见逐条回应。 |
| **arxiv** | 与 arXiv 检索、元数据或下载流程相关的能力封装。 |
| **semantic-scholar** | 借助 Semantic Scholar 的文献检索与引用关系（若 skill 内配置了相应工具）。 |
| **research-wiki** | 维护研究笔记/wiki 式文档（依 SKILL 内说明使用）。 |
| **vast-gpu** / **serverless-modal** | 云 GPU（Vast / Modal）相关的创建与运行（常被 `run-experiment` 间接调用）。 |

### 2.5 目录变体（`skills/` 下）

除顶层各 Skill 外，仓库中还有 **`skills-codex`**、**`skills-codex-gemini-review`**、**`skills-codex-claude-review`** 等子目录，为**不同审稿/执行器组合**的同名 Skill 副本。日常优先使用**顶层** `skills/<name>/`；若文档要求固定审稿后端，再切换到对应子目录中的 `SKILL.md`。

另有 **`auto-review-loop-llm`**：用兼容 OpenAI API 的 MCP（如 `llm-chat`）替代 Codex 时的审稿循环变体。

---

## 3. Claude Code / 其它环境中的斜杠命令（对照用）

若你在 **Claude Code** 或自行安装的 **aris** 等 CLI 中使用 ARIS，Skill 的**逻辑**仍在 `SKILL.md`；加载方式为 **`/skill-name`**（与 `SKILL.md` 中 `name:` 一致），例如：

```text
/idea-discovery "智能体安全中的工具滥用风险"
/auto-review-loop "你的论文主题或范围"
```

具体以各 `SKILL.md` 为准。CLI 的执行器、环境变量与 `aris --help` 说明见上游仓库文档；**本工作区不内置 aris**。

外部审稿若走 **Codex MCP**，在 Cursor 中配置 `.cursor/mcp.json` 等（参见上游 [CURSOR_ADAPTATION](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/main/docs/CURSOR_ADAPTATION.md)）。

---

## 4. 在 Cursor 中使用（与 CLI 对照）

- **引用 Skill 文件**（路径相对本仓库根目录）：

```text
@extern/tools/Auto-claude-code-research-in-sleep/skills/auto-review-loop/SKILL.md

请按该 SKILL 执行，主题为「……」。
```

- **子流程**：SKILL 正文里的 `/research-lit` 等，在 Cursor 中应改为显式 `@extern/tools/Auto-claude-code-research-in-sleep/skills/research-lit/SKILL.md` 等，或分多轮会话按阶段执行。
- **需要 MCP 审稿**时：在 Cursor 中配置 `.cursor/mcp.json`（如 Codex 或 `llm-chat`），并在提示中说明使用的工具前缀（参见上游文档）。

---

## 5. 常见产出文件（便于接力）

| 文件或目录 | 典型用途 |
|------------|----------|
| `IDEA_REPORT.md` | idea-discovery 汇总 |
| `refine-logs/FINAL_PROPOSAL.md` | 方法提案定稿 |
| `refine-logs/EXPERIMENT_PLAN.md` | 实验路线图 |
| `AUTO_REVIEW.md`、`REVIEW_STATE.json` | auto-review-loop 日志与断点恢复 |
| `NARRATIVE_REPORT.md` | paper-writing 输入叙事材料 |
| `paper/` | LaTeX 与 PDF 输出目录 |

新开会话时 **`@` 上述文件 + 对应 SKILL** 即可续做。

---

## 6. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-04-10 | 初版：基于 ARIS `skills` 下 SKILL 元数据整理 |
| 2026-04-15 | 目录调整：`repo/` 为 Git 根；ARIS 放 `extern/tools/`；移除本工作区对 aris CLI 的依赖说明 |
