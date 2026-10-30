## Why

作业批改变更（`add-homework-grading`）已在 `MistakeNote` 表写入教师判错的题目，但学生端「错题」页仍是一张硬编码演示卡，没有真实错题列表、筛选、讲解或掌握标记入口。错题本是作业批改数据的直接消费方，也是学情分析的前置数据来源；没有它，判错结果无法被学生复习利用。

## What Changes

- 扩展 `MistakeNote` 表：新增 `mastered`（bool，默认 False）、`mastered_at`（可空 datetime）字段，用于标记错题是否已掌握
- 新建 `mistake_service.py`（业务层）和 `routers/mistake.py`（接口层），在 `check_layering.py` 登记层级
- 学生接口：错题列表（支持按学科过滤、仅未掌握过滤）、错题详情、标记已掌握/取消掌握、AI 错题讲解（生成错因分析与解题思路）
- AI 错题讲解：调用 `llm_service.generate_answer`，传入题目题干、学生作答、教师评语作为上下文，要求返回结构化讲解；未配置 API Key 时降级返回提示
- 前端：学生「错题」页从演示数据改为真实接口，支持学科筛选、已掌握切换、单题 AI 讲解；首页「我的错题」统计卡改为真实错题数（仅未掌握）
- 首页统计卡「我的错题」由演示值改为调用错题接口计数

## Capabilities

### New Capabilities
- `mistake-notebook`: 学生错题本——按本人归属展示判错题列表、学科筛选、已掌握标记、AI 错因讲解，严格按学生本人隔离。

### Modified Capabilities
- `student-workspace`: 「错题」页从演示卡改为真实错题列表与讲解；首页「我的错题」统计卡由演示值改为真实未掌握错题数。

## Impact

- **后端 (FastAPI)**：`models.py` 为 `MistakeNote` 新增 `mastered`、`mastered_at` 字段；`database.py` 增加 `ALTER TABLE` 迁移；新增 `mistake_service.py`、`routers/mistake.py`；`main.py` 注册新路由；`scripts/check_layering.py` 登记新模块层级。
- **数据库 (SQLite)**：`mistake_notes` 表增列两列；改表前需用 SQLite backup API 备份到 `data/current/before-mistake-notebook-<时间>.db`。
- **前端 (Next.js)**：`frontend/lib/api.ts` 新增错题相关 API 方法与类型；`frontend/app/student/page.tsx` 的 `StudentMistakes` 改为真实数据并实现筛选/讲解/掌握标记；首页「我的错题」统计卡调用真实接口。
- **AI**：复用 `llm_service.generate_answer` 进行错题讲解，提示词要求返回错因分析与解题思路（不直接给最终答案，默认开启解题引导风格）；AI 结果不写审计日志原文。
- **安全**：所有接口按学生本人隔离（`student_id == current.user_id`），按 ID 取错题时先取行再校验归属；不暴露其他学生错题；AI 讲解只读取本人错题内容。
- **测试**：`apitest/check_mistake.py` 覆盖正常/失败/越权三类场景，使用临时库和假模型。
