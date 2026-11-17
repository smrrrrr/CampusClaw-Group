# Proposal

## Why

当前前端 `frontend/package.json` 锁定 `next@14.2.15`，命中 4 条 critical 安全通告（`GHSA-f82v-jwr5-mffw`、`GHSA-p293-qw3h-jr36`、`GHSA-2xp9-vwfh-vxw4`、`GHSA-2464-fhr4-w9xw`），导致 `make check-security` 在课程「高危/critical 零条」判据上持续为 `RED`（参见 `reports/next-risk-applicability.md`）。

前期在隔离临时副本中已预演 `next@14.2.15 → 15.5.28`：在保持 React 18.3.1 与全部现有前端源码不变的前提下，`next build`（14 个页面、TypeScript 类型检查、`.next/standalone/server.js`）直接通过，且升级后 `npm audit --omit=dev` 的 `critical` 与 `high` 漏洞数均清零。本提案规划以最小改动将 `next` 升级至 `15.5.28`，并同步完成运行时冒烟回归与剩余 4 个 `low` 级依赖的合规登记，使安全门禁在真实依赖层面收口。

## What Changes

- **最小依赖升级**：将 `frontend/package.json` 中的 `"next": "14.2.15"` 精确更新为 `"next": "15.5.28"`；保留既有 `"source-map-js": "1.2.2"` 与 `"postcss": "8.5.33"` 根 `overrides`，不升级 React 18.3.1 及其他无关依赖。
- **定向重锁**：在隔离验证通过后使用固定 npm 工具链重新生成 `frontend/package-lock.json`（不手改 hash/resolved，不执行全局 `npm update`）。
- **安全例外表收口**：更新 `reports/security-evidence/dependency-exceptions.json`，移除已失效的 `next@14.2.15` 豁免条目，并按 `docs/standards/03-安全开发规范.md` 登记升级后 `npm audit --omit=dev` 暴露的 4 个 `low` 级包（`katex`、`micromark-extension-math`、`rehype-katex`、`remark-math`），确保不放宽 `scripts/security_precheck.py` 任何判据。
- **文档与报告同步**：更新 `reports/next-risk-applicability.md`（标注 14.2.15 历史适用性论证已被升级至 15.5.28 替代）及 `report.md` 对应状态索引。

## Capabilities

### New Capabilities

无。`.openspec.yaml` 明确 `skip_specs: true`，不新增业务能力规约。

### Modified Capabilities

无业务要求变更。继续以既有主规约验收，包括：
- 登录、首次强制改密、刷新恢复完整会话与登出（`login-and-account-system`）；
- 页面路由角色守卫与教师单科切班隔离（`teacher-workspace`、`student-workspace`、`class-data-isolation`）；
- Markdown、LaTeX 公式及鉴权配图渲染（`research-materials`、`smart-lesson-prep`、`material-upload`）；
- 学生助手 SSE 流式响应与跨班 403 边界（`agent-assistant`、`class-data-isolation`）。

若运行时回归发现 Next 15 改变了任何外部行为或页面路由/缓存语义，先暂停实施并补写对应 delta specs，不借本变更默许差异。

## Impact

- **后续获准实施后预计修改文件**：
  - `frontend/package.json`（仅 `next` 版本号 1 行）
  - `frontend/package-lock.json`
  - `reports/security-evidence/dependency-exceptions.json`
  - `reports/next-risk-applicability.md` 与 `report.md`（状态同步）
- **明确不改动范围**：
  - 本轮仅提交提案，不改任何源码、锁文件或配置；
  - 不升级 Next 16 或 React 19，不修改 `frontend/Dockerfile`（继续复用 `.next/standalone/server.js` 与运行层 `.py = 0` 断言）；
  - 不修改后端/MCP 依赖、数据库表结构或业务接口；
  - 不运行 `backend/dev_seed.py`，不挂载或修改真实教学数据库，未经明确授权不提交、不推送、不归档。
- **独立边界声明**：本变更仅收口前端 `next` 引发的 `npm audit` critical/high 与未登记包；`backend` 镜像 OS 层 Trivy `HIGH=51` 及 CI 临时库种子账号问题属于独立收口项，不混入本提案验收范围。
