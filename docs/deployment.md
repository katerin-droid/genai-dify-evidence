# 部署准备记录（2026-11-05，Asia/Shanghai）

## 已核实的官方发布
- 官方仓库：https://github.com/langgenius/dify.git
- 最新正式 Release 标签：1.19.0（非 draft、非 prerelease，发布于 2026-11-04）。
- Release 指向的 commit：8e689e868b63b6dd2b449d0eb568ca5cc7127759。
- 来源：https://github.com/langgenius/dify/releases/tag/1.19.0
- commit：https://github.com/langgenius/dify/commit/8e689e868b63b6dd2b449d0eb568ca5cc7127759
- 在线确认该标签的 docker/docker-compose.yaml 和 docker/.env.example 存在；不是 ECS 落盘文件完整性验收。
- 模板：https://raw.githubusercontent.com/langgenius/dify/1.19.0/docker/.env.example
- Compose：https://raw.githubusercontent.com/langgenius/dify/1.19.0/docker/docker-compose.yaml
- 官方要求 Compose >=2.35.0；Linux 最低 CPU 2 核、RAM 4 GiB。这是 Dify 最低要求，同机 FastAPI 仍需资源余量。
- 文档：https://docs.dify.ai/en/self-host/deploy/quick-start/docker-compose

## 阻塞与未验证项
当前用户 ~/.ssh/config 与系统 %ProgramData%/ssh/ssh_config 都不存在，没有可用 ECS 别名；未猜测主机地址或身份文件。
未连接 ECS，未检查 OS/CPU/内存/磁盘、Docker Engine、Compose、现有容器、/opt/dify 是否存在。
未克隆官方源码。git ls-remote 首次失败：本机已配置的代理 127.0.0.1:7897 不可连接；仅本次命令禁用 HTTP 代理后直连 GitHub 443 也失败。未改变 Git 配置。
通过浏览工具读取官方发布、版本文件和 commit，不等同于 Git 标签列表获取成功或克隆成功。
当前目录无 .git，没有分支或 origin 可确认；未执行 git init 或 remote add/set-url。

## 审核后先补完源码准备
1. 用户提供已配置 SSH 别名（若使用非默认 config，同时给出配置路径）；或提供主机、公用 SSH 端口、用户名、认证方式及已有本地密钥文件路径。不要在聊天中发送私钥或 API Key。
2. 只读检查 cat /etc/os-release、uname -m、nproc、free -h、df -h /opt、docker --version、docker compose version；确认磁盘余量。
3. 若 /opt/dify 存在，检查 git -C /opt/dify remote -v、branch --show-current、describe --tags --always、rev-parse HEAD、status --short；不输出 diff 或真实 .env。若非官方或有改动，报告并保留，禁止 reset/覆盖。
4. 若 /opt/dify 不存在且权限足够，从 ECS 获取官方 tags 与正式 Release，排除预发布。复核目标标签仍符合选择条件，记录准确 commit；不要自动改用 main。
5. 在仅确认目标不存在时执行 git clone --branch 1.19.0 --depth 1 https://github.com/langgenius/dify.git /opt/dify；执行前重新核实标签，若与本记录不同先记录原因。用 rev-parse HEAD 与记录比对。
6. 检查两个指定部署文件与 Compose 引用的 envs/defaults、挂载配置文件是否齐全，并确认 Compose >=2.35.0。版本不足只报告，不升级。
7. 恢复正确私有仓库工作区关联；保留本次文件，不凭空创建 origin 或推送。

## 进入部署阶段后的具体步骤（本次不执行）
1. 核查现有服务、端口占用、安全组、持久化目录与备份方案，确认同机资源预算。
2. 使用实际官方网络配置设计独立自研 Compose，核实 SSRF 代理与 DNS 可达路径。
3. 审核部署配置与端口后才准备真实环境变量，避免覆盖已有配置，密钥不进入日志/仓库。
4. 运行静态配置验证，构建 FastAPI 镜像；不得把包含密钥的 compose config 完整输出到聊天。
5. 经用户授权后启动两个 Compose 项目，检查健康状态、Dify 到 Mock /verify 的网络与契约。
6. 先完成 Mock 联调与回归；完整核验逻辑、DeepSeek 接入和收费调用另行审核。
