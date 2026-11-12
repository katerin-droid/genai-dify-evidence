# Dify Chatflow 工作流方案

状态：**已落地**。云端 Dify 1.19.0 已按本文创建应用「课程问答证据核验」，线上已发布版本 **#9**；`dify/workflow/chatflow-course-qa.yml` 是版本 #4 的导出（节点结构相同，检索参数与知识库绑定有差异，见第 15 节末尾）。第 15 节记录实际配置与实测输出，与本文前面的设计稿如有差异，以第 15 节为准。本文不包含任何密钥。

## 1. 目标与边界

目标链路（已实现）：

```text
用户输入
  → 知识检索（genai-course-vector-v2，top_k=8）
  → 代码执行（Evidence 裁剪）
  → LLM（deepseek-flash）
  → 代码执行（JSON 转义）
  → HTTP 请求（POST http://verifier:8000/verify）
  → 直接回复
```

边界：

- Dify 负责检索、生成答案、调用核验服务，并把结果交给 `POST /api/chat` 的调用方。
- FastAPI `/verify` 负责逐条陈述核验；Dify 不重新计算 `overall_status`，只透传。
- `/api/chat` 代理**已实现**（`service/app/dify.py` + `main.py`），负责拆分「LLM 文本」与「核验 JSON」，并把 `overall_status / claims / citations / error_code` 归一化后返回前端。
- 不在 Dify 里保存 DeepSeek Key、Dify 应用 Key 或任何密钥。

## 2. 前置条件

1. 云端 Dify 1.19.0 已可登录，已创建 Chatflow 应用。
2. 课程知识库已建立，且已用 10–20 个问题验证过检索召回。
3. Dify 的 DeepSeek 模型 provider 可用；embedding 模型可用（若使用高质量索引）。
4. `verifier` 与 Dify 在同一 `genai_integration` 网络；HTTP 节点能访问 `http://verifier:8000/verify`。
5. 已确认 HTTP 节点出站经过 `ssrf_proxy`，且白名单仍只放行 `172.30.80.10/32`。

## 3. 节点与变量

| 顺序 | 节点 | 类型 | 输入 | 输出 | 说明 |
|---:|---|---|---|---|---|
| 1 | Start | Start | `question`（text，必填） | `question` | 题面；测试时单轮，不把历史答案拼进题干 |
| 2 | Knowledge Retrieval | Knowledge Retrieval | `query = Start.question` | `result`（chunk 数组） | `top_k` 建议 3–5；记录索引模式与阈值 |
| 3 | Evidence Transform | Code | `result` | `evidence`（数组）、`evidence_json`（字符串）、`evidence_count` | 只保留 `id/content/source/page`，剥离 `score` 等字段 |
| 4 | LLM Answer | LLM | system prompt、`Start.question`、`result` | `answer`（text） | 仅依据检索片段回答；温度 0–0.3 |
| 5 | HTTP Request | HTTP Request | URL、headers、body | `verify_response`（body）、`status_code` | `POST`，JSON，超时 60s，不重试 |
| 6 | Result Adapter | Code | `verify_response`、`status_code`、`answer`、`evidence` | `overall_status`、`claims`、`error_code`、`verification_message` | 校验响应；异常映射为 `verification_failed` |
| 7 | End | End | `answer`、`overall_status`、`claims`、`evidence`、`error_code` | 最终输出 | 供 `/api/chat` 读取 |

如果当前 Dify 版本没有 Code 节点，不要直接把原始 `result` 塞进 HTTP 节点；应改用可用的变量聚合/模板能力，或把转换放到 FastAPI 侧新增适配层。直接传原始 chunk 会因 `extra="forbid"` 触发 422。

## 4. Evidence Transform：字段裁剪

核验服务的 `evidence` 只接受以下字段：

```json
{
  "id": "E1",
  "content": "证据原文",
  "source": "文档标题",
  "page": 12
}
```

规则：

