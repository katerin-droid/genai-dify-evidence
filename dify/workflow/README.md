# Workflow 目录说明

此目录只保存后续从云端 Dify 导出的脱敏 DSL，不保存官方源码，也不保存任何密钥。

- [`chatflow-course-qa.yml`](chatflow-course-qa.yml)：从云端 Dify 1.19 导出的应用包（`.ifpkg` 内的 `app.yaml`，`kind: app`、`version: 0.7.0`），对应已发布版本 #3。

链路：用户输入 → 知识检索 → 代码执行（Evidence 裁剪）→ LLM → JSON转义（代码执行）→ HTTP 请求 → 直接回复。

JSON转义节点用 `json.dumps` 生成整串请求体，HTTP 节点 body 为 `raw-text` 且只插值 `{{#JSON转义.result#}}`，避免 Dify 原样拼接导致 JSON 非法（422）。

节点级方案、变量映射、HTTP 节点配置和异常透传规则见：

- [`docs/dify-chatflow-plan.md`](../../docs/dify-chatflow-plan.md)

导出文件已扫描 `app-`、`sk-`、`Bearer`、`api_key`、`secret`、`password`、`token`，无命中；`dependencies` 只含 marketplace 插件标识，不含模型密钥。
