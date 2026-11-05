# 安全自查记录（2026-11-05）

本轮结论：**发现红项，不能宣称安全验收全部通过或据此正式发布。** 现有功能没有修改，账号没有重置。自动回归通过与安全专项发现问题可以同时成立。

依据：用户提供的《第8课·安全检测清单》《小组项目下一阶段重点·学会审核AI写的代码》，以及项目八类工程规范。此次是实施代理自查，另一名组员评审尚未进行。

## 环境和证据范围

- Windows，本地工作区有既有未提交变更，不以HEAD代替工作区内容。HEAD、UTC起止时间及总退出码见 [run.json](security-evidence/run.json)。中文报告日期采用北京时间。
- 业务源码运行前后SHA-256相同，见 [source-before.json](security-evidence/source-before.json)、[source-after.json](security-evidence/source-after.json)。检查范围为后端Python、前端app/components/lib的代码文件；不等于验证所有配置从未变化。
- 教学数据库仅用SQLite `mode=ro`查询身份字段；未查询口令或哈希。四个旧账号仍存在，见 [账号只读记录](security-evidence/accounts-readonly.json)。本轮没有对真实服务执行登录请求，不能把存在等同于本次在线登录成功。
- 写接口全部在新临时SQLite和临时上传目录中执行，合成身份通过HTTP登录；假模型、假MCP，不访问真实DeepSeek、不消耗额度、不运行dev_seed。
- 本机Docker引擎不可达：运行容器日志、容器内前端产物和真实RabbitMQ本轮复跑均待验。历史真实代理结果只引用，不冒称本次结果。

## 演示身份

| 标识 | 角色及范围 | 本轮验证 |
| --- | --- | --- |
| TEA001 | 数学教师，任教101/102 | 真实库只读存在；临时同结构身份登录200 |
| TEA002 | 物理教师，任教101/102 | 同上 |
| 20260001 | A班101学生 | 同上 |
| 20260002 | B班102学生 | 同上 |

临时库使用专用合成测试口令，不代表真实账号的当前口令；报告不保存真实口令、令牌或哈希。

## 七项结果

逐条的期望、实际值和布尔判定见 [api-probe.json](security-evidence/api-probe.json)。本轮共26条观察（含4个登录前提）：24条通过、2条红项。依赖扫描与密钥范围另列，不能把26条观察当成26项独立课程要求。

| 编号 | 前置和操作 | 预期 | 实际及结论 | 证据 |
| --- | --- | --- | --- | --- |
| SEC-01 | 不携带Token/Cookie，GET下表7个合法受保护接口 | 全部401，无业务数据 | 7条均401，通过 | api-probe的SEC-01 |
| SEC-02 | A学生先下载A资料，再下载B资料；两班分别询问相同知识及A班独有知识 | 本班成功；跨班课程口径404；B询问A独有知识空引用 | 本班200；跨班403、无B正文且有审计；两班只返回本班引用，A独有知识在B为空。**隔离有效，课程404口径红项** | api-probe的SEC-02；[授权报告](risk-authz.md) |
| SEC-03 | 学生带合法请求体，修改助手提示词、创建/修改Skill、登记MCP服务器 | 403，相关业务行不变 | 4条均403；配置、Skill、MCP、提交、任务、错题状态快照不变，通过 | api-probe的SEC-03 |
| SEC-04 | 先由合法教师发布、学生提交，再以学生身份直接请求改100分和发起AI初批 | 拒绝，分数、任务及错题无变化 | 2条均403，状态快照一致，通过 | api-probe的SEC-04 |
| SEC-05 | 扫描工作区、本地全部引用历史、当前本机密钥；补查运行日志/前端产物 | 明文命中0，范围完整 | 8个本地提交与工作区未检出；**运行产物/日志未取得，整体待验** | [密钥基线](security-evidence/secret-baseline.json) |
| SEC-06 | 锁文件导出运行依赖，联网npm audit/pip-audit | high/critical清零或提供合格处置 | 前端4个受影响包：critical 1、high 2、moderate 1；后端5个包48条通告，尚未判级；MCP未检出。**红项** | [依赖基线](security-baseline.md) |
| SEC-07 | 学生实际命中合成Skill，假模型决定调用一次假MCP，再由教师查询日志 | 持久记录actor、skill、status、duration、usage | 实际调用1次且落库1行，actor/status正确；**持久日志缺skill标识、耗时、用量，红项**。SSE展示技能名不能代替可查询日志 | api-probe的SEC-07 |

