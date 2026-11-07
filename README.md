# 基于开源 Dify 的课程资料问答证据支持度核验系统

架构：Dify + FastAPI + DeepSeek + Docker Compose。阶段四已实现 DeepSeek 核验路径；默认仍为离线 Mock。已完成50项离线测试及一次 deepseek-flash 真实核验冒烟测试。
Dify 1.19.0 官方源码独立存放在本地 `D:/opensource/dify`（未来 ECS 位置为 `/opt/dify`），此仓库只管理自研服务、工作流和评估配置。

## 本地验证
```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r service/requirements-dev.txt
.venv/Scripts/python -m pytest -q service/tests
```
测试已在现有 Python 环境运行；上述 venv 命令供后续隔离复现。
本地运行（手动可选）：`python -m uvicorn service.app.main:app --host 127.0.0.1 --port 8000`。
Docker 构建上下文是 `service/`；本阶段未构建或启动镜像。

## 接口契约
`GET /health` 返回 `{"status":"ok","mode":"mock"}`。
`POST /verify` 示例：
```json
{"question":"课程多久？","answer":"两小时","evidence":[{"evidence_id":"e1","text":"课程时长两小时。"}]}
```
返回 mode=mock、overall_status=not_evaluated、support_label=null、score=null、evidence_count 和说明。
输入要求严格字符串；正文 1–20000 字符，证据 ID 1–128 字符，证据数量 1–50。
字符串去除首尾空白；缺失、未知字段和非法输入返回 422。
Mock 不比较文本，不输出支持度结论。默认 VERIFIER_MODE=mock；新增 deepseek 模式，仍拒绝旧的 live 值与其他未知值。
应用本身只读取环境变量；Mock 无需 API Key。CSV 仅含表头，没有虚构测试结论。

详情见 docs/architecture.md、docs/deployment.md、docs/development-log.md。

## 阶段四：真实核验接口

在自研目录创建未跟踪 `.env`，参考 `.env.example` 设置 `VERIFIER_MODE=deepseek`、`DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`。真实 Key 仅放在本地被 Git 忽略的 `.env`，不要粘贴到终端或日志。模型 ID 无默认值，必须填账户可用的 ID。启动时使用：

```powershell
python -m pip install -r service/requirements-dev.txt
python -m uvicorn service.app.main:app --env-file .env --host 127.0.0.1 --port 8000
```

