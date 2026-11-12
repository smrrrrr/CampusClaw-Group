# 第三轮评审修复验证

## 范围与状态

日期：2026-11-12（北京时间）；macOS / Python 3.12.15 / Node v25.9.0。基线 HEAD 为 704b631；原工作区干净。本次为实施者自检，不代签另一名组员，不声称真实模型评测或课程验收完成。

目标及实际分支：`fix/review-lesson09-all`。代理首次创建分支被共享 Git 元数据写入边界拒绝；用户随后明确确认已创建并切换，已用 `git branch --show-current` 核实。提交状态见文末。

用户授权直接修复评审代码并编写 OpenSpec；没有执行 apply/archive，没有修改任何 tasks 勾选，没有同步主规约、部署、重置账号、升级依赖、创建 PR 或推送。未新增 OpenSpec 以外的 Markdown 报告；只修改原交接说明。所有数据库与模型写入验证使用临时库、假模型/假 MCP；安全扫描仅只读查询本地教学库（本工作树不存在该库）。

## 全部问题逐条处置

| 问题 | 修复/核实结果 | 本次证据 |
| --- | --- | --- |
| P0-1 数据包不兼容 | 原 review-03 已记载重打包关闭；本树没有包/manifest/restore.py，不臆造包修改；交接改用已验证 70f0048 基线 | 原 reports/review-03.md §1.1；外部包本次未复验 |
| P0-2 实验缺失 | 新增 apitest/probe_prompt_injection.py；修改现有交接命令，保留替身实验边界 | prompt-injection-results.json，4/4 |
| P0-3 探针缺 SEC-08 | 补学生写入拒绝、教师对照、他科拒绝、未知缓存、SSE done 及业务快照检查 | review-fix-api.json，41/41 |
| P0-4 ctx 未定义 | 去掉 ctx；执行前读取数据库 User，校验当前会话/技能/服务器归属及状态 | 同上 SEC-08 4 条；写工具生产聊天路径不崩溃 |
| P0-5 writable 丢失 | 客户端发现、ORM 缺省及落库保留保守分类；仅宿主已审阅的内置端点工具可只读；远端提示不能授予权限；旧缓存与重连再校验 | review-fix-gate.txt 发现分类 3 项；review-fix-api.json 重连和旧缓存 |
| P1-1 401 不审计 | 中间件增加 401，响应后台独立写入，按当前数据库身份或匿名落库 | api 匿名 401；gate 中 ASGI 正文发出先于审计写入 |
| P1-2 五列未赋值/查询缺项 | 技能调用原子写 McpToolCall/AuditLog，赋 action/object/skill/duration；解析真实决策轮 usage.total_tokens 并保存/返回；同轮共享数不可直接累加；未返回用量为 null | api 技能审计值为37及班级/角色隔离；gate 覆盖合法37/0、缺失、布尔、负数、字符串 |
| P1-3 npm 漏报 | summary 保留包、via/nodes、锁定版本及递归通告；例外按精确版本/全部通告/有效日期匹配；缺失明细、循环引用、坏日期均阻断 | gate 正常/失败/边界10项；真实安全门禁现在 RED，4个包未获有效豁免 |
| P1-4 Markdown 破坏 | 历史返回原文，既有 ReactMarkdown 显式 skipHtml | api 原文逐字比较及权限反例；实际组件SSR/KaTeX 7条断言通过，并复现旧 escape 导致 katex-error |
| P2-1 注释与指针 | 下载/预览 docstring 改404；交接基线由残留55d18d3统一70f0048，并区分外部包恢复基线与本轮修复分支 | git diff；原历史评审不改写 |
| 早期审核表：审计失败静默 | 两类审计写入失败均回滚并记录固定 audit_write_failed 告警，不输出异常正文或凭证 | gate 提交失败故障注入3项通过 |
| 早期SEC-02/05/06/07及异步审核 | SEC-02已改404且复跑；SEC-07纳入本修复；SEC-05运行范围仍待验；SEC-06保留真实风险；异步57条原回归在完整门禁中执行 | make check；安全自查范围见下文 |

JSON/TXT 证据均位于 `reports/security-evidence/`，名称是本次新增的 `review-fix-*` 或 `prompt-injection-results.json`。安全脚本会覆盖的历史证据在命令完成后原样恢复，本次结果另存前缀文件，未以本次日期覆盖旧评审记录。

## 实际命令与结果

| 命令（仓库根） | 结果 |
| --- | --- |
| `UV_CACHE_DIR=/private/tmp/campusclaw-review-uv UV_PYTHON_INSTALL_DIR=/private/tmp/campusclaw-review-python uv sync --project backend --locked` | 退出0，安装锁定依赖；最初未指定临时目录时因用户缓存目录不可写失败，调整缓存/解释器目录后成功，未改锁文件 |
| `npm --cache /private/tmp/campusclaw-review-npm --prefix frontend ci` | 退出0；最初默认缓存目录不可写，指定临时缓存后成功；未升级依赖 |
| `OPENSPEC_TELEMETRY=0 openspec validate 2026-11-12-fix-review-findings --strict --no-interactive` | 退出0；proposal/design/tasks/三份delta齐全 |
| `OPENSPEC_TELEMETRY=0 make check` | 退出0，31/31子项PASS；包括全部离线回归、前端类型、分层、密钥与OpenSpec；review-fix-check.txt |
| `PYTHONPATH=backend backend/.venv/bin/python apitest/check_security_gate.py` | 退出0，23条断言；review-fix-gate.txt |
| `node apitest/check_security_review_rendering.cjs` | 退出0，7条渲染断言；也包含在make check |
| `PYTHONPATH=backend backend/.venv/bin/python apitest/probe_security_precheck.py --output reports/security-evidence/review-fix-api.json` | 退出0，41通过/0红项 |
| `PYTHONPATH=backend backend/.venv/bin/python apitest/probe_prompt_injection.py` | 退出0，4组替身实验通过，非真实模型安全评测 |
| `PYTHONPATH=backend backend/.venv/bin/python apitest/probe_security_precheck.py --mutate-tool-auth --output reports/security-evidence/review-fix-mutation.json` | 预期退出1，38通过/3失败：学生写入、他科教师、未知旧缓存三条确实变红；仅本进程monkeypatch取消授权，不改磁盘源码 |
| `npm --prefix frontend run build` | 退出0，编译、lint/typecheck阶段与14页静态生成成功；review-fix-build.txt |
| `make check-security`（临时缓存/工具目录，见下） | make退出2，内部脚本退出1/RED；探针退出0、源码指纹不变；npm4个漏洞包未有效豁免；无运行容器/教学库导致范围待验；review-fix-security-run.json及review-fix-security-precheck.txt |
| `git diff --check` | 退出0，无空白错误 |

