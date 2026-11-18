# 评审 04：扫描报告完整性与例外范围

整理日期 2026-11-17；发现与修复发生于同日。性质为 Codex 辅助自审和脚本复现，人工评论另见 [peer-review.md](peer-review.md)。本文提炼已有发现，不把整理日期冒充新增问题发现。

| 四项 | 记录 |
| --- | --- |
| 手段 | AI 阅读 `scripts/trivy_os_gate.py` 与 `.github/workflows/lesson10.yml`，构造合成 Trivy 报告；同一回归脚本对修复前后各执行一次。 |
| 对象 | `{}` 空对象、错误 Results 结构、重复镜像、同 CVE 不同软件包、CI 漏交某一镜像报告。 |
| 判据 | 无效/缺失/重复报告必须退出 2；未登记 HIGH 必须退出 1；只有合法零漏洞报告或精确命中的有效例外才可退出 0。CRITICAL 不接受例外。 |
| 结果 | 基线 `977bcde` 单项 19/25，6 条失败，完整门禁 42/43 exit 1；修复 `cc5b0fc` 后单项 25/25、完整门禁 43/43 exit 0；本次扩展回归 31/31 exit 0。 |

根因：旧脚本仅按 CVE 查例外，未验证 Trivy 报告的必要元数据；CI 通配符只传存在的报告。修复要求三份指定报告，校验结构、去重镜像，并按 CVE、软件包与期限匹配。新增反例常驻 `apitest/check_os_vuln_gate.py`，由 `scripts/check.py` 自动发现。

历史原始证据：[单项红](lesson-10/20261117-image-vuln-gate/targeted-red.txt)、[单项绿](lesson-10/20261117-image-vuln-gate/targeted-green.txt)、[全量红](lesson-10/20261117-image-vuln-gate/full-red.json)、[全量绿](lesson-10/20261117-image-vuln-gate/full-green.json)。修复提交 [cc5b0fc](https://github.com/smrrrrr/CampusClaw-Group/commit/cc5b0fc22b7755fbb2fb843ee9fd0b056a0be3d6)。

本次证据：[31 条输出](project-evidence/image-gate.txt)、[时间/退出码/源码摘要](project-evidence/validation-runs.json)。准备后端 Python 环境后，在仓库根执行：

```text
python apitest/check_os_vuln_gate.py
```

预期退出 0。这里的 Docker 调用采用测试替身，只验证判定逻辑，实际镜像核验见 [review-06.md](review-06.md)。
