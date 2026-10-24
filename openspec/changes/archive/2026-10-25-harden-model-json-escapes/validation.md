# 模型 JSON 反斜杠修补 · 实施与验收记录（2026-10-23 ～ 2026-10-24）

本文件记录 `harden-model-json-escapes` 实际执行的内容、验证结果与未覆盖项，按“实际跑过”口径填写。
tasks.md 的勾选状态未改动，由使用者决定。

## 实际执行

### 离线回归（tasks §4，不调用网关）

| 环节 | 命令/方式 | 结果 |
| --- | --- | --- |
| 修补规则单元用例 | `PYTHONPATH=backend backend/.venv/bin/python apitest/check_model_json.py` | **65/65 通过** |
| 命题集成 | `apitest/check_question_bank.py`（虚构 `stream_chat`） | **102/102 通过** |
| 备课集成 | `apitest/check_lesson_prep.py` | **119/119 通过**（含 2026-10-24 新增的「修补次数写入服务端日志且不含正文」） |
| 既有回归 | `check_research_materials` / `check_mcp_tools` / `check_sqlite_storage` / `check_lessons_2_5` | 54/54、62/62、16/16、122/122 全部通过 |
| 规约校验 | `openspec validate harden-model-json-escapes --strict` | valid；另有 1 条 INFO：`smart-question-generation` 主规约尚不存在，归档需排在 `add-smart-question-generation` 之后（见 tasks §6.1） |
| 真实失败样本回放 | 本机 scratchpad 中 2026-10-23 抓到的两份失败输出，经 `question_service.parse_output` 解析（样本含资料改编题与答案，**未入仓库**） | 两份旧解析均失败（`JSONDecodeError`）；新解析各得 5 题、0 个 gaps，修补 39 处与 5 处（与 design 表中单反斜杠命令数一致），所有字符串字段不含 U+0008 / U+000C；被静默解码的 `\frac`、`\begin` 已还原 |

以上回归在 2026-10-23 实现后跑过一次，2026-10-24 修复日志问题后又全部重跑，结果相同（`check_lesson_prep` 多出 1 条新断言）。

### 部署（tasks §5.1）

| 环节 | 方式 | 结果 |
| --- | --- | --- |
| 部署前备份 | 容器内 SQLite backup API → `data/current/before-harden-model-json-escapes-20261023-182651.db` | `integrity_check = ok` |
| 重建后端 | `docker compose --project-directory <仓库根> up -d --build backend` | 容器内 `model_json.py` 与本地逐字一致；`routers/quiz.py` 含 `escape_repairs`；网关配置（`course-chat`）保留；health 200 |
| 复测后备份 | 同上 → `data/current/after-real-retest-20261024-230801.db` | `integrity_check = ok`；含下文全部复测数据 |
| 日志修复后重建 | 同上 | 启动正常，health 200；容器内导入 `main` 后调用 `parse_student_output`，日志输出 `INFO: lesson_service - 学生稿 LaTeX 反斜杠修补 3 处`，正文公式已还原 |

### 真实复测：智能命题（tasks §5.2，2026-10-24，课程网关 `course-chat`）

参数与 2026-10-23 失败时相同：资料「第一章 空间立体几何.md」，知识点立体几何 + 空间向量，单选 2 / 判断 1 / 填空 1 / 解答 1，易 2 / 中 2 / 难 1。经浏览器以教师 TEA001 操作。

| 生成记录 | JSON 解析 | 通过 / 未通过 | `escape_repairs` | 未通过原因 |
| --- | --- | --- | --- | --- |
| #3 | 成功 | 5 / 0 | 0 | — |
| #4 | 成功 | 3 / 2 | 0 | 判断题、解答题：缺少字段 `options` |
| #5 | 成功 | 0 / 5 | 0 | 5 题均为「知识点超出本次所选范围」；其中填空题另有空位数与答案数不符 |

