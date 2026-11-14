# Verification Plan

## 适用范围与证据分层

本轮只交付 propose，文件为 `.openspec.yaml`、`proposal.md`、`design.md`、`tasks.md`、本文件；不创建 specs（skip_specs: true）。本次可执行检查只有只读/干跑版本探测、产物自查和 OpenSpec 严格校验。make check、make check-security、token 对照、重锁、构建、Trivy 与回滚均为**后续待执行**，不写为本轮 PASS。

本轮探测证据就地保存在 design.md 的 Q1–Q9；结构与 CLI 结果记录在本文件末尾，避免新增第六个文件。后续获准实施后，使用 `reports/lesson-10/<UTC批次>-upgrade-deps-and-jwt/`（下称 E）归档，不能在本轮创建。E 的 metadata 记录 UTC 时间、分支/HEAD/dirty 状态、工具版本、平台架构、命令、起止时间、stdout/stderr、退出码、清单/锁哈希及镜像 ID/digest。原始 token、真实密钥、Cookie 值、个人资料及教学数据不得进入证据。

## 逐项验收

| 编号 / 范围 | 检查与通过信号 | 失败/未知信号 | 后续证据位置 | 本轮状态 |
| --- | --- | --- | --- | --- |
| V1 版本与许可 | 重查 design Q1–Q9；目标存在、未撤回、修复范围覆盖；uv 项目解析成功；许可证有按仓库规则的判断/组内结论 | 无版本响应、解析冲突、无许可证结论；不得猜版本 | E/versions/、E/license-review.md；本次见 design.md | 版本探测已记录；运行兼容/许可待验 |
| V2 清单与锁 | 前端 katex=0.16.47、source-map-js=1.2.2、PostCSS 为最终验证目标；后端 certifi=2026.10.19、Pillow=13.0.0、PyJWT=2.15.1；python-jose 不在运行图；Next/React/DOM 与 python-pptx、cryptography 保持 | 任一路径残留目标漏洞包、锁漂移、误删 cryptography、出现不同的 jwt 包或手改哈希 | E/locks/（diff、hashes、npm-ls、uv-tree、lock-check、生产安装清单） | 待执行 |
| V3 Next 兼容 | 固定 Next 14.2.15/React 18.3.1/Node 22 下 npm ci、npm run build 成功；真实 CSS pipeline/source map、standalone 页面与公式用例通过；目标才从候选转确认 | 安装成功但构建/页面失败、未覆盖 CSS，或仅依据引擎范围宣称兼容 | E/frontend/（build、css、standalone、formula） | **PostCSS 最终版本待确认，候选 8.5.18** |
| V4 完整离线门禁 | 根目录 `make check`，33/33 原有子项全绿、exit=0，无跳过/放宽；新增断言放现有脚本以保留检查入口 | 任一子项失败、少于原 33、缺退出码、删断言凑数；如检查自然增加，应逐项通过并解释，不能删回33 | E/gates/check.txt、check-meta.json（通过 scripts/check.py --json 等价入口记录） | 待执行；历史33/33仅见 design Context |
| V5 安全门禁与归因 | 原样执行 `make check-security`，可 RED；对完整 npm/backend/MCP 应用依赖结果证明剩余 high/critical **仅来自 Next 及其传递依赖**；按下节逐条证明，不用总计代替 | 非 Next high/critical、无法归因/判级、不可解析/过期扫描；其他扫描故障单列，不能伪称 RED 仅因 Next | E/gates/security.txt、E/security/（raw audits、归因表、scanner/DB版本） | 待执行，安全 RED 不构成发布许可 |
| V6 后端镜像 | 对同一新建镜像全层（OS+语言+内嵌库）Trivy 扫描；**CRITICAL=0**，专项退出码=0；核对安装清单无 jose | CRITICAL>0、未扫全层、拿旧镜像/空JSON、数据库下载失败；HIGH另报而非抹除 | E/images/backend-trivy.json、backend-critical.txt、image-meta.json | 待执行，历史有12个Python critical |
| V7 JWT 等价 | 下表 J1–J8 正常/过期/篡改/刷新/撤销与边界对照全部通过；四种编码/解码组合及 API 结果一致 | claim/缺省值变化、时间边界不同、401/403/detail/Cookie改变、500、敏感信息入日志 | E/jwt/comparison.json、http-results.json、mutation.md | 待执行，仅源码差异已核实 |
| V8 图片/PPTX | 用合成 PPTX（文字+图片）验证解析文字/图片数量及语义内容不变；合法 JPG/PNG、损坏图片/文档遵循旧成功/失败边界；目标Linux架构可启动导入 | Pillow13 移除API导致解析变化/异常，坏文件误成功，架构无可用分发 | E/pillow/（fixtures说明、结果、Linux启动记录） | 待执行 |
| V9 回滚与复核 | 成套旧代码/清单/锁/镜像回滚后健康、新旧token与刷新通过，数据卷未迁移；独立复核人签名和实际日期可查 | 混用版本、未演练、依赖教学库、缺人工证据 | E/rollback/、E/review.md | 待执行 |

