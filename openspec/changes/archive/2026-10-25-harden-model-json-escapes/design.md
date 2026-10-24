## Context

智能命题（`question_service.parse_output`）和备课学生稿（`lesson_service.parse_student_output`）都要求模型「只输出一个 JSON 对象」，各自剥除代码围栏后直接 `json.loads`。两者的字符串字段都是含 LaTeX 公式的 Markdown。

2026-10-23 用课程网关 `course-chat` 实测命题（资料「第一章 空间立体几何.md」，知识点立体几何 + 空间向量，5 题）。页面 1 次、容器内同提示词重放 3 次，失败 3 次，错误都是 `Invalid \escape`：

| 样本 | 单反斜杠命令 | 双反斜杠命令 | 会报错的（举例） | 会静默解码的 |
| --- | --- | --- | --- | --- |
| 重放 1 | 39 | 89 | `overrightarrow` 17、`vec` 15、`end`、`sqrt`、`cos` | `frac` 3、`begin` 1 |
| 重放 2 | 5 | 112 | `overrightarrow` 5 | 无 |

成功的那一次也不能证明没有问题：只要所有单反斜杠恰好都落在 `\f \b \t \r \n` 开头的命令上，解析就会「成功」，公式却已被解码成控制字符。

## Goals / Non-Goals

**Goals**

- 模型把 LaTeX 反斜杠写成单个时，能按作者本意读出 LaTeX，不再整批失败。
- 已经被解码成退格、换页的公式不能悄悄入库或进入学生稿。
- 命题与备课学生稿共用同一套规则，避免两处口径不同。
- 用真实失败样本做离线回归，不依赖网关额度。

**Non-Goals**

- 不修复截断、缺字段、Markdown 正文等真正不合法的输出，它们仍整批失败。
- 不改用 function calling 或 JSON mode（原设计已说明理由，保持不变）。
- 不证明公式或题目语义正确；修补只恢复字符，正确性仍由教师复核。
- 不改智能备课教师教案（纯 Markdown 流，不经 JSON），也不改学生助手问答。

## Decisions

### 1. 共用函数 `backend/model_json.py`

```python
def load_model_json(raw: str) -> tuple[Any, int]:
    """剥除单层代码围栏 → 修补字符串内的 LaTeX 反斜杠 → json.loads。

    返回 (对象, 修补次数)。不合法时抛 ModelJSONError，消息带 json 报出的行列。
    """
```