- `id`：按检索顺序生成 `E1`、`E2`……，去重后连续编号；不要用随机 ID 或数据库主键。
- `content`：使用 chunk 的正文，不要拼接标题、分数或 Markdown 标记；不要静默截断。若单段超过 20000 字符，先调整分块，或在转换时拆成多条证据。
- `source`：优先 `title` / `metadata.document_name`；没有时用文档名，不要编造页码或章节。
- `page`：只有检索结果确实提供页码时才传；类型为正整数或非空字符串；没有就省略。
- 最多 50 条；建议 `top_k=3–5`，避免核验 prompt 过长。
- 不传 `score`、`document_id`、`metadata` 等额外字段；这些字段会导致 422。
- `content` 必须是最终传给核验服务的同一份文本；前端展示的引用必须能在这份文本中找到连续子串。

参考转换逻辑（Code 节点，Python 伪代码）：

```python
def build_evidence(chunks):
    evidence = []
    seen = set()
    for chunk in chunks:
        content = (chunk.get("content") or chunk.get("text") or "").strip()
        if not content or content in seen:
            continue
        seen.add(content)

        meta = chunk.get("metadata") or {}
        source = (
            chunk.get("title")
            or meta.get("document_name")
            or meta.get("source")
            or "unknown"
        )
        source = str(source)[:2000]

        item = {
            "id": f"E{len(evidence) + 1}",
            "content": content[:20000],
            "source": source,
        }

        page = meta.get("page", chunk.get("page"))
        if isinstance(page, int) and page >= 1:
            item["page"] = page
        elif isinstance(page, str) and page.strip():
            item["page"] = page.strip()[:128]

        evidence.append(item)
        if len(evidence) >= 50:
            break
    return evidence
```

注意：上面的 `content[:20000]` 只是兜底；如果发生截断，必须同时调整分块并在 `runs.csv` 记录，不能假装原文完整。

## 5. HTTP Request 节点

请求：

```http
POST http://verifier:8000/verify
Content-Type: application/json
```

Body 结构：

```json
{
  "question": "{{#start.question#}}",
  "answer": "{{#llm_answer.answer#}}",
  "evidence": "{{#evidence_transform.evidence#}}"
}
```

上面的 `evidence` 必须是**数组**，不是 JSON 字符串。若 Dify 只能提供字符串变量，改用不带引号的变量插入：

```json
{
  "question": "{{#start.question#}}",
  "answer": "{{#llm_answer.answer#}}",
  "evidence": {{#evidence_transform.evidence_json#}}
}
```

两种写法都必须在 HTTP 节点的“预览/测试”里确认最终请求体是合法 JSON。若控制台把数组转义成字符串，说明变量类型不对，应回到 Code 节点输出数组，而不是在 Dify 里手工拼字符串。

节点设置：

| 项 | 建议值 | 原因 |
|---|---|---|
| Method | POST | `/verify` 只接受 POST |
| Body | JSON | 不能发 form |
| Timeout | 60s | 大于 FastAPI 的 30s DeepSeek 超时 |
| Retries | 0 | 避免重复计费与重复核验 |
| SSL verify | 不适用（内网 HTTP） | 不要为了绕过证书校验关闭全局校验 |
| Output | `body`、`status_code` | 后续节点需要区分 HTTP 错误与业务失败 |

如果 HTTP 节点返回非 200，不要把它当成 `unsupported`；应进入系统异常分支。

## 6. Result Adapter：透传与异常映射

Adapter 需要做四件事：

1. `status_code != 200` → `overall_status=verification_failed`，`error_code=upstream_http_error`。
2. body 不是合法 JSON 或缺少 `overall_status/claims` → `verification_failed`，`error_code=invalid_upstream_response`。
3. 合法响应 → 原样透传 `overall_status`、`claims`、`evidence_count`、`error_code`、`message`；不要改写状态，不要重新聚合。
4. 把实际发送的 `evidence` 一并输出，供前端把 `evidence_id` 映射回 `source/page/content`。

异常映射：

