# 第10课索引改进：分块检索覆盖索引

- 批次：`reports/lesson-10/20261114T072100Z-apply/`
- 变更位置：`backend/models.py`（`MaterialChunk`）、`backend/database.py`（`run_simple_migrations`）
- 数据影响：无。仅索引，不搬行数据、不删列、不改写内容。

## 一、改进前的执行计划

合成库：`grade_tasks` 3000 行、`material_chunks` 5000 行（100 份资料 × 50 分块）。

```text
[retrieval]
  SEARCH materials USING INTEGER PRIMARY KEY (rowid=?)
  SEARCH material_chunks USING INDEX ix_material_chunk_class_material (class_id=? AND material_id=?)
  USE TEMP B-TREE FOR ORDER BY
```

检索 SQL（`rag_search_service`）同时按 `class_id` 过滤、按 `(material_id, chunk_index)` 排序，并且只取 `id/material_id/chunk_index`。旧索引 `(class_id, material_id)` 不能覆盖排序与投影，计划里出现临时 B 树，且需要回表读取每个分块行。

## 二、改进

将 `(class_id, material_id)` 升级为其超集：

```sql
CREATE INDEX IF NOT EXISTS ix_material_chunk_class_material_chunk
  ON material_chunks(class_id, material_id, chunk_index);
DROP INDEX IF EXISTS ix_material_chunk_class_material;  -- 已被超集完全覆盖
```

## 三、改进后的执行计划

```text
[retrieval]
  SEARCH materials USING INTEGER PRIMARY KEY (rowid=?)
  SEARCH material_chunks USING COVERING INDEX ix_material_chunk_class_material_chunk (class_id=? AND material_id=?)
  USE TEMP B-TREE FOR ORDER BY
```

- 由回表索引变为 **COVERING INDEX**：查询列全部来自索引，不再逐行读取 `content/embedding`。
- 临时 B 树仍存在：检索使用 `IN` 多班级/多资料，SQLite 需要归并多段有序结果。本课不宣称消除了排序。
- `dispatch` 与 `task_detail` 计划未变；未引入无用索引。

证据：`migration/explain-before.json`、`migration/explain-after.json`、`migration/explain-after.txt`。

## 四、扩 → 迁 → 缩

| 阶段 | 本课动作 | 验证 |
| --- | --- | --- |
| 扩 | 新增三列覆盖索引，旧索引保留到新索引建成 | 迁移内先 `CREATE` 后 `DROP` |
| 迁 | 启动时 `run_simple_migrations` 自动执行；重复执行幂等 | `apitest/check_lesson10_ops.py` M1/M2/M3：连跑两次、数据行数不变、计划使用覆盖索引 |
| 缩 | **本课不执行**；不删列、不删数据 | N/A |

无行数据迁移，因此“迁”阶段只做适用性与兼容复验；不伪造数据搬迁。

## 五、回退

```sql
CREATE INDEX IF NOT EXISTS ix_material_chunk_class_material
  ON material_chunks(class_id, material_id);
DROP INDEX IF EXISTS ix_material_chunk_class_material_chunk;
```

回退只影响查询计划，不影响数据。

## 六、限制

- **API 级同参复测已完成**：旧索引 P95 123.2 ms、新索引 123.7 ms，**无显著收益**。检索耗时主要来自应用层对 500 个分块的相似度计算，SQL 覆盖索引只减少回表与排序。
- 因此本课索引改进在 SQL 级有效、在 API 级未达 ≥10% 的改进目标；按项目规则如实记录为失败，不删改数据。
- 进一步优化（如向量缓存）需要先补隔离/失效规约，不在本课擅自实施。