## 安全门禁：允许 RED 的证明边界

1. 原样保存 `make check-security` 的退出码及 npm audit --omit=dev、backend/MCP pip 审计、密钥扫描子项结果。脚本会写 reports/security-evidence 与 .review；后续运行前另存已有证据，运行后按批次归档，禁止把旧 JSON 当新结果。本轮不运行该脚本。
2. 以重锁后的 package-lock 全路径解析 npm audit 的 advisory、via 与 nodes，列出包/版本/漏洞ID/严重度/引入链/修复状态。Next 包级“受影响”的聚合条目与底层 advisory 分开记录，避免重复计数，也不以包数冒充 CVE 数。
3. 允许残余集合仅限可证明源于保持的 Next 版本及其专属传递依赖漏洞。**PostCSS 与 source-map-js 即使由 Next 引入，也属于本轮必须修复的对象**，指定通告不得继续出现；katex 目标漏洞同样必须消失。其他直接依赖不能借共有依赖路径被归为 Next。
4. 后端与 MCP 必须完成审计；certifi 指定 GHSA 消失，Pillow 目标漏洞消失，python-jose/CVE-2026-85394 消失。ecdsa/pyasn1 等若仍存在，必须证明必要反向依赖并逐项判级；high/critical 不能仅写“已移除 jose”就忽略。pip 审计不提供严重度时，关联官方 GHSA/CVE 或 Trivy 的漏洞ID与来源补齐；UNKNOWN 不视作零。
5. 归因断言：应用依赖的 high/critical 集合扣除已证实 Next 集合后为空。若不为空或存在 UNKNOWN，**该判据失败**；可交付真实 RED 和阻断项，不能宣称 A+B 安全验收通过。密钥扫描范围不足/联网失败也须单独列明，不能说“安全门禁仅因 Next 为 RED”。
6. 镜像扫描另含 OS 层。必须附全层非 Next high/critical 清单；历史后端 OS 有 HIGH，不能把应用级“仅 Next”扩展为整个系统结论。若验收范围要求全系统仅剩 Next，则任何非 Next HIGH 都使该结论失败，另起基础层维护，不在本轮偷改基础镜像或豁免。后端全层 CRITICAL=0 仍为独立硬判据。

## Trivy 检查方法（仅后续计划）

使用固定 Trivy 版本或容器 digest，记录 `trivy --version` 与漏洞库元数据，对不可变 IMAGE_ID 执行：

```text
trivy image --scanners vuln --format json --output <E>/images/backend-trivy.json <IMAGE_ID>
trivy image --scanners vuln --severity CRITICAL --exit-code 1 <IMAGE_ID>
```

未筛选 JSON 用来汇总所有 Results 下的 OS/语言/内嵌库漏洞；CRITICAL 总和为0且第二条正常退出才通过。不得使用 --ignore-unfixed、关闭 OS 扫描、忽略文件或筛掉未知目标来做零。前端/MCP 同样保留完整扫描报告，OS HIGH 单列并保持发布限制。镜像构建/扫描失败或漏洞库不可用标 BLOCKED，不套用历史结果。

## JWT 新旧对照用例设计

对照版本为 python-jose 3.5.0 与 PyJWT 2.15.1（含规划的 security 兼容适配层）。使用临时 SQLite/上传目录、假模型、专用测试密钥；只用合成教师/学生，固定 UTC 时钟及 UUID/jti，不使用真实会话。旧 jose 仅在隔离测试 oracle 环境运行；不得重新加入应用生产依赖或镜像。补充断言优先放 `apitest/check_lessons_2_5.py` 等现有认证检查入口，原门禁仍33项。

每条至少覆盖“旧编码→旧解码、旧编码→新解码、新编码→旧解码、新编码→新解码”；验证解码 payload 类型/值/可选字段是否省略，并经过实际 deps/路由比较状态码、中文 detail、响应字段和 Cookie 属性。签名字符串不要求逐字相同；失败 token 不能进入业务处理或泄露内部异常。

