# Next 15.5.28 apply 实施记录

- 变更：`2026-11-16-upgrade-next-15-5-28`；2026-11-16 UTC。
- 基线 HEAD：`01f47cc5cd1a440b547e8abbf53bddedf11277b2`；本次依赖更新在未提交工作区中。没有提交、推送或 OpenSpec 归档。
- **任务 11/14 完成，3.2、3.3、4.3 未勾选。升级未完整验收，不宣称双绿。**
- 按用户本次指示保留实际非零门禁结果与升级工作区；本轮不沿用规划中“任一门禁失败自动回滚”的默认做法，不扩大到修改后端行为、门禁或真实库。

## 本次结果

| 项目 | 本轮真实结果 | 证据 |
| --- | --- | --- |
| 基线与回退标识 | 三个指定文件 SHA-256、原前端镜像 ID/digest 与原工作区状态已记录；原改动仅为规划目录 | [baseline.json](baseline.json) |
| 定向依赖更新 | package.json 只改 next 14.2.15 → 15.5.28；React/React DOM 18.3.1、katex 0.16.47、两项 overrides 不变；固定宿主 Node 25.9.0 / npm 11.12.1；未手改 integrity/resolved、未全量 npm update | [targeted-lock](targeted-lock.txt)、[锁树差异](lock-diff.json)、[npm ls](npm-ls.txt) |
| 隔离安装/构建 | npm ci exit 0，23.43s；build exit 0，14.99s；生成静态页面 14/14，类型检查成功，standalone server.js 存在。构建路由表显示 12 个路径；没有把内部页面生成计数冒称 14 条公开路由 | [npm ci](npm-ci.txt)、[build](next-build.txt)、[产物](build-artifacts.json) |
| 仓库门禁前置 | 仓库 frontend 另按当前锁树 npm ci，exit 0 | [workspace-npm-ci](workspace-npm-ci.txt) |
| Docker 构建 | 独立 tag `campusclaw-frontend:next15-20261116t124118z`；exit 0，42.35s；运行层 .py=0、revision=基线 HEAD。运行 Node 22.23.4，构建 npm 10.9.9；标签不冒充已提交升级 | [build](docker-build.txt)、[镜像断言](image-zero-source.json)、[运行依赖](image-runtime-dependencies.json) |
| 隔离启动 | 独立 COMPOSE_PROJECT_NAME `campusclaw-next15-20261116t124118z`，仅本机回环端口 55788 / 55789；原七服务加本地假模型；数据库、上传与队列卷独立；backend 镜像源码指纹与本工作区逐文件匹配；不挂真实库、不运行 dev_seed.py | [隔离配置](runtime-isolation.json)、[启动](compose-up.txt)、[服务状态](compose-ps.jsonl) |
| HTTP 冒烟 | 26/29 检查通过。health/login=200、Next rewrite、首次改密 API 拦截、登录/refresh 完整身份、教师两班 API、logout 清 Cookie 后 refresh=401、鉴权配图 200/未登录401、Nginx SSE 分块/done 通过 | [http-smoke.json](http-smoke.json) |
| npm 审计 | critical=0 / high=0 / moderate=0 / low=4；audit 命令 exit 1 是低危导致。版本/通告从实际 via + nodes + lock 解析 | [原始审计](npm-audit.json)、[精确解析](npm-audit-summary.json) |
| 例外登记 | 移除旧 next；四个 low 的版本、GHSA、范围、责任组、缓解、失效条件和 2026-12-15 复查日期已登记。非人工签字，也不代表漏洞修复；未调整无关 pip 条目 | [登记快照](security-final/dependency-exceptions.json) |
| make check | **exit 0；41/41 PASS；42.38s** | [输出](make-check.txt)、[退出码](make-check.result.json) |
| make check-security | **make exit 2 / 脚本 exit 2 / BLOCKED；46.70s**。unregistered_vulns=[]、expired_exceptions=[]、npm high+critical=0；backend/mcp 本轮漏洞包均0。仅剩只读账号核查缺四个演示身份；不向教学库补账号 | [输出](make-check-security.txt)、[退出码](make-check-security.result.json)、[原始状态](security-final/run.json)、[账号阻塞](security-final/accounts-readonly.json) |
| OpenSpec | strict --all --no-interactive exit 0；38/38 | [输出](openspec-validate.txt)、[退出码](openspec-validate.result.json) |

