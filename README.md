# CampusClaw 小组项目

教师备课与学生学习平台，使用 FastAPI、SQLite、Next.js 和 Docker Compose。

当前已实现学科教师助手、解题引导、多轮流式对话、班级资料与引用核对、教研组资料、智能备课、定稿及学生稿分班发布。功能范围和待实现事项见 [OpenSpec 索引](openspec/README.md)。

## 启动与交接

1. 克隆本小组仓库：`https://github.com/smrrrrr/CampusClaw-Group.git`。
2. 参考根目录 `.env.example` 创建 `.env`，填写随机 JWT 密钥；使用真实 AI 生成时填写服务端 DeepSeek Key。
3. 启动 Docker Desktop，在项目根目录运行 `docker compose up -d --build`。
4. 默认入口为 `http://localhost:8080/login`；已有其他项目占用端口时，在 `.env` 设置 `CAMPUSCLAW_PORT=8081`。

完整部署、空开发库初始化及种子账号说明见 [DEPLOYMENT.md](DEPLOYMENT.md)。数据库不会随源码分发，也不会在启动时自动初始化演示账号；只在确认是空的开发库时按文档运行种子脚本，已有数据库不能为更新代码重跑种子。

真实 `.env`、数据库及日志、上传资料、教学素材包、依赖、构建产物和本地验证证据均不纳入版本管理。每位组员自行配置本地环境，业务数据如需交接应另行备份迁移。

## 规约与验证

- [功能及规约](openspec/README.md)
- [最近规约校验](openspec/validation-2026-10-20.md)
- `apitest/`：隔离回归脚本及虚构模型试跑入口；显式真实 AI 试跑会访问服务端配置的模型并产生调用费用。
