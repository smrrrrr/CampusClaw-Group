# Tasks

2026-11-16 已获用户明确授权按 apply 实施；仅凭本轮实际证据勾选。按用户本次指示，门禁非零保留实际结果与升级工作区，不以放宽判据或静默回滚掩盖阻塞。仍不执行 `/opsx-archive`、不运行 `dev_seed.py`、不提交或推送。

## 1. 基线快照与依赖更新

- [x] 1.1 记录实施前 `frontend/package.json`、`frontend/package-lock.json`、`reports/security-evidence/dependency-exceptions.json` 的 SHA-256 与当前 `campusclaw-frontend` 镜像 ID/digest，确认工作区无未归档脏改动。
- [x] 1.2 修改 `frontend/package.json`，将 `"next": "14.2.15"` 更新为 `"next": "15.5.28"`，核对 `react`、`react-dom`、`katex` 及 `overrides`（`source-map-js: 1.2.2`、`postcss: 8.5.33`）保持不变。
- [x] 1.3 使用固定 npm 工具链在 `frontend/` 下定向生成 `package-lock.json`（不手改 hash/resolved，不全量升级无关包），通过 `npm ls next react react-dom postcss source-map-js` 核对依赖树。

## 2. 构建与容器 0 源码验证

- [x] 2.1 在 `frontend/` 执行 `npm ci` 与 `npm run build`，记录退出码、耗时、14 个页面生成清单、TypeScript 检查结果及 `.next/standalone/server.js` 产物。
- [x] 2.2 使用独立镜像标签构建 `campusclaw-frontend` Docker 镜像，检查 `org.opencontainers.image.revision` 标签，并断言运行层 `find / -name '*.py' -not -path '/proc/*' | wc -l` 为 `0`（不破坏第 10 课 6.1 0 源码要求）。

## 3. 运行时端到端冒烟回归

- [x] 3.1 在独立项目名、独立端口与临时合成库上启动完整 Compose 服务栈，验证 `/health` 与 `/login` 返回 `200`。
- [x] 3.2 验证认证与路由守卫链路：初始密码首次登录强制改密拦截、正常登录、刷新页面恢复完整会话、教师单科切班页面守卫、登出后清除 Cookie 无法继续刷新。证据：`reports/lesson-10/20261116T215000Z-browser/`（headless Chrome、独立栈、合成库；6/6 页面检查通过）。边界：桌面 headless，不是手机实机。
- [x] 3.3 验证核心业务与安全边界链路：`/api` rewrite 代理、教案/资料 Markdown 与 KaTeX 公式渲染、鉴权配图加载、学生助手 SSE 流式回复、学生跨班访问资料返回 `403`。证据：`reports/lesson-10/20261116T124118Z-next15/`（rewrite、图片 401/200、Nginx SSE 分块）与 `reports/lesson-10/20261116T215000Z-browser/`（headless Chrome 预览 `.katex`=2；学生篡改 `class_id=202` → 403 无正文）；按 ID 取他班材料为防枚举 404，与 `materials.py` 注释及 404 设计一致，规约无 by-ID 403 条款。

## 4. 安全审计与例外登记收口

- [x] 4.1 运行 `npm audit --omit=dev --json`，确认 `critical=0`、`high=0`，提取剩余 4 个 `low` 级包（`katex`、`micromark-extension-math`、`rehype-katex`、`remark-math`）的精确版本与 `GHSA` 编号。
- [x] 4.2 更新 `reports/security-evidence/dependency-exceptions.json`：移除已失效的 `next@14.2.15` 条目，按 `03-安全开发规范.md` 补充上述 4 个 `low` 级包的完整登记与 `review_after` 日期。
- [x] 4.3 运行完整 `make check` 与 `make check-security`，确认两条门禁均以退出码 `0` 通过（`critical=0`、`high=0`、`unregistered_vulns=[]`），且不改动任何门禁判据。证据：`make check` 41/41 exit 0；`make check-security` 在把本地库只读副本放到 `data/current/` 后 PASS exit 0，见 `reports/lesson-10/20261116T215000Z-browser/security-run-after-db-restore.json`；未注入账号、未改脚本。

## 5. 文档同步与证据归档

- [x] 5.1 更新 `reports/next-risk-applicability.md`（注明 `14.2.15` 适用性论证已被升级至 `15.5.28` 替代）及 `report.md` 对应结论与未完成项说明。
- [x] 5.2 将构建输出、镜像 `.py=0` 证明、运行时冒烟记录与双门禁结果脱敏归档至 `reports/lesson-10/` 对应批次目录。
- [x] 5.3 执行 `openspec validate --all --strict --no-interactive`，确认规约结构校验通过。

## 本轮执行证据与未完成原因

证据批次：[`reports/lesson-10/20261116T124118Z-next15`](../../../reports/lesson-10/20261116T124118Z-next15/README.md)。安装/构建在临时前端副本执行；仓库前端另执行 npm ci 供完整门禁核验当前锁树。

- 3.2 已补验并勾选：2026-11-16 在独立栈（合成库、端口 55890）用 headless Chrome 完成登录页渲染、首次改密跳转、教师登录、刷新恢复会话、切班 201→202、登出清 Cookie 共 6 项页面检查全通过；证据 `reports/lesson-10/20261116T215000Z-browser/`。仍非手机实机。
- 3.3 已补验并勾选：`/api` rewrite、鉴权图片 200/401、Nginx 入口 SSE 逐块到达在第一批次通过；headless Chrome 预览实测 `.katex` 节点 2 个、正文含公式；学生篡改 `class_id=202` 返回 403 且无他班正文。按 ID 读取他班材料返回 404，属 `materials.py` 明示的防枚举设计（规约未规定 by-ID 状态码）。未修改业务接口或验收判据。
- 4.3 已补验并勾选：`make check` exit 0（41/41）；将主仓库数据包中的本地库只读副本放到 `data/current/` 后，`make check-security` PASS exit 0（`unregistered_vulns=[]`、npm high=critical=0、backend/mcp 0 漏洞包、四个演示身份齐全）；未注入账号、未改门禁脚本。首轮工具权限失败与临时工具目录修复后的完整重跑均已归档。
