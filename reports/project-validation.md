# 项目报告验证

日期2026-11-17。业务基线 `main@89642008b1a65ef0e73a31a5754f3286fc496873`，文档工作基线 `5cca99761cf9eb2290685a0c504b45dab9aaf4f3`（PR #6）。本次不改业务实现、模型、数据库、CI判据或旧任务勾选。

## 本次实跑

| 检查 | 结果 | 原始证据 |
| --- | --- | --- |
| 并发/事务/任务权限离线检查 | 57/57，exit 0 | [async.json](project-evidence/async.json) |
| 合成双班身份安全探针 | 41/41，0红项，exit 0 | [security-probe.json](project-evidence/security-probe.json) |
| 镜像门禁逻辑回归 | 31/31，exit 0 | [image-gate.txt](project-evidence/image-gate.txt) |
| 完整普通门禁 | 43/43，exit 0；2026-11-17 11:21:42-11:23:37 UTC | [check.json](project-evidence/check.json)、[check.txt](project-evidence/check.txt) |

环境为Windows、Python3.12.13；使用临时SQLite、假模型、假MCP，不操作教学数据。开始/结束时间、命令与源码SHA-256见 [validation-runs.json](project-evidence/validation-runs.json)。

完整门禁通过规约、分层、密钥扫描、前端类型与全部离线回归。工具为Python3.12.13、Node22.16.0、OpenSpec1.13.1；后端依赖与前端node_modules通过目录联接复用本机相同锁文件安装结果，源码仍从独立工作目录读取。初次受限执行环境的进程未产生结果，停止后在允许子进程的环境重跑，归档的是成功完成的这次。

本次未修改业务代码或降低检查标准；归档的HEAD是工作基线5cca997，执行时已有报告文档改动，不把它标成干净提交。本次普通门禁缺少本地.env时不会扫描其中秘密值，敏感文件与通用密钥模式检查仍运行。

## 文档与阅读副本检查

- 根报告恰好六节，AGENTS清单恰好七类，每类含问题、手段、判据与证据；三份独立评审与三查文件存在。
- 本次新增/修改Markdown的本地链接逐一核对，未发现文件目标缺失；统计见 [document-checks.json](project-evidence/document-checks.json)。代码围栏不作为Markdown链接解析。
- `reports/live-demo.md` 的PowerShell片段经PowerShell解析器检查，无语法错误；仅做静态检查，没有外部环境执行结果，见 [demo-syntax.json](project-evidence/demo-syntax.json)。
- `scripts/render_project_report.py` 通过Python语法检查，实际生成两页PDF；PDF全文提取与Markdown正文（剔除标记）一致，元数据的SHA-256与源文件字节一致。
- 用Poppler渲染两页并逐页查看，确认中文、长路径、表格、页脚清楚，无重叠或裁切。PDF是阅读副本，输出在 `output/pdf/`，不把它当第二份提交报告。
- 版面及证据整理后未变更业务代码，无需以重复全量测试代替文档验证。完整门禁记录仍使用上述实际时间，不改成最后文档编辑时间。

## 历史与远端证据

2026-11-17重新只读查询GitHub，PR #3已合并，main与PR #6相关CI均成功；PR #6仍Open无正式Review；main保护要求一次批准及三项检查。见 [github-snapshot.json](project-evidence/github-snapshot.json)。未把旧CI叫作本次工作区的新CI。

镜像扫描沿用带提交号的远端结果。本次未重新执行联网依赖审计、实际镜像构建/扫描、真实RabbitMQ故障实验、真实模型或公网演示。安全探针通过不等于完整安全门禁本轮通过。

## 待办与范围

- 教师提供外部地址后，补 `reports/deployment-verification.md` 与报告第五节。
- 新报告分支尚未推送、评审或合入main，不能引用旧批准冒充新批准。
- 真实姓名/学号如平台要求，由本人提供；三名用户、手机等历史验收项仍按原证据，不代签或扩大。