`make check-security` 使用以下环境变量，避免向不可写的用户缓存/工具目录安装：

```sh
UV_CACHE_DIR=/private/tmp/campusclaw-review-uv \
UV_PYTHON_INSTALL_DIR=/private/tmp/campusclaw-review-python \
UV_TOOL_DIR=/private/tmp/campusclaw-review-uv-tools \
UV_TOOL_BIN_DIR=/private/tmp/campusclaw-review-uv-bin \
npm_config_cache=/private/tmp/campusclaw-review-npm \
make check-security
```

实际执行由 `/private/tmp/run_review_security.py` 调用同一 `make check-security`，仅负责备份/原样恢复其覆盖的历史证据、另存本次JSON，不修改命令参数、退出码或判定。先前两次因 uv tools 目录不可写导致 pip-audit 无法执行，定位后设置 UV_TOOL_DIR/UV_TOOL_BIN_DIR 再跑；最终 npm audit退出1（检出漏洞），backend pip-audit退出1（5包49条通告），mcp pip-audit退出0（0漏洞）。后端扫描的本机缓存写入警告仅影响性能，最终漏洞响应已取得，不能把前两次失败写成PASS。

## Scenario → 检查映射

| delta Scenario | 对应实际检查 |
| --- | --- |
| 命中工具并用到提示、两步任务连续两轮、超过轮次上限、工具超时 | check_mcp_tools：成功调用/两轮meta/每问与会话上限/error审计 |
| 学生写入拒绝且SSE完整、发现重连未知权限默认拒绝、教师与错误归属执行对照 | check_security_review → probe中的SEC-08；check_security_gate中的真实发现分类 |
| 三种结果各有记录、记录只看自己的范围 | check_mcp_tools：ok/error/断开denied、教师可见/同伴不可见/学生403 |
| 审计存储失败可观察、决策轮用量可追溯 | check_security_gate：提交故障/固定告警/六类usage；probe中的技能审计值37 |
| 前端越权跳转403页面 | check_route_guard：学生/教师路由守卫与合法教师切班 |
| 后端越权返回403并记录审计、教师跨班操作记录审计 | check_lessons_2_5、check_async_grading拒绝及审计断言；probe SEC-02/03/04 |
| 审计日志异步写入不影响响应性能 | check_security_gate：ASGI terminal body先发出，再调用审计；不宣称生产延迟基准 |
| 未登录请求留匿名审计、技能审计字段查询与范围 | probe：匿名401/本班字段/学生403/他班班主任不可见 |
| 回显历史消息、仅带最近若干轮作为上下文 | check_lessons_2_5：agent.multiturn_context、agent.messages_persist、agent.failure_sources_persisted；6轮/12条截断边界未专项复验 |
| 历史公式代码与实时回答一致、历史消息权限不变 | probe原文比较及401/404；check_security_review_rendering实际组件/KaTeX/恶意标签断言 |

## 未解决与完成定义

- **依赖风险仍存在**：npm 1 critical、2 high、1 moderate，katex/next/postcss/source-map-js 旧例外不能精确覆盖；后端5个包49条通告（pip-audit不提供严重度）。本任务禁止升级依赖，不能编造新例外来放行；本次修复的是漏报，不能宣称消除了漏洞。
- **外部核验缺口**：本树无数据包和教学库，不能再次验证P0-1的包指纹/恢复；Docker引擎不可达或本项目容器未运行，运行日志与容器前端产物密钥范围未验；没有本次在线服务、真实队列、真实模型评测或组员签名。
- 自动门禁与构建满足；相关新场景有隔离检查；未改提示词或模型参数，语义评测不适用。主规约同步/归档按用户要求暂不执行，人工复核待组员；安全门禁RED，**当前不可据此合并或宣称课程任务全部完成**。

## 提交状态

用户明确要求所有改动提交在 `fix/review-lesson09-all`，只准备本分支的一次提交，不推送。代理实际执行 `git add -- <本次文件清单>` 退出128，无法在工作树外的 `CampusClaw-Group/.git/worktrees/CampusClaw-Group-review/` 创建 `index.lock`（Operation not permitted）。因此该次尝试未暂存、未提交。已准备 `.review/review-fix-commit-message.txt` 和只包含本次文件的 `.review/commit-review-fix.sh`，供本机运行；无额外署名且不推送。最终提交状态以实际 `git log` 为准，不能把准备好的提交信息当成已经提交。
