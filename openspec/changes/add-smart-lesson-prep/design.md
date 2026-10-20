# 实现设计（2026-10-19）

## 状态与存储

LessonPlan 保存课题/班级/学科/本人、教学要求、教师正文、来源快照、两份学生稿、绑定定稿版本和 revision。draft → reviewed → final；编辑或章节重写回 draft；final 只读，开始新修订清空学生稿、保留旧定稿。LessonPlanVersion 只保存定稿不可变快照。LessonPublication 记录版本/类型/班级/Material 与正文 SHA，相同组合重复发布复用。SQL 条件更新 revision 避免长生成和多窗口覆盖。

## AI 与来源

复用 llm_service.stream_chat（180 秒生成总时限），教师稿 SSE delta，学生稿/局部重写 SSE progress，成功 done 才落库；无 Key 503，其他失败 error 帧，旧稿保留。上下文以完整 Markdown 小节组织，按课题/范围排序，16 段/45000 字符预算，每份资料至少一段。保留真实行号、摘录、文件指纹，图片以 sources/资料ID/原路径消除多文件冲突。生成前后核对来源文件，发布前核对所有图像。

引用编号检查只证明该片段被提供，语义是否直接支持论断由教师审阅；不承诺自动证明或伪造 Word 页码。真实学情未接入，仅使用教师填写信息。

## 学生稿与发布

定稿与所选上下文输入第二次 AI，输出学生可见教案/配套讲义 JSON。显式答案/教师提示、私有引用、链接/HTML、未知图片拒绝，vspace 转成 Markdown 作答横线。生成失败不覆盖旧稿。人工编辑后重新核对，发布从数据库已保存学生稿读取，批次所有任教班级先校验，再逐班独立存 Material/实际用图、索引正文。完整教师稿不进入学生索引；未使用解析图不复制。此检查不是答案/图片语义识别，仍须教师核对。

## 接口

GET/POST-generate /api/teacher/lesson-plans；GET/PUT/DELETE /{id}；POST /{id}/review、finalize、revise、regenerate-section、student-drafts、publish；PUT /{id}/student-drafts；GET /{id}/assets。请求 revision 用于所有写入；发布 kind 为 lesson 或 handout，带 class_ids 和 reviewed。详情包含定稿版本和发布记录。

## 前端与权限

/teacher/lesson-prep 独立页面，旧 view=lesson-prep 重定向。保存后可重开编辑，未保存修改/生成中离开浏览器提示。已有 React Markdown/KaTeX、鉴权图片及浏览器打印按钮复用。生成按钮提示将所选片段发送 DeepSeek。所有接口校验当前数据库教师、学科、任教班级及本人；学生只访问独立发布的普通班级资料。删除私人教案保留班级文稿，删除班级资料清理发布关系。

## 可选教研组共享

POST /api/teacher/lesson-plans/{id}/share-to-group 接受 revision，只有作者当前 final 可主动共享。LessonGroupPublication 记录私人原稿、定稿版本、组内 ResearchMaterial、原始出处 JSON。同一定稿唯一；共享时复制完整正文和实际使用配图并核对 SHA，建立独立 ResearchChunk，不触碰学生索引。新修订不影响共享快照；删除私人教案将组内关联 lesson_plan_id 置空并保留副本。

组内材料详情提供 kind/lesson_version/lesson_sources；GET /api/teacher/research-materials/{id}/bundle 导出教师图文包并校验指纹。组内界面筛选共享教案、保留原始摘录及图片、支持预选为新备课素材。旧 S编号仅在新 AI 上下文去除，原始摘录照存。共享完整教师稿不能使用旧 student-preview/publish 简单提取流程，必须走新备课学生稿核对发布。私人原教案权限不因共享而放开。
