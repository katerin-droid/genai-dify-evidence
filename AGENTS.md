# 项目执行约束
- Dify 官方源码独立位于 ECS /opt/dify，不得 vendoring 到本仓库，不修改官方源码。
- 部署必须固定官方正式标签及 commit，不使用 main。
- 第一阶段仅 Mock、输入校验和响应契约，不访问 DeepSeek 或其他收费 API。
- 不读取或输出真实密钥，不提交 .env、私钥、资料原文或真实评估数据。
- 不覆盖或删除已有文件，不修改 origin；Git 推送及部署须取得用户后续授权。
- 未经审核不执行 compose up、不启动/重启容器、不升级软件。
- Dify 和自研 Compose 分开管理；根据实际网络与 SSRF 代理配置验证通信，禁止假定 localhost 互通。
- 测试：python -m pytest -q service/tests。
