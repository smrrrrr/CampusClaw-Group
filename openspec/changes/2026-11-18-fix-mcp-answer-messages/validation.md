# MCP 工具回答回归记录

2026-11-18，本机 Windows、Docker Compose、DeepSeek `deepseek-chat`。

| 核查 | 结果 |
| --- | --- |
| OpenSpec 严格校验 | 通过。 |
| MCP 回归 `apitest/check_mcp_tools.py` | 旧代码在新加的三项断言上失败（70/73，退出 1）。修复后连同额外的多轮配对断言共 74/74，退出 0。 |
| 安全探针 `apitest/probe_security_precheck.py` | 临时库与替身 41 项通过、0 红项。注入内容在后续决策与最终回答两个阶段均未转发，错误审计保留。 |
| 普通门禁 `backend/.venv/Scripts/python.exe scripts/check.py` | 43/43，退出 0。 |
| Compose 重建和启动 | 下列命令退出 0，七项服务就绪，`/health` 返回 `ok`。比对后端镜像中的三个修改文件的构建哈希，均与工作区相符。 |
| 真实学生提问 | 二班演示会话 `4`，请求 ID `701b7b501a2d495cb69096670d523794`。教师审计确认 `formula_hint@campus-tools` 状态为 `ok`，学生 SSE 有 155 个正文片段并以 `done` 正常结束。 |

本机联调实例从仓库根目录执行：

```powershell
docker compose -p campusclaw-lesson10-local -f docker-compose.yml -f .review/lesson10-local/compose.local.yml up -d --build --wait --wait-timeout 120 --force-recreate
```

联调覆写文件用于本机端口绑定和后端镜像标签。新环境使用仓库根目录的标准 Compose，准备本机 `.env` 后执行 `docker compose up -d --build --wait`。真实问答还需要可用的模型 Key，以及教师在目标班级已连接 MCP 并启用了相应技能。
