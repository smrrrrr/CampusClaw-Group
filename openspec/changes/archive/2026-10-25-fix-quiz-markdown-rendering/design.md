## Context

前端只有一个 Markdown + KaTeX 渲染器：`frontend/components/markdown-answer.tsx`（react-markdown 9.0.1 + remark-math 6.0.0 + rehype-katex 7.0.1）。渲染前它已做两步文本预处理：`normalizeMarkdownImagePaths`（仅在传了 `imageUrl` 时）和 `normalizeLatex`（给公式里漏写反斜杠的命令补 `\`）。

/teacher/quiz 中使用它的位置：

| 位置 | 渲染内容 | 选项 / 答案 |
| --- | --- | --- |
| 题库 / 待复核列表卡片（`page.tsx:191`） | 题干 | 不显示 |
| 题目详情面板（`page.tsx:224–227`，题库与待复核共用） | 题干、解析 | 选项、答案均为**纯文本**（`page.tsx:225`、`226`） |
| 草稿试卷编辑器、换题候选（`page.tsx:463、469`） | 题干 | 不显示 |
| 已定稿试卷题目列表（`page.tsx:397`） | 题干 | 不显示 |
| 学生卷预览（`page.tsx:405`） | 服务端 `render_student_paper` 生成的整卷 Markdown | 选项拼在 Markdown 里，已渲染 |

学生端：试卷发布后是班级 Material（`试卷标题（试卷）.md`），学生在资料预览里打开，走 `MaterialPreview` → `MarkdownAnswer`。学生页面没有单独的题目渲染组件。

### 问题 1 的成因

CommonMark 的强调规则看分隔符两侧的字符。题干 `坐标为____，____，____。` 里：

- 第 1 个 `____`：左边「为」是普通字符，右边「，」是标点，只能闭合，没有可配对的开启分隔符，按字面显示；
- 第 2、3 个 `____`：两侧都是中文标点，既可开也可闭，互相配对，生成 `<strong><strong>，</strong></strong>`，下划线被吃掉。

本地复现（`renderToStaticMarkup`）：原文输出 `<p>坐标为____，<strong><strong>，</strong></strong>。</p>`；把空位写成 `\_\_\_\_` 后输出 `<p>坐标为____，____，____。</p>`。

学生卷中解答题的作答横线是独占一行的 `______________________________`，CommonMark 把它当作分隔线（`<hr/>`），当前显示为横线。这个效果要保留。

### 问题 2 的成因

`page.tsx:225` 直接输出 `{o.text}`，没有走 `MarkdownAnswer`。

### 问题 3 的成因（评审后补充）

2026-10-24 复测时发现：`page.tsx:226` 的答案行是 `<p><b>答案：</b>{formatAnswer(detail.answer)}</p>`，同样是纯文本。`formatAnswer` 把布尔值转成「正确 / 错误」，数组用「、」连接，其他转字符串。待复核 #4（填空，答案 `["$\frac{\sqrt{15}}{5}$"]`）和 #5（解答，答案 `"$\frac{\sqrt{3}}{3}$"`）的答案以 `$…$` 源码显示。该问题在本变更之前就存在。

## Goals / Non-Goals

**Goals**

- 填空题每个空位都按原样显示，数量与后端校验一致。
- 详情面板中选项和答案的公式和题干一样用 KaTeX 渲染。
- 修正对题库、待复核、组卷、学生卷预览和学生端试卷资料同时生效，不在各处各写一份。

**Non-Goals**

- 不改数据库中已有题目、接口返回、后端校验与学生卷 Markdown 的生成。
- 不把空位改成可填写的输入框，不做在线作答（试卷仍是只读资料）。
- 不改编辑模式：编辑时的题干、选项输入框仍显示原文。
- 不处理 `*` 星号连续出现等其他 Markdown 冲突；本次只处理下划线空位。

## Decisions

### 1. 用转义而不是专用元素

把空位里每个 `_` 写成 `\_`，在 Markdown 层面让它成为字面字符。

- 优点：不需要自定义 remark/rehype 插件，也不需要开启原始 HTML；打印、复制出来的文本和原文一样是下划线；对 react-markdown 升级不敏感。
- 备选：替换成 `<span class="quiz-blank">` 等专用元素。好处是可单独设置样式，但要么开启 `rehype-raw`（会放开 HTML，与学生稿「不得含 HTML」的口径冲突），要么写一个 remark 插件在解析后处理文本节点——而解析后强调已经发生，插件只能在 tokenizer 层介入，复杂度明显更高。本次不采用。

### 2. 放在共用渲染器里，默认生效

在 `MarkdownAnswer` 里统一处理，不加开关。

- 学生端打开已发布试卷走的是通用资料预览，那里不知道这是不是试卷；加开关就要额外判断文件名或标签，容易漏。
- 后端对空位的定义是 `_{4,}`，在中文正文里连续 4 个以上下划线基本只用于填空或作答线，不会是有意的强调写法（强调用 `__x__` 或 `**x**`）。附带影响已写入 proposal。
- 备选：只在 quiz 页面和 `MaterialPreview` 中按需开启。若评审认为附带影响不可接受，可改为 `MarkdownAnswer` 增加 `fillBlanks` 属性，quiz 页面全部开启，资料预览仅对文件名以「（试卷）.md」结尾的资料开启。

### 3. 空位转换规则（`frontend/lib/markdown-blanks.ts`：`protectFillBlanks(text)`）

按顺序扫描，以下片段原样跳过，不做替换：

1. 围栏代码块：` ```…``` `、`~~~…~~~`；
2. 行内代码：`` `…` ``；
3. 公式：`$$…$$`、`$…$`（与 `normalizeLatex` 用同一种切分，先块级后行内）；
4. 尖括号自动链接：`<scheme:…>`（其中反斜杠不是转义符，转义会改坏链接）。

其余正文中：

- 整行（去掉首尾空白后）只由下划线组成的行不改，保留分隔线/作答横线渲染；
- 其他位置匹配 `(?<!\\)_{4,}`，把其中每个 `_` 换成 `\_`。前面已是反斜杠的不处理，避免改变作者已转义的写法。

实现方式与 `normalizeMarkdownImagePaths` 相同：一个全局正则，交替匹配「跳过片段」与「目标片段」，回调里只替换目标片段。

### 4. 在渲染管线中的位置

`MarkdownAnswer` 中顺序为：`normalizeMarkdownImagePaths`（可选）→ `protectFillBlanks` → `normalizeLatex`。`normalizeLatex` 只改公式内部，`protectFillBlanks` 只改公式外部，两者互不影响；放在 `normalizeLatex` 之前，是为了让它看到的公式边界与原文一致。

离线用例（实现时用 node 脚本跑，不进仓库测试框架，因为前端目前没有测试脚本）：

| 输入 | 期望 |
| --- | --- |
| `坐标为____，____，____。` | 三处都转义，渲染后 3 个空位，无 `<strong>` |
| `$A_1B_1C_1D_1$ 中，长为____` | 公式不变，空位转义 |
| `` `a____b` `` 与围栏代码中的 `____` | 不变 |
| 独占一行的 `______________________________` | 不变，仍渲染为 `<hr>` |
| `__粗体__`、`___` | 不变 |
| `\____` | 不变 |
| `<https://x.test/a____b>` | 不变 |
| `答案：____（2 分）`（per-item 分值后缀） | 转义 |

