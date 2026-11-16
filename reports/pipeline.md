# 第10课流水线与镜像追溯

- 工作流：`.github/workflows/lesson10.yml`
- 远端验证：GitHub Actions **已实跑并全绿**（PR #3，run `43885117587`）：`check` 通过、`security` 通过、`images` 构建并扫描通过
- 状态：**受控绿版本已达成（7.2）**；主干保护（5.6/7.3 收口）与线上反查（7.4）仍为阻塞项

## 一、流水线结构

```
checkout 实际 SHA
  ├─ job check     : 安装 uv/npm/OpenSpec → make check
  └─ job security  : 生成一次性 .env → docker compose up -d → make check-security → down -v
        （两者都成功）
          ↓
       job images : 用同一 SHA 构建 backend/frontend/mcp-tools
                    → 记录 image ID 与 OCI revision
                    → trivy 扫描 CRITICAL/HIGH，非零即失败
                    → 归档脱敏证据
```

- 两个门禁 job 不共享可写目录；失败也 `if: always()` 上传证据。
- 安全 job 需要运行中的容器才能完成密钥扫描范围，因此先启动测试栈；测试栈镜像**不是**可交付镜像。
- 未使用 `continue-on-error`；缺 Docker/联网直接失败，不降级为绿。
- 镜像 tag 为 `${GIT_SHA}`，Dockerfile 同时写入 `org.opencontainers.image.revision`。

## 二、本地可核实项

| 项 | 结果 | 证据 |
| --- | --- | --- |
| 工作流文件存在且为单一入口 | PASS | `.github/workflows/lesson10.yml` |
| 本地同命令双门禁 | `make check` 41/41；`make check-security` RED | `reports/lesson-10/<run>/gates/` |
| 镜像标签参数贯通 Compose | PASS（`GIT_SHA` → image tag + build arg） | `docker-compose.yml`、三个 Dockerfile |
| 镜像 OCI revision | 本机构建可查 | 见下方命令与 `boot/` 证据 |
| 远端 CI 运行编号 | 已执行但为红：run `43826707775`（check 绿、security 红、images 跳过） | PR #3、`reports/lesson-10/20261116T075000Z-remote-ci/` |
| 独立 PR 故障重放 | 已执行：run `43828237591` 的 `make check` 失败、`images` 跳过 | PR #4（已关闭）、`reports/lesson-10/20261116T080640Z-ci-fault-replay/` |
| 镜像仓库 digest | 本机 registry 演练已产生；远端未产生 | `reports/lesson-10/20261116T024000Z-clone-registry-rollback/local-registry.txt` |
| main required checks | 未配置；当前账号 `admin=false, maintain=false` | `gh api repos/...` 权限查询；无远端管理权限 |

## 三、镜像反查（本机部分）

构建后可用以下命令核对“镜像 → 提交”：

```bash
GIT_SHA=$(git rev-parse HEAD)
docker image inspect campusclaw-backend:${GIT_SHA} --format '{{.Id}} {{index .Config.Labels "org.opencontainers.image.revision"}}'
```

远端完整链路应为：线上 URL → 部署实例 → 实际镜像 digest → OCI revision → CI run → 提交。当前**没有线上实例**，该链缺最后一环，不能宣称 7.3/7.4 通过。

### 本机 registry 演练（2026-11-16，不替代远端）

在本机启动 `registry:2`（仅监听 `127.0.0.1:5001`），把当前提交的三镜像 tag → push → pull，再记录 `RepoDigests`、OCI revision 并复验容器内 `.py=0`：

| 镜像 | RepoDigest | OCI revision | `.py` |
| --- | --- | --- | --- |
| backend | `127.0.0.1:5001/campusclaw-backend@sha256:3275eeec2ffa…` | `984c4c8…` | 0 |
| mcp-tools | `127.0.0.1:5001/campusclaw-mcp-tools@sha256:130a84fe2878…` | `984c4c8…` | 0 |
| frontend | `127.0.0.1:5001/campusclaw-frontend@sha256:8b5778d9ac1d…` | `984c4c8…` | 0 |

结论：镜像可经 OCI registry 分发，digest 与 revision 在 push/pull 后保持一致。**这不是远端仓库/GHCR**：没有 CI run、没有远端保留策略、没有线上实例反查，4.2 仍为 BLOCKED。完整 digest 与原始输出见 `reports/lesson-10/20261116T024000Z-clone-registry-rollback/local-registry.txt`。

### GitHub Actions 远端实跑（2026-11-16）

| 项 | 结果 |
| --- | --- |
| 触发方式 | 推送 `deps/upgrade-a-b` 后以 **Draft PR #3**（未合并）触发 `pull_request` |
| 首次 run `43826358847` | `check` 失败：npm 404 `'@openspec/cli@1.13.1' is not in this registry`（工作流配置错误） |
| 修复提交 | `fca85f7`：改为 `@fission-ai/openspec@1.13.1`，并加 CI6 静态断言 |
| 第二次 run `43826707775` | head `fca85f7`，PR 合并引用 `2ba142a…` |
| `make check` | **success**，远端 Ubuntu 41/41 |
| `make check-security` | **failure**（exit 2）：`status=RED`、5 个未登记 npm 包、npm high+critical=1；容器账本 blocked（无四个种子身份） |
| `build-and-scan` | **skipped**（`needs: [check, security]`）：无远端镜像、无 Trivy、无 digest |
| 远端测试栈 | backend/frontend/rabbitmq Healthy；其余服务已启动；随后清理 `down -v` |

