## MODIFIED Requirements

### Requirement: SSE 流式回答

学生提问后，系统 MUST 以 SSE（`text/event-stream`）返回增量文本和最终结果。命中技能时，系统 MUST 在第一个增量之前发送 `meta` 事件，含 `skill.name`；本轮存在工具调用或被拒引用时 `meta` MUST 含按发生顺序排列的 `tool_calls`（`ref`、`status` 为 ok/denied/error、成功提示摘要或失败原因）。服务端 MUST 在工具调用循环全部结束后、第一个增量之前只发送一次 `meta`，其中 `tool_calls` 为本轮全部调用的完整列表，本期不逐轮推送中间进度；无调用时 MUST 省略 `tool_calls` 而不是给空数组，未命中技能时不发送 `meta`。`tool_calls` MUST NOT 含令牌或服务器地址。前端 MUST 在回答正文开始前展示本次使用的工具及状态，并忽略不认识的事件类型；本期历史回显不恢复工具栏。

生成中增量尚未完成引用核对，前端 MUST 明示此状态；正常 done 事件 MUST 含已校验引用编号的最终答案、实际使用的 citations 和 remaining，并替换临时显示内容。异常 error 事件 MUST 包含最终 message、citations 和 remaining，不承诺额外 done。模型中断后的部分文本 MUST 同样核对编号；完全失败或未配置 Key 时 MUST 展示服务器生成的检索段落及其实际来源。反向代理 MUST 关闭 `/api/` 响应缓冲。

#### Scenario: 流式逐字输出

- **WHEN** 学生在会话内提问且 DeepSeek 正常
- **THEN** 前端显示生成中引用待核对提示，逐字渲染增量，最后用 done 中的最终答案和实际使用的有效来源替换临时内容

#### Scenario: 工具事件先于正文

- **WHEN** 学生提问命中绑定 `formula_hint@campus-tools` 的技能并发生一次成功调用
- **THEN** 事件顺序为 `meta`（含该引用、status=ok 与提示摘要）→ `delta` → `done`，页面在第一个字出现前已显示所用工具

#### Scenario: 多轮调用只推送一次 meta

- **WHEN** 学生提问命中技能，模型分两轮各提议一次 `formula_hint@campus-tools` 调用且均成功
- **THEN** 响应中只有一个 `meta` 事件，位于第一个 `delta` 之前，`tool_calls` 按发生顺序含两条 ok 记录

#### Scenario: 断开后的引用显示被拒

- **WHEN** 技能引用的服务器已断开或已删除，学生提问命中该技能
- **THEN** `meta.tool_calls` 中该引用为 denied，回答仍正常生成，不静默显示成功

#### Scenario: 多轮会话检索无命中时延续历史

- **WHEN** 本班没有相关分块被召回
- **THEN** 多轮会话仍调用模型，传入最近历史及本轮无新资料说明，可延续已有题目；不存在资料时如实说明，引用列表为空。旧单次 ai-question 接口仍直接返回无资料提示

#### Scenario: DeepSeek 失败时降级为检索段落

- **WHEN** 有相关分块但 DeepSeek 调用失败或未配置 API Key
- **THEN** error 事件包含降级 message、段落对应的结构化 citations 和 remaining；前端立即显示与保存到历史一致的最终内容及来源；不发起工具调用

#### Scenario: 流式结束写回会话

- **WHEN** 流式完成（无论成功或降级）
- **THEN** 系统把 user 消息和完成引用编号核对的 assistant 消息写回会话，sources 仅保存最终答案实际使用的来源，降级段落保存实际展示来源
