# 验收记录：fix-quiz-latex-and-option-layout

日期：2026-10-25（Asia/Shanghai）

## 结论

本变更的 tasks 0.1–3.5 已完成。公式结构检查同时覆盖生成、修改保存与通过；学生卷选择题按 A–D 分行并按题号宽度缩进。未修改数据库题目、已发布资料、答案卷格式、接口或前端渲染器，未调用真实 AI。

## 数据库备份

- 实现前以 Python `sqlite3.Connection.backup()` 备份当前数据库：
  `data/current/before-fix-quiz-latex-and-option-layout-20261025-125316.db`
- 大小：2,244,608 字节；备份库 `PRAGMA integrity_check` 返回 `ok`。
- 实现与回归过程未改写业务数据库；浏览器验收只执行登录、读取试卷及预览。

## 实现对应

| 范围 | 结果 |
| --- | --- |
| 公式校验 | `check_formula_structure` 忽略 `\$`，按 `$$…$$`、`$…$` 切分；检查残留 `$` 与公式内未转义花括号。 |
| 校验入口 | `validate_question` 对题干、选项、填空/解答答案字符串和解析逐字段追加原因，选项原因含 A–D 字段名。 |
| 提示词 | 第 6 条要求花括号成对，省略括号的命令改写为完整形式。 |
| 学生卷 | 题干与选项续行按 `len(f"{number}. ")` 缩进；单行选项使用硬换行，含换行的选项独立成段；选项按 A–D 排序。 |

## 自动化验证

| 检查 | 结果 |
| --- | --- |
| `PYTHONPATH=backend backend/.venv/bin/python apitest/check_question_bank.py` | **115/115 通过**（最终代码复跑）。 |
| 全部 `apitest/check_*.py` | 10 个脚本通过。环境未预装 pytest 的夹具自检使用 `UV_CACHE_DIR=/tmp/campusclaw-uv-cache uv run --with pytest --with requests ...` 执行，**9/9 通过**；未改项目依赖。 |
| 其余 Python 回归 | formula retrieval 11/11；lesson prep 119/119；lessons 2–5 122/122；MCP 62/62；model JSON 65/65；research materials 54/54；SQLite storage 16/16。 |
| 前端已有离线脚本 | `check_markdown_images.cjs` 14 个断言通过；`check_recent_history.cjs` 通过。 |
| 语法与格式 | `py_compile` 通过；本次修改文件的 `git diff --check` 通过。仓库其他既有文档改动不纳入本变更。 |
| `openspec validate --all --strict --no-interactive` | **22 passed，0 failed**。输出含其他变更的归档提示，不影响本次严格校验结果。 |

### 规约场景覆盖

`check_question_bank.py` 已增加并通过：

- #15 原样选项生成时拒绝，原因含「选项 D 公式花括号不配对」；
- 转义括号、`cases`、`\$`、混用公式与公式外花括号通过；
- 多余右花括号及 `$` 不成对拒绝；
- 修改引入不配对返回 400，内容和 `revision` 不变；
- 补齐后保存、通过，进入题库且 `modified_in_review=true`；
- 学生卷选项分行、硬换行及第 10 题四格缩进。

## Markdown 实际渲染

临时脚本：`/tmp/campusclaw-quiz-render.cjs`（未进仓库）。直接调用前端已安装的 react-markdown 9.0.1、remark-math 6.0.0、rehype-katex 7.0.1，输入由最终 `render_student_paper` 生成。

| design §4 场景 | 结果 |
| --- | --- |
| 四个单行选项 | 题干独立段落；选项段落有 3 个 `<br>`。 |
| 第 10–12 题 | 从一个 `<ol start="10">` 中取得 3 个 `<li>`，编号及所属关系连续；9 个硬换行。 |
| 行内公式 | 5 处 KaTeX，0 错误。 |
| 含 `$$…$$` 的选项 | A–D 独立段落，1 个 `katex-display`，无硬换行。 |
| 多行题干 | 两段题干及块级公式均在同一 `<li>`，选项仍在该题下。 |
| 单选、多选、填空、解答混排 | 分节与编号连续，解答题仍为 4 条 `<hr>`。 |

全部 6 组通过，`.katex-error` 均为 0。临时输出保存在 `/tmp/campusclaw-quiz-*.html`。

## 后端容器与浏览器

- 最终代码执行 `docker compose build backend && docker compose up -d backend`；容器状态 healthy。
- 运行容器以 `.venv/bin/python` 核对最终 `render_student_paper` 与公式检查，检查通过。
- `GET /api/health`：`{"status":"ok","database":"ok"}`。
- Chrome 156 + 临时 Playwright（未进仓库）打开 `http://127.0.0.1:8081/teacher/quiz`，以项目默认教师账号登录，选择试卷 3「实测：空间向量小测」并点击「预览学生卷」。
- 2 道选择题的题干与选项均分段；每题选项段落均含 3 个 `<br>`，A、B、C、D 各占一行。
- 页面共有 25 处 KaTeX，`.katex-error = 0`，`pageerror = 0`。
- 截图：`/tmp/campusclaw-quiz-paper3.png`；图中选项逐行显示，公式正常渲染。

## 已知限制

2026-10-25 复验时发现一处误判，经评审暂不修复，记录如下。

- **现象**：公式中的 LaTeX 换行 `\\` 直接贴着闭合的 `$` 时，被误判为「公式定界符 $ 不成对」，该题未通过。例如 `$$a=1\\b=2\\$$`、`$a\\$`。KaTeX（前端已安装版本）能正常渲染这两种写法。
- **原因**：`check_formula_structure` 先把所有 `\$` 删掉，再切分公式。`\\$` 是转义的反斜杠加闭合的 `$`，不是转义的美元符号，但其中的 `\$` 也被删掉了，于是闭合的 `$` 丢失。这与规约「转义的 `\$` 不计为公式定界符」的本意不一致。design §1 第 1 步也没有区分这两种情况。
- **影响面**：只有 `\\` 紧贴 `$` 时才会触发。常见的 `aligned` / `cases` 写法是 `\\\end{…}$$`，不受影响。复验时扫描当前库的题目，命中 0 处。
- **触发后的表现**：生成时该题不入库，页面显示缺口；修改或通过时返回 400。绕开办法：去掉末尾多余的 `\\`，或在 `\\` 与 `$` 之间加一个空格。
- **以后修复时**：只把前面有偶数个（含 0 个）反斜杠的 `\$` 当作转义的美元符号；在 `check_question_bank.py` 补 `$$a=1\\b=2\\$$`、`$a\\$` 两条通过用例；同时修正 design §1 第 1 步的措辞。这次修复在现有规约范围内，不需要改规约。