## 阻塞项

1. **3.2 页面验收缺失**：浏览器 host 不可用；尝试原生 Safari 时工具返回 “Computer Use was not approved to use Safari”。没有打开测试页面，不能以 HTTP 会话检查或已有离线路由守卫检查代替页面刷新与教师切班验收；没有要求用户改密码或接管页面。
2. **3.3 状态码不符**：学生读取真实存在的他班合成资料，本轮 Nginx/Next rewrite 都返回 404，正文未泄露；tasks 要求403。现有 backend 镜像源码指纹与工作区一致，`backend/routers/materials.py` 原有归属分支即为404；本轮不修改接口或把预期改成404。
3. **3.3 直接 rewrite 的 SSE 压缩行为**：默认 gzip 下三个短 delta 在约1.24s合并到达；Next14 与 Next15 对照一致；identity 下两版本分别约0/400/800ms逐块到达，Nginx入口也正常。记录既有现象，不据此宣称 Next15 引入新回归，也不修改压缩配置。见 [版本对照](sse-version-comparison.json)。实际教案/资料页面 Markdown/KaTeX 渲染仍未验。
4. **4.3 安全门禁非零**：只读核查库没有四个演示身份。临时合成库已创建身份并用于运行时冒烟，但现有 gate 的 readonly_accounts 读取本机固定核查路径；未改判据、未替换真实库、未注入账号来制造绿灯。
5. 本轮不处理历史 backend OS Trivy HIGH=51，也没有刷新远端CI、真人签字、真实模型评测。

## 首次执行失败与更正

- 首次 npm 重锁尝试使用默认缓存目录，因目录不可写失败；改用独立临时 npm 缓存后重新定向生成成功，没有更改用户缓存权限。
- 首次 Docker build 因 buildx activity 目录不可写失败；[原始错误](docker-build-initial.txt)保留，BUILDX_CONFIG 指向临时目录后构建成功。
- 安全门禁首轮 pip-audit 工具目录不可写，exit2；[首轮完整证据](security-attempt1/run.json)与[原因](security-attempt1/tool-blocker.txt)保留；使用临时 UV_TOOL_DIR、UV_CACHE_DIR 与已有 Python 后完整重跑，没有复用旧审计 JSON。
- HTTP 探针开发时先修正登录 user 字段层级与 logout 应携带 Authorization 的脚本错误，再完整重跑；未为改善结果修改应用逻辑或跨班403预期。最终记录仍保留3个失败断言。

## 证据与清理范围

- 文本已移除绝对用户目录、工作区/临时路径、口令与密钥值；Cookie/Access/Refresh Token 不写证据。演示账号标识已替换为角色占位符（`<demo-teacher-1>` 等）。原始私有配置和数据库仅留临时目录，没有归档到仓库。
- `replay/*.py.txt` 是本轮探针/夹具/运行器的脱敏源快照，使用占位路径/口令，供审阅；不作为业务实现或可直接运行的一键入口。
- 本批次 SHA-256 清单见 [manifest.json](manifest.json)，它不包含自身。固定 `reports/security-evidence/` 更新为本轮实际扫描输出，原始历史副本已在私有临时目录保全。
- 独立栈结束后停止并移除本批次容器、网络与专属队列卷；未触碰已有教学栈，合成 SQLite/上传文件保留在私有临时目录供复核。镜像独立 tag 保留，未替换已有标签。
