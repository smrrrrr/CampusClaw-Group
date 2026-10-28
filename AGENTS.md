# 项目规则

本文件每次会话都会被读到。`CLAUDE.md` 通过 `@AGENTS.md` 引入本文件，`.trae/rules/project_rules.md` 指向本文件；只改这里，不要在别处另写一份。

## 规约优先

1. **无规约不写代码**：任何行为变更，先在 `openspec/changes/YYYY-MM-DD-<短横小写英文名>/` 中写好并评审 proposal / design / specs / tasks，再实现。
2. 要改行为，先改规约 Markdown，再按规约改代码；不得只在对话里口头追加需求。
3. 实现以 `openspec/specs/**/spec.md` 与变更中的 Scenario 为验收标准；“模型说完成了”不等于完成。
4. 未经明确指示，不执行 `/opsx-apply`、`/opsx-archive`，不修改 tasks.md 的勾选状态。

## 安全三条硬约束（全文见 docs/standards/03-安全开发规范.md）

1. **默认拒绝，逐资源判定归属**：业务接口默认要求登录；按 ID 取资源先取行再校验班级、学科、本人归属。跨班访问返回 403 并写审计（书面例外，见 03 规范）。
2. **身份只取自服务端会话**：`class_id`、`teaching_classes`、`subject`、`role` 只从令牌与数据库取，不采信 query、body、请求头中的同名字段；前端隐藏按钮不是授权。
3. **密钥只在本机 `.env`**：不进代码、提示词、日志、响应、前端产物、镜像与提交历史；口令只存哈希。泄露即轮换，不是删文件。

## 改代码前先读对应规范

| 改动范围 | 必读 |
| --- | --- |
| `frontend/app/**`、`frontend/components/**`、界面文案 | `docs/standards/01-产品设计规范.md` |
| `backend/**/*.py`、任何接口 | `docs/standards/02-后端开发规范.md` |
| 登录、权限、上传、出站请求、依赖 | `docs/standards/03-安全开发规范.md` |
| `apitest/**`，以及实现任何 tasks.md 任务之后 | `docs/standards/04-测试规范.md` |
| Dockerfile、`docker-compose.yml`、`deploy/`、`.env.example`、发版 | `docs/standards/05-部署运维规范.md` |
| 提示词、`llm_service.py`、`lesson_service.py`、`question_service.py`、`mcp_orchestrator.py`、检索 | `docs/standards/06-AI应用规范.md` |
| `models.py`、`database.py`、表结构、`uploads/`、数据包 | `docs/standards/07-数据规范.md` |
| 提交、评审、归档 | `docs/standards/08-评审与完成定义规范.md` |

最常用的几条（细节以规范全文为准）：

- 后端分层只能自上而下：`routers/` → `*_service.py` → `models.py` / `database.py`；外部能力（模型、向量、MCP）只在 `llm_service`、`embedding_service`、`mcp_client`。新模块先在 `scripts/check_layering.py` 登记层级。
- 失败一律 `HTTPException(status_code, detail="中文说明")`，detail 不含 SQL、路径、异常原文。
- 日志用 `logging.getLogger(__name__)`，自动为单行 JSON 带 `request_id`；不记令牌、口令、提问原文、资料正文。
- 配置只从 `config.Settings` 读；密钥不给默认值。
- 测试写在 `apitest/check_<能力>.py`，临时库 + 假模型，按正常 / 失败 / 边界三类，检查名写清对应的 Scenario。

## 完成定义与门禁（全文见 docs/standards/08-评审与完成定义规范.md）

一条变更同时满足才算完成：① 每个 Scenario 都有对应检查（含越权与失败路径）；② `make check` 全部 PASS；③ 改提示词已附评测或抽查记录；④ README、主规约、规范、模型注释已同步；⑤ 验证记录已归档。

- 合并前必须跑 `make check`（Windows：`backend\.venv\Scripts\python.exe scripts\check.py`）。不得为了变绿放宽检查、删断言或跳过子项。
- 不符合规范又确需保留的写法，写进对应规范的“例外（书面）”，注明理由与失效条件；口头豁免无效。
- 提交信息末尾写 `Change:` / `Verify:` / `Evidence:` 三行，值必须查得到。

## 技能（`.claude/skills/`，按场景调用）

| 技能 | 什么时候用 |
| --- | --- |
| `add-endpoint` | 按规范新增或修改一个后端接口 |
| `add-tests` | 实现一组任务之后，按测试规范补齐三类检查 |
| `data-change` | 改表结构或删除数据 |
| `prompt-change` | 修改任何提示词或模型参数 |
| `release` | 发一次版本、打标签 |
| `review-change` | 合并前按评审检查表审一次变更 |
| `fresh-start` | 在新机器上从零克隆、启动并验证 `/health` |

## 数据安全

已有数据的库不运行 `backend/dev_seed.py`（会重置学生账号）；改表结构前先备份数据库；`.env`、数据库、`backend/uploads/`、组内数据包不进 Git。