| 用例 / 类型 | Given / When | Then：新旧实现必须一致 | 检查名/证据键 |
| --- | --- | --- | --- |
| J1 正常签发/解析 | 已改密教师/学生，覆盖 class_id=null、任教列表空/多班、subject与班主任字段存在/省略；固定时钟/jti签发access/refresh并交叉解码 | HS256；user_id为int、改密为bool；保留现有claims；type=access/refresh；UTC整数iat/exp、jti hex；有效期分别7200/604800秒；登录/刷新响应token_type=bearer，refresh HttpOnly/Path=/api/auth/SameSite/Secure/Max-Age不变 | JWT-J1 正常 claims 与双向兼容；comparison.json/J1 |
| J2 过期/临界 | 冻结UTC到N秒并在同秒的小数位置重复；exp=N-1/N/N+1；分别请求受保护接口及refresh；再测两个TTL两端 | 按jose旧判据：exp<N拒绝，exp=N和N+1在该整数秒接受；下一整数秒再过期。失败走现有401中文消息；类型检查和签名仍开启，不靠扩大所有claim leeway混过 | JWT-J2 过期整数秒边界；comparison.json/J2、http-results.json/J2 |
| J3 篡改/非法 | 分别改payload但保留签名、改签名、用错误密钥、alg=none/HS512、截断/乱码；调access与refresh入口 | 全部拒绝，access为401“认证失效，请重新登录”，refresh为401“刷新令牌已失效，请重新登录”；保留WWW-Authenticate边界，无500、无内部异常/token日志 | JWT-J3 篡改与算法失败；comparison.json/J3 |
| J4 type/token_type边界 | access拿去refresh、refresh拿去业务接口、有效签名但缺失/未知type；正常签发时分别读取payload与HTTP响应 | 不交叉放行；refresh类型错401“令牌类型错误”，业务401；不将payload字段改名为token_type，HTTP仍bearer | JWT-J4 类型不可互换；comparison.json/J4 |
| J5 刷新与权限现态 | access过期、refresh有效；临时库修改任教班级/学科/改密状态后调用refresh；另测缺Cookie、过期Cookie、账号已删除 | 正常200，响应完整user取当前数据库，续发access与7天refresh Cookie；字段与旧路径一致，jti更新；缺Cookie401“未提供刷新令牌”，无用户401“账号不存在”；前端会话恢复/原请求重试沿用既有检查 | JWT-J5 刷新恢复与滑动续期；http-results.json/J5 |
| J6 撤销/登出边界 | 持旧access/refresh：调用logout并清客户端内存；再尝试无Cookie刷新；分别对独立fixture执行班主任密码重置、删除账号、普通改密 | logout清refresh与CSRF Cookie；无Cookie刷新401。重置后旧access调用业务为403“请先修改初始密码”，认证自身改密/刷新仍按旧规则工作；删账号后access/refresh401。普通改密与手工重放旧refresh按旧基线比较，不虚构全令牌撤销或新增黑名单，多端互不踢下线 | JWT-J6 既有撤销路径；http-results.json/J6 |
| J7 claim校验边界 | 有效签名但iat=N+60、不可转整数iat/exp、缺省可选claim、nbf=N-1/N/N+1、aud/sub/jti的正常/错误类型 | 未来iat按旧类型校验后允许；非法整数按既有JWT失败边界拒绝；不新增claim必填要求。nbf/aud/sub/jti对照旧库结果，不顺带扩大或缩紧合同；发现其他差异先适配并留证，未解决即失败 | JWT-J7 claim默认差异；comparison.json/J7 |
| J8 权限/回滚连续性 | 维护前签发的token在新版本使用、新版token交给旧实现；未登录、错误角色、跨班/跨科请求分别执行；模拟回滚后refresh | 有效token按原TTL与权限继续工作；未登录401、错误角色403，跨范围遵循现有主规约403/私有资源404，不产生越权内容；保留现有审计语义；回滚不靠轮换密钥强迫重新登录 | JWT-J8 权限与回滚；http-results.json/J8、rollback记录 |

J7 不把旧库所有未知异常当已验证：若极端类型触发既有500或与规约冲突，记录具体输入与结果并暂停相关实施，先澄清规约；不能凭迁移之名悄悄修复外部行为。对照中的正常与已知失败路径必须具备明确断言，不能只检查函数跑完。故障注入限临时环境，至少人为移除验签/过期或type检查之一，确认相应检查变红，再恢复并重跑。

