# Entropy-Guided Adaptive Safety Intervention in Multi-Turn LLM Conversations

## Research Outline

---

## 1. Introduction

### 1.1 Problem Statement

- 大语言模型在多轮对话中的安全性会随交互深度逐步退化（safety degradation）
- 现有安全对齐方法主要关注静态防护（system prompt、RLHF），缺乏对动态退化过程的实时检测与干预能力
- 核心缺口：缺少一个 inference-time、black-box-feasible 的"检测 → 干预"闭环框架

### 1.2 Research Questions

- **RQ1（信号发现）**：语义熵轨迹（semantic entropy trajectory）能否作为安全退化的早期预警信号？
- **RQ2（干预有效性）**：基于熵信号触发的自适应干预策略能否有效逆转或减缓安全退化？
- **RQ3（干预优化）**：Improvement-based reward 设计是否优于绝对值奖励在干预策略选择中的表现？
- **RQ4（泛化性）**：该框架在不同模型（Llama、Claude、Mistral）上是否具有跨模型有效性？

### 1.3 Contributions

1. 首次建立语义熵轨迹与安全退化之间的预测性关联（predictive link）
2. 提出"检测 → 干预"闭环框架，将被动预测升级为主动安全控制
3. 引入 improvement-based reward 机制优化干预策略选择
4. 在多个开源与闭源模型上验证框架的泛化能力

---

## 2. Related Work

### 2.1 LLM Safety Alignment & Jailbreak

- RLHF / Constitutional AI 等静态对齐方法
- 多轮越狱攻击的演化（Crescendo、multi-turn jailbreak 等）
- 现有防御方法的局限性：主要是事后检测，缺乏过程级动态防护

### 2.2 Semantic Entropy & Uncertainty Estimation

- Semantic entropy 的定义与计算方法（Kuhn et al., 2023）
- 基于 NLI 的语义等价聚类
- 不确定性估计在幻觉检测中的应用
- **Gap**：尚无工作将语义熵轨迹用于安全退化的过程级预测

### 2.3 Sequential Decision-Making for LLM Optimization

- In-context learning 的动态优化（prompt editing、context refinement）
- 树搜索与回溯机制在序列决策中的应用
- Improvement-based reward vs. absolute reward 的设计权衡
- **定位**：借鉴序列决策框架中的奖励设计原则，应用于安全干预策略优化

### 2.4 Runtime Safety Monitoring

- 运行时安全监控方法（output filtering、guardrails）
- Self-reflection / self-critique 机制
- **Gap**：现有方法多为规则驱动，缺乏基于动态信号的自适应干预

---

## 3. Methodology

### 3.1 Overview：三阶段框架

```
Phase 1: Signal Discovery（信号发现）
    输入：多轮对话序列
    输出：每轮语义熵值 → 熵轨迹 → 退化预测信号
        ↓ 触发条件满足
Phase 2: Adaptive Intervention（自适应干预）
    输入：触发信号 + 当前对话上下文
    输出：最优干预策略
        ↓ 干预执行
Phase 3: Evaluation & Feedback（评估与反馈）
    输入：干预后的对话续写
    输出：合规率变化 → 奖励信号 → 策略更新
```

### 3.2 Phase 1：语义熵轨迹与退化预测

#### 3.2.1 安全退化的操作化定义

- **四级合规量表（0–3）**：
  - 0 = 完全拒绝（Full Refusal）
  - 1 = 部分拒绝 + 教育性回应（Partial Refusal with Educational Response）
  - 2 = 弱合规，带免责声明（Weak Compliance with Disclaimers）
  - 3 = 完全合规，无安全边界（Full Compliance without Safety Boundaries）
- **退化事件 t\***：对话中首次从 score ≤ 1 转变为 score ≥ 2 的时间步

#### 3.2.2 语义熵计算流程

