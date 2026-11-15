# 第10课场景逐条映射（候选）

- 生成时间（UTC）：2026-11-15T14:49:20.846060+00:00
- 主规约 Scenario 总数：**505**
- 断言名候选（重叠≥6）：**56**；别名候选（人工等价初稿）：**89**；弱候选（2–5）：**178**；仅文件级：**33**；无匹配断言：**149**；无检查文件：**0**

> 本表只给候选，不等于语义证明。人工复核须逐条确认断言强度、失败路径与边界；「别名候选」是按标题关键词建立的等价映射初稿，同样需要人工确认；「无匹配断言」与「无检查文件」是补检查的优先队列，不能当作已覆盖。

## 按能力统计

| 能力 | 总数 | 断言名候选 | 别名候选 | 弱候选 | 仅文件级 | 无匹配断言 | 无检查文件 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| agent-assistant | 47 | 2 | 7 | 14 | 4 | 20 | 0 |
| async-homework-grading | 20 | 0 | 0 | 19 | 0 | 1 | 0 |
| class-data-isolation | 34 | 12 | 15 | 6 | 1 | 0 | 0 |
| login-and-account-system | 40 | 4 | 18 | 17 | 1 | 0 | 0 |
| material-upload | 39 | 0 | 3 | 0 | 8 | 28 | 0 |
| mcp-tool-integration | 31 | 0 | 0 | 12 | 2 | 17 | 0 |
| quiz-homework-publication | 28 | 14 | 4 | 7 | 0 | 3 | 0 |
| rag-search | 32 | 1 | 28 | 2 | 1 | 0 | 0 |
| rbac-role-permissions | 56 | 11 | 10 | 35 | 0 | 0 | 0 |
| research-materials | 19 | 0 | 0 | 0 | 3 | 16 | 0 |
| runtime-reliability | 6 | 0 | 0 | 5 | 0 | 1 | 0 |
| smart-lesson-prep | 25 | 0 | 0 | 0 | 5 | 20 | 0 |
| smart-question-generation | 68 | 9 | 0 | 38 | 5 | 16 | 0 |
| student-workspace | 23 | 0 | 0 | 3 | 0 | 20 | 0 |
| teacher-identity-and-permissions | 14 | 1 | 2 | 10 | 1 | 0 | 0 |
| teacher-workspace | 23 | 2 | 2 | 10 | 2 | 7 | 0 |

## 需要补检查的场景（无匹配断言 / 无检查文件，按高风险能力优先）

| 优先级 | 类别 | 能力 | Requirement | Scenario | 判定 |
| --- | --- | --- | --- | --- | --- |
| P1 | 前端/展示 | async-homework-grading | 权限与页面范围 | E2 页面与刷新恢复 | 无匹配断言 |
| P1 | 前端/展示 | material-upload | 上传元数据与班级选择 | 多班级教师班级选择器展示所有任教班级 | 无匹配断言 |
| P1 | 前端/展示 | material-upload | 教师删除资料 | 前端仅教师展示删除入口 | 无匹配断言 |
| P1 | 前端/展示 | material-upload | 文件重名与异常处理 | 网络中断前端提供重试 | 无匹配断言 |
| P1 | 前端/展示 | mcp-tool-integration | 服务端调用循环与上限 | 命中工具并用到提示 | 无匹配断言 |
| P1 | 接口/逻辑 | agent-assistant | SSE 流式回答 | 多轮会话检索无命中时延续历史 | 无匹配断言 |
| P1 | 接口/逻辑 | agent-assistant | 「解题引导」技能开关 | 教师预览技能文案 | 无匹配断言 |
| P1 | 接口/逻辑 | agent-assistant | 使用已有公式依据时标注引用 | 历史未标注来源的回答 | 无匹配断言 |
| P1 | 接口/逻辑 | agent-assistant | 删除会话 | 删除会话并清理消息 | 无匹配断言 |
| P1 | 接口/逻辑 | agent-assistant | 助手技能与 MCP 配置界面 | 以技能文件注册技能 | 无匹配断言 |
| P1 | 接口/逻辑 | agent-assistant | 助手技能与 MCP 配置界面 | 打开教师助手配置 | 无匹配断言 |
| P1 | 接口/逻辑 | agent-assistant | 多轮会话与上下文延续 | 在会话内连续追问 | 无匹配断言 |
| P1 | 接口/逻辑 | agent-assistant | 多轮会话与上下文延续 | 新建与列出会话 | 无匹配断言 |
| P1 | 接口/逻辑 | agent-assistant | 学生按科目切换教师助手 | 没有该科配置 | 无匹配断言 |
| P1 | 接口/逻辑 | agent-assistant | 引导短追问重新检索依据 | 学生只回复数字或不会 | 无匹配断言 |
| P1 | 接口/逻辑 | agent-assistant | 引导短追问重新检索依据 | 换题或无题目锚点 | 无匹配断言 |
| P1 | 接口/逻辑 | agent-assistant | 按学习进度自适应引导 | 多次卡住与完成 | 无匹配断言 |
| P1 | 接口/逻辑 | agent-assistant | 按学习进度自适应引导 | 概念与学生公式作答 | 无匹配断言 |
| P1 | 接口/逻辑 | agent-assistant | 教师技能文件 | 技能文件格式错误 | 无匹配断言 |
| P1 | 接口/逻辑 | agent-assistant | 消息与会话持久化 | 仅带最近若干轮作为上下文 | 无匹配断言 |
| P1 | 接口/逻辑 | agent-assistant | 消息与会话持久化 | 历史公式代码与实时回答一致 | 无匹配断言 |
| P1 | 接口/逻辑 | agent-assistant | 消息与会话持久化 | 历史消息权限不变 | 无匹配断言 |
| P1 | 接口/逻辑 | agent-assistant | 消息与会话持久化 | 回显历史消息 | 无匹配断言 |
| P1 | 接口/逻辑 | agent-assistant | 独立的按班级助手配置界面 | 切班回读配置 | 无匹配断言 |
| P1 | 接口/逻辑 | agent-assistant | 自动检索班级学科参考资料 | 查看当前班级参考资料 | 无匹配断言 |
| P1 | 接口/逻辑 | material-upload | 上传元数据与班级选择 | 上传元数据完整记录 | 无匹配断言 |
| P1 | 接口/逻辑 | material-upload | 上传元数据与班级选择 | 教师选择任教班级上传成功 | 无匹配断言 |
| P1 | 接口/逻辑 | material-upload | 下载与预览 | 学生下载材料成功 | 无匹配断言 |
| P1 | 接口/逻辑 | material-upload | 下载与预览 | 学生在线预览 PDF 成功 | 无匹配断言 |
| P1 | 接口/逻辑 | material-upload | 下载与预览 | 学生在线预览图片成功 | 无匹配断言 |
| P1 | 接口/逻辑 | material-upload | 下载与预览 | 学生尝试下载其他班材料被拒 | 无匹配断言 |
| P1 | 接口/逻辑 | material-upload | 下载与预览 | 引用原文的文件版本已变化 | 无匹配断言 |
| P1 | 接口/逻辑 | material-upload | 下载与预览 | 教师下载任教班级材料成功 | 无匹配断言 |
| P1 | 接口/逻辑 | material-upload | 教师上传权限控制 | 教师上传资料成功 | 无匹配断言 |
| P1 | 接口/逻辑 | material-upload | 教师删除资料 | 删除后资料不可再访问 | 无匹配断言 |
| P1 | 接口/逻辑 | material-upload | 文件存储策略 | SQLite 仅存储元数据 | 无匹配断言 |
| P1 | 接口/逻辑 | material-upload | 文件存储策略 | 容器重启后文件不丢失 | 无匹配断言 |
| P1 | 接口/逻辑 | material-upload | 文件存储策略 | 文件存储在挂载目录 | 无匹配断言 |
| P1 | 接口/逻辑 | material-upload | 文件类型与大小限制 | 上传不允许的格式被拒 | 无匹配断言 |
| P1 | 接口/逻辑 | material-upload | 文件类型与大小限制 | 上传允许格式的文件成功 | 无匹配断言 |
| P1 | 接口/逻辑 | material-upload | 文件类型与大小限制 | 上传超大文件被拒 | 无匹配断言 |
| P1 | 接口/逻辑 | material-upload | 文件类型与大小限制 | 伪造扩展名被后端 MIME 校验拦截 | 无匹配断言 |
| P1 | 接口/逻辑 | material-upload | 文件重名与异常处理 | DB 写入失败时回滚删除物理文件 | 无匹配断言 |
| P1 | 接口/逻辑 | material-upload | 文件重名与异常处理 | 同名文件自动重命名 | 无匹配断言 |
| P1 | 接口/逻辑 | material-upload | 文件重名与异常处理 | 恶意文件头校验不通过被拒 | 无匹配断言 |
| P1 | 接口/逻辑 | material-upload | 材料数据隔离 | 学生尝试下载其他班材料被拒 | 无匹配断言 |
| P1 | 接口/逻辑 | material-upload | 材料数据隔离 | 学生查询本班材料成功 | 无匹配断言 |
| P1 | 接口/逻辑 | material-upload | 材料数据隔离 | 教师查询任教班级材料成功 | 无匹配断言 |
| P1 | 接口/逻辑 | material-upload | 知识库索引关联 | 上传成功后异步解析为纯文本 | 无匹配断言 |
| P1 | 接口/逻辑 | material-upload | 知识库索引关联 | 解析失败的材料保持未索引 | 无匹配断言 |
| P1 | 接口/逻辑 | mcp-tool-integration | MCP 与技能接口文档 | 默认关闭文档 | 无匹配断言 |
| P1 | 接口/逻辑 | mcp-tool-integration | MCP 工具调用审计 | 三种结果各有记录 | 无匹配断言 |
| P1 | 接口/逻辑 | mcp-tool-integration | MCP 工具调用审计 | 记录只看自己的范围 | 无匹配断言 |
| P1 | 接口/逻辑 | mcp-tool-integration | MCP 服务器登记与令牌边界 | 不在允许清单的地址 | 无匹配断言 |
| P1 | 接口/逻辑 | mcp-tool-integration | MCP 服务器登记与令牌边界 | 换机后令牌不可用 | 无匹配断言 |
| P1 | 接口/逻辑 | mcp-tool-integration | 候选工具与工具声明 | 只带技能内工具 | 无匹配断言 |
| P1 | 接口/逻辑 | mcp-tool-integration | 工具内容的信任边界 | 工具说明夹带指令 | 无匹配断言 |
| P1 | 接口/逻辑 | mcp-tool-integration | 工具内容的信任边界 | 工具返回夹带指令 | 无匹配断言 |
| P1 | 接口/逻辑 | mcp-tool-integration | 工具引用格式与保存期校验 | 引用写法不合规 | 无匹配断言 |
| P1 | 接口/逻辑 | mcp-tool-integration | 服务端调用循环与上限 | 两步任务连续两轮 | 无匹配断言 |
| P1 | 接口/逻辑 | mcp-tool-integration | 服务端调用循环与上限 | 工具超时 | 无匹配断言 |
| P1 | 接口/逻辑 | mcp-tool-integration | 服务端调用循环与上限 | 教师与错误归属执行对照 | 无匹配断言 |
| P1 | 接口/逻辑 | mcp-tool-integration | 服务端调用循环与上限 | 超过轮次上限 | 无匹配断言 |
| P1 | 接口/逻辑 | mcp-tool-integration | 自建 MCP 工具服务 | 令牌缺失或错误 | 无匹配断言 |
| P1 | 接口/逻辑 | mcp-tool-integration | 自建 MCP 工具服务 | 非法请求可读 | 无匹配断言 |
| P1 | 接口/逻辑 | mcp-tool-integration | 连接、发现与断开 | 连续连接两次 | 无匹配断言 |
| P1 | 接口/逻辑 | quiz-homework-publication | 作业终评与错题同步 | M1 首次满分不入错题 | 无匹配断言 |
| P1 | 接口/逻辑 | quiz-homework-publication | 作业终评与错题同步 | M2 低分改为及格或满分 | 无匹配断言 |
| P1 | 接口/逻辑 | quiz-homework-publication | 作业终评与错题同步 | M3 修复历史残留不改成绩 | 无匹配断言 |
| P1 | 接口/逻辑 | research-materials | 发布时生成知识点标签 | 标题未包含已知知识点 | 无匹配断言 |
| P1 | 接口/逻辑 | research-materials | 学生版按任教班级独立发布 | 发布学生讲义到两个任教班级 | 无匹配断言 |
| P1 | 接口/逻辑 | research-materials | 学生版按任教班级独立发布 | 越权班级混入发布批次 | 无匹配断言 |
| P1 | 接口/逻辑 | research-materials | 学生版题干提取与教师核对 | 现有结构化讲义生成学生版 | 无匹配断言 |
| P1 | 接口/逻辑 | research-materials | 学生版题干提取与教师核对 | 编辑后重新核对 | 无匹配断言 |
| P1 | 接口/逻辑 | research-materials | 学生讲义打印与另存 PDF | 学生保存图文讲义 | 无匹配断言 |
| P1 | 接口/逻辑 | research-materials | 学生讲义打印与另存 PDF | 教师打印未发布的学生预览 | 无匹配断言 |
| P1 | 接口/逻辑 | research-materials | 学生讲义打印与另存 PDF | 配图尚未就绪 | 无匹配断言 |
| P1 | 接口/逻辑 | research-materials | 教师资料先导入学科组 | 导入完善版图文资料包 | 无匹配断言 |
| P1 | 接口/逻辑 | research-materials | 班级配图与图文包受权访问 | 删除班级讲义 | 无匹配断言 |
| P1 | 接口/逻辑 | research-materials | 班级配图与图文包受权访问 | 学生预览和下载有图讲义 | 无匹配断言 |
| P1 | 接口/逻辑 | research-materials | 组内共享教案查阅与复用 | 下载教师图文包 | 无匹配断言 |
| P1 | 接口/逻辑 | research-materials | 组内共享教案查阅与复用 | 同科同事复用共享教案 | 无匹配断言 |
| P1 | 接口/逻辑 | research-materials | 组内共享教案查阅与复用 | 绕过学生稿制作 | 无匹配断言 |
| P1 | 接口/逻辑 | research-materials | 组内教师共享与学生隔离 | 同科同事选用素材 | 无匹配断言 |
| P1 | 接口/逻辑 | research-materials | 组内教师共享与学生隔离 | 学生直接猜测教师原稿地址 | 无匹配断言 |
| P1 | 接口/逻辑 | runtime-reliability | 存储修复保留业务数据 | 会话接口磁盘 I/O 故障修复 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-lesson-prep | 两种学生文稿分班发布 | 发布批次混入其他班 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-lesson-prep | 两种学生文稿分班发布 | 教案和讲义均发布给学生 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-lesson-prep | 中文空格图片路径兼容 | 原题图的中文目录含空格 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-lesson-prep | 中文空格图片路径兼容 | 生成与发布图文包 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-lesson-prep | 从学科组教师资料发起备课 | 尚未提供学情 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-lesson-prep | 从定稿生成两种学生稿 | 学生稿生成未通过检查 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-lesson-prep | 完整片段与出处核对 | 多份资料均被选入 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-lesson-prep | 完整片段与出处核对 | 核对例题出处 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-lesson-prep | 定稿快照与并发保护 | 旧窗口写入 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-lesson-prep | 定稿快照与并发保护 | 第二次定稿 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-lesson-prep | 教师定稿可选共享到教研组 | 主动共享完整教师定稿 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-lesson-prep | 教师定稿可选共享到教研组 | 删除私人原教案 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-lesson-prep | 教师定稿可选共享到教研组 | 教师选择保留私有 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-lesson-prep | 教师定稿可选共享到教研组 | 重复发布或后续修改 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-lesson-prep | 教案隔离删除与审计 | 删除私人教案 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-lesson-prep | 教案隔离删除与审计 | 同学科同事访问私人教案 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-lesson-prep | 流式生成与失败处理 | AI 完成教师草案 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-lesson-prep | 流式生成与失败处理 | 生成中断或无 Key | 无匹配断言 |
| P1 | 接口/逻辑 | smart-lesson-prep | 编辑审阅与章节重写 | 审阅后再改正文 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-lesson-prep | 编辑审阅与章节重写 | 重写教学过程 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-question-generation | 公式结构校验 | 转义括号与环境不被误判 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-question-generation | 公式结构校验 | 转义的美元符号 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-question-generation | 公式结构校验 | 选项缺右括号 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-question-generation | 学生卷选项排版 | 选项各占一行 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-question-generation | 学生卷选项排版 | 选项含块级公式 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-question-generation | 学科题库 | 下架后组卷 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-question-generation | 按配比组卷 | 手工替换为下架题 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-question-generation | 流式进度与失败处理 | 生成中模型超时 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-question-generation | 结构化输出与逐题校验 | 模型声明无依据的空位 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-question-generation | 结构化输出与逐题校验 | 题干泄露答案 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-question-generation | 试卷定稿与分班发布 | 发布参数边界 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-question-generation | 试卷定稿与分班发布 | 发布身份边界 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-question-generation | 试卷定稿与分班发布 | 混合已有和新目标班级 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-question-generation | 题目内容显示 | 代码中的下划线 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-question-generation | 题目内容显示 | 空位与公式下标共存 | 无匹配断言 |
| P1 | 接口/逻辑 | smart-question-generation | 题目内容显示 | 选项含公式 | 无匹配断言 |
| P1 | 接口/逻辑 | student-workspace | 作业界面先展示演示结果 | 浏览演示作业结果 | 无匹配断言 |
| P1 | 接口/逻辑 | student-workspace | 助手对话保留真实会话能力 | 从助手页连续追问 | 无匹配断言 |
| P1 | 接口/逻辑 | student-workspace | 助手对话保留真实会话能力 | 查看回答来源 | 无匹配断言 |
| P1 | 接口/逻辑 | student-workspace | 学情分析演示界面 | 浏览学习画像演示 | 无匹配断言 |
| P1 | 接口/逻辑 | student-workspace | 学生作业历史持续可查 | H1 提交后进入历史并可刷新 | 无匹配断言 |
| P1 | 接口/逻辑 | student-workspace | 学生作业历史持续可查 | H3 历史读取隔离与失败 | 无匹配断言 |
| P1 | 接口/逻辑 | student-workspace | 学生作业历史持续可查 | H4 空历史与时间边界 | 无匹配断言 |
| P1 | 接口/逻辑 | student-workspace | 学生导航与路由 | 无效视图回退 | 无匹配断言 |
| P1 | 接口/逻辑 | student-workspace | 学生导航与路由 | 资料页返回其他模块 | 无匹配断言 |
| P1 | 接口/逻辑 | student-workspace | 学生导航与路由 | 首页进入助手对话 | 无匹配断言 |
| P1 | 接口/逻辑 | student-workspace | 学生本地搜索与提问历史 | 助手历史不自动发送 | 无匹配断言 |
| P1 | 接口/逻辑 | student-workspace | 学生本地搜索与提问历史 | 搜索后刷新与再次使用 | 无匹配断言 |
| P1 | 接口/逻辑 | student-workspace | 学生本地搜索与提问历史 | 科目和账号隔离 | 无匹配断言 |
| P1 | 接口/逻辑 | student-workspace | 本班讲义列表与检索界面 | 学生搜索本班讲义 | 无匹配断言 |
| P1 | 接口/逻辑 | student-workspace | 本班讲义列表与检索界面 | 学科标签过滤资料卡 | 无匹配断言 |
| P1 | 接口/逻辑 | student-workspace | 本班讲义列表与检索界面 | 预览和下载实际资料 | 无匹配断言 |
| P1 | 接口/逻辑 | student-workspace | 本班首页概览 | 浏览首页概览 | 无匹配断言 |
| P1 | 接口/逻辑 | student-workspace | 讲义页科目切换布局稳定 | 从有资料切到空科目 | 无匹配断言 |
| P1 | 接口/逻辑 | student-workspace | 讲义页科目切换布局稳定 | 搜索加载与恢复 | 无匹配断言 |
| P1 | 接口/逻辑 | student-workspace | 错题界面及助手跳转 | 由错题进入助手 | 无匹配断言 |
| P1 | 接口/逻辑 | teacher-workspace | 任课管理的单科资料列表 | 发布与查看入口分开 | 无匹配断言 |
| P1 | 接口/逻辑 | teacher-workspace | 全科总览与单科教学入口区分 | 在教研组内选择教师版发布学生稿 | 无匹配断言 |
| P1 | 接口/逻辑 | teacher-workspace | 全科总览与单科教学入口区分 | 打开未接入的学情或教研模块 | 无匹配断言 |
| P1 | 接口/逻辑 | teacher-workspace | 助手配置独立入口及菜单顺序 | 检查系统菜单顺序 | 无匹配断言 |
| P1 | 接口/逻辑 | teacher-workspace | 教师共用工作空间导航 | 教师进入智能命题页 | 无匹配断言 |
| P1 | 接口/逻辑 | teacher-workspace | 教师教研占位入口移除 | R2 旧教研链接有明确落点 | 无匹配断言 |
| P1 | 接口/逻辑 | teacher-workspace | 教师页移除快捷切换账号 | 教师检查顶栏 | 无匹配断言 |

