# 独立分支故障重放（任务 7.3）

- 时间：2026-11-16（UTC）
- 目的：在**独立分支/Draft PR** 注入一个可逆断言失败，验证远端门禁会失败、镜像 job 不会产出可交付镜像；验证后关闭并删除分支。
- 故障分支：`ci-fault-replay`，提交 `a626a75`（基于 `6690202`）
- Draft PR：https://github.com/smrrrrr/CampusClaw-Group/pull/4（已关闭，未合并）
- 远端 run：https://github.com/smrrrrr/CampusClaw-Group/actions/runs/43828237591
- 失败 job：https://github.com/smrrrrr/CampusClaw-Group/actions/runs/43828237591/job/133167046778

## 注入内容

只改一处测试预期值，不碰业务代码、数据、密钥或部署文件：

```diff
- check("M2 边界：纯索引迁移不改分块数据", chunk_rows == 1)
+ check("M2 边界：纯索引迁移不改分块数据", chunk_rows == 2)
```

## 结果

| 项 | 结果 | 证据 |
| --- | --- | --- |
| 本机 `scripts/check.py` | 退出码 **1**，失败项 `check_lesson10_ops` | `local-check.txt` |
| 远端 `make check` job | **failure**，步骤“运行全量门禁”在 `check_lesson10_ops` 抛 `AssertionError: M2 边界：纯索引迁移不改分块数据` | `remote-check.txt`、`run-meta.json` |
| 远端 `make check-security` job | **failure** | 与本次注入无关；该 job 在正常分支上本就因 Next critical 与未登记 npm 包为 RED |
| 远端 `build-and-scan` | **skipped**（`needs: [check, security]`） | `run-meta.json` |
| 可交付镜像 | 未构建、未推送、无 digest | 同上 |

## 边界

- 本项证明的是：**注入的可逆故障会让远端 `make check` 失败，并使镜像 job 被跳过**。
- **不能**证明“required check 阻止合入”：当前账号对仓库 `admin=false, maintain=false`，无法配置 required checks 或分支保护（见 2.4）。因此 7.3 仍为部分完成。
- 故障分支已删除，PR 已关闭；`main` 与交付分支未包含该提交。

## 清理

- PR #4 已关闭；
- 远端分支 `ci-fault-replay` 已删除；
- 临时 worktree 已移除；
- 本目录只保留脱敏的 run 元数据与失败日志摘录。
