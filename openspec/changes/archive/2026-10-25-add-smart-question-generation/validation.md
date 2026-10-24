# 智能命题 · 实施与验收记录（2026-10-23）

本文件按「实际跑过」口径记录 `add-smart-question-generation` 的执行与验证结果。

## 实际执行

| 环节 | 方式 | 结果 |
| --- | --- | --- |
| 分支 | `git checkout -b feat/smart-question-generation` | 已建 |
| 数据库备份 | SQLite backup API → `data/current/before-smart-question-generation-20261023-004013.db` | `integrity_check=ok`，27 张表，4 用户/7 资料/1 教案/2 教研资料 |
| 知识点词表 | `knowledge_tags.TOPICS` | 六学科齐备（math 24、physics 17、chinese 7、english 8、chemistry 7、biology 7） |
| 数据模型 | 启动 `create_all` | 新增 6 张表（question_generations/items/papers/paper_items、quiz_publications、question_events），共 32 张表，旧表不变 |
| stem_key/content_sha256 | 单元断言 | 全角/半角、多余空白归一后 key 相同；content_sha256 与键序无关 |
| 校验器 | 单元断言 | 部分通过场景得 6 通过 2 未通过（答案 E、引用 S9 各 1 题） |
| 组卷算法 | 单元断言 | 单选 10→3/5/2；解答 3→1/1/1；合计 13 题 80 分 |
| 隔离验收 | `apitest/check_question_bank.py`（临时库 + 虚构 stream_chat） | **41/41 通过**：配额 400、词表外 400、跨科 404、全部通过/部分不合格、非 JSON 不落题、无 Key 503、他人候选 404、学生 403、未确认 400、通过入库、重复 409、驳回后通过 409、入库不可改 409、复制、题库可见、组卷 13/80、题库不足 422、学生卷去答案、定稿、草稿发布 409、越权 403、发布两班、is_indexed=False、重复复用、答案卷、事件 |
| 回归 | `check_lesson_prep`/`check_research_materials`/`check_mcp_tools`/`check_lessons_2_5`/`check_sqlite_storage` | 112/112、54/54、39/39、122/122、16/16 全部通过 |
| 前端 | `tsc --noEmit`、`next build` | 通过；`/teacher/quiz` 产出 |
| OpenAPI | 生成 schema | 18 个 quiz 路径全部有 summary |
| Docker 端到端 | `docker compose up -d --build backend frontend`，经 8081 | 无 Key 生成 503；造题后组卷 13 题/80 分 → 定稿 → 学生卷预览不含答案/解析/S编号 → 未确认 400、混班 403 → 发布 101+102 成功、学生资料页可见试卷、`is_indexed=0`、标签含「试卷/学生版」；同伴读试卷 404、学生读题 403、同伴列表 0 条 |
| 演示库 | 端到端后清理测试数据 | 恢复基线（4 用户/7 资料/1 教案/2 教研资料），integrity ok |

## 未覆盖 / 未完成项

1. **真实 DeepSeek 生成链路**：本机 `.env` 无 `DEEPSEEK_API_KEY`，端到端只验证了 503 与「造题后」的后半链路（组卷/定稿/发布/越权）。真实模型生成 → 解析 → 校验 → 落库的完整链路，已在 `check_question_bank.py` 用虚构 `stream_chat` 覆盖，但未对真实 DeepSeek 复测。
2. **前端浏览器逐项点按**：四个标签页只做了类型检查与构建，未在浏览器中逐项操作验证交互细节。
3. **任务 9.3 的「交叉复核并签字」**：与 MCP 变更一致，同伴签字需由另一位组员完成，本次未做。
4. **语义正确性**：编号与指纹只证明来源身份，题目/答案/解析是否被原文支撑仍由教师复核；本实现不宣称自动证明。

## 复查修复（2026-10-23）

复查发现 5 项与规约不符，均已修复。没有改动规约与 tasks.md 勾选。

