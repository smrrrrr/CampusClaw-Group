# 镜像无源码方案评审（任务 6.1）

- 日期：2026-11-14
- 口径依据：课程答复第 4 条——**要 0 源码**
- 结论：采用“全量编译为 legacy `.pyc` 后删除 `.py`”，已在本机实测启动与业务链路
- 性质：方案评审 + 实现记录；`.pyc` 可反编译，**不等于代码加密**

## 一、目标与边界

1. 最终镜像内 `find / -name "*.py"` 结果为 0，包含应用代码与 `.venv` 第三方包。
2. 不引入 PyInstaller/Nuitka 等大编译改造，保持 Dockerfile 级改动。
3. `.pyc` 仍是字节码，可被反编译；课程若要求“不可逆向”，需另做混淆/加密，超出本轮。

## 二、方案对比

| 方案 | 做法 | 优点 | 风险 | 结论 |
| --- | --- | --- | --- | --- |
| A 仅应用无源码 | 编译 `/app/*.py` 后删除 | 改动小 | 第三方仍有 `.py`，不满足“0 源码” | 不采用 |
| **B 全量 `.pyc`** | `compileall -b` 编译 `/app` 与 `.venv`，删除所有 `.py` | 无 `.py`；不改依赖；构建阶段完成 | 构建变慢；极少数包可能依赖 `.py` 数据文件；可反编译 | **采用** |
| C 打包器 | PyInstaller/Nuitka | 产物最封闭 | 大改构建、调试困难、镜像行为变化 | 不采用 |

## 三、实验记录

| 实验 | 操作 | 结果 |
| --- | --- | --- |
| A 应用层 | 仅编译 `/app/*.py` 并删除 | 0 个 `.py`、33 个 `.pyc`，`/api/health` 200 |
| B 首次全量 | `compileall -b /app/.venv` 后删除全部 `.py` | **失败**：`ImportError: cannot import name 'auth' from 'routers'`，原因是只编译了顶层，`routers/*.py` 被删但未编译 |
| B 修正 | `compileall -b /app` 递归编译后再删除 | 0 个 `.py`、1468 个 `.pyc`、`routers/__init__.pyc` 存在；启动正常、登录 200、`/api/materials` 200、上传 200、索引 1 块、`retrieve_top_k` 命中 |

关键教训：必须**递归编译整个 `/app`**，包括 `routers/` 等包子目录；仅编译顶层会导致包识别失败。

## 四、实施

在 `backend/Dockerfile` 运行层、移除开发材料之后加入：

```dockerfile
RUN /app/.venv/bin/python -m compileall -b -q /app >/dev/null 2>&1 \
    && find /app -name "*.py" -delete
```

顺序要求：

1. 必须在 `COPY . .` 与开发材料清理之后，避免删完又被覆盖。
2. 必须在 `chown` 之前以 root 执行，避免权限问题。
3. 不删除 `__pycache__`，保留双份字节码以降低兼容风险。

## 五、验证要求

| 检查 | 通过信号 |
| --- | --- |
| 镜像内 `.py` 计数 | `find / -name "*.py" -not -path "/proc/*" \| wc -l` = 0 |
| 启动 | 容器 `Application startup complete`，`/api/health` 200 |
| 业务 | 登录 200、材料列表 200、上传 200、索引成功、检索命中 |
| 门禁 | `make check` 与本改动无关，仍需全绿 |

## 六、风险与回滚

1. **可反编译**：`.pyc` 不是加密；若课程要求更强保护，需重新评审。
2. **构建时间**：`compileall` 全量约 1–2 分钟，CI 镜像构建变慢。
3. **数据文件依赖**：少数包若在运行时按 `__file__` 找 `.py`，会在特定功能上报错；本机已验证登录/材料/上传/索引/检索，其余功能需回归。
4. **回滚**：删除该 `RUN` 行并重建镜像即可恢复含 `.py` 版本。

## 七、结论

方案 B 满足“镜像 0 源码”的字面要求且不引入打包器；代价是构建变慢与可反编译。

## 八、实施与验证结果（2026-11-15）

Dockerfile 实际加入三步：递归编译 `/app` 与 `/usr/local/lib/python3.12`、删除所有 `.py`、删除 GCC 调试辅助脚本，末尾以 `test` 断言 `.py` 计数为 0。

| 验证项 | 实测 |
| --- | --- |
| 镜像内 `.py` 总数 | **0**（`find / -name "*.py" -not -path "/proc/*"`） |
| `.pyc` 数量 | 1468 |
| `main.pyc` / `routers/__init__.pyc` | 均存在 |
| `dev_seed.pyc` | 不存在（开发材料已在编译前删除） |
| 启动 | `Application startup complete` |
| `/api/health` | 200 |
| `/docs`（ENABLE_DOCS=true） | 200 |
| 登录 | 200，token 长度 396 |
| `/api/materials?class_id=102` | 200 |
| 上传材料 | 200 |
| 索引 | 成功写入分块 |
| `retrieve_top_k` | 命中 2 条，首位 `nosrc-mat.md` |
| `make check` | 41/41 PASS |

关键补充：系统 Python 标准库与 GCC 调试脚本必须一并处理，否则 `find /` 仍会残留 1102 + 5 个 `.py`，只处理 `/app` 无法满足“0 源码”。

## 九、Docker 可用后的当前提交复验（2026-11-16）

以工作区分支最新提交重建三个业务镜像并重建七服务栈后实测：

| 验证项 | backend | mcp-tools | frontend |
| --- | --- | --- | --- |
| 镜像内 `.py` | **0** | **0** | **0**（已删除基础镜像 npm/node-gyp 与 lldb 脚本） |
| 镜像内 `.pyc` | 2612 | 1598 | 0 |
| 测试文件 | 0 | 0 | 0 |
| OCI `revision` | 与提交一致 | 与提交一致 | 与提交一致 |
| 启动 | healthy，`/api/health` 200 | healthy，`/health` 200 | healthy，`/login` 200 |

前端运行层只保留 `node server.js`；基础镜像 `node:22-alpine` 自带的 `/usr/local/lib/node_modules/npm`（含 node-gyp 的 Python 脚本）与 `/usr/local/share/doc/node/lldb_commands.py` 已删除，并以 `test "$(find / -name '*.py' | wc -l)" -eq 0` 在构建期断言。

同一轮发现并修复：`grading-worker`/`grading-dispatcher` 仍按脚本路径启动 `grading_worker.py`，而运行层已删除 `.py`，导致两容器反复退出。已改为 `python -m grading_worker --mode …`（legacy `.pyc` 可直接导入），并在 `check_lesson10_scenario_gaps.py` 增加静态断言防止回归。

删除源码前新增构建期 `.source-sha256.json`（只含应用 `.py` 的相对路径与 SHA-256，不含源码），用于核对“镜像是否由当前源码构建”；`scripts/reproduce_async_grading.py` 改为读取该清单，不再按源码文件路径哈希。证据见 `reports/lesson-10/20261116T161500Z-docker/no-source.txt`。

同一提交又在全新空目录（独立 compose 项目、端口 8097）重建并启动七服务，三镜像容器内 `.py` 仍为 0，OCI revision 与提交一致；证据见 `reports/lesson-10/20261116T024000Z-clone-registry-rollback/clone-no-source.txt`。这是换目录复验，不是换机。
