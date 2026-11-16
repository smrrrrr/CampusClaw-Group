# GitHub Actions 远端实跑证据（2026-11-16）

- PR：https://github.com/smrrrrr/CampusClaw-Group/pull/3（Draft，未合并）
- 分支：`deps/upgrade-a-b`
- 首个 run：43826358847（head `9618be7`）
  - `check` 失败：workflow 安装 `@openspec/cli@1.13.1`，npm 返回 404；这是 CI 配置错误，不是业务代码失败。
  - 修复：`fca85f7` 改为 `@fission-ai/openspec@1.13.1`，并加 CI6 静态断言。
- 第二个 run：43826707775（head `fca85f7`；PR 合并引用 `2ba142a`）
  - `make check`：**success**，远端 Ubuntu 上 41 组全部通过。
  - `make check-security`：**failure**；`security-run.json` 显示 `status=RED`、`has_blocked_scope=true`；未登记 npm 包 5 个，npm high+critical=1；演示库无四个种子身份，`accounts-readonly` blocked。
  - `build-and-scan`：**skipped**（`needs: [check, security]`）。
- 远端测试栈：GitHub runner 上 backend/frontend healthy、nginx 启动；随后安全门禁失败，清理步骤删除容器与卷。
- 本目录只含 run 元数据、脱敏计数/状态与安全证据；不含 `.env`、令牌、数据库或上传正文。
- 边界：这是“另一台 Linux 机器”的运行证据，不是“另一个人”；也不代表 7.2 的受控绿版本或 4.2 的远端镜像 digest。