- 围栏剥除合并两处现有写法：文本以 ```` ``` ```` 开头时，去掉首行围栏标记与结尾围栏。这样备课原来要求「首尾都是围栏」的判断也统一了，结果只会更宽松，不会更严格。
- `question_service.parse_output` 调用它，再照旧检查 `questions` / `gaps` 两个数组；`OutputParseError` 保留，消息改为带位置。
- `lesson_service.parse_student_output` 调用它，其余逻辑（字段集合、`\vspace` 替换、图片规范化、`validate_student`）不变，对外报错文案也不变。

### 2. 修补算法：只在字符串字面量内逐字符扫描

不用一条全局正则，原因是要区分「字符串内 / 外」以及「已经转义的 `\\`」。扫描时维护 `in_string`：

1. 字符串外：遇到 `"` 进入字符串；其他字符原样输出。
2. 字符串内遇到 `"`：退出字符串。
3. 字符串内遇到 `\`，看下一个字符 `c` 和紧随其后的连续 ASCII 字母串 `word`（含 `c`）：

| 情况 | 处理 | 例子 |
| --- | --- | --- |
| `c` 是 `\`、`"`、`/` | 合法转义，原样保留两个字符 | `\\frac`、`\"` |
| `c` 是 `u` 且后面 4 位都是十六进制 | 合法 Unicode 转义，保留 | `中` |
| `c` 是 `b`、`f`、`t`、`r`，且后面紧跟 ASCII 字母 | LaTeX 命令，补成 `\\` | `\frac`、`\beta`、`\times`、`\right` |
| `c` 是 `n`，且 `word` 在白名单中 | LaTeX 命令，补成 `\\` | `\neq`、`\nabla` |
| `c` 是 `b f t r n`，其余情况 | 合法控制字符转义，保留 | `\n第二步`、`\t` |
| 其他任何字符（含 `u` 后不满 4 位十六进制） | 非法转义，补成 `\\` | `\vec`、`\sqrt`、`\cdot`、`\underline`、`\{` |
| 字符串末尾的孤立 `\` | 补成 `\\` | — |

`n` 开头命令白名单（按整段字母串精确匹配）：`nabla ne neq neg not notin ni nu nmid nleq ngeq nless ngtr nexists newline nparallel nsubseteq nsupseteq nsim ncong nearrow nwarrow nleftarrow nrightarrow nLeftarrow nRightarrow nolimits`。

修补次数 = 被补成 `\\` 的位置数。修补后的文本只在内存中使用，不另存。

### 3. 为什么 `\n` 用白名单，而 `\b \f \t \r` 不用

- 退格、换页在 Markdown 题面里没有意义；制表、回车后面直接跟字母在模型输出里也不会出现（回车只以 `\r\n` 形式出现）。所以这四个后面跟字母就可以认定是 LaTeX。
- 换行后接一行以英文字母开头的正文是真实可能的（如「解：\nx=2」），不能一律当成命令，因此只认白名单里的命令名。

### 4. 控制字符兜底

修补之后若字段里仍有退格（U+0008）或换页（U+000C），说明有漏网的单反斜杠：

- 命题：`validate_question` 对 `stem`、`options[].text`、`answer`（字符串或字符串数组）、`explanation` 检查，命中则该题未通过，原因「含不可见控制字符，疑似公式转义错误」。生成、修改、通过三处复用同一校验器，所以教师手工编辑也受此约束。
- 学生稿：`validate_student` 增加同样的检查，命中时抛出与现有一致的「格式或去答案检查未通过」错误，旧学生稿保留。

制表符、回车不纳入兜底：它们可能是合法空白，误杀代价大于收益。

### 5. 提示词

- `QUESTION_PROMPT` 第 6 条改为：公式用 `$...$` 或 `$$...$$`；**JSON 字符串里每个 LaTeX 反斜杠都写成两个，例如 `"$\\frac{1}{2}$"`、`"$\\vec{a}$"`**；配图规则不变。
- `STUDENT_PROMPT` 的「所有反斜杠必须正确进行 JSON 转义」后补同样的示例。

提示词只降低出错率，正确性由第 2、4 条保证，不依赖模型配合。

### 6. 失败原因与审计

- 整体解析失败：生成记录 `error` 写成「模型输出不是合法 JSON（第 L 行第 C 列：<json 错误类型>）」。不写入模型原文，避免把资料摘录与答案再存一份。SSE `error` 帧文案不变。
- 命题 `generate` 事件 `detail` 增加 `escape_repairs`（整数，0 表示未修补），便于统计模型遵循程度。
- 备课学生稿没有独立的生成事件表，修补次数只写服务端日志（`logging.info`，不含正文）。uvicorn 只配置它自己的 logger，所以后端入口 `main.py` 要为 `lesson_service` 单独配置 INFO 处理器，否则这条日志会被丢弃；第三方库的 INFO 日志不放开。

### 7. 离线回归样本

真实失败输出包含教师资料改编的题目与答案，**不入仓库**（仅保留在本机）。仓库里放的是从中提炼的最小片段，覆盖各类情况：

- 两份失败样本的结构骨架：同一字符串里混用 `\\overrightarrow` 与 `\overrightarrow`、`\vec`、`\sqrt`、`\cos`、`\begin{cases}...\end{cases}`、`\frac`。
- 合法写法不受影响：`\\frac`、`\"`、`中`、`\n第二步`、`\nx=2` 中的换行。
- 白名单：`\neq` 补、`\nx` 不补。
- 不可修补：截断的 JSON、Markdown 正文、缺 `gaps` 仍失败。
- 兜底：手工构造含 U+000C 的题干，判未通过。

## Data Flow

```
stream_chat → raw
  → load_model_json(raw)
       剥围栏 → 字符串内修补反斜杠（计数）→ json.loads
       └ 失败 → ModelJSONError(行列) → 命题: failed 记录 + error 帧 / 学生稿: error 帧，旧稿保留
  → 命题: questions/gaps 检查 → validate_batch（含控制字符兜底）→ 落库 + generate 事件(escape_repairs)
  → 学生稿: 字段检查 → validate_student（含控制字符兜底）→ 保存
```

权限、并发锁、资料指纹核对、断开处理都不经过这里，保持原样。

## Risks / Trade-offs

- **误修补**：以 `\n` 开头、恰好拼成白名单命令名的正文（如换行后写裸文本 `ne`）会被改成 `\ne`。在中文题面里极少见；结果是多出一个字面命令，教师复核时可见，不会静默丢内容。
- **漏修补**：模型若写出 `\b` 后接非字母（如 `\b{`），会被当作退格保留，然后由控制字符兜底判为未通过，不会入库。
- **修补掩盖模型问题**：用 `escape_repairs` 计数保留可观测性；数值长期很高时可考虑换模型或改提示词。
- **归档依赖**：`smart-question-generation` 主规约要等 `add-smart-question-generation` 归档后才存在，本变更必须排在其后归档。
