# 安全基线验证（续跑日期2026-11-05）

本变更于11月4日准备，网络恢复后于11月5日实际执行。仅新增观察工具、基线证据和说明，`skip_specs: true`；没有业务行为变化，不编造主业务Scenario。没有执行opsx-apply/archive，没有改变tasks勾选。

## 检查与证据

| 课程条款/文档要求 | 检查名或命令 | 本次结果 | 证据 |
| --- | --- | --- | --- |
| 身份准备 | 真实SQLite只读查询；PRE临时HTTP登录 | 4个真实身份存在；4个临时登录200；真实服务在线登录待验 | reports/security-evidence/accounts-readonly.json、api-probe.json |
| SEC-01 | probe的SEC-01 GET七路径 | 7条401，通过 | api-probe.json |
| SEC-02 | 本班/跨班下载、两班检索、A独有知识检索 | 隔离通过；课程404与项目403差异为红项 | api-probe.json |
| SEC-03/04 | 合法请求体的学生非法写入及快照比较 | 6条拒绝且相关业务状态不变 | api-probe.json |
| SEC-05 | secret_scan及本地历史/运行范围扫描 | 本地未检出；Docker引擎不可达，日志/产物待验 | secret-baseline.json、secret-scan.txt |
| SEC-06 | npm audit/pip-audit | 前端4包（1critical/2high/1moderate），后端5包48条通告；红项保留 | dependency-run.json、dependency-summary.json及原始审计JSON |
| SEC-07 | 合成Skill实际调用后读教师日志 | 调用和落库成功；持久日志缺三类字段，红项 | api-probe.json |
| 并发/事务/一致性 | check_async_grading.py | 57条PASS，内存队列+假模型 | async-offline.json |
| 检查有效性 | probe --mutate-access（临时进程内替换授权函数） | 跨班下载200并泄漏合成B正文，该检查变红；正常版本同项403 | api-probe-mutation.json对照api-probe.json |
| 完整门禁 | scripts/check.py | 27组PASS | full-check.txt |
| 业务源码未改 | 运行前后SHA-256对比 | 相同，仅针对声明的代码文件范围 | source-before.json、source-after.json |
| 文档可追溯 | 新增Markdown相对链接、要求与证据映射 | 见文档核查记录 | document-check.json |
| 人工评审/另机复现 | review-01本人填写 | 待执行，不代签 | reports/review-01.md |

上表证据均位于仓库`reports/security-evidence/`，另有明确路径的除外。原始起止时间、工作区HEAD、源码指纹和退出码见run.json；HEAD不能代表本地全部未提交改动。

安全入口退出1，既有正确性门禁退出0；两者结论不互相覆盖。不能认定安全要求全部完成或可正式合并/发布。没有改提示词/参数、模型和主业务规约；相应业务迁移/提示词评测不适用。人工审批、Docker运行检查及真实代理复跑尚缺证据。

环境说明：第一次未提权运行探针未完成，已中止；正式结果来自正常本机测试权限执行。此前断网/缓存权限造成的审计失败不计入漏洞数量，也不作通过证据。本轮未关闭安全门禁或削弱现有断言。
