# 交接说明：Next.js 15.5.28 升级（2026-11-16）

本文件面向接手人，说明当前状态、如何启动、如何评审、剩余任务怎么做，以及本次工作由谁完成。结论与索引同步在根 [report.md](../../report.md)，原始证据在 `reports/`。

## 一、当前状态

| 项 | 值 |
| --- | --- |
| 变更目录 | `openspec/changes/2026-11-16-upgrade-next-15-5-28/`（5 个文件，`skip_specs: true`） |
| 代码改动 | `frontend/package.json` 仅 `next` 14.2.15 → **15.5.28**；`frontend/package-lock.json` 定向重锁 |
| 清单 | `tasks.md` **14/14** 已勾选（证据见下） |
| 门禁 | `make check` **41/41 PASS，exit 0**；`make check-security` **PASS，exit 0** |
| 审计 | npm `critical=0 / high=0 / moderate=0 / low=4`（4 个 low 已在例外表登记） |
| 镜像 | `campusclaw-frontend:next15-20261116t124118z`，运行层 `.py=0` |
| 提交 | 本文件所在提交；分支 `deps/upgrade-a-b`，PR 面向 `main` |
| 未完成 | 真人/手机/远端 required checks/线上部署等，见第五节 |

## 二、交接数据

| 数据 | 路径 | 说明 |
| --- | --- | --- |
| 提案与验收标准 | `openspec/changes/2026-11-16-upgrade-next-15-5-28/` | proposal / design / tasks / verification-plan |
| 实施证据（第一批） | `reports/lesson-10/20261116T124118Z-next15/` | 基线、重锁、构建、镜像、隔离栈、HTTP 冒烟、双门禁、审计原文 |
| 补测证据（第二批） | `reports/lesson-10/20261116T215000Z-browser/` | headless Chrome 页面检查、KaTeX、跨班 403/404、安全门禁复跑 |
| 安全扫描输出 | `reports/security-evidence/` | `run.json`、`npm-audit.json`、`dependency-exceptions.json` 等 |
| 风险适用性 | `reports/next-risk-applicability.md` | 14.2.15 历史论证已被升级替代的说明 |
| 场景矩阵 | `reports/scenario-coverage.md` | 505 条逐条判定（第10课任务 1.2） |
| 启动复现 | `reports/boot-reproduce.md` | 七服务独立启动（第10课任务 2.3） |
| 数据包 | `data/current/campusclaw.db` | **不入 Git**；需从组内数据包恢复，供 `make check-security` 读取四个演示身份 |
| 私有配置 | `.env` | **不入 Git**；按 `.env.example` 生成，含 JWT/队列/模型密钥 |

哈希清单见 [manifest.json](handover-2026-11-16-next15.manifest.json)。

## 三、如何启动（接手人从零开始）

### 3.1 前置

- Node 22+、npm 10+、Python 3.12、`uv`、Docker Desktop。
- 从组内数据包恢复 `data/current/campusclaw.db`（至少包含 `<demo-teacher-1>/<demo-teacher-2>/<demo-student-1>/<demo-student-2>` 四个演示身份）。
- 按 `.env.example` 生成根目录 `.env`（密钥不得提交）。

### 3.2 前端构建

```bash
cd frontend
npm ci
npm run build          # 期望 exit 0；14 个静态页面；.next/standalone/server.js 存在
```

### 3.3 双门禁

```bash
cd <repo-root>
make check             # 期望 41/41 PASS，exit 0
make check-security    # 期望 PASS，exit 0
```

`make check-security` 依赖 `data/current/campusclaw.db` 中的四个演示身份；缺失会以 `BLOCKED / exit 2` 结束，这是范围未完成，不是漏洞红项。

### 3.4 隔离栈 + 浏览器验收（可选，复核 3.2/3.3 用）

```bash
TMP=$(mktemp -d); mkdir -p "$TMP/data" "$TMP/uploads"
DATABASE_URL="sqlite:///$TMP/data/campusclaw.db" \
  JWT_SECRET_KEY="<临时值>" \
  backend/.venv/bin/python scripts/lesson10_seed_fixture.py
# 复制 docker-compose.yml 到 $TMP/compose.yml，并把上传卷改为 $TMP/uploads，
# frontend 镜像改为 campusclaw-frontend:next15-20261116t124118z，
# grading-worker/dispatcher 补 image: campusclaw-backend:<GIT_SHA>
CAMPUSCLAW_PORT=55890 CAMPUSCLAW_DATA_DIR="$TMP/data" GIT_SHA=<基线SHA> \
  docker compose -p ccnext15-browser -f "$TMP/compose.yml" --env-file .env up -d --no-build
```

- 只使用回环端口、临时库与独立卷；**不要**挂真实教学库，**不要**运行 `backend/dev_seed.py`。
- 页面验收用 headless Chrome + `puppeteer-core`：登录、刷新恢复、切班、登出、资料预览 KaTeX。
- 结束务必 `docker compose down -v` 并删除临时目录。

## 四、如何评审

建议按以下顺序，每条都能在证据里找到对应项：

1. **读提案**：`proposal.md` → `design.md` → `verification-plan.md`，确认范围只有依赖升级，没有业务行为变化。
2. **核对 diff**：
   - `git diff main -- frontend/package.json` 应只有 `next` 一行；
   - `frontend/package-lock.json` 不应出现 React/其他主版本漂移；
   - `git diff main -- scripts/security_precheck.py` 应为空（**未放宽任何门禁**）。
