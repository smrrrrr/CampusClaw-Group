# 项目可复现证据

此目录只放脱敏记录，不能放.env、数据库、上传资料、真实学生正文或令牌。运行时私有配置与临时数据库放被忽略的.review。

## 当前项目报告入口（2026-11-17）

正式六节报告是根目录 [report.md](../report.md)，历史长篇交付索引保留在 [project-history.md](project-history.md)。以下是本次整理的可核验材料：

- [三查与门禁复跑命令](reproduce-checks.md)、[本次验证范围与结果](project-validation.md)
- 三份具体评审：[扫描报告完整性](review-04.md)、[MCP写工具授权](review-05.md)、[运行镜像风险缓解](review-06.md)
- [人工交叉评审来源](peer-review.md)、[成员贡献与AI范围](contributions.md)
- [门禁保护与先红后绿时间线](project-gate.md)、[脱敏原始证据](project-evidence/README.md)
- [外部环境现场四步](live-demo.md)、[部署结果待验项](deployment-verification.md)
- [八分钟汇报与问答提纲](presentation-notes.md)、[提交核对表](submission-readiness.md)

## 历史与专项证据

本次提交顺序、验证和伙伴评审步骤见 [2026-11-05交付说明](submission-2026-11-05.md)。

- [异步作业AI初批：操作、复现与证据](async-grading/README.md)
- [2026-11-04：计数修正、学生作业历史与错题同步](assignment-history-2026-11-04.md)
- [2026-11-04：移除教研问答与课例分析](remove-research-pages/README.md)
- [并发检查](risk-concurrency.md)
- [事务检查](risk-transaction.md)
- [任务权限检查](risk-authz.md)
- [性能测量范围](bench.md)
- [本次审核记录](review-async-grading.md)
- [2026-11-05：七项安全自查](security-precheck.md)
- [密钥与依赖修复前基线](security-baseline.md)
- [首次安全评审与待完成的人工复现](review-01.md)
- [逐文件审核表](../docs/security-review-table.md)
- [换目录、本机 registry 与备份回滚演练](release-rollback.md)
- [流水线与 GitHub Actions 远端实跑](pipeline.md)
- [远端 CI 原始证据（Draft PR #3，run 43826707775）](lesson-10/20261116T075000Z-remote-ci/README.md)
- [独立分支故障重放（任务 7.3，PR #4 已关闭）](lesson-10/20261116T080640Z-ci-fault-replay/README.md)

上述历史记录按各自日期和版本解释。这里的本机自检、真实队列+假模型结果，不代替另一成员复现、真实模型质量或外网部署；人工交叉评审以实际Review为准。
