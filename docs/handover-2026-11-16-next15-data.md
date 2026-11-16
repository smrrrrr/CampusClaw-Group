# 交接数据说明（Next 15 升级，2026-11-16）

配套文档：[交接评审文档](handover-2026-11-16-next15.md)。本文件只回答“数据在哪、怎么恢复、哪些不能传”。

## 一、数据清单

| 数据 | 位置 | 是否入库 | 用途 |
| --- | --- | --- | --- |
| 机器可读状态与全量文件哈希 | `docs/handover-2026-11-16-next15.data.json` | 是 | 161 个变更文件 + 门禁/版本/PR/CI 状态 |
| 关键文件哈希 | `docs/handover-2026-11-16-next15.manifest.json` | 是 | 16 个核心文件快速核对 |
| 实施证据 | `reports/lesson-10/20261116T124118Z-next15/` | 是 | 构建、镜像、隔离栈、HTTP 冒烟、双门禁原始输出 |
| 补测证据 | `reports/lesson-10/20261116T215000Z-browser/` | 是 | headless Chrome 页面检查、KaTeX、跨班 403/404、门禁复跑 |
| 安全扫描输出 | `reports/security-evidence/` | 是 | npm/pip 审计、例外登记、密钥扫描、账号核查 |
| 本地数据库 | `data/current/campusclaw.db` | **否**（.gitignore） | 门禁读取四个演示身份；运行时数据 |
| 上传资料 | `backend/uploads/` | **否** | 真实/合成资料正文，按需交接 |
| 环境密钥 | `.env` | **否** | JWT、队列、MCP、模型密钥 |
| 真实教学库与数据包 | 组内数据包（离线） | **否** | 只在组内传递，不进公开仓库 |

## 二、恢复步骤

### 2.1 数据库（门禁所需）

1. 从组内数据包取得 `campusclaw.db`（含四个演示身份）。
2. 放到 `data/current/campusclaw.db`。
3. 只读核对：

```bash
sqlite3 data/current/campusclaw.db \
  "select identifier, role, class_id from users where identifier in ('<demo-teacher-1>','<demo-teacher-2>','<demo-student-1>','<demo-student-2>');"
```

4. 再运行 `make check-security`；缺库会以 `BLOCKED / exit 2` 结束，属范围未完成。

### 2.2 环境变量

按 `.env.example` 生成 `.env`，至少包含：`JWT_SECRET_KEY`、`GRADING_BROKER_PASSWORD`、`MCP_AUTH_TOKEN`、`MCP_TOKEN_KEY`、`CAMPUSCLAW_DATA_DIR`、`CAMPUSCLAW_PORT`、`DEEPSEEK_API_KEY`（可为空）。

### 2.3 上传资料

从数据包恢复 `backend/uploads/`；不要将真实学生资料提交到 Git。

## 三、校验方式

```bash
python3 - <<'PY'
import hashlib, json
d = json.load(open("docs/handover-2026-11-16-next15.data.json"))
bad = [f["path"] for f in d["files"] if hashlib.sha256(open(f["path"],"rb").read()).hexdigest() != f["sha256"]]
print("mismatch:", bad)
PY
```

输出 `mismatch: []` 表示交接内容与清单一致。

## 四、交接边界

- 本仓库为公开仓库：数据库、`.env`、上传正文、令牌一律不提交。
- 证据中的演示账号标识已替换为 `<demo-teacher-1>` 等占位符；绝对路径已脱敏。
- 若需把真实数据交给下一位组员，走组内私有渠道，不使用 Git。
