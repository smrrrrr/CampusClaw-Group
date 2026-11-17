# Design

## Context

动机与范围见 [proposal.md](proposal.md)。本轮为 propose，基线为 `lesson10-delivery` / `04088626787c1ca5dcb99b771d407d1c63e6153c`，开始时工作区干净；仅允许本变更目录内五个文件。已读取 AGENTS、OpenSpec 配置与索引、安全/测试/部署/完成定义规范、清单/锁文件、JWT 实现及登录主规约。

当前依赖分别由 `frontend/package-lock.json`、`backend/uv.lock`、`mcp-server/uv.lock` 锁定。前端镜像 Node 22，后端 Python 3.12；后端声明 `requires-python >=3.12`。JWT 调用仅在 `backend/security.py`，异常由 `main.py`、`deps.py`、`routers/auth.py` 经 security 导出的 `JWTError` 捕获。cryptography 还用于 MCP Fernet，不能随 jose 一起删除。

历史门禁证据 `reports/lesson-10/20261114T072100Z-apply/gates/check-meta-final.json` 实际有 33 个子项、exit=0；其报告正文部分仍写 32/32。本轮只读盘点 `scripts/check.py` 的 4 个固定步骤与自动收集的检查文件，合计也是 33，不将历史结果冒充本次执行。

## Goals / Non-Goals

目标为可审查的依赖选择、可复现的定向重锁方案和 token 行为等价验证设计。`skip_specs: true` 仅因不改变业务要求；任何无法保持的行为差异都阻断实现，不能用该标志免除业务规约。

不升级 Next/React 大版本，不迁移数据库/向量服务/语言，不改 API、角色权限、并发和业务状态机。本轮不执行安装、重锁、业务测试、镜像构建/扫描、部署或提交；下文实施命令均为后续授权后的计划，已执行探测另有明确记录。

## Decisions

### 1. 版本矩阵：发布/解析与运行验证分开

所有探测于 2026-11-14 执行。Q 编号对应下一节可复查命令与结果；注册表元数据经 HTTPS GET 在内存解析，未落盘。未运行构建/回归，因此所有运行兼容结论仍待验。

| 对象 | 当前锁定 | 规划目标/候选 | 核实依据与兼容性判断 | 实施选择 |
| --- | --- | --- | --- | --- |
| katex | 0.16.11 | 0.16.47 | Q1：确有该版本，MIT；依赖 commander `^8.3.0`。现有 rehype-katex 7.0.1 要求 katex `^0.16.0`，包含目标。公式渲染回归待验 | 更新直接依赖精确版本 |
| source-map-js | 1.2.1 | 1.2.2 | Q2：确有该版本，Node `>=0.10.0`，BSD-3-Clause；满足 PostCSS 候选的 `^1.2.1` | 根 overrides 精确为 1.2.2，核查所有锁路径 |
| postcss | 8.4.31 | **最终兼容版本待确认；候选 8.5.18** | Q3/Q4：8.5.18 存在，Node 范围包含 22。两条通告修复下限分别为 8.5.12、8.5.18。Next 14.2.15 将其精确声明为 8.4.31，无放宽范围；不能声称获 Next 官方兼容保证 | 后续隔离试验根 overrides=8.5.18，通过 Next 构建/CSS/公式检查后才能定版；失败则阻断，不退回漏洞版本 |
| certifi | 2026.7.22 | 2026.10.19 | Q5/Q6：2026.10.18 与 .19 均存在，Python `>=3.7`，uv 全项目 dry-run 均解析成功。GHSA 修复下限 .18，正文建议 .19 恢复未受影响根证书 | 直接声明精确安全版本，防重锁回退；MPL-2.0 组内评审待确认 |
| Pillow | 12.3.0 | 13.0.0 | Q7：存在且 Python `>=3.11`，含 cp312 macOS arm64 / Linux aarch64、x86_64 wheel。Q5：python-pptx 1.0.2 只要求 `Pillow>=3.3.2`，无上限。Q6：uv 全项目 dry-run 可解析 | **直接声明 `Pillow==13.0.0`**，无需 uv override；保留 python-pptx 1.0.2 锁版本 |
| python-jose[cryptography] | 3.5.0 | 移除 | Q9 与官方通告：CVE-2026-85394 影响 <=3.5.0、无修复。当前只用 HS256，不能据通告直接断言本服务已可被利用 | 清单移除并重锁，确认运行产物不含 jose；不保留为生产测试依赖 |
| PyJWT | 未声明 | 2.15.1 | Q5/Q8：已发布，MIT，Python `>=3.9`，py3-none-any wheel；uv 安装 dry-run 解析成功。无 crypto extra 时 Python 3.12 无必需传递依赖；替换后的完整锁图待验 | 直接声明 `PyJWT==2.15.1`，HS256 无需 crypto extra |
| Next / React / React DOM | 14.2.15 / 18.3.1 / 18.3.1 | 保持 | Q4：Next 要求 React/DOM `^18.2.0`，Node `>=18.17.0`，现版本满足 | 清单/锁文件复核不升级；漏洞另行跟踪 |
| python-pptx / cryptography | 1.0.2 / 50.0.1 | 保持 | Q5 与当前 uv.lock；cryptography 是显式业务依赖 | 不做全量升级，不因 jose 移除误删 Fernet 支持 |