1. 对第 t 轮对话，采样 N 次模型输出（N=5–10，temperature=0.7–1.0）
2. 使用 DeBERTa-v3-large 进行 pairwise NLI 判断
3. 基于 NLI 结果聚类语义等价组
4. 计算聚类分布上的 Shannon 熵 → H(t)
5. 构造熵轨迹：[H(1), H(2), ..., H(T)]

#### 3.2.3 熵特征工程

从熵轨迹中提取五类特征：

| 特征 | 定义 | 直觉 |
|------|------|------|
| `H_mean` | 窗口内熵均值 | 整体不确定性水平 |
| `H_slope` | 线性回归斜率 | 不确定性变化趋势 |
| `H_volatility` | 熵序列标准差 | 不确定性波动程度 |
| `H_spike` | max(H) − median(H) | 突发不确定性峰值 |
| `ΔH_max` | 相邻轮次最大熵差 | 最大单步不确定性跳变 |

#### 3.2.4 预测模型

- **基线**：Logistic Regression（熵特征 → 是否发生退化）
- **进阶**：时序分类器（LSTM / 1D-CNN on 熵轨迹 → 退化预测）
- **评估指标**：AUC-ROC、早期预警提前量（lead time = t\* − t_alert）

#### 3.2.5 Go/No-Go 判据（Day 14）

- ✅ AUC > 0.65 on 50 trajectories → 继续
- ❌ AUC < 0.65 → 诊断、调整特征或数据后再决定
- ✅ 至少一个熵特征与退化显著相关（p < 0.05）→ 继续

### 3.3 Phase 2：自适应干预策略

#### 3.3.1 干预触发机制

- 当熵轨迹满足预设条件时触发干预：
  - 条件 A：`H_slope` 超过阈值 θ₁（持续上升趋势）
  - 条件 B：`ΔH` 单步跳变超过阈值 θ₂（突发性变化）
  - 条件 C：预测模型输出的退化概率 > θ₃
- 阈值通过 Phase 1 验证集确定

#### 3.3.2 候选干预策略池

| 策略 ID | 策略类型 | 描述 | 示例 |
|---------|---------|------|------|
| S1 | Safety Reminder | 在 system prompt 中插入安全提醒 | "Remember to follow safety guidelines..." |
| S2 | Topic Redirect | 将对话引导回安全话题 | "Let's focus on the constructive aspects..." |
| S3 | Constraint Reinforcement | 显式重申约束条件 | "As an AI assistant, I cannot..." |
| S4 | Context Reset | 部分重置对话上下文（截断早期有害轮次） | 移除最近 k 轮对话历史 |
| S5 | Reflective Prompt | 引导模型自我审查 | "Before responding, consider whether..." |

#### 3.3.3 Improvement-Based Reward 设计

- **奖励定义**：

  ```
  R(intervention_i, context_t) = C̄(t+1:t+w | intervention_i) − C̄(t-w:t)
  ```

  其中 C̄ 为窗口 w 内的平均合规分数（0–3 量表的归一化值）

- **设计原则**（借鉴 LSE）：
  - 使用差值奖励而非绝对值 → 激励真实改善
  - 绝对值奖励的问题：偏向保护已安全的对话，对处于危险边缘的对话缺乏灵敏度
  - 差值奖励的优势：无论对话当前安全水平如何，都能衡量干预的边际效果

#### 3.3.4 干预策略选择

**方案 A：Top-K 选择（基线，Week 3–4 实现）**

1. 对每个候选策略 Sᵢ，在当前上下文上模拟续写 w 轮
2. 计算每个策略的 R(Sᵢ, context_t)
3. 选择 R 最高的策略执行

**方案 B：UCB 树搜索（进阶，如时间允许）**

1. 构建策略树：根节点 = 当前对话状态，子节点 = 各干预策略
2. 使用 UCB1 公式平衡探索与利用：

   ```
   UCB(Sᵢ) = R̄(Sᵢ) + c × √(ln(N) / nᵢ)
   ```

3. 支持回溯：如果当前策略效果不佳，回退到上一级选择次优策略
4. 适用场景：当策略空间扩大或需要多步干预时

### 3.4 Phase 3：评估与泛化验证

