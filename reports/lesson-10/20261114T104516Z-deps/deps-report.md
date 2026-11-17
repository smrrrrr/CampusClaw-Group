# A+B 依赖升级实施记录

- 变更：`openspec/changes/2026-11-14-upgrade-deps-and-jwt/`
- 分支：`deps/upgrade-a-b`（基于 `0408862`）
- 批次：`reports/lesson-10/20261114T104516Z-deps/`
- 时间：2026-11-14（UTC）
- 性质：实施记录；安全门禁仍 RED，不构成可发布结论

## 一、实际升级

| 对象 | 原版本 | 实施版本 | 说明 |
| --- | --- | --- | --- |
| katex | 0.16.11 | **0.16.47** | 高/中危消除；仍有 katex 低危（修复需 0.18.2+） |
| source-map-js | 1.2.1 | **1.2.2**（override） | high 消除 |
| postcss | 8.4.31 | **8.5.33**（override） | 比 propose 候选 8.5.18 更高：8.5.18 仍受 `GHSA-fxqj-rqcc-2cmp`（<=8.5.22）影响 |
| certifi | 2026.7.22 | **2026.10.19** | 指定 GHSA 消除 |
| Pillow | 12.3.0 | **13.0.0** | 大版本例外；python-pptx 约束允许 |
| python-jose | 3.5.0 | **移除** | 无修复 CVE；由 PyJWT 替代 |
| PyJWT | — | **2.15.1** | 仅 HS256，无 crypto extra |
| opentelemetry-api（MCP） | 1.45.1 | **1.45.2** | propose 计划外补丁：非 Next 漏洞，不修则“仅 Next”归因失败 |

Next/React/React DOM 未升级；python-pptx、cryptography 保持。

锁文件哈希（base `0408862` → 工作区）见 `lock-hashes.txt`。后端锁定向变更：新增 pyjwt/certifi/pillow 版本，移除 python-jose、ecdsa、pyasn1、rsa、six。

## 二、JWT 适配

- `security.py` 改用 PyJWT，保留 `security.JWTError` 导出；调用方无需改动。
- 关闭 PyJWT 原生 exp/iat/nbf 校验，由适配层复刻旧 python-jose 的整数秒语义：
  - `exp == 当前整数秒` 仍有效，`exp < 当前秒` 拒绝；
  - 未来 `iat` 允许，但必须可转整数；
  - `nbf > 当前秒` 拒绝；
  - `aud` 不校验（旧库无 audience 概念）；
  - 签名与算法白名单仍由 PyJWT 执行。
- 新增门禁断言：`JWT-J2`（exp 边界）、`JWT-J3`（签名篡改）、`JWT-J7`（未来/非法 iat）。
- 真实镜像冒烟（`jwt-smoke.txt`）：
  - 登录 200，返回 access/refresh Cookie；
  - Bearer 访问受保护接口 200；
  - 刷新 200 并续发 access，刷新后再访问 200；
  - 带 Bearer + CSRF 登出 200。

## 三、门禁与安全

| 项 | 结果 |
| --- | --- |
| `make check` | **33/33 PASS**，exit 0 |
| 前端 `npm ci` / `npm run build` / `tsc` | 全部 0 |
| `make check-security` | **RED**，exit 1；密钥范围完整、无泄漏 |
| npm high/critical | **0 high / 1 critical（仅 next）** |
| backend pip | **0 漏洞** |
| mcp pip | **0 漏洞** |
| 后端镜像 Trivy | 全层 **CRITICAL=0**；HIGH=51（基础镜像 OS） |
| 前端镜像 Trivy | CRITICAL=4，全部来自 Next |
| MCP 镜像 Trivy | CRITICAL=0 |

归因结论：应用依赖的 high/critical 扣除 Next 后为空；katex 链只剩 low。详见 `security-attribution.md`。

Next 的 4 条 critical 在当前代码与 Linux standalone 部署下的适用性见 [next-risk-applicability.md](../../next-risk-applicability.md)：middleware 只放行不鉴权、无 `next/image`、镜像内无 `sharp`、优化器对所有图片返回 400、远程 URL 被拒。该论证不改变 audit 计数与门禁 RED。

## 四、与 propose 的偏差

1. **PostCSS 用 8.5.33，而非候选 8.5.18**：8.5.18 仍命中 `GHSA-fxqj-rqcc-2cmp`（受影响 <=8.5.22）。已用 Next 14.2.15 完整构建验证兼容。
2. **MCP 锁被修改**：propose 原计划保持 MCP 锁，但审计发现 `opentelemetry-api 1.45.1` 的 CVE-2026-126360 有 1.45.2 修复；不升级会留下非 Next 漏洞。

## 五、未完成

- 1.4 许可证：PyJWT 为 MIT（允许）；certifi（MPL-2.0）与 Pillow 是既有传递依赖，本轮未新增许可证类型，但独立评审人签字仍未落实。
- 2.4 / 4.4：J1–J8 只实现了 J2/J3/J7 子集与真实登录/刷新冒烟，J4/J5/J6/J8 的完整 HTTP 对照未逐条固化。
- 5.4：回滚演练未执行。
- 6.2：非实施者复核与签名未落实。
- 镜像基于 dirty 工作区构建；提交后应从干净快照重建再扫描。

## 六、结论

A+B 达到预期：后端与 MCP 依赖漏洞清零，前端 high 清零、critical 仅剩 Next；JWT 行为等价通过边界测试与真实冒烟。安全门禁仍 RED 且不得宣称可发布，剩余红项为 Next 大版本问题。