- 安全 RED 是**真实门禁结果**，未放宽、未加 `continue-on-error`。`images` 被跳过是设计行为，说明“门禁绿才出镜像”生效。
- 首次 404 日志见 `reports/lesson-10/20261116T075000Z-remote-ci/first-run-404.txt`，run 元数据与门禁摘要同目录。
- **边界**：这是另一台 Linux 机器的运行证据，不是“另一个人”；因 `security` 未绿，**该轮不构成 7.2 的受控绿版本，也没有 4.2 的远端 digest**（后续 run `43885117587` 已全绿，见下文“受控绿版本”）。

### 独立分支故障重放（任务 7.3，2026-11-16）

在隔离分支 `ci-fault-replay`（基于 `6690202`）把 `check_lesson10_ops` 的 M2 预期值从 `1` 改为 `2`，提交 `a626a75`，以 Draft PR #4 触发远端运行；验证后关闭 PR、删除分支与临时 worktree。

| 项 | 结果 |
| --- | --- |
| 本机 `scripts/check.py` | 退出码 **1**，失败项 `check_lesson10_ops` |
| 远端 run `43828237591` 的 `make check` | **failure**：`AssertionError: M2 边界：纯索引迁移不改分块数据` |
| 远端 `make check-security` | failure（与注入无关，正常分支本就 RED） |
| `build-and-scan` | **skipped**，未构建、未推送、无 digest |

- **证明**：注入的可逆故障会让远端 `make check` 失败，并使镜像 job 被跳过。
- **未证明**：required check 阻止合入——当前账号无仓库管理权限，required checks 未配置（2.4）。因此 7.3 仍为部分完成。
- 证据：`reports/lesson-10/20261116T080640Z-ci-fault-replay/`；PR #4 已关闭，`main` 未包含故障提交。

### 受控绿版本（任务 7.2，2026-11-16）

`deps/upgrade-a-b` 推送后由 PR #3 触发 `pull_request` 运行，三个 job 全部通过。这是**真实远端运行**，不是本机日志替代：

| 项 | 值 |
| --- | --- |
| CI 编号 | run `43885117587` — https://github.com/smrrrrr/CampusClaw-Group/actions/runs/43885117587 |
| 提交 / 合并引用 | head `3074cae`；PR 合并引用 `ea3134a9` |
| 工具链 | 工作流固定：OpenSpec `1.13.1`、uv `0.13.5`、Node `22`、Python `3.12` |
| `make check` | **success**，远端输出 `门禁全部通过`（含 `check_os_vuln_gate`） |
| `make check-security` | **success**（临时库写入四个演示身份，未改判据） |
| `build-and-scan` | **success**：三镜像构建 → Trivy 扫描 → `scripts/trivy_os_gate.py` 判定通过 |
| 镜像内容摘要 | backend `sha256:a9f926a7…`、frontend `sha256:c3087880…`、mcp-tools `sha256:c89c53e6…` |
| OCI revision | 三镜像标签 `org.opencontainers.image.revision=ea3134a9…`（PR 合并引用） |
| OS 层扫描 | backend 47 / mcp-tools 47 / frontend 0 条 HIGH，CRITICAL 0；HIGH 均在未过期书面例外内（`reports/security-evidence/os-vuln-exceptions.json`，复查 2026-12-15） |
| 证据归档 | CI artifact `images`：`os-vuln-gate.txt`、`trivy-*.json`、`*-image.txt` |

**边界与诚实说明**：

1. 镜像只在本跑的任务内构建，**未推送到任何 registry**，因此没有 `RepoDigest`；上表“镜像内容摘要”是 `docker image inspect .Id` 的内容寻址摘要，不等同于 registry digest。
2. 该绿版本不包含分支保护效果验证——required checks 仍需仓库管理员配置（5.6），因此 7.3 的“不能进 main”仍未被证明。
3. 扫描通过依赖书面例外；例外到期（2026-12-15）后门禁会自动失败，必须重新评估而不是续期了事。

## 四、阻塞与后续

1. 远端写权限与 GitHub Actions 运行权限已具备；仍缺仓库管理权限（`admin=false, maintain=false`），无法配置 required checks / 分支保护。
2. 需在仓库设置中把 `lesson10-delivery / make check`、`make check-security` 设为 required checks，并禁止未审批合入；当前账号无此权限。
3. 安全门禁已绿（run `43885117587`），`images` 已构建并扫描通过；但镜像未推送 registry，仍无远端 `RepoDigest`。本机 registry 演练只证明链路。
4. 需要线上实例与正式发布流程，才能完成“线上 URL → 镜像 digest → OCI revision → CI run → 提交”的完整反查。
