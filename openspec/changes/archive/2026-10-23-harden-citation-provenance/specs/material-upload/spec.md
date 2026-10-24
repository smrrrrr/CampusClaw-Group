## MODIFIED Requirements

### Requirement: 知识库索引关联

上传材料 MUST 异步解析、分块并生成向量，全部成功后才标记 is_indexed=true。索引 MUST 在解析前后计算文件 SHA-256；内容稳定且解析成功时持久化 source_sha256，解析期间文件变化或不可读 MUST 视为失败。AI 来源上下文 MUST 同时满足已索引及当前原文件指纹一致；解析失败材料 MUST NOT 被 AI 检索。升级 MUST 为既有 Material 表追加 nullable source_sha256，不删除历史数据；旧无指纹索引 MUST 由教师重新索引后才可引用。

#### Scenario: 上传成功后异步解析为纯文本

- **WHEN** 教师上传一份 PDF 资料成功，Material 记录创建后
- **THEN** 系统异步启动文本解析任务，将文件内容提取为纯文本存储

#### Scenario: 解析完成后标记 is_indexed 为 true

- **WHEN** 异步文本解析任务成功完成
- **THEN** 解析、分块和向量化成功且解析前后文件指纹一致时，记录 source_sha256 并更新 is_indexed=true

#### Scenario: 仅 is_indexed=true 的材料被 AI 检索

- **WHEN** AI 解题助手检索知识库素材作为上下文
- **THEN** AI 来源上下文仅包含 is_indexed=true 且 source_sha256 与当前文件一致的材料；无指纹、已变化或丢失的文件不提供引用

#### Scenario: 解析失败的材料保持未索引

- **WHEN** 异步文本解析任务执行失败（如文件损坏、格式不支持）
- **THEN** 系统将该材料的 is_indexed 保持为 false，记录失败原因，该材料不被 AI 检索

### Requirement: 下载与预览

前端 MUST 支持点击在线预览（PDF/图片/Markdown/纯文本）或下载材料。PNG/JPG 以图片渲染、PDF 以 iframe 渲染、MD/TXT 以纯文本拉取并用 MarkdownAnswer（react-markdown + KaTeX）渲染，使含 LaTeX 公式的讲义以数学符号展示；PPTX/DOCX 暂不支持预览并提示下载查看。下载接口 MUST 校验当前用户的 class_id（学生）或 teaching_classes（教师）是否与材料的 class_id 匹配，不匹配 MUST 返回 403 Forbidden。引用原文下载 MUST 携带可选 expected_sha256（64 位小写十六进制），后端在权限校验后核对文件，不一致 MUST 返回 409 并提示版本变化；普通资料下载可不带该参数。

#### Scenario: 引用原文的文件版本已变化

- **WHEN** 用户携带引用记录的 expected_sha256 请求原文件，但当前文件哈希不一致
- **THEN** 返回 409 并要求重新检索核对，前端显示错误而不将错误响应当作文件打开

#### Scenario: 学生在线预览 PDF 成功

- **WHEN** 学生 class_id=101 点击一份 PDF 材料的预览按钮
- **THEN** 前端校验材料 class_id=101 与学生 class_id=101 匹配，展示 PDF 在线预览

#### Scenario: 学生在线预览图片成功

- **WHEN** 学生 class_id=101 点击一份 JPG 材料的预览按钮
- **THEN** 前端展示图片在线预览

#### Scenario: 学生下载材料成功

- **WHEN** 学生 class_id=101 点击一份材料的下载按钮
- **THEN** 后端校验材料 class_id=101 与学生 class_id=101 匹配，返回文件流供下载

#### Scenario: 学生尝试下载其他班材料被拒

- **WHEN** 学生 class_id=101，尝试下载 class_id=102 的材料
- **THEN** 后端校验材料 class_id=102 与学生 class_id=101 不匹配，返回 403 Forbidden，记录审计日志

#### Scenario: 教师下载任教班级材料成功

- **WHEN** 教师 teaching_classes=[101,102] 下载 class_id=101 的材料
- **THEN** 后端校验 101 在 teaching_classes 中，返回文件流供下载
