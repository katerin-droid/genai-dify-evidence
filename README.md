# 基于开源 Dify 的课程资料问答证据支持度核验系统

架构：Dify + FastAPI + DeepSeek + Docker Compose。当前仅 Mock 接口，未调用 DeepSeek，未部署。
Dify 官方源码必须独立存放在 ECS `/opt/dify`，此仓库只管理自研服务、工作流和评估配置。

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
返回 mode=mock、status=not_evaluated、support_label=null、score=null、evidence_count 和说明。
输入要求严格字符串；正文 1–20000 字符，证据 ID 1–128 字符，证据数量 1–50。
字符串去除首尾空白；缺失、未知字段和非法输入返回 422。
Mock 不比较文本，不输出支持度结论。仅支持 VERIFIER_MODE=mock；其他值在应用创建时拒绝。
应用不加载 `.env`，无需 API Key。CSV 仅含表头，没有虚构测试结论。

详情见 docs/architecture.md、docs/deployment.md、docs/development-log.md。
