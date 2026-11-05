# Real Verifier Implementation Plan

**Goal:** 在既有接口上新增一次调用的证据核验，默认保持离线 Mock。总体字段统一为 overall_status，陈述字段为 status。
**Architecture:** 保留 VerifyRequest/VerifyResponse；新增真实模式模型、HTTP 客户端与严格结果验证。配置用环境变量，客户端注入便于离线测试。
**Tech Stack:** FastAPI / Pydantic / httpx / pytest。

1. 保留并执行原有 14 个测试；不改变原测试内容。
2. 扩展 config/schemas，deepseek 模式需 Key、HTTPS Base URL、显式模型名。Mock 不读 Key。真实输入可空 evidence、支持 id/content 和旧别名，拒绝重复 ID。
3. 新增 deepseek.py 单次 JSON 请求、无重试、超时及错误脱敏，不保存原始请求响应日志。
4. verifier.py 验证所有返回字段、最多5条、已存在证据 ID、支持结论必需原文引用；无陈述、错误及无效输出单独处理，聚合由服务端计算。
5. 新增 MockTransport/接口测试，覆盖用户九类案例及鉴权/限流/截断/别名/注入边界；默认 pytest 拦截真实网络。
6. README/architecture/log/env example 更新；提供显式 --allow-paid 的手动脚本，只用合成资料，不在本次运行。
7. 全量 pytest 与 git diff 检查，不提交、不推送、不操作 Dify。
