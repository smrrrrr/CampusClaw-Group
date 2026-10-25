## 0. 准备

- [x] 0.1 实现前用 SQLite backup API 备份当前数据库到 `data/current/before-fix-quiz-latex-and-option-layout-<时间>.db`（`before-fix-quiz-latex-and-option-layout-20261025-125316.db`，integrity_check=ok）

## 1. 公式结构校验

- [x] 1.1 `backend/question_service.py` 新增 `check_formula_structure(text)`，按 design §1 去掉 `\$`、切分公式、检查 `$` 成对与花括号配对
- [x] 1.2 在 `validate_question` 中对题干、选项 A–D、答案字符串、解析逐字段调用，原因带字段名，与控制字符检查同级
- [x] 1.3 `QUESTION_PROMPT` 第 6 条后追加 design §3 的花括号规则

## 2. 学生卷选项排版

- [x] 2.1 `render_student_paper`：按 design §4 计算每题缩进，题干续行加缩进
- [x] 2.2 选择题：题干后空一行，选项每项一行，除最后一项外行尾加硬换行；任一选项含换行时改为每项单独成段

## 3. 验证

- [x] 3.1 `apitest/check_question_bank.py` 增加用例：
  - #15 原样选项在生成时未通过，原因含「选项 D 公式花括号不配对」；
  - 转义括号、`cases` 环境、`\$` 通过；
  - 定界符不成对未通过；
  - 修改为不配对返回 400 且 `revision` 不变；
  - 补齐后修改并通过成功；
  - 学生卷选择题选项分行，第 10 题缩进 4 格
- [x] 3.2 跑全部离线回归脚本（`apitest/check_*.py`），全部通过
- [x] 3.3 离线 node 脚本（放会话临时目录，不进仓库）用前端已安装的 react-markdown + remark-math + rehype-katex 渲染 design §4 全部用例
- [x] 3.4 重建后端容器后在浏览器核对：试卷 3「实测：空间向量小测」学生卷预览中选项各占一行，`.katex-error` 为 0
- [x] 3.5 `openspec validate --all --strict` 通过，验收记录写入本变更的 `validation.md`
