# 门禁先红后绿证据

第9课安全修复门禁验证：证明 `make check-security` 中的密钥扫描确实能检出红项，修复后变绿。

提交号：`55d18d36d6aec194e549271658e7f7d15d683a0f`（分支 `fix/security-lesson09-DuLaolaoDu`）
测试时间：2026-11-11

## 第一次运行（必红）

**操作**：在项目根目录创建临时文件 `_red_green_test.py`，内容含 `sk-` 前缀拼接 32 位字母数字的假 API Key（为避免被本文件自身触发扫描，此处不写出完整密钥，仅描述结构：`"sk-" + 32位随机字母数字`）：

```python
fake_key = "sk-" + "abcdefghijklmnopqrstuvwxyz012345"  # 拼接形式，扫描时为 sk-<32 chars>
```

**命令**：`python scripts/secret_scan.py`

**输出**：
```
  ✗ 已跟踪文件 _red_green_test.py 含疑似sk- 开头的 API Key
密钥扫描：15 个提交；本机密钥 JWT_SECRET_KEY、MCP_AUTH_TOKEN、MCP_TOKEN_KEY、GRADING_BROKER_PASSWORD；1 处问题
```

**退出码**：`1`（RED）

## 第二次运行（必绿）

**操作**：删除 `_red_green_test.py` 后重新运行。

**命令**：`python scripts/secret_scan.py`

**输出**：
```
密钥扫描：15 个提交；本机密钥 JWT_SECRET_KEY、MCP_AUTH_TOKEN、MCP_TOKEN_KEY、GRADING_BROKER_PASSWORD；0 处问题
```

**退出码**：`0`（GREEN）

## 结论

| 阶段 | 退出码 | 问题数 | 状态 |
| --- | --- | --- | --- |
| 含假密钥 | 1 | 1 | RED |
| 移除假密钥 | 0 | 0 | GREEN |

密钥扫描门禁能正确检出工作区中的 `sk-` 开头 API Key，移除后变绿，证明门禁有效而非摆设。

---

# 第10课：完整双门禁先红后绿（2026-11-14 追加）

本节是新的日期/版本记录，不修改上面第9课的子项红绿结论。

## 故障注入

- 位置：`backend/grading_service.py` 的 `matches()`（教师终评/重交保护）。
- 注入内容：`return sub is not None`，即跳过提交状态、作答与时间戳比对。
- 目的：让旧 AI 结果覆盖教师终评或新提交，验证完整 `make check` 能检出。

## 红

- 命令：`backend/.venv/bin/python scripts/check.py`
- 退出码：**1**
- 失败子项：`check_async_grading`、`check_quiz_homework`
- 证据：`reports/lesson-10/20261114T072100Z-apply/gate-red-green/mutation-red.txt`、`mutation-meta.json`

## 恢复

- 工作区注入：恢复 `matches()` 原始实现（`git diff` 为空），对应同一提交 `fe227a1`。
- 随后在**独立证据分支** `lesson10-mutation-evidence` 重放：
  - 故障提交：`10af3b0`（`test(lesson10): 注入终评保护故障`）
  - 修复提交：`f7cddcb`（`Revert "…"`），只回退故障，不改业务实现
- 该分支不合并、不推送；`lesson10-delivery` 上的正确实现为 `e02e83f`。
- 证据：`gate-red-green/branch-mutation-meta.json`、`branch-mutation-red.txt`、`branch-revert-meta.json`、`branch-revert-green.txt`。

## 绿

- 命令：`backend/.venv/bin/python scripts/check.py`
- 退出码：**0**，全部门禁通过
- 证据：`gate-red-green/mutation-green.txt`、`revert-meta.json`

## 四要素对照

| 要素 | 本课结果 |
| --- | --- |
| 改坏位置 | `grading_service.matches()` |
| 红输出与退出码 | `check_async_grading`、`check_quiz_homework` FAIL，exit 1（提交 `10af3b0`） |
| 真实修复提交 | `f7cddcb`（独立证据分支，不合并） |
| 绿输出与退出码 | 全部通过，exit 0（`f7cddcb`） |

结论：完整门禁能检出终评保护故障，红→修复提交→绿四要素齐全；证据分支不进入交付分支。