Pillow 此次 **12→13 是大版本例外**；本任务“非大版本”限制特指不升级 Next/React，按明确指定的 Pillow 目标规划，不把它描述为小版本更新。

### 2. 本次只读核实记录

Q1–Q5、Q7 使用 `python3 -` 内存读取注册表 JSON；可复查形式如下（逐个使用表中 URL；不创建脚本或下载文件）：

```sh
python3 - <<'PY'
import json, urllib.request
url = 'https://registry.npmjs.org/postcss/8.5.18'
with urllib.request.urlopen(url, timeout=20) as response:
    data = json.load(response)
info = data.get('info', data)
for key in ('name', 'version', 'dependencies', 'peerDependencies', 'engines',
            'requires_python', 'requires_dist', 'license', 'license_expression'):
    if key in info:
        print(key, info[key])
PY
```

| 编号 | 实际查询与结果（HTTPS GET 均成功，探测进程 exit=0） |
| --- | --- |
| Q1 | GET `https://registry.npmjs.org/katex/0.16.47` → version=0.16.47、commander=^8.3.0、license=MIT |
| Q2 | GET `https://registry.npmjs.org/source-map-js/1.2.2` → version=1.2.2、engines.node=>=0.10.0、BSD-3-Clause |
| Q3 | GET `https://registry.npmjs.org/postcss/8.5.18` → version=8.5.18、engines.node=^10 \|\| ^12 \|\| >=14；dependencies=nanoid ^3.3.12、picocolors ^1.1.1、source-map-js ^1.2.1 |
| Q4 | GET `https://registry.npmjs.org/next/14.2.15` → postcss=8.4.31（精确）、react/react-dom=^18.2.0、node=>=18.17.0；与本地锁文件一致 |
| Q5 | GET `https://pypi.org/pypi/python-pptx/1.0.2/json` → Pillow>=3.3.2、Python>=3.8；GET `https://pypi.org/pypi/PyJWT/json` → version=2.15.1、Python>=3.9、MIT；GET `https://pypi.org/pypi/certifi/2026.10.18/json` 及 `/2026.10.19/json` → 两版均存在、Python>=3.7、MPL-2.0，wheel 未撤回 |
| Q7 | GET `https://pypi.org/pypi/Pillow/13.0.0/json` → version=13.0.0、Python>=3.11、MIT-CMU；上述 cp312 wheel 未撤回 |

Q6：在原仓库运行 uv 0.13.5，仅 dry-run，不写锁、不安装、不下载 Python、不构建 sdist。两次 exit=0，第二次为选择版本的解析依据：

