# Verification Plan

## 一、验收判据总表

| 编号 | 验收维度 | 预期通过信号 | 阻断/失败信号 |
| --- | --- | --- | --- |
| V1 | 依赖与锁树一致性 | `frontend/package.json` 仅 `next` 变为 `15.5.28`；`npm ci` 成功；`react@18.3.1`、`postcss@8.5.33`、`source-map-js@1.2.2` 未漂移 | 出现 React 19、非预期主版本升级或手改锁文件 |
| V2 | 构建与 Standalone 产物 | `npm run build` exit=0，14 个路由全量生成，`.next/standalone/server.js` 存在 | 编译错误、类型报错或缺失 standalone 产物 |
| V3 | 容器运行层 0 源码 | `campusclaw-frontend` 运行层 `.py` 计数为 `0`，OCI revision 标签正确 | 运行层残留 `.py` 或调试工具 |
| V4 | 运行时端到端冒烟 | 登录、首次改密拦截、刷新恢复会话、切班守卫、登出、`/api` rewrite、KaTeX 公式、鉴权配图、SSE 流式响应、跨班 `403` 全部正常 | 任一链路 500/404、Cookie 丢失、SSE 阻塞或越权放行 |
| V5 | 安全门禁收口 | `npm audit --omit=dev` `critical=0` 且 `high=0`；4 个 `low` 包完成合规登记；`make check-security` exit=0 | 存在未消除的 high/critical、未登记漏洞包或修改脚本放宽门禁 |
| V6 | 全量工程门禁 | `make check` 全子项 PASS，exit=0 | 任一检查项失败或新增跳过项 |

## 二、标准验证命令（后续获准实施时在隔离环境执行）

```bash
# 1. 前端安装与构建
npm --prefix frontend ci
npm --prefix frontend run build

# 2. 安全审计明细核对
npm --prefix frontend audit --omit=dev --json

# 3. 双门禁完整校验
make check
make check-security

# 4. OpenSpec 规约校验
openspec validate --all --strict --no-interactive
```

## 三、回滚触发条件

出现以下任一情况时立即中止升级，按 `design.md` 回滚至升级前成套清单、锁文件与旧前端镜像：
1. `next@15.5.28` 构建失败或 standalone 服务无法启动；
2. 独立 Compose 栈下登录、Cookie 刷新、路由守卫、SSE 流式回复或跨班 `403` 出现行为回归；
3. `make check` 或 `make check-security` 出现非预期的失败项且无法在最小范围内定位修复。
