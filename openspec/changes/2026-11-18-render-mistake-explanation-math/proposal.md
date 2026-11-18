## Why

学生错题页的 AI 讲解以纯文本展示，向量等公式显示为 LaTeX 源码，列表和加粗也无法排版。

## What Changes

- 在错题讲解中显示 Markdown 与 KaTeX 公式，兼容模型返回的反斜杠定界符。
- 继续展示降级提示，屏蔽模型输出中的原始 HTML 和图片。

## Capabilities

### Modified Capabilities

- `student-workspace`: 错题讲解公式与 Markdown 排版。

## Impact

学生端错题页、共享 Markdown 渲染和前端离线检查。沿用现有讲解响应字段。
