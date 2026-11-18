# 学生演示与角色刷新验证

2026-11-18，Windows 本机，`http://127.0.0.1:18090`。远端 `main` 为 `8964200`，本地版本 `3da68c5` 的提交树与该版本一致。应用镜像从包含本地修复的工作区单独构建。

- 一班教师登记和连接 `campus-tools`，发现 `formula_hint`、`unit_convert`，公式提示技能和二班使用同一配置。
- 浏览器登录教师与一班演示学生后刷新教师标签页，仍进入教师工作台。一班首页实际显示 3 份讲义。发起真实问答，结束后显示 `MCP 调用成功 · formula_hint@campus-tools`，刷新并重新打开同一会话仍可见。
- 二班的资料接口返回 5 份讲义。真实流式请求以 `done` 结束，返回 `formula_hint@campus-tools`，重新读取历史后引用一致。
- SQLite 备份 `data/current/before-student-demo-20261118-101211.db` 通过完整性检查；匹配上传文件副本保存在 `.review/lesson10-local/before-student-demo-20261118-101211/uploads`。隔离库连续迁移两次，旧回答文本和引用保持不变，旧记录的工具摘要为空。
- 本机用既有 Compose 参数重新构建，七项服务就绪。新增行为测试覆盖师生续期隔离、单角色登出、调用成功标志、班级改名和动态资料计数。
- 普通门禁 `backend/.venv/Scripts/python.exe scripts/check.py` 43/43，退出 0。