项目现行规范明确跨班403并审计；课堂清单要求404。此处分别记录，不擅自修改规约或代码，也不把这项差异说成已发生跨班正文泄漏。SEC-04验证的是学生无权写分；教师人工改分本来就是合法业务，不要求教师必须经Skill改分。

## 受保护接口清单

以下7条均进行了SEC-01；其他路由不能由此推断已全部覆盖。

| 方法 | 路径 | 授权范围 |
| --- | --- | --- |
| GET | /api/materials | 本班学生/任教教师 |
| GET | /api/student/homeworks | 本班学生 |
| GET | /api/teacher/students?class_id=101 | 任教教师 |
| GET | /api/teacher/agent-config?class_id=101 | 本班本科教师 |
| GET | /api/teacher/skills?class_id=101 | 本班本科教师 |
| GET | /api/mcp/servers?class_id=101 | 教师本人资源 |
| GET | /api/mcp/tool-calls?class_id=101 | 教师本人资源 |

## 写接口清单（本轮路径，不是全系统写接口全集）

| 方法及路径 | 本轮用途 |
| --- | --- |
| POST /api/auth/login | 临时四身份登录 |
| PUT /api/teacher/agent-config | 学生非法改提示词被拒 |
| POST /api/teacher/skills | 教师创建合成Skill；学生创建被拒 |
| PUT /api/teacher/skills/{id} | 学生修改已有Skill被拒 |
| POST /api/mcp/servers | 教师登记合成工具；学生登记被拒 |
| POST /api/mcp/servers/{id}/connect | 假MCP工具发现 |
| POST /api/teacher/homeworks | 教师创建合成作业 |
| PUT /api/teacher/homeworks/{id}/publish | 教师发布 |
| POST /api/student/homeworks/{id}/submit | 学生提交，实际200 |
| PUT /api/teacher/submissions/{id}/grade | 学生非法改分被拒 |
| POST /api/teacher/homeworks/{id}/ai-grade | 学生越权被拒；合法教师202另由异步回归覆盖 |
| POST /api/student/conversations | 合成检索及Skill会话 |
| POST /api/student/conversations/{id}/chat | 实际检索和合成Skill调用 |

## 怎样重放

仓库根目录，Windows：

```powershell
backend\.venv\Scripts\python.exe scripts\security_precheck.py
backend\.venv\Scripts\python.exe scripts\check.py
```

macOS/Linux：`make check-security`、`make check`。准备条件见README。安全专项本次退出1，表示已成功记录红项；完整回归27组通过，见 [full-check.txt](security-evidence/full-check.txt)。不能因为前者红就删断言，也不能因为后者绿就忽略前者。

仅复现接口项可运行 `backend\.venv\Scripts\python.exe apitest\probe_security_precheck.py`，无须真实服务或模型。本轮临时应用的授权函数被刻意替换后，跨班下载确实变成200且拿到B班正文，新增探针变红；见 [故意改坏结果](security-evidence/api-probe-mutation.json)。正常结果中同项为403且不泄漏；磁盘业务源码没有修改。

并发/事务57条现有检查已本次复跑，见 [async-offline.json](security-evidence/async-offline.json)、[并发](risk-concurrency.md)、[事务](risk-transaction.md)。队列为内存替身；这份结果不是本轮真实RabbitMQ证据。

## 后续处理顺序（本轮未实施）

1. 根据原始漏洞通告核对实际攻击前提，提出依赖升级规约及回归方案，保留此红色基线。
2. 明确课程404与项目403合同如何统一；改动前先更新业务规约、审计和越权检查。
3. 为Skill持久日志补技能标识、耗时及用量的定义；工具无模型token用量时应明确“不适用”及原因，不能伪造数值。
4. Docker恢复后重跑运行日志、前端产物、真实队列及在线登录检查；至少另一名组员独立复现2项并填写 [review-01](review-01.md)。

没有真实签名和运行证据的项目仍待验；本轮不提交、不推送、不归档OpenSpec，不改变tasks勾选。
