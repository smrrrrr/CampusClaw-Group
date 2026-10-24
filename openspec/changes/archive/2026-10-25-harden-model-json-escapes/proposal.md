## Why

2026-10-23 后端改用课程网关（`course-chat`，openai 兼容）后，第一次用真实模型跑智能命题：4 次生成有 3 次因「模型输出不是合法 JSON」整批失败，一道题都没保存。

原因是模型在 JSON 字符串里写 LaTeX 时，常常只写一个反斜杠。抓到的两份失败样本里，单反斜杠命令分别有 39 个、5 个；双反斜杠写法分别有 89 个、112 个。同一次输出里两种写法混用，提示词已经要求「正确转义」也无法杜绝。问题分两类：

- **直接报错**：`\vec`、`\overrightarrow`、`\sqrt`、`\cos`、`\end` 里的 `\v`、`\o`、`\s`、`\c`、`\e` 都不是合法 JSON 转义，`json.loads` 抛错，整批作废。
- **静默损坏**：`\frac`、`\begin`、`\times`、`\theta`、`\right`、`\neq` 开头的 `\f`、`\b`、`\t`、`\r`、`\n` 恰好是合法转义，会被解码成换页、退格、制表、回车、换行。解析成功，但公式已经坏了（`\frac` 变成「换页符 + rac」），校验不报错，题目照样入库。

智能备课的学生稿（`parse_student_output`）用同一种 JSON 输出口径，提示词里也写了「所有反斜杠必须正确进行 JSON 转义」，同样会受影响；它还没在真实模型上复测（当天额度不足）。

现行规约《结构化输出与逐题校验》只允许剥除代码围栏，「整体不是合法 JSON……本次生成失败」。要容错，必须先改规约。

## What Changes

- 新增一个共用的模型 JSON 解析函数：剥除外层代码围栏后，**只在 JSON 字符串字面量内部**修补 LaTeX 反斜杠，再交给 `json.loads`。命题和备课学生稿都改用它。
- 修补规则是确定的，只针对 LaTeX 命令：
  - 反斜杠后面不是合法 JSON 转义字符时，补成两个反斜杠（`\vec` → `\\vec`）。
  - `\b`、`\f`、`\t`、`\r` 后面紧跟 ASCII 字母时，视为 LaTeX 命令，补成两个反斜杠（`\frac`、`\beta`、`\times`、`\right`）。
  - `\n` 只在后面的字母串是已知 LaTeX 命令（`\neq`、`\nabla`、`\not`、`\nu` 等，见设计白名单）时才补，否则保留为换行，避免把「换行 + 正文」误改。
  - 已经写成 `\\`、`\"`、`\/`、`\uXXXX` 的合法转义不动；字符串外的内容不动。
- 两处提示词补一条明确示例：JSON 字符串中每个 LaTeX 反斜杠都写成两个（如 `\\frac`）。
- 逐题校验增加一条兜底：任一文本字段含退格（U+0008）或换页（U+000C）时判为未通过，原因为「含不可见控制字符，疑似公式转义错误」；学生稿同样拒绝。
- 命题生成事件 `generate` 的详情增加修补次数 `escape_repairs`；整体解析失败时，失败原因带上 `json` 报出的行列位置。
- 回归：在 `apitest/check_question_bank.py`、`apitest/check_lesson_prep.py` 中加入离线用例，样本由真实失败输出提炼而成，不花网关额度。

## Capabilities

### Modified Capabilities

- `smart-question-generation`：《结构化输出与逐题校验》允许在解析前修补 LaTeX 反斜杠，新增控制字符兜底与相应场景。
- `smart-lesson-prep`：《从定稿生成两种学生稿》学生稿解析采用同一修补规则与控制字符兜底。

## Impact

- 代码：新增 `backend/model_json.py`；改 `backend/question_service.py`（`parse_output`、提示词、校验器）、`backend/lesson_service.py`（`parse_student_output`、`STUDENT_PROMPT`）、`backend/routers/quiz.py`（事件详情、失败原因）。不改接口路径、请求或响应结构，不改数据库表结构。
- 不改变的部分：缺少 `questions` / `gaps`、Markdown 正文、截断等真正不合法的输出仍整批失败；逐题校验、配额、引用、去答案检查规则不变。修补只让「本来就是 LaTeX 的反斜杠」被正确读出，不保证题目语义或公式正确，仍由教师复核。
- 归档顺序：`smart-question-generation` 目前只存在于未归档的 `add-smart-question-generation` 变更中。本变更须在它归档之后再归档，否则 MODIFIED 找不到主规约中的需求。
- 验收：离线回归用真实失败样本提炼的片段；真实模型复测（命题 + 备课学生稿）在网关额度重置后进行，结果写入本变更的 `validation.md`。
