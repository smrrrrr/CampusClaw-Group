# 交接说明：Next.js 15.5.28 升级（2026-11-16）

本文件面向接手人，说明当前状态、如何启动、如何评审、剩余任务怎么做，以及本次工作由谁完成。结论与索引同步在根 [report.md](../../report.md)，原始证据在 `reports/`，可私下传递的数据实体在 **`handover-packs/2026-11-16-next15.zip`**（仓库外，见[数据说明](handover-2026-11-16-next15-data.md)）。

## 一、当前状态

| 项 | 值 |
| --- | --- |
| 变更目录 | `openspec/changes/2026-11-16-upgrade-next-15-5-28/`（5 个文件，`skip_specs: true`） |
| 代码改动 | `frontend/package.json` 仅 `next` 14.2.15 → **15.5.28**；`frontend/package-lock.json` 定向重锁 |
| 清单 | `tasks.md` **14/14** 已勾选（证据见下） |
| 门禁（本地） | `make check` **41/41 PASS，exit 0**；`make check-security` **PASS，exit 0** |
| 审计 | npm `critical=0 / high=0 / moderate=0 / low=4`（4 个 low 已在例外表登记） |
| 镜像 | `campusclaw-frontend:next15-20261116t124118z`，运行层 `.py=0` |
| 提交 | 分支 `deps/upgrade-a-b`，PR #3 面向 `main`；依赖升级 `f6d3a2b`，CI 与文档修复 `90bcbe7`→`9fffcb2`（最新提交以 `git log -1` 为准） |
| 远端 CI | run `43879790468`（`bcf3c92`）：`check` pass、`security` pass、`images` 构建三个镜像成功但 Trivy 红——backend 基础镜像 debian 13.7 有 **49 条 HIGH / 0 CRITICAL**，`Fixed Version` 为空（上游无修复） |
| 未完成 | 真人/手机/远端 required checks/线上部署等，见第五节 |

## 二、交接数据

| 数据 | 位置 | 说明 |
| --- | --- | --- |
| **数据包（实体）** | `campusgroup/handover-packs/2026-11-16-next15.zip` | 232 个文件；含本地库、`.env`、上传材料、证据、提案。**仓库外，不进 Git**，组内私下传递 |
| 提案与验收标准 | `openspec/changes/2026-11-16-upgrade-next-15-5-28/` | proposal / design / tasks / verification-plan |
| 实施证据（第一批） | `reports/lesson-10/20261116T124118Z-next15/` | 基线、重锁、构建、镜像、隔离栈、HTTP 冒烟、双门禁、审计原文 |
| 补测证据（第二批） | `reports/lesson-10/20261116T215000Z-browser/` | headless Chrome 页面检查、KaTeX、跨班 403/404、安全门禁复跑 |
| 安全扫描输出 | `reports/security-evidence/` | `run.json`、`npm-audit.json`、`dependency-exceptions.json` 等 |
| 风险适用性 | `reports/next-risk-applicability.md` | 14.2.15 历史论证已被升级替代的说明 |
| 场景矩阵 | `reports/scenario-coverage.md` | 505 条逐条判定（第10课任务 1.2） |
| 启动复现 | `reports/boot-reproduce.md` | 七服务独立启动（第10课任务 2.3） |
| 哈希清单 | `docs/handover-2026-11-16-next15.manifest.json` | 16 个关键文件快速核对 |
| 机器可读状态 | `docs/handover-2026-11-16-next15.data.json` | 变更文件哈希 + 门禁/版本/PR/CI 状态 |
| 本地数据库 | `data/current/campusclaw.db` | **不入 Git**；由数据包恢复，`make check-security` 读取四个演示身份 |
| 私有配置 | `.env` | **不入 Git**；由数据包恢复或按 `.env.example` 生成 |

数据包怎么解、怎么校验、哪些不能外传，见[数据说明](handover-2026-11-16-next15-data.md)。

## 三、如何启动（接手人从零开始）

### 3.1 前置

- Node 22+、npm 10+、Python 3.12、`uv`、Docker Desktop。
- 从数据包恢复 `data/current/campusclaw.db`（含 `<demo-teacher-1>`/`<demo-teacher-2>`/`<demo-student-1>`/`<demo-student-2>` 四个演示身份）、`.env` 与 `backend/uploads/`。
- 先跑 `python3 -I verify.py`，输出 `OK` 再往下。

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

1. **先验数据包**：`python3 -I verify.py` 输出 `OK`，再比对 zip 的 `.sha256`。
2. **读提案**：`proposal.md` → `design.md` → `verification-plan.md`，确认范围只有依赖升级，没有业务行为变化。
3. **核对 diff**：
   - `git diff main -- frontend/package.json` 应只有 `next` 一行；
   - `frontend/package-lock.json` 不应出现 React/其他主版本漂移；
   - `git diff main -- scripts/security_precheck.py` 应为空（**未放宽任何门禁**）。
