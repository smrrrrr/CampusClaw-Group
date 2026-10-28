# 项目规则（Trae）

开始任何任务前，先完整阅读仓库根目录的 `AGENTS.md` 并遵守其中全部规则；改代码前按其中“改代码前先读对应规范”一表阅读 `docs/standards/` 下的对应规范。

规则只维护在 `AGENTS.md`，本文件不另写条目，避免两份内容漂移。

三条安全硬约束（摘自 AGENTS.md，便于常驻）：

1. 默认拒绝，按 ID 取资源先取行再校验班级、学科、本人归属；
2. 身份只取自服务端会话，不采信请求中的 class_id、role 等字段；
3. 密钥只在本机 `.env`，不进代码、日志、响应、镜像与提交历史。

合并前必须跑 `make check`（Windows：`backend\.venv\Scripts\python.exe scripts\check.py`）并全部通过。
