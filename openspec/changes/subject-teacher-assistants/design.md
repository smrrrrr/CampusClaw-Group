## Configuration and Routing

教师接口从认证用户读取 teacher_id、当前数据库 subject，不信任客户端传入身份；class_id 必须在任教范围。配置按班级、学科、教师联合唯一，支持同科多教师分别保存。

学生接口以本人 class_id 为边界。新会话优先使用仍任教该班该学科的最近保存配置；无配置时使用编号最小的任课教师及默认助手。会话绑定 teacher_id 后不因其他教师保存配置而切换；绑定关系失效返回 409，要求新建会话。学生查看历史时读取该会话绑定教师的当前配置。

没有保存配置时 student configured=false、tutor_enabled=false，界面明确提示默认助手。教师保存时开启解题引导仍使用固定框架替代自定义提示词，这是此前已确认保留的行为。

## Retrieval and History

Conversation 增加 subject（旧会话默认 math）和 teacher_id（旧会话首次续聊时绑定）。同一科目只列出本人的本班该科会话。每轮检索增加科目条件，材料科目仍由发布教师当前 User.subject 识别，不推断文件名标签；不实现材料学科历史快照。

多轮和旧单次问答接口均支持科目范围；旧 ai-history 为兼容保留的聚合日志，学生新页面只用分科会话。每日限额仍共用 AIQuestionLog，跨科共享 40 次。

## Migration and Validation

SQLite 旧 agent_configs 单列唯一表通过事务复制到新表，保留原 ID、教师、提示词、引导状态及时间，科目根据配置所属教师当前身份补齐。迁移可重复执行。旧会话补 subject=math 和空 teacher_id。

执行前通过 SQLite backup 保存当前数据库为 data/current/before-subject-assistants-20261018T133651186657.db。仅更新当前小组数据库 TEA002 的学科，不运行 dev_seed，不重置密码，不迁移个人项目或旧副本。
