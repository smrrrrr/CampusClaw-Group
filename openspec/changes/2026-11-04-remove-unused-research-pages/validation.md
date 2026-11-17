# 实施与验证记录

2026-11-04。先完成proposal/design/specs/tasks与实施前自查，strict通过后修改实现。用户明确要求去掉两项功能；没有执行opsx-apply/archive、没有修改tasks勾选。

## Scenario对应

| 场景 | 检查与证据 | 结果 |
| --- | --- | --- |
| R1 三项教研入口 | check_teacher_navigation：6页面×2身份、空班级；实际教师首页及备课侧栏 | 导航检查PASS；页面记录见reports |
| R2 旧链接落点 | check_teacher_navigation：2view×2workspace×2class；实际浏览器各访问一次旧链接；check_route_guard仍验证学生/未登录教师内容拒绝 | 自动检查PASS；跳转页面见reports |
| R3 其他导航 | check_teacher_navigation：9种其他view、现有入口点击、作业/助手/资料/班主任切班；原业务全量门禁 | PASS |
| 原全科/单科、资料、命题场景 | 原check_research_materials、check_question_bank、check_quiz_homework、check_route_guard及全量业务回归 | PASS，未声称重做所有页面端到端 |
| 原教研身份与角色矩阵 | 只去掉退役功能枚举，原后端权限不变，check_lessons_2_5等原授权检查继续运行 | PASS |

## 过程和真实边界

- 新检查先对旧实现运行，R1实际5项与期望3项不符，进程退出1；随后删菜单并归一旧view，35项通过。没有为了通过删断言。
- strict首次指出MODIFIED不能漏掉旧Scenario标题；保留原标题并更新退役行为。同步主规约后首次全量又发现旧待归档变更会漏掉新增R1–R3，已将新场景放到独立ADDED Requirement。没有修改旧变更、放宽校验或跳过它们。
- 首次全量输出还遇到Windows GBK无法打印失败符号；仅设置PYTHONIOENCODING=utf-8/PYTHONUTF8=1重新运行，门禁脚本未变。最终27组全部PASS。
- 不涉及后端/接口/表结构/提示词/模型参数/依赖/持久数据；接口失败矩阵、数据迁移与模型质量评测不适用。角色与资源授权保持，原回归继续验证。
- 当前改动叠加在已有未提交工作区，仅两个前端源码文件、本次检查和规约/证据属于这次范围，不将旧未提交修改混称为本次工作。
- 更新前保留旧前端镜像；仅更新本组8083前端及刷新nginx。实际服务健康和其他容器编号核对见deployment.json。没有演练回滚、没有正式发版、没有另一成员评审。

可重放命令、原始输出、页面截图及部署记录见[证据索引](../../../reports/remove-research-pages/README.md)。
