# 高风险检查：本次新增任务权限

## 当前复核（2026-11-17）

| 四项 | 本次记录 |
| --- | --- |
| 手段 | `python apitest/probe_security_precheck.py --output .review/security-probe.json`；两班合成账号 HTTP 登录，临时库、假模型/MCP。另执行 `python apitest/check_async_grading.py` 核对任务权限。 |
| 对象 | 本班与他班讲义下载、跨班检索、学生写工具、未登录/学生/他班教师/他科教师的任务请求。 |
| 判据 | 有权下载必须 200 且正文正确；同一资源跨班下载必须 404、无他班正文且留审计；未登录任务 401、无权限任务 403；学生写工具不得执行或写分。 |
| 结果 | 安全探针 41/41、退出 0；SEC-02明确记录本班200和跨班404。异步检查57/57、退出0，含E1拒绝与审计。 |

证据：[project-evidence/security-probe.json](project-evidence/security-probe.json)、[project-evidence/async.json](project-evidence/async.json)、[时间与源码摘要](project-evidence/validation-runs.json)。准备见 [reproduce-checks.md](reproduce-checks.md)。

当前合同按端点区分：资料下载越权404，任务越权403，SSE拒绝检查事件和副作用。以下2026-11-05资料下载403是历史修复前结果；不能据此覆盖当前复验，也不能把所有越权接口统一描述为404。

下文为历史检查，保留原始日期与结果。

| 项目 | 内容 |
| --- | --- |
| 用什么手段查 | check_async_grading的E1接口反例，临时库与合成身份 |
| 查什么 | 初批创建、任务列表、详情、重试：未登录、学生、他班教师、他科教师 |
| 判据 | 未登录401，其余403；不返回私有输入、不改评分，403有审计 |
| 结果证据 | [offline-result.json](async-grading/offline-result.json) E1共16条拒绝检查及审计断言；原作业/配图隔离回归继续执行 |

本次沿用项目主规约“跨班403并审计”，不照抄报告示例的404。身份以当前数据库与会话为准，消息只有任务编号。此记录只证明所列场景，不代替后续完整安全专项、依赖全量审计或渗透测试。

## 2026-11-05安全专项追加（不覆盖前次记录）

本轮 [接口探针](security-evidence/api-probe.json) 使用临时两班资料及通过HTTP登录的合成师生。A学生下载A资料200；下载B资料403，无B班正文且403审计新增。两班同问只能引用本班资料；A独有知识在A有引用，在B返回空引用。课程要求跨班404，因此SEC-02课程口径为红项；项目403合同仍通过，未发现此路径的正文越权。

复现：`backend/.venv/Scripts/python.exe apitest/probe_security_precheck.py`。只在临时应用移除`_check_material_access`后，跨班下载变成200、B班正文可见，授权探针确实变红，见 [故意改坏证据](security-evidence/api-probe-mutation.json)；未修改磁盘源码。

学生合法请求体修改助手配置/Skill/MCP或直接写100分、发起AI初批，均403，所比较业务表状态一致。当前教学账号仅只读确认存在；本轮在线服务登录、全系统所有路由及全部Token撤销路径未覆盖。异步任务E1的16条拒绝也已在本次 [57条离线结果](security-evidence/async-offline.json) 中复跑。

---

## 第10课复跑（2026-11-14）

新增离线反例 `apitest/check_lesson10_skills.py`（10/10 通过）：

- `R1 本班没有的他班知识返回空引用`：跨班独有知识不产生引用。
- `R2 归属班级内可检索到`、`R3 本班知识正常命中`：正向对照，排除“检索永远为空”。
- `M4 模型不可用不伪造生成成功`：错题讲解降级不报成功。

同时 `make check` 中 `check_injection` 9/9、`check_baseline` 越权与 503 断言均通过，见 `reports/lesson-10/20261114T072100Z-apply/gates/check-final.txt`。

结论：项目 403/404 合同与跨班空引用一致；课程字面 404 口径仍按既有评审记录保留。
