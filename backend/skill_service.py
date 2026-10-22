"""教师技能文件解析与保存期校验（add-mcp-tool-integration，design.md 决策 9）。

技能文件格式（原文提交）：

```
名称：公式提示
适用条件：夹角,公式
工具：knowledge_search, formula_hint@campus-tools
启用：是
资料：数学            ← 可选，填写时必须等于教师当前学科名称

以下为技能说明……
```

- 第一个空行以上是键值头部，以下是技能说明
- 键限定为 名称/适用条件/工具/启用/资料；未知字段报错
- 工具按逗号或顿号拆分，去空白去重；MCP 引用必须是 ``工具名@服务器名``
- 不给最终答案的固定约束由系统提示负责，技能说明不得覆盖
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from agent_service import SUBJECT_NAMES
from mcp_client import TOOL_NAME_RE, TOOL_REF_RE

BUILTIN_TOOL = "knowledge_search"

NAME_MAX = 32
TRIGGER_MAX = 120
DESCRIPTION_MAX = 2000
SOURCE_MAX = 8000

_KEY_ALIASES = {
    "名称": "name",
    "适用条件": "trigger",
    "工具": "tools",
    "启用": "enabled",
    "资料": "subject",
}
_REQUIRED_KEYS = {"name", "trigger", "tools", "enabled"}


class SkillParseError(ValueError):
    """技能文件格式错误（中文原因）。"""


@dataclass
class ParsedSkill:
    name: str
    trigger: str
    tools: list[str]
    enabled: bool
    description: str
    subject: str | None = None
    raw: str = ""
    # 解析出的 MCP 引用：[(tool_name, server_name)]
    tool_refs: list[tuple[str, str]] = field(default_factory=list)

    @property
    def trigger_keywords(self) -> list[str]:
        return [t for t in re.split(r"[,，、]", self.trigger) if t.strip()]

    @property
    def has_mcp_tools(self) -> bool:
        return bool(self.tool_refs)


def _split_tools(raw: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"[,，、]", raw) if p.strip()]
    seen: list[str] = []
    for p in parts:
        if p not in seen:
            seen.append(p)
    return seen


def parse_skill_file(source: str) -> ParsedSkill:
    """解析技能文件原文；格式错误抛 SkillParseError。"""
    if not isinstance(source, str):
        raise SkillParseError("技能文件必须是文本")
    source = source.replace("\r\n", "\n").replace("\r", "\n")
    if not source.strip():
        raise SkillParseError("技能文件不能为空")
    if len(source) > SOURCE_MAX:
        raise SkillParseError(f"技能文件最长 {SOURCE_MAX} 字")

    # 第一个空行分隔头部与说明
    match = re.search(r"\n\s*\n", source)
    if not match:
        raise SkillParseError("技能文件缺少分隔头部与说明的空行")
    header_text = source[: match.start()]
    description = source[match.end():].strip()

    headers: dict[str, str] = {}
    for line in header_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        kv = re.split(r"[：:]", line, maxsplit=1)
        if len(kv) != 2:
            raise SkillParseError(f"无法识别的头部行：{line}")
        key_raw, value = kv[0].strip(), kv[1].strip()
        key = _KEY_ALIASES.get(key_raw)
        if key is None:
            raise SkillParseError(f"未知字段：{key_raw}")
        if key in headers:
            raise SkillParseError(f"字段重复：{key_raw}")
        headers[key] = value

    missing = _REQUIRED_KEYS - set(headers)
    if missing:
        names = "、".join(k for k, v in _KEY_ALIASES.items() if v in missing)
        raise SkillParseError(f"缺少必填字段：{names}")

    name = headers["name"].strip()
    if not name:
        raise SkillParseError("名称不能为空")
    if len(name) > NAME_MAX:
        raise SkillParseError(f"名称最长 {NAME_MAX} 字")

    trigger = headers["trigger"].strip()
    if not trigger:
        raise SkillParseError("适用条件不能为空")
    if len(trigger) > TRIGGER_MAX:
        raise SkillParseError(f"适用条件最长 {TRIGGER_MAX} 字")
    if not _split_tools(trigger):
        raise SkillParseError("适用条件需至少包含一个关键词")

    tools = _split_tools(headers["tools"])
    if not tools:
        raise SkillParseError("工具不能为空")
    tool_refs: list[tuple[str, str]] = []
    for item in tools:
        if item == BUILTIN_TOOL:
            continue
        m = TOOL_REF_RE.match(item)
        if not m:
            raise SkillParseError(
                f"工具引用「{item}」格式不正确，可用写法为 knowledge_search 或 工具名@服务器名"
            )
        tool_refs.append((m.group(1), m.group(2)))

    enabled_raw = headers["enabled"].strip()
    if enabled_raw not in ("是", "否"):
        raise SkillParseError("启用只能填写「是」或「否」")
    enabled = enabled_raw == "是"

    if not description:
        raise SkillParseError("技能说明不能为空")
    if len(description) > DESCRIPTION_MAX:
        raise SkillParseError(f"技能说明最长 {DESCRIPTION_MAX} 字")

    subject = headers.get("subject")
    if subject is not None:
        subject = subject.strip()
        if subject not in SUBJECT_NAMES.values():
            raise SkillParseError("资料字段若填写，必须等于本科目名称，如「数学」")

    return ParsedSkill(
        name=name,
        trigger=trigger,
        tools=tools,
        enabled=enabled,
        description=description,
        subject=subject,
        raw=source,
        tool_refs=tool_refs,
    )
