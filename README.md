# CampusClaw

面向中学教师和学生的 AI 教学平台。教师用它导入教研资料、生成教案和学生讲义、出题组卷；学生在本班资料范围内向学科助手提问，回答附带可核对的出处。

当前版本：**v1.1**（2026-10-25），见文末[版本记录](#版本记录)。

## 功能

**教师端**

- **教研组资料**：导入教师版 Markdown 或图文 ZIP，同学科共享。系统生成去答案的学生版，经教师核对后发布到多个班级。
- **智能备课**：从组内资料生成教师教案，可编辑、按章节重写；审阅后定稿，保留版本。由定稿生成学生可见教案和配套讲义，人工核对后分班发布。定稿可以主动共享给教研组。
- **智能命题**：入口 `/teacher/quiz`。
  - 出题：按“知识点 × 题型 × 难度”生成结构化题目，逐题自动校验。
  - 复核：教师逐题通过、修改或驳回，通过的题进入学科题库。
  - 组卷与发布：按配比组卷，定稿后把去答案的学生卷分班发布，另附答案卷。
- **学科助手配置**：每位教师按班级配置自己学科的助手，包括提示词、解题引导开关和技能文件。
- **MCP 工具**：登记自建的 MCP 工具服务器并连接、发现工具。技能文件用 `工具名@服务器名` 引用工具。
- **班主任**：管理本班学生名单、重置学生密码、查看本班审计记录。

**学生端**

- **学科助手**：多轮对话，流式输出（SSE）。
  - 解题引导：分步提示和概念解释，不直接给出答案。
  - 范围：只检索本班本学科的已发布资料，回答里的引用编号可以和原文摘录对照。
  - 工具：命中教师配置的技能时，服务端会调用 MCP 工具，回答上方显示调用状态。
- **本班资料**：浏览和下载已发布的讲义、教案和试卷，支持浏览器打印或另存为 PDF。
- **快捷历史**：最近的搜索和提问保存在当前浏览器，可以一键重搜。

**通用**

- **账号与权限**：学号或工号加密码登录，首次登录强制改密，连续失败会锁定。权限按角色、学科、班级隔离，全部在服务端判定。
- **公式与配图**：KaTeX 渲染公式；配图使用导入的原图，并核对 SHA-256 指纹。

作业批改、错题本和学情画像目前还是演示页面，后端尚未接入。完整的功能边界见 [openspec/README.md](openspec/README.md)。

## 技术栈

| 部分   | 技术                                                 |
| ---- | -------------------------------------------------- |
| 后端   | Python 3.12、FastAPI、SQLAlchemy、SQLite，依赖用 uv 管理    |
| 前端   | Next.js 14、React 18、Zustand、react-markdown + KaTeX |
| 模型   | OpenAI 兼容接口，默认 DeepSeek，也可配置为课程网关                  |
| 工具服务 | 自建 MCP 服务（JSON-RPC 2.0），见 `mcp-server/`            |
| 部署   | Docker Compose，Nginx 作为唯一对外入口                      |

## 快速开始

需要 Docker Desktop。

```bash
git clone https://github.com/smrrrrr/CampusClaw-Group.git
cd CampusClaw-Group
cp .env.example .env    # 至少填写 JWT_SECRET_KEY；需要 AI 生成时再填模型 Key
docker compose up -d --build
```

打开 <http://localhost:8080/login>。端口可以在 `.env` 的 `CAMPUSCLAW_PORT` 里修改。

新库启动时会自动建表，但没有任何账号。有两种初始化方式：

- **组内数据包**：用包里的恢复脚本导入组内开发数据。
- **空库**：运行一次种子脚本，创建演示账号。

两种方式的具体步骤、环境变量、数据备份和本地开发方法都在 [DEPLOYMENT.md](DEPLOYMENT.md)。**已有数据的库不要运行种子脚本**，它会重置学生账号。

## 目录结构

```text
backend/        FastAPI 后端：routers/ 是接口，*_service.py 是业务逻辑，models.py 是数据表
frontend/       Next.js 前端：app/ 是页面，lib/api.ts 是接口封装
mcp-server/     自建 MCP 工具服务
deploy/         Nginx 配置
apitest/        回归测试脚本与接口用例
openspec/       规约：specs/ 是现行主规约，changes/ 是变更提案、设计、任务和验收记录
docs/           验收与工作记录
```

## 开发

项目采用规约驱动开发：任何行为变更，先在 `openspec/changes/<变更名>/` 写好 proposal、design、spec 和 tasks，评审后再实现。验收以主规约中的 Scenario 为准。规则全文见 [CLAUDE.md](CLAUDE.md)。

```bash
openspec validate --all --strict --no-interactive
```

回归测试使用临时数据库和假模型，不访问真实数据，也不花模型额度。先在 `backend/` 下执行 `uv sync`，然后在项目根目录运行：

```bash
PYTHONPATH=backend backend/.venv/bin/python apitest/check_question_bank.py
```

每个脚本的覆盖范围见 [openspec/README.md](openspec/README.md#检查与交接)。

**不进 Git 的内容**：

- 真实的 `.env`、数据库、上传资料和教学素材包；
- 依赖和构建产物；
- 本地验证证据（`.review/`）。

组员之间用数据包交接数据。密钥只放在服务端环境变量里。

## 文档

- [DEPLOYMENT.md](DEPLOYMENT.md)：部署、环境变量、数据与备份、本地开发
- [openspec/README.md](openspec/README.md)：功能与规约索引
- [docs/work-and-validation-2026-10-25.md](docs/work-and-validation-2026-10-25.md)：v1.1 的代码工作、验证结果和未完成的检测
- [docs/lesson-2-5-acceptance-2026-10-18.md](docs/lesson-2-5-acceptance-2026-10-18.md)：第 2—5 课功能验收记录

## 版本记录

### v1.1（2026-10-25）

**新增**

- **MCP 工具集成**：
  - 新增 `mcp-tools` 服务，提供公式提示和单位换算两个工具，只给提示不给答案；
  - 教师可以登记、连接、发现和断开工具服务器，令牌加密存储且不回传；
  - 技能文件按 `工具名@服务器名` 引用工具；
  - 学生提问时由服务端调用工具，有次数上限和参数校验，每次调用都写审计。
- **智能命题**：生成、逐题校验、人工复核、学科题库、按配比组卷、定稿、学生卷分班发布、答案卷与审计。

**修复**

- **模型输出解析**：模型输出 LaTeX 单反斜杠时，命题和学生稿的 JSON 解析不再失败，控制字符也会被兜底处理。
- **题目渲染**：
  - 填空题的多个空位不再被当作加粗而消失；
  - 选项和答案里的公式能正常渲染。
- **命题公式校验**：公式 `$` 不成对或花括号不配对的题不再入库。
- **学生卷排版**：选择题选项每项单独一行。

**部署与配置**

- **新增环境变量**：
  - `MCP_AUTH_TOKEN`、`MCP_TOKEN_KEY`、`MCP_ALLOWED_HOSTS`；
  - `ENABLE_DOCS`；
  - `DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`：用于切换到课程网关等 OpenAI 兼容接口。
- **Swagger 默认关闭**：Nginx 转发 `/docs` 和 `/openapi.json`，`ENABLE_DOCS=false` 时返回 404。
- **重写 DEPLOYMENT.md**：新增数据包恢复、备份、MCP 和本地开发说明。

**规约**

- 新增主规约 `mcp-tool-integration`、`smart-question-generation`。
- 归档已完成的旧变更，修正几处会冲掉新规约的旧增量。`openspec validate --all --strict` 全部通过。

### v1.0（2026-10-20）

首个小组版本：

- 账号与权限、班级隔离；
- 学科教师助手：解题引导、多轮流式对话、引用核对；
- 资料上传与检索；
- 教研组资料；
- 智能备课及学生稿分班发布；
- 学生快捷历史；
- 运行可靠性：SQLite 日志模式、健康检查。
