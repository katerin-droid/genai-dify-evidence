# 评测数据说明

本目录用于课程资料问答的 30 题测试集、人工金标和对照实验记录。当前状态：**30 题、56 条证据、74 条陈述级金标已填写并标记为 `ready`**，来源是本仓库 `materials/` 下的自建课程讲义（不是学校官方课件）。金标先逐条对照证据原文校验，再由刘英超人工抽查 10 条（`annotator=刘英超（抽查 10/74）`）。

真实实验已于 2026-11-11 完成：改进版（Dify + `/verify`）30 题全部成功，汇总见 `results.csv` / `runs.csv`，分析见 `docs/experiment-report.md`。baseline 组仅缺人工标注。

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
| `annotator` | 标注人缩写 |
| `annotated_at` | ISO 日期，例如 `2026-11-10` |
| `notes` | 判断理由、冲突点、歧义说明 |

**关于四态对齐：** 核验服务有四个状态，但 `verification_failed` 表示系统异常，不是人工语义判断。人工金标只使用 `supported / partially_supported / unsupported`；`verification_failed` 只出现在 `results.csv` 的 `overall_status/claim_status` 中，并在统计时单独计为系统失败，不能算作“缺乏依据”。

建议至少 10 题由两人独立标注，记录分歧后再合并；分歧题不要强行统一，保留 `notes`。

## 5. 指标口径

以陈述级为主，全部基于 `results.csv` 与 `gold_labels.csv` 的连接结果：

- **核验标签准确率** = 系统 `claim_status` 与人工 `gold_status` 一致的陈述数 / 已标注陈述总数。
- **无依据陈述识别召回率** = 正确判为 `unsupported` 的人工 `unsupported` 陈述数 / 人工 `unsupported` 陈述总数。
- **无答案问题识别召回率** = 正确判为 `unsupported`（或 `unsupported/no_evidence`）的 `no_answer` 题数 / `no_answer` 题总数。
- **有依据陈述误报率** = 被系统判为 `unsupported` 的人工 `supported` 陈述数 / 人工 `supported` 陈述总数。
- **平均响应时间** = 从提交问题到核验结果返回的耗时均值；建议同时记录 P50/P95。
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