- 解析成功 3/3。对照：2026-10-23 同参数下页面 1 次 + 容器内重放 3 次，失败 3 次，全部是 `Invalid \escape`。
- 3 次 `escape_repairs` 都是 0：本次模型全部写成了双反斜杠，大概率是提示词第 6 条加了示例后的效果。**修补路径本身在真实环境里没有被触发**，它的正确性由上面的离线回归和真实样本回放证明。
- 未通过的原因都来自原有的字段、知识点、填空校验，与转义无关；按规约 MUST NOT 自动重试凑数，系统也确实没有重试。
- 入库的 8 道题，题干、选项、答案、解析都不含控制字符。
- 3 次生成共消耗约 34.8k tokens（网关「今日已用」从 0 涨到 34760）。

### 真实复测：逐题复核（tasks §5.3）

| 操作 | 题目 | 结果 |
| --- | --- | --- |
| 渲染检查 | 待复核列表 8 题 | 47 处 KaTeX 公式，0 个 `.katex-error`，没有漏渲染的原始 `$\…` |
| 通过 | #7 | 人工核对答案正确后点「确认已核对，通过」；状态 `approved`，事件 `approve` |
| 修改 | #6 | 在解析末尾追加一句含 `\overrightarrow`、`\frac` 的说明；revision 1→2，`modified_in_review=1`，仍为待复核；事件 `modify` 记录前后指纹；字段不含控制字符；页面 0 个渲染错误 |
| 驳回 | #1 | 模型把选项 B/C/D 和解析写成 `\vec{c$`、`\vec{c)`，缺右花括号，详情页 2 处 KaTeX 报错；以此为理由驳回，事件 `reject` 记录了原因 |

#1 的错误是模型自己写错了公式，不是转义问题；按 design 的 Non-Goals，修补只恢复字符，不修正公式。

### 真实复测：备课学生稿（tasks §5.4）

| 环节 | 结果 |
| --- | --- |
| 生成教师教案 | 新建「空间向量求夹角（复测）」（lesson_plans id=2，高二（1）班，45 分钟，资料同上）；草稿 3154 字，不含控制字符 |
| 审阅 → 定稿 | 勾选「我已核对…」后审阅通过，确认定稿 v1；仅本人可见，未发布到教研组 |
| 生成两份学生稿 | 均成功，`student_from_version = current_version = 1`；学生可见教案 716 字，讲义 1703 字 |
| 内容检查 | 两份都不含 U+0008 / U+000C、答案/解析/解答/教师提示标记、S 引用编号；公式命令（`\vec`、`\frac`、`\cos`、`\theta`、`\begin{cases}` 等）为正常 LaTeX |
| 渲染 | 学生可见教案 6 处、讲义 17 处 KaTeX，0 个渲染错误；讲义两张原图均加载成功 |
| 发布 | `lesson_publications`、`lesson_group_publications` 中 plan 2 均为 0 条，未发布到真实班级 |

备课（教案 + 两份学生稿）共消耗约 23.3k tokens（网关累计 34760 → 58036）。

### 实施中发现并修复：学生稿修补次数日志不输出（2026-10-24）

- **现象**：`lesson_service.parse_student_output` 用 `logger.info` 记录修补次数，但容器内这个 logger 的生效级别是 WARNING。uvicorn 只配置它自己的 logger，根 logger 没有处理器，INFO 被 Python 的兜底处理器丢掉。design §6 要求的「修补次数写服务端日志」在部署环境里实际没起作用。因此 §5.4 那次真实学生稿生成有没有发生修补，**无法事后确认**。
- **修复**：`backend/main.py` 增加 `_configure_app_logging()`，只给 `lesson_service` 挂 StreamHandler 并设为 INFO，`propagate = False`，第三方库（httpx 等）的 INFO 日志保持不放开。design §6 同步补了一句说明。接口行为和规约 Requirement 没有变。
- **回归**：`check_lesson_prep.py` 新增断言：logger 对 INFO 生效且有真实处理器；单反斜杠学生稿只写 1 条修补日志，次数为正整数，内容不含学生稿正文。本地运行实际输出 `修补 9 处`，与用例里的单反斜杠数一致。

## 未覆盖 / 未完成项

