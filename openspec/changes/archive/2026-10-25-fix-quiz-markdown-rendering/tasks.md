## 1. 填空空位保护

- [x] 1.1 新增 `frontend/lib/markdown-blanks.ts`：`protectFillBlanks(text)`，按 design §3 跳过围栏代码、行内代码、公式、尖括号自动链接与整行下划线，其余 `(?<!\\)_{4,}` 中每个 `_` 转成 `\_`
- [x] 1.2 `frontend/components/markdown-answer.tsx`：按 design §4 的顺序接入（图片路径 → 空位保护 → `normalizeLatex`）

## 2. 选项渲染

- [x] 2.1 `frontend/app/teacher/quiz/page.tsx` 题目详情选项改用 `MarkdownAnswer`（传 `quizImageUrl`）
- [x] 2.2 `frontend/app/globals.css` 增加 `.quiz-options .markdown-body` 内联样式，保持「A. 内容」同行

## 2A. 答案行渲染（评审后补充）

- [x] 2A.1 `frontend/app/teacher/quiz/page.tsx` 详情答案行：填空、解答题用 `MarkdownAnswer` 渲染 `formatAnswer` 结果（传 `quizImageUrl`），单选、多选、判断保持纯文本；编辑模式不变
- [x] 2A.2 `frontend/app/globals.css` 增加 `.quiz-answer .markdown-body` 内联样式

## 3. 验证

- [x] 3.1 离线 node 脚本（放会话临时目录，不进仓库）跑 design §4 表格全部用例，经 react-markdown + remark-math + rehype-katex 实际渲染核对
- [x] 3.2 `npm run build` 通过（前端无单元测试脚本）
- [x] 3.3 重建前端容器后在浏览器核对：#8 显示 3 个空位；#2、#6（待复核）与 #7（题库）详情选项公式渲染、同行；页面 `.katex-error` 为 0；#4、#5 详情答案公式渲染，#8 答案显示 `1、1、-1`，#2/#3 答案为字母与「正确」；编辑模式答案框为原文；学生卷预览中解答题横线不变
- [x] 3.4 `openspec validate fix-quiz-markdown-rendering --strict` 通过

## 4. 归档前

- [x] 4.1 确认 `add-smart-question-generation` 已先归档，再归档本变更
