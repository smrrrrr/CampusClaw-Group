# 提交前核对表

汇报当天完成三样：在研发楼 1202 小组汇报 5 分钟，课堂派上传与仓库根目录内容一致的 `report.md`，提交百度网盘或北大网盘的录屏下载地址。

| 计分节 | 分值 | 核对位置 |
| --- | --- | --- |
| 一句话介绍 | 10 | `report.md` 第 1 节，目标用户和要解决的问题。 |
| AI 写了什么 | 20 | `report.md` 第 2 节的 Harness、规则、测试用例、评审、压测、验证编排与 README；`AGENTS.md` 有七类问题与手段。 |
| 审核记录 | 25 | `reports/review-04.md`、`reports/review-05.md`、`reports/review-06.md`，至少两份由 AI 自审或脚本发现。 |
| 高风险三查 | 25 | `reports/risk-concurrency.md`、`reports/risk-transaction.md`、`reports/risk-authz.md`，三条有命令、对象、判据和结果。 |
| 门禁与演示 | 20 | `reports/project-gate.md` 有红绿 CI 与保护状态。录屏待录制，缺录屏时本节 0 分。 |
| 复盘 | 必写，不计分 | `report.md` 第 6 节交代镜像门禁返工原因与代价。 |

1. 按 [demo-recording.md](demo-recording.md) 录制三分钟以内视频。保留每条验证命令的运行与结果，演示登录后操作。
2. 上传到百度网盘或北大网盘，验证链接和提取码。把地址填在根报告开头，同步录制信息到 [demo-recording-evidence.md](demo-recording-evidence.md)，再生成 PDF 阅读副本。
3. 核对 Git 署名与分工，将最终报告交组员评审并走受保护的合并流程。汇报当天把同一份 `report.md` 上传课堂派，一组一份。
4. 按 [presentation-notes.md](presentation-notes.md) 分配 5 分钟的讲解，直接展示仓库或使用 PPT。
