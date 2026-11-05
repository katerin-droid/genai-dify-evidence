# POST /verify 接口契约

此文档描述阶段四真实模式（VERIFIER_MODE=deepseek）的当前实现，示例全部为合成资料、非真实模型结果。Pydantic 与运行时 OpenAPI 是结构校验来源。

## 请求

```json
{
  "question": "课程多久？",
  "answer": "课程两小时。",
  "evidence": [
    {"id": "e1", "content": "课程两小时。", "source": "synthetic", "page": 1, "metadata": {"chapter": "demo"}}
  ]
}
```

question/answer 为非空字符串，去除首尾空白后最长20000字符。evidence 必填，真实模式允许0–50条。id 为非空、最多128字符的唯一标识；content 为非空、最多20000字符的正文。
兼容 evidence_id/text 别名，但同一条不接受新旧字段同时出现。source 为可选字符串（最多2000字符）；page 为正整数或非空、最多128字符的字符串；metadata 为 JSON 对象（默认空对象）。未知字段、空正文、重复证据 ID 等输入错误为 HTTP 422，模型不调用。

## 响应

```json
{
  "mode": "deepseek",
  "overall_status": "supported",
  "claims": [
    {
      "claim": "课程两小时。",
      "status": "supported",
      "evidence_ids": ["e1"],
      "reason": "给定证据提供时长。",
      "citations": [{"evidence_id": "e1", "quote": "两小时"}]
    }
  ],
  "evidence_count": 1,
  "message": "Evaluated against supplied evidence only.",
  "error_code": null
}
```

顶层只使用 overall_status，不再输出顶层 status，也不同时输出旧别名。claims[*].status 保持不变；GET /health 的 status 是进程健康标志，仍保持原名。
mode 为 deepseek；evidence_count 是传入证据数量，不是引用数量。claims 最多5条；reason 为非空说明。message 用于解释结果，调用方不要匹配其文案，应检查 overall_status/error_code。
模型只返回 claims；总体状态由服务端计算，模型不得自报总体状态。结构有效的业务失败仍返回 HTTP 200。

## evidence_ids 与 citations

- evidence_ids：本条判断实际引用的证据 ID 列表，必须去重，全部存在于请求 evidence。
- citations：精确原文片段列表，每项含 evidence_id 与 quote。quote 必须是对应 content 的连续精确子串；服务端不做模糊匹配。
- citations 中所有 ID 的集合必须与 evidence_ids 的集合相等，列表顺序不要求一致。一个 ID 可对应多个不同原文片段；相同 (evidence_id, quote) 不允许重复。
- supported/partially_supported 必须至少引用一个 ID 并提供对应原文。
- unsupported 若没有相关证据，两个列表都为空；若依据反证判断 unsupported，也可以引用真实存在的原文。引用表示判断依据，不等于支持陈述。
- 不存在的 ID → verification_failed/unknown_evidence_id；重复 ID/引用、错误原文或引用不在列表 → verification_failed/invalid_citations；缺少必要引用 → verification_failed/missing_citations。无效结果整体丢弃，claims=[]，不把部分已验证内容当作最终结论。
- 原文匹配仅证明引用来自输入，不证明语义蕴含正确；语义判断和事实提取仍依赖模型，需要人工金标评估。

## 状态与聚合

| 陈述状态 | 含义 |
|---|---|
| supported | 传入证据完整支持该陈述 |
| partially_supported | 传入证据只支持其中一部分 |
| unsupported | 传入证据不足以建立陈述，或与之矛盾；不等于证明其在外部世界为假 |
| verification_failed | 核验过程失败，不能给出可靠结论 |

| 条件 | overall_status | error_code |
|---|---|---|
| 非空 claims 全 supported | supported | null |
| 非空 claims 全 unsupported | unsupported | null |
| 有 partially_supported 或 supported/unsupported 混合 | partially_supported | null |
| 任一陈述 verification_failed | verification_failed | claim_verification_failed |
| 空 evidence | unsupported，不调用模型，claims=[] | no_evidence |
| 未提取到陈述 | verification_failed，claims=[] | no_verifiable_claims |
| API 超时 | verification_failed，claims=[] | provider_timeout |
| 模型 JSON/schema 错误或超过5条 | verification_failed，claims=[] | invalid_model_output |
| HTTP错误/网络失败 | verification_failed，claims=[] | provider_http_error / provider_unavailable |
| 空输出/非 stop 完成原因 | verification_failed，claims=[] | empty_completion / incomplete_completion |
| Provider envelope 无效/其他系统异常 | verification_failed，claims=[] | invalid_provider_response / internal_error |

先排除空列表和失败，再聚合。无陈述不会因“所有陈述支持”的空集合逻辑误判 supported。

## Mock 兼容与配置

默认 mock 仍不调用任何模型，不做语义判定；/verify 顶层也统一 overall_status，但值为 not_evaluated，保留 support_label=null/score=null/evidence_count/message。Mock 空证据仍为422。
这是总体字段改名，需要原来读取 response.status 的客户端改为 response.overall_status；不能改动 claims[*].status 或 /health.status。
真实模式从环境变量读取 DEEPSEEK_API_KEY、DEEPSEEK_BASE_URL、DEEPSEEK_MODEL、DEEPSEEK_TIMEOUT_SECONDS；模型名无默认值。应用不自行读取 .env，uvicorn --env-file 或手动脚本显式加载，已存在环境变量优先。
离线测试使用合成环境值与 MockTransport 验证读取、Bearer header、模型名、URL；随后另经授权使用 deepseek-flash 完成一次真实三陈述冒烟测试，详情见 development-log.md。本文JSON仍为结构示例，不替代真实测试记录。真实凭据只存放在本地 Git 忽略的 .env，模板凭据字段为空。
