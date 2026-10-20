# material-upload Specification

## Purpose

为 CampusClaw 提供材料上传入库行为契约，覆盖教师上传权限、文件类型与大小限制、上传元数据与班级选择、文件存储策略、重名与异常处理、知识库索引关联、材料数据隔离与审计、下载与预览，确保资料管理在权限边界和班级隔离内安全运行，并为 AI 解题助手提供可检索的知识库素材。

## Implementation Status

2026-10-16 同步现有材料变更规约。列表、预览、下载和教师资料入口已接入；MD/TXT 与 PDF 公式降级代码已存在，其专门验收任务仍按原 tasks.md 的未勾选项处理。本次文档同步未重新执行上传、删除或 Docker 持久化测试。学生端资料卡与学科元数据过滤见 student-workspace；班主任只读总览为前端入口限制，不代表后端已完成跨学科细粒度资料授权。

## Requirements

### Requirement: 教师上传权限控制

系统 MUST 仅允许教师（role=teacher）上传资料。学生（role=student）MUST 仅具备查看和下载权限，MUST NOT 拥有上传入口。后端上传接口 MUST 通过 Depends(get_current_teacher) 拦截，非教师角色调用 MUST 返回 403 Forbidden。

#### Scenario: 教师上传资料成功

- **WHEN** role=teacher 的教师登录后访问上传页面，选择文件并提交上传
- **THEN** 系统接受上传请求，处理文件并存储

#### Scenario: 学生尝试上传被拒

- **WHEN** role=student 的用户尝试访问上传接口
- **THEN** get_current_teacher 依赖校验失败，返回 403 Forbidden，记录审计日志

#### Scenario: 学生前端无上传入口

- **WHEN** role=student 的用户查看材料页面
- **THEN** 前端不展示上传按钮或上传入口

### Requirement: 文件类型与大小限制

系统 MUST 仅允许以下文件格式：PDF、PPTX、DOCX、JPG、PNG、MD、TXT。单文件大小上限 MUST 为 50MB。前端 MUST 通过 accept 属性做初步限制。后端 MUST 校验真实的 MIME 类型（不信任文件扩展名）和文件大小，不合规 MUST 返回 400 Bad Request。MD/TXT 为纯文本、无 magic number，后端 MUST 以「内容可解码为 UTF-8 且不含 NUL 字节」判定真实性，拦截二进制文件伪装成文本。

#### Scenario: 上传允许格式的文件成功

- **WHEN** 教师上传一个 PDF 文件（大小 10MB）
- **THEN** 后端校验 MIME 类型为 application/pdf，大小未超限，接受上传

#### Scenario: 上传超大文件被拒

- **WHEN** 教师上传一个 51MB 的 PDF 文件
- **THEN** 后端校验文件大小超过 50MB 上限，返回 400 Bad Request

#### Scenario: 上传不允许的格式被拒

- **WHEN** 教师上传一个 .exe 文件
- **THEN** 后端校验 MIME 类型不在允许列表中，返回 400 Bad Request

#### Scenario: 伪造扩展名被后端 MIME 校验拦截

- **WHEN** 教师将一个 .exe 文件重命名为 .pdf 后上传
- **THEN** 后端校验真实 MIME 类型为 application/x-msdownload 而非 application/pdf，返回 400 Bad Request

#### Scenario: 前端 accept 属性初步限制

- **WHEN** 教师在文件选择器中选择文件
- **THEN** 前端 accept 属性仅显示 PDF/PPTX/DOCX/JPG/PNG/MD/TXT 格式的文件，其他格式不可选

### Requirement: 上传元数据与班级选择

教师上传资料时前端 MUST 提供班级选择器，展示该教师 teaching_classes 中的所有任教班级。上传 MUST 附带元数据：文件名、所属 class_id、上传者 user_id、上传时间、文件描述/标签、file_path。后端 MUST 校验目标 class_id 是否在教师 JWT Payload 的 teaching_classes 范围内，不在则返回 403 Forbidden。

#### Scenario: 教师选择任教班级上传成功

- **WHEN** 教师 teaching_classes=[101,102]，选择班级 101 上传一份资料并填写描述和标签
- **THEN** 系统校验 class_id=101 在 teaching_classes 中，接受上传，记录完整元数据

