# 换目录、registry 与备份回滚演练证据（2026-11-16）

- `clone-*`：当前提交 `984c4c8` 在全新空目录、独立 compose 项目、端口 8097 的构建与启动记录。证明换目录可复现，**不是换机**。
- `local-registry.txt`：本机 `registry:2`（127.0.0.1:5001）三镜像 push/pull 后的 RepoDigest、OCI revision 与 `.py=0` 复验。**不替代远端仓库/GHCR**。
- `backup-restore.txt`：演示库只读在线备份、恢复副本指纹（34 表行数、integrity、SHA-256）与 uploads manifest 对比。未修改真实库。
- `rollback-*`：上一 tag `37aecf9` 三镜像使用恢复副本在独立项目、端口 8098 启动并验证；演练后已清理。
- `main-after-health.*`：回滚演练后主栈仍为 `984c4c8` 的健康与 revision 复核。

本目录只含计数、哈希、镜像标识与状态，不含 `.env`、数据库、上传正文或令牌。
