# 对照实验分析报告（2026-11-11）

> 状态：改进版结果已由真实运行产生并落库；baseline 为**配对分析**（复用同次生成的答案，不额外调用模型），逐题数据见 `evaluation/baseline_answers.csv`、`evaluation/improved_responses.jsonl`。
> 数据来源：`evaluation/results.csv`、`evaluation/runs.csv`（由 `evaluation/build_results.py` 从 `evaluation/private/` 的原始响应汇总，原始响应不入库，脱敏副本已交付）。
> 配置说明：下表是 **2026-11-11 跑数时**的状态（版本 #3–#5、`top_k=5`、Markdown 原文入库）。2026-11-12 起线上为版本 #9（`top_k=8`、材料换成纯文本预处理版），只做了抽题验证，**本报告全部指标未重跑**，引用时请勿与 #9 配置混用。

## 1. 实验目的

验证「Dify 课程问答 + 自研 `/verify` 证据核验」相对「Dify 原样问答」是否能：

1. 在答案之外给出可核查的逐条陈述状态；
2. 识别课程资料未覆盖的问题，而不是用模型常识补答；
3. 在合理延迟内完成端到端问答。

## 2. 实验环境

| 项 | 值 |
|---|---|
| Dify 版本 | 1.19.0（官方源码，未改动） |
| 应用 | 课程问答证据核验（`advanced-chat`，已发布版本 #3） |
| 知识库 | `genai-course-vector-v2`，6 份自建讲义，高质量索引 |
| Embedding | 硅基流动 bge-m3（免费额度） |
| 生成模型（Dify LLM 节点） | deepseek-flash（`langgenius/deepseek:0.0.26`） |
| 核验模型（FastAPI `/verify`） | deepseek-chat（服务端 `DEEPSEEK_MODEL` 指定；修复前 max_tokens 偏小导致 6 题截断） |
| 检索参数 | top_k = 5，无分数阈值，重排 BAAI/bge-reranker-v2-m3 |
| 工作流 | 用户输入 → 知识检索 → 证据裁剪 → LLM → JSON 转义 → `/verify` → 直接回复 |
| 核验服务 | 自研 FastAPI，`VERIFIER_MODE=deepseek` |
| 云端部署 | `113.44.227.132`，commit `5b1bb0b4d5ae2b95204a283c6ecd067c1f8708c7` |
| 提问入口 | 服务端代理 `POST /api/chat`，blocking 模式，每题独立会话 |

## 3. 测试集

30 题，分四类；人工金标 74 条陈述（66 supported / 8 unsupported）。

| 类型 | 题数 | 题号 |
|---|---:|---|
| 明确有答案 `answerable` | 8 | Q01–Q08 |
| 需要多段证据 `multi_evidence` | 8 | Q09–Q16 |
| 资料没有答案 `no_answer` | 8 | Q17–Q24 |
| 资料矛盾或歧义 `ambiguous` | 6 | Q25–Q30 |

## 4. 改进版（Dify + `/verify`）结果

### 4.1 运行概况

| 指标 | 值 |
|---|---|
| 完成核验题数 | **30 / 30**（最终合并样本；其中 24 题来自 `0e845fe` 本地批次，6 题为修复后 `5b1bb0b` 云端补跑，未做同版本全量重跑） |
| 整体状态分布 | supported 18、partially_supported 12、unsupported 0 |
| 输出陈述总数 | 103 条（supported 89、partially 7、unsupported 7） |
| 平均 / 中位响应时间 | **12.87 s / 13.61 s**（按 30 个不同题各计一次，取每题首条陈述耗时） |
| P95 / 最长 / 最短 | 23.62 s（最近秩法）/ 24.33 s / 4.68 s |
| 模型调用 | 每题 1 次生成 + 1 次核验，无重复调用 |

### 4.2 逐题结果