| # | 问题 | 修复 | 验证 |
| --- | --- | --- | --- |
| 1 | 所选资料带配图时生成直接异常（`validate_links` 收到字符串列表） | `question_service._asset_catalog` 包装为 `{name}` 对象；`routers/quiz.py` 补 `Path` 导入，入库时给配图快照补原图 `path`/`mime`（`_asset_files`） | 带图资料生成：不含图、引用原图均通过；引用不存在的图判为未通过 |
| 2 | 含图题无法通过复核与发布 | `_edit_context` 改用题目自身 `assets_json` 中的图名；`_collect_assets` 在旧快照缺路径时回查原资料，复制前核对 SHA-256 | 含图题通过 200；发布后 `MaterialAsset` 名称、指纹与原图一致；原图被替换后发布 409 |
| 3 | 蓝图题型顺序与学生卷分节顺序不同时，答案卷题号与学生卷错位 | 新增 `ordered_items`，学生卷与答案卷共用同一排序 | 蓝图「解答在前、单选在后」与草稿手工倒序两种情况，学生卷与答案卷题号逐条一致 |
| 4 | 前端判断题、填空题答案无法保存（统一按字符串提交） | 编辑框按题型转换：判断题下拉转布尔，多选逗号分隔转数组，填空每行一空转数组 | 接口用例：判断题改为 `false`、填空改为数组均 200；`tsc` 通过 |
| 5 | 草稿编辑界面缺失（任务 7.4） | 新增 `DraftEditor`：上移/下移、删除、改分值（0.5 步长校验）、从本学科已入库未下架的同题型题目替换，携带 `revision` 保存；有未保存修改时禁用定稿 | `tsc`、`next build` 通过；接口用例覆盖 PUT 换题、改分值 |

另外，教师端题目、草稿和学生卷预览中的配图改走原资料取图接口（`quizImageUrl` → `/api/teacher/research-materials/{id}/assets`），不再显示为坏图。

实际跑过：

| 命令 | 结果 |
| --- | --- |
| `PYTHONPATH=backend backend/.venv/bin/python apitest/check_question_bank.py` | **57/57 通过**（新增 16 条：带图资料生成 3、含图题快照与复核 2、判断/填空答案修改 3、题型顺序打乱 5、含图发布与指纹 3） |
| 回归 `check_lesson_prep`/`check_research_materials`/`check_mcp_tools`/`check_sqlite_storage`/`check_lessons_2_5` | 112/112、54/54、39/39、16/16、122/122 |
| `npx tsc --noEmit` | 通过 |
| `docker compose up -d --build backend frontend`（含 `next build`） | 构建成功，backend healthy；容器内代码为修复后版本 |
| 8081 冒烟（TEA001 令牌） | `knowledge-points` 200、`items` 200、教研资料配图接口 200 `image/png`；未登录访问 `/teacher/quiz` 307 |

本轮仍未覆盖：草稿编辑与答案编辑没有在浏览器中逐项点按，真实 DeepSeek 生成仍未复测（Key 无效）。

### 第二轮：三处小问题（2026-10-23）

三处行为都已在既有规约中写明，本轮没有改动规约：修改事件含前后指纹见 spec「命题审计记录」，生成后核对资料指纹见 design §3，断开属于生成失败、须留记录见 spec 审计清单与 design §12。

| # | 问题 | 修复 | 验证 |
| --- | --- | --- | --- |
| 6 | 修改事件的「修改前」指纹只对题干和答案原文取哈希，与题目存储的指纹口径不同，前后对比无意义；入库指纹还混入了批次内序号 `index` | 新增 `_content`，生成入库与修改共用同一口径（校验后的题目、不含 `index`）。修改事件的 `before` 取题目当前存储的指纹；`modified_in_review` 只在内容确实变化时置真 | 原样保存：前后指纹相同，不计为修改；改写解析：前指纹接上一条的后指纹，后指纹变化，计为修改；最后一条后指纹等于题目当前指纹 |
| 7 | `hashes` 计算后未使用，生成结束后没有再核对资料 | 新增 `_changed_sources`，解析后、落库前比对生成前的资源快照：资料被删除或改学科、正文指纹变化、所用原图指纹变化，均整批作废，写失败记录并发 `error` 帧 | 生成期间分别替换正文指纹、替换原图指纹、删除资料：三种情况均返回 `error`、不落题、写失败记录；恢复后再生成正常 |
| 8 | 客户端断开时只抛出取消，不写失败记录和事件 | 检测到断开时写失败记录（含 `generate_failed` 事件）后结束流；服务端取消或关闭流（`CancelledError` / `GeneratorExit`）时，若尚未写入结果，也补写同一失败记录；任务锁仍在 `finally` 中释放。保存题目异常时也补写失败记录 | 模拟 `is_disconnected` 为真：无 `done`、不落题、写失败记录与事件；直接驱动生成流，读到首帧后关闭：不落题、写断开失败记录、任务锁已释放 |