#### Scenario: 多班级教师班级选择器展示所有任教班级

- **WHEN** 教师 teaching_classes=[101,102,103]，打开上传页面
- **THEN** 前端班级选择器展示班级 101、102、103 三个选项

#### Scenario: 教师篡改 class_id 上传非任教班级被拒

- **WHEN** 教师 teaching_classes=[101,102]，尝试在请求中传入 class_id=201 上传资料
- **THEN** 后端校验 201 不在 teaching_classes 中，返回 403 Forbidden

#### Scenario: 上传元数据完整记录

- **WHEN** 教师上传成功后查询材料记录
- **THEN** Material 表记录包含 class_id、uploader_id、filename、file_path、file_type、file_size、description、tags、is_indexed（初始为 false）、created_at

### Requirement: 文件存储策略

系统 MUST 将文件元数据存储在 SQLite 的 Material 表中，文件本体 MUST 存储在 Docker 挂载的宿主机目录（/app/uploads/）中。系统 MUST NOT 将文件二进制流直接存入 SQLite。docker-compose.yml MUST 明确挂载卷 ./backend/uploads:/app/uploads，确保容器重启后文件不丢失。

#### Scenario: 文件存储在挂载目录

- **WHEN** 教师上传一份资料，系统处理完成后
- **THEN** 文件本体存储在 /app/uploads/ 目录中，Material 表中 file_path 字段记录存储路径

#### Scenario: SQLite 仅存储元数据

- **WHEN** 查询 Material 表记录
- **THEN** 表中不包含文件二进制流字段，仅包含元数据字段

#### Scenario: 容器重启后文件不丢失

- **WHEN** Docker 容器重启后教师查询已上传的资料
- **THEN** 文件元数据在 SQLite 中完好，文件本体在 /app/uploads/ 卷挂载目录中完好，可正常下载

#### Scenario: 文件按 class_id 分子目录存储

- **WHEN** 教师上传资料到班级 101
- **THEN** 文件存储在 /app/uploads/101/ 子目录下，便于按班级管理文件

### Requirement: 文件重名与异常处理

系统 MUST NOT 覆盖同名文件，MUST 自动重命名（如加时间戳前缀 1620000000_filename.pdf）。若文件写入成功但数据库记录写入失败，系统 MUST 删除已写入的物理文件（回滚）。网络中断时前端 MUST 提供重试按钮。系统 MUST 对上传文件做基础文件头校验，拒绝含有恶意脚本或伪造文件头的文件。

#### Scenario: 同名文件自动重命名

- **WHEN** 教师上传文件名为"lesson1.pdf"的资料，且 /app/uploads/101/ 下已存在同名文件
- **THEN** 系统自动重命名为 1620000000_lesson1.pdf（时间戳前缀），不覆盖原文件

#### Scenario: DB 写入失败时回滚删除物理文件

- **WHEN** 文件已写入 /app/uploads/ 但 Material 表记录写入失败（如 SQLite 异常）
- **THEN** 系统删除已写入的物理文件，返回上传失败提示，不留下孤立文件

#### Scenario: 网络中断前端提供重试

- **WHEN** 教师上传文件时网络中断，请求未到达后端或响应未返回
- **THEN** 前端展示"上传失败，请重试"提示和重试按钮，教师点击后重新发起上传

#### Scenario: 恶意文件头校验不通过被拒

- **WHEN** 教师上传一个扩展名为 .pdf 但文件头不是 %PDF 的文件
- **THEN** 后端校验文件头不匹配 PDF 格式，返回 400 Bad Request，拒绝上传

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

### Requirement: 材料数据隔离

学生 MUST 只能查询和下载自己所在班级（class_id）的材料。教师 MUST 只能查询和下载自己任教班级（teaching_classes）的材料。后端查询 MUST 带 WHERE class_id 隔离条件。任何越权尝试（篡改 class_id 查询或下载其他班材料）MUST 返回 403 Forbidden 并记录审计日志。

#### Scenario: 学生查询本班材料成功

- **WHEN** 学生 class_id=101 请求查看材料列表
- **THEN** 系统返回 class_id=101 的材料，查询带 WHERE class_id = :current_class_id

