# Scenario 检查对应表

本变更共 51 个 Scenario（新增 24、修改 Requirement 中 27）。API 检查使用临时库和假模型；继承的显示场景使用当前页面及合成数据重新核验，不引用搭建阶段的通过记录。所有脚本位置以下列行号为准。

| 能力 | Scenario | 检查位置或页面证据 |
| --- | --- | --- |
| quiz-homework-publication | 保留手工布置 | `apitest/check_quiz_homework.py:108`，`保留手工布置` |
| quiz-homework-publication | 两种作业同时展示 | `apitest/check_quiz_homework.py:117`，`两种作业同时展示` |
| quiz-homework-publication | 学科与班级筛选 | `apitest/check_quiz_homework.py:125`，`学科与班级筛选` |
| quiz-homework-publication | 学生响应不泄露评分依据 | `apitest/check_quiz_homework.py:118`，`学生响应不泄露评分依据` |
| quiz-homework-publication | 原题和原资料后续变化 | `apitest/check_quiz_homework.py:354`，`原题和原资料后续变化` |
| quiz-homework-publication | 提交命题作业 | `apitest/check_quiz_homework.py:203`，`提交命题作业` |
| quiz-homework-publication | 截止前重新提交 | `apitest/check_quiz_homework.py:205`，`截止前重新提交` |
| quiz-homework-publication | 逾期或关闭后提交 | `apitest/check_quiz_homework.py:360`，`逾期或关闭后提交` |
| quiz-homework-publication | 题面显示一致 | `apitest/check_quiz_homework.py:254`，`题面显示一致` |
| quiz-homework-publication | AI 使用发布时的评分依据 | `apitest/check_quiz_homework.py:221`，`AI 使用发布时的评分依据` |
| quiz-homework-publication | 非百分制原卷折算 | `apitest/check_quiz_homework.py:223`，`非百分制原卷折算` |
| quiz-homework-publication | 分数折算边界 | `apitest/check_quiz_homework.py:225`，`分数折算边界` |
| quiz-homework-publication | 教师直接评分并联动错题学情 | `apitest/check_quiz_homework.py:248`，`教师直接评分并联动错题学情` |
| quiz-homework-publication | 教师覆盖 AI 分且后续初批跳过 | `apitest/check_quiz_homework.py:235`，`教师覆盖 AI 分且后续初批跳过` |
| quiz-homework-publication | 初批失败仍可人工改分 | `apitest/check_quiz_homework.py:243`，`初批失败仍可人工改分` |
| quiz-homework-publication | 初批期间提交被更新或教师改分 | `apitest/check_quiz_homework.py:264`，`初批期间提交被更新或教师改分` |
| quiz-homework-publication | 未登录读取作业或配图 | `apitest/check_quiz_homework.py:131`，`未登录读取作业或配图` |
| quiz-homework-publication | 学生跨班读取或提交 | `apitest/check_quiz_homework.py:138`，`学生跨班读取或提交` |
| quiz-homework-publication | 教师班级或学科不符 | `apitest/check_quiz_homework.py:134`，`教师班级或学科不符` |
| quiz-homework-publication | 访问他人的提交或教师接口 | `apitest/check_quiz_homework.py:140`，`访问他人的提交或教师接口` |
| quiz-homework-publication | 配图异常 | `apitest/check_quiz_homework.py:145`，`配图异常` |
| quiz-homework-publication | 更新后旧资料仍可访问 | `apitest/check_quiz_homework.py:323`，`更新后旧资料仍可访问` |
| quiz-homework-publication | 老试卷主动重新发布 | `apitest/check_quiz_homework.py:334`，`老试卷主动重新发布` |
| quiz-homework-publication | 迁移重复执行 | `apitest/check_quiz_homework.py:397`，`迁移重复执行` |
| smart-question-generation | 发布到两个任教班级 | `apitest/check_quiz_homework.py:112`，`发布到两个任教班级` |
| smart-question-generation | 批次混入非任教班级 | `apitest/check_quiz_homework.py:155`，`发布参数边界或批次混入非任教班级` |
| smart-question-generation | 草稿试卷发布 | `apitest/check_quiz_homework.py:159`，`草稿试卷发布` |
| smart-question-generation | 发布身份边界 | `apitest/check_quiz_homework.py:142`，`发布身份边界` |
| smart-question-generation | 未确认核对或版本冲突 | `apitest/check_quiz_homework.py:178`，`未确认核对或版本冲突` |
| smart-question-generation | 重复发布 | `apitest/check_quiz_homework.py:161`，`重复发布` |
| smart-question-generation | 混合已有和新目标班级 | `apitest/check_quiz_homework.py:170`，`混合已有和新目标班级` |
| smart-question-generation | 重复发布更换截止时间或遇到已关闭作业 | `apitest/check_quiz_homework.py:165`，`重复发布更换截止时间或遇到已关闭作业` |
| smart-question-generation | 发布参数边界 | `apitest/check_quiz_homework.py:155`，`发布参数边界` |
| smart-question-generation | 原图校验或文件写入失败 | `apitest/check_quiz_homework.py:291`，`原图校验或文件写入失败` |
| smart-question-generation | 查看入库题目的复核历史 | `apitest/check_question_bank.py:686`，`查看入库题目的复核历史` |
| smart-question-generation | 删除候选题后追溯 | `apitest/check_question_bank.py:693`，`删除候选题后追溯` |
| smart-question-generation | 作业发布审计 | `apitest/check_quiz_homework.py:124`，`作业发布审计` |
| smart-question-generation | 多空位填空题显示 | 浏览器继承渲染验收（见 validation.md）；共用 MarkdownAnswer，当前隔离库重新检查 |
| smart-question-generation | 空位与公式下标共存 | 浏览器继承渲染验收（见 validation.md）；共用 MarkdownAnswer，当前隔离库重新检查 |
| smart-question-generation | 选项含公式 | 浏览器继承渲染验收（见 validation.md）；共用 MarkdownAnswer，当前隔离库重新检查 |
| smart-question-generation | 填空与解答题答案含公式 | 浏览器继承渲染验收（见 validation.md）；共用 MarkdownAnswer，当前隔离库重新检查 |
| smart-question-generation | 多空答案与选择判断答案 | 浏览器继承渲染验收（见 validation.md）；共用 MarkdownAnswer，当前隔离库重新检查 |
| smart-question-generation | 编辑答案时显示原文 | 浏览器继承渲染验收（见 validation.md）；共用 MarkdownAnswer，当前隔离库重新检查 |
| smart-question-generation | 解答题作答横线不变 | 浏览器继承渲染验收（见 validation.md）；共用 MarkdownAnswer，当前隔离库重新检查 |
| smart-question-generation | 学生端打开已发布试卷 | 浏览器继承渲染验收（见 validation.md）；共用 MarkdownAnswer，当前隔离库重新检查 |
| smart-question-generation | 代码中的下划线 | 浏览器继承渲染验收（见 validation.md）；共用 MarkdownAnswer，当前隔离库重新检查 |
| smart-question-generation | 选项各占一行 | `apitest/check_question_bank.py:427`，`学生卷选择题：A–D 每项一行且行尾硬换行`；浏览器 `studentAnswerLines` |
| smart-question-generation | 第 10 题以后 | `apitest/check_question_bank.py:430`，`学生卷第 10 题：选项缩进 4 格`；浏览器 `studentAnswerLines` |
| smart-question-generation | 选项含块级公式 | 浏览器继承渲染验收（见 validation.md）；共用 MarkdownAnswer，当前隔离库重新检查 |
| smart-question-generation | 学生端打开新发布的试卷 | 浏览器继承渲染验收（见 validation.md）；共用 MarkdownAnswer，当前隔离库重新检查 |
| smart-question-generation | 已发布资料不被改写 | `apitest/check_quiz_homework.py:329`，`已发布资料不被改写` |

页面证据在 validation.md 的浏览器验收表和本机 `.review/qa/browser-checks.json`。旧资料原图、正文、下载、标签、索引及发布记录由独立历史 Material 夹具检查，不用新作业代替旧资料职责。