实际跑过：

| 命令 | 结果 |
| --- | --- |
| `PYTHONPATH=backend backend/.venv/bin/python apitest/check_question_bank.py` | **68/68 通过**（本轮新增 11 条：指纹口径 3、生成后指纹核对 4、断开审计 4） |
| 回归 `check_lesson_prep`/`check_research_materials`/`check_mcp_tools`/`check_sqlite_storage`/`check_lessons_2_5` | 112/112、54/54、39/39、16/16、122/122 |
| `docker compose up -d --build backend` | 构建成功，backend healthy，容器内为本轮代码 |
| 8081 冒烟（TEA001 令牌） | `knowledge-points`、`items`、`events` 均 200 |

断开的两条用例是在临时库中模拟的：一条替换 `Request.is_disconnected`，一条直接关闭生成流。真实浏览器中途关闭页面的情况没有在 Docker 上手工复测。

### 第三轮：代码审查发现的 5 项正确性问题（2026-10-23）

这些行为在既有规约中都已写明，本轮没有改动规约。依据如下：答案卷须附出处，见 spec「答案卷」；逐题校验、不合格题只作废本题，见 spec 结构化输出与逐题校验；生成失败须留记录，见 spec 审计清单与 design §12；同一教师同时只有一个命题任务，见 design。

| # | 问题 | 修复 | 验证 |
| --- | --- | --- | --- |
| 9 | 答案卷的「出处」始终为空：`render_answer_key` 要先检查快照的 `source_refs` 非空，才会输出出处段。但快照（`serialize_item`）里没有这个字段，出处只存放在 `sources` 里，于是整个出处段都被跳过 | 答案卷改为读取 `sources`，逐条输出 S 编号、资料名、原文行号与摘录 | 含图试卷的答案卷有 `**出处**：S1`，且有 `> [S1] 立体几何配图.md 原文行 …`；行号与摘录和题目快照逐字一致 |
| 10 | 模型返回的字段类型不符时，校验器直接抛异常（如 `stem` 为数字、`type` 为数组、选项文本为数字、`explanation` 为对象），整条生成流中断 | `validate_question` 中的题型、难度、来源均先判断是否为字符串；题干、解析、选项文本都只取字符串参与正则与链接检查。`validate_batch` 外加兜底：校验器自身出错也只作废当前这一题 | 1 道合格题与 6 道字段类型错误的题混合生成：正常结束、没有 error 帧，合格题入库 1 道，其余 6 道逐题未通过且都附原因。直接调用 `validate_batch` 传入对象题干、字符串、`None`：不抛异常，3 题均被拒绝 |
| 11 | 生成流中出现其他意外异常时，既不写失败记录，也不通知客户端 | `stream()` 增加 `except Exception`：尚未落库时先回滚，再写失败记录（含 `generate_failed` 事件），并发送 `error` 帧；若结果已落库，则照常抛出 | 把 `validate_batch` 替换为抛出 `RuntimeError` 的函数：收到 error 帧、无 done、不落题，有含「生成过程出错」的失败记录和事件，任务锁已释放 |
| 12 | 任务锁泄漏：锁在路由函数里登记，到流式生成器的 `finally` 才释放。如果响应还没开始就被丢弃，生成器从不运行，锁会一直留着，该教师从此无法再生成 | 登记改为带令牌和开始时间。超过 `GENERATION_LOCK_TTL`（300 秒，大于 180 秒的生成超时）的登记视为残留，允许重新登记。释放时核对令牌，过期旧任务不会误删新任务的登记 | 直接调用 `create_generation` 但不迭代响应：锁仍在，再次生成返回 409。把登记时间调到超过 TTL 后：可以重新生成，结束后锁已释放。用旧令牌释放：新登记保留；用新令牌释放：登记清空 |
| 13 | 并发请求能绕过「单任务」限制：原先先检查、后登记，两步不在同一把锁内；`create_generation` 是同步路由、在线程池中执行，两个请求可能同时通过检查 | 检查和登记合并为 `acquire_generation`，在同一个 `threading.Lock` 内完成；路由在资源构建之后、返回流之前登记 | 20 个线程经 `threading.Barrier` 同时登记同一教师：恰好 1 个拿到令牌。释放后可以再次登记 |

