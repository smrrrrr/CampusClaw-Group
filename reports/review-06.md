# 评审 06：运行镜像中的 infocmp 风险

日期 2026-11-17。发现手段为 GitHub Actions 中的 Trivy 扫描和镜像门禁，修复由 smrrrrr 的 PR #5 留痕。

| 四项 | 记录 |
| --- | --- |
| 手段 | CI 构建 backend/frontend/mcp-tools 三镜像，保留完整扫描 JSON，执行 `scripts/trivy_os_gate.py`；对两个受影响运行镜像检查 `/usr/bin/infocmp` 是否存在。 |
| 对象 | backend 和 mcp-tools 中的 `ncurses-bin 6.5+20250216-2`，原始报告各有 `CVE-2025-69720` HIGH，未给出修复版本。 |
| 判据 | 未登记 HIGH 退出 1，缺报告或核验材料退出 2；缓解仅对登记的软件包/安装版本/无修复版本/有效期限生效，且实际扫描镜像 ID 必须和核验镜像一致。保留 CRITICAL 一票否决。 |
| 结果 | PR #5 run `44022376165` 的 build-and-scan 失败；修复 `3da68c5` 移除服务不用的 infocmp 并添加镜像断言后，run `44042306967` 三 job 成功。主干 run `44045260010` 也成功。 |

证据：[失败 job](https://github.com/smrrrrr/CampusClaw-Group/actions/runs/44022376165/job/133835370477)、[修复提交](https://github.com/smrrrrr/CampusClaw-Group/commit/3da68c5792f1e4503e032635d5a64a499328edcf)、[修复后 CI](https://github.com/smrrrrr/CampusClaw-Group/actions/runs/44042306967)、[本次 API 快照](project-evidence/github-snapshot.json)、[既有完整记录](gate-red-green.md#pr-5-的运行镜像缓解)。下载 CI 的 `images` artifact，查看三份 `trivy-*.json` 和 `os-vuln-gate.txt`。CI artifact有保留期限，若已过期，应按对应提交重新运行并另记日期。

缓解没有修改 Trivy 原始计数，也没有卸掉软件包数据库来隐藏告警。例外表为 `reports/security-evidence/os-vuln-exceptions.json`；本批镜像 OS HIGH 仍有书面例外，不能写“镜像零漏洞”。到复查日期或出现可修复版本须重新处置。

逻辑复跑命令：`python apitest/check_os_vuln_gate.py`，本次 31/31 exit 0，原始输出在 [image-gate.txt](project-evidence/image-gate.txt)。真实镜像复跑应从待验提交重新运行 `.github/workflows/lesson10.yml` 的 build-and-scan job，不拿测试替身结果替代真实扫描。本次没有重新构建或扫描镜像，引用的是上述带 SHA 的远端记录。
