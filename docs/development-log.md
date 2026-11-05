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

## 2026-11-05 阶段四
- 已有 Public 仓库和初始化提交保留，Dify 独立源码与运行容器均未操作。
- 先读 AGENTS/README/全部 app 代码和原测试；基线14项通过。
- 新增 deepseek 模式和官方兼容 JSON completion；Base URL 与模型可配置，模型无默认 ID。默认仍为 Mock，旧 live 模式继续拒绝。
- 新输入 id/content 可带 source/page/metadata，兼容旧别名；真实模式允许空证据短路。最多5条、状态聚合、ID/原文引用有效性均由服务端约束。
- 新增一次请求、无重试、HTTPS 配置约束、超时与异常固定错误码；默认 pytest 拦截真实网络。原14项测试未改写。
- 新增独立 --allow-paid 手动合成资料脚本，本次未执行；未读取或创建真实密钥、未调用真实模型，不能报告模型实际准确率。
- README、架构和环境模板更新；httpx 升为运行依赖，python-dotenv 用于显式 --env-file 加载。
- 测试与最终验证结果见本阶段交付记录；完成后暂停，不自动提交或推送。
- 最终验证：原有 test_api.py 14 passed；新增 test_real_verifier.py 36 passed；完整 python -m pytest -q 为50 passed in 1.36s。git diff --check 无空白错误（Windows 文档存在 CRLF/LF 提示）。

## 2026-11-05 真实模型测试前契约审查
- 阅读全部 app 代码、README、架构、两套测试与手动脚本；修改前基线50项通过。
- /verify 顶层字段统一 overall_status，claims[*].status 和 /health.status 保持不变；同步 Pydantic、verifier、手动脚本、文档及原14/新增36项测试断言。
- 引用 ID 列表去重，citation ID 集合必须与其相等，拒绝重复 ID/quote 对；允许同证据不同片段、无依据 unsupported 双空数组、反证引用。
- 保留四状态聚合以及无证据/无陈述/非法ID/超时的处理；无额外模型或调用次数。
- 用合成环境变量与 MockTransport 验证 Key、模型、Base URL、超时读取及 Bearer header 传递，不读取或输出真实密钥。
- 新增 docs/verify-api.md 作为当前完整接口说明；默认测试仍阻断真实 HTTP。
- 最终验收：原有14项通过、新增36项通过，完整50 passed in 1.66s；文档JSON与实际MockTransport接口响应一致；Git忽略和敏感扫描通过，无真实调用或推送。

## 2026-11-05 单次真实 DeepSeek 冒烟测试：配置检查阻塞
- 已阅读 docs/verify-api.md 和现有手动脚本；现有脚本使用单条两小时时长合成资料，未直接运行（本次用户要求的是12周/笔试口试资料）。
- 自研项目根目录 .env 不存在；当前进程缺失必要配置项：DEEPSEEK_API_KEY,DEEPSEEK_MODEL。只检查配置是否存在，未打印密钥、未读取其他项目 .env。
- 模型名称未配置；若未覆盖，代码默认 Base URL 为 https://api.deepseek.com。没有更改配置或创建 .env。
- 按配置不完整立即停止：FastAPI 未启动，/verify 请求0次，真实 DeepSeek 请求0次，无重试或批量测试。
- HTTP状态、响应时间、token usage 和陈述判断均未产生；不能据此认定模型调用成功或证据核验通过。未把配置失败记作证据不足。
- 无测试服务需要关闭；未操作 Dify 容器，未推送 GitHub，等待用户在本地补齐配置后重新授权单次测试。

## 2026-11-05 单次真实 DeepSeek 冒烟测试：配置预检停止
- 已阅读 docs/verify-api.md、现有手动脚本、配置管理与 DeepSeek 客户端。
- 自研目录 .env 不存在；当前进程中 VERIFIER_MODE、DEEPSEEK_API_KEY、DEEPSEEK_BASE_URL、DEEPSEEK_MODEL 均未设置。只输出配置存在性及非敏感配置，不记录用户提供的凭据。
- 代码默认 Base URL 为 https://api.deepseek.com，模型名无默认值。用户提供的 platform.deepseek.com/api_keys 为密钥管理页面，不作为 API Base URL。
- 因缺少明确的账户模型 ID，遵循配置缺失立即停止的要求，未创建或修改 .env、未启动 FastAPI、未发送任何真实 DeepSeek 请求、未重试。
- 实际模型请求次数：0。HTTP 状态码、响应时间、token usage、陈述结果均不适用；不能将用户预期写为真实模型结果，也不能判断账户额度。
- 未操作 Dify 容器、未修改官方源码、未推送 GitHub。待用户明确 DEEPSEEK_MODEL 及需要覆盖的 Base URL 后再配置并执行一次请求。

