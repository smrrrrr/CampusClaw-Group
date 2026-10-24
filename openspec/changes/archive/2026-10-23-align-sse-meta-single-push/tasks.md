## 1. 规约

- [x] 1.1 修改「SSE 流式回答」：工具调用循环结束后只发送一次 `meta`，并新增「多轮调用只推送一次 meta」场景
- [x] 1.2 删除 `harden-citation-provenance`、`harden-foundation-and-align-specs` 增量中过时的「SSE 流式回答」块，使 `openspec validate --all` 不再因这条需求失败

## 2. 验收

- [x] 2.1 `apitest/check_mcp_tools.py` 增加多轮调用用例：只有一个 `meta` 且为首帧（先于任何 `delta`/`done`/`error`），`tool_calls` 按序含两条 ok 记录
- [x] 2.2 回归 `check_mcp_tools.py` 全部通过，`openspec validate align-sse-meta-single-push` 通过
