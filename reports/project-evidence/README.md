# 项目报告原始证据

此目录只归档脱敏文本与JSON，禁止数据库、上传材料、口令和令牌。采集日期2026-11-17。

| 文件 | 来源与范围 |
| --- | --- |
| `github-snapshot.json` | GitHub API只读结果，包含PR #3/#5/#6状态、Review、main保护、红绿CI和job链接；不含API凭证。 |
| `validation-runs.json` | 本次三个定向检查的开始/完成时间、命令、退出码、代码基线、环境和受测源码/锁文件SHA-256。 |
| `async.json` | `apitest/check_async_grading.py`原始JSON输出，57条断言，临时库/内存队列/假模型。 |
| `security-probe.json` | `apitest/probe_security_precheck.py`原始输出，41条检查的预期、实际结果和通过标志；全部是合成身份/材料。 |
| `image-gate.txt` | `apitest/check_os_vuln_gate.py`原始输出，31条逻辑回归；Docker核验使用替身。 |
| `check.json`、`check.txt` | 完整普通门禁43/43、退出0，记录各子项和起止时间。 |
| `document-checks.json` | 六节、七类、相对链接、PDF两页及正文一致性、文件摘要。 |
| `demo-syntax.json` | 历史记录，旧版现场演示 PowerShell 片段的静态语法检查。新版录屏指引在 `reports/demo-recording.md`。 |

完整普通门禁与文档检查的范围、PDF来源核对见上一级 [project-validation.md](../project-validation.md)。

GitHub状态是采集时快照，不承诺未来不变。离线用例、远端CI、外部部署和人工Review分别标记，不合并成“全部实测通过”。本次未读真实教学库或调用供应商模型，未再次执行联网安全审计与镜像扫描。
