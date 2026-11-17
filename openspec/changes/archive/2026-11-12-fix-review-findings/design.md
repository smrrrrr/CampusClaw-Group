## Context

问题来源完整阅读：reports/review-01.md、review-02.md、review-03.md、review-async-grading.md，docs/security-review-table.md，reports/security-precheck.md、security-fix-log.md、risk-authz.md、risk-concurrency.md、risk-transaction.md，及历史 docs/lesson-2-5-acceptance-2026-10-18.md。未发现独立 TODO/issue 清单。历史验收页明确声明已修复并指向 harden-foundation-and-align-specs，异步自检无新增未修复缺陷；本次不重开已关闭的历史事项。

## 评审问题与处置清单

| 来源/编号 | 核实结论与本次动作 |
| --- | --- |
| review-03 P0-1 | 评审记载重打包后关闭；当前工作树没有 manifest/restore.py 或数据包，不能再次核验外部包。修正交接说明仍残留的 55d18d3；不改包内数据或指纹 |
| P0-2 | 缺失实验属实；改用 apitest/probe_prompt_injection.py，可执行替身实验及 JSON，不伪称真实模型防注入评测 |
| P0-3 | 原探针无 SEC-08；补学生写入拒绝、教师对照、SSE 终止及业务快照断言 |
| P0-4 | writable 路径引用未定义 ctx；数据库身份校验替代该变量 |
| P0-5 | discovered/cache 未传 writable；宿主保守分类，重连与旧缓存检查 |
| P1-1 | 中间件仅 403/404；补 401，独立后台写入 |
| P1-2 | AuditLog 五列已有但未赋值/暴露；补调用、拒绝上下文与响应，不新增表列 |
| P1-3 | npm summary 丢明细导致分支不执行；保留包、锁定版本、全部 advisory，严格校验有效例外 |
| P1-4 | 历史 html.escape 属实；保留 Markdown，检验既有 ReactMarkdown 安全边界 |
| P2-1 | 下载注释与旧交接提交不一致；统一 404 注释和已验证的 70f0048 基线，保留原评审历史 |
| review-01 / 逐文件审核表 / risk-transaction | record_call 静默 rollback；两类审计失败均脱敏告警并注入故障验证 |
| 早期 SEC-02/05/06/07 | SEC-02 已实现 404；SEC-07 纳入上述修复；SEC-05 是运行环境证据边界；SEC-06 不升级依赖，严格门禁揭示未有效处置风险，不新造豁免 |
| 人工签名、真实队列/在线/真实模型证据 | 不是可由代码伪造的修复；在 validation 记录本次边界，保留待组员复现签名 |

## Goals / Non-Goals

只修复以上问题及直接测试依赖。所有修复在同一工作树，目标单一 review 修复分支；不运行 apply/archive、不勾选 tasks、按用户后续明确要求提交到 fix/review-lesson09-all，不推送。不升级依赖、不改变提示词、CSRF 合同、其他历史规约或后续功能。

## Decisions

1. **执行身份与分类**：不接受 role 参数作为权限依据，在 run_tool_loop 读取数据库 User。发现缓存 writable 默认 True；宿主仅信任已审阅的内置端点与两项只读工具，远端声明只能收紧权限。每次执行校验当前会话/技能/服务器/工具归属，兼容旧错误缓存。避免仅信任远端 readOnlyHint 或只改 ctx 后继续绕过。
2. **审计**：保留两张已有表，record_call 在同一独立事务写 McpToolCall 与 AuditLog；tokens 保存决策响应 usage.total_tokens；同轮多调用共享该数值，不可直接相加；上游未返回或无决策调用时为 null，不能伪造零。HTTP 拒绝审计经 BackgroundTasks 独立会话、服务端身份及匹配路由模板写入，匿名日志不归入某班。失败告警只记录固定事件名与状态，不记录异常原文。
3. **依赖门禁**：npm 原始 vulnerabilities 加锁文件实际 node_modules 路径版本，via 间接引用递归解析 advisory。缺明细/版本/通告、过期或无效日期均 fail closed。例外须精确 version 与 advisory 集合覆盖；旧的模糊 next/postcss 范围不能自动豁免新漏洞。pip 仍按已登记包处理，避免借本次 npm 修复扩大依赖策略；已过期例外仍阻断。
4. **历史渲染**：只去掉消息整体 escape，前端既有 ReactMarkdown 默认禁止原始 HTML 执行和危险 URL，显式 skipHtml；测试公式、代码块和恶意标签。无需引入新渲染依赖。
5. **证据**：保留历史报告；可执行实验位于 apitest，脱敏结果用 reports/security-evidence/*.json（现有跟踪规则），修改原交接命令。新增说明仅在本 OpenSpec 目录，不创建额外总结 Markdown。

## Risks / Trade-offs

- 未知第三方只读工具也默认按可写处理 → 学生拒绝，需将来单独审阅后更新宿主清单。
- 审计库故障仍可能丢记录 → 本次按现有“回答不中断”合同提供告警；不扩展为可靠队列系统。
- 旧依赖例外含模糊版本和通告 → 门禁应红，不为变绿升级依赖或扩大豁免。
- 无外部数据包、运行容器或组员签名 → 明确记录未复验，不能宣称课程全完成。

## Migration Plan

不改表结构，不操作教学库或 dev_seed。只读工具默认策略随代码更新；旧缓存执行时再分类。部署前按既有规范备份，回滚代码即可回滚本次行为。此任务不执行部署或恢复。

## 验证与评审

每项新 Scenario 对应 check_security_review、check_security_review_rendering 或原 check_mcp_tools/check_lessons_2_5。先运行新增检查获取修复前红项；完成后运行探针、注入实验、npm 门禁反例、make check 与 frontend build。验证原始结果与退出码记录 validation.md；这是实施者自检，人工复核仍待组员。主规约暂不同步，保留本变更 delta 供评审。
