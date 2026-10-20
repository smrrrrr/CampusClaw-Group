## ADDED Requirements

### Requirement: 任课管理的单科资料列表

任课管理 MUST 在“班级学生”之后提供“本班资料（单科）”入口，与“单科资料发布”分开。入口 MUST 使用 /materials?workspace=teaching&class_id=当前任教班级；页面及侧栏 MUST 高亮 subject-materials，展示已发布资料、索引状态与现有预览/下载操作。切换任教班级 MUST 保留资料页面、更新班级并重新加载列表，MUST NOT 回到学生页或混用先前班级异步返回结果。

列表 MUST 通过 subject_only=true 请求，由后端同时限定任教班级和当前教师学科。当前学科归类按发布教师的 User.subject 识别，包含同学科其他教师发布的资料，不依赖文件名或标签猜测学科；尚未建立独立的材料学科快照字段。未分配学科的教师或学生请求此教师专用过滤 MUST 返回 403。班主任全科列表及学生默认资料范围 MUST 保持原有行为。

#### Scenario: 查看当前任教班级本科目资料

- **WHEN** 数学教师在任课管理选择 102 班并进入本班资料（单科）
- **THEN** 只返回 102 班由数学教师发布的资料，不返回该班英语教师的资料，列表可预览和下载

#### Scenario: 切班后保留资料视图

- **WHEN** 教师在单科资料页将任教班级从 102 切换为 101
- **THEN** 保留 /materials 与 teaching 工作区，更新 class_id=101，仅显示 101 班本科目资料；无资料时显示空状态

#### Scenario: 发布与查看入口分开

- **WHEN** 教师打开单科资料发布页点击查看已发布资料
- **THEN** 进入同一班级的单科资料列表，侧栏高亮本班资料（单科），不再高亮发布菜单

## MODIFIED Requirements

### Requirement: 任课与带班上下文独立

任课管理 MUST 提供 `teaching_classes` 范围内的班级选择器，并包含班级学生、本班资料（单科）、学情分析（单科）、作业与改分、单科资料发布。任课链接 MUST 使用 `workspace=teaching`；班主任链接 MUST 使用 `workspace=homeroom`，并固定为本人 `homeroom_class_id`。任课切班 MUST NOT 改变班主任班级。无效任课 URL 班级值 MUST 回退到有效任教班级；前端路由参数 MUST NOT 赋予后端权限。

#### Scenario: 切换任课班级不切换带班班级

- **WHEN** 任教 101、102 且带班 101 的教师将任课下拉切到 102
- **THEN** 任课请求使用 102，班主任入口仍使用 101，后端继续校验各操作所需权限
