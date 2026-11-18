## ADDED Requirements

### Requirement: 错题讲解支持公式排版

错题页的 AI 讲解 SHALL 使用安全的 Markdown 和 KaTeX 渲染，支持 `$...$`、`$$...$$`、`\(...\)` 和 `\[...\]`。代码示例中的定界符 MUST 保留为文本。模型讲解中的原始 HTML 和图片 MUST 被过滤；无效公式和服务降级提示 MUST 保持可读。

#### Scenario: 讲解含向量和解题步骤

- **WHEN** 讲解返回带列表、加粗、行内向量公式和独立公式的 Markdown
- **THEN** 错题卡显示格式化步骤和 KaTeX 公式，原有美元符号公式也正常显示

#### Scenario: 讲解含代码、坏公式或外部资源

- **WHEN** 讲解含代码示例、未配对定界符、无效数学命令、HTML 或 Markdown 图片
- **THEN** 代码和无效公式保持可读，原始 HTML 不被执行，图片不加载，其他有效公式照常展示

#### Scenario: 讲解服务未配置

- **WHEN** 接口报告讲解服务未配置
- **THEN** 错题卡仍显示原有降级提示
