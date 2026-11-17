# Proposal

## Why

第10课安全门禁仍为 RED，现有前后端锁文件包含可修复漏洞，python-jose 3.5.0 的 CVE-2026-85394 则尚无修复版本。本变更规划路线 A+B：在保持 Next 14 / React 18、SQLite、现有 API 与会话行为的前提下，缩减依赖风险；不把本轮规划或后续离线门禁通过表述为安全发布完成。

## What Changes

- 路线 A：规划 katex 0.16.11 → 0.16.47，以及通过 `frontend/package.json` 的 overrides 将 source-map-js 1.2.1 → 1.2.2、PostCSS 8.4.31 → 已修复两条指定通告的 8.5.x。PostCSS 候选 8.5.18 已核实发布与修复范围；Next 14.2.15 的实际构建兼容性仍待确认，不能直接批准为最终版本。
- 规划后端 certifi 2026.7.22 → 2026.10.19（2026.10.18 为通告修复下限，两版均经 uv dry-run 解析）；Pillow 12.3.0 → 13.0.0。python-pptx 1.0.2 仅要求 `Pillow>=3.3.2`，因此选择直接声明 Pillow 安全版本，不覆盖其上游约束。
- 路线 B：规划以 PyJWT 2.15.1 替换 `python-jose[cryptography]`，保留 HS256、claims、时效、类型校验、刷新、登出和既有数据库状态拦截。旧/新双向 token 对照设计见 [verification-plan.md](verification-plan.md)。保留 MCP 使用的显式 cryptography 依赖。
- 后续实施按核实版本、改清单、定向重锁、双门禁、镜像扫描、证据归档推进；未通过兼容性验证的版本留为待确认。本轮仅生成五个规划文件，所有实施任务未勾选。

## Capabilities

### New Capabilities

无。`.openspec.yaml` 明确 `skip_specs: true`，不新增 delta specs。

### Modified Capabilities

无业务要求变更。继续以 `login-and-account-system` 的 JWT 会话管理、刷新页面恢复完整会话、多端在线与登出、强制首次改密，以及既有权限/班级隔离规约验收。JWT 库替换属于实现维护；如对照发现必须改变外部行为，先暂停该实现并另行修订业务规约，不能借本变更默许差异。

## Impact

- 后续实施预计涉及 `frontend/package.json`、`frontend/package-lock.json`、`backend/pyproject.toml`、`backend/uv.lock`、`backend/security.py` 和现有认证回归检查；本轮均不修改。`main.py`、`deps.py`、`routers/auth.py` 继续通过 security 导出的 `JWTError` 捕获失败。
- 无 Next/React 大版本升级，无 MySQL/Qdrant/Golang 迁移，无 API、权限、数据库结构或业务数据变更；不运行 dev_seed、不接触教学库、不部署、不提交或推送。
- 后续验收要求完整 `make check` 33/33 全绿；安全门禁允许仍 RED，但必须证明剩余 high/critical 仅来自 Next 及其传递依赖；后端镜像 Trivy 全层 CRITICAL=0。非 Next 风险、镜像 OS high、扫描失败与许可证待审不得隐藏或当作已通过，判定范围和阻断条件见验证计划。
- 本轮不会放宽安全门禁或新增漏洞豁免；RED 不等于可正式发布。Next 残余漏洞、PostCSS 构建兼容、许可证和镜像基础层风险列入设计中的限制。
