"""第10课：Next 图片优化与 middleware 风险前提的回归护栏。

对应 reports/next-risk-applicability.md。该论证依赖三个前提：
1. 未安装 sharp（图片优化不可用，AVIF/SVG RCE 不可触发）；
2. next.config 未放行远程图片域；
3. middleware 不承担鉴权（中间件绕过无意义）。

任一前提被改动即视为论证失效，本检查先红，避免风险在无人察觉时重新打开。
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def check(name, value):
    print(("PASS " if value else "FAIL ") + name)
    if not value:
        raise AssertionError(name)


def load_package() -> dict:
    return json.loads((FRONTEND / "package.json").read_text(encoding="utf-8"))


def next_config_text() -> str:
    for name in ("next.config.mjs", "next.config.js", "next.config.ts"):
        path = FRONTEND / name
        if path.exists():
            return path.read_text(encoding="utf-8")
    return ""


def middleware_text() -> str:
    for name in ("middleware.ts", "middleware.js", "src/middleware.ts", "src/middleware.js"):
        path = FRONTEND / name
        if path.exists():
            return path.read_text(encoding="utf-8")
    return ""


def main():
    package = load_package()
    declared = {}
    declared.update(package.get("dependencies", {}))
    declared.update(package.get("devDependencies", {}))
    check("Next 风险前提：未声明 sharp，图片优化保持不可用",
          "sharp" not in declared)

    config = next_config_text()
    check("Next 风险前提：存在 next 配置文件", bool(config))
    check("Next 风险前提：未放行 images.remotePatterns",
          "remotePatterns" not in config)
    check("Next 风险前提：未放行 images.domains",
          not re.search(r"\bdomains\s*:", config))

    middleware = middleware_text()
    check("Next 风险前提：存在 middleware.ts", bool(middleware))
    auth_markers = ("NextResponse.redirect", "NextResponse.rewrite", "Unauthorized",
                    "status: 401", "status:401")
    check("Next 风险前提：middleware 不承担鉴权或跳转",
          not any(marker in middleware for marker in auth_markers))

    sources = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for base in (FRONTEND / "app", FRONTEND / "components")
        if base.exists()
        for path in base.rglob("*")
        if path.suffix in (".ts", ".tsx", ".js", ".jsx")
    )
    check("Next 风险前提：业务代码未使用 next/image",
          "next/image" not in sources and "<Image" not in sources)


if __name__ == "__main__":
    main()
