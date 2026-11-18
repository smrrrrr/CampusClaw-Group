# 第 10 课 Windows 本地复验（2026-11-17）

- 基线：PR #3 源分支 `deps/upgrade-a-b`，`977bcde028b24892ac58466b5612e844bd5b2ecb`。环境为 Windows 10.0.26200、Docker Engine 29.8.0、Compose 5.5.1、Python 3.12.13、Node.js 22.16.0、npm 10.9.4、uv 0.12.18 和 OpenSpec 1.13.1。
- 执行方式：在空目录中新克隆，由 Codex 辅助执行。普通启动使用校验过的组内演示数据副本，另开空库与本地假模型做业务链路。模型服务和部署均在本机测试范围。时间戳见各 JSON。

## 启动、业务和门禁

| 判据 | 本次结果 | 证据 |
| --- | --- | --- |
| 从干净目录启动，七服务可用 | 首次构建后 backend 因入口脚本 CRLF 无法启动。将本地脚本恢复为提交中的 LF 后重新构建，七服务运行，backend、frontend、mcp-tools 与 RabbitMQ healthy。`/health`、`/api/health`、`/login` 均为 200；数据库和 MCP 为 ok，模型未配置。三个应用容器的 OCI revision 与基线 SHA 一致，扫描均为 0 个 `.py`。 | [启动与镜像](boot.json) |
| 作业流转和跨班隔离 | 合成环境中学生提交 200、教师初批 202，轮询观察到 pending → running → succeeded。本人查结果 200，别班讲义 404，本班讲义 200。 | [冒烟](h5-smoke.json)、[三态及安全用例](h5-api.json) |
| CORS、CSRF 与审计 | 允许来源预检 200 并返回该来源；外部测试来源预检 400 且无允许来源响应头。Cookie 请求缺 CSRF 头被拒绝，返回 403。审计库中有跨班 404 和 CSRF 403 记录。成功链路的完整七列审计留待核实。 | [三态及安全用例](h5-api.json) |
| Windows 普通门禁，两次同参 | 两次均为 42/43 通过，退出 1，唯一失败均为 `check_os_vuln_gate`。Windows 子进程以本地代码页输出中文，回归按 UTF-8 解码而失败。该单项原样在 Linux 镜像中为 17/17。 | [第 1 次](check-1.json)、[第 2 次](check-2.json)、[Linux 单项](trivy-linux-test.txt) |
| 安全门禁，两次同参 | 两次均 PASS、退出 0。两次均重新访问漏洞库，未复用历史结果。密钥扫描范围完整且未检出泄漏，npm high+critical 为 0，未检出未登记或过期的依赖例外。此结果覆盖项目安全专项脚本的范围。 | [第 1 次](security-1.json)、[第 2 次](security-2.json) |
| 真实 RabbitMQ、假模型 | 首轮 A1 耗时断言失败，接收请求 P95 为 274 ms，假模型实测 206 ms。同参重试为 14/14 通过，P95 为 97 ms，假模型 227 ms，含暂停、崩溃恢复、幂等、死信和日志关联。两轮耗时结果均保留。 | [首轮](../../async-grading/20261117-windows-local-real-broker-result.json)、[复跑](../../async-grading/20261117-windows-local-retry-real-broker-result.json) |
| 60 秒窗口报数 | 采集器读取指定 UTC 窗口并返回三个技能。该窗口没有样本，失败率为 null，面板口径为「无样本」。 | [窗口输出](observability-window.json) |

## PR 评审发现

1. **门禁可能接受缺失扫描内容。** `scripts/trivy_os_gate.py` 的 `collect_findings()` 把 `{}` 读成零发现，实际退出 0。工作流按通配符传入已有报告。建议校验预期三份文件与报告结构，同时接受扫描器产生的合法零漏洞报告。证据见 [空对象](trivy-empty-object.json)。
2. **漏洞例外可跨软件包生效。** 门禁读入 `packages`，判定时只按 CVE 查找例外。用已登记 CVE、未登记软件包、有修复版本的合成报告复现，程序退出 0。按例外声明中的软件包校验命中应有回归用例。证据见 [包范围反例](trivy-excepted-cve-other-package.json)和[退出码](trivy-negative-probes.json)。
3. **Windows 从零启动缺少行尾约束。** 默认 `core.autocrlf=true` 的克隆将 `backend/entrypoint.sh` 转成 CRLF。镜像中该文件存在，执行时仍报 `exec /app/entrypoint.sh: no such file or directory`。本次用 Git 对象中的 LF 字节恢复，在此克隆的本地 Git 属性里固定该文件为 LF。仓库可为容器入口脚本声明 LF。
4. **漏洞门禁回归依赖默认字符编码。** `apitest/check_os_vuln_gate.py` 通过 `python -I` 调用带中文输出的脚本。隔离模式忽略 Python 环境编码设置，Windows UTF-8 读取端与子进程的本机代码页不一致。两次本机门禁与 Linux 单项结果可重放。建议在父子进程两端显式使用 UTF-8。

对照依赖清单和锁文件，Next.js 为 15.5.28，React 和 React DOM 均保持 18.3.1。工作流门禁管道已有 `set -o pipefail`。审计字段清洗与截断回归随两次普通门禁均通过。第 1、2 项需处理后再据扫描证据判定 PR 是否满足镜像门禁要求。

## 尚需现场完成

| 编号 | 后续所需条件 |
| --- | --- |
| 3.2 | 已完成桌面 HTTP 预验收。需要本人用手机走页面、留实机记录并核查七列审计。 |
| 3.3 | 交接包模型 Key 为空。正式在线用例仍需有效 Key 和同实例夹具。 |
| 4.2、10.1、10.2 | 另一位组员执行并签名。可直接按本次记录复跑。10.1 需解决 Windows 普通门禁失败并重验。 |
| 5.1、9.5 | 需要实际交叉复核记录和三位使用者的试用反馈。 |
| 5.6、7.3 | 需要仓库管理员的分支保护配置，以及配置生效后测试 PR 被实际拦截的证据。 |
| 7.4 | 需要线上部署地址、实际实例和镜像仓库。上表已有本地容器版本证据。 |
| 8.5、8.6 | 需要确认真实接收通道及发送授权，再验证告警实际送达与恢复。 |

## 本机复跑入口

```powershell
uv sync --locked --project backend
npm.cmd --prefix frontend ci --no-audit --no-fund
npm.cmd install --prefix .review/lesson10-local/openspec --no-audit --no-fund --no-package-lock @fission-ai/openspec@1.13.1
$env:Path = (Resolve-Path .review/lesson10-local/openspec/node_modules/.bin).Path + [IO.Path]::PathSeparator + $env:Path
docker compose -f docker-compose.yml -f .review/lesson10-local/compose.local.yml config --quiet
docker compose -f docker-compose.yml -f .review/lesson10-local/compose.local.yml up -d --build --wait --wait-timeout 180
backend/.venv/Scripts/python.exe scripts/check.py --json .review/lesson10-local/check-repeat.json
backend/.venv/Scripts/python.exe scripts/security_precheck.py
```

本次使用 ZIP 中的演示数据库和 33 个上传文件。包内 237 个校验条目比对通过，另有两个控制文件。使用本地生成的 JWT、队列与 MCP 配置，真实模型 Key 留空。`.review/lesson10-local/compose.local.yml` 把入口限制为 `127.0.0.1:18090`，Compose 项目名为 `campusclaw-lesson10-local`。安全门禁通过导入原脚本并重定向输出目录运行了两次，原有报告和例外表均保留。直接运行命令会更新默认安全证据目录。
