# 展示层与本地素材验收（2026-11-07）

10张原图均未改写。原始格式和尺寸：

| 原图路径（web/assets/mascots/ 下） | 格式 | 尺寸 |
|---|---|---|
| bigfish/bigfish_busy.webp | WEBP | 430×322 |
| bigfish/bigfish_main.jpg | JPEG | 448×448 |
| bigfish/bigfish_self_comfort.jpg | JPEG | 448×448 |
| gugugaga/gugugaga_salute.jpg | JPEG | 448×448 |
| gugugaga/gugugaga_sideeye.jpg | JPEG | 512×384 |
| gugugaga/gugugaga_smirk.jpg | JPEG | 427×320 |
| gugugaga/gugugaga_thumbsup.webp | WEBP | 300×225 |
| nailong/nailong_face.jpg | JPEG | 448×448 |
| nailong/nailong_look.jpg | JPEG | 448×448 |
| nailong/nailong_wait.jpg | JPEG | 448×448 |

## 本地启动

```powershell
python -m pip install -r service/requirements-dev.txt
$env:VERIFIER_MODE="mock"
python -m uvicorn service.app.main:app --host 127.0.0.1 --port 8000
```

打开 http://127.0.0.1:8000/。此展示无需Key、不要加载真实.env。根页面只静态服务web目录，配置文件在目录之外。原有/verify协议与核验核心未改。
Windows浏览器测试使用已安装Edge；Linux先运行 python -m playwright install --with-deps chromium，再运行pytest。运行时仅需普通FastAPI依赖，页面无CDN和框架。现有Dockerfile只打包service；容器部署页面前须将web完整目录只读挂载到/web（或另行审核镜像打包），本次未操作容器。

## 交互与数据边界

真实问答入口显示“服务尚未连接”且禁用。新增/api/ui-status仅报告集成事实，不返回Key。未发现Dify代理、工作流调用或聊天接口，不能以Dify容器正在运行推定问答集成成功。
示例模式仅使用JS内的合成资料，所有等待和结果始终有示例标签，不发送POST请求；阶段动画仅表示前端等待、不表示后端进度。真实问答恢复后需要服务器端Dify代理、工作流映射、证据source/page关联与网络/SSRF代理验收。
引用渲染只使用当前响应citations和关联的证据字段，不补造缺失source/page。当前可交互引用来自显式示例；没有展示假冒的真实问答。真实模式无结果，与示例切换会清空结果。
严肃模式隐藏角色/趣味反馈，不改变状态与报告数据。复制失败时显示可选中文本，不宣称复制成功。角色图片错误时显示文字备用。所有响应文本以textContent渲染，避免资料HTML注入。

## 截图与测试

artifacts/ui/保存桌面/手机首页、三阶段等待、三种结果、系统失败、趣味/严肃、图片失败截图。所有结果截图均为明确标记的示例，非新模型调用。
新增10项图片HTTP路由检查、1项静态/连接状态检查、1项真实Edge浏览器综合测试（引用展开、模式隔离、复制、双模式、随机文案、4状态、响应式无横向溢出、加载失败、无POST和外部CDN）。浏览器测试使用临时Mock服务并在finally停止。
公开clone未带授权素材时，依赖图片的测试会明确skip，不能将skip作为本地资源验收通过。

## Public资源规则

web/assets/mascots/和artifacts/ui/已被Git忽略，图片及含图片的截图均不自动提交。提供本地图片不等于已取得网络表情包或角色的公开再分发许可。当前不建议将素材提交Public仓库；需权利人授权、可再分发许可或用户确认合法来源后再审。代码可以在审查后独立提交，部署时另行提供有权使用的资源。未经确认不更换图片。

## 从Public仓库复现

Git仓库不附带图片素材、截图或密钥，必须单独准备拥有合法使用权的10张原图并放到上表指定目录；不要从代码仓库推定素材授权。不得以自动下载或生成替代图补齐。缺图时页面仍可打开并显示备用文字；需要完整图片及浏览器环境才能复现全部62项本地测试。真实问答代理未集成，默认真实入口保持禁用，示例仅供离线体验。