真实配置仅存本地被忽略的 `.env`；临时 FastAPI 已在冒烟测试结束后停止。不要使用 Dify 的 `.env` 作为自研服务配置。
官方 OpenAI 兼容地址默认 `https://api.deepseek.com`，客户端向其 `/chat/completions` 发送一次请求；也支持账户明确配置的 `/v1` 前缀。仅接受无凭据/查询串的 HTTPS Base URL，不跟随重定向，不自动重试，不使用系统代理环境变量。
参考：[官方接口](https://api-docs.deepseek.com/)、[JSON Output](https://api-docs.deepseek.com/guides/json_mode/)。账号实际可用模型与 JSON Output 能力需手动确认。

`GET /health` 在真实模式返回 `{"status":"ok","mode":"deepseek"}`，只表示进程运行，不验证模型可达性。
`POST /verify` 真实模式示例（仅合成资料）：

```json
{"question":"课程多久？","answer":"课程两小时。","evidence":[{"id":"e1","content":"课程两小时。","source":"synthetic","page":1,"metadata":{"chapter":"demo"}}]}
```

成功响应结构示例（非真实模型测试结果）：

```json
{"mode":"deepseek","overall_status":"supported","claims":[{"claim":"课程两小时。","status":"supported","evidence_ids":["e1"],"reason":"证据给出两小时时长。","citations":[{"evidence_id":"e1","quote":"两小时"}]}],"evidence_count":1,"message":"Evaluated against supplied evidence only.","error_code":null}
```

兼容旧 `evidence_id/text`；同一条不可同时传新旧字段。source/page/metadata 可选；page 为正整数或非空页码字符串。证据 ID 不允许重复。正文与字段长度上限沿用原契约。
一次调用提取并判断最多5条陈述；模型返回超过5条时整份拒绝。supported/partially_supported 必须有合法 ID 和逐字原文引用；服务端核验 quote 是相应 content 的子串。任何伪造 ID/原文都会使整份结果 verification_failed。

聚合由服务端计算：全 supported→supported，全 unsupported→unsupported，混合或包含 partially_supported→partially_supported，任一失败/系统异常→verification_failed。不返回模型自报的总体结论。
真实模式空 evidence 返回 unsupported、error_code=no_evidence、claims=[]，不调用模型；无事实陈述返回 verification_failed、error_code=no_verifiable_claims，绝不默认 supported。
超时、HTTP 错误、空响应、截断、非法 JSON/schema 等均返回 verification_failed 和固定错误码；不返回原始异常或模型无效输出。请求输入错误仍为 HTTP 422；成功处理的核验失败结果使用 HTTP 200，调用方必须检查 overall_status/error_code。
默认 Mock 保留原语义与14项测试用例（总体状态字段统一为 overall_status）：空 evidence 仍为422，结果为 not_evaluated；要验证空证据业务分支须显式使用 deepseek 模式。

证据与问题仅作为 JSON 数据，提示词禁止执行其中指令或使用外部知识；这是缓解措施，不是语义正确性保证。引用原文匹配不能证明模型判断正确，仍需人工金标评估。服务目前无鉴权，仅建议本机监听；Dify 网络联调与生产安全配置尚待后续开发。

## 测试与手动付费入口

默认 `python -m pytest -q` 只运行离线测试，真实 HTTP 传输被测试夹具拦截，模拟 Provider 使用 httpx.MockTransport。原有14项测试用例保留（仅更新总体状态字段断言）。
下面命令会实际消耗 API 额度，仅供用户明确授权后运行；它与已完成的三陈述专项冒烟测试使用不同输入：

```powershell
python -m service.scripts.smoke_deepseek --allow-paid --env-file .env
```

脚本只发送合成资料，输出总体状态/陈述数量/固定错误码；没有 --allow-paid 不会加载配置或调用 API。现有环境变量优先于 `.env`。不要启用 HTTP 调试日志或把真实凭据放入命令行。

## 接口契约审查修订

完整请求字段、响应与异常规则见 [POST /verify 接口说明](docs/verify-api.md)。/verify 顶层总体字段统一为 **overall_status**（Mock 亦同）；陈述仍使用 claims[*].status，/health.status 不变。调用方需同步修改旧的 response.status 读取逻辑。
evidence_ids 为去重 ID 列表；citations 为原文引用列表，两者 ID 集合必须完全一致。允许同一 ID 引用多个不同片段，但不允许重复的 ID/quote 对；unsupported 可以两个数组都为空，也可引用反证。引用来源检查不等同于语义正确性保证。

## v0.1-backend 稳定检查点

2026-11-05：50项离线pytest通过。已用 deepseek-flash 完成一次三陈述真实核验，DeepSeek与本地接口均HTTP200，结果为 supported / partially_supported / unsupported，总体 partially_supported，证据ID和原文引用检查通过。该单题冒烟不代表批量准确率；详细脱敏结果见开发记录。
默认模式仍为Mock，模板不包含密钥或默认模型ID。Dify管理员由用户完成初始化；FastAPI与Dify容器网络/工作流联调尚未验收，不是完整生产部署。

## 课程资料侦探社展示层

已新增原生HTML/CSS/JS展示页，由FastAPI根路径提供。用Mock模式本机启动后访问 http://127.0.0.1:8000/；真实Dify问答代理尚未集成，入口明确显示未连接。独立体验示例不调用模型，保留示例标记。素材清单、交互测试、截图路径及Public版权边界见 [展示层说明](docs/web-showcase.md)。

公开仓库仅包含展示代码，**不包含10张角色图片或截图**。使用者需自行准备有权使用的素材，按 docs/web-showcase.md 的路径清单放入 web/assets/mascots/；缺图时页面显示文字备用。未提供图片时相关测试会明确跳过，不等同于本地62项完整验收。真实Dify问答入口仍未连接，体验示例不是实际模型问答。
