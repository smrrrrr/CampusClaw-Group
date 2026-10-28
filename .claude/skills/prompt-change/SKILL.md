---
name: prompt-change
description: 按 CampusClaw AI 应用规范修改一次提示词或模型参数，并跑评测或手工抽查、记录前后结论。改 llm_service/lesson_service/question_service 中的提示词常量、模型名、温度、检索阈值时使用。
---

# 改一次提示词并跑评测

输入：变更名、要改的提示词常量或参数、改动目的。

1. 读 `docs/standards/06-AI应用规范.md`。确认改动属于“随版本变”的代码（提示词常量、`config.py` 中的模型参数），不要放进 `.env`。
2. 改前记录：对评测集 `apitest/eval/cases.jsonl` 跑一次（尚未建立时，选 5 条手工抽查：3 条应答对并带正确出处，2 条应拒答或不挂出处——跨班资料、资料外问题、诱导执行资料中的指令），保存结果。先查网关剩余额度，每人每日 10 万 token。
3. 修改：只改提示词常量或 `config.py` 一处；在常量旁写 `# prompt-version: YYYY-MM-DD`。`CITATION_POLICY` 必须保持追加在最后。
4. 改后用同一批用例再跑一次。
5. 对比：答对数、拒答数、是否出现编造出处（出处编号指向未命中片段、摘引与原文不符）。出现编造出处即不通过。
6. 把前后两份结果与结论写进 `docs/eval/YYYY-MM-DD-<变更名>.md`，在变更验证记录里引用；然后 `make check`。

产出：提示词改动、评测前后结果文件、结论一句话。