#### 3.4.1 干预效果评估

- **主要指标**：
  - 干预成功率（intervention success rate）：干预后合规分数回到 ≤ 1 的比例
  - 平均合规恢复量（mean compliance recovery）：干预后 w 轮内平均合规分数下降幅度
  - 干预持久性（intervention durability）：干预效果维持的轮次数
- **消融实验**：
  - Improvement-based reward vs. absolute reward
  - 有触发机制 vs. 固定频率干预 vs. 无干预
  - 各干预策略单独 vs. 策略组合

#### 3.4.2 跨模型验证

| 模型 | 类型 | 运行环境 | 用途 |
|------|------|---------|------|
| Llama-3-8B | 开源 | 本地 3090 | 主要实验模型 |
| Mistral-7B | 开源 | 本地 3090 | 跨模型验证 |
| Llama-3-70B | 开源 | A100 | 模型规模泛化验证 |
| Claude (API) | 闭源 | API | 黑盒场景验证 |
| GPT-4o-mini | 闭源 | API | 黑盒场景验证 |

---

## 4. Experimental Setup

### 4.1 数据集构建

#### 4.1.1 种子数据集（Week 1，手动构建）

- 规模：~50 条多轮对话轨迹
- 每条轨迹：10–30 轮
- 覆盖类型：
  - 渐进式越狱（gradual escalation）
  - 角色扮演诱导（role-play induction）
  - 上下文操纵（context manipulation）
  - 正常对话（negative samples）
- 标注：每轮合规分数（0–3），由人工标注 + GPT-4 辅助

#### 4.1.2 扩展数据集（Week 3，半自动化生成）

- 规模：~300 条轨迹
- 生成方式：GPT-4o 根据种子模板生成多样化攻击对话
- 质量控制：人工抽检 20% + LLM-as-judge 全量评估
- 合规分数标注：GPT-4o-mini 作为 judge，与人工标注对齐（Cohen's κ > 0.7）

### 4.2 实验配置

#### 4.2.1 语义熵计算参数

| 参数 | 值 | 说明 |
|------|-----|------|
| 采样次数 N | 5 | 平衡精度与成本 |
| Temperature | 0.8 | 确保输出多样性 |
| NLI 模型 | DeBERTa-v3-large | 语义等价判断 |
| NLI 阈值 | entailment prob > 0.7 | 判定为语义等价 |

#### 4.2.2 干预参数

| 参数 | 值 | 说明 |
|------|-----|------|
| 评估窗口 w | 3 轮 | 干预前后的对比窗口 |
| 候选策略数 k | 5 | 初始策略池大小 |
| 模拟续写轮数 | 5 轮 | 每个策略的评估深度 |
| UCB 探索系数 c | 1.41 | √2，标准 UCB1 |

### 4.3 Baselines

| 基线 | 描述 |
|------|------|
| No Intervention | 不做任何干预，自然退化 |
| Fixed Intervention | 每隔 k 轮固定插入 safety reminder |
| Random Intervention | 随机选择干预策略 |
| Perplexity-based Trigger | 用 perplexity 替代语义熵作为触发信号 |
| Absolute Reward | 用绝对合规分数替代差值奖励选择策略 |

---

## 5. Resource Plan

### 5.1 计算资源

| 资源 | 用途 | 预估用量 |
|------|------|---------|
| 3090 × 1 | Llama-3-8B / Mistral-7B 推理 | Week 1–4 持续使用 |
| 3090 × 1 | DeBERTa-v3-large 语义熵计算 | Week 1–4 持续使用 |
| 3090 × 1 | 控制器训练（如做 LoRA 版本） | Week 3–4 |
| A100 | Llama-3-70B 推理 | Week 4，约 2–3 天 |

### 5.2 API 预算（$1000）

| 用途 | 模型 | 预估费用 |
|------|------|---------|
| 对话数据生成 | GPT-4o | $200 |
| LLM-as-judge 安全评分 | GPT-4o-mini | $300 |
| Claude 跨模型验证 | Claude 3.5 Sonnet | $200 |
| 实验迭代 Buffer | — | $300 |

