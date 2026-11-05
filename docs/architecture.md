# 架构与阶段边界

Dify 负责课程知识库检索、问答与后续工作流编排；FastAPI 接收问题、候选回答、证据片段，后续才通过 DeepSeek 核验证据支持度。
第一阶段 FastAPI 只有 GET /health 和 POST /verify，所有结果为 mock/not_evaluated，不具有实际核验含义。
没有数据库、模型客户端、真实密钥或后台任务。评估 CSV 只有表头。

## 源码与运行环境
- 官方 Dify：ECS /opt/dify，独立 Git origin=https://github.com/langgenius/dify.git。
- 自研项目：本工作区；目前无 .git，不能确认已关联私有 GitHub 仓库。
- Dify 和 FastAPI 将来同机运行，使用不同 Compose 项目。
- 已在线查看 1.19.0 官方 Compose：API/worker 等使用 default 与 ssrf_proxy_network。此信息不是 ECS 实际配置确认。
- 下一阶段先核实调用实际发起容器、Compose 项目名和网络、HTTP 节点的 SSRF 代理路径及 ACL。
- 可评估让自研 Compose 使用 external 网络加入已确认的官方网络；必要时通过独立 override 接入专用共享网络，不能编辑官方文件。
- 服务名或网络别名解析后才可配置 http://<verified-alias>:8000/verify；容器 localhost 仅代表本容器。
- 不将内部核验端口默认暴露到公网。网络连通不代表 SSRF 代理允许请求，需端到端验证且保留防护。

当前未创建网络、Compose 配置或运行容器。Dockerfile 已准备，镜像构建与容器测试尚未执行。
