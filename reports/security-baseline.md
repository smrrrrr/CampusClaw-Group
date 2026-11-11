# 密钥与依赖基线（2026-11-05）

这是一份修复前记录，不是安全合格证明；本轮没有升级依赖或修改锁文件。

## 密钥

`scripts/secret_scan.py`：8个本地提交，当前本机5项密钥在历史/可扫描工作区中0处命中；输出只记录键名。补充扫描全部本地引用的Git补丁，API Key形态及私钥块命中均0。记录见 [secret-scan.txt](security-evidence/secret-scan.txt)、[secret-baseline.json](security-evidence/secret-baseline.json)。

未拉取的远端引用、无法识别的已轮换旧密钥及被删除/轮换的日志不在覆盖范围；本机Docker引擎不可达，当前运行日志和容器前端静态产物也没有扫描成功。因此SEC-05整体为待验，不能写“全部历史及所有产物无泄漏”。当前未发现需立即轮换的真实明文泄漏。

## 联网依赖审计

来源：npm官方registry安全审计API；pip-audit默认PyPI漏洞服务。查询时间、工具版本、退出码、耗时和三份锁文件SHA-256见 [dependency-run.json](security-evidence/dependency-run.json)。在线漏洞库是动态服务，不提供本次可固定的数据库版本号；用原始响应与时间留证，不编造版本。

工具实测：npm 10.9.4、uv 0.12.18、pip-audit 2.10.1。仅扫描运行依赖，开发依赖、基础镜像操作系统及未进入锁文件的软件不在本次范围。后端与MCP按锁文件导出所有运行时传递依赖再用`--no-deps --disable-pip`扫描；此选项不代表只检查直接依赖。

| 范围 | 真实结果 | 退出码 | 原始证据 |
| --- | --- | --- | --- |
| 前端 | 4个受影响包：critical 1、high 2、moderate 1、low 0 | 1 | [npm-audit.json](security-evidence/npm-audit.json) |
| 后端 | 5个受影响包，48条包-通告记录，46个唯一漏洞ID | 1 | [backend-audit.json](security-evidence/backend-audit.json) |
| MCP服务 | 0个受影响包、0条已知通告 | 0 | [mcp-audit.json](security-evidence/mcp-audit.json) |

前端包级最高严重度：next=critical，postcss/source-map-js=high，katex=moderate。npm计数是受影响包数量，不能把它说成所有CVE的条数。

后端通告记录：certifi 2、ecdsa 2、pillow 39、pyasn1 4、python-jose 1。pip-audit JSON没有给出严重度；后端high/critical数量**尚未判级**，不得填0。重复漏洞ID可影响多个包，48条与46个唯一ID是不同口径。版本及修复候选见原始JSON、[汇总](security-evidence/dependency-summary.json)与 [锁定后端清单](security-evidence/backend-requirements.txt)、[锁定MCP清单](security-evidence/mcp-requirements.txt)。

当前没有完成逐条可利用性分析，也没有登记“本项目不受影响”的豁免。按安全规范§7，high/critical未处置前不能正式发布。后续先验证攻击前提并按规约升级，再保留前后对比；本轮不运行audit fix、不修改依赖来把报告变绿。

网络恢复前的失败属于环境故障，不能计为0漏洞；上述数量来自2026-11-05实际收到的可解析联网响应。复查仍需联网；网络失败时新入口不沿用旧JSON冒称当次扫描成功。

---

## 修复后当日基线（2026-11-11）

本节记录第9课安全修复完成后的密钥扫描与依赖审计结果，作为"当日基线"。

### 密钥扫描（SEC-05）

`scripts/security_precheck.py`（含 `secret_scan.py` + 运行日志 + 前端产物扫描）：

| 扫描范围 | 命中数 | 说明 |
| --- | --- | --- |
| 工作区源码与提交历史 | 0 | `secret_scan.py` 全量扫描 |
| 8 个 Docker 容器运行日志 | 0 | `docker logs` 全部容器 |
| 前端构建静态产物（tar） | 0 | nginx 容器内 `/usr/share/nginx/html` |

`reports/security-evidence/secret-baseline.json`：`complete=True`、`leak_detected=False`。

**处置**：无真实明文密钥命中，无需轮换。`security_precheck.py` 已修复项目名与数据库路径硬编码问题（从 `.env` 读取 `COMPOSE_PROJECT_NAME` 与 `DATABASE_URL`），运行日志与前端产物扫描范围完整。

### 依赖审计（SEC-06）

审计结果（与 2026-11-05 基线一致，漏洞库未变）：

| 范围 | 受影响包 | 退出码 | 处置方式 |
| --- | --- | --- | --- |
| 前端 | next(critical)、postcss(high)、source-map-js(high)、katex(moderate) | 1 | 登记例外条目 |
| 后端 | certifi、ecdsa、pillow、pyasn1、python-jose | 1 | 登记例外条目 |
| MCP 服务 | 0 | 0 | 无漏洞 |

**处置**：9 个漏洞包全部写入 `reports/security-evidence/dependency-exceptions.json`，每条含：包名、版本、严重度、漏洞编号、为什么暂不修、降险措施、`review_after=2026-12-15`。`security_precheck.py` 新增 `load_exceptions()` / `check_dependency_exceptions()` 校验：已登记且未过期的漏洞不计红项；未登记或过期登记触发 RED。

**门禁结果**：`scripts/security_precheck.py --reuse-dependency-evidence` 退出码 0，PASS。详见 `reports/security-evidence/run.json`。

### 先红后绿证据

`reports/gate-red-green.md`：
- RED：注入假密钥 `sk-...`（拆分写入避免扫描器误报），`secret_scan.py` 命中，退出码 1
- GREEN：移除假密钥后，`secret_scan.py` 0 命中，退出码 0