### 5. 选项渲染

`page.tsx:225` 改为 `<li key={o.label}><b>{o.label}.</b> <MarkdownAnswer text={o.text} imageUrl={quizImageUrl} /></li>`。

`MarkdownAnswer` 外层是 `<div class="markdown-body">`，内部是 `<p>`，会把内容挤到下一行。在 `globals.css` 增加：

```css
.quiz-options .markdown-body { display: inline-block; vertical-align: top; }
.quiz-options .markdown-body p { margin: 0; }
```

让「A. 内容」保持同行；选项里若出现 `$$…$$` 块级公式，会在该选项内换行显示，可以接受。

### 6. 答案行渲染

按题型分别处理，答案文本仍由现有 `formatAnswer` 生成，不改它的分隔方式：

| 题型 | 答案数据 | 显示 |
| --- | --- | --- |
| 填空 | 字符串数组，每项对应一个空位 | `formatAnswer` 用「、」连接后交给 `MarkdownAnswer`，如 `$\frac{\sqrt{15}}{5}$`、`1、1、-1`；每项中的公式各自成对，连接不会改变公式边界 |
| 解答 | 字符串（参考答案或评分要点） | 交给 `MarkdownAnswer`，与解析一样可含多段、列表、公式 |
| 单选 / 多选 | 选项字母或字母数组 | 保持纯文本（如 `A`、`A、C`），不经过 Markdown |
| 判断 | 布尔值 | 保持纯文本「正确 / 错误」 |

写法：`page.tsx:226` 改为按 `detail.type` 判断，填空与解答时输出 `<div className="quiz-answer"><b>答案：</b><MarkdownAnswer text={formatAnswer(detail.answer)} imageUrl={quizImageUrl} /></div>`，其余题型保持现有 `<p>`。`globals.css` 增加 `.quiz-answer .markdown-body { display: inline-block; vertical-align: top; }` 与 `.quiz-answer .markdown-body p { margin: 0; }`，让单行答案与「答案：」同行；解答题多段答案在同一块内换行显示。

编辑模式不变：答案输入框（填空每行一个空、解答为多行文本）仍显示原文，由 `answerToText` / `textToAnswer` 转换，不做渲染。

答案卷下载（`GET /papers/{id}/answer-key`，服务端 `render_answer_key`）只做说明、不改：它把快照中的答案原样写入 Markdown（`**答案**：…`，布尔转「正确 / 错误」，数组用「、」连接），因此答案中的 `$…$` 公式已在文件里，以 LaTeX 源码形式保存；是否显示为数学符号取决于教师用来打开 `.md` 文件的阅读器。前端不在页面内渲染答案卷。

## Risks / Trade-offs

- **附带影响到其他页面**：AI 回答、讲义中如果真有人用 4 个以上下划线做强调，以后会按字面显示。概率低，且字面显示不丢信息。见 Decision 2 的备选。
- **自动链接中的下划线**：`<https://a____b>` 这种尖括号自动链接里反斜杠不是转义符，因此作为跳过片段处理（Decision 3 第 4 条）。普通 `[文字](地址)` 链接地址中的 `\_` 会被还原为 `_`，不受影响。
- **打印**：打印稿取同一渲染结果，无需单独处理。
- **纯文本答案被当成 Markdown**：填空、解答答案改走渲染器后，若某个答案恰好形如 `1.` 或 `- x`（以列表标记开头加空格），会被渲染成列表。题目答案一般是数值或公式，概率低；选择、判断题不经过渲染器，不受影响。

## 已知限制

- 只处理下划线空位；其他 Markdown 特殊字符与中文混排的问题不在本次范围。
- 前端没有单元测试框架，空位转换的回归是离线脚本加浏览器检查，不是自动化测试。
