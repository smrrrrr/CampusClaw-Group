## 1. 收集与规约

- [ ] 1.1 核对全部评审来源和已关闭事项，保留 design 逐条映射。
- [ ] 1.2 完成 proposal/design/三份 delta 并严格校验；保留任务未勾选，不运行 apply/archive。

## 2. 已授权的评审修复

- [ ] 2.1 修复工具执行身份、发现/缓存/重连权限分类及默认拒绝，以 check_security_review 与 check_mcp_tools 验证。
- [ ] 2.2 补 401 与技能审计字段、查询返回和存储失败告警，以 check_security_gate 故障注入及探针验证。
- [ ] 2.3 修复 npm 明细和精确例外校验及失败边界，不升级依赖，以 check_security_gate 精确匹配反例验证。
- [ ] 2.4 恢复历史 Markdown，在既有渲染边界验证安全，以 check_security_review_rendering 和历史接口逐字比较验证。
- [ ] 2.5 补 SEC-08 探针/实验及 JSON，修正交接说明和下载注释，以 probe_prompt_injection 及源码引用核对验证。

## 3. 验证与交付

- [ ] 3.1 新增正常/失败/边界回归，证明旧实现红、恢复后绿。
- [ ] 3.2 运行完整 make check、提示注入实验、前端构建及安全门禁，记录真实结果与限制。
- [ ] 3.3 最终差异核对、逐条处置与待确认记录写入 validation，不创建额外报告、不推送。

任务勾选保持未选是本次授权边界，不以未选表示已执行或未执行；实际结果以 validation.md 为准。此列表不授权额外 apply 后续功能。
