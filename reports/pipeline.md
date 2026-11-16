# 第10课流水线与镜像追溯

- 工作流：`.github/workflows/lesson10.yml`
- 远端验证：GitHub Actions **已实跑**（Draft PR #3，run `43826707775`）：`check` 通过、`security` RED、`images` 跳过
- 状态：部分完成；受控绿版本、镜像 digest、主干保护为阻塞项

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
- **边界**：这是另一台 Linux 机器的运行证据，不是“另一个人”；因 `security` 未绿，**不构成 7.2 的受控绿版本，也没有 4.2 的远端 digest**。

## 四、阻塞与后续

1. 远端写权限与 GitHub Actions 运行权限已具备；仍缺仓库管理权限（`admin=false, maintain=false`），无法配置 required checks / 分支保护。
2. 需在仓库设置中把 `lesson10-delivery / make check`、`make check-security` 设为 required checks，并禁止未审批合入；当前账号无此权限。
3. 安全门禁当前 RED（Next critical + 5 个未登记 npm 包），`images` 因此被跳过；不放宽门禁，因此没有远端镜像与 digest。本机 registry 演练只证明链路。
4. 需要线上实例与正式发布流程，才能完成“线上 URL → 镜像 digest → OCI revision → CI run → 提交”的完整反查。