3. **核对审计与例外**：`npm audit --omit=dev --json` 的 critical/high 为 0；`reports/security-evidence/dependency-exceptions.json` 的版本与 GHSA 必须与审计原文一致，且含复查日期。
4. **核对勾选**：逐条对照 `tasks.md` 与证据路径；重点看 3.2/3.3/4.3 的边界说明是否与证据一致。
5. **复跑门禁**：至少执行 `make check` 与 `make check-security`，退出码应为 0。
6. **看报告而非听结论**：`report.md` 的每个数字都应能在 `reports/` 找到原始输出；发现不符按 FAIL 处理。
7. **红灯项**：若 `make check-security` 变 BLOCKED，先确认是数据包缺失还是新增漏洞；不要用豁免表掩盖真实 high/critical。

评审红线：

- 修改门禁脚本或删除断言换取绿色；
- 把 404 写成 403、把 BLOCKED 写成 PASS；
- 证据里出现密钥、真实学生数据或未脱敏绝对路径；
- 未经授权勾选真人签名类任务（4.2/5.1/9.5 等）。

## 五、剩余任务与做法

### 5.1 第10课清单（13 项未勾）

| 任务 | 缺什么 | 接手做法 |
| --- | --- | --- |
| 3.2 手机实机 | 真机浏览器 | 用手机浏览器登录学生/教师账号，跑提交流程并留截图 |
| 3.3 在线用例 | 有效模型 Key | 配 `DEEPSEEK_API_KEY` 后重跑在线 cases，补唯一 skip |
| 4.2 组员独立验收 | 另一名组员 | 按 `demo-checklist.md` 从新目录走四项判定，本人签名 |
| 5.1 分工与复核 | 真实姓名/角色 | 在 `lesson10-delivery.md` 填 A/B/C 负责人与交叉复核结论 |
| 5.6 main 保护 | 仓库 admin | owner 配 required checks `check`/`security` |
| 7.2 受控绿版本 | 推送 + CI 种子 | 推送后用 PR 跑 CI；先在 workflow 临时库补四个演示身份 |
| 7.3 故障重放收口 | required check | 5.6 完成后，在测试 PR 验证红色状态无法合入并留证 |
| 7.4 线上反查 | 线上部署目标 | 部署后记录 URL → digest → revision → CI run → commit |
| 8.5 告警规则 | 接收通道/授权 | 与负责人确认渠道，补 `reports/observe-alert.md` |
| 8.6 真实告警触发 | 真实接收方 | 用假模型触发 Pending→Firing→送达→Resolved |
| 9.5 三名真实用户 | 真人 | 按模板记录脱敏会话与去向 |
| 10.1 换人双跑 | 另一名执行者 | 同 SHA/锁/参数跑两次并对比 |
| 10.2 另一人启动 | 另一人/另一机 | 按 README 从零启动并留证 |

### 5.2 依赖/JWT 变更（`2026-11-14-upgrade-deps-and-jwt`，7 项未勾）

`1.4` 许可证评审、`2.4` J1–J8 断言、`3.3` 锁图审查、`4.4` 新旧 token 对照、`5.4` 回滚演练、`6.1` 证据归档、`6.2` 独立复核。实施代码已在仓库，缺的是验收与签字；按该变更 `verification-plan.md` 执行。

### 5.3 跨清单外部缺口

- CI 临时库四个种子身份：已在 `.github/workflows/lesson10.yml` 增加写库步骤（2026-11-16），待远端复跑确认；
- 远端 CI 已在 Next 15.5.28 上重跑一次（run `43876201284`）：`check` 通过，`security` 因种子身份缺失 BLOCKED；补种子后需再跑一次；
- backend 镜像 OS 层 Trivy `HIGH=51` 另立维护任务；
- 真实模型语义抽查、手机端、线上部署、真实告警接收。

## 六、已知边界与风险

1. **跨班资料状态码**：学生篡改 `class_id` 参数 → 403（规约场景，实测通过）；按 ID 读取他班材料 → 404，属 `backend/routers/materials.py` 明示的防枚举设计。任务书两种说法按此区分，评审时不要误判为回归。
2. **浏览器验收为桌面 headless Chrome**，不等于手机实机。
3. **安全门禁依赖本地数据包副本**：CI 无种子身份时会 BLOCKED，需补 workflow 种子步骤。
4. **SSE 在直接 Next rewrite 的 gzip 下短响应会合并**：Next 14/15 对照一致，非本次回归；Nginx 入口逐块正常。
5. **未提交前镜像 revision 指向基线 SHA**：提交后重新构建才能让 OCI revision 对应新提交。

## 七、工作说明（本次由谁完成）

| 环节 | 执行者 | 说明 |
| --- | --- | --- |
| 需求、范围与授权 | 项目成员（用户） | 确定只升级 Next、不升 React/Next 16、不改业务行为 |
| 提案起草 | Claude Code | `openspec/changes/2026-11-16-upgrade-next-15-5-28/` 五份文件 |
| 实施（改依赖、重锁、构建、隔离栈、审计、报告） | Codex CLI（写模式，经 codex-companion） | 对应第一批证据；未提交、未推送 |
| 补测（页面验收、门禁复跑、证据归档） | Claude Code | headless Chrome + 本地库副本，对应第二批证据 |
| 真人签名、手机实机、线上部署、告警接收 | **待接手人/组员** | 见第五节，不得由 AI 代签 |

提交约定：单次提交；提交信息含 `Change:` / `Verify:` / `Evidence:` 三行；不添加 AI 共同作者署名。
