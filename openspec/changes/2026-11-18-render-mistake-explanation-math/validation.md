# 错题讲解公式排版验证

2026-11-18，Windows 本地工作区。

- `openspec.cmd validate 2026-11-18-render-mistake-explanation-math --strict` 通过。
- `node.exe apitest/check_mistake_explanation_rendering.cjs` 在纯文本实现上以退出码 1 复现，失败信号是错题讲解未使用数学渲染。接入后，三个场景均通过，退出码 0。
- 真实 Markdown 和 KaTeX 渲染验证了向量箭头、五处数学公式（两处独立公式）、加粗和列表。保留代码与坏公式的可读性，过滤模型文本中的图片和原始 HTML，并显示未配置提示。
- 本机前端镜像生产构建成功，容器重建后健康。浏览器登录一班演示账号并抵达错题页，核对「立体几何作业3 · 第 2 题」的讲解入口。真实讲解点击被自动审批拦截，合成文本在离线渲染检查中验证。
- Windows 完整门禁首次卡在 `check_analytics`。在本机重新运行 `backend/.venv/Scripts/python.exe scripts/check.py --json .review/lesson10-local/mistake-explanation-math-retry.json` 后，44 项全部通过，退出码 0。