## 逐条候选

| 能力 | Requirement | Scenario | 判定 | 候选检查 | 候选断言 | 重叠 |
| --- | --- | --- | --- | --- | --- | --- |
| agent-assistant | SSE 流式回答 | DeepSeek 失败时降级为检索段落 | 别名候选 | check_lessons_2_5 | agent.failure_fallback | 2 |
| agent-assistant | SSE 流式回答 | 多轮会话检索无命中时延续历史 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| agent-assistant | SSE 流式回答 | 多轮调用只推送一次 meta | 断言名候选 | check_mcp_tools | 两轮调用只推送一次 meta 且为首帧 | 11 |
| agent-assistant | SSE 流式回答 | 工具事件先于正文 | 弱候选 | check_mcp_tools | meta 事件先于 delta | 3 |
| agent-assistant | SSE 流式回答 | 断开后的引用显示被拒 | 弱候选 | check_mcp_tools | 断开后引用记 denied | 3 |
| agent-assistant | SSE 流式回答 | 流式结束写回会话 | 别名候选 | check_lessons_2_5 | agent.sse_transport_mock_llm | 1 |
| agent-assistant | SSE 流式回答 | 流式逐字输出 | 别名候选 | check_lessons_2_5 | agent.sse_transport_mock_llm | 1 |
| agent-assistant | 「解题引导」技能开关 | 关闭解题引导技能 | 仅文件级 | check_lesson10_skills | （未定位到具体断言） | 4 |
| agent-assistant | 「解题引导」技能开关 | 开启解题引导技能 | 弱候选 | check_lesson10_skills | T1 正常：开启引导时使用苏格拉底框架 | 2 |
| agent-assistant | 「解题引导」技能开关 | 教师预览技能文案 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| agent-assistant | 使用已有公式依据时标注引用 | 历史未标注来源的回答 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| agent-assistant | 使用已有公式依据时标注引用 | 引导求两向量夹角余弦 | 仅文件级 | check_mcp_tools | （未定位到具体断言） | 5 |
| agent-assistant | 兼容既有约束 | 教师配置与班级检索共享隔离 | 弱候选 | check_lesson10_skills | R2 正常：在归属班级内可检索到 | 2 |
| agent-assistant | 兼容既有约束 | 未分配班级学生被拒 | 别名候选 | check_lessons_2_5 | agent.unassigned_student_denied | 2 |
| agent-assistant | 兼容既有约束 | 追问计入每日限次 | 别名候选 | check_lessons_2_5 | agent.spec_40_question_limit | 2 |
| agent-assistant | 删除会话 | 删除会话并清理消息 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| agent-assistant | 助手技能与 MCP 配置界面 | 以技能文件注册技能 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| agent-assistant | 助手技能与 MCP 配置界面 | 在配置页登记并连接 MCP 服务器 | 弱候选 | check_mcp_tools | 登记服务器 201 | 3 |
| agent-assistant | 助手技能与 MCP 配置界面 | 打开教师助手配置 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| agent-assistant | 助手技能与 MCP 配置界面 | 调整预览技能不产生真实批改配置 | 弱候选 | check_mcp_tools | 未命中技能不发 meta | 2 |
| agent-assistant | 多轮会话与上下文延续 | 在会话内连续追问 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| agent-assistant | 多轮会话与上下文延续 | 新建与列出会话 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| agent-assistant | 多轮会话与上下文延续 | 访问他人会话被拒绝 | 仅文件级 | check_mcp_tools | （未定位到具体断言） | 4 |
| agent-assistant | 学生按科目切换教师助手 | 切换科目时隔离异步状态 | 别名候选 | check_lessons_2_5 | agent.physics_save_does_not_overwrite_math | 1 |
| agent-assistant | 学生按科目切换教师助手 | 同科教师不覆盖彼此配置 | 别名候选 | check_lessons_2_5 | agent.same_subject_teacher_configs_independent | 3 |
| agent-assistant | 学生按科目切换教师助手 | 数学与物理配置各自生效 | 仅文件级 | check_lessons_2_5 | （未定位到具体断言） | 5 |
| agent-assistant | 学生按科目切换教师助手 | 没有该科配置 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| agent-assistant | 学生提问的技能路由 | 命中技能 | 弱候选 | check_mcp_tools | 未命中技能不发 meta | 3 |
| agent-assistant | 学生提问的技能路由 | 未命中或技能停用 | 弱候选 | check_mcp_tools | 未命中技能不发 meta | 3 |
| agent-assistant | 引导短追问重新检索依据 | 学生只回复数字或不会 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| agent-assistant | 引导短追问重新检索依据 | 换题或无题目锚点 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| agent-assistant | 按学习进度自适应引导 | 多次卡住与完成 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| agent-assistant | 按学习进度自适应引导 | 概念与学生公式作答 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| agent-assistant | 教师技能文件 | 他人技能不可见 | 弱候选 | check_mcp_tools | 同伴删他人技能 404 | 3 |
| agent-assistant | 教师技能文件 | 保存绑定 MCP 工具的技能 | 弱候选 | check_mcp_tools | 未配置 MCP_TOKEN_KEY 拒绝保存令牌 | 3 |
| agent-assistant | 教师技能文件 | 技能文件格式错误 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| agent-assistant | 教师的可配置提示词 | 教师保存某班自定义提示词 | 断言名候选 | check_lesson10_skills | T3 边界：未开启引导时保留教师自定义提示词 | 6 |
| agent-assistant | 教师的可配置提示词 | 留空回退默认提示词 | 弱候选 | check_lesson10_skills | T3 边界：未开启引导时保留教师自定义提示词 | 2 |
| agent-assistant | 教师的可配置提示词 | 配置非任教班级被拒绝 | 弱候选 | check_mcp_tools | 非任教班级 403 | 4 |
| agent-assistant | 消息与会话持久化 | 仅带最近若干轮作为上下文 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| agent-assistant | 消息与会话持久化 | 历史公式代码与实时回答一致 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| agent-assistant | 消息与会话持久化 | 历史消息权限不变 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| agent-assistant | 消息与会话持久化 | 回显历史消息 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| agent-assistant | 独立的按班级助手配置界面 | 保存提示词及解题引导 | 弱候选 | check_lesson10_skills | T3 边界：未开启引导时保留教师自定义提示词 | 3 |
| agent-assistant | 独立的按班级助手配置界面 | 切班回读配置 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| agent-assistant | 自动检索班级学科参考资料 | 尚无任教班级 | 弱候选 | check_mcp_tools | 非任教班级 403 | 3 |
| agent-assistant | 自动检索班级学科参考资料 | 查看当前班级参考资料 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| async-homework-grading | 可复现与证据归档 | F1 一键复现和迁移保留 | 弱候选 | check_async_grading | F1 边界：重复迁移不改变旧数据 | 2 |
| async-homework-grading | 可靠投递及进程恢复 | B1 消费者停止再启动 | 弱候选 | check_async_grading | B1 正常：队列有消息、消费者未运行时pending | 3 |
| async-homework-grading | 可靠投递及进程恢复 | B2 队列故障后补投 | 弱候选 | check_async_grading | B2 正常：恢复后补投并可消费 | 3 |
| async-homework-grading | 可靠投递及进程恢复 | B3 事务中途失败 | 弱候选 | check_async_grading | B3 失败：数据库错误503且不泄露内部信息 | 2 |
| async-homework-grading | 可靠投递及进程恢复 | B4 执行中杀进程与旧租约 | 弱候选 | check_async_grading | B4 失败：旧租约不能覆盖 | 3 |
| async-homework-grading | 幂等与原评分边界 | C1 并发与重复投递 | 弱候选 | check_async_grading | C1 边界：20并发数据库唯一幂等 | 2 |
| async-homework-grading | 幂等与原评分边界 | C2 重交及教师终评竞态 | 弱候选 | check_quiz_homework | H/初批期间提交被更新或教师改分：教师终评 | 3 |
| async-homework-grading | 快速提交与只读查询 | A1 正常提交不等待 | 弱候选 | check_async_grading | A1 正常：20次202无评分且P95小于200ms假执行，无请求内模型调用 | 3 |
| async-homework-grading | 快速提交与只读查询 | A2 查询无副作用与空批次 | 弱候选 | check_async_grading | A2 边界：无提交空批次 | 3 |
| async-homework-grading | 快速提交与只读查询 | A3 参数与资源失败 | 弱候选 | check_async_grading | A3 失败：非法任务编号422 | 2 |
| async-homework-grading | 有限重试与可处置死信 | D1 失败退避与死信 | 弱候选 | check_async_grading | D1 失败：死信投递失败不假确认 | 4 |
| async-homework-grading | 有限重试与可处置死信 | D2 手动重试与合法模型恢复 | 弱候选 | check_async_grading | D2 正常：授权手动重试202 | 4 |
| async-homework-grading | 权限与页面范围 | E1 未登录及越权 | 弱候选 | check_quiz_homework | H/未登录读取作业或配图： | 2 |
| async-homework-grading | 权限与页面范围 | E2 页面与刷新恢复 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| async-homework-grading | 权限与页面范围 | E3 初批反馈在当前作业卡片可见 | 弱候选 | check_homework | S1 正常：草稿作业学生不可见 | 2 |
| async-homework-grading | 权限与页面范围 | E4 查看提交同步人数 | 弱候选 | check_homework | S6 失败：学生查看他人提交 → 404 | 2 |
| async-homework-grading | 确认后限次投递与执行计数 | Q1 暂停消费者不积攒副本 | 弱候选 | check_async_grading | Q1 边界：确认后跨越30分钟不积攒副本 | 5 |
| async-homework-grading | 确认后限次投递与执行计数 | Q2 未确认及过期运行恢复 | 弱候选 | check_async_grading | Q2 边界：同一过期租约只确认一条恢复消息 | 4 |
| async-homework-grading | 确认后限次投递与执行计数 | Q3 管理员明确恢复丢失消息 | 弱候选 | check_async_grading | Q2 边界：同一过期租约只确认一条恢复消息 | 2 |
| async-homework-grading | 确认后限次投递与执行计数 | Q4 界面不把消息数当批改数 | 弱候选 | check_homework | S4 正常：异步初批202且消费后批改数正确 | 2 |
| class-data-isolation | SQLite 存储兼容与数据库就绪检查 | Windows Docker 共享目录读写 | 弱候选 | check_lessons_2_5 | citations.original_version_download | 4 |
| class-data-isolation | SQLite 存储兼容与数据库就绪检查 | 原生磁盘保留 WAL | 别名候选 | check_lesson10_p0_scenarios | P0 接口：SQLite 代码默认日志模式为 WAL，且支持环境变量覆盖 | 1 |
| class-data-isolation | SQLite 存储兼容与数据库就绪检查 | 数据库暂不可用 | 弱候选 | check_baseline | R1 失败：数据库异常 → 503 与通用提示 | 2 |
| class-data-isolation | 一人一号班级上下文 | 学生登录建立本人班级上下文 | 别名候选 | check_lessons_2_5 | auth.refresh_restores_full_user | 3 |
| class-data-isolation | 一人一号班级上下文 | 登出后重新登录使用新的班级范围 | 别名候选 | check_lessons_2_5 | auth.refresh_restores_full_user | 2 |
| class-data-isolation | 前端班级数据渲染控制 | 任课切班不改变带班上下文 | 别名候选 | check_lesson10_p0_scenarios | P0 接口：任教班级与带班班级均由服务端令牌/数据库派生（不采信客户端参数） | 1 |
| class-data-isolation | 前端班级数据渲染控制 | 学生资料请求使用本人班级 | 弱候选 | check_baseline | R2 失败：学生调用教师接口 → 403 且带请求标识 | 2 |
| class-data-isolation | 前端班级数据渲染控制 | 篡改 class_id 不能扩权 | 断言名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation | 6 |
| class-data-isolation | 后端数据查询强制隔离 | 后端不信任请求参数中的 class_id | 断言名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation | 6 |
| class-data-isolation | 后端数据查询强制隔离 | 后端查询强制带 class_id 过滤 | 断言名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation | 6 |
| class-data-isolation | 后端数据查询强制隔离 | 请求参数 class_id 与 JWT 不符被拒 | 断言名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation | 6 |
| class-data-isolation | 学生班级数据范围控制 | 学生尝试查看其他班级资料被拒 | 别名候选 | check_lessons_2_5 | materials.subject_list_cross_class_denied | 4 |
| class-data-isolation | 学生班级数据范围控制 | 学生提交作业关联到本班 | 别名候选 | check_homework | S3 正常：学生提交成功 | 3 |
| class-data-isolation | 学生班级数据范围控制 | 学生查看本班资料成功 | 弱候选 | check_injection | 上传含 <script> 描述的材料成功 | 2 |
| class-data-isolation | 教师班级数据范围控制 | 教师查看任教班级资料成功 | 弱候选 | check_lesson10_p0_scenarios | P0 前端：教师未分配任教班级时存在空状态提示 | 4 |
| class-data-isolation | 教师班级数据范围控制 | 教师查看非任教班级资料被拒 | 别名候选 | check_lessons_2_5 | auth.teacher_cross_class_denied | 3 |
| class-data-isolation | 教师班级数据范围控制 | 教师跨班布置作业被拒 | 别名候选 | check_homework | S1 失败：非任教班级布置 → 403 | 3 |
| class-data-isolation | 无班级分配边界处理 | 学生未分配班级前端展示空状态 | 别名候选 | check_lessons_2_5 | agent.unassigned_student_denied | 2 |
| class-data-isolation | 无班级分配边界处理 | 学生未分配班级后端拒绝查询 | 别名候选 | check_lessons_2_5 | agent.unassigned_student_denied | 2 |
| class-data-isolation | 无班级分配边界处理 | 教师未分配任教班级前端展示空状态 | 别名候选 | check_lesson10_p0_scenarios | P0 前端：教师未分配任教班级时存在空状态提示 | 1 |
| class-data-isolation | 无班级分配边界处理 | 教师未分配任教班级后端拒绝查询 | 断言名候选 | check_lesson10_p0_scenarios | P0 前端：教师未分配任教班级时存在空状态提示 | 8 |
| class-data-isolation | 班级数据隔离模型与字段规范 | AI 提问记录表按 class_id 隔离 | 断言名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation | 6 |
| class-data-isolation | 班级数据隔离模型与字段规范 | 作业布置表按 class_id 隔离 | 断言名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation | 6 |
| class-data-isolation | 班级数据隔离模型与字段规范 | 作业提交记录表按 class_id 隔离 | 断言名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation | 6 |
| class-data-isolation | 班级数据隔离模型与字段规范 | 班级资料表按 class_id 隔离 | 断言名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation | 6 |
| class-data-isolation | 班级数据隔离模型与字段规范 | 错题本表按 class_id 隔离 | 断言名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation | 6 |
| class-data-isolation | 跨班访问拦截与审计日志 | 教师篡改 class_id 跨班访问被拦截 | 断言名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation | 6 |
| class-data-isolation | 跨班访问拦截与审计日志 | 篡改 API Payload 中 class_id 被拦截 | 断言名候选 | check_lessons_2_5 | materials.cross_class_download_denied | 8 |
| class-data-isolation | 跨班访问拦截与审计日志 | 篡改 URL 参数跨班访问被拦截 | 仅文件级 | check_baseline | （未定位到具体断言） | 5 |
| class-data-isolation | 跨班访问拦截与审计日志 | 跨班访问审计日志记录完整 | 别名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation | 2 |
| class-data-isolation | 隔离数据范围界定 | 学校级公共资源不隔离 | 别名候选 | check_lesson10_p0_scenarios | P0 接口：学科组素材按学科归属、不绑定班级 | 1 |
| class-data-isolation | 隔离数据范围界定 | 班级资料严格隔离 | 别名候选 | check_lessons_2_5 | materials.cross_class_download_denied | 2 |
| class-data-isolation | 隔离数据范围界定 | 用户账号基础信息不隔离 | 弱候选 | check_baseline | R1 失败：伪造令牌仍 200，且不含用户信息 | 2 |
| class-data-isolation | 隔离数据范围界定 | 系统公告不隔离 | 别名候选 | check_lesson10_p0_scenarios | P0 接口：不存在按班级隔离的系统公告模型（特性未实现，无误隔离） | 1 |
| login-and-account-system | JWT 会话管理 | Access Token 过期自动刷新 | 弱候选 | check_baseline | R3 正常：44 个字符（openssl rand -base64 32）可启动 | 2 |
| login-and-account-system | JWT 会话管理 | JWT Payload 包含必要字段 | 弱候选 | check_baseline | R3 失败：缺少 JWT_SECRET_KEY → 非零退出并提示键名 | 2 |
| login-and-account-system | JWT 会话管理 | Refresh Token 过期需重新登录 | 弱候选 | check_baseline | R1 正常：三项依赖为 ok/ok/configured | 2 |
| login-and-account-system | JWT 会话管理 | 登录成功签发双 Token | 别名候选 | check_lessons_2_5 | auth.login.<角色>（动态断言名） | 2 |
| login-and-account-system | 初始密码规则 | 学生账号初始密码生成 | 断言名候选 | check_lesson10_scenarios | 学生账号初始密码：前缀为学校缩写且结尾为学号末六位 | 7 |
| login-and-account-system | 初始密码规则 | 教师账号初始密码生成 | 断言名候选 | check_lesson10_scenarios | 教师账号初始密码：前缀为学校缩写且结尾为工号末六位 | 7 |
| login-and-account-system | 刷新页面恢复完整会话 | 刷新失败回登录 | 弱候选 | check_baseline | R2 失败：未登录 → 401 且带请求标识 | 2 |
| login-and-account-system | 刷新页面恢复完整会话 | 学生刷新后仍指向本人 | 别名候选 | check_lessons_2_5 | auth.refresh_restores_full_user | 1 |
| login-and-account-system | 刷新页面恢复完整会话 | 教师刷新后保留页面 | 弱候选 | check_route_guard | 双标签提示变化后的单科切班：教师页面不被学生提示拒绝 | 2 |
| login-and-account-system | 多端在线与登出 | 同一账号多端登录都成功 | 别名候选 | check_lessons_2_5 | auth.login.<角色>（动态断言名） | 2 |
| login-and-account-system | 多端在线与登出 | 登出清除所有 Token 和状态 | 仅文件级 | check_route_guard | （未定位到具体断言） | 4 |
| login-and-account-system | 学生 CSV 导入的双向班级权限 | 任教范围内创建或更新 | 别名候选 | check_lessons_2_5 | auth.csv_assigned_class_allowed | 1 |
| login-and-account-system | 学生 CSV 导入的双向班级权限 | 修改非任教班级学生被拒绝 | 弱候选 | check_lesson10_p0_scenarios | P0 前端：教师未分配任教班级时存在空状态提示 | 3 |
| login-and-account-system | 学生 CSV 导入的双向班级权限 | 合法行之后出现越权行 | 别名候选 | check_lessons_2_5 | auth.csv_forbidden_batch_rolled_back | 2 |
| login-and-account-system | 学生 CSV 导入的双向班级权限 | 导入非任教目标班级被拒绝 | 弱候选 | check_baseline | R3 边界：31 个字符被拒绝 | 2 |
| login-and-account-system | 密码安全策略与存储 | 不符合策略的密码被拒绝 | 别名候选 | check_lessons_2_5 | auth.weak_password_denied | 3 |
| login-and-account-system | 密码安全策略与存储 | 密码长度不足被拒绝 | 别名候选 | check_lessons_2_5 | auth.weak_password_denied | 3 |
| login-and-account-system | 密码安全策略与存储 | 符合策略的密码被接受 | 别名候选 | check_lessons_2_5 | auth.change_password | 1 |
| login-and-account-system | 密码登录 | 学生用学号和密码登录成功 | 别名候选 | check_lessons_2_5 | auth.login.<角色>（动态断言名） | 2 |
| login-and-account-system | 密码登录 | 密码错误登录失败 | 弱候选 | check_baseline | R2 失败：未登录 → 401 且带请求标识 | 2 |
| login-and-account-system | 密码登录 | 教师用工号和密码登录成功 | 别名候选 | check_lessons_2_5 | auth.login.<角色>（动态断言名） | 2 |
| login-and-account-system | 密码登录 | 账号不存在登录失败 | 弱候选 | check_baseline | R2 失败：不存在的接口 → 404 且带请求标识 | 3 |
| login-and-account-system | 密码登录失败锁定 | 密码登录成功清零失败计数 | 别名候选 | check_lessons_2_5 | auth.login.<角色>（动态断言名） | 2 |
| login-and-account-system | 密码登录失败锁定 | 连续5次密码失败后锁定 | 别名候选 | check_lessons_2_5 | auth.five_failures_lock | 2 |
| login-and-account-system | 密码登录失败锁定 | 锁定期间正确密码也被拒 | 别名候选 | check_lessons_2_5 | auth.five_failures_lock | 1 |
| login-and-account-system | 密码登录失败锁定 | 锁定过期后可正常登录 | 别名候选 | check_lessons_2_5 | auth.five_failures_lock | 1 |
| login-and-account-system | 封闭注册与一人一号账号预置 | CSV 缺少学号列被拒绝 | 弱候选 | check_baseline | R3 边界：31 个字符被拒绝 | 2 |
| login-and-account-system | 封闭注册与一人一号账号预置 | 多个学生使用相同联系方式 | 别名候选 | check_lesson10_p0_scenarios | P0 接口：用户唯一约束仅限 role+identifier，不含 phone（联系方式可重复） | 1 |
| login-and-account-system | 封闭注册与一人一号账号预置 | 教师通过 CSV 批量导入学生含手机号 | 弱候选 | check_baseline | R2 失败：学生调用教师接口 → 403 且带请求标识 | 2 |
| login-and-account-system | 封闭注册与一人一号账号预置 | 未登录用户无法注册 | 弱候选 | check_baseline | R2 失败：未登录 → 401 且带请求标识 | 2 |
| login-and-account-system | 封闭注册与一人一号账号预置 | 预置教师账号携带学科与班主任身份 | 弱候选 | check_lesson10_scenarios | 教师账号初始密码：前缀为学校缩写且结尾为工号末六位 | 3 |
| login-and-account-system | 开发种子账号与班级名称 | 教师种子维护身份而不覆盖已改密码 | 弱候选 | check_route_guard | 身份恢复前不显示业务内容：首次改密优先 | 2 |
| login-and-account-system | 开发种子账号与班级名称 | 李明初始密码按学号末六位生成 | 断言名候选 | check_lesson10_scenarios | 学生账号初始密码：前缀为学校缩写且结尾为学号末六位 | 7 |
| login-and-account-system | 开发种子账号与班级名称 | 王芳初始密码按学号末六位生成 | 断言名候选 | check_lesson10_scenarios | 学生账号初始密码：前缀为学校缩写且结尾为学号末六位 | 7 |
| login-and-account-system | 强制首次改密（无验证码例外） | 改密成功后恢复正常访问 | 弱候选 | check_baseline | R2 正常：恰好一行访问日志且标识一致 | 2 |
| login-and-account-system | 强制首次改密（无验证码例外） | 未改密时访问业务接口被拦截 | 弱候选 | check_baseline | R4 失败：业务层 import 路由被拦下 | 2 |
| login-and-account-system | 强制首次改密（无验证码例外） | 首次密码登录被拦截要求改密 | 弱候选 | check_route_guard | 身份恢复前不显示业务内容：首次改密优先 | 2 |
| login-and-account-system | 忘记密码与重置密码 | 任课权限不能代替班主任权限 | 别名候选 | check_lessons_2_5 | auth.subject_teacher_reset_denied | 3 |
| login-and-account-system | 忘记密码与重置密码 | 班主任重置本班学生密码 | 别名候选 | check_lessons_2_5 | auth.homeroom_reset | 3 |
| login-and-account-system | 忘记密码与重置密码 | 用户忘记密码看到班主任提示 | 别名候选 | check_lesson10_p0_scenarios | P0 前端：忘记密码显示「请联系班主任重置」提示 | 1 |
| material-upload | 上传元数据与班级选择 | 上传元数据完整记录 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| material-upload | 上传元数据与班级选择 | 多班级教师班级选择器展示所有任教班级 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| material-upload | 上传元数据与班级选择 | 教师篡改 class_id 上传非任教班级被拒 | 仅文件级 | check_lesson_prep | （未定位到具体断言） | 9 |
| material-upload | 上传元数据与班级选择 | 教师选择任教班级上传成功 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| material-upload | 下载与预览 | 学生下载材料成功 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| material-upload | 下载与预览 | 学生在线预览 PDF 成功 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| material-upload | 下载与预览 | 学生在线预览图片成功 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| material-upload | 下载与预览 | 学生尝试下载其他班材料被拒 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| material-upload | 下载与预览 | 引用原文的文件版本已变化 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| material-upload | 下载与预览 | 教师下载任教班级材料成功 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| material-upload | 教师上传权限控制 | 学生前端无上传入口 | 别名候选 | check_lessons_2_5 | materials.student_upload_denied | 2 |
| material-upload | 教师上传权限控制 | 学生尝试上传被拒 | 别名候选 | check_lessons_2_5 | materials.student_upload_denied | 2 |
| material-upload | 教师上传权限控制 | 教师上传资料成功 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| material-upload | 教师删除资料 | 删除后资料不可再访问 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| material-upload | 教师删除资料 | 前端仅教师展示删除入口 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| material-upload | 教师删除资料 | 学生尝试删除资料被拒 | 仅文件级 | check_lesson_prep | （未定位到具体断言） | 4 |
| material-upload | 教师删除资料 | 教师删除任教班级资料成功 | 仅文件级 | check_lesson_prep | （未定位到具体断言） | 4 |
| material-upload | 教师删除资料 | 教师尝试删除非任教班级资料被拒 | 别名候选 | check_lessons_2_5 | auth.teacher_cross_class_denied | 3 |
| material-upload | 文件存储策略 | SQLite 仅存储元数据 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| material-upload | 文件存储策略 | 容器重启后文件不丢失 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| material-upload | 文件存储策略 | 文件存储在挂载目录 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| material-upload | 文件存储策略 | 文件按 class_id 分子目录存储 | 仅文件级 | check_lesson_prep | （未定位到具体断言） | 7 |
| material-upload | 文件类型与大小限制 | 上传不允许的格式被拒 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| material-upload | 文件类型与大小限制 | 上传允许格式的文件成功 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| material-upload | 文件类型与大小限制 | 上传超大文件被拒 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| material-upload | 文件类型与大小限制 | 伪造扩展名被后端 MIME 校验拦截 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| material-upload | 文件类型与大小限制 | 前端 accept 属性初步限制 | 仅文件级 | check_lesson_prep | （未定位到具体断言） | 5 |
| material-upload | 文件重名与异常处理 | DB 写入失败时回滚删除物理文件 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| material-upload | 文件重名与异常处理 | 同名文件自动重命名 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| material-upload | 文件重名与异常处理 | 恶意文件头校验不通过被拒 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| material-upload | 文件重名与异常处理 | 网络中断前端提供重试 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| material-upload | 材料数据隔离 | 学生尝试下载其他班材料被拒 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| material-upload | 材料数据隔离 | 学生查询本班材料成功 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| material-upload | 材料数据隔离 | 学生篡改 class_id 查询被拒 | 仅文件级 | check_lesson_prep | （未定位到具体断言） | 8 |
| material-upload | 材料数据隔离 | 教师查询任教班级材料成功 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| material-upload | 知识库索引关联 | 上传成功后异步解析为纯文本 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| material-upload | 知识库索引关联 | 仅 is_indexed=true 的材料被 AI 检索 | 仅文件级 | check_lesson_prep | （未定位到具体断言） | 15 |
| material-upload | 知识库索引关联 | 解析失败的材料保持未索引 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| material-upload | 知识库索引关联 | 解析完成后标记 is_indexed 为 true | 仅文件级 | check_lesson_prep | （未定位到具体断言） | 12 |
| mcp-tool-integration | MCP 与技能接口文档 | 打开 Swagger 试调 | 仅文件级 | check_security_gate | （未定位到具体断言） | 5 |
| mcp-tool-integration | MCP 与技能接口文档 | 默认关闭文档 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| mcp-tool-integration | MCP 工具调用审计 | 三种结果各有记录 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| mcp-tool-integration | MCP 工具调用审计 | 决策轮用量可追溯 | 弱候选 | check_security_gate | P1-2 决策轮用量： | 4 |
| mcp-tool-integration | MCP 工具调用审计 | 审计存储失败可观察 | 弱候选 | check_security_gate | 审计故障：工具存储回滚且不中断 | 2 |
| mcp-tool-integration | MCP 工具调用审计 | 记录只看自己的范围 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| mcp-tool-integration | MCP 服务器登记与令牌边界 | 不在允许清单的地址 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| mcp-tool-integration | MCP 服务器登记与令牌边界 | 同名再登记 | 弱候选 | check_mcp_tools | 同名再登记 400 | 4 |
| mcp-tool-integration | MCP 服务器登记与令牌边界 | 换机后令牌不可用 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| mcp-tool-integration | MCP 服务器登记与令牌边界 | 登记后响应不含令牌 | 弱候选 | check_mcp_tools | 响应不含令牌 | 5 |
| mcp-tool-integration | 候选工具与工具声明 | 只带技能内工具 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| mcp-tool-integration | 工具内容的信任边界 | 工具说明夹带指令 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| mcp-tool-integration | 工具内容的信任边界 | 工具返回夹带指令 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| mcp-tool-integration | 工具引用格式与保存期校验 | 工具不在清单或服务器未连接 | 弱候选 | check_mcp_tools | 重复连接工具不翻倍 | 3 |
| mcp-tool-integration | 工具引用格式与保存期校验 | 引用写法不合规 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| mcp-tool-integration | 服务器与调用记录的归属隔离 | 同伴访问我的服务器 | 弱候选 | check_mcp_tools | 同伴读取他人服务器 404 | 3 |
| mcp-tool-integration | 服务器与调用记录的归属隔离 | 学生调用管理接口 | 弱候选 | check_mcp_tools | 学生访问管理接口 403 | 4 |
| mcp-tool-integration | 服务端调用循环与上限 | 两步任务连续两轮 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| mcp-tool-integration | 服务端调用循环与上限 | 发现重连未知权限默认拒绝 | 弱候选 | check_security_gate | P0-5 边界：未知DiscoveredTool默认可写 | 2 |
| mcp-tool-integration | 服务端调用循环与上限 | 命中工具并用到提示 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| mcp-tool-integration | 服务端调用循环与上限 | 学生写入拒绝且 SSE 完整 | 仅文件级 | check_mcp_tools | （未定位到具体断言） | 5 |
| mcp-tool-integration | 服务端调用循环与上限 | 工具超时 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| mcp-tool-integration | 服务端调用循环与上限 | 教师与错误归属执行对照 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| mcp-tool-integration | 服务端调用循环与上限 | 超过轮次上限 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| mcp-tool-integration | 自建 MCP 工具服务 | 令牌缺失或错误 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| mcp-tool-integration | 自建 MCP 工具服务 | 带令牌发现并调用工具 | 弱候选 | check_mcp_tools | 确实带令牌调用了工具 | 4 |
| mcp-tool-integration | 自建 MCP 工具服务 | 非法请求可读 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| mcp-tool-integration | 连接、发现与断开 | 令牌错误时连接失败 | 弱候选 | check_mcp_tools | 连接失败 502 | 3 |
| mcp-tool-integration | 连接、发现与断开 | 断开后不可调用 | 弱候选 | check_mcp_tools | 断开后引用记 denied | 2 |
| mcp-tool-integration | 连接、发现与断开 | 连接自建服务发现工具 | 弱候选 | check_mcp_tools | 重复连接工具不翻倍 | 2 |
| mcp-tool-integration | 连接、发现与断开 | 连续连接两次 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| quiz-homework-publication | 作业及配图逐资源授权 | 学生跨班读取或提交 | 别名候选 | check_quiz_homework | H/学生跨班读取或提交 | 3 |
| quiz-homework-publication | 作业及配图逐资源授权 | 教师班级或学科不符 | 别名候选 | check_quiz_homework | H/教师班级或学科不符： | 3 |
| quiz-homework-publication | 作业及配图逐资源授权 | 未登录读取作业或配图 | 别名候选 | check_quiz_homework | H/未登录读取作业或配图： | 2 |
| quiz-homework-publication | 作业及配图逐资源授权 | 访问他人的提交或教师接口 | 断言名候选 | check_quiz_homework | H/访问他人的提交或教师接口：教师接口 | 11 |
| quiz-homework-publication | 作业及配图逐资源授权 | 配图异常 | 弱候选 | check_quiz_homework | H/配图异常：非法名 | 3 |
| quiz-homework-publication | 作业终评与错题同步 | M1 首次满分不入错题 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| quiz-homework-publication | 作业终评与错题同步 | M2 低分改为及格或满分 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| quiz-homework-publication | 作业终评与错题同步 | M3 修复历史残留不改成绩 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| quiz-homework-publication | 作业终评与错题同步 | M4 越权或事务失败不部分改分 | 弱候选 | check_quiz_homework | H/教师班级或学科不符：改分学生越权 | 2 |
| quiz-homework-publication | 历史资料和既有作业兼容 | 更新后旧资料仍可访问 | 断言名候选 | check_quiz_homework | H/更新后旧资料仍可访问 | 9 |
| quiz-homework-publication | 历史资料和既有作业兼容 | 老试卷主动重新发布 | 断言名候选 | check_quiz_homework | H/老试卷主动重新发布 | 8 |
| quiz-homework-publication | 历史资料和既有作业兼容 | 迁移重复执行 | 弱候选 | check_quiz_homework | H/迁移重复执行 | 5 |
| quiz-homework-publication | 发布内容和教师评分依据分离冻结 | 原题和原资料后续变化 | 断言名候选 | check_quiz_homework | H/原题和原资料后续变化 | 9 |
| quiz-homework-publication | 发布内容和教师评分依据分离冻结 | 学生响应不泄露评分依据 | 别名候选 | check_quiz_homework | H/学生响应不泄露评分依据 | 2 |
| quiz-homework-publication | 命题作业支持初批及教师终评 | AI 使用发布时的评分依据 | 断言名候选 | check_quiz_homework | H/AI 使用发布时的评分依据 | 11 |
| quiz-homework-publication | 命题作业支持初批及教师终评 | 分数折算边界 | 弱候选 | check_quiz_homework | H/分数折算边界： | 5 |
| quiz-homework-publication | 命题作业支持初批及教师终评 | 初批失败仍可人工改分 | 断言名候选 | check_quiz_homework | H/初批失败仍可人工改分： | 9 |
| quiz-homework-publication | 命题作业支持初批及教师终评 | 初批期间提交被更新或教师改分 | 断言名候选 | check_quiz_homework | H/初批期间提交被更新或教师改分：重交 | 13 |
| quiz-homework-publication | 命题作业支持初批及教师终评 | 教师直接评分并联动错题学情 | 断言名候选 | check_quiz_homework | H/教师直接评分并联动错题学情 | 12 |
| quiz-homework-publication | 命题作业支持初批及教师终评 | 教师覆盖 AI 分且后续初批跳过 | 断言名候选 | check_quiz_homework | H/教师覆盖 AI 分且后续初批跳过 | 13 |
| quiz-homework-publication | 命题作业支持初批及教师终评 | 非百分制原卷折算 | 断言名候选 | check_quiz_homework | H/非百分制原卷折算 | 7 |
| quiz-homework-publication | 命题作业的展示与文本提交 | 截止前重新提交 | 断言名候选 | check_quiz_homework | H/截止前重新提交 | 6 |
| quiz-homework-publication | 命题作业的展示与文本提交 | 提交命题作业 | 弱候选 | check_quiz_homework | H/提交命题作业 | 5 |
| quiz-homework-publication | 命题作业的展示与文本提交 | 逾期或关闭后提交 | 断言名候选 | check_quiz_homework | H/逾期或关闭后提交：逾期 | 7 |
| quiz-homework-publication | 命题作业的展示与文本提交 | 题面显示一致 | 弱候选 | check_quiz_homework | H/题面显示一致 | 5 |
| quiz-homework-publication | 手工与命题作业共用作业入口 | 两种作业同时展示 | 断言名候选 | check_quiz_homework | H/两种作业同时展示 | 7 |
| quiz-homework-publication | 手工与命题作业共用作业入口 | 保留手工布置 | 弱候选 | check_quiz_homework | H/保留手工布置：草稿不可见 | 5 |
| quiz-homework-publication | 手工与命题作业共用作业入口 | 学科与班级筛选 | 断言名候选 | check_quiz_homework | H/学科与班级筛选 | 6 |
| rag-search | AI 回答的 Markdown 与公式渲染 | 公式渲染为数学符号 | 别名候选 | check_lesson10_p0_scenarios | P0 前端：公式渲染使用 KaTeX 数学符号 | 1 |
| rag-search | AI 回答的 Markdown 与公式渲染 | 支持 Markdown 列表与加粗 | 弱候选 | check_lessons_2_5 | materials.download | 3 |
| rag-search | AI 回答的 Markdown 与公式渲染 | 独立公式居中美化与长公式横向滚动 | 别名候选 | check_lesson10_p0_scenarios | P0 前端：独立公式居中与长公式横向滚动样式存在 | 1 |
| rag-search | 上传材料的索引流程扩展 | 上传成功后异步解析并分块向量化 | 别名候选 | check_lessons_2_5 | rag.chunks_vectors_persisted | 3 |
| rag-search | 上传材料的索引流程扩展 | 解析成功但向量化失败保持未索引 | 弱候选 | check_lesson10_p0_scenarios | P0 接口：向量化失败时 is_indexed=False 但上传接口已返回成功 | 5 |
| rag-search | 关键字、向量与混合检索 | 关键字检索返回字面命中的分块 | 别名候选 | check_formula_retrieval | keyword formula recalled despite coordinate distractor | 1 |
| rag-search | 关键字、向量与混合检索 | 向量检索按哈希向量相似度排序 | 别名候选 | check_formula_retrieval | vector formula recalled despite coordinate distractor | 1 |
| rag-search | 关键字、向量与混合检索 | 混合检索融合两路排序 | 别名候选 | check_formula_retrieval | hybrid formula recalled despite coordinate distractor | 2 |
| rag-search | 内容溯源 | 回答标注引用来源 | 别名候选 | check_lessons_2_5 | agent.citations_provenance | 2 |
| rag-search | 内容溯源 | 引用来源与检索一致 | 别名候选 | check_formula_retrieval | real formula reference retained | 2 |
| rag-search | 内容溯源 | 文件变更或历史索引无版本 | 别名候选 | check_formula_retrieval | tampered source excluded | 3 |
| rag-search | 内容溯源 | 无效编号与未使用候选 | 别名候选 | check_lessons_2_5 | citations.invalid_number_removed | 1 |
| rag-search | 向量化存储 | 分块向量化并存储 | 别名候选 | check_lessons_2_5 | rag.chunks_vectors_persisted | 2 |
| rag-search | 向量化存储 | 向量化失败不阻塞上传 | 别名候选 | check_lesson10_p0_scenarios | P0 接口：向量化失败时 is_indexed=False 但上传接口已返回成功 | 1 |
| rag-search | 回答不包含检索过程元话语 | 用户直接询问教材标准公式 | 别名候选 | check_formula_retrieval | real formula reference retained | 1 |
| rag-search | 回答不包含检索过程元话语 | 资料未含公式本体时说明依据不足 | 别名候选 | check_formula_retrieval | no invented auto reference | 1 |
| rag-search | 回答正文与参考资料分离展示 | 命中可标注出处并回溯到原文 | 别名候选 | check_lessons_2_5 | citations.excerpt_is_exact_chunk | 1 |
| rag-search | 回答正文与参考资料分离展示 | 回答与参考资料独立成卡 | 别名候选 | check_lesson10_p0_scenarios | P0 接口：回答与参考资料在数据模型中分离（citations 独立字段） | 1 |
| rag-search | 回答正文与参考资料分离展示 | 多命中逐条展示保留溯源 | 别名候选 | check_lesson10_p0_scenarios | P0 前端：参考资料独立区域逐条展示并保留溯源 | 1 |
| rag-search | 回答正文与参考资料分离展示 | 引用摘录保留真实分块 | 别名候选 | check_formula_retrieval | raw excerpts unchanged | 2 |
| rag-search | 回答正文与参考资料分离展示 | 无引用时仅显示回答 | 别名候选 | check_lesson10_p0_scenarios | P0 前端：无引用时仅显示回答（条件渲染） | 1 |
| rag-search | 基于限定的被检索资料回答 | 无召回分块不臆造依据 | 别名候选 | check_formula_retrieval | no invented auto reference | 2 |
| rag-search | 基于限定的被检索资料回答 | 答案基于召回分块生成 | 别名候选 | check_formula_retrieval | real formula reference retained | 1 |
| rag-search | 数值题公式检索与原文保持 | 坐标题检索夹角余弦公式 | 仅文件级 | check_formula_retrieval | （未定位到具体断言） | 5 |
| rag-search | 数值题公式检索与原文保持 | 无关或变更资料 | 别名候选 | check_formula_retrieval | irrelevant question not forced into chapter | 2 |
| rag-search | 文本分块 | 短材料生成单个分块 | 断言名候选 | check_lesson10_scenarios | 文本分块：短材料生成单个分块 | 8 |
| rag-search | 文本分块 | 解析材料生成多个分块 | 别名候选 | check_lessons_2_5 | rag.chunks_vectors_persisted | 2 |
| rag-search | 跨章节检索预筛 (Cross-Chapter Prefilter) | 跨章节无关材料被预筛排除 | 别名候选 | check_formula_retrieval | irrelevant question not forced into chapter | 2 |
| rag-search | 跨章节检索预筛 (Cross-Chapter Prefilter) | 预筛无保留时回退全保留 | 别名候选 | check_formula_retrieval | irrelevant question not forced into chapter | 2 |
| rag-search | 限定班级的知识库检索 | 学生提问召回本班相关分块 | 别名候选 | check_formula_retrieval | keyword formula recalled despite coordinate distractor | 1 |
| rag-search | 限定班级的知识库检索 | 无可用分块时降级 | 别名候选 | check_formula_retrieval | no invented auto reference | 2 |
| rag-search | 限定班级的知识库检索 | 检索严格限定本班范围 | 别名候选 | check_formula_retrieval | class and subject retained | 1 |
| rbac-role-permissions | AI 提问每日次数限制（按学生独立计数） | 不同学生账号次数独立计算 | 弱候选 | check_lesson10_scenarios | 学生账号初始密码：前缀为学校缩写且结尾为学号末六位 | 3 |
| rbac-role-permissions | AI 提问每日次数限制（按学生独立计数） | 学生当日提问未达上限 | 别名候选 | check_lesson10_p0_scenarios | P0 接口：AI 提问每日上限为 40 次 | 1 |
| rbac-role-permissions | AI 提问每日次数限制（按学生独立计数） | 学生当日提问达到上限被拒 | 别名候选 | check_lessons_2_5 | agent.spec_40_question_limit | 2 |
| rbac-role-permissions | AI 提问每日次数限制（按学生独立计数） | 次日提问次数重置 | 别名候选 | check_lesson10_p0_scenarios | P0 接口：提问计数按中国时区自然日重置 | 1 |
| rbac-role-permissions | 前端路由级权限拦截 | 伪造角色提示不赋予页面权限 | 断言名候选 | check_route_guard | 伪造角色提示不赋予页面权限：提示仅允许启动校验 | 12 |
| rbac-role-permissions | 前端路由级权限拦截 | 刷新恢复后的角色仍须匹配 | 断言名候选 | check_route_guard | 刷新恢复后的角色仍须匹配： | 11 |
| rbac-role-permissions | 前端路由级权限拦截 | 双标签提示变化后的单科切班 | 断言名候选 | check_route_guard | 双标签提示变化后的单科切班：教师页面不被学生提示拒绝 | 12 |
| rbac-role-permissions | 前端路由级权限拦截 | 学生访问学生路由通过 | 弱候选 | check_analytics | S3 失败：学生访问班级学情 → 403 | 3 |
| rbac-role-permissions | 前端路由级权限拦截 | 学生访问教师路由被拦截 | 弱候选 | check_baseline | R4 失败：业务层 import 路由被拦下 | 3 |
| rbac-role-permissions | 前端路由级权限拦截 | 教师访问学生路由被拦截 | 弱候选 | check_baseline | R4 失败：业务层 import 路由被拦下 | 3 |
| rbac-role-permissions | 前端路由级权限拦截 | 教师访问教师路由通过 | 弱候选 | check_analytics | S3 失败：教师跨班访问 → 403 | 2 |
| rbac-role-permissions | 前端路由级权限拦截 | 未登录用户访问业务路由重定向登录 | 弱候选 | check_baseline | R2 失败：未登录 → 401 且带请求标识 | 2 |
| rbac-role-permissions | 前端路由级权限拦截 | 角色目录按完整路径边界判断 | 断言名候选 | check_route_guard | 角色目录按完整路径边界判断：${route} / ${role} | 12 |
| rbac-role-permissions | 前端路由级权限拦截 | 身份恢复前不显示业务内容 | 断言名候选 | check_route_guard | 身份恢复前不显示业务内容：缺少 | 11 |
| rbac-role-permissions | 前端路由级权限拦截 | 辅助提示缺失但会话有效 | 断言名候选 | check_route_guard | 辅助提示缺失但会话有效：允许启动并恢复 ${route} | 10 |
| rbac-role-permissions | 双角色定义与教师学科身份 | 学生仅以学号密码登录 | 弱候选 | check_lesson10_scenarios | 学生账号初始密码：前缀为学校缩写且结尾为学号末六位 | 3 |
| rbac-role-permissions | 双角色定义与教师学科身份 | 教师学科身份登录后进入教研组 | 弱候选 | check_analytics | S3 失败：教师跨学科访问 → 403 | 2 |
| rbac-role-permissions | 双角色定义与教师学科身份 | 系统不创建独立家长角色 | 断言名候选 | check_lesson10_scenarios | 双角色定义：系统不创建独立家长角色 | 10 |
| rbac-role-permissions | 后端接口级权限拦截 | 学生调用学生接口通过 | 弱候选 | check_baseline | R2 失败：学生调用教师接口 → 403 且带请求标识 | 4 |
| rbac-role-permissions | 后端接口级权限拦截 | 学生调用教师接口返回 403 | 别名候选 | check_lessons_2_5 | auth.student_teacher_api_denied | 2 |
| rbac-role-permissions | 后端接口级权限拦截 | 教师调用学生接口返回 403 | 别名候选 | check_lessons_2_5 | auth.teacher_student_api_denied | 2 |
| rbac-role-permissions | 后端接口级权限拦截 | 教师调用教师接口通过 | 弱候选 | check_baseline | R2 失败：学生调用教师接口 → 403 且带请求标识 | 5 |
| rbac-role-permissions | 学生功能权限矩阵 | 学生不能越权查看其他学生数据 | 弱候选 | check_homework | S1 正常：草稿作业学生不可见 | 2 |
| rbac-role-permissions | 学生功能权限矩阵 | 学生修改个人密码 | 别名候选 | check_lessons_2_5 | auth.change_password | 1 |
| rbac-role-permissions | 学生功能权限矩阵 | 学生发起 AI 提问并查看历史 | 弱候选 | check_lesson10_p0_scenarios | P0 接口：AI 提问每日上限为 40 次 | 3 |
| rbac-role-permissions | 学生功能权限矩阵 | 学生将 AI 解答加入错题本 | 弱候选 | check_homework | S7 正常：判错（50分）写入错题本 | 3 |
| rbac-role-permissions | 学生功能权限矩阵 | 学生查看个人错题本 | 弱候选 | check_homework | S6 失败：学生查看他人提交 → 404 | 3 |
| rbac-role-permissions | 学生功能权限矩阵 | 学生查看本班资料并提交作业 | 别名候选 | check_homework | S3 正常：学生提交成功 | 3 |
| rbac-role-permissions | 学生数据权限 - 个人数据隔离（一人一号） | 学生尝试查询他人数据被拒 | 弱候选 | check_homework | S6 失败：学生查看他人提交 → 404 | 2 |
| rbac-role-permissions | 学生数据权限 - 个人数据隔离（一人一号） | 学生查询自己数据成功 | 弱候选 | check_homework | S3 正常：学生提交成功 | 2 |
| rbac-role-permissions | 教师功能权限矩阵 | 任课教师不能重置学生密码 | 弱候选 | check_baseline | R2 失败：学生调用教师接口 → 403 且带请求标识 | 2 |
| rbac-role-permissions | 教师功能权限矩阵 | 教师上传资料并布置作业 | 弱候选 | check_homework | S1 正常：教师创建草稿作业 200 | 2 |
| rbac-role-permissions | 教师功能权限矩阵 | 教师不能代替学生发起 AI 提问 | 弱候选 | check_lesson10_p0_scenarios | P0 接口：AI 提问每日上限为 40 次 | 3 |
| rbac-role-permissions | 教师功能权限矩阵 | 教师不能查看非任教班级的学生数据 | 弱候选 | check_homework | S1 失败：非任教班级布置 → 403 | 4 |
| rbac-role-permissions | 教师功能权限矩阵 | 教师仅能访问本学科教研资料 | 弱候选 | check_analytics | S3 失败：教师跨学科访问 → 403 | 3 |
| rbac-role-permissions | 教师功能权限矩阵 | 教师批改作业并查看本班学生数据 | 弱候选 | check_analytics | S1 正常：班主任查看本班全科 101 学情 | 3 |
| rbac-role-permissions | 教师功能权限矩阵 | 教师查看本班学生 AI 提问历史 | 弱候选 | check_analytics | S1 正常：班主任查看本班全科 101 学情 | 3 |
| rbac-role-permissions | 教师功能权限矩阵 | 教师管理自己任教的班级 | 弱候选 | check_lesson10_p0_scenarios | P0 前端：教师未分配任教班级时存在空状态提示 | 3 |
| rbac-role-permissions | 教师功能权限矩阵 | 教师重置本班学生密码 | 弱候选 | check_baseline | R2 失败：学生调用教师接口 → 403 且带请求标识 | 2 |
| rbac-role-permissions | 教师功能权限矩阵 | 班主任跨学科查看本班学情 | 断言名候选 | check_analytics | S1 正常：班主任查看本班全科 101 学情 | 6 |
| rbac-role-permissions | 教师多班级操作校验 | 多班级选择器展示所有任教班级 | 弱候选 | check_homework | S1 失败：非任教班级布置 → 403 | 3 |
| rbac-role-permissions | 教师多班级操作校验 | 教师选择任教班级操作成功 | 弱候选 | check_lesson10_p0_scenarios | P0 前端：教师未分配任教班级时存在空状态提示 | 4 |
| rbac-role-permissions | 教师多班级操作校验 | 教师选择非任教班级操作被拒 | 弱候选 | check_homework | S1 失败：非任教班级布置 → 403 | 4 |
| rbac-role-permissions | 教师数据权限 - 任教班级隔离 | 后端不信任请求体中的 class_id | 断言名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation | 6 |
| rbac-role-permissions | 教师数据权限 - 任教班级隔离 | 教师查询任教班级数据成功 | 弱候选 | check_lesson10_p0_scenarios | P0 前端：教师未分配任教班级时存在空状态提示 | 4 |
| rbac-role-permissions | 教师数据权限 - 任教班级隔离 | 教师查询非任教班级数据被拒 | 弱候选 | check_homework | S1 失败：非任教班级布置 → 403 | 4 |
| rbac-role-permissions | 教师数据权限 - 任教班级隔离 | 教师跨班操作被拒 | 弱候选 | check_analytics | S3 失败：教师跨班访问 → 403 | 3 |
| rbac-role-permissions | 权限变更生效机制 | Refresh Token 刷新后新权限生效 | 断言名候选 | check_lessons_2_5 | auth.refresh_cookie_httponly | 6 |
| rbac-role-permissions | 权限变更生效机制 | 未刷新前旧权限仍有效 | 弱候选 | check_security_gate | JWT-J2 正常：exp==当前整数秒仍有效 | 2 |
| rbac-role-permissions | 权限变更生效机制 | 重新登录后新权限生效 | 别名候选 | check_lesson10_p0_scenarios | P0 接口：权限从数据库实时读取（populate_existing=True） | 1 |
| rbac-role-permissions | 越权处理与审计日志 | 前端越权跳转 403 页面 | 断言名候选 | check_route_guard | 前端越权跳转 403 页面：已就绪页面角色变化时先隐藏业务 | 10 |
| rbac-role-permissions | 越权处理与审计日志 | 后端越权返回 403 并记录审计日志 | 弱候选 | check_route_guard | 前端越权跳转 403 页面：已就绪页面角色变化时先隐藏业务 | 4 |
| rbac-role-permissions | 越权处理与审计日志 | 审计日志异步写入不影响响应性能 | 弱候选 | check_security_gate | R2 审计异步：401响应正文发出后再写入 | 4 |
| rbac-role-permissions | 越权处理与审计日志 | 技能审计字段查询与范围 | 别名候选 | check_lessons_2_5 | auth.audit_logs_query | 1 |
| rbac-role-permissions | 越权处理与审计日志 | 教师跨班操作记录审计日志 | 别名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation | 2 |
| rbac-role-permissions | 越权处理与审计日志 | 未登录请求留匿名审计 | 弱候选 | check_baseline | R2 失败：未登录 → 401 且带请求标识 | 3 |
| research-materials | 原班级直传入口阻止明显教师版 | 完整教师 Markdown 误传班级 | 仅文件级 | check_research_materials | （未定位到具体断言） | 8 |
| research-materials | 发布时生成知识点标签 | 标题未包含已知知识点 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| research-materials | 发布时生成知识点标签 | 立体几何章节带知识点标签 | 仅文件级 | check_research_materials | （未定位到具体断言） | 5 |
| research-materials | 学生版按任教班级独立发布 | 发布学生讲义到两个任教班级 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| research-materials | 学生版按任教班级独立发布 | 越权班级混入发布批次 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| research-materials | 学生版题干提取与教师核对 | 现有结构化讲义生成学生版 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| research-materials | 学生版题干提取与教师核对 | 编辑后重新核对 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| research-materials | 学生讲义打印与另存 PDF | 学生保存图文讲义 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| research-materials | 学生讲义打印与另存 PDF | 教师打印未发布的学生预览 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| research-materials | 学生讲义打印与另存 PDF | 配图尚未就绪 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| research-materials | 教师资料先导入学科组 | 图片没有随 Markdown 导入 | 仅文件级 | check_research_materials | （未定位到具体断言） | 7 |
| research-materials | 教师资料先导入学科组 | 导入完善版图文资料包 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| research-materials | 班级配图与图文包受权访问 | 删除班级讲义 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| research-materials | 班级配图与图文包受权访问 | 学生预览和下载有图讲义 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| research-materials | 组内共享教案查阅与复用 | 下载教师图文包 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| research-materials | 组内共享教案查阅与复用 | 同科同事复用共享教案 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| research-materials | 组内共享教案查阅与复用 | 绕过学生稿制作 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| research-materials | 组内教师共享与学生隔离 | 同科同事选用素材 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| research-materials | 组内教师共享与学生隔离 | 学生直接猜测教师原稿地址 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| runtime-reliability | 可配置且受限的 SQLite 日志模式 | Windows 共享目录运行小组服务 | 弱候选 | check_lesson10_p0_scenarios | P0 接口：向量化失败时 is_indexed=False 但上传接口已返回成功 | 2 |
| runtime-reliability | 可配置且受限的 SQLite 日志模式 | 使用原生磁盘的 WAL 配置 | 弱候选 | check_lesson10_p0_scenarios | P0 接口：SQLite 代码默认日志模式为 WAL，且支持环境变量覆盖 | 2 |
| runtime-reliability | 可配置且受限的 SQLite 日志模式 | 无效日志模式 | 弱候选 | check_lesson10_p0_scenarios | P0 接口：SQLite 代码默认日志模式为 WAL，且支持环境变量覆盖 | 3 |
| runtime-reliability | 存储修复保留业务数据 | 会话接口磁盘 I/O 故障修复 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| runtime-reliability | 数据库可读性纳入健康检查 | 数据库存储异常 | 弱候选 | check_baseline | R1 失败：数据库异常 → 503 与通用提示 | 3 |
| runtime-reliability | 数据库可读性纳入健康检查 | 数据库读取正常 | 弱候选 | check_lesson10_p0_scenarios | P0 接口：权限从数据库实时读取（populate_existing=True） | 3 |
| smart-lesson-prep | 两种学生文稿分班发布 | 发布批次混入其他班 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-lesson-prep | 两种学生文稿分班发布 | 教案和讲义均发布给学生 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-lesson-prep | 两种学生文稿分班发布 | 新修订尝试发布旧学生稿 | 仅文件级 | check_lesson_prep | （未定位到具体断言） | 5 |
| smart-lesson-prep | 中文空格图片路径兼容 | 原题图的中文目录含空格 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-lesson-prep | 中文空格图片路径兼容 | 生成与发布图文包 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-lesson-prep | 从学科组教师资料发起备课 | 尚未提供学情 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-lesson-prep | 从学科组教师资料发起备课 | 数学教师发起线面角备课 | 仅文件级 | check_lesson_prep | （未定位到具体断言） | 4 |
| smart-lesson-prep | 从定稿生成两种学生稿 | 学生稿中的单反斜杠公式被修补 | 仅文件级 | check_lesson_prep | （未定位到具体断言） | 8 |
| smart-lesson-prep | 从定稿生成两种学生稿 | 学生稿含漏网控制字符 | 仅文件级 | check_lesson_prep | （未定位到具体断言） | 8 |
| smart-lesson-prep | 从定稿生成两种学生稿 | 学生稿生成未通过检查 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-lesson-prep | 从定稿生成两种学生稿 | 教师生成并修改学生讲义 | 仅文件级 | check_lesson_prep | （未定位到具体断言） | 6 |
| smart-lesson-prep | 完整片段与出处核对 | 多份资料均被选入 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-lesson-prep | 完整片段与出处核对 | 核对例题出处 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-lesson-prep | 定稿快照与并发保护 | 旧窗口写入 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-lesson-prep | 定稿快照与并发保护 | 第二次定稿 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-lesson-prep | 教师定稿可选共享到教研组 | 主动共享完整教师定稿 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-lesson-prep | 教师定稿可选共享到教研组 | 删除私人原教案 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-lesson-prep | 教师定稿可选共享到教研组 | 教师选择保留私有 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-lesson-prep | 教师定稿可选共享到教研组 | 重复发布或后续修改 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-lesson-prep | 教案隔离删除与审计 | 删除私人教案 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-lesson-prep | 教案隔离删除与审计 | 同学科同事访问私人教案 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-lesson-prep | 流式生成与失败处理 | AI 完成教师草案 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-lesson-prep | 流式生成与失败处理 | 生成中断或无 Key | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-lesson-prep | 编辑审阅与章节重写 | 审阅后再改正文 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-lesson-prep | 编辑审阅与章节重写 | 重写教学过程 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-question-generation | 候选题逐题复核 | 修改后通过 | 弱候选 | check_question_bank | 细分知识点：归一到所选知识点后通过 | 2 |
| smart-question-generation | 候选题逐题复核 | 未确认即通过 | 弱候选 | check_question_bank | 未确认即通过 400 | 5 |
| smart-question-generation | 候选题逐题复核 | 重复题目 | 弱候选 | check_question_bank | 重复题干通过 409 | 2 |
| smart-question-generation | 候选题逐题复核 | 驳回后尝试通过 | 弱候选 | check_question_bank | 驳回后通过 409 | 3 |
| smart-question-generation | 公式结构校验 | 修改时引入不配对括号 | 断言名候选 | check_question_bank | 修改引入不配对括号：400 且题目与 revision 不变 | 7 |
| smart-question-generation | 公式结构校验 | 修改补齐括号后通过 | 断言名候选 | check_question_bank | 补齐括号后保存并通过：进入题库且标记已修改 | 6 |
| smart-question-generation | 公式结构校验 | 定界符不成对 | 弱候选 | check_question_bank | 公式结构：转义、cases 与定界符正反用例 | 2 |
| smart-question-generation | 公式结构校验 | 转义括号与环境不被误判 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-question-generation | 公式结构校验 | 转义的美元符号 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-question-generation | 公式结构校验 | 选项缺右括号 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-question-generation | 发起命题生成 | 使用词表外的知识点 | 弱候选 | check_question_bank | 词表外知识点 400 | 4 |
| smart-question-generation | 发起命题生成 | 数学教师按配比发起命题 | 仅文件级 | check_question_bank | （未定位到具体断言） | 4 |
| smart-question-generation | 发起命题生成 | 选用他科资料 | 弱候选 | check_question_bank | 选用他科资料 404 | 5 |
| smart-question-generation | 发起命题生成 | 配比不一致或越界 | 弱候选 | check_question_bank | 原图被替换后发布 409（指纹不一致） | 2 |
| smart-question-generation | 命题审计记录 | 作业发布审计 | 弱候选 | check_question_bank | 发布生成已发布命题作业 | 2 |
| smart-question-generation | 命题审计记录 | 删除候选题后追溯 | 断言名候选 | check_question_bank | 删除候选题后追溯 | 7 |
| smart-question-generation | 命题审计记录 | 查看入库题目的复核历史 | 断言名候选 | check_question_bank | 查看入库题目的复核历史 | 10 |
| smart-question-generation | 命题接口文档与验收脚本 | 无 Key 环境运行验收脚本 | 弱候选 | check_question_bank | 无 Key 返回 503 | 3 |
| smart-question-generation | 命题范围隔离 | 同科同事读取他人候选题 | 断言名候选 | check_question_bank | 同科同事读取他人候选题 404 | 10 |
| smart-question-generation | 命题范围隔离 | 学生调用命题接口 | 仅文件级 | check_question_bank | （未定位到具体断言） | 4 |
| smart-question-generation | 命题范围隔离 | 物理教师读取数学题目 | 弱候选 | check_question_bank | 学生读取题目 403 | 2 |
| smart-question-generation | 学生卷选项排版 | 学生端打开新发布的试卷 | 弱候选 | check_question_bank | 新发布不写入 quiz_publications 或资料 | 2 |
| smart-question-generation | 学生卷选项排版 | 已发布资料不被改写 | 弱候选 | check_question_bank | 发布生成已发布命题作业 | 2 |
| smart-question-generation | 学生卷选项排版 | 第 10 题以后 | 弱候选 | check_question_bank | 学生卷第 10 题：选项缩进 4 格 | 3 |
| smart-question-generation | 学生卷选项排版 | 选项各占一行 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-question-generation | 学生卷选项排版 | 选项含块级公式 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-question-generation | 学科题库 | 下架后组卷 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-question-generation | 学科题库 | 修改入库题目 | 弱候选 | check_question_bank | 入库题目修改 409 | 4 |
| smart-question-generation | 学科题库 | 同科同事浏览题库 | 弱候选 | check_question_bank | 同科同事可见题库 | 4 |
| smart-question-generation | 按配比组卷 | 手工替换为下架题 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-question-generation | 按配比组卷 | 按 3:5:2 组卷 | 仅文件级 | check_question_bank | （未定位到具体断言） | 5 |
| smart-question-generation | 按配比组卷 | 题库不足 | 弱候选 | check_question_bank | 题库不足 422 并列出缺口 | 3 |
| smart-question-generation | 来源片段与出处快照 | 原稿在入库后被替换 | 弱候选 | check_question_bank | 原图被替换后发布 409（指纹不一致） | 2 |
| smart-question-generation | 来源片段与出处快照 | 查看题目出处 | 弱候选 | check_question_bank | 答案卷出处带原文行号与摘录（与题目快照一致） | 2 |
| smart-question-generation | 流式进度与失败处理 | 同一教师重复点击生成 | 仅文件级 | check_question_bank | （未定位到具体断言） | 5 |
| smart-question-generation | 流式进度与失败处理 | 未配置模型 Key | 弱候选 | check_question_bank | 无 Key 返回 503 | 2 |
| smart-question-generation | 流式进度与失败处理 | 生成中模型超时 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-question-generation | 结构化输出与逐题校验 | 修补后仍不是合法 JSON | 弱候选 | check_question_bank | 用户消息以 JSON 数组重申标签 | 3 |
| smart-question-generation | 结构化输出与逐题校验 | 全部题目通过校验 | 弱候选 | check_question_bank | 全部通过 8 题落库 | 2 |
| smart-question-generation | 结构化输出与逐题校验 | 单反斜杠 LaTeX 被修补后通过 | 断言名候选 | check_question_bank | 单反斜杠 LaTeX：生成成功且题目保存 | 8 |
| smart-question-generation | 结构化输出与逐题校验 | 模型声明无依据的空位 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-question-generation | 结构化输出与逐题校验 | 模型返回不构成字面包含的细分说法 | 断言名候选 | check_question_bank | 非字面包含的细分术语：判超出范围 | 6 |
| smart-question-generation | 结构化输出与逐题校验 | 模型返回字面包含所选标签的表述 | 弱候选 | check_question_bank | 细分知识点：落库知识点为所选标签 | 3 |
| smart-question-generation | 结构化输出与逐题校验 | 漏网的控制字符被拦截 | 弱候选 | check_question_bank | U+000C 题干：原因为含不可见控制字符 | 3 |
| smart-question-generation | 结构化输出与逐题校验 | 细分知识点与所选知识点无关 | 断言名候选 | check_question_bank | 细分知识点：归一到所选知识点后通过 | 6 |
| smart-question-generation | 结构化输出与逐题校验 | 被误解码的公式命令被修补 | 弱候选 | check_question_bank | 提示词要求公式花括号成对并写完整命令 | 2 |
| smart-question-generation | 结构化输出与逐题校验 | 输出不是 JSON | 弱候选 | check_question_bank | 用户消息以 JSON 数组重申标签 | 3 |
| smart-question-generation | 结构化输出与逐题校验 | 部分题目不合格 | 弱候选 | check_question_bank | 部分不合格：6 通过 2 未通过 | 3 |
| smart-question-generation | 结构化输出与逐题校验 | 题干泄露答案 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-question-generation | 试卷定稿与分班发布 | 原图校验或文件写入失败 | 仅文件级 | check_question_bank | （未定位到具体断言） | 4 |
| smart-question-generation | 试卷定稿与分班发布 | 发布到两个任教班级 | 弱候选 | check_question_bank | 发布到两个班 200 | 4 |
| smart-question-generation | 试卷定稿与分班发布 | 发布参数边界 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-question-generation | 试卷定稿与分班发布 | 发布身份边界 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-question-generation | 试卷定稿与分班发布 | 批次混入非任教班级 | 断言名候选 | check_question_bank | 批次混入非任教班级 403 | 8 |
| smart-question-generation | 试卷定稿与分班发布 | 未确认核对或版本冲突 | 弱候选 | check_question_bank | 未确认核对 400 | 4 |
| smart-question-generation | 试卷定稿与分班发布 | 混合已有和新目标班级 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-question-generation | 试卷定稿与分班发布 | 草稿试卷发布 | 弱候选 | check_question_bank | 含图试卷发布 200 | 3 |
| smart-question-generation | 试卷定稿与分班发布 | 重复发布 | 弱候选 | check_question_bank | 重复发布复用作业 | 3 |
| smart-question-generation | 试卷定稿与分班发布 | 重复发布更换截止时间或遇到已关闭作业 | 弱候选 | check_question_bank | 重复发布复用作业 | 4 |
| smart-question-generation | 题目内容显示 | 代码中的下划线 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-question-generation | 题目内容显示 | 填空与解答题答案含公式 | 弱候选 | check_question_bank | 答案卷含答案与解析 | 2 |
| smart-question-generation | 题目内容显示 | 多空位填空题显示 | 弱候选 | check_question_bank | 判断题与填空题生成成功 | 2 |
| smart-question-generation | 题目内容显示 | 多空答案与选择判断答案 | 弱候选 | check_question_bank | 答案卷含答案与解析 | 2 |
| smart-question-generation | 题目内容显示 | 学生端打开已发布试卷 | 弱候选 | check_question_bank | 发布生成已发布命题作业 | 2 |
| smart-question-generation | 题目内容显示 | 空位与公式下标共存 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| smart-question-generation | 题目内容显示 | 编辑答案时显示原文 | 弱候选 | check_question_bank | 答案卷出处带原文行号与摘录（与题目快照一致） | 2 |
| smart-question-generation | 题目内容显示 | 解答题作答横线不变 | 弱候选 | check_question_bank | 蓝图解答题在前、单选在后：组卷成功 | 2 |
| smart-question-generation | 题目内容显示 | 选项含公式 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| student-workspace | 作业界面先展示演示结果 | 浏览演示作业结果 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| student-workspace | 助手对话保留真实会话能力 | 从助手页连续追问 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| student-workspace | 助手对话保留真实会话能力 | 查看回答来源 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| student-workspace | 学情分析演示界面 | 浏览学习画像演示 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| student-workspace | 学生作业历史持续可查 | H1 提交后进入历史并可刷新 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| student-workspace | 学生作业历史持续可查 | H2 关闭后保留终评及配图 | 弱候选 | check_homework | S3 失败：关闭后提交 → 400 | 2 |
| student-workspace | 学生作业历史持续可查 | H3 历史读取隔离与失败 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| student-workspace | 学生作业历史持续可查 | H4 空历史与时间边界 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| student-workspace | 学生导航与路由 | 无效视图回退 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| student-workspace | 学生导航与路由 | 资料页返回其他模块 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| student-workspace | 学生导航与路由 | 首页进入助手对话 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| student-workspace | 学生本地搜索与提问历史 | 助手历史不自动发送 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| student-workspace | 学生本地搜索与提问历史 | 搜索后刷新与再次使用 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| student-workspace | 学生本地搜索与提问历史 | 科目和账号隔离 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| student-workspace | 学生身份与班级上下文 | 学生首页展示本人班级 | 弱候选 | check_analytics | S3 失败：学生访问班级学情 → 403 | 2 |
| student-workspace | 学生身份与班级上下文 | 未分班学生访问 | 弱候选 | check_analytics | S3 失败：学生访问班级学情 → 403 | 3 |
| student-workspace | 本班讲义列表与检索界面 | 学生搜索本班讲义 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| student-workspace | 本班讲义列表与检索界面 | 学科标签过滤资料卡 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| student-workspace | 本班讲义列表与检索界面 | 预览和下载实际资料 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| student-workspace | 本班首页概览 | 浏览首页概览 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| student-workspace | 讲义页科目切换布局稳定 | 从有资料切到空科目 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| student-workspace | 讲义页科目切换布局稳定 | 搜索加载与恢复 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| student-workspace | 错题界面及助手跳转 | 由错题进入助手 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| teacher-identity-and-permissions | 双重身份权限判定规则 | 同一教师不同模块权限不同 | 别名候选 | check_lesson10_p0_scenarios | P0 接口：题库/组卷模块校验任教学科（subject），班级模块校验任教班级（teaching_classes） | 1 |
| teacher-identity-and-permissions | 学生密码重置仅限本班班主任 | 任课教师调用重置接口被拒 | 弱候选 | check_baseline | R2 失败：学生调用教师接口 → 403 且带请求标识 | 3 |
| teacher-identity-and-permissions | 学生密码重置仅限本班班主任 | 班主任重置本人带班学生密码 | 别名候选 | check_lessons_2_5 | auth.homeroom_reset | 2 |
| teacher-identity-and-permissions | 教师学科身份 | 教师学科身份随 JWT 生效 | 弱候选 | check_baseline | R3 失败：缺少 JWT_SECRET_KEY → 非零退出并提示键名 | 2 |
| teacher-identity-and-permissions | 教师学科身份 | 教师登录进入本学科教研组 | 弱候选 | check_analytics | S3 失败：教师跨学科访问 → 403 | 2 |
| teacher-identity-and-permissions | 教研资料按学科隔离 | 数学教师访问数学教研资料成功 | 弱候选 | check_analytics | S3 失败：教师跨班访问 → 403 | 2 |
| teacher-identity-and-permissions | 教研资料按学科隔离 | 数学班主任跨学科访问英语资料被拒 | 弱候选 | check_analytics | S3 失败：教师跨学科访问 → 403 | 4 |
| teacher-identity-and-permissions | 教研资料按学科隔离 | 跨学科教研资料不可见 | 弱候选 | check_analytics | S3 失败：教师跨学科访问 → 403 | 2 |
| teacher-identity-and-permissions | 班主任身份不随工作区消失 | 任课教学保留班主任模块 | 弱候选 | check_analytics | S1 正常：班主任查看本班全科 101 学情 | 2 |
| teacher-identity-and-permissions | 班主任身份与跨学科本班学情特权 | 任课老师仅看本学科成绩 | 仅文件级 | check_analytics | （未定位到具体断言） | 5 |
| teacher-identity-and-permissions | 班主任身份与跨学科本班学情特权 | 班主任查看其他班级学情被拒 | 弱候选 | check_analytics | S1 正常：班主任查看本班全科 101 学情 | 5 |
| teacher-identity-and-permissions | 班主任身份与跨学科本班学情特权 | 班主任查看本班全科学情 | 断言名候选 | check_analytics | S1 正常：班主任查看本班全科 101 学情 | 9 |
| teacher-identity-and-permissions | 班级管理边界 | 任课老师仅见任教班级名单 | 弱候选 | check_lesson10_p0_scenarios | P0 前端：教师未分配任教班级时存在空状态提示 | 3 |
| teacher-identity-and-permissions | 班级管理边界 | 班主任可见本班全部学生 | 弱候选 | check_analytics | S1 正常：班主任查看本班全科 101 学情 | 4 |
| teacher-workspace | 两种学生名单的操作差异 | 同一教师在任课页不展示重置操作 | 仅文件级 | check_lesson10_p0_scenarios | （未定位到具体断言） | 6 |
| teacher-workspace | 两种学生名单的操作差异 | 班主任学生页展示重置操作 | 别名候选 | check_lessons_2_5 | auth.homeroom_reset | 2 |
| teacher-workspace | 任课与带班上下文独立 | 切换任课班级不切换带班班级 | 弱候选 | check_lesson10_p0_scenarios | P0 接口：任教班级与带班班级均由服务端令牌/数据库派生（不采信客户端参数） | 3 |
| teacher-workspace | 任课管理的单科资料列表 | 切班后保留资料视图 | 弱候选 | check_teacher_navigation | R3 正常：切班保留现有页面行为  | 2 |
| teacher-workspace | 任课管理的单科资料列表 | 发布与查看入口分开 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| teacher-workspace | 任课管理的单科资料列表 | 查看当前任教班级本科目资料 | 弱候选 | check_teacher_navigation | R1 边界：没有任教班级仍只有三项教研入口 | 3 |
| teacher-workspace | 全科总览与单科教学入口区分 | 在教研组内选择教师版发布学生稿 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| teacher-workspace | 全科总览与单科教学入口区分 | 打开未接入的学情或教研模块 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| teacher-workspace | 全科总览与单科教学入口区分 | 智能命题不再是占位 | 弱候选 | check_teacher_navigation | R3 正常：资料、备课、命题点击仍到原路径，移除项不再可导航 | 2 |
| teacher-workspace | 全科总览与单科教学入口区分 | 班主任进入全科资料总览 | 弱候选 | check_analytics | S1 正常：班主任查看本班全科 101 学情 | 3 |
| teacher-workspace | 助手配置独立入口及菜单顺序 | 在助手配置页切换班级 | 仅文件级 | check_lessons_2_5 | （未定位到具体断言） | 4 |
| teacher-workspace | 助手配置独立入口及菜单顺序 | 检查系统菜单顺序 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| teacher-workspace | 教师共用工作空间导航 | 教师打开资料页仍可访问其他模块 | 弱候选 | check_analytics | S3 失败：教师跨班访问 → 403 | 2 |
| teacher-workspace | 教师共用工作空间导航 | 教师进入智能命题页 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| teacher-workspace | 教师教研占位入口移除 | R1 教研中心只有三个现有入口 | 弱候选 | check_teacher_navigation | R1 边界：没有任教班级仍只有三项教研入口 | 5 |
| teacher-workspace | 教师教研占位入口移除 | R2 旧教研链接有明确落点 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| teacher-workspace | 教师教研占位入口移除 | R3 其他导航与班级不退化 | 弱候选 | check_teacher_navigation | R3 边界：其他view保持原值 ${JSON.stringify(view)} | 2 |
| teacher-workspace | 教师页移除快捷切换账号 | 教师检查顶栏 | 无匹配断言 |  | （同能力有检查文件但无相近断言） | 0 |
| teacher-workspace | 本地预览包含静态资源 | standalone 服务交付登录样式 | 断言名候选 | check_lessons_2_5 | citations.changed_file_stale_index_excluded | 6 |
| teacher-workspace | 本班审计日志页面与接口 | 任课身份或跨班审计被拒绝 | 别名候选 | check_lessons_2_5 | auth.audit_logs_class_isolation | 2 |
| teacher-workspace | 本班审计日志页面与接口 | 班主任查看本班日志 | 断言名候选 | check_analytics | S1 正常：班主任查看本班全科 101 学情 | 6 |
| teacher-workspace | 班主任模块按身份常驻 | 任课教学保留班主任入口 | 弱候选 | check_analytics | S1 正常：班主任查看本班全科 101 学情 | 2 |
| teacher-workspace | 班主任模块按身份常驻 | 非班主任只显示任课与教研功能 | 弱候选 | check_lesson10_p0_scenarios | P0 前端：忘记密码显示「请联系班主任重置」提示 | 3 |
