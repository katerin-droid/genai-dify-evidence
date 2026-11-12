# 评测数据说明

本目录用于课程资料问答的 30 题测试集、人工金标和对照实验记录。当前状态：**30 题、56 条证据、74 条陈述级金标已填写并标记为 `ready`**，来源是本仓库 `materials/` 下的自建课程讲义（不是学校官方课件）。

**标注过程如实说明**：74 条金标先由 AI 辅助起草并逐条对照证据原文校验，随后由刘英超抽查 10 条确认。**当时未逐条记录被抽查的 `claim_id`**，因此无法精确追溯哪 10 条经过人工二次核对，属标注流程缺陷；`annotator` 字段统一写为「刘英超（AI 辅助起草；抽查 10/74，未逐条复核）」，不把 74 条全部声明为人工独立完成。

真实实验已于 2026-11-11 完成：改进版（Dify + `/verify`）最终合并样本 30 题均成功（24 题旧批次 + 6 题修复后云端补跑），汇总见 `results.csv` / `runs.csv`，逐题脱敏明细见 `improved_responses.jsonl`、`paired_analysis.csv`、`baseline_answers.csv`，分析见 `docs/experiment-report.md`。baseline 为**配对分析**（复用同次生成的答案，不额外调用模型），不做独立重跑。

## 1. 数据与隐私约束

- 课程原文、教材 PDF/PPT、真实评估数据不提交到 Git。原始资料放在仓库根目录 `materials/`（已被 `.gitignore` 忽略）。
- 需要在本机保留的真实运行结果放在 `evaluation/private/`（已被 `.gitignore` 忽略）。
- 本目录只提交表头、脱敏后的题目/证据（在确认授权后）和可复现的实验配置。
- 不把 DeepSeek Key、Dify Key、管理员密码写入任何 CSV、Markdown、DSL 或截图。

## 2. 文件与用途

| 文件 | 粒度 | 用途 |
|---|---|---|
| `documents.csv` | 文档 | 登记课程资料；`relative_path` 指向被忽略的 `materials/`，并记录 SHA-256 便于复现 |
| `evidence.csv` | 证据片段 | 保存人工选取的原文证据；`content` 必须是原文连续片段，供人工标注和引用核对 |
| `questions.csv` | 题目 | 30 道题及题型配额；`evidence_ids` 指向 `evidence.csv` |
| `gold_labels.csv` | 陈述 | 人工金标；一题可有多条关键陈述，每条一个 `gold_status` |
| `runs.csv` | 实验批次 | 记录一次对照实验的知识库索引模式、模型、top_k、commit 等 |
| `results.csv` | 陈述/运行 | 记录系统输出与人工金标对照；支持陈述级指标 |
| `run_questions.py` | 脚本 | 逐题调用 `/api/chat`，原始响应写 `private/`，每题独立会话 |
| `build_results.py` | 脚本 | 汇总原始响应生成 `results.csv` / `runs.csv`，并打印指标 |
| `improved_responses.jsonl` | 题 | 改进版 30 题脱敏原始响应：完整 answer、逐条 claim 原文、status、evidence_ids、citations |
| `baseline_answers.csv` | 题 | baseline 的 30 题原始答案 + 人工核对结论（是否编造、是否漏答、复核人、日期） |
| `paired_analysis.csv` | 题 | baseline 与 improved 的逐题配对表，可直接复算状态分布与耗时 |

## 3. 题目分布

`questions.csv` 的 `category` 必须严格满足：

| category | 含义 | 数量 |
|---|---|---:|
| `answerable` | 明确有答案 | 8 |
| `multi_evidence` | 需要多段证据才能回答 | 8 |
| `no_answer` | 课程资料没有答案 | 8 |
| `ambiguous` | 资料矛盾或存在歧义 | 6 |
| **合计** | | **30** |

当前 `questions.csv` 已填入 `Q01`–`Q30` 的题干、参考答案、`evidence_ids`、`claim_ids`，`status=ready`。`gold_labels.csv` 的 74 条陈述中 66 条 `supported`、8 条 `unsupported`（对应 8 道 `no_answer` 题）。校验过程中修正了 3 处证据错配或证据不足（Q09、Q16-C3、Q28-C4）和 1 处结论超出原文（Q26-C1），随后人工抽查 10 条确认。

### 出题规则

- `answerable`：答案能在单一段落中直接找到；人工参考答案必须能在 `evidence.csv` 中找到对应原文。
- `multi_evidence`：答案需要合并两段或以上证据；不能靠单段直接回答。
- `no_answer`：课程资料确实没有相关内容；人工参考答案应明确写“资料未覆盖”，不要用模型常识补充。
- `ambiguous`：资料之间存在冲突、版本差异或表述含糊；人工需要记录冲突点和采用的判断口径。
- 不要用模型输出当标准答案；人工标签必须基于课程原文。
- 题干不要包含答案提示；不要从同一句话机械改写多题。

## 4. 人工金标

`gold_labels.csv` 一行一条关键陈述：

| 字段 | 说明 |
|---|---|
| `question_id` | 对应 `questions.csv` |
| `claim_id` | 例如 `Q01-C1`，题内唯一 |
| `claim_text` | 从参考答案中拆出的、可独立判断的事实性陈述 |
| `gold_status` | `supported` / `partially_supported` / `unsupported` |
| `evidence_ids` | 支持或反驳该陈述的 `evidence.csv` ID；无证据时留空 |
| `label_basis` | 标注依据：`evidence_support`（陈述是否被原文支持）或 `coverage_claim`（该陈述本身是“资料未覆盖”类元陈述） |
| `annotator` | 标注人缩写 |
| `annotated_at` | ISO 日期，例如 `2026-11-10` |
| `notes` | 判断理由、冲突点、歧义说明 |

