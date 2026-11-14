# Next.js 14.2.15 四条 critical 的适用性论证

- 日期：2026-11-14（UTC）
- 分支：`deps/upgrade-a-b`，基于 `4b005e1`
- 对象：`frontend` 镜像与源码，`next@14.2.15`
- 性质：**实际适用性论证**，不改变 `npm audit` 的计数，也不改变安全门禁的 RED 结论
- 结论：保持 14.2.15，4 条 critical 在当前代码与部署形态下均不可利用；但不宣称“零高危”

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

## 七、结论

保持 `next@14.2.15` 在**当前代码与 Linux standalone 部署**下，4 条 critical 均不可触发；风险可接受，但安全门禁的 RED 与“未达课程零高危”的结论不变。任何启用图片优化、安装 sharp、middleware 承担鉴权或迁移 Windows 的改动，都必须先重评本论证。