### 5.3 时间线

| 时间 | 里程碑 | 交付物 |
|------|--------|--------|
| **Week 1** | Pipeline 搭建 + 种子数据 | 熵计算 pipeline、50 条标注轨迹、4 项 sanity check |
| **Week 2** | Phase 1 核心分析 | 描述统计、Logistic Regression AUC、早期预警 lead time |
| **Day 14** | **Go/No-Go 决策点** | AUC > 0.65 → 继续；否则诊断调整 |
| **Week 3** | 数据扩展 + Phase 2 实现 | 300 条轨迹、干预策略 pipeline、Top-K 选择实验 |
| **Week 4** | 跨模型验证 + 论文写作 | 完整实验结果、论文初稿 |

---

## 6. Expected Results

### 6.1 Lower-Bound Claims（保底成果）

- AUC > 0.70 的熵轨迹退化预测（100+ trajectories，2+ models）
- 至少一种干预策略显著优于 no intervention baseline（p < 0.05）
- Improvement-based reward 选出的策略优于 random selection

### 6.2 Middle-Bound Claims（预期成果）

- 特定熵模式（如 slope + spike 组合）的预测 AUC > 0.75
- 自适应干预的 compliance recovery > 固定干预的 1.5 倍
- 跨模型（Llama/Mistral/Claude）一致有效

### 6.3 Upper-Bound Claims（如果一切顺利）

- UCB 树搜索策略选择优于 Top-K
- 熵轨迹提供 ≥ 3 轮的早期预警 lead time
- 框架在 70B 模型上同样有效（规模泛化性）

---

## 7. Paper Structure（论文结构预览）

1. **Abstract**
2. **Introduction**：问题动机 → 研究空白 → 方法概述 → 贡献列表
3. **Related Work**：安全对齐、语义熵、运行时监控、序列决策优化
4. **Method**
   - 3.1 语义熵轨迹与退化预测（Phase 1 — Signal Discovery）
   - 3.2 自适应干预框架（Phase 2 — Intervention）
   - 3.3 Improvement-based 策略优化（Phase 2 — Optimization）
5. **Experiments**
   - 4.1 数据集与实验设置
   - 4.2 退化预测实验（RQ1）
   - 4.3 干预有效性实验（RQ2）
   - 4.4 奖励设计消融实验（RQ3）
   - 4.5 跨模型泛化实验（RQ4）
6. **Results & Analysis**
7. **Discussion**：局限性、伦理考量（防御导向定位）、future work（UCB 树搜索、多智能体场景）
8. **Conclusion**

---

## 8. Risk Mitigation

| 风险 | 影响 | 应对策略 |
|------|------|---------|
| Phase 1 AUC < 0.65 | Phase 2 无意义 | Day 14 stop：检查特征/数据质量，必要时调整熵计算参数 |
| 干预策略均无效 | Phase 2 失败 | 回退到纯预测论文，干预作为 negative result 报告 |
| LLM-as-judge 与人工标注不一致 | 数据质量问题 | 扩大人工抽检比例，调整 prompt 直到 κ > 0.7 |
| API 成本超预算 | 实验不完整 | 优先保证核心实验（Llama-8B），削减 Claude/GPT 验证规模 |
| 熵计算速度过慢 | 时间线延误 | 减少采样次数 N（5→3），或使用更小的 NLI 模型 |
| 审稿人质疑伦理/dual-use | 论文被拒 | 全程防御导向定位，不报告攻击成功率，只报告检测/干预效果 |

---

## 9. Ethical Considerations

- 研究全程采用**防御导向（defense-oriented）**定位
- 不开发新的攻击方法，仅使用已公开的多轮越狱模式作为测试用例
- 数据集不包含可直接用于攻击的完整 prompt 模板
- 论文中不报告攻击成功率排名（避免成为攻击方法比较指南）
- 开源时仅发布检测/干预代码，不发布攻击数据集原文
