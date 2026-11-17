# 可核验的组内交叉评审

快照日期 2026-11-17，原始元数据见 [github-snapshot.json](project-evidence/github-snapshot.json)。

| 四项 | 记录 |
| --- | --- |
| 手段 | smrrrrr 在 Windows 新克隆目录启动并检查组员交付，结合 Codex 辅助定位和脚本反例，在 GitHub 评论并提交正式 Review。 |
| 对象 | hexzun1 的 PR #3，最终候选 `ca66b9a9e22db8d04fd234778290660fa7586690`。 |
| 判据 | 新目录服务可启动，门禁拒绝不完整扫描与未登记软件包；修复后通过三项 CI；审批对准合并候选。 |
| 结果 | 正式批准发生于 2026-11-17 08:14:22 UTC，针对 `ca66b9a`；08:15:57 UTC 合并为 `8964200`。 |

- [最初复核意见](https://github.com/smrrrrr/CampusClaw-Group/pull/3#issuecomment-6938974465)
- [正式批准](https://github.com/smrrrrr/CampusClaw-Group/pull/3#pullrequestreview-5935012549)
- [PR #3 合并记录](https://github.com/smrrrrr/CampusClaw-Group/pull/3)
- [本人新目录启动证据](https://github.com/smrrrrr/CampusClaw-Group/blob/85f7573/reports/boot-reproduce.md#九102-本人启动复验2026-11-17)

确认后固化的检查为 `apitest/check_os_vuln_gate.py` 的“缺少 Trivy 元数据的空对象”“同 CVE 的未登记软件包”“workflow 门禁显式要求三份报告”等，修复 `cc5b0fc`，见 [review-04.md](review-04.md)。自动检查与人工参与按来源分别记录。

范围说明：smrrrrr 既对组员内容评审，也贡献了 PR #5 修复；不能把本人批准说成其自己修复获得了另一名组员的独立批准。PR #5 没有正式 Review 记录，先合入源分支后包含在 PR #3；本次报告分支及 PR #6 尚无另一人批准，不能沿用旧 Review 宣称新内容已审。历史评审文件里的空签名不补填。