## 2026-11-05 单次真实 DeepSeek 冒烟测试：请求失败后停止
- 用户明确模型 ID 为 deepseek-v4.1flash；使用代码默认 Base URL https://api.deepseek.com，未自动替换模型名。
- 已在自研目录以独占创建方式生成 Git 忽略的 .env；凭据未输出或写入日志。本段不含凭据值。
- 启动仅监听127.0.0.1动态空闲端口的临时 FastAPI，通过本机 POST /verify 发送用户指定的课程12周/笔试口试合成资料。
- Provider 请求次数严格为1，禁用重试和重定向；没有执行30题测试，没有失败后重试。
- DeepSeek HTTP状态码400，error.type=invalid_request_error；Provider响应耗时0.117秒，未返回token usage。未保存原始Provider响应或凭据。
- 本机FastAPI HTTP200，耗时0.580秒；响应 overall_status=verification_failed、error_code=provider_http_error、evidence_count=2、claims=[]。HTTP200仅表示接口已处理，不能表示模型调用成功。
- JSON结构有效、调用失败映射正确。模型未返回有效核验陈述，三条预期状态、最多5条的真实提取效果、证据ID及原文引用、成功结果聚合均未能验收，不能以空数组检查通过替代真实结果。
- HTTP400说明请求被拒绝，但现有保存信息不足以进一步确认是模型ID/参数兼容性或其它具体问题；不据此判断账户额度。未擅自更换模型重试。
- finally 已停止本次临时FastAPI服务，service_stopped=true。Dify容器未操作、官方源码未修改、未推送GitHub。
- 脱敏本地记录 docs/local-deepseek-smoke-2026-11-05.json 已加入忽略；本阶段结束等待审核。

## 2026-11-05 修正模型 ID 后的单次真实冒烟测试
- 确认代码实际使用 DEEPSEEK_MODEL；本地 .env 原值 deepseek-v4.1flash，仅将该赋值改为 deepseek-flash，其他环境变量、核验逻辑及提示词未修改。
- 使用已有凭据查询官方 GET https://api.deepseek.com/models 一次：HTTP200，0.790秒，模型列表包含 deepseek-flash。未输出请求头或凭据。
- 仅启动本机临时 FastAPI，并对用户原始三条合成陈述和E1/E2执行一次 POST /verify；没有自动重试或批量测试。
- 上游 DeepSeek HTTP200，finish_reason=stop，响应耗时3.999秒；本机FastAPI HTTP200，全程4.461秒。
- usage：prompt_tokens=470，completion_tokens=698，total_tokens=1168；prompt_cache_hit_tokens=0，prompt_cache_miss_tokens=470。
- 实际三条陈述依次：本课程共12周→supported/E1；期末考核包括笔试和口试→partially_supported/E2；所有学生必须参加口试→unsupported/E2。
- 模型分别引用E1原文、E2完整原文及E2中“不设置口试。”作为判断依据，精确子串检查全部通过；引用反证并不意味着支持该陈述。
- 合法JSON，3条陈述未超过5条，证据ID均真实存在，引用均可在原始证据找到，服务端总体聚合partially_supported，error_code=null；与本题预期一致。
- 上游没有错误，error.type/code/message不适用。临时服务已停止，Dify容器未操作，官方源码未修改，未推送GitHub。
- 脱敏详细结果保留于Git忽略的 docs/local-deepseek-smoke-flash-2026-11-05.json；本地 .env 继续被忽略。
- 本次真实请求后完整离线回归：python -m pytest -q → 50 passed in 1.33s；git diff --check 无空白错误，仅Windows换行提示。任务完成后停止。

## 2026-11-05 v0.1-backend 发布准备
- 用户授权提交并推送当前稳定版本，提交说明为 feat: implement DeepSeek evidence verification service，标签v0.1-backend。
- origin/main 与本地提交基线一致，目标标签不存在；公开候选文件扫描未检出真实凭据，.env及本地运行记录保持忽略。
- README、接口、架构及部署说明已与实际本地状态和真实单题冒烟结果同步；完整pytest为50 passed。
- 仅执行Git发布；无模型调用、Dify容器操作、历史改写或强制推送。