| 题号 | 类别 | 陈述数 | 整体状态 | 非 supported 陈述 | 耗时 |
|---|---|---:|---|---:|---:|
| Q01 | answerable | 5 | supported | 0 | 13.0s |
| Q02 | answerable | 3 | supported | 0 | 7.6s |
| Q03 | answerable | 2 | supported | 0 | 11.0s |
| Q04 | answerable | 2 | supported | 0 | 6.5s |
| Q05 | answerable | 4 | supported | 0 | 8.4s |
| Q06 | answerable | 3 | supported | 0 | 5.7s |
| Q07 | answerable | 4 | partially_supported | 1 | 18.1s |
| Q08 | answerable | 2 | supported | 0 | 8.9s |
| Q09 | multi_evidence | 3 | supported | 0 | 6.2s |
| Q10 | multi_evidence | 5 | supported | 0 | 5.3s |
| Q11 | multi_evidence | 4 | supported | 0 | 14.3s |
| Q12 | multi_evidence | 4 | supported | 0 | 19.3s |
| Q13 | multi_evidence | 3 | supported | 0 | 21.6s |
| Q14 | multi_evidence | 3 | supported | 0 | 16.5s |
| Q15 | multi_evidence | 4 | supported | 0 | 14.3s |
| Q16 | multi_evidence | 3 | partially_supported | 1 | 17.7s |
| Q17 | no_answer | 4 | supported | 0 | 5.1s |
| Q18 | no_answer | 2 | partially_supported | 1 | 23.6s |
| Q19 | no_answer | 2 | supported | 0 | 4.7s |
| Q20 | no_answer | 4 | partially_supported | 2 | 11.5s |
| Q21 | no_answer | 4 | partially_supported | 1 | 24.3s |
| Q22 | no_answer | 3 | partially_supported | 1 | 14.8s |
| Q23 | no_answer | 5 | supported | 0 | 6.7s |
| Q24 | no_answer | 2 | partially_supported | 2 | 15.0s |
| Q25 | ambiguous | 3 | partially_supported | 1 | 16.0s |
| Q26 | ambiguous | 4 | supported | 0 | 7.5s |
| Q27 | ambiguous | 5 | partially_supported | 1 | 20.6s |
| Q28 | ambiguous | 5 | partially_supported | 1 | 16.3s |
| Q29 | ambiguous | 3 | partially_supported | 1 | 7.6s |
| Q30 | ambiguous | 3 | partially_supported | 1 | 17.9s |

### 4.3 陈述级与人工金标的一致性

对齐方法：同题内按字符二元组相似度取最佳金标，相似度 < 0.35 记为未对齐、不计入分母。103 条输出中 **58 条对齐（56.3%）、45 条未对齐（43.7%）**，未对齐样本不在下方任何比例的分母内。

按口径 A，`no_answer` 题不参与陈述级一致率，改用「是否明确声明资料未覆盖」单独统计（见 4.4）。

| 类别 | 陈述数 | 对齐数 | 与金标一致率 |
|---|---:|---:|---:|
| answerable | 25 | 13 | **100%** |
| multi_evidence | 29 | 18 | **100%** |
| ambiguous | 23 | 13 | 84.6%（11/13） |
| **语义类合计** | 77 | 44 | **95.5%**（42/44） |
| no_answer | 26 | 14 | 不参与（见 4.4） |

不一致的 2 条：

| 输出陈述 | 系统判定 | 人工金标 | 说明 |
|---|---|---|---|
| Q25-S2 | unsupported | supported | 讲义并列狭义/广义定义，模型取的片段只覆盖其中一种，判定偏严 |
| Q27-S4 | partially_supported | supported | 同上，单段证据即可支撑，模型要求了跨段支撑 |

**这个 95.5% 的适用范围必须限定**：进入分母的 44 条人工金标**全部是 supported**（人工侧 66 supported / 8 unsupported 中，语义类对齐到的都是 supported）。也就是说，一个“永远输出 supported”的核验器在这个子集上能拿到 44/44。因此 95.5% 只能说明**在有据可依的陈述上不会误杀**，不能作为综合分类性能，也不能证明对 unsupported / partially_supported 的区分能力。