#### Scenario: 教师查询任教班级材料成功

- **WHEN** 教师 teaching_classes=[101,102] 请求查看材料列表
- **THEN** 系统返回 class_id IN (101,102) 的材料

#### Scenario: 学生篡改 class_id 查询被拒

- **WHEN** 学生 class_id=101，尝试在请求中传入 class_id=102 查询材料
- **THEN** 系统以 JWT 中的 class_id=101 为准，返回 403 Forbidden，记录审计日志

#### Scenario: 学生尝试下载其他班材料被拒

- **WHEN** 学生 class_id=101，尝试下载 class_id=102 的材料
- **THEN** 系统校验材料 class_id=102 与学生 class_id=101 不匹配，返回 403 Forbidden，记录审计日志

### Requirement: 下载与预览

前端 MUST 将教师资料表格及学生资料卡的操作统一为“预览与下载”，列表不再单列下载按钮。该入口 MUST 对全部资料格式可用：PDF/图片/Markdown/纯文本可在线预览，其他格式提示下载查看。预览窗口 MUST 为 Markdown 提供“下载图文包”，为其他格式提供“下载原文件”；支持的文本讲义保留“打印／另存为 PDF”。PNG/JPG 以图片渲染、PDF 以 iframe 渲染、MD/TXT 以纯文本拉取并用 MarkdownAnswer（react-markdown + KaTeX）渲染，使含 LaTeX 公式的讲义以数学符号展示；PPTX/DOCX 暂不支持预览并提示下载查看。下载接口 MUST 校验当前用户的 class_id（学生）或 teaching_classes（教师）是否与材料的 class_id 匹配，不匹配 MUST 返回 403 Forbidden。引用原文下载 MUST 携带可选 expected_sha256（64 位小写十六进制），后端在权限校验后核对文件，不一致 MUST 返回 409 并提示版本变化；普通资料下载可不带该参数。

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

### Requirement: 教师删除资料

教师(role=teacher) MUST 能够删除自己所任教班级已上传的资料（删除后，学生/其他教师均不可再访问该材料）。删除 MUST 同时移除：Material 记录、所属 MaterialContent（纯文本解析内容）、所属 MaterialChunk（分块向量）、以及磁盘上的物理文件。删除接口 MUST 通过 Depends(get_current_teacher) 拦截，学生 MUST 无删除权限，调用 MUST 返回 403 Forbidden。删除前 MUST 校验目标材料的 class_id 在当前教师 JWT teaching_classes 范围内，不在范围 MUST 返回 403 Forbidden 并记录审计日志。若数据库记录删除失败，系统 MUST NOT 删除物理文件（避免产生孤立/不可追踪文件）；成功删除后 MUST 记录审计日志。

#### Scenario: 教师删除任教班级资料成功

- **WHEN** 教师 teaching_classes=[101,102] 登录后对 class_id=101 的某份资料发起删除
- **THEN** 后端校验该材料 class_id=101 在 teaching_classes 中，删除 Material 记录及其 MaterialContent/MaterialChunk，并删除磁盘物理文件，返回删除成功

#### Scenario: 删除后资料不可再访问

- **WHEN** 教师成功删除某资料后，学生或教师再尝试下载/预览/查询该资料
- **THEN** 系统返回 404 Not Found（记录已不存在），且 AI 检索不再召回该资料的任何分块

#### Scenario: 教师尝试删除非任教班级资料被拒

- **WHEN** 教师 teaching_classes=[101,102] 尝试对 class_id=201 的资料发起删除
- **THEN** 后端校验 201 不在 teaching_classes 中，返回 403 Forbidden，记录审计日志，不删除任何数据

#### Scenario: 学生尝试删除资料被拒

- **WHEN** role=student 的用户尝试调用删除接口
- **THEN** get_current_teacher 依赖校验失败，返回 403 Forbidden，记录审计日志

#### Scenario: 前端仅教师展示删除入口

- **WHEN** 学生或教师的班主任全科总览查看材料列表
- **THEN** 前端不展示删除按钮；删除按钮仅在 role=teacher 且处于任课教学上下文时展示，点击前弹确认提示
