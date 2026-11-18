# 逐题批改验证

2026-11-18，Windows 本地工作区。

- `openspec validate 2026-11-18-store-quiz-item-grades --strict` 通过。
- `backend/.venv/Scripts/python.exe apitest/check_quiz_homework.py` 使用临时数据库和替身模型，112 项通过。新增检查覆盖缺题、重号、越界、跨班与跨学科拒绝，错题写入失败时事务回滚，旧页面对新作答不能写回。
- 三题各 5 分的案例，教师确认 `0、5、5`，总分为 67，学生列表与详情均可查看三题成绩。错题本只收录第 1 题，重复确认仍只有一条，改为满分则移除。
- 模拟旧库迁移两次，保留旧成绩、答案、账号与资料元数据，新增逐题列和题号索引。旧成绩没有推断出的逐题明细。
- 部署前用 SQLite 在线备份生成 `data/current/before-quiz-item-grades-20261118-142216.db`，完整性检查通过，匹配上传文件保存在 `.review/lesson10-local/before-quiz-item-grades-20261118-142216/uploads`。
- Windows 完整门禁 `backend/.venv/Scripts/python.exe scripts/check.py --json .review/lesson10-local/quiz-item-grades-check.json` 共 43 项通过，退出码 0。
- 本机 Compose 重建后，七项服务运行，`/health` 与 `/login` 返回 HTTP 200。镜像中的批改服务、异步批改服务和作业路由源码摘要与工作区一致。演示库新增逐题列与题号列，仍有一份 67 分的旧提交保留原成绩和空逐题结果。
- 对本机后端配置的 `deepseek-chat` 使用三道合成算术题抽查。模型逐题建议 `0、5、5`，服务折算为 67 分。抽查使用内存数据库。