| 上游情况 | Dify 输出 |
|---|---|
| HTTP 非 200 | `verification_failed` + `upstream_http_error` |
| 响应非 JSON | `verification_failed` + `invalid_upstream_response` |
| 缺少 `overall_status` 或 `claims` | `verification_failed` + `invalid_upstream_response` |
| HTTP 节点超时 | `verification_failed` + `upstream_timeout` |
| 网络不可达 | `verification_failed` + `upstream_unavailable` |
| 正常 `unsupported/no_evidence` | 保持 `unsupported`，不要改成系统失败 |
| 正常 `verification_failed/*` | 保持 `verification_failed` 与原始 `error_code` |

`verification_failed` 与 `unsupported` 必须在最终输出里保持区分：前者是系统异常，后者是“资料不足以支持”。前端不能把前者显示成“有依据”或“缺乏依据”。

## 7. End 节点输出

End 节点至少输出：

| 输出变量 | 类型 | 说明 |
|---|---|---|
| `answer` | string | LLM 原始答案 |
| `overall_status` | string | 四态之一 |
| `claims` | array/object | 核验服务返回的 `claims` |
| `evidence` | array | 实际发送给核验服务的证据 |
| `error_code` | string/null | 系统错误码 |
| `verification_message` | string | 面向用户的核验说明 |

Dify Chatflow 的 `/v1/chat-messages` 是否把这些结构化输出原样返回，需要在 1.19.0 控制台实测。若只返回 `answer` 文本，有两个备选方案：

1. **MVP**：End 节点把结构化结果序列化为 JSON 放进 `answer`，`/api/chat` 解析后返回前端；缺点是答案不再是纯文本。
2. **结构化方案**：改用 Dify 的 workflow run API 或工作流运行详情接口读取 `outputs`；需要确认 Chatflow 是否支持、以及 `conversation_id` 如何维护。

这是本方案最大的待确认点，不要在未实测前假设 `/v1/chat-messages` 会返回 `claims`。

## 8. 超时与 blocking 模式

- MVP 使用 `response_mode: "blocking"`：一次请求返回完整答案和核验结果，前端实现简单。
- 链路包含“检索 + LLM 生成 + DeepSeek 核验”，单题可能 5–20 秒；高负载时更长。
- 时间预算建议：
  - FastAPI DeepSeek 超时：30s（现有默认）；
  - Dify HTTP 节点超时：60s；
  - Dify LLM 节点超时：60s；
  - `/api/chat` 调 Dify 的客户端超时：90–120s；
  - nginx `/api/chat` 的 `proxy_read_timeout`：120s（已配置）。
- 如果 Dify 平台的工作流总超时小于 60s，需要先调大，否则 HTTP 节点还没返回就被平台终止。
- 如果 blocking 经常超过 60s，再评估 streaming。streaming 下答案先到、核验结果后到，前端需要处理 SSE 和最终事件，复杂度更高，不建议作为 MVP。

## 9. conversation_id 维护

Dify `/v1/chat-messages` 需要：

- `query`：本轮问题；
- `user`：稳定的匿名用户标识；
- `conversation_id`：首轮为空，之后使用 Dify 返回的值；
- `response_mode`：`blocking` 或 `streaming`；
- `inputs`：如工作流有额外输入变量，按需传入。

`/api/chat` 侧建议契约（待与团队确认后实现）：

```json
// 请求
{"question": "……", "conversation_id": "可选"}
// 响应
{
  "answer": "……",
  "conversation_id": "Dify 返回值",
  "overall_status": "supported",
  "claims": [],
  "evidence": [],
  "error_code": null
}
```

规则：

- 首轮 `conversation_id` 传空字符串或省略；FastAPI 把 Dify 返回的 `conversation_id` 回传前端。
- 前端按标签页/会话保存 `conversation_id`，不要跨用户复用。
- 评测时必须每题使用独立会话（或首轮空 `conversation_id`），避免上一题答案污染下一题。
- 如果 MVP 只做单轮，也要在响应里保留 `conversation_id` 字段，避免以后改契约。

## 10. `/api/chat` 的映射职责

`/api/chat` 不是简单转发文本，需要：