```text
$ uv lock --project backend --dry-run --upgrade-package certifi==2026.10.18 --upgrade-package pillow==13.0.0 --no-cache --no-python-downloads --no-build --color never
Resolved 53 packages in 5.30s
Update certifi v2026.7.22 -> v2026.10.18
Update pillow v12.3.0 -> v13.0.0

$ uv lock --project backend --dry-run --upgrade-package certifi==2026.10.19 --upgrade-package pillow==13.0.0 --no-cache --no-python-downloads --no-build --color never
Resolved 53 packages in 5.97s
Update certifi v2026.7.22 -> v2026.10.19
Update pillow v12.3.0 -> v13.0.0
```

Q8：仅解析 PyJWT 在现有 Python 3.12.15 环境的安装计划，exit=0，未安装：

```text
$ uv pip install --python backend/.venv/bin/python --dry-run --no-cache --no-python-downloads --no-build --color never 'PyJWT==2.15.1'
Using Python 3.12.15 environment at: backend/.venv
Resolved 1 package in 2.25s
Would download 1 package
Would install 1 package
 + pyjwt==2.15.1
```

Q9：浏览官方通告与带版本源码，核实修复范围及差异；以下为本次证据来源：

- [PostCSS GHSA-6g55-p6wh-862q](https://github.com/advisories/GHSA-6g55-p6wh-862q)：受影响 <=8.5.11，修复 8.5.12。
- [PostCSS GHSA-r28c-9q8g-f849](https://github.com/advisories/GHSA-r28c-9q8g-f849)：受影响 <=8.5.17，修复 8.5.18。
- [certifi GHSA-6q48-6c7w-9gw2](https://github.com/advisories/GHSA-6q48-6c7w-9gw2)：修复下限 2026.10.18，正文建议 2026.10.19 或以后。
- [python-jose GHSA-3qf3-8w2g-rqmx](https://github.com/advisories/GHSA-3qf3-8w2g-rqmx)：对应 CVE-2026-85394，无修复版本。
- [python-jose 3.5.0 jwt.py](https://github.com/mpdavis/python-jose/blob/3.5.0/jose/jwt.py) 与 [PyJWT 2.15.1 api_jwt.py](https://github.com/jpadilla/pyjwt/blob/2.15.1/jwt/api_jwt.py)：核对默认 options、iat、exp 的静态语义，未运行 token 对照。
- [Next 14.2.15 CSS 处理入口](https://github.com/vercel/next.js/blob/v14.2.15/packages/next/src/build/webpack/config/blocks/css/index.ts)：动态 require('postcss') 并调用 process；仅能说明 override 影响真实构建路径，不能证明 8.5.18 构建成功。

未成功的探测也保留：`npm --logs-max=0 --update-notifier=false --cache=/dev/null view katex@0.16.47 version dependencies --json` exit=1，ENOTDIR `/dev/null/_cacache/tmp`，为避免缓存写入而使用的路径不可用；不能将该失败解释为包不存在。后改用上述无落盘 GET。`uv pip index --help` exit=2：`error: unrecognized subcommand 'index'`；本机 `uv add --help` 也未提供 dry-run，因此没有执行 add，改用 lock/pip install 的 dry-run。`--no-cache` 仅使用工具生命周期内的临时缓存，不改项目清单、锁或虚拟环境。

### 3. 前端 overrides 与兼容性准入

选择根 overrides 统一约束 source-map-js 和 PostCSS，可防多路径残留；不新增直接 PostCSS 使用点，不全量 npm update。PostCSS 8.5.18 与 Node 22 的引擎兼容且满足两条修复下限，但它超出 Next 的精确声明。替代方案是仅 scoped Next override；本轮优先根 override，实施时用锁图证明覆盖范围确为预期，不误改其他版本。

**当前没有“已验证与 Next 14.2.15 运行兼容”的最终 PostCSS 版本。** 后续仅在获准的隔离环境试验候选，运行 npm ci、完整 Next build、CSS/source map 检查及既有公式/Markdown 回归，检查 Node 22 与 standalone 产物。全部通过才把候选确认成目标；失败则保留待确认并阻断，不扩大到 Next/React 大版本，也不自行改用其他未经核实版本。

### 4. Python 依赖声明与锁文件策略

Pillow 没有 python-pptx 上游约束冲突，直接声明 `Pillow==13.0.0` 能表达当前安全版本意图，无需使用更强的 `tool.uv.override-dependencies`。certifi 同样直接声明精确目标；仅靠一次 `uv lock --upgrade-package` 而不记录约束会在以后重锁时丢失安全意图。PyJWT 精确声明，不安装 `jwt` 这个不同的包，也不添加 crypto extra。certifi MPL-2.0、Pillow MIT-CMU 按安全规范先取得许可证判断/组内评审证据，不默认视作已有书面例外。

后续实施才修改清单并在各项目目录定向重锁；不手改 integrity/hash/resolved，不删除锁文件重建。前端使用 npm 的 package-lock-only/ignore-scripts 重锁后以 npm ci 验证，后端使用 uv lock 定向升级后以 `uv sync --locked --no-dev` 验证生产依赖、以包含 dev 的锁定同步运行门禁。拒绝全局 `--upgrade`，保留无关锁版本；审查 PostCSS 引起的 nanoid/picocolors 必要传递变化。

移除 jose 后由解析器清理仅被它引用的 ecdsa、rsa、pyasn1；先检查反向依赖，不手工强删仍被其他依赖使用的包。MCP 自身清单/锁保持不变，但仍审计以免漏掉非 Next 漏洞。Q6 没有移除 jose、Q8 也没有建立替换后完整项目图，不能当作最终锁文件验证。

### 5. JWT 等价适配与数据流

保留流程：登录/改密 → security 签发 → access 响应及 refresh Cookie；业务请求 → security 验签/解析 → deps 查询用户存在性及当前改密状态 → 既有权限判定；刷新 → 验证 refresh `type` → 查询当前数据库身份 → 滑动续期；登出 → 清除 Cookie/客户端内存。无新增持久状态、黑名单、撤销表或锁，无模型调用、并发机制变更。

- 使用现有服务端密钥与明确算法白名单（当前 HS256），不从 token header 决定可接受算法；保留 `settings.jwt_algorithm` 的受控配置路径，不扩大算法支持。验签和算法检查不可关闭。
- 保留 security 模块导出的 `JWTError` 捕获边界，适配 PyJWT 的失败到该边界，调用方中文 detail、状态码、WWW-Authenticate 与日志脱敏不变。不直接把 PyJWT 内部异常原文返回客户端。
- claims 保留 `user_id`（整数）、role、class_id（可 null）、must_change_password（布尔）、按现有条件包含的 teaching_classes / subject / homeroom_class_id；不把缺省省略改成显式 null。UTC iat/exp 为整数秒，jti 为 UUID hex；access 120 分钟、refresh 7 天。payload 中叫 `type=access/refresh`，HTTP 响应 `token_type=bearer`，不能重命名混用。
- 旧 jose 的 iat 校验仅检查可转整数，不拒绝未来时间；PyJWT 默认还拒绝未来 iat。规划在有回归约束的最小适配层中保留旧类型检查，替代其未来时间限制，不能通过简单关闭所有 claim 校验应付。
- 旧 jose 仅在 `int(exp) < 当前UTC整数秒` 时判过期，PyJWT 默认在 `exp <= 当前浮点秒` 判过期。为达到本任务等价要求，规划由适配层完整执行旧 exp 判据；如关闭 PyJWT 的原生 exp 检查，必须同步替代且回归证明，不得留下无过期校验路径。不用统一增加 leeway（会同时改变 nbf 等行为）。缺省可选 claim 不新增 required 约束；本服务正常签发始终含 iat/exp/jti。
- 对 nbf、aud、sub、jti 等可选输入保留原有验证，补边界对照；本轮不引入新的发行者、受众、token version 或撤销语义。若对照发现额外差异，先定位兼容适配，无法保持则停止并修订计划，不能默默改变合同。
- 新旧库交叉验签用于滚动升级和回滚时已有 token 连续有效；无需保证签名字符串逐字相同，应比较固定时间/jti 的语义 payload 和 HTTP 结果。完整用例见验证计划 J1–J8。

### 6. “撤销路径”按当前合同验证

登录主规约明确无状态、多端在线、不引入黑名单。现状 logout 只清 refresh/CSRF Cookie，前端清内存；旧 token 被另行保存后不会仅因 logout 在服务端即时失效。密码重置通过数据库 must_change_password 拦截旧 access 的业务访问（403）；账号删除使认证/刷新返回 401。普通改密未实现 token version，不能声称全部旧 token 已撤销。

因此对照必须覆盖这些现有行为，包括 logout 后浏览器无法凭已清除 Cookie 刷新、重置后旧 access 被业务依赖拒绝、账号删除后旧 access/refresh 被拒绝，以及旧 refresh 重放的现有无黑名单边界。不借替换 JWT 库新增“登出后所有 token 立即失效”。

## Risks / Trade-offs

- [Next 残余 high/critical] → 保留真实 RED 与漏洞明细，不新增豁免、不放宽检查；本轮不宣称正式发布可用。
- [PostCSS override 超出 Next 精确 pin] → 已发布/修复/引擎信息已核实，运行兼容仍待确认；构建失败阻断目标定版。
- [Pillow 跨大版本与原生 wheel] → 元数据可解析不保证图片/PPTX 行为；后续验证 PPTX 文字与图像提取、坏图/损坏文件及目标 Linux 架构，不动教学数据。
- [JWT 默认语义差异] → exp 秒边界与未来 iat 明确适配，对照、交叉解码、失败路径及旧 token 回滚检查缺一不可。
- [许可证] → certifi MPL-2.0 不在仓库默认白名单，Pillow 标识 MIT-CMU 也需核对。评审/书面例外的责任人与证据待确认；本轮不改规范、不自授豁免。
- [安全证据范围] → 历史 Trivy 后端 OS 层已有 51 HIGH、0 CRITICAL，Python 层另有 critical；即使完成 A+B，也不能直接宣称整个镜像或整个系统的剩余 high/critical 仅来自 Next。应用依赖归因、全层镜像 critical=0 与其他扫描失败分别验收，任何更广义“仅 Next”结论若存在非 Next high 均须判失败。
- [扫描器/漏洞库变化与上游基础镜像] → 记录时间、DB 版本、镜像 ID/digest、全层原始结果；本轮不承诺后续扫描必定为 0，不借此扩大 Dockerfile/基础层升级范围。OS 风险需后续另起维护；未判级或不可解析响应为 UNKNOWN，不当作零。

## Migration Plan

后续在明确实现授权后，按 tasks 的六阶段执行；先关闭待确认的版本/许可证事项，再改清单与 JWT、定向重锁，随后跑双门禁与全层镜像扫描。原数据库/上传目录/环境密钥不更改；镜像验证使用独立测试目录与合成数据，不挂载真实教学卷，不调用 dev_seed。不在本轮启动这些操作。

回滚方案（未演练）：记录旧代码、成套清单与锁文件、工具链版本及旧镜像 ID/digest。若构建/对照/门禁失败，停止推进；在后续授权的实现环境恢复整套维护前清单、锁及 security 实现，重建或使用已记录旧镜像，禁止混用新代码旧锁。当前会话不执行 checkout/reset/stash。回滚无需数据迁移；保留密钥、Cookie 配置与数据，验证新旧双向 token 解码、刷新和健康后才认为恢复成功。恢复旧版本也恢复旧漏洞，不能作为安全验收通过。

## Open Questions

- PostCSS 候选的完整 Next 14.2.15 / Node 22 构建、CSS 和 standalone 回归能否通过：待后续隔离试验，当前保持“待确认”。
- 许可证组内评审人与独立复核人姓名、后续镜像架构和原始镜像 digest：待实施前登记，不伪造签名或发布记录。
- 替换后完整锁图、实际剩余漏洞与镜像 CRITICAL 数：待实施后验证，Q6/Q8 不代替这些结果。