实际跑过：

| 命令 | 结果 |
| --- | --- |
| `PYTHONPATH=backend backend/.venv/bin/python apitest/check_question_bank.py` | **83/83 通过**（本轮新增 15 条：答案卷出处 2、字段类型 3、意外异常 3、锁残留与令牌 5、并发登记 2） |
| 回归 `check_mcp_tools`/`check_formula_retrieval`/`check_lesson_prep`/`check_research_materials`/`check_sqlite_storage`/`check_lessons_2_5` | 58/58、11/11、112/112、54/54、16/16、122/122 |
| `node apitest/check_markdown_images.cjs`、`node apitest/check_recent_history.cjs` | 通过 |
| `docker compose up -d --build backend` | 构建成功，backend healthy，容器内为本轮代码 |
| 8081 冒烟 | `/api/health` 200；未登录访问 `knowledge-points` 401；后端日志无报错 |

本轮未覆盖：

- 锁残留是用「直接调用、不迭代响应」模拟的，并发是在线程层面直接验证 `acquire_generation`。两者都没有在 Docker 上用真实的并发 HTTP 请求复测。
- 8081 冒烟没有带教师令牌，没有在容器内重跑生成链路。

### 第四轮：代码审查其余 5 项（2026-10-23）

只有第 15 项改变了存储行为，因此先改了 `design.md` §3「快照写入」，再实现。其余 4 项要么与既有规约一致，要么只涉及测试与文档：第 14 项按 spec「原作者可下架 / 恢复」处理；第 16–18 项属于 MCP 变更的测试与 OpenAPI 说明。

| # | 问题 | 修复 | 验证 |
| --- | --- | --- | --- |
| 14 | 题库详情对所有入库题都显示「下架 / 恢复」，而后端只允许原作者操作，非作者点了返回 404「题目不存在」 | `GET /items/{id}` 增加 `can_archive`（入库题且本人是作者）；前端据此显示按钮，非作者显示「仅原作者可下架 / 恢复」。后端权限不变 | 作者为真；同科非作者为假，且直接调用下架仍返回 404；待复核题为假；`tsc` 通过 |
| 15 | 每道题都写入整批资料的全部配图，与代码注释不符，并且修改时可以插入出处以外的任意配图 | 新增 `_item_assets`：只保存本题出处所在资料的配图，再加上题面（题干、选项、答案、解析）实际引用的配图。修改与通过复核仍以这份清单为准。`design.md` §3 同步改写 | 函数级 3 条：只含出处资料的配图；另加题面引用的他资料配图，但不带其余配图；都不满足时为空。接口级：同时选纯文字资料与配图资料生成两题，每题清单都只来自出处资料或题面引用，含图题保留原图。变异检查：改回整批照抄后，接口级这条失败 |
| 16 | `CHAIN.py` 的 ok 审计用例只在 error 帧时跳过；模型自行决定不调工具（合法行为）时会误报失败 | 提问中明确请模型先用公式提示工具；模型没有提议调用时跳过并写明原因；已提议的调用必须为 ok，否则失败 | 新增 `apitest/check_apitest_harness.py`，用伪造的事件与接口驱动该用例。未调用：跳过并写明原因；error 帧：跳过；调用为 error：失败；ok 但查不到记录：失败；ok 且查得到记录：通过 |
| 17 | `conftest.py` 默认学生账号 `20230002` 不在开发种子中 | 默认值改为种子表的 `20260002`（王芳，102 班）及其种子初始密码，文档字符串同步；环境变量覆盖保留。`ai-question/POST.py` 的说明同步 | 同一自检脚本解析 `login-and-account-system` 规约种子表：默认教师、学生账号都在表中，密码一致，学生属 102 班；环境变量仍可覆盖 |
| 18 | 路由器级已统一声明 403，`list_servers`、`list_tool_calls`、`list_skills` 仍在路由级重复声明；`create_server` 还把 403 改写成「非任教班级」 | 删除这 4 处路由级 403；`create_server` 只保留特有的 400 | `check_mcp_tools` 新增 2 条：MCP 与技能共 12 个接口的 403 说明都是「非教师或非任教班级」；登记服务器仍有 400 与 401 |

实际跑过：