1. 从服务端环境变量读取 `DIFY_API_BASE_URL`、`DIFY_API_KEY`；Key 不出现在响应、日志、前端。
2. 调用 Dify `/v1/chat-messages`，传递 `query`、`user`、`conversation_id`、`response_mode=blocking`。
3. 解析 Dify 返回的结构化输出；如果 Dify 只返回文本，按第 7 节的 MVP 方案解析 JSON。
4. 把 `overall_status`、`claims`、`evidence`、`error_code` 映射为前端字段；不要把 `verification_failed` 降级成 `unsupported`。
5. 对 Dify 超时/网络错误返回 `verification_failed` + `upstream_*`，并给前端明确文案。
6. 限制请求体大小和问题长度；公网入口已有 6r/m 限流，批量评测不要走公网。

## 11. 本地字段映射验证

在未接云端 Dify 前，用固定证据验证“检索 chunk → evidence[] → `/verify` 请求”的字段裁剪：

```powershell
python -m service.scripts.validate_evidence_mapping
```

脚本会：

- 读取仓库内真实文档片段作为固定证据（不是伪造的检索结果）；
- 模拟 Dify 检索节点的额外字段（`score`、`metadata.document_id`）；
- 裁剪为只含 `id/content/source/page` 的 `evidence[]`；
- 用 `EvidenceVerifyRequest` 校验；
- 验证多余字段确实会触发 422。

这只是字段契约验证，不代表真实检索效果，也不替代 30 题实验。

## 12. Dify 控制台落地清单

1. 创建 Chatflow 应用，命名如“课程资料问答证据核验”。
2. 绑定课程知识库；记录索引模式、embedding 模型、`top_k`、score 阈值。
3. 按第 3 节建节点；变量名与本文一致，便于对照。
4. 在 HTTP 节点用“测试”功能发一条固定证据，确认请求体是合法 JSON。
5. 用 3–5 个真实问题做端到端测试，覆盖 supported / partial / unsupported / 系统失败。
6. 确认 `/v1/chat-messages` 的响应结构；若拿不到 `claims`，先按第 7 节 MVP 处理。
7. 导出 DSL 前检查：搜索 `app-`、`sk-`、`Bearer`、`api_key`，确认没有密钥；导出的 YAML 放 `dify/workflow/`。
8. 在 `runs.csv` 记录 Dify 版本、索引模式、模型、`top_k`、commit。

## 13. DSL 说明

云端应用已导出并落库为 [`dify/workflow/chatflow-course-qa.yml`](../dify/workflow/chatflow-course-qa.yml)。该文件是 Dify 1.19 应用包（`.ifpkg`）里的 `app.yaml` 原文，`kind: app`、`version: 0.7.0`，不是手写草稿。

导出前已扫描 `app-`、`sk-`、`Bearer`、`api_key`、`secret`、`password`、`token`，无命中；`dependencies` 只记录 marketplace 插件标识，模型凭据保存在 Dify 平台侧，不随 DSL 导出。

## 14. 已确认事项

1. Dify 1.19.0 的 Code 节点可用（`code_language: python3`），用它做 evidence 裁剪和请求体组装。
2. Knowledge Retrieval 输出 chunk 含 `content`、`title`/`document_name`、`metadata.page`；`page` 不保证存在，代码节点做了兜底。
3. HTTP 节点不能可靠地内联数组变量，且文本插值不做 JSON 转义；改为代码节点 `json.dumps` 生成整串 body，HTTP 节点 body 用 `raw-text` 只引用一个变量。
4. 知识库使用 SiliconFlow `BAAI/bge-m3` 向量检索，`top_k=8`，权重检索（`keyword_weight=0`、`vector_weight=1`，实际等价纯向量），未开 rerank。
5. Chatflow 没有 End 节点，用「直接回复」输出。
6. 仍待确认：`/v1/chat-messages` 是否返回结构化 `claims`；平台工作流总超时上限；`/api/chat` 的最终 schema 与多轮策略。

## 15. 已落地应用说明

