## Why

教师在单科学情页切换任教班级时会被错误跳到 403。隔离环境已复现：另一个标签页登录学生后，共享的辅助角色 Cookie 被改写，middleware 直接拒绝仍持有有效教师 Access Token 的原标签页；后端未发生对应越权请求。

## What Changes

- middleware 只放行页面会话恢复的入口，不再用可被其他标签页覆盖的 `cc_role`、`cc_has_token` 决定登录或 403 跳转。
- AuthGate 在恢复当前页会话后、挂载业务内容前，校验教师/学生路由角色；有效教师切班保持原视图，真实角色不符继续进入 403，恢复失败继续进入登录页。
- 保留现有后台 JWT、任教班级和资源归属检查，补齐共享提示冲突、越权、刷新和页面加载边界回归。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `rbac-role-permissions`：前端页面角色判定交由已恢复的当前页会话，辅助 Cookie 不构成拒绝或放行依据；同步越权跳转的执行位置。

## Impact

修改前端 middleware、AuthGate，新增可独立检查的路径角色判断；新增前端离线检查。同步主规约、产品/安全说明、README 与验证记录。无后端接口、数据库、提示词、依赖、账号或权限数据变更；仅更新本机 8083 前端，保留其他部署。
