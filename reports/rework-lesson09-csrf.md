# 返工记录

第9课安全修复过程中代价最大的一次返工：CSRF 中间件与未认证请求的交互。

## 怎么错的

**问题**：CSRF 保护中间件 `csrf_protection_middleware` 对所有 POST/PUT/DELETE/PATCH 请求强制校验 `X-CSRF-Token` 头。但未登录用户发起的写请求（如注册、登录）没有 `csrf_token` Cookie，中间件直接返回 403，导致登录接口本身无法访问——用户连登录都登不了。

**现象**：`POST /api/auth/login` 返回 403 而非 200；`make check` 中所有需要先登录的测试全部失败。

**根因**：把 CSRF 校验放在了认证之前，且没有区分"有会话 Cookie 的已登录用户"和"无 Cookie 的匿名请求"。CSRF 的攻击前提是攻击者利用受害者的已认证 Cookie 发起伪造请求；匿名请求本身不携带认证 Cookie，不受 CSRF 攻击，不应被 CSRF 中间件拦截。

## 怎么改的

**修改 `backend/main.py` 的 `csrf_protection_middleware`**：

1. 仅当请求中存在 `csrf_token` Cookie 时才执行 CSRF 校验（即用户已登录）
2. 若请求带 `Authorization: Bearer` 头，豁免 CSRF 校验（Bearer 令牌不受 CSRF 攻击，因为浏览器不会自动携带自定义头）
3. 匿名请求（无 csrf_token Cookie、无 Bearer 头）直接放行，由后续认证中间件返回 401

**修改 `backend/routers/auth.py`**：
- 登录成功后下发 `csrf_token` Cookie（非 HttpOnly，SameSite=Lax）
- 修改密码接口同样刷新 csrf_token

**验证**：
- 匿名 POST /api/auth/login → 200（不再被 CSRF 拦截）
- 已登录用户 Cookie 会话 POST 写接口无 X-CSRF-Token → 403
- 已登录用户 Cookie 会话 POST 写接口带正确 X-CSRF-Token → 放行
- Bearer 令牌请求 → 豁免 CSRF

## 代价

- 首次实现后 `make check` 全量失败（所有需登录的接口 403）
- 排查耗时约 30 分钟，定位到中间件顺序问题
- 修改后需重新跑全量 27 组测试确认无回归

## 教训

CSRF 保护应只作用于"已认证的 Cookie 会话"。实现安全中间件时必须先明确攻击前提，不能对所有请求一刀切。认证（你是谁）应在授权（你能做什么）和 CSRF（请求是否伪造）之前完成。
