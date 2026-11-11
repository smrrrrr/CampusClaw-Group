## ADDED Requirements

### Requirement: 用户提交文本的输出转义

用户提交的文本型字段（如讲义标题、资料描述、作业标题等）在进入页面 HTML 或 Markdown 渲染前 MUST 经过转义处理，MUST NOT 原样输出可执行脚本。转义 MUST 在服务端输出层完成，前端隐藏或客户端转义不构成防护。转义范围 MUST 至少覆盖 `<`、`>`、`"`、`'`、`&` 字符。

#### Scenario: 讲义标题含脚本被转义

- **WHEN** 教师上传资料时标题填写 `<script>alert(1)</script>`
- **THEN** 资料列表页渲染时该标题被转义为文本，页面源码中无未转义的 `<script>` 标签，脚本不执行

#### Scenario: 资料描述含脚本被转义

- **WHEN** 教师提交资料描述包含 `<img src=x onerror=alert(1)>`
- **THEN** 预览和列表展示时描述内容被转义，onerror 事件处理器不被浏览器解析执行

#### Scenario: 转义在服务端完成

- **WHEN** 直接调用 API 获取资料列表（绕过前端页面）
- **THEN** 响应中的文本字段已由服务端转义，不依赖客户端二次处理
