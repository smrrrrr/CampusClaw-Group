# Tasks

本清单全部为后续实施任务，本轮仅 propose，保持全部未勾选。版本探测的本次执行记录在 design.md，不把探测成功当作实施完成；不得执行 apply/archive、提交/推送或接触教学库。

## 1. 核实版本

- [x] 1.1 在实施当次复查 design.md Q1–Q9 的注册表、通告和 uv dry-run，记录时间、工具版本及输出；逐项确认目标仍可取得、未撤回且覆盖修复范围，失败项保留待确认。
- [x] 1.2 在获准的独立试验环境验证 PostCSS 8.5.18 override 与 Next 14.2.15 / Node 22，保存解析图、完整 build、CSS/source map/公式检查结果；全部通过才确认目标，否则阻断，不升级 Next/React。
- [x] 1.3 复核 python-pptx 1.0.2 的 Pillow>=3.3.2 约束、Pillow 13.0.0 的目标 Linux/Python wheel，以及 certifi 2026.10.19 与 PyJWT 2.15.1；以元数据和项目解析证据确认直接声明策略，无需 uv override。
- [ ] 1.4 完成 certifi MPL-2.0 与 Pillow MIT-CMU 的许可证判断/组内评审，登记独立评审人及证据；未获仓库规则要求的结论前不自行放行。
- [x] 1.5 保存实施前成套清单/锁文件哈希、代码版本、工具链和镜像 ID/digest，并盘点 33 个门禁子项；通过证据清单确认可追溯且测试目录未指向教学数据。

## 2. 改清单与等价适配

- [x] 2.1 按已确认目标更新前端 katex，增加 source-map-js 与 PostCSS 根 overrides；审查清单差异确认 Next/React/DOM 版本未变，PostCSS 不仍处于待确认状态。
- [x] 2.2 后端移除 python-jose[cryptography]，直接声明 PyJWT==2.15.1、certifi==2026.10.19、Pillow==13.0.0；核对 cryptography 显式依赖保留、python-pptx 与 MCP 清单无无关改动。
- [x] 2.3 按 design.md 的 JWT 兼容决策适配 security.py，保留导出异常、claims、HS256、type/token_type、iat/exp 秒边界及原有刷新/登出/数据库状态拦截；以 J1–J8 对照证明各入口 HTTP 行为相同。
- [ ] 2.4 在现有认证检查文件中补齐 J1–J8 正常/失败/边界断言，旧库仅作独立测试 oracle，运行产物不依赖它；用隔离故障注入证明至少篡改、过期和类型错用检查会变红，恢复后通过并留证。

## 3. 重锁

- [x] 3.1 使用固定 npm 工具链定向生成 package-lock（不手改、不全量 update），运行 npm ci、npm ls 与完整构建；确认所有 katex/PostCSS/source-map-js 锁路径均命中目标、无无关框架漂移。
- [x] 3.2 用 uv 0.13.5 定向重锁 backend/uv.lock，运行 uv lock --check、锁定开发/生产同步；确认 PyJWT/安全版本正确，jose 消失，ecdsa/rsa/pyasn1 仅在无其他反向依赖时消失。
- [ ] 3.3 审查清单与两份锁的最终差异和哈希，确认 mcp-server/uv.lock 保持、cryptography 可用，安装后不重新写锁；保存维护前后依赖路径对照。

## 4. 跑双门禁

- [x] 4.1 运行完整 make check，逐项确认原 33 个子项均 PASS、无跳过且 exit=0，并归档原始 stdout/stderr 与检查列表；不得为凑 33 删除检查，新发现项须同样通过。
- [x] 4.2 运行 make check-security，归档真实退出码与原始 npm/pip/密钥结果，保持 RED 原因原样；不添加漏洞豁免、不改门禁、不覆盖丢失历史证据。
- [x] 4.3 依据锁图、npm advisory/via/nodes 和 backend/MCP 审计逐条归因剩余 high/critical；证明应用依赖仅剩 Next 及其传递依赖，指定三类修复包不得借 Next 路径继续豁免，非 Next 或未知严重度项阻断该判据。
- [ ] 4.4 完成 J1–J8 的新旧双向 token/API 对照、PPTX/图片失败边界、公式/Markdown 与既有权限反例；确认所有差异关闭、无 token/密钥进入证据。

## 5. 镜像扫描

- [x] 5.1 在独立测试环境按锁构建后端/前端运行镜像，记录源码与锁哈希、基础层 digest、架构及 image ID；检查运行依赖与目标一致，不挂教学卷、不启动生产栈。
- [x] 5.2 使用可追溯 Trivy 与漏洞库对后端镜像全层扫描，保存未筛选 JSON 和 CRITICAL 专项命令退出码；确认 OS/语言/内嵌库合计 CRITICAL=0，不使用 ignore-unfixed 或忽略规则隐藏项。
- [x] 5.3 扫描前端及现有 MCP 运行镜像，分别列出 Next 残余、OS 风险与扫描缺口；任何非 Next high/critical 使全范围“仅 Next”结论失败，保持实际 RED，不冒称正式发布可用。
- [ ] 5.4 在隔离环境按 design.md 演练成套代码/锁/旧镜像回滚，验证新旧 token 连续性、刷新和健康；记录结果与耗时，不恢复/重置真实数据库，不因回滚成功声称旧漏洞消失。

## 6. 证据归档

- [ ] 6.1 在 verification-plan.md 约定的后续批次目录归档版本、锁图、双门禁、J1–J8、镜像与回滚原始结果，以“判据→检查→结果→证据”逐项映射；未运行、失败与 UNKNOWN 独立标明。
- [ ] 6.2 由非实施者复核兼容性、许可证、API 等价、33/33、残余漏洞归因与后端镜像 CRITICAL=0，登记真实姓名与日期；如有非 Next 风险或缺失证据，不签为已通过。
- [ ] 6.3 检查 README/主规约/规范/模型注释受影响性：不改行为则记录主规约无需 delta，不为完成定义制造无关编辑；实施记录明确安全 RED 与非发布状态，并再次执行本变更 openspec validate --strict 留证。
- [ ] 6.4 准备可查的 Change / Verify / Evidence 三行交接材料，Verify 写实际执行及结果、Evidence 指向批次；检查无源码外溢、无敏感数据，未经另行授权不提交、不推送、不归档。
