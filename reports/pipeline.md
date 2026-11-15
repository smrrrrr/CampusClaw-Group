# 第10课流水线与镜像追溯

- 工作流：`.github/workflows/lesson10.yml`
- 本地验证：工作流结构检查；**未在 GitHub 远端运行**
- 状态：部分完成；远端编号、镜像 digest、主干保护为阻塞项

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
| 远端 CI 运行编号 | 未执行 | 无权限/未推送 |
| 镜像仓库 digest | 未产生 | 未推送 |
| main required checks | 未配置 | 无远端管理权限 |

## 三、镜像反查（本机部分）

构建后可用以下命令核对“镜像 → 提交”：

```bash
GIT_SHA=$(git rev-parse HEAD)
docker image inspect campusclaw-backend:${GIT_SHA} --format '{{.Id}} {{index .Config.Labels "org.opencontainers.image.revision"}}'
```

远端完整链路应为：线上 URL → 部署实例 → 实际镜像 digest → OCI revision → CI run → 提交。当前**没有线上实例**，该链缺最后一环，不能宣称 7.3/7.4 通过。

## 四、阻塞与后续

1. 需要远端仓库写权限与 GitHub Actions 运行权限。
2. 需要在仓库设置中把 `lesson10-delivery / make check`、`make check-security` 设为 required checks，并禁止未审批合入。
3. 需要镜像仓库（或 GHCR）推送权限，才能记录 digest。
4. 安全门禁当前 RED，即使推送也会在 security job 失败；这是预期行为，不放宽。
