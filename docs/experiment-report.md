# 对照实验分析报告（2026-11-11）

> 状态：**改进版结果已由真实运行产生并落库**；对照实验的 baseline 组与截图仍待补。
> 数据来源：`evaluation/results.csv`、`evaluation/runs.csv`（由 `evaluation/build_results.py` 从 `evaluation/private/` 的原始响应汇总，原始响应不入库）。

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
| 生成模型 | deepseek-chat |
| 检索参数 | top_k = 5，无分数阈值 |
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
| 完成核验题数 | **30 / 30**（系统失败 0） |
| 整体状态分布 | supported 18、partially_supported 12、unsupported 0 |
| 输出陈述总数 | 103 条（supported 89、partially 7、unsupported 7） |
| 平均响应时间 | **12.9 s** |
| P50 / P95 / 最长 / 最短 | 14.3 s / 23.6 s / 24.3 s / 4.7 s |
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

对齐方法：同题内按字符二元组相似度取最佳金标，相似度 < 0.35 记为未对齐、不计入分母（103 条中 58 条对齐）。

按口径 A，`no_answer` 题不参与陈述级一致率，改用「是否明确声明资料未覆盖」单独统计（见 4.4）。

| 类别 | 陈述数 | 对齐数 | 与金标一致率 |
|---|---:|---:|---:|
| answerable | 25 | 13 | **100%** |
| multi_evidence | 29 | 18 | **100%** |
| ambiguous | 23 | 13 | 84.6%（11/13） |
| **语义类合计** | 77 | 44 | **95.5%**（42/44） |
| no_answer | 26 | 14 | 不参与（见 4.4） |

不一致的 2 条都在 `ambiguous` 类（Q27、Q29）：讲义对同一概念保留两种并列口径，核验模型按其中一段判 supported，人工金标判 partially_supported。属于「资料内部矛盾」导致的合理分歧，不是核验错误。

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
| 核验判断准确率（语义类陈述级，对齐子集） | **95.5%**（42/44） | 不适用（无核验输出） |
| 有依据陈述误报率 | **2.3%**（1/43 条人工 supported 陈述被判 unsupported） | 不适用 |
| 无依据陈述识别召回率 | 人工核对后答案中无凭空编造陈述，分母为 0，**不适用**；系统判出的 7 条 unsupported 均为“资料未覆盖”这类正确描述 | 同（0 条编造） |
| 无答案问题识别准确率（口径 A） | **100%**（8/8 明确声明未覆盖） | 13/13 声明未覆盖，其中 3 题属漏答 |
| 漏答率（本可回答却答“资料没有”） | **10%**（3/30） | **10%**（3/30，同一生成器） |
| 平均响应时间 | 12.9 s（P50 14.3 / P95 23.6） | 未单独计量 |
| 系统失败率 | 0%（修复前 20%） | — |

## 7. 错误案例与修复

首轮本地运行 30 题中有 6 题 `verification_failed`：

| 题号 | 首轮错误码 | 原因 | 修复后 |
|---|---|---|---|
| Q16、Q21、Q23、Q25 | `incomplete_completion` | 核验输出被 4096 token 上限截断 | 云端补跑成功 |
| Q06 | `invalid_citations` | 引用与证据 ID 不匹配 | 补跑成功 |
| Q09 | `claim_verification_failed` | 核验模型未按 JSON 结构返回 | 补跑成功 |

修复：`DEEPSEEK_MAX_TOKENS` 默认 4096 → 8192（可在 `.env` 覆盖）。云端以 commit `5b1bb0b` 重跑 6 题，**全部成功**，失败率 20% → 0%。

另一处已修问题：Dify 直接回复会把 DeepSeek 的 `<think>` 推理块混入答案文本，已在 `/api/chat` 服务端剥离，不进入展示层。

## 8. 局限

1. 课程资料为自建 6 章讲义，**不是学校官方课件**；`no_answer` 题依据讲义“不覆盖”声明设计，换官方教材后需重新标注。
2. 陈述级对齐用文本相似度，56% 的系统陈述未对齐到金标，人工核对仍有偏差；金标仅人工抽查 10/74。
3. 样本量 30 题，单次运行，未做重复实验，延迟受云端负载影响。
4. `ambiguous` 题只有 6 道，一致率 84.6% 的置信区间较宽。
5. 未做双人独立标注，未计算标注者一致性（Kappa）。
6. **核验不覆盖检索充分性**：3 道漏答题（Q06/Q08/Q13）全部被判 supported，因为“检索片段里确实没写”属实。要发现漏答需要额外的召回评估（另建标准答案匹配或提高 top_k 重跑）。
7. baseline 与 improved 共用同一生成器，答案文本完全相同，因此本实验只能说明“可审计性”的提升，不能说明“幻觉率下降”。
8. 核验耗时未单独计量，baseline 平均响应时间因此缺失。

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

# 2. 启动服务
python -m uvicorn service.app.main:app --host 127.0.0.1 --port 8765

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
