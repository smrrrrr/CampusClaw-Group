# `security-fix-lesson09` 实际状态核对（2026-11-16）

## 一、为什么核对

该变更 `tasks.md` 是 **3 勾 / 36 未勾**，且没有 `validation.md`，在清单盘点中看起来像最大缺口。逐条比对代码与证据后发现：**绝大多数条目已实现，只是当时没有回填勾选**。本文件只记录"代码里到底有没有"，不代替验收签字。

核对方式：读实现、跑 `grep` 定位、确认证据文件存在。未运行线上探针，未改 `tasks.md`。

## 二、逐条结论

图例：**已实现**＝代码/证据确实存在；**缺失**＝没有实现；**待确认**＝代码在但缺当次验收记录。

### 2. 跨班取数 403→404

| 任务 | 结论 | 依据 |
| --- | --- | --- |
| 2.1 按 ID 取材料返回 404，参数篡改仍 403 | **已实现** | `backend/routers/materials.py:108` `_check_material_access`：`material is None` 与归属不符均抛 404，注释写明"不区分不存在与无权访问"；`materials.py:288` 学生传入他班 `class_id` 参数抛 403 |
| 2.2 其他按 ID 取数统一 fetch-then-check | **已实现** | `grep HTTP_403_FORBIDDEN backend/routers/` 仅剩 7 处，全部是参数篡改（`materials.py:288/294`）或教师班级选择校验（`materials.py:164`、`teacher.py:206/303/328`），无一处是"按 ID 取行后返回 403" |
| 2.3 检索侧班级过滤在查询层生效 | **已实现** | `backend/rag_search_service.py:184` `retrieve_top_k(class_ids)`；`Material.class_id.in_(class_ids)` 与 `MaterialChunk.class_id.in_(class_ids)` 均在 SQL 层过滤 |
| 2.4 删除内存过滤旧路径 | **已实现** | `grep "filter.*class_id"` 命中均为 SQLAlchemy 查询层 `.filter()`，无"先取全表再内存筛" |
| 2.5 复测 SEC-02 探针 | **待确认** | `apitest/probe_security_precheck.py` 存在；未见该轮的探针输出归档 |

### 3. 注入防护三件套

| 任务 | 结论 | 依据 |
| --- | --- | --- |
| 3.1 SQL 注入反例 | **已实现** | `apitest/cases/api/student/conversations/chat/POST-sqli.py` 存在；查询均用 SQLAlchemy 参数绑定 |
| 3.2 XSS 反例 | **已实现** | `apitest/cases/api/materials/xss.py` 存在；`backend/routers/materials.py:14` 导入 `html.escape`，第 335 行对返回的 `description` 转义 |
| 3.3 CSRF 令牌 | **已实现** | `backend/main.py:85` `csrf_protection_middleware`：校验 `csrf_token` Cookie 与 `X-CSRF-Token` 头；`config.py:39` `cookie_samesite = "lax"`；`apitest/cases/csrf.py` 存在 |
| 3.4 三条反例接入 `make check` | **已实现** | `apitest/check_injection.py` 存在（docstring 写明"注入三件套反例回归"），`scripts/check.py` 按 `check_*.py` 通配加载 |

### 4. SEC-07 审计七列

| 任务 | 结论 | 依据 |
| --- | --- | --- |
| 4.1 `McpToolCall` 增 `skill_id`/`duration_ms`/`tokens` | **已实现** | `backend/models.py:649` 起，第 667 行有 `# SEC-07：技能标识、耗时、token 用量` 注释与三列 |
| 4.2 `AuditLog` 增 `action`/`object_id`/`skill_id`/`duration_ms`/`tokens` | **已实现** | `backend/models.py:91` 起，第 106—111 行五列齐全 |
| 4.3 迁移脚本 | **已实现** | `scripts/migrate_audit_fields.py` 存在 |
| 4.4 工具调用写入三列 | **已实现** | `backend/mcp_orchestrator.py` 写 `McpToolCall` 时填充；`mcp_tool_calls` 表结构含三列 |
| 4.5 `write_audit_log` 新增参数 + 拒绝请求也写 | **已实现** | `backend/services.py:78` 签名含 `action/object_id/skill_id/duration_ms/tokens`；`mcp_orchestrator.py:206` 对 denied 记 `status_code=403` |
| 4.6 日志字段转义与截断 | **已实现（补修）** | 核对时此条确实缺失：`write_audit_log` 直接赋值，无长度截断。已由变更 `openspec/changes/2026-11-16-harden-audit-field-bounds/` 补齐：`services.py:17` `_AUDIT_TEXT_LIMITS` 按 `AuditLog` 列宽定义 7 个文本字段上限，`services.py:28` `_clean_audit_text` 把 U+0000–U+001F 与 U+007F 换为空格并按上限截断（`None` 原样返回），`write_audit_log` 七个文本字段统一走该函数。回归 `apitest/check_audit_field_bounds.py` 24/24 通过并纳入 `make check`。补充更正：控制字符对单行 JSON 日志的破坏风险被高估——`backend/logging_setup.py:36` 的 `JsonFormatter` 已用 `json.dumps` 转义；真实缺口是**长度**（SQLite 不校验 `String(N)`，超长不报错），`main.py:122` 曾手工 `[:256]` 兜底，其余 3 处调用方没有 |
| 4.7 审计查询接口授权（学生 403） | **已实现** | `backend/routers/teacher.py:387` `@router.get("/audit-logs")` 依赖 `Depends(get_current_teacher)`，学生令牌进不来 |
| 4.8 复测七列齐全 | **待确认** | 代码具备七列；未见该轮探针输出归档 |

