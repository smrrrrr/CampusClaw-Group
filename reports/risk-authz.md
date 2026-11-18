# 高风险检查：本次新增任务权限

## 当前复跑（2026-11-18）

| 项目 | 本次记录 |
| --- | --- |
| 手段 | 脚本 `backend/.venv/Scripts/python.exe apitest/probe_security_precheck.py --output .review/high-risk-probe.json`，以及 `apitest/check_async_grading.py` 的 E1。 |
| 对象 | 本班与跨班讲义下载、学生写工具，以及不同身份调用教师初批任务接口。 |
| 判据 | 本班下载 200；跨班下载 404、无正文且留审计。未登录访问任务为 401，学生误入教师接口为 403，他班或他科教师访问对应任务为 404。学生请求写工具不得执行或改变成绩。 |
| 结果 | [权限探针](security-evidence/20261118-high-risk-probe.json) 41/41、退出 0。本班和跨班下载均达到判据；学生写工具零执行且有拒绝记录。[离线初批检查](security-evidence/20261118-high-risk-async.json) 57/57、退出 0，E1 的 16 个拒绝用例及审计检查均通过。另复跑 `apitest/check_mcp_tools.py` 78/78，师生独立续期和单角色登出均通过。 |

## 历史记录

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
