# 成员贡献与 AI 使用来源

2026-11-17 按 `main@8964200` 的 Git 署名和 GitHub PR 元数据整理。此表说明可查贡献，不推断姓名、学号、工时、工作量百分比或组内正式分工。GitHub `hexzun1` 的 PR #3 包含 Git 署名为 Jackler 的提交。

| Git 署名 / 账号 | 可核验的贡献样本 | 提交/记录 |
| --- | --- | --- |
| Jackler / hexzun1 | MCP 集成、评审修复、依赖升级、运行验证 | `99f476e`、`97ba0f5`、PR #3 |
| Grey_Wolf_King | 作业批改/学情/错题功能，跨班权限、CSRF、注入反例、安全文档 | `e10c81b`、`76be9f2`、`4cfaa15`、`efbfb67`、`4ad52f5` |
| smrrrrr | 智能命题作业接入异步批改、作业历史、镜像门禁修复、正式 Review 与交付 | `6bb70e1`、`68acf9a`、`cc5b0fc`、`3da68c5`、PR #3 Review、PR #5、PR #6 |

仓库根复核：

```text
git log main --format="%h %an %s"
git show --stat 6bb70e1
git show --stat 97ba0f5
git show --stat cc5b0fc
git show --stat 3da68c5
```

如果本地还没有 main，先 `git fetch origin main`，将命令里的 main 改为 origin/main。PR 与 Review 公开链接见 [peer-review.md](peer-review.md)，原始状态见 [github-snapshot.json](project-evidence/github-snapshot.json)。

## AI 辅助范围与 Harness

可追溯样本包括 `backend/grading_service.py` 的异步任务实现及自检（`reports/review-async-grading.md`），以及 `scripts/trivy_os_gate.py`、`apitest/check_os_vuln_gate.py` 的 Codex 辅助修复（`reports/review-04.md` 与 PR #5）。代码经过后续人工/代理修订，不能据 Git 作者名推断每一行究竟由谁生成。

本次材料整理与脚本复核使用 Codex，直接读取 `AGENTS.md` 与相应规范。仓库另有 `CLAUDE.md`、`.trae/rules/project_rules.md`、`.cursor/rules/project_rules.mdc` 入口；存在配置不等于本次实际运行过这些 Harness。历史每次对话的模型版本没有完整运行记录，报告不编造统一模型名称。

正式交作业前，如平台要求真实姓名/学号/组号，由成员提供后映射到以上署名；当前报告用已核实的仓库署名。