要衡量区分能力，需要人工逐条构造负例（故意让回答编造、或使用超出资料的提问）。本实验的 no_answer 类 8 题已提供该类证据，但现有四态输出没有「资料未覆盖」态，见 4.4。

### 4.3.1 可独立复算的数值

以下数值均可由 `evaluation/results.csv` 直接复算（每题单次耗时计一次，同题多条陈述不重复计权）：

| 项 | 值 |
|---|---|
| 不同题数 | 30 |
| 整体状态 | supported 18、partially_supported 12 |
| 陈述状态 | supported 89、partially_supported 7、unsupported 7（合计 103） |
| 平均耗时 | 12.8736 s |
| 中位数（常规中位数算法） | 13.611 s |
| 最短 / 最长 | 4.684 s / 24.325 s |
| P95（最近秩法，第 29 个值） | 23.622 s |
| 语义类已对齐子集一致率 | 42 / 44 = 95.45% |

### 4.4 无答案题：口径 A（已采用）

现有四态（supported / partially / unsupported / verification_failed）缺少「资料未覆盖」态：核验服务判断的是「这条陈述是否被证据支持」，而“资料里没有 X”这句话本身**被证据支持**（讲义确实写了“不包含 X”）；人工金标判断的是「该问题在课程资料中是否有答案」。两套口径不同，直接比较会得出 21.4% 这种误导性数字。

**采用口径 A**：`no_answer` 类题只统计「回答是否明确声明资料未覆盖」，不进入陈述级一致率分母。

| 题号 | 整体状态 | 回答是否明确声明未覆盖 | 是否用模型常识补答 |
|---|---|---|---|
| Q17 | supported | 是（“资料中没有相关内容”） | 否 |
| Q18 | partially_supported | 是（“资料中没有……推导内容”） | 否 |
| Q19 | supported | 是（“资料中没有……具体结构内容”） | 否 |
| Q20 | partially_supported | 是（“资料未提供……也未提及”） | 否 |
| Q21 | partially_supported | 是（“资料中没有给出……实验数据”） | 否 |
| Q22 | partially_supported | 是（“资料中没有关于……数值信息”） | 否 |
| Q23 | supported | 是（“没有。检索资料未给出……”） | 否 |
| Q24 | partially_supported | 是（“资料中没有给出……API 调用示例”） | 否 |

**结果：8 / 8 明确声明未覆盖，0 例用模型常识补答。**

## 5. 对照实验（baseline）

### 5.1 设计

- baseline：同一知识库、同一 LLM、同一 top_k，**不接** `/verify`，只回原始答案。
- improved：本次已跑数据。
- 每题独立会话，避免多轮上下文污染。

### 5.2 数据来源

baseline 的「原始答案」直接取自本次运行 `response.answer` 字段——同一知识库、同一 top_k、同一 LLM，核验前原文，**未额外消耗 token 重跑**。

### 5.3 人工核对结果（30 题逐题对照课程原文）

| 检查项 | 结果 |
|---|---|
| 原始答案中含**凭空编造**（课程资料完全没有的数值/结论）的陈述 | **0 条** |
| 明确声明“资料未覆盖”的题 | 13 题（Q06、Q08、Q13、Q16–Q25 中相应题） |
| **本可回答却答“资料中没有”的漏答题** | **3 题（10%）**：Q06、Q08、Q13 |

漏答原因不是模型能力，而是**检索未命中**：这 3 题的相关段落没有被 top_k=5 召回到，模型只看到“不包含该内容”的片段，于是如实回答“资料没写”。人工金标显示这三题在讲义中确有答案（如 RLHF 三阶段分别为 SFT / 奖励模型 / PPO+KL）。

