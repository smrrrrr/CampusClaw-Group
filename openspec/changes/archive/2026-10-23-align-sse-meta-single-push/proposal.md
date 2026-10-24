## Why

`agent-assistant` 主规约「SSE 流式回答」要求命中技能时「每完成一轮调用推送一次累计列表」。实现（`backend/routers/student.py` 的 `event_stream`）是在 `run_tool_loop` 跑完全部轮次（最多 `MCP_MAX_ROUNDS` 轮）后只发一次 `meta`。只调用一轮时两者没有区别；多轮调用时，前端看不到中间进度。用户决定按现有实现改规约，不改代码。

同时，`harden-citation-provenance` 与 `harden-foundation-and-align-specs` 的增量里各有一份 MCP 之前的「SSE 流式回答」整块 MODIFIED。其内容已全部并入主规约，只是缺少 MCP 新增的部分；如果按原样归档，会把 MCP 的 `meta` / `tool_calls` 要求覆盖掉。这两处重复块已删除，本变更成为这条需求唯一的增量。

## What Changes

- 「SSE 流式回答」改为：工具调用循环全部结束后、第一个增量之前只发送一次 `meta`，`tool_calls` 为本轮全部调用的完整列表；本期不逐轮推送中间进度。
- 新增场景「多轮调用只推送一次 meta」。
- 其余要求与场景保持主规约现文不变：`meta` 先于正文、无调用省略 `tool_calls`、不含令牌与地址、引用核对、降级、写回会话、关闭代理缓冲。
- 从 `harden-citation-provenance`、`harden-foundation-and-align-specs` 的 `specs/agent-assistant/spec.md` 中删除过时的「SSE 流式回答」块。两个变更的其余增量不动。

## Impact

- 只改规约，不改代码与接口。前端本来就只在收到 `meta` 时整体渲染工具栏，不受影响。
- 验收：`apitest/check_mcp_tools.py` 增加多轮调用的断言（只有一个 `meta`，位于 `delta` 之前，含两条按序的 ok 记录）。
- 以后如果要逐轮显示进度，需另开变更：让 `run_tool_loop` 每轮回调，再由流式接口逐轮推送。
