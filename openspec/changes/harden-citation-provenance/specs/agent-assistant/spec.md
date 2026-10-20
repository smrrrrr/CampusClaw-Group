## MODIFIED Requirements

### Requirement: 教师的可配置提示词

教师 MUST 能按任教班级和自己的学科自定义 AI 解题助手的系统提示词，并能在任意时刻保存与重新读取。系统 MUST 将配置持久化（class_id、subject、teacher_id 联合唯一，各教师独立），关闭解题引导时，教师留空提示词 MUST 回退到内置默认提示词；开启时 MUST 使用固定引导框架，忽略已保存的自定义提示词但不删除它。教师 MUST 只能配置其任教班级（`teaching_classes` 范围内），越权配置 MUST 返回 403 并记录审计日志。

#### Scenario: 教师保存某班自定义提示词

- **WHEN** 教师在任教班级（如 class_id=101）保存一份自定义系统提示词
- **THEN** 系统将其持久化到本人/该学科/该班级的 AgentConfig，学生在该班关闭解题引导后提问时使用该提示词；开启引导时保留配置但使用固定引导框架

#### Scenario: 留空回退默认提示词

- **WHEN** 教师关闭解题引导并清空某班级的自定义提示词，或该班从未保存过配置
- **THEN** 学生在该班提问时使用内置默认提示词，保留 LaTeX 定界符及直接表达要求，并追加统一引用真实性约束；依据不足时必须如实说明

#### Scenario: 配置非任教班级被拒绝

- **WHEN** 教师尝试保存或读取一个不在其 `teaching_classes` 内的班级配置
- **THEN** 系统返回 403 Forbidden 并记录审计日志

### Requirement: SSE 流式回答

学生提问后，系统 MUST 以 SSE（`text/event-stream`）返回增量文本和最终结果。生成中增量尚未完成引用核对，前端 MUST 明示此状态；正常 done 事件 MUST 含已校验引用编号的最终答案、实际使用的 citations 和 remaining，并替换临时显示内容。异常 error 事件 MUST 包含最终 message、citations 和 remaining，不承诺额外 done。模型中断后的部分文本 MUST 同样核对编号；完全失败或未配置 Key 时 MUST 展示服务器生成的检索段落及其实际来源。反向代理 MUST 关闭 `/api/` 响应缓冲。

#### Scenario: 流式逐字输出

- **WHEN** 学生在会话内提问且 DeepSeek 正常
- **THEN** 前端显示生成中引用待核对提示，逐字渲染增量，最后用 done 中的最终答案和实际使用的有效来源替换临时内容

#### Scenario: 多轮会话检索无命中时延续历史

- **WHEN** 本班没有相关分块被召回
- **THEN** 多轮会话仍调用模型，传入最近历史及本轮无新资料说明，可延续已有题目；不存在资料时如实说明，引用列表为空。旧单次 ai-question 接口仍直接返回无资料提示

#### Scenario: DeepSeek 失败时降级为检索段落

- **WHEN** 有相关分块但 DeepSeek 调用失败或未配置 API Key
- **THEN** error 事件包含降级 message、段落对应的结构化 citations 和 remaining；前端立即显示与保存到历史一致的最终内容及来源

#### Scenario: 流式结束写回会话

- **WHEN** 流式完成（无论成功或降级）
- **THEN** 系统把 user 消息和完成引用编号核对的 assistant 消息写回会话，sources 仅保存最终答案实际使用的来源，降级段落保存实际展示来源

### Requirement: 消息与会话持久化

系统 MUST 将消息持久化到 `messages`，assistant 消息 MUST 保存经过编号核对的最终内容及实际使用的 sources（JSON 数组），含原 reference_id 和 file_sha256。历史 MUST 按时间正序回显并保留原来源；作为新一轮模型上下文时 MUST 仅取有限轮次，并去除旧 assistant 正文数字来源编号，避免沿用旧编号。旧无版本来源 MUST 明示未记录版本并禁止直接打开原文。

#### Scenario: 回显历史消息

- **WHEN** 学生重新打开某会话
- **THEN** 系统按时间正序返回该会话全部 user/assistant 消息，assistant 消息携带其溯源引用

#### Scenario: 仅带最近若干轮作为上下文

- **WHEN** 会话消息很多、学生继续追问
- **THEN** 系统只取最近 6 轮、最多 12 条消息，去除 assistant 历史中的数字来源编号后再传给模型；原持久化历史不被改写
