## MODIFIED Requirements

### Requirement: 消息与会话持久化

系统 MUST 将消息持久化到 `messages`，assistant 消息 MUST 保存经过编号核对的最终内容及实际使用的 sources（JSON 数组），含原 reference_id 和 file_sha256。历史 MUST 按时间正序回显并保留原来源；作为新一轮模型上下文时 MUST 仅取有限轮次，并去除旧 assistant 正文数字来源编号，避免沿用旧编号。旧无版本来源 MUST 明示未记录版本并禁止直接打开原文。

#### Scenario: 回显历史消息

- **WHEN** 学生重新打开某会话
- **THEN** 系统按时间正序返回该会话全部 user/assistant 消息，assistant 消息携带其溯源引用

#### Scenario: 仅带最近若干轮作为上下文

- **WHEN** 会话消息很多、学生继续追问
- **THEN** 系统只取最近 6 轮、最多 12 条消息，去除 assistant 历史中的数字来源编号后再传给模型；原持久化历史不被改写

历史接口 MUST 原样返回持久化 Markdown，不整体 html.escape；渲染沿用 ReactMarkdown，不启用原始 HTML 执行，危险链接不得执行。

#### Scenario: 历史公式代码与实时回答一致
- **GIVEN** 本人本班会话保存了含 `a < b` 的数学公式、代码围栏和 HTML 标签的回答
- **WHEN** 学生重新读取消息并经既有组件渲染
- **THEN** 接口正文逐字等于持久化值；公式无 katex-error，代码文本保留，script/img 事件属性和 javascript 链接不执行

#### Scenario: 历史消息权限不变
- **WHEN** 未登录或另一学生读取该会话历史
- **THEN** 分别返回 401/404，不返回消息正文
