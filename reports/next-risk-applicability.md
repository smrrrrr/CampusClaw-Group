# Next.js 升级后的审计结论与历史适用性论证

- 本次时间：2026-11-16 UTC；变更：`2026-11-16-upgrade-next-15-5-28`。
- 对象：**未提交工作区** `next@15.5.28`；React / React DOM 保持 `18.3.1`，根 overrides 保持 `postcss@8.5.33`、`source-map-js@1.2.2`。
- **14.2.15 的适用性论证已被升级至 15.5.28 替代**。下面保留的旧镜像日志、优化器不可用结论与 RED 原因仅是历史证据，不能描述本轮工作区或新镜像。
- 本轮 `npm audit --omit=dev --json`：`critical=0`、`high=0`、`moderate=0`、`low=4`；审计命令 exit 1（存在低危），没有通过豁免折减高危数量。
- 四个 low：`katex@0.16.47`、`micromark-extension-math@3.1.0`、`rehype-katex@7.0.1`、`remark-math@6.0.0`，均解析到 `GHSA-238p-pmpm-9mq7`。已按实际锁树登记范围、责任组、缓解措施、失效条件与 `review_after=2026-12-15`，移除旧 `next@14.2.15` 登记。低危登记不代表漏洞修复或人工签字。
- Next 15 的可选传递依赖实际引入 **`sharp@0.35.5`**，新镜像 `/app/node_modules/sharp` 存在；不再使用“无 sharp”作为缓解前提。旧 `check_frontend_image_safety` 只检查 package.json 未直接声明 sharp，PASS 不能证明镜像中没有传递依赖 sharp。该脚本和所有门禁判据均未修改。
- 隔离 `npm ci`、`npm run build` exit 0，静态页面生成 14/14（构建打印的路径表单独归档），类型检查通过，standalone server.js 存在；独立镜像 `.py=0`，OCI revision 与基线 HEAD 一致。revision 仅标识基础提交，锁文件 SHA-256 另标识未提交升级。
- `make check` **exit 0，41/41 PASS**；`make check-security` **exit 2，BLOCKED**：`unregistered_vulns=[]`、npm high+critical=0、backend/mcp 本轮各 0 个漏洞包，但只读账号检查未找到四个演示身份。首次 pip 工具目录权限失败也保留记录，改用可写临时工具目录后完整重跑，未复用旧审计响应。
- 独立八服务栈（原七服务 + 本地合成模型）HTTP 冒烟 26/29：入口 `/health`、`/login`、Next `/api` rewrite、登录/刷新完整会话、首次改密拦截、登出 Cookie 清除、鉴权配图、Nginx SSE 通过。跨班资料实际 **404，要求 403**；直接 Next rewrite 在 gzip 下短 SSE 合并（Next 14/15 同样现象，identity 下均逐块到达）。浏览器服务不可用，页面刷新/切班守卫与实际 Markdown/KaTeX 渲染待验；**不宣称运行时全部通过**。
- 原始证据与阻塞项：[本轮 README](lesson-10/20261116T124118Z-next15/README.md)、[结果](lesson-10/20261116T124118Z-next15/results.json)。本轮不处理既有后端镜像 OS 层 Trivy HIGH=51，不声称容器 OS 漏洞已清零，也未提交、推送或归档 OpenSpec。

---

以下是 **Next.js 14.2.15 四条 critical 的历史适用性论证**（截至升级前）。

- 日期：2026-11-14（UTC）
- 分支：`deps/upgrade-a-b`，基于 `4b005e1`
- 对象：`frontend` 镜像与源码，`next@14.2.15`
- 性质：**实际适用性论证**，不改变 `npm audit` 的计数，也不改变安全门禁的 RED 结论
- 历史结论（已被本次升级替代）：保持 14.2.15，4 条 critical 在当前代码与部署形态下均不可利用；但不宣称“零高危”

## 一、为什么需要这份论证

`make check-security` 按 `npm audit --omit=dev` 的版本范围计数。`next@14.2.15` 落在 4 条 critical 通告的受影响区间内，因此计数为 critical=1（包级聚合）。审计不分析代码路径，无法区分“依赖存在”与“受影响功能启用”。

本文件只回答一个问题：这 4 条通告在当前代码里是否能被触发。答案用于风险决策，**不用于把门禁改绿**。

## 二、四条 critical 的逐条论证

| 通告 | 标题 | 受影响范围 | 触发前提 | 当前状态 | 结论 |
| --- | --- | --- | --- | --- | --- |
| `GHSA-f82v-jwr5-mffw` | Middleware 鉴权绕过 | `>=14.0.0 <14.2.25` | middleware 承担鉴权，攻击者用特制请求头跳过其执行 | `frontend/middleware.ts` 只 `NextResponse.next()`，不校验身份、不跳转、不放行判定；鉴权全部在后端逐接口完成 | **不可利用** |
| `GHSA-p293-qw3h-jr36` | Windows 上的远程代码执行 | `>=13.4.0 <15.5.24` | 运行在 Windows 主机 | 部署为 Linux 容器（`node:22` 基础镜像），无 Windows 运行时 | **不可利用** |
| `GHSA-2xp9-vwfh-vxw4` | Image Optimizer 未授权 RCE（AVIF/libheif） | `>=10.0.0 <15.5.24` | 图片优化可用，且经 `sharp` 内置 `libheif` 处理 AVIF | 镜像内 **无 `sharp`**；优化器直接报错，任何图片请求返回 400 | **不可利用** |
| `GHSA-2464-fhr4-w9xw` | Image Optimizer 未认证 RCE（SVG） | `>=10.0.0 <=15.5.27` | 图片优化可用，`sharp < 0.35.5`，处理恶意 SVG | 同上，**无 `sharp`**，优化器不可用 | **不可利用** |