| 项 | 值 |
|---|---|
| 应用名 | 课程问答证据核验 |
| 应用类型 | Chatflow（`mode: advanced-chat`） |
| 平台版本 | Dify 1.19.0，已发布版本 #9 |
| 依赖插件 | `langgenius/deepseek:0.0.26`、`langgenius/siliconflow:0.0.64` |
| 知识库 | `genai-course-vector-v2` |

输入变量只有一个：

| 变量 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `question` | text-input | 是 | 用户问题，单轮问答直接透传给检索节点 |

节点顺序与内部变量：

| 节点 | 关键输出 | 备注 |
|---|---|---|
| 用户输入 | `question` | 开始节点 |
| 知识检索 | `result` | `top_k=8`，bge-m3 |
| 代码执行 | `evidence_json`、`evidence_count` | 裁剪为 `id/content/source/page`，最多 50 条 |
| LLM | `text` | `deepseek-flash`，temperature 0.2，按（E1）编号引用 |
| JSON转义 | `result` | 剥离 think 段，`json.dumps` 生成完整请求体 |
| HTTP 请求 | `body`、`status_code` | `POST http://verifier:8000/verify`，body 为 `raw-text`，只插值 `{{#JSON转义.result#}}` |
| 直接回复 | `answer` | `{{#llm.text#}}` + 空行 + `{{#HTTP 请求.body#}}` |

对外输出是**一段文本**：LLM 答案在前，空行之后是核验服务的原始 JSON。JSON 字段沿用 [`verify-api.md`](verify-api.md)：

| 字段 | 类型 | 说明 |
|---|---|---|
| `mode` | string | 当前为 `deepseek` |
| `overall_status` | string | `supported` / `partially_supported` / `unsupported` / `verification_failed` |
| `claims` | array | 每条含 `claim`、`status`、`evidence_ids`、`reason`、`citations` |
| `evidence_count` | int | 实际送入核验的证据条数 |
| `message` | string | 结果说明，调用方不要匹配文案 |
| `error_code` | string/null | 系统错误码，正常为 `null` |

实测（预览输入「什么是 KV Cache？」）：`overall_status=supported`、3 条 claims 全部 `supported`、`evidence_count=3`、`error_code=null`。

已知限制：`answer` 是「文本 + JSON」混合体，`/api/chat` 需要在空行处切分或改用工作流运行详情接口读取 `outputs`；在实测 `/v1/chat-messages` 之前不要假设它返回结构化 `claims`。

### 15.1 版本 #9 与导出文件的差异（2026-11-12）

线上版本从 #3 演进到 #9，主要变化：

| 变化 | 内容 |
|---|---|
| 检索参数 | `top_k` 5 → 8；`keyword_weight=0`、`vector_weight=1`（等价纯向量），未开 rerank |
| 知识库材料 | Markdown 原文 → 纯文本预处理版（`tools/build_knowledge_base_materials.py`），解决「只召回标题、正文丢失」 |
| 知识库绑定 | 重新绑定到 `4d403051-ccdc-434e-8285-af93ddcb5660`；此前一次误绑旧库导致 `evidence_count=0`、`error_code=no_evidence` |
| 结果补全节点 | 在 HTTP 节点后补一次代码执行，把 `source`/`page` 回填进 `citations[]`（`page` 缺失时为空，不显示「后端未提供」） |

仓库里的 `dify/workflow/chatflow-course-qa.yml` 仍是 **#4** 的导出：节点与连线相同，只差上表的检索参数和 `dataset_id`。导入后必须按 [`knowledge-base-rebuild.md`](knowledge-base-rebuild.md) 重新绑定知识库并确认 `top_k=8`。

版本 #9 实测（云端 `POST /api/chat`，`evidence_count=8`）：

| 问题 | 整体状态 | 引用原文长度（字） |
|---|---|---|
| 这门课有哪些学习要求？ | partially_supported | 53 / 28（完整列出 6 条学习要求） |
| agent 是什么 | supported | 52 / 116 / 71 |
| Transformer 的注意力怎么计算的？ | supported | 18 / 88 / 17 / 48（含 `Attention(Q, K, V) = softmax(QK^T / sqrt(d_k)) V`） |
