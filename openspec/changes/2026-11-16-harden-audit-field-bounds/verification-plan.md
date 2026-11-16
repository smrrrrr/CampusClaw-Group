# 验证计划

## 一、检查项与判据

| # | 检查 | 方法 | 通过信号 |
| --- | --- | --- | --- |
| V1 | 超长 `object_id` 被截断 | 传 500 字符 `object_id`，读回 | 长度 128，值等于前 128 字符，无 `…`/`(truncated)` 后缀 |
| V2 | 控制字符被替换 | 传含 `\n`、`\t`、`\x00` 的 `object_id`，读回 | 不含 U+0000–U+001F，对应位置为空格 |
| V3 | 正常值不变 | 传 `object_id="42"` | 读回 `"42"` |
| V4 | `None` 不变 | 传 `skill_id=None` | 读回 `None`，不是 `"None"`/`""`，DB 中为 NULL |
| V5 | 数值字段不受影响 | 传 `user_id=7`、`status_code=403`、`duration_ms=12`、`tokens=99` | 读回均为原整数 |
| V6 | 常量与模型同源 | 比对 `_AUDIT_TEXT_LIMITS` 与 `AuditLog` 列 `type.length` | 7 个键全部一致，无遗漏 |
| V7 | 全量门禁 | `make check` | 全通过，含新增 `check_audit_field_bounds` |

## 二、正常 / 失败 / 边界三类映射

| 类别 | 覆盖检查 |
| --- | --- |
| 正常 | V3 正常值不变、V5 数值不变 |
| 失败路径 | V4 `None` 不被误转（历史 bug 高发点：`str(None)`） |
| 边界 | V1 超长、V2 控制字符、V6 常量漂移 |

## 三、执行方式

```bash
# 单条检查
backend/.venv/bin/python apitest/check_audit_field_bounds.py

# 全量门禁
make check
```

检查使用 `tempfile.TemporaryDirectory()` 建临时 SQLite，不连接 `data/current/` 的真实库，不写入任何真实审计数据。

## 四、不验证什么

- **不验证**换行是否破坏日志单行性：`JsonFormatter` 已用 `json.dumps` 转义换行，这层不在本次改动范围内，也不需要新增检查。若将来换成非 JSON 输出格式，需重新评估。
- **不验证**历史超长记录：本次不回溯清洗。
- **不验证**换库行为：当前只有 SQLite，常量与列宽对齐即为保障。

## 五、证据位置

- 检查脚本：`apitest/check_audit_field_bounds.py`
- 门禁输出：`make check` 终端结果
- 规约：`openspec/changes/2026-11-16-harden-audit-field-bounds/specs/rbac-role-permissions/spec.md`
- 状态回填：`reports/security-fix-lesson09-status-2026-11-16.md`