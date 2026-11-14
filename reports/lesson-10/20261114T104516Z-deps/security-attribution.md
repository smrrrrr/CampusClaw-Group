# A+B 依赖升级后的安全归因

- 批次：`reports/lesson-10/20261114T104516Z-deps/`
- 分支：`deps/upgrade-a-b`（基于 `0408862`）
- 执行：`COMPOSE_PROJECT_NAME=campusclaw-group backend/.venv/bin/python scripts/security_precheck.py`
- 结果：**RED（exit=1）**，密钥扫描范围完整=True、疑似泄漏=False

## 剩余 high / critical

| 生态 | high | critical | 来源 | 结论 |
| --- | --- | --- | --- | --- |
| npm | 0 | 1 | `next@14.2.15`（Next 自身及其传递依赖） | 剩余 high/critical **仅来自 Next** |

Next 的 4 条 critical 在当前代码与 Linux standalone 部署下的适用性见 [next-risk-applicability.md](../../next-risk-applicability.md)：middleware 不鉴权、无 `next/image`、镜像内无 `sharp`、优化器对所有图片返回 400、远程 URL 被拒。该论证不改变 audit 计数与门禁 RED。
| backend (pip) | 0 | 0 | — | certifi、Pillow 已升级；python-jose 已移除 |
| mcp (pip) | 0 | 0 | — | opentelemetry-api 1.45.1→1.45.2 |

## 低危与 moderate

| 包 | 版本 | 严重度 | 说明 |
| --- | --- | --- | --- |
| katex | 0.16.47 | low | `GHSA-238p-pmpm-9mq7` 修复需 katex 0.18.2+（0.19 为主版本）；本轮高/中危已消除，低危保留 |
| micromark-extension-math / rehype-katex / remark-math | 3.1.0 / 7.0.1 / 6.0.0 | low | 均由 katex 低危传递 |

PostCSS 由 8.4.31 升到 **8.5.33** 后，`GHSA-6g55-p6wh-862q`、`GHSA-r28c-9q8g-f849`、`GHSA-fxqj-rqcc-2cmp` 均不再出现；source-map-js 1.2.2 的 high 已消除。

## 未登记项说明

安全脚本按“未登记漏洞包”列出：`npm:katex`、`npm:micromark-extension-math`、`npm:next`、`npm:rehype-katex`、`npm:remark-math`。其中只有 `next` 属于 high/critical；其余为 low。未新增任何漏洞豁免，未放宽门禁。

因此本批次的允许 RED 判据成立：**应用依赖的 high/critical 扣除 Next 后为空**。但整个系统的 RED 仍存在，不能宣称安全发布完成。
