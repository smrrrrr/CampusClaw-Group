---
name: add-tests
description: 按 CampusClaw 测试规范为一组已实现的任务补齐离线回归检查（正常/失败/边界三类，断言值而非形状），并验证检查有效。每实现完 tasks.md 的一组任务后使用。
---

# 按规范补测试

输入：变更名（`openspec/changes/<变更名>/`）、刚完成的任务组。

1. 读 `docs/standards/04-测试规范.md`，列出本组任务涉及的全部 Scenario。
2. 选文件：扩展已有的 `apitest/check_<能力>.py`，或新建一个（门禁自动收集，无需登记）。结构参照 `apitest/check_baseline.py`：
   - `tempfile.TemporaryDirectory()` 下设置 `DATABASE_URL`、`UPLOAD_DIR`，再 import `main`；
   - 自建班级、教师、学生，令牌用 `security.create_access_token`；
   - 模型、MCP、外网请求一律 monkeypatch 替身。
3. 每个 Scenario 至少一条检查，检查名写成 `R<编号> <正常|失败|边界>：<场景要点>`。失败类至少覆盖 422、401、403（跨班 / 跨学科 / 学生调教师接口）、404、依赖不可达；越权成对写“他人账号”与“未登录”。
4. 断言值与数据变化：状态码 + 响应关键字段 + 数据库行数或字段 + 响应 / 日志中不该出现的内容。
5. 有效性验证：挑一条最关键的检查，临时改坏被测逻辑（删一个归属判断或改错一个状态码），确认它变红，再改回；把“改了哪里、哪条变红”写进变更的验证记录。
6. 运行 `make check`，全部 PASS 后结束。

产出：检查脚本、有效性验证记录、`make check` 输出尾部。
