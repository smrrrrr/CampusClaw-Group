# 评审 05：MCP 写工具授权与上下文

整理/复跑日期 2026-11-17；历史问题发现记录日期 2026-11-12。手段为 AI 辅助源码核查与隔离脚本。原交叉评审上下文保留在 [review-03.md](review-03.md)，本次不代填其中的签名栏。

| 四项 | 记录 |
| --- | --- |
| 手段 | 阅读 `backend/mcp_client.py`、`backend/routers/mcp.py`、`backend/mcp_orchestrator.py`；临时 SQLite、假模型与假 MCP 下，对只读/写入、学生/教师/他科身份分别探测。 |
| 对象 | 写工具执行路径读取未定义的 `ctx`；发现/重连阶段未可靠保留 `writable` 分类，未知工具可能被当作只读。 |
| 判据 | 合法教师写工具可执行；学生写工具被拒且不改分；未知权限默认拒绝；拒绝后 SSE 正常结束并有审计；重连保留可信分类。SSE 的 HTTP 200 只说明连接成功，必须同时检查 denied 事件和实际写入。 |
| 结果 | 历史生产路径出现 `NameError`，对照实验留下原始记录；修复 `97ba0f5` 传递角色上下文并补权限核验。本次安全探针 41 通过、0 红项、exit 0，包含 SEC-08 四项正反与边界检查。 |

历史原始证据：[四组实验](security-evidence/review03-sec08.json)、[原评审发现 P0-4/P0-5](review-03.md)、修复提交 [97ba0f5](https://github.com/smrrrrr/CampusClaw-Group/commit/97ba0f5)。当前证据：[security-probe.json](project-evidence/security-probe.json)、[validation-runs.json](project-evidence/validation-runs.json)。

准备好后端依赖，在仓库根执行：

```text
python apitest/probe_security_precheck.py --output .review/security-probe.json
```

预期退出 0，查看输出 JSON 的 `SEC-08` 项，同时核对执行次数、拒绝事件和写入结果。探针自动创建临时库及合成身份，不读写教学库，不调用真实供应商。

常驻回归在 `apitest/check_security_gate.py` 与 `apitest/check_mcp_tools.py`，由完整门禁执行。人工风险取舍仍需实际参与人确认；自动脚本不替代真人签字。
