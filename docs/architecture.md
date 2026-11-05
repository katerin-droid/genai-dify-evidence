# 架构与阶段边界

Dify 负责课程知识库检索、问答与后续工作流编排；FastAPI 接收问题、候选回答、证据片段，阶段四新增通过 DeepSeek 核验证据支持度的客户端（已通过单次真实冒烟测试）。
第一阶段 FastAPI 只有 GET /health 和 POST /verify，所有结果为 mock/not_evaluated，不具有实际核验含义。
自研服务没有数据库或后台任务；新增模型客户端，真实密钥仅通过环境注入。评估 CSV 只有表头。

## 源码与运行环境
- 官方 Dify：本地 D:/opensource/dify，后续 ECS /opt/dify，独立 Git origin=https://github.com/langgenius/dify.git。
- 自研项目：本工作区；已关联 Public GitHub 仓库 https://github.com/katerin-droid/genai-dify-evidence。
- Dify 和 FastAPI 将来同机运行，使用不同 Compose 项目。
- 已在线查看 1.19.0 官方 Compose：API/worker 等使用 default 与 ssrf_proxy_network。此信息不是 ECS 实际配置确认。
- 下一阶段先核实调用实际发起容器、Compose 项目名和网络、HTTP 节点的 SSRF 代理路径及 ACL。
- 可评估让自研 Compose 使用 external 网络加入已确认的官方网络；必要时通过独立 override 接入专用共享网络，不能编辑官方文件。
- 服务名或网络别名解析后才可配置 http://<verified-alias>:8000/verify；容器 localhost 仅代表本容器。
- 不将内部核验端口默认暴露到公网。网络连通不代表 SSRF 代理允许请求，需端到端验证且保留防护。

Dify 本地容器已由前三阶段启动并由用户初始化管理员；本次不操作容器。自研服务尚未容器化联调。Dockerfile 已准备，镜像构建与容器测试尚未执行。

## 阶段四核验流程

环境配置 → create_app 选择 Mock/DeepSeek 契约 → Pydantic 输入校验 → 空证据短路 → 单次 httpx JSON completion → 结果 schema 校验 → ID/原文引用校验 → 服务端聚合。
模型抽取与判定在同一次调用内完成，不调用搜索/额外模型，无自动重试。ModelResult 只接受 claims，最多5条，禁止模型返回伪造总体状态。
DeepSeekClient 与 Settings 可注入，测试全部使用 MockTransport；默认测试禁止原生 httpx HTTPTransport 网络请求。异常只映射固定错误码，不记录密钥、资料、原始响应或 provider 异常。
无证据是不足以支持答案，无陈述是不可核验，二者不等同于通过。仅 supported/partially_supported 必须引用已有证据并附精确子串；语义蕴含与陈述覆盖度仍由模型判断，需人工评估。
文档示例均为合成资料，已完成单次真实模型冒烟，但没有批量模型质量指标。后续网络/鉴权/速率限制/请求体总量限制与金标评估需在实际接入 Dify 前验收。

## 接口契约审查

POST /verify 在 Mock/DeepSeek 两种模式下均使用 overall_status，claims[*].status 保持陈述级状态，GET /health.status 保持进程级健康标志。
evidence_ids 去重且引用输入 ID，citations 为对应精确原文，两者 ID 集合一致，禁止重复 ID/quote 对；unsupported 可为空引用或提供反证。
总体状态只由服务端聚合；空证据短路、空陈述、非法引用及 API 超时均有独立错误码。详细结构和行为以 [verify-api.md](verify-api.md) 为准。
配置读取使用合成变量进行离线验证，不读取真实 .env/Key；本次不涉及真实模型或容器操作。
