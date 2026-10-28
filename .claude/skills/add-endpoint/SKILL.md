---
name: add-endpoint
description: 按 CampusClaw 后端开发规范新增或修改一个接口（分层、命名、权限、错误响应、日志、检查）。在实现 tasks.md 里涉及新接口的任务时使用。
---

# 按规范加一个接口

输入：变更名、要实现的 Scenario。

1. 读 `docs/standards/02-后端开发规范.md` 与 `03-安全开发规范.md`；确认变更的 spec 里有该接口的正常、失败（422、401、403、404、依赖不可达）与边界场景，没有就先补规约，不要先写代码。
2. 选路径：教师端 `/api/teacher/<资源复数>`，学生端 `/api/student/...`，共用 `/api/materials/...`；动作型用 `POST /资源/{id}/动作`。
3. 写在对应的 `backend/routers/<模块>.py`：
   - 认证与角色用 `deps.py` 依赖（`get_current_teacher` / `get_current_student` / `require_subject` / `require_homeroom`），不读请求里的 `class_id`、`role`；
   - 请求与响应用 Pydantic 模型，写 `response_model=` 与 `summary=`；
   - 按 ID 取资源：先查行，再校验班级 / 学科 / 本人归属，不符 403、不存在 404。
4. 业务规则放进 `*_service.py`；外部调用只经 `llm_service` / `mcp_client`；事务内不夹带外部调用；排序带唯一兜底键。
5. 失败用 `HTTPException(status_code, detail="中文说明")`，不含 SQL、路径、异常原文。日志用 `logging.getLogger(__name__)`，不记令牌与正文。
6. 新模块先在 `scripts/check_layering.py` 的 `LAYERS` 登记层级。
7. 调用技能 `add-tests` 补检查，然后跑 `make check`。

产出：路由代码、业务代码、对应的 `apitest/check_*.py` 检查、`make check` 全部 PASS 的输出尾部。
