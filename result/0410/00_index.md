# paper/ 文献分析索引（2026-04-10）

分析方法：按 `tools/skill/readpaper.md` 第一性原理模板，每篇输出五节：Task / Challenge / Insight & Novelty / Potential Flaw / Motivation。

---

## 重命名对照


| 原文件名               | 新文件名                                                                |
| ------------------ | ------------------------------------------------------------------- |
| `agentfactory.pdf` | `AgentFactory_Self-Evolving_Subagents_arXiv2603.18000.pdf`          |
| `Crescendo.pdf`    | `Crescendo_Multi-Turn_Jailbreak_USENIX_Security_2025.pdf`           |
| `2602.22983v3.pdf` | `CC-BOS_Classical_Chinese_Jailbreak_ICLR2026_arXiv2602.22983v3.pdf` |
| `2603.08234v1.pdf` | `Continuation_Triggered_Jailbreak_Mechanism_arXiv2603.08234v1.pdf`  |
| `2603.20161v1.pdf` | `Semantic_Token_Clustering_Uncertainty_arXiv2603.20161v1.pdf`       |
| `2603.18620v1.pdf` | `LSE_Learning_to_Self-Evolve_RL_TestTime_arXiv2603.18620v1.pdf`     |


---

## 五篇论文一览


| 论文                                   | 核心问题（一句话）                                             | 主要创新层     | 与 agentsecurity 相关性                     |
| ------------------------------------ | ----------------------------------------------------- | --------- | --------------------------------------- |
| **AgentFactory**                     | 让 LLM agent 把成功执行轨迹固化为可执行子智能体代码并持续积累                  | 方法层 + 架构层 | **高**：可执行能力积累 → 有害能力积累风险、跨系统信任边界        |
| **Crescendo**                        | 用「看似良性的多轮渐进对话」完全黑盒地越狱安全对齐模型                           | 策略层       | **高**：多轮 × 工具调用场景的直接攻击面                 |
| **CC-BOS**                           | 用文言文语境 + 八维策略空间 + 果蝇优化自动生成黑盒越狱提示                      | 方法层 + 架构层 | **高**：对齐覆盖不均的语言/编码变体攻击面                 |
| **Continuation-Triggered Jailbreak** | 在注意力头层面解释为何把续写后缀移到提示边界外会触发越狱                          | 方法层（机制分析） | **中高**：安全头定位 → 推理时可控安全增强可能性             |
| **STC**                              | 用离线 embedding 聚类聚合同义 token 概率，实现单次低开销不确定性量化           | 方法层 + 效率  | **中**：轻量级「是否可信」监控，适合嵌入 agent 运行时        |
| **LSE**                              | 用 RL（改进量奖励 + UCB 树搜索）显式训练「如何改 prompt 才能提升下游表现」这一自进化技能 | 方法层 + 架构层 | **中高**：自进化策略可被对抗性训练 → 恶意自进化 / 绕过对齐的新攻击面 |


---

## 值得深挖的研究方向（跨篇综合）


| 研究点                                  | 涉及论文                   |
| ------------------------------------ | ---------------------- |
| 可执行子智能体的意图级安全审查（防止有害能力固化）            | AgentFactory           |
| 多轮 × 工具调用 agent 场景下的 Crescendo 变体与检测 | Crescendo              |
| 「对齐覆盖度地图」：自动检测哪些语言/编码变体存在理解-对齐不对称    | CC-BOS                 |
| 基于安全头定位的推理时可控安全放大                    | Continuation-Triggered |
| STC 作为 agent 工具调用决策的轻量可靠性监控器         | STC                    |
| 被恶意训练的自进化策略的检测与限制（有害自进化）             | LSE                    |


