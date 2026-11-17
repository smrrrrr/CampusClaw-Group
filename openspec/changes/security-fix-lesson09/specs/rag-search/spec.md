## ADDED Requirements

### Requirement: 检索查询参数化与注入防护

检索相关的所有数据库查询（关键字检索、向量检索、混合检索的 SQL 部分）MUST 使用参数化查询（占位符绑定），MUST NOT 通过字符串拼接构造 SQL 语句。无法参数化的位置（如排序列名、排序方向）MUST 使用白名单枚举校验，命中白名单外的值 MUST 返回 400 并拒绝执行。用户提交的检索词 MUST 仅作为查询参数值，MUST NOT 被解释为 SQL 语法。

#### Scenario: 检索词含 SQL 注入返回空或报错

- **WHEN** 学生提交检索词 `' OR '1'='1`
- **THEN** 系统将其作为普通字符串参数绑定查询，返回空结果或格式校验错误，MUST NOT 返回全表数据或执行非预期 SQL

#### Scenario: 排序列名白名单校验

- **WHEN** 请求携带排序参数 `order_by=class_id; DROP TABLE materials--`
- **THEN** 后端校验该值不在允许的排序列名白名单内，返回 400 Bad Request，不执行查询

#### Scenario: 班级过滤参数化不被注入绕过

- **WHEN** 学生提交检索词 `102' OR '1'='1` 试图绕过班级过滤
- **THEN** class_id 条件与检索词均通过参数绑定，检索仍限定在本班范围，不返回其他班级数据