### 5. SEC-08 工具执行层

| 任务 | 结论 | 依据 |
| --- | --- | --- |
| 5.1 执行前按身份校验写入类工具 | **已实现** | `backend/mcp_orchestrator.py:257`：`if tool.writable or tool_requires_write(...)` → 第 258 行返回"学生无权执行写入或未知权限工具"，并写 denied 审计 |
| 5.2—5.5 四个实验 | **已实现** | `reports/sec08-experiment.md` 存在，含实验一（恶意文档）等章节；脚本 `reports/security-evidence/prompt-injection/run_experiments.py` |

### 6. 资产处置

| 任务 | 结论 | 依据 |
| --- | --- | --- |
| 6.1 密钥扫描 | **已实现** | `reports/security-baseline.md` 存在；`make check-security` 内含 secret_scan |
| 6.2 依赖审计 | **已实现** | `reports/security-evidence/dependency-exceptions.json` 登记在册；本轮 `make check-security` PASS |
| 6.3 Makefile `check-security` | **已实现** | `Makefile:7` `check-security:` 调用 `scripts/security_precheck.py` |
| 6.4 先红后绿证据 | **已实现** | `reports/gate-red-green.md` 存在，含"第一次运行（必红）"与变绿记录 |

### 7—8. 回归与归档

| 任务 | 结论 | 依据 |
| --- | --- | --- |
| 7.1 全量回归 | **已实现** | 本轮 `make check` 41/41 PASS |
| 7.2 异步三条 | **待确认** | 异步判据在 `apitest/check_async_grading.py` 覆盖；该轮的三条记录未见归档 |
| 7.3 注入三件套全绿 | **已实现** | `apitest/check_injection.py` 在本轮 `make check` 中通过 |
| 7.4 四步走查 | **待确认** | `reports/review-02.md`、`review-03.md` 有相关记录，但未找到该轮完整四步输出 |
| 7.5 `reports/security-fix-log.md` | **已实现** | 文件存在，覆盖 SEC-01 至 SEC-08 全部八项 |
| 7.6 `reports/risk-authz.md` | **已实现** | 文件存在 |
| 7.7 记录一次返工 | **已实现** | `reports/rework-lesson09-csrf.md` 存在；提交 `4ad52f5` 归档返工记录 |
| 7.8 交叉评审 `reports/review-02.md` | **已实现** | 文件存在 |
| 8.1 逐条单独提交 | **已实现** | 提交历史按 SEC 分组：`4cfaa15`（SEC-07/08+CSRF）、`76be9f2`（SEC-02）、`3d63e9b`（SEC-05/06），提交信息含 SEC 编号 |
| 8.2 最终双门禁全绿 | **已实现** | 本轮 `make check` 与 `make check-security` 均 exit 0 |

## 三、汇总

| 结论 | 数量 |
| --- | --- |
| 已实现 | **33**（含 4.6 补修） |
| 待确认（代码在、缺当次记录） | **3**：2.5、4.8、7.4 |
| 缺失 | **0** |

> 4.6 初次核对时为**缺失**（32 / 3 / 1）；补齐后重算为 33 / 3 / 0。补修变更与提交号见第四节。

## 四、建议

1. ~~**4.6 是真缺口**~~ → **已修**：变更 `openspec/changes/2026-11-16-harden-audit-field-bounds/`（含 proposal / design / spec delta / tasks / verification-plan），代码改动集中在 `backend/services.py` 的 `_clean_audit_text`，回归在 `apitest/check_audit_field_bounds.py`。
2. **待确认的 3 项**需要当时的运行记录，可以重跑探针补齐（`apitest/probe_security_precheck.py`），或由评审认可现有代码状态后补勾。
3. **`tasks.md` 未改动**：按 AGENTS.md「未经明确指示，不修改 tasks.md 的勾选状态」，本文件只做核对，勾选与否等你裁决。4.6 亦然——补修不自动勾选历史变更的框。
4. 该变更一直缺 `validation.md`。若决定收口，建议补一份，把上表"已实现"的项作为验收依据，而不是简单勾 30 个框。

## 五、4.6 的补修清单

| 项 | 位置 |
| --- | --- |
| 规约（行为变更先行） | `openspec/changes/2026-11-16-harden-audit-field-bounds/specs/rbac-role-permissions/spec.md` |
| 实现 | `backend/services.py:17—41`（常量、清洗函数）、`services.py:128—143`（`write_audit_log` 内逐字段接入） |
| 回归 | `apitest/check_audit_field_bounds.py`（24 条断言），已由 `make check` 通配加载 |
| 验证计划 | `openspec/changes/2026-11-16-harden-audit-field-bounds/verification-plan.md` |
| 提交号 | 见本文件落库后的提交 `git log -1 --format=%h -- reports/security-fix-lesson09-status-2026-11-16.md` |

不在本次范围：不回溯清洗历史超长记录、不改表结构、不加数据库迁移。