**关于四态对齐：** 核验服务有四个状态，但 `verification_failed` 表示系统异常，不是人工语义判断。人工金标只使用 `supported / partially_supported / unsupported`；`verification_failed` 只出现在 `results.csv` 的 `overall_status/claim_status` 中，并在统计时单独计为系统失败，不能算作“缺乏依据”。

**关于两个维度不能混用（重要）：**

- `questions.csv` 的 `category` 记录的是**问题在资料中是否可回答**（`answerable / multi_evidence / no_answer / ambiguous`）；
- `gold_labels.csv` 的 `gold_status` 记录的是**该条陈述是否被原文证据支持**。

这两者不是一回事。8 条 `unsupported` 金标全部是 `Q17-C1`–`Q24-C1`，内容形如“本资料没有给出……的数学推导”——它们描述的是**资料的覆盖范围**，无法由“支持该主题的原文”来支持，因此标为 `unsupported`，并用 `label_basis=coverage_claim` 显式区分。它们**不代表答案编造**：这 8 道 `no_answer` 题的回答都正确声明了资料未覆盖。

因此统计时按口径 A 处理：`no_answer` 类不进入陈述级一致率分母，只统计“是否明确声明未覆盖”；`evidence_support` 类（66 条 supported）才参与陈述级一致率。这样既不篡改标签，也不把两种概念混在一个比例里。

当前 74 条中 66 条 `evidence_support / supported`、8 条 `coverage_claim / unsupported`，**没有任何 `partially_supported` 金标**——因此系统输出的 `partially_supported` 在陈述级只能被判为“与金标不一致”，这是金标覆盖不足，需后续补充部分支持类金标。

建议至少 10 题由两人独立标注，记录分歧后再合并；分歧题不要强行统一，保留 `notes`。

## 5. 指标口径

以陈述级为主，全部基于 `results.csv` 与 `gold_labels.csv` 的连接结果。**所有比例必须写明分母**：

- **对齐**：同题内按字符二元组相似度取最佳金标，`sim >= 0.35` 记为对齐。本次 103 条系统陈述中 58 条对齐（56.3%）、45 条未对齐（43.7%）；未对齐的不进入任何一致率的分母。
- **陈述级一致率（语义类，口径 A）** = 系统 `claim_status` 与人工 `gold_status` 一致的已对齐陈述数 / 语义类（`answerable` + `multi_evidence` + `ambiguous`）已对齐陈述数 = 42/44 = **95.45%**。分母 44 条金标全为 `supported`，因此该指标只反映“不误杀”，不反映负例区分能力。
- **有依据陈述误报率** = 系统判为 `unsupported` 的已对齐 `supported` 金标数 / 已对齐 `supported` 金标数 = 1/43 = **2.33%**（唯一一例 Q25-S2）。
- **无依据陈述识别召回率** = 正确判为 `unsupported` 的 `coverage_claim` 金标数 / `coverage_claim` 金标数。本实验**不做该统计**：口径 A 下 `coverage_claim` 不参与陈述级指标；且人工核对后答案中无凭空编造陈述，正样本为 0。
- **无答案问题识别准确率** = 明确声明“资料未覆盖”的 `no_answer` 题数 / `no_answer` 题数 = 8/8 = **100%**。
- **平均响应时间** = 每题首条陈述的 `latency_ms` 均值（同题多条陈述不重复计权）= 12.8736 s；中位数 13.611 s；P95 按最近秩法取第 29 个值 = 23.622 s。
- `verification_failed` 不计入上述语义指标的分母，单独报告系统失败率与错误码分布。

`score` 字段当前没有定义；DeepSeek 核验响应不返回分值，留空即可，不要用 mock 的 `score=null` 当真实分数。

## 6. 对照实验

`runs.csv` 一行一次运行，`results.csv` 用 `run_id` 关联。至少两组：

- `baseline`：Dify 知识库问答，不做证据核验；
- `improved`：Dify 知识库问答 + HTTP 节点调用 `/verify`。

两组必须使用同一知识库、同一 LLM、同一 `top_k`、尽量一致的生成参数；测试时每题使用独立会话，避免多轮上下文污染。

## 7. 课程资料现状

本机没有找到本课程的学校课件、讲义或教材，因此当前 `materials/` 下使用的是自建 6 章讲义（`01-第1章…` 到 `06-第6章…`，以及根目录 `课程资料包/` 的合订本 Markdown/DOCX/PDF）。这些材料：

- **不是学校官方课件**，报告中必须如实说明来源与自建性质；
- 每章都有“覆盖/不覆盖”范围声明，8 道 `no_answer` 题正是依据这些声明设计的；
- 第 3–6 章刻意保留了两种并列说法（RAG 范围、temperature、Agent 边界、RLHF/DPO、幻觉口径、RAG 评估指标），对应 6 道 `ambiguous` 题；
- 若之后拿到学校课件，应优先用官方材料替换或补充 `materials/`，重新核对证据原文并更新 `documents.csv` 的 SHA-256。

上传到云端 Dify、在报告中引用原文之前，需要确认这些自建材料的授权与引用方式。