| 命令 | 结果 |
| --- | --- |
| `PYTHONPATH=backend backend/.venv/bin/python apitest/check_question_bank.py` | **91/91 通过**（本轮新增 8 条：下架标记 4、每题配图 4） |
| `PYTHONPATH=backend backend/.venv/bin/python apitest/check_mcp_tools.py` | **60/60 通过**（新增 OpenAPI 2 条） |
| `python apitest/check_apitest_harness.py`（含 pytest、requests 的环境） | **9/9 通过** |
| 回归 `check_formula_retrieval`/`check_lesson_prep`/`check_research_materials`/`check_sqlite_storage`/`check_lessons_2_5` | 11/11、112/112、54/54、16/16、122/122 |
| `node apitest/check_markdown_images.cjs`、`node apitest/check_recent_history.cjs` | 通过 |
| `npx tsc --noEmit` | 通过 |
| `docker compose up -d --build backend frontend` | 构建成功，backend healthy，容器内为本轮代码 |
| 8081 冒烟 | `/api/health` 200；未登录访问 `knowledge-points` 和 `mcp/servers` 均为 401，访问 `/teacher/quiz` 为 307；日志无报错 |

本轮未覆盖：

- 「仅原作者可下架」只验证了接口字段与 `tsc`，没有在浏览器里用两个教师账号逐项点按。
- `CHAIN.py` 没有对真实服务重跑：Key 无效时仍走 error 帧跳过分支。新分支只由自检脚本中的伪造数据覆盖。
- 种子学生的 `must_change_password` 为真。如果演示库里这名学生改过密码，或者尚未改密，仍须用 `APITEST_STUDENT_*` 覆盖。
- 已入库题目的 `assets_json` 没有回填；旧题仍是整批清单，不影响发布时的指纹核对。

## 结论

除上述明确标注项外，规约中的生成请求校验、结构化输出与逐题校验、SSE 进度与失败处理、逐题复核状态机、学科题库、按配比组卷、定稿与分班发布、范围隔离与审计，均已在隔离验收或 Docker 端到端中通过。任务 9.1、9.2 已由本次端到端覆盖；9.3 的同伴签字待补。

## 归档记录（2026-10-25）

- 经使用者明确指示归档；32/33 任务完成，**9.3「交叉复核并签字」仍未勾选**：同伴签字需由另一位组员完成，归档时如实保留为未完成，补签后在此追记。
- `openspec validate add-smart-question-generation --strict` 通过。
- 已把 delta 合入主规约：新建 `specs/smart-question-generation/spec.md`（11 条 Requirement）；`specs/teacher-workspace/spec.md` 修改 2 条。
- 归档顺序：本变更 → `harden-model-json-escapes` → `fix-quiz-markdown-rendering`。后两个变更的 delta 依赖本变更建立的主规约。
- 归档前，本变更的《结构化输出与逐题校验》已补充知识点「字面包含即向上归一」规则与 3 个 Scenario。`harden-model-json-escapes` 的 MODIFIED 块原本基于旧文本，按原样归档会冲掉这些规则，因此先把它们合入该 MODIFIED 块，再归档。
- 归档前回归：`check_question_bank` 108/108、`check_model_json` 65/65、`check_lesson_prep` 119/119。
- 归档后在主规约 `specs/smart-question-generation/spec.md` 补写了 Purpose（替换 openspec 自动生成的 TBD 占位）。
- **已知遗留问题**：未归档的历史变更 `align-teacher-student-workspaces` 中，teacher-workspace 的两个 MODIFIED 块（《教师共用工作空间导航》《全科总览与单科教学入口区分》）基于旧主规约，缺少本变更新增的 Scenario「教师进入智能命题页」「智能命题不再是占位」。`openspec validate --all --strict` 因此报 21 passed、1 failed。这是既有归档债务，本次没有改动那个变更；归档它之前，需要把这两个 Scenario 补进对应 MODIFIED 块，否则会被冲掉。
  - 已解决（2026-10-25）：两个 MODIFIED 块改为主规约现行全文，补入上述两个 Scenario，同时补上正文里的 `/teacher/quiz` 路由与「智能命题」入口说明。只补 Scenario 不够：旧正文仍写着「智能命题…使用占位状态」，与新 Scenario 矛盾，归档时还会把主规约的正文改回去。主规约原本就包含旧块的全部内容，该变更其余 6 个 MODIFIED 块也与主规约一致。处理后 `openspec validate --all --strict --no-interactive` 结果为 22 passed、0 failed。
