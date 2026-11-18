# 命题作业逐题作答验证

2026-11-18，Windows 本地工作区。

- SQLite 在线备份 `data/current/before-quiz-item-answers-20261118-153227.db`，`PRAGMA integrity_check` 为 `ok`。配套上传文件备份至 `.review/lesson10-local/before-quiz-item-answers-20261118-153227/uploads`。
- `openspec.cmd validate 2026-11-18-store-quiz-item-answers --strict` 通过，前端类型检查及后端分层检查通过。
- `backend/.venv/Scripts/python.exe apitest/check_quiz_homework.py` 通过 124 项。提交和重交、空题、错误题号、归属隔离、异步的逐题输入、错题讲解只接收对应题及旧库连续两次迁移均使用临时数据库和模型替身验证。
- 有效性验证在测试进程内临时把错题答案替换为旧的整卷原文，命中「旧错题的整份文本只取对应题号，历史仍保留原文」，退出码 1。恢复正常加载后 124 项通过，退出码 0。
- 完整门禁首次发现缺少题号字段的旧快照导致历史列表报错。回退到历史文本模式后，`backend/.venv/Scripts/python.exe scripts/check.py --json .review/lesson10-local/quiz-item-answers-retry.json` 通过 44 项，退出码 0。见[完整门禁记录](../../../reports/lesson-10/20261118-demo-updates/full-gate.json)。
- 本机 Compose 重建后，重启代理更新上游连接。`/health` 和 `/login` 返回 200。演示学生账号读到「立体几何作业3」第 2 题的单题作答 `A`，作业历史保留原始文本和三个按题显示的答案。
