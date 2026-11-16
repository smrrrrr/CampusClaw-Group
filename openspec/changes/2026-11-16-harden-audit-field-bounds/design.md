# 设计：审计字段收口

## 决策一：在 `write_audit_log` 内收口，而非各调用方

**选择**：清洗逻辑放在 `backend/services.py` 的 `write_audit_log` 内部，作为唯一入口。

**理由**：调用点已有 4 处（`main.py`、`materials.py`、`student.py`、`lesson_plans.py`），其中只有 `main.py` 手工截断。把规则放在入口，新增调用点自动受益；放在调用方则每加一处都要重复一遍，容易漏。

**代价**：`write_audit_log` 多一层处理，但它是后台任务（`BackgroundTasks`），不在请求主路径上，可忽略。

## 决策二：按模型列宽截断，长度常量与模型同源

**选择**：在 `services.py` 定义 `_AUDIT_FIELD_LIMITS`，取值与 `models.py` 的 `String(N)` 一致。

**理由**：SQLite 不校验长度，超长值能写进去，问题被掩盖。显式按列宽截断，等于把数据库本该做的约束提前到应用层，换库时行为不变。

**为什么不直接从模型反射列宽**：`AuditLog.__table__.columns[...].type.length` 可行，但调用时多一次反射、可读性差；4 个字段写成常量表更直白，且能在测试里独立断言。代价是模型改列宽时需同步改常量——用一条测试锁住这个对应关系（见验证计划）。

## 决策三：控制字符替换为空格，而非删除

**选择**：把 `\x00`—`\x1f`（保留 `\t` 之外的）等控制字符替换为空格。

**理由**：直接删除会让 `"a\x00b"` 变成 `"ab"`，掩盖了"输入被清洗过"这一事实；替换为空格保留长度感，便于人工核对。保留 `\t`？——不保留，制表符在单行 JSON 里同样是噪音，一并替换。

**影响**：正常中文、字母数字、常见标点（含 `-` `_` `:` `/` `.`）不受影响。

## 决策四：截断后不再追加省略标记

**选择**：超长字段直接取前 N 字符，不加 `…` 或 `(truncated)` 后缀。

**理由**：加后缀会占用列宽、污染值本身，且审计查询按 `object_id` 精确匹配时会匹配不上。需要知道是否被截断的场景极少，且可通过长度等于列宽推断。

## 实现位置

```python
# backend/services.py
_AUDIT_TEXT_LIMITS = {
    "action": 64,
    "object_id": 128,
    "skill_id": 64,
    "request_path": 256,
    "ip_address": 64,
    "role": 20,
    "subject": 32,
}

def _clean_audit_text(value: str | None, limit: int) -> str | None:
    """去掉控制字符并按列宽截断；None 原样返回。"""
    if value is None:
        return None
    text = "".join(" " if ch < " " or ch == "\x7f" else ch for ch in value)
    return text[:limit]
```

在 `write_audit_log` 构造 `AuditLog` 前，对上述字段逐个调用。

## 风险

| 风险 | 处置 |
| --- | --- |
| 常量与模型列宽漂移 | 加一条测试断言两者一致 |
| 已有超长历史记录 | 不回溯，仅新写入受约束；历史数据本就可能是脏的，单独清理是另一件事 |
| 严格过滤影响排查 | 只过滤控制字符，中文与常见标点全部保留 |