**关键局限**：改进版的核验模块对这 3 题全部判 `supported`——因为“检索到的片段里确实没写”是事实。**核验只能判断“答案是否忠于所给证据”，不能判断“证据是否检索充分”**，所以漏答不会被现有核验逻辑发现。

### 5.4 baseline 与 improved 的实质差别

两者答案文本完全相同（同一生成器），差别在于：

| 维度 | baseline | improved |
|---|---|---|
| 答案文本 | 相同 | 相同 |
| 逐条陈述状态 | 无 | 103 条，可逐条核查 |
| 引用定位（证据 ID + 原文片段） | 无（答案里只有模型自贴的 (E1) 标记，未经校验） | 由 verifier 校验并回填 citations |
| 漏答是否可见 | 不可见 | 不可见（同局限） |
| 系统异常与“缺乏依据”是否区分 | 不适用 | 区分（error_code 独立） |
| 平均响应 | 未单独计量（同链路减去核验） | 12.9 s |

## 6. 指标计算

| 指标 | 改进版 | baseline |
|---|---|---|
| 陈述级一致率（语义类，已对齐子集） | **95.5%**（42/44）——分母全为 supported 金标，见 4.3 的适用范围说明 | 不适用（无核验输出） |
| 有依据陈述误报率 | **2.3%**（对齐子集中人工标 supported 的陈述共 **43** 条，其中 1 条被判 unsupported：Q25-S2） | 不适用 |
| 无依据陈述识别召回率 | **不可计算**：人工核对后答案中无凭空编造陈述，正样本为 0；系统判出的 7 条 unsupported 均为“资料未覆盖”这类正确描述 | 同（0 条编造） |
| 无答案问题识别准确率（口径 A） | **100%**（8/8 明确声明未覆盖） | 13/13 声明未覆盖，其中 3 题属漏答 |
| 漏答率（本可回答却答“资料没有”） | **10%**（3/30） | **10%**（3/30，同一生成器） |
| 平均 / 中位响应时间 | 12.87 s / 13.61 s（P95 23.62 s） | **未单独计量**（核验耗时点未拆分，不做估算） |
| 系统失败率（最终合并样本） | 0%（30 题最终均成功）；修复前本地批次 30 题中 6 题失败（20%），未在同版本下全量重跑 | — |

## 7. 错误案例与修复

首轮本地运行 30 题中有 6 题 `verification_failed`：

| 题号 | 首轮错误码 | 原因 | 修复后 |
|---|---|---|---|
| Q16、Q21、Q23、Q25 | `incomplete_completion` | 核验输出被 4096 token 上限截断 | 云端补跑成功 |
| Q06 | `invalid_citations` | 引用与证据 ID 不匹配 | 补跑成功 |
| Q09 | `claim_verification_failed` | 核验模型未按 JSON 结构返回 | 补跑成功 |

修复：`DEEPSEEK_MAX_TOKENS` 默认 4096 → 8192（可在 `.env` 覆盖）。云端以 commit `5b1bb0b` 补跑这 6 题，**6 题全部成功**。因此最终合并样本（24 题旧批次 + 6 题补跑）30 题均成功；但这不等于“新版本下 30 题全量重跑的失败率为 0”，该结论需在部署后的稳定版本上整体重跑才能得出（受 token 成本限制，本次未做）。

另一处已修问题：Dify 直接回复会把 DeepSeek 的 `<think>` 推理块混入答案文本，已在 `/api/chat` 服务端剥离，不进入展示层。

## 8. 局限

