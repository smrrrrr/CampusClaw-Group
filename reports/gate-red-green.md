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
