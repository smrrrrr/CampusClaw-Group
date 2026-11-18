# 从仓库根复跑检查

以下准备在独立克隆目录执行。普通门禁及三查使用临时数据库和模型替身，不需要讲义包、真实模型 Key 或正在运行的 Docker。Python 3.12、Node 22、uv、Git 是前置环境；联网只发生在安装依赖和安全审计阶段。

## Windows PowerShell

```powershell
uv sync --project backend --locked
if ($LASTEXITCODE -ne 0) { throw '后端依赖安装失败' }
npm.cmd --prefix frontend ci
if ($LASTEXITCODE -ne 0) { throw '前端依赖安装失败' }
npm.cmd install --prefix .review/report-tools --no-audit --no-fund --no-package-lock @fission-ai/openspec@1.13.1
if ($LASTEXITCODE -ne 0) { throw 'OpenSpec 安装失败' }
$env:Path = (Resolve-Path .review/report-tools/node_modules/.bin).Path + ';' + (Resolve-Path backend/.venv/Scripts).Path + ';' + $env:Path
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
python scripts/check.py --json .review/report-check.json
if ($LASTEXITCODE -ne 0) { throw '普通门禁未通过，请保留失败输出' }
```

之后执行报告里的 `python ...` 会使用后端虚拟环境。单项复跑可直接使用完整解释器路径，避免选错 Python：

```powershell
backend/.venv/Scripts/python.exe apitest/check_async_grading.py
backend/.venv/Scripts/python.exe apitest/probe_security_precheck.py --output .review/report-security-probe.json
backend/.venv/Scripts/python.exe apitest/check_os_vuln_gate.py
```

每条后立即查看 `$LASTEXITCODE`。预期分别为 57 条、41 条、31 条通过，且退出 0；未来新增检查后总数可变，不能为了凑历史数量删断言。

## Linux / macOS

```bash
uv sync --project backend --locked
npm --prefix frontend ci
npm install --prefix .review/report-tools --no-audit --no-fund --no-package-lock @fission-ai/openspec@1.13.1
export PATH="$PWD/.review/report-tools/node_modules/.bin:$PWD/backend/.venv/bin:$PATH"
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
make check
```

安装每步必须成功才能继续。三条单项命令与报告相同。将日志写入自己的 `.review/`，不覆盖本仓库已归档的历史证据。

## 安全门禁的额外前置

`make check-security` 不等于离线权限探针。它还检查容器日志/前端产物范围、四个合成身份和联网依赖审计。只启动空库就执行可能退出 2，表示有范围未验证。

优先在 PR 的 `.github/workflows/lesson10.yml` 运行该检查，工作流会创建独立临时环境与四个演示身份。本机复现可按 [demo-checklist.md](demo-checklist.md) 和该 workflow 准备隔离环境后执行：

```text
Windows: backend/.venv/Scripts/python.exe scripts/security_precheck.py
Linux:   make check-security
```

不要在已有教学库运行 `backend/dev_seed.py`，不要以 `--reuse-dependency-evidence` 的旧结果声明完成了本次联网审计。退出 0 为通过，1 为发现红项，2 为执行/范围不完整；依赖响应不能提供严重度时，不把它编成 high=0。

## 结果解释

完整普通门禁、离线三查、联网安全门禁与镜像扫描各有对应结果。课堂录屏需要录到命令执行和结果，以及登录后的核心业务演示。[demo-recording.md](demo-recording.md)

## 重生成报告阅读副本

正式源文件是根目录 `report.md`，PDF仅为同源阅读副本。排版工具 `scripts/render_project_report.py` 使用独立的作者环境，不往应用依赖里添加PDF组件：

```text
uv run --no-project --with reportlab --with pypdf python scripts/render_project_report.py
```

Windows 默认使用系统宋体和黑体，其他系统可用 `--font` 指定中文 TrueType 字体。还在草稿分支时可加 `--ref docs/project-report` 让 PDF 中的文件链接指向该分支。输出为 `output/pdf/CampusClaw-project-report.pdf`，脚本检查恰好两页，元数据和页脚记录源文件摘要。修改正文后重新生成并逐页检查，内容核验见 `reports/project-evidence/document-checks.json`。
