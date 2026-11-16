# 交接数据说明（Next 15 升级，2026-11-16）

配套文档：[交接评审文档](handover-2026-11-16-next15.md)。本文件只回答“数据在哪、怎么恢复、哪些不能传”。

**这一版起，交接数据是一个离线数据包，不再只是哈希清单。** 此前 `handover-2026-11-16-next15.manifest.json` 与 `.data.json` 只记录文件哈希和状态，数据库、`.env`、上传正文都没有实体；现在这些内容打进 `handover-packs/2026-11-16-next15.zip`，走组内私有渠道传递，不进 Git。

## 一、数据包位置

| 项 | 值 |
| --- | --- |
| 解压目录 | `campusgroup/handover-packs/2026-11-16-next15/`（仓库外，与 Git 无关） |
| 压缩包 | `campusgroup/handover-packs/2026-11-16-next15.zip` |
| 规模 | 232 个文件，解压约 3.8 MB，压缩后约 1.1 MB |
| 校验值 | 与 zip 同目录的 `2026-11-16-next15.zip.sha256` |
| 重新生成 | `python3 -I -B dist/pack-build.py`（脚本在仓库内，`dist/` 已被 `.gitignore` 忽略） |

## 二、包内清单

| 路径 | 内容 | 是否含敏感数据 |
| --- | --- | --- |
| `db/campusclaw.db` | 本地 SQLite 2.1 MB；`users` 表仅 4 条：`TEA001`、`TEA002`、`20260001`、`20260002` | 是（演示账号哈希口令） |
| `env/.env` | 本机真实配置 481 B，含 JWT / 队列 / MCP / 模型密钥 | 是（密钥） |
| `env/.env.example` | 配置模板，密钥为空 | 否 |
| `uploads/` | 33 个文件：12 份 Markdown + 21 张配图，子目录 `101`/`102`/`research` | 是（材料正文） |
| `evidence/lesson-10/20261116T124118Z-next15/` | 第一批：基线、重锁、构建、镜像、隔离栈、HTTP 冒烟、双门禁、审计原文 | 已脱敏 |
| `evidence/lesson-10/20261116T215000Z-browser/` | 第二批：headless Chrome 页面检查、KaTeX、跨班 403/404、门禁复跑 | 已脱敏 |
| `evidence/security-evidence/` | `run.json`、`npm-audit.json`、`dependency-exceptions.json`、只读账号核查 | 已脱敏 |
| `evidence/reports/` | `next-risk-applicability.md`、`scenario-coverage.md`、`boot-reproduce.md` | 否 |
| `evidence/report.md` | 根报告快照 | 否 |
| `openspec/2026-11-16-upgrade-next-15-5-28/` | proposal / design / tasks / verification-plan | 否 |
| `docs/` | 交接说明、本文件、哈希清单、机器可读状态 | 已脱敏 |
| `patches/next15-code.patch` | 仅代码：`package.json`、`package-lock.json`、workflow、例外表 | 否 |
| `ci/ci-status.json` | 远端 CI run 状态 | 否 |
| `README.md`、`MANIFEST.json`、`SHA256SUMS.txt`、`verify.py` | 包说明、元数据、逐文件哈希、校验脚本 | 否 |

## 三、恢复步骤

```bash
# 1) 先校验完整性，不通过就不要用
python3 -I verify.py                 # 期望输出 OK

# 2) 放进仓库（注意目标路径）
cp db/campusclaw.db   <repo>/data/current/campusclaw.db
cp env/.env           <repo>/.env
cp -R uploads/.       <repo>/backend/uploads/

# 3) 确认四个演示身份
sqlite3 <repo>/data/current/campusclaw.db "select identifier, role from users;"

# 4) 双门禁
cd <repo> && make check && make check-security
```

`make check` 期望 41/41 PASS、exit 0；`make check-security` 期望 PASS、exit 0。缺库会以 `BLOCKED / exit 2` 结束，属范围未完成，不是漏洞红项。

## 四、校验方式

三层，任一层不符即视为包损坏或被改过：

1. `python3 -I verify.py` → `OK`（逐文件对 `SHA256SUMS.txt`）；
2. `shasum -a 256 2026-11-16-next15.zip` 对比同名 `.sha256`；
3. `MANIFEST.json` 里的提交号、分支、门禁状态应与仓库 `git log` 一致。

## 五、不入包、不入库

- 真实教学库全量数据、学生作业正文、任何令牌明文；
- 镜像 tar、容器卷、`node_modules`、构建产物；
- 真实模型调用日志。

## 六、传递边界

- 本包含 `.env` 与本地库，**只走组内私有渠道**；不要解压进公开仓库目录，不要提交，不要生成公开下载链接。
- 要交给组外，先轮换 `.env` 全部密钥，并删除 `env/.env` 后重新打包。
- 远端公开仓库里只有脱敏证据（演示标识替换为 `<demo-teacher-1>` 等占位符、绝对路径脱敏），与本包不重合。
