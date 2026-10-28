"""后端分层检查：依赖只能自上而下（docs/standards/02-后端开发规范.md §1）。

层级（数字越小越靠外）：
    0 接口层  main · routers/* · deps · schemas · logging_setup · dev_seed
    1 业务层  *_service · services · mcp_orchestrator · model_json · knowledge_tags · security
    2 适配层  llm_service · embedding_service · mcp_client · mcp_crypto
    2 数据层  models · database
    3 配置    config · version

规则：模块只能 import 层级数不小于自己的项目模块（同层互引允许）；
新增的后端模块必须先在 LAYERS 登记，否则检查失败。

用法（项目根）：python scripts/check_layering.py
"""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"

INTERFACE, BUSINESS, ADAPTER, DATA, CONFIG = 0, 1, 2, 2, 3
LAYER_NAMES = {0: "接口层", 1: "业务层", 2: "适配/数据层", 3: "配置"}

LAYERS = {
    "main": INTERFACE,
    "routers": INTERFACE,
    "deps": INTERFACE,
    "schemas": INTERFACE,
    "logging_setup": INTERFACE,
    "dev_seed": INTERFACE,
    "services": BUSINESS,
    "agent_service": BUSINESS,
    "chunk_service": BUSINESS,
    "citation_service": BUSINESS,
    "lesson_service": BUSINESS,
    "material_service": BUSINESS,
    "question_service": BUSINESS,
    "rag_search_service": BUSINESS,
    "research_service": BUSINESS,
    "skill_service": BUSINESS,
    "mcp_orchestrator": BUSINESS,
    "model_json": BUSINESS,
    "knowledge_tags": BUSINESS,
    "security": BUSINESS,
    "llm_service": ADAPTER,
    "embedding_service": ADAPTER,
    "mcp_client": ADAPTER,
    "mcp_crypto": ADAPTER,
    "models": DATA,
    "database": DATA,
    "config": CONFIG,
    "version": CONFIG,
}

# 业务层只允许依赖 Web 框架之外的东西；以下两处历史例外见 02-后端开发规范.md「例外」，只许减少不许新增
FRAMEWORK_MODULES = {"fastapi", "starlette"}
FRAMEWORK_EXCEPTIONS = {("services", "fastapi"), ("agent_service", "fastapi")}


def module_name(path: Path) -> str:
    rel = path.relative_to(BACKEND)
    return rel.parts[0] if len(rel.parts) > 1 else path.stem


def imports_of(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module.split(".")[0])
    return found


def main() -> int:
    errors = []
    files = sorted(BACKEND.glob("*.py")) + sorted((BACKEND / "routers").glob("*.py"))
    for path in files:
        name = module_name(path)
        if name not in LAYERS:
            errors.append(f"{path.relative_to(ROOT)}：模块 {name} 未登记层级，请先在 scripts/check_layering.py 的 LAYERS 中登记")
            continue
        own = LAYERS[name]
        for dep in sorted(imports_of(path)):
            if dep in LAYERS and dep != name and LAYERS[dep] < own:
                errors.append(
                    f"{path.relative_to(ROOT)}：{LAYER_NAMES[own]}模块 {name} 反向依赖{LAYER_NAMES[LAYERS[dep]]}模块 {dep}"
                )
            if own >= BUSINESS and dep in FRAMEWORK_MODULES and (name, dep) not in FRAMEWORK_EXCEPTIONS:
                errors.append(f"{path.relative_to(ROOT)}：{LAYER_NAMES[own]}模块 {name} 依赖 Web 框架 {dep}")
    for error in errors:
        print("  ✗ " + error)
    print(f"分层检查：{len(files)} 个模块，{len(errors)} 处违规")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
