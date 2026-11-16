# Design

## Context

- **基线状态**：分支 `deps/upgrade-a-b`（当前最新提交 `01f47cc`），工作区干净；本轮仅起草规划，未修改仓库文件。
- **前端技术栈与部署形态**：
  - `frontend/package.json` 当前锁定 `next@14.2.15`、`react@18.3.1`、`react-dom@18.3.1`、`zustand@4.5.5`、`katex@0.16.47`、`react-markdown@9.0.1`、`rehype-katex@7.0.1`、`remark-math@6.0.0`，根 `overrides` 已锁定 `source-map-js: 1.2.2` 与 `postcss: 8.5.33`。
  - `frontend/next.config.mjs` 仅配置 `output: "standalone"` 与 `/api/:path*` → `${BACKEND_INTERNAL_URL}/api/:path*` rewrites。
  - `frontend/middleware.ts` 仅返回 `NextResponse.next()`，页面角色检查由客户端 `AuthGate` 恢复会话后执行，真实权限校验全部在后端逐接口完成。
  - `frontend/Dockerfile` 采用 `deps -> builder -> runner`（`node:22-alpine`）三阶段构建，运行层仅拷贝 `.next/standalone` 与 `.next/static`，并删除镜像自带 `npm`/调试脚本以保证运行层 `.py = 0`（第 10 课 6.1）。

## Goals / Non-Goals

- **Goals**：
  1. 通过将 `next` 升级至 `15.5.28`，从版本根源消除全部 4 条历史 critical 漏洞，使 `npm audit --omit=dev` 的 `critical=0`、`high=0`。
  2. 完成 4 个 `low` 级依赖的合规登记，使 `make check` 与 `make check-security` 在同一交付版本上实现双绿（exit 0）。
  3. 在独立测试栈中完成容器构建（保持 `.py = 0`）与端到端运行时冒烟，验证 Next 15 未破坏登录、Cookie 刷新、切班守卫、SSE 流式回复及公式/配图渲染。
- **Non-Goals**：
  1. 不跨入 Next 16 或 React 19；
  2. 不将现有客户端组件重构为 Server Components 或 Server Actions；
  3. 不处理 `next lint` 在 Next 15 中的弃用提示（当前门禁 `scripts/check.py` 不执行 `next lint`，后续另立前端工程维护任务迁移 ESLint CLI）；
  4. 不在本变更中处理 `backend` 镜像 OS 层 Trivy `HIGH=51`。

## Decisions

### 1. 目标版本选择 `15.5.28`

| 维度的考量 | 结论 |
| --- | --- |
| 漏洞覆盖范围 | `GHSA-f82v-jwr5-mffw` 修复于 `14.2.25`；`GHSA-p293-qw3h-jr36` 与 `GHSA-2xp9-vwfh-vxw4` 修复于 `15.5.24`；`GHSA-2464-fhr4-w9xw` 修复于 `15.5.28`。`15.5.28` 完整覆盖上述全部 4 条 critical。 |
| 框架兼容边界 | `15.5.28` 仍完整支持 React `18.3.1` 与 Node `22`，避免升级 React 19 带来的类型定义与第三方库（`react-markdown`、`zustand`）联动破坏。 |
| 预演构建结果 | 在隔离副本中仅将 `next` 改为 `15.5.28` 后，`npm install` 与 `next build`（2.9s，14 个路由页面、TypeScript 检查、`.next/standalone/server.js`）均以退出码 0 通过，业务源码零改动。 |

### 2. 保留既有 `overrides` 与 `Dockerfile` 构建链路

- `frontend/package.json` 中的 `"overrides": { "source-map-js": "1.2.2", "postcss": "8.5.33" }` 保持不变，防止 Next 15 子依赖引入旧版 `postcss` 或 `source-map-js`。
- `frontend/Dockerfile` 无需改动；实施构建后必须重新执行镜像内 `.py` 文件计数检查（`find / -name '*.py' -not -path '/proc/*' | wc -l == 0`），确保第 10 课 6.1“镜像 0 源码”要求不回退。

### 3. 安全门禁收口与 4 个 `low` 级包登记

- `scripts/security_precheck.py` 执行两项独立检查：
  1. **课程高危判据**：`npm audit --omit=dev` 的 `high + critical == 0`；
  2. **例外登记完整性**：`npm audit --omit=dev` 返回的每一个有漏洞包，必须在 `reports/security-evidence/dependency-exceptions.json` 中存在未过期（`review_after >= 当日`）且覆盖对应版本与全部 `GHSA` 编号的条目。
- 升级至 `15.5.28` 后，`high=0`、`critical=0`，但 `npm audit --omit=dev` 仍会报告 4 个 `low` 级依赖：`katex`、`micromark-extension-math`、`rehype-katex`、`remark-math`。
- **处置原则**：严禁修改 `scripts/security_precheck.py` 放宽判据；先运行 `npm audit --omit=dev --json` 提取这 4 个包的精确版本号与 `GHSA` ID，再在 `dependency-exceptions.json` 中逐条登记（写明仅用于受控 Markdown/LaTeX 公式渲染、无危险 HTML 注入、缓解措施与复查日期），同时删除已不再命中的 `next@14.2.15` 豁免项。

## Risks / Trade-offs

- **[Next 15 路由缓存与客户端导航语义变化]** → Next 15 调整了部分客户端 Router Cache 默认行为；需在运行时冒烟中重点测试：教师登录 → 切班 → 登出 → 学生登录，确认无上一角色的页面状态残留，且跨班访问仍被后端拒绝为 `403`。
- **[`/api` rewrite 与 SSE 流式响应缓冲]** → 需在 Docker Compose（Nginx → Frontend standalone → Backend）全链路下验证 `/api/auth/login`、`HttpOnly` Refresh Cookie 透传、`/api/auth/refresh` 滑动续期，以及学生助手 SSE 逐块输出不被中间层异常缓冲或截断。
- **[4 个 `low` 包登记需严格匹配版本与通告集合]** → `security_precheck.py` 会校验 `required_ids.issubset(set(raw_ids))` 与版本号集合；必须以升级重锁后的实际 `npm audit --omit=dev --json` 输出为准填写，不能凭记忆手填通告号。

## Migration & Rollback Plan

- **隔离实施原则**：不在共享教学端口或真实数据库上试验；容器构建与冒烟使用独立 `COMPOSE_PROJECT_NAME`、独立端口与临时合成库。
- **回滚方案**：
  1. 实施前保存 `frontend/package.json`、`frontend/package-lock.json`、`reports/security-evidence/dependency-exceptions.json` 的 SHA-256 及当前 `campusclaw-frontend` 镜像 ID/digest；
  2. 若构建、容器启动、运行时冒烟或双门禁任一环节失败，立即停止推进，恢复升级前的成套清单、锁文件与例外登记表，重新构建或回退至旧前端镜像，并验证 `/health` 与 `/login` 恢复 200。
