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

## 安全反例（同一日期追加）

- 位置：工作区新增 `_lesson10_fake_secret.txt`，内容为 `sk-` 开头的合成假 Key。
- 红：`scripts/secret_scan.py` 退出码 **1**，检出“已跟踪文件含疑似 sk- 开头的 API Key”，1 处问题。
- 恢复：删除该文件。
- 绿：`scripts/secret_scan.py` 退出码 **0**，0 处问题。
- 证据：`reports/lesson-10/20261114T072100Z-apply/gate-red-green/security-mutation-red.txt`、`security-mutation-green.txt`。

说明：完整 `make check-security` 当前仍为 RED，原因是依赖漏洞与扫描范围，不是因为假 Key；安全反例只证明密钥扫描子项能检出并恢复。

---

## 2026-11-17 PR #3 镜像漏洞门禁修复

基线是 `977bcde028b24892ac58466b5612e844bd5b2ecb`。复验使用 Windows、Python 3.12.13 和同一工作区。先加入回归与 UTF-8 子进程配置，在旧的判定脚本和 CI 工作流上执行，再应用实际修复。两次使用相同测试，测试文件的 Git blob 为 `6424bd22da9c5ddb83aae68c56134ee45cf7bfbc`。

| 证据 | 实测 |
| --- | --- |
| 问题位置 | `scripts/trivy_os_gate.py` 将缺少扫描元数据的空对象视为零漏洞，且仅用 CVE 查找 HIGH 例外。`.github/workflows/lesson10.yml` 原先用通配符传入现有报告，漏掉一份时仍可能继续。 |
| 红 | 完整普通门禁 42/43，退出 **1**，唯一失败为 `check_os_vuln_gate`。单项 19/25，退出 **1**，包括空报告、同 CVE 的未登记软件包、重复镜像、无效结构和 CI 缺显式报告路径。见[完整红灯](lesson-10/20261117-image-vuln-gate/full-red.txt)、[退出码与时间](lesson-10/20261117-image-vuln-gate/full-red.json)、[单项红灯](lesson-10/20261117-image-vuln-gate/targeted-red.txt)。 |
| 修复提交 | `cc5b0fc22b7755fbb2fb843ee9fd0b056a0be3d6`，作者 `smrrrrr`。校验 Trivy 报告并拒绝重复镜像，要求三份指定报告，按 CVE、软件包和复查日期判定 HIGH。 |
| 绿 | 完整普通门禁 **43/43**，退出 **0**。单项 **25/25**，退出 **0**。合法零漏洞报告仍通过。见[完整绿灯](lesson-10/20261117-image-vuln-gate/full-green.txt)、[退出码与时间](lesson-10/20261117-image-vuln-gate/full-green.json)、[单项绿灯](lesson-10/20261117-image-vuln-gate/targeted-green.txt)。 |

安全专项也在运行中的隔离 Compose 环境成功复跑，退出 **0**，本次重新查询依赖漏洞库。见[安全结果](lesson-10/20261117-image-vuln-gate/security-green.json)。门禁 JSON 的 `git_head` 记录的是执行时的基线 HEAD，绿色执行使用随后写入修复提交的工作树。

### 复跑

在独立副本检出修复提交，按 README 准备依赖及 OpenSpec。执行下列命令，预期退出 0。复现红灯时，可在同一副本将 `scripts/trivy_os_gate.py` 和 `.github/workflows/lesson10.yml` 恢复为 `977bcde` 的内容，保留修复提交中的回归脚本，执行同样命令并检查退出 1。

```powershell
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
backend/.venv/Scripts/python.exe -u scripts/check.py --json .review/image-vuln-red-green/full-check.json
backend/.venv/Scripts/python.exe apitest/check_os_vuln_gate.py
```

历史 Trivy 报告复核中，新规则在 backend 和 mcp-tools 的旧镜像样本中检出 `CVE-2025-69720` 的 `ncurses-bin` 软件包超出例外范围。保留现有例外表。最新镜像须由修复版 CI 重新扫描以确认当前结果。
