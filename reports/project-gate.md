# 门禁、审批与合并证据

截至 2026-11-17 的只读核验，来源为 GitHub API；可复核快照 [github-snapshot.json](project-evidence/github-snapshot.json)。本次没有更改保护规则。

## 当前保护

- `main` 要求一次正式批准，以及 `make check`、`make check-security`、`build-and-scan` 三项成功。
- `enforce_admins=true`，禁止强推与删除。
- 工作流在 `.github/workflows/lesson10.yml`，镜像构建依赖两项检查成功。红色检查不能作为通过结果。

## 先红后绿与合入时间线

| 提交 / 检查 | 实际结果 | 证据 |
| --- | --- | --- |
| `b068cb9` / PR #5 | 普通和安全检查成功，镜像检查失败 | [run 44022376165](https://github.com/smrrrrr/CampusClaw-Group/actions/runs/44022376165) |
| `3da68c5` / PR #5 | 缓解与镜像核验后，三项成功 | [run 44042306967](https://github.com/smrrrrr/CampusClaw-Group/actions/runs/44042306967) |
| `ca66b9a` / PR #3 候选 | 三项成功，随后 smrrrrr 正式批准这一 SHA | [run 44043187194](https://github.com/smrrrrr/CampusClaw-Group/actions/runs/44043187194)、[Review](https://github.com/smrrrrr/CampusClaw-Group/pull/3#pullrequestreview-5935012549) |
| `8964200` / main 合并 | 三项成功 | [run 44045260010](https://github.com/smrrrrr/CampusClaw-Group/actions/runs/44045260010) |
| `5cca997` / PR #6 文档 | 三项成功，PR 仍 Open 且没有正式批准 | [run 44053944407](https://github.com/smrrrrr/CampusClaw-Group/actions/runs/44053944407) |

修复细节与原始红绿输出在 [gate-red-green.md](gate-red-green.md)、[review-04.md](review-04.md)、[review-06.md](review-06.md)。不得将“job成功”解释为OS漏洞原始计数归零；镜像门禁使用有期限的书面例外。

## 证据边界

历史红 CI 和当前 required checks 分别证实检查能失败、现行主干要求这些检查；本次没有再次创建故障 PR 或尝试强行合并红灯，不能声称验证过 GitHub 对某次红提交的具体拒绝响应。PR #5 先合入源分支，API 中无该 PR 的正式 Review；不得伪造额外评审人。

新报告基于 PR #6 文档内容，尚未推送或合入 main。本次文档检查不代表新报告已经完成另一名组员批准。合并前应针对最终提交重新核对保护、检查和 Review，不能复用旧 SHA 的绿灯。
