# 第10课双门禁归档（任务 2.2）

- 批次：`reports/lesson-10/20261114T124804Z-gates/`
- 时间（UTC）：2026-11-14T12:48:04Z – 12:48:36Z（`make check`）
- 提交：`073ce993c6232753e5bd492d4efbe7ffd60d2f17`
- 环境：macOS 15.x（Darwin 24.6.0）；Python 3.12.15；Node 25.9.0；Docker 29.8.0
- 项目名：`campusclaw-group`（密钥扫描按此范围，`范围完整=True`）

## 一、命令与退出码

| 命令 | 退出码 | 结果 | 原始输出 |
| --- | --- | --- | --- |
| `backend/.venv/bin/python scripts/check.py --json <批次>/check.json` | **0** | **35/35 PASS** | `check.txt`、`check.json` |
| `COMPOSE_PROJECT_NAME=campusclaw-group backend/.venv/bin/python scripts/security_precheck.py` | **1** | **RED** | `security.txt` |

`check.json` 记录：`git_head=073ce99…`、`started/finished`、每步 `name/status/seconds/exit/finished`、`failed=[]`。

## 二、安全门禁明细

| 项 | 实测 |
| --- | --- |
| 密钥扫描 | 疑似泄漏 **False**，范围完整 **True** |
| npm | high=0、critical=1（仅 `next@14.2.15`）、low=4（katex 链） |
| backend pip | 0 漏洞 |
| mcp pip | 0 漏洞 |
| 课程高危判据 | `npm high+critical=1`；`pip 未判级且有漏洞=[]` |
| 未登记包 | `katex`、`micromark-extension-math`、`next`、`rehype-katex`、`remark-math`（仅 `next` 为 high/critical） |

## 三、结论

- 按课程口径第 1 条（允许适用性论证），`next@14.2.15` 的 4 条 critical 已逐条证明不可触发，详见 [next-risk-applicability.md](../../next-risk-applicability.md)。
- 因此任务 2.2 的“无课程高危红项”按**实际可利用性**成立，可收口。
- 但脚本判据仍为 RED，`npm audit` 计数不变；任何报告不得写成“安全门禁通过”或“高危 0 条”。
- 本批次未沿用历史 28 组、33/33 等旧数字；35 项为当前 `scripts/check.py` 实际收集结果，新增的 `check_frontend_image_safety`、`check_lesson10_scenarios` 逐项通过。