1. **真实环境下的修补路径**：3 次命题的 `escape_repairs` 都是 0；学生稿那次因为日志问题无法确认。「真实模型输出单反斜杠 → 线上修补 → 入库」这条链路，只能用 2026-10-23 的真实失败样本离线回放来证明，没有在线上实际触发过。
2. **日志修复后没有再做真实学生稿生成**：修复只在容器内用构造输入验证过，没有再花网关额度走一次真实生成。
3. **教师手工编辑写入控制字符**：命题的「修改」「通过」复用了同一校验器（含控制字符检查），但浏览器表单无法输入 U+000C，这条只由离线用例覆盖，没有在线上实测。
4. **学生端展示**：学生稿没有发布，所以没有以学生身份查看渲染效果。

## 观察（不属于本变更）

- **填空题多空位显示**：题干原文 `…的坐标为____，____，____。`（题目 #8）在前端被 Markdown 当作加粗分隔符，渲染成 `____，<strong><strong>，</strong></strong>。`，后两个空位消失。数据正确，只是显示错。
- **待复核详情的选项**：选项 A–D 显示原始 `$…$`，没有经过 KaTeX 渲染。
- 以上两项已另开会话处理，按项目规则先写 openspec 变更。
- **模型遵循度**：漏写空数组 `options`、知识点超出所选范围、公式缺右花括号，都被现有校验或人工复核拦下了。是否需要加强提示词，留待后续评估。
- **讲义配图语义**：讲义带了一张图注为「原解析图」的建系图，可能提前透露解题思路。规约写明不做图片语义检测，发布前需人工核对。
- **`check_mcp_tools.py` 会连外网**：运行时会尝试连接 `ai-gateway.devops.hello1023.com`。本次被沙箱拦截，62/62 仍通过；在不受限的网络里跑可能会消耗网关额度。这是既有行为，不是本变更引入的。

## 测试数据（保留）

按使用者要求暂时保留，便于继续核对或演示。需要还原时，可以用上面两份备份。

| 数据 | 内容 | 状态 |
| --- | --- | --- |
| `question_generations` | #1（2026-10-23，失败）、#2（2026-10-23，成功），#3–#5（本次复测） | 保留 |
| `question_items` | #1–#8（#1–#5 来自生成 #3，#6–#8 来自生成 #4） | #7 已通过，#1 已驳回，#6 已修改、待复核，其余待复核；都未组卷、未发布 |
| `question_events` | generate 4 条（#2–#5）、generate_failed 1 条（#1），approve、modify、reject 各 1 条 | 保留 |
| `lesson_plans` | id=2「空间向量求夹角（复测）」 | 定稿 v1，含两份学生稿，未发布 |
| 其他 | 2026-10-23 MCP 链路测试留下的服务器、技能、学生对话与工具调用审计 | 不属于本变更，保留 |

## 结论

解析修补、控制字符兜底、失败原因带行列、`escape_repairs` 计数，都已在离线回归和真实样本回放中通过验证。真实网关下，同参数的命题解析从 4 次失败 3 次变为 3/3 成功，备课学生稿生成、保存、渲染正常，且没有发布。实施中发现的修补日志不输出问题已修复并补了回归。真实环境里修补路径没有被触发、日志修复后没有再做真实学生稿生成，这两项如实列为未覆盖。

## 归档记录（2026-10-25）

- 经使用者明确指示，按上文记录勾选 tasks.md 并归档，全部任务完成；`openspec validate harden-model-json-escapes --strict` 通过。
- 6.1：`add-smart-question-generation` 已先归档。核对时发现本变更的 MODIFIED《结构化输出与逐题校验》缺少该变更后来补充的知识点归一规则（提示词逐字复制标签、字面包含向上归一、3 个 Scenario），已先合入本 MODIFIED 块。合入后与主规约逐行比对，差异只剩本变更新增的反斜杠修补、控制字符兜底与 4 个 Scenario。
- 已把 delta 合入主规约：`specs/smart-question-generation/spec.md`、`specs/smart-lesson-prep/spec.md` 各修改 1 条。
- 上文「未覆盖 / 未完成项」仍然成立，归档不代表已覆盖。