4. **核对审计与例外**：`npm audit --omit=dev --json` 的 critical/high 为 0；例外表的版本与 GHSA 必须与审计原文一致，且含复查日期。
5. **核对勾选**：逐条对照 `tasks.md` 与证据路径；重点看 3.2/3.3/4.3 的边界说明是否与证据一致。
6. **复跑门禁**：至少执行 `make check` 与 `make check-security`，退出码应为 0。
7. **看报告而非听结论**：`report.md` 的每个数字都应能在 `reports/` 找到原始输出；发现不符按 FAIL 处理。
8. **红灯项**：若 `make check-security` 变 BLOCKED，先确认是数据包缺失还是新增漏洞；不要用豁免表掩盖真实 high/critical。

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
| 7.2 受控绿版本 | 全绿 CI | `check`/`security` 已绿；`images` 卡在 backend OS 层 49 条 HIGH（上游无修复），需先处置基础镜像才可能全绿 |
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

`images` job 连续踩了三个上游问题，已逐个修掉：

1. `aquasecurity/trivy-action@0.28.0` 这个 tag 不存在（仓库只有 `v0.28.0` 及更新版本），任务在 `Set up job` 阶段报 `Unable to resolve action`；
2. 改成 `v0.28.0` 后，它内部引用的 `aquasecurity/setup-trivy@v0.2.1` 也已被上游删除（现存 `v0.2.6`/`v0.3.0`/`v0.3.1`）；
3. 最终改为 `trivy-action v0.36.0` 并按 commit 固定（`a9c7b0f`），该版本自己按 SHA 固定 `setup-trivy`。

同一个 job 还缺 `.env`：`docker-compose.yml` 对 `JWT_SECRET_KEY`、`GRADING_BROKER_PASSWORD` 用 `:?` 强校验，已补构建前一次性占位 `.env`（本地 `--env-file` 实证：空环境 exit 1、生成后 exit 0）。

修完后真实结果：三个镜像都构建成功（`61bbca8…`），backend 扫描 `Total: 49 (HIGH: 49, CRITICAL: 0)`，全部位于 debian 13.7 系统层，`Fixed Version` 为空。这是**上游尚未修复**的 OS 层问题，不是本次升级引入；处置办法是等基础镜像更新或另立维护变更，不得靠放宽 `severity`/`exit-code` 换绿。前端与 mcp-tools 的扫描因 job 在后端处失败而未执行。

其余缺口：真实模型语义抽查、手机端、线上部署、真实告警接收。

## 六、已知边界与风险

1. **跨班资料状态码**：学生篡改 `class_id` 参数 → 403（规约场景，实测通过）；按 ID 读取他班材料 → 404，属 `backend/routers/materials.py` 明示的防枚举设计。任务书两种说法按此区分，评审时不要误判为回归。
2. **浏览器验收为桌面 headless Chrome**，不等于手机实机。
3. **安全门禁依赖本地数据包副本**：本地已恢复；CI 侧由 workflow 生成临时库并写入四个演示身份，已转绿。
4. **SSE 在直接 Next rewrite 的 gzip 下短响应会合并**：Next 14/15 对照一致，非本次回归；Nginx 入口逐块正常。
5. **未提交前镜像 revision 指向基线 SHA**：提交后重新构建才能让 OCI revision 对应新提交。
6. **数据包在仓库外**：换机器、换组员时必须单独传递 zip；只 clone 仓库拿不到数据库与 `.env`。

## 七、工作说明（本次由谁完成）

| 环节 | 执行者 | 说明 |
| --- | --- | --- |
| 需求、范围与授权 | 项目成员（用户） | 确定只升级 Next、不升 React/Next 16、不改业务行为 |
| 提案起草 | Claude Code | `openspec/changes/2026-11-16-upgrade-next-15-5-28/` 五份文件 |
| 实施（改依赖、重锁、构建、隔离栈、审计、报告） | Codex CLI（写模式，经 codex-companion） | 对应第一批证据；未提交、未推送 |
| 补测（页面验收、门禁复跑、证据归档） | Claude Code | headless Chrome + 本地库副本，对应第二批证据 |
| CI 修复（`security` 种子身份、`images` 的 compose `.env` 与 trivy 版本） | Claude Code | `e08a99e`、`90bcbe7`、`a944069`、`bcf3c92`；每次先取远端日志定位真因，本地复现后再改，未放宽门禁 |
| 交接数据包打包 | Claude Code | `handover-packs/2026-11-16-next15.zip`，含库、`.env`、上传材料、证据；仓库外生成 |
| 真人签名、手机实机、线上部署、告警接收 | **待接手人/组员** | 见第五节，不得由 AI 代签 |

提交约定：单次提交；提交信息含 `Change:` / `Verify:` / `Evidence:` 三行；不添加 AI 共同作者署名。