## 证据归档与完成声明

后续报告按 `V/J编号 → 既有Scenario → 检查名 → 实际结果 → E路径` 映射。缺执行证据写待验；自动检查与独立人工复核分别记录。RED允许保留仅指本轮风险收敛的验收政策，不修改安全规范“high/critical未处理不能正式发布”的要求。

后续获准提交时提交说明保留以下三行（本轮不创建提交），其中 Verify 必须带真实结果，Evidence 必须替换成实际批次：

```text
Change: 2026-11-14-upgrade-deps-and-jwt
Verify: <实际命令与结果，含安全RED原因>
Evidence: reports/lesson-10/<实际UTC批次>-upgrade-deps-and-jwt/
```

## 本轮 propose 执行记录

2026-11-14，分支 lesson10-delivery，起始 HEAD `04088626787c1ca5dcb99b771d407d1c63e6153c`。只读版本探测结果及失败命令见 design.md Q1–Q9。未运行 make check、安全门禁、JWT用例或镜像检查；未修改清单/锁/源码，未执行 apply/archive、commit/push/checkout/reset/stash，未运行教学库操作。

本轮产物自查通过（exit=0）：恰好5个文件，schema/date/skip_specs正确，无specs目录；24个任务全部未勾选；版本矩阵9行均有依据或待确认说明；上述四条必需判据与J1–J8齐全；本目录Markdown相对链接可解析。`git diff --exit-code` 与 `git diff --cached --exit-code` 均为0，未跟踪文件仅为这5个文件，清单/锁/源码无差异。

严格校验实际命令（仓库根目录）：

```sh
OPENSPEC_TELEMETRY=0 openspec validate 2026-11-14-upgrade-deps-and-jwt --strict --no-interactive
```

exit=0，原始输出如下：

```text
Change '2026-11-14-upgrade-deps-and-jwt' is valid
ℹ [INFO] file: skip_specs is set in .openspec.yaml: change declares no spec-level behavior changes, zero deltas accepted
```

`openspec status --change 2026-11-14-upgrade-deps-and-jwt` 也实际返回 `Progress: 3/3 artifacts complete (1 skipped)`；此处complete仅表示规划文件存在，tasks.md实施任务仍全部未勾选，不表示实施/安全/课程验收完成。CLI给出的apply提示未执行。

## 本轮校验结果（2026-11-14 追加）

```text
$ openspec validate 2026-11-14-upgrade-deps-and-jwt --strict
Change '2026-11-14-upgrade-deps-and-jwt' is valid
ℹ [INFO] file: skip_specs is set in .openspec.yaml: change declares no spec-level behavior changes, zero deltas accepted
```

目录自查：`.openspec.yaml`、`proposal.md`、`design.md`、`tasks.md`、`verification-plan.md` 五个文件，未修改清单/锁/源码。

## 实施结果（2026-11-14，分支 `deps/upgrade-a-b`）

- 实际版本：katex 0.16.47、source-map-js 1.2.2、**postcss 8.5.33**（8.5.18 仍受 `GHSA-fxqj-rqcc-2cmp` 影响）、certifi 2026.10.19、Pillow 13.0.0、PyJWT 2.15.1；python-jose 移除。MCP `opentelemetry-api` 1.45.1→1.45.2（计划外补丁，消除非 Next 漏洞）。
- `make check` 33/33 PASS；前端 npm ci/build/tsc 全 0；安全门禁 RED，但 npm high=0、critical 仅 `next`，backend/mcp pip 漏洞=0。
- 后端镜像 Trivy 全层 CRITICAL=0（HIGH=51 为基础镜像 OS）；前端 CRITICAL=4 全来自 Next；MCP CRITICAL=0。
- JWT：J2/J3/J7 边界断言通过；真实镜像登录/刷新/受保护接口/登出冒烟通过。
- 未完成：许可证独立评审、J1–J8 全量 HTTP 对照、回滚演练、非实施者复核。详见 `reports/lesson-10/20261114T104516Z-deps/deps-report.md`。

```text
$ openspec validate 2026-11-14-upgrade-deps-and-jwt --strict
Change '2026-11-14-upgrade-deps-and-jwt' is valid
ℹ [INFO] file: skip_specs is set in .openspec.yaml: change declares no spec-level behavior changes, zero deltas accepted
```