1. 课程资料为自建 6 章讲义，**不是学校官方课件**；`no_answer` 题依据讲义“不覆盖”声明设计，换官方教材后需重新标注。
2. 陈述级对齐用文本相似度（阈值 0.35），**43.7% 的系统陈述（45/103）未对齐到任何金标**，这部分完全不计入一致率；人工核对本身也有偏差。
3. 人工金标 74 条中仅抽查 10 条做过二次核对，且**当时未逐条记录被抽查的 claim_id**，无法精确追溯，属标注流程缺陷；CSV 中 `annotator` 字段已如实区分“AI 辅助起草”与“因人抽查”。
4. `gold_labels.csv` 的 `gold_status` 记录的是**陈述是否被原文支持**，`questions.csv` 的 `category` 记录的是**问题在资料中是否可回答**，两者不是同一维度；`no_answer` 题的 8 条 unsupported 金标全部是“资料未覆盖”类元陈述，详见 4.4 与 `evaluation/README.md`。
5. 样本量 30 题，单次运行，未做重复实验，延迟受云端负载影响。
6. `ambiguous` 题只有 6 道，一致率 84.6% 的置信区间较宽。
7. 未做双人独立标注，未计算标注者一致性（Kappa）。
8. **核验不覆盖检索充分性**：3 道漏答题（Q06/Q08/Q13）全部被判 supported，因为“检索片段里确实没写”属实。要发现漏答需要额外的召回评估（另建标准答案匹配或提高 top_k 重跑）。
9. baseline 与 improved 共用同一生成器，答案文本完全相同，本实验只能说明“可审计性”的提升，不能说明“幻觉率下降”；逐题配对数据见 `evaluation/baseline_answers.csv`。
10. 核验耗时未单独计量，baseline 平均响应时间因此缺失。
11. 截图未保留浏览器 URL 栏与请求记录，单凭图片不能证明执行环境；真实接口证据以 `/api/chat` 返回的 `conversation_id` 与原始响应 JSON 为准。

## 9. 截图

全部来自云端 `http://113.44.227.132/` 的真实接口（真实问答模式，非示例模式），2026-11-11 由刘英超在联想浏览器中手动作答并截取，存放于 `artifacts/ui/cloud/`（该目录被 `.gitignore` 忽略，不入库）。

| 文件 | 内容 | 已知信息 |
|---|---|---|
| `cloud-01-home.png` | 首页大胖鱼欢迎界面 | 顶部标签「真实问答与核验」，提示「已连接课程问答工作流，核验结果来自真实接口。」 |
| `cloud-02-waiting.png` | 等待动画一 | 提问「KV Cache 的作用和代价是什么？」，奶龙「先别急，让我看看……」 |
| `cloud-03-waiting-evidence.png` | 等待动画二 | 「正在核对证据……」 |
| `cloud-04-result-supported.png` | supported 结果页 | 「证据充足，奶龙认证！」，陈述 1/2 均有依据，含证据 ID E1 与原文折叠 |
| `cloud-05-serious.png` | 严肃模式 | 角色图片与趣味文案隐藏，状态与陈述数据不变 |

仍缺：`unsupported`（缺乏依据）与 `partially_supported`（咕咕嘎嘎）场景截图。30 题实验中未出现 `unsupported` 整体状态（模型对给定证据忠实、无凭空编造），需构造一条会触发缺依据判定的提问后再截；`partially_supported` 可用歧义题（如「Agent 的边界是什么？能调用工具就算 Agent 吗？」）触发。

## 10. 复现步骤

```powershell
# 1. 配置（Key 仅存本地 .env，不入库）
copy .env.example .env   # 填 DEEPSEEK_* 与 DIFY_*

# 2. 启动服务（必须显式 --env-file，服务本身不会自动读取 .env）
python -m uvicorn service.app.main:app --host 127.0.0.1 --port 8765 --env-file .env

# 3. 逐题运行（原始响应写 evaluation/private/raw，不入库）
python evaluation/run_questions.py --base-url http://127.0.0.1:8765

# 4. 汇总为 results.csv / runs.csv 并打印指标
python evaluation/build_results.py

# 5. 跑测试
python -m pytest -q service/tests
```

本次云端补跑使用的是：

```powershell
python evaluation/run_questions.py --base-url http://113.44.227.132 `
  --ids Q06,Q09,Q16,Q21,Q23,Q25 --out evaluation/private/raw-cloud
```
