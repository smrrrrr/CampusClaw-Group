# Why

用户要求去掉教研问答和课例分析。当前两项只有共用教师侧栏入口和占位展示，没有独立后端接口或持久数据；移除可减少无实际用途的菜单。

# What Changes

- 所有教师页面的教研中心只保留教研组资料、智能备课、智能命题。
- 访问旧view=research-qa或case-analysis时进入现有智能备课页。
- 同步工作区及权限主规约，去除两项仍应存在的表述。
- 不改其他功能的权限、接口、账号、成绩、作业历史、模型配置及数据；不清库。

# Capabilities

## Modified Capabilities
- teacher-workspace：精简共用导航，处理旧链接。
- teacher-identity-and-permissions：教研权限枚举与当前功能一致。
- rbac-role-permissions：角色功能枚举同步。

# Impact

仅前端导航、教师查询参数处理、规约文档与导航回归。更新当前8083前端；其他部署不动。
