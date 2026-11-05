# 开发记录

## 2026-11-05
- 工作区 D:/genai-dify-evidence 初始为空；git status/branch/remote 均提示 not a git repository。未覆盖已有文件、未初始化 Git、未修改远程配置。
- 用户级和系统级默认 SSH 配置不存在；无 ECS 连接信息，未发起服务器连接。
- Git 标签获取受不可用本机代理和直连网络阻塞；浏览工具独立确认官方最新正式 1.19.0 与 commit 8e689e868b63b6dd2b449d0eb568ca5cc7127759。
- ECS /opt/dify 源码拉取尚未完成；官方部署文件只完成线上存在性核实。ECS 资源与软件版本均未验证。
- 新增请求指定全部文件/目录，另有实施计划、包标识、测试文件、requirements-dev.txt、.dockerignore 和 workflow README。
- GET /health；POST /verify 严格输入校验与 Mock 响应，不给出实际支持度结论。
- 本地 Python 3.13.7，FastAPI 0.141.1、Pydantic 2.13.4、pytest 9.1.1、httpx 0.28.1、uvicorn 0.40.0；依赖已存在，未安装或升级系统软件。
- 第一次测试 1 passed / 13 errors，原因是测试网络拦截妨碍 Windows asyncio 初始化；修正拦截时机后 python -m pytest -q service/tests：14 passed in 1.24s。
- 覆盖健康接口、确定性 Mock/null 分值、必填/空白/类型/长度/数量/额外字段/嵌套证据/非法 JSON、拒绝 live 模式，接口测试拦截网络连接。
- 未创建真实 .env；未读取真实 API Key/私钥；未调用收费 API；未构建或启动容器；未升级服务器；未提交或推送；未删除文件。
- 当前停在审核点，不自行进入部署阶段。