### 2.1 关键证据：图片优化器不可用

运行中的 frontend 容器日志：

```text
⨯ Error: 'sharp' is required to be installed in standalone mode for the image optimization to function correctly.
   Read more at: https://nextjs.org/docs/messages/sharp-missing-in-production
⨯ The requested resource isn't a valid image for /api/health received application/json
```

镜像内 `find / -type d -name sharp` 结果为 **0**；`frontend/package.json` 未声明 `sharp`。

因此 `/_next/image` 路由虽然存在（不返回 404），但无法处理任何图片：

| 请求 | 结果 |
| --- | --- |
| `/_next/image?url=%2Fprobe.png&w=64&q=75`（容器内放入真实 PNG） | `400`，`The requested resource isn't a valid image` |
| `/_next/image?url=http%3A%2F%2F127.0.0.1%3A8000%2Fapi%2Fhealth` | `400`，`"url" parameter is not allowed` |
| `/_next/image?url=http%3A%2F%2Fbackend%3A8000%2Fapi%2Fhealth` | `400` |

两条 critical 都要求“优化器可实际解码图片”，当前连合法 PNG 都返回 400，故不成立。

### 2.2 远程 URL 也未被放行

`frontend/next.config.mjs` 没有 `images.remotePatterns` 或 `images.domains`，所以 `url` 参数只接受本站相对路径；远程与内网地址均返回 `"url" parameter is not allowed`。

## 三、复现命令

```bash
# 1. 镜像内无 sharp
docker run --rm --entrypoint sh campusclaw-frontend:<tag> \
  -c 'find / -type d -name sharp -not -path "/proc/*" | wc -l'   # 0

# 2. 优化器不可用（需要容器内可写 /app/public）
docker exec campusclaw-group-frontend-1 sh -c \
  'mkdir -p /app/public && printf "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==" | base64 -d > /app/public/probe.png'
curl -s -o /dev/null -w '%{http_code}\n' \
  'http://127.0.0.1:8086/_next/image?url=%2Fprobe.png&w=64&q=75'   # 400
docker logs --tail 5 campusclaw-group-frontend-1                    # sharp is required

# 3. 远程 URL 被拒
curl -s 'http://127.0.0.1:8086/_next/image?url=http%3A%2F%2Fbackend%3A8000%2Fapi%2Fhealth&w=64&q=75'
# "url" parameter is not allowed

# 4. middleware 不鉴权
sed -n '1,20p' frontend/middleware.ts

# 5. 无 next/image 使用
grep -rn "next/image" frontend/app frontend/components   # 无输出
```

## 四、论证的失效条件

以下任一条件成立，本论证即失效，必须重新评估：

1. 安装 `sharp`（任何版本），或基础镜像改为自带 `sharp`。
2. 在 `next.config.mjs` 增加 `images.remotePatterns` / `images.domains`，或把 `images.unoptimized` 改为 `false` 并实际启用优化。
3. `middleware.ts` 开始做身份校验、路径拦截或放行判定。
4. 部署目标改为 Windows 运行时。
5. 升级 Next 到其他版本（届时按新版本的通告重新判断）。

## 五、自动护栏

`apitest/check_frontend_image_safety.py` 把这五条前提中的前三条变成可回归断言（`package.json` 无 `sharp`、`next.config.mjs` 无 `remotePatterns`/`domains`、`middleware.ts` 不鉴权），并登记在 `make check` 中。前提一旦被改动，门禁会先红，避免论证在无人察觉时失效。

## 六、与门禁和课程口径的关系

- `make check-security` 仍为 **RED**，`course_high_critical` 仍返回 npm critical=1。
- 本文件不登记漏洞例外，不放宽 `security_precheck.py` 的任何判据。
- 是否接受“版本范围内但受影响功能未启用”的论证，取决于课程口径；在获得明确答复前，不得宣称“高危 0 条”。
- 若课程要求按审计计数归零，唯一路径仍是升级到 Next `15.5.28+`（或 `16.4.1+`），需独立变更与回归。

## 七、历史结论（不适用于 Next 15）

保持 `next@14.2.15` 在**当前代码与 Linux standalone 部署**下，4 条 critical 均不可触发；风险可接受，但安全门禁的 RED 与“未达课程零高危”的结论不变。任何启用图片优化、安装 sharp、middleware 承担鉴权或迁移 Windows 的改动，都必须先重评本论证。
