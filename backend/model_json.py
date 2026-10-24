"""模型 JSON 输出：代码围栏剥除、LaTeX 反斜杠修补与解析。

设计见 openspec/changes/harden-model-json-escapes/design.md §1、§2、§4。

模型在 JSON 字符串里写 LaTeX 时常常只写一个反斜杠，同一次输出里两种写法混用：

- ``\\vec``、``\\sqrt``、``\\cos`` 这类反斜杠后的字符不是合法 JSON 转义，``json.loads`` 直接报错；
- ``\\frac``、``\\begin``、``\\times``、``\\right`` 开头的 ``\\f``、``\\b``、``\\t``、``\\r``
  恰好是合法转义，会被解码成换页、退格、制表、回车，解析成功但公式已经损坏。

``load_model_json`` 只在字符串字面量内部按 design §2 的规则把 LaTeX 反斜杠补成两个，再交给
``json.loads``；修补后的文本只在内存中使用，不另存。修补只恢复字符，不证明公式或题目正确。
"""

from __future__ import annotations

import json
import re
from typing import Any

# 反斜杠后是这些字符时，本来就是合法 JSON 转义，原样保留
_STANDARD_ESCAPES = frozenset('\\"/')
# 这几个转义在 Markdown 题面里没有意义；后面紧跟字母即可认定是 LaTeX 命令
_COMMAND_STARTERS = frozenset("bftr")
# 合法控制字符转义的另一半：\n 只有在白名单里才当作 LaTeX 命令，见 design §3
_CONTROL_ESCAPES = frozenset("bfnrt")

# 以 n 开头的 LaTeX 命令（design §2 白名单）：按整段字母串精确匹配
N_COMMANDS = frozenset("""
nabla ne neq neg not notin ni nu nmid nleq ngeq nless ngtr nexists newline nparallel
nsubseteq nsupseteq nsim ncong nearrow nwarrow nleftarrow nrightarrow nLeftarrow
nRightarrow nolimits
""".split())

_FENCE = re.compile(r"^```[a-zA-Z0-9_-]*\s*\n")


class ModelJSONError(ValueError):
    """模型输出在修补后仍不是合法 JSON，或剥除围栏后不是 JSON 对象。"""


def has_control_chars(text: Any) -> bool:
    """文本是否含退格（U+0008）或换页（U+000C）。

    修补之后仍有这两个字符，说明有漏网的单反斜杠把公式解码成了控制字符，见 design §4。
    制表符、回车不纳入兜底：它们可能是合法空白，误杀代价大于收益。
    """
    return isinstance(text, str) and ("\b" in text or "\f" in text)


def _word_at(text: str, index: int) -> str:
    """从 index 起取连续的 ASCII 字母串。"""
    end = index
    while end < len(text) and text[end].isascii() and text[end].isalpha():
        end += 1
    return text[index:end]


def _needs_repair(text: str, index: int) -> bool:
    """text[index] 是字符串内的反斜杠，判断它到下一个字符是不是需要补成 ``\\\\``。

    返回 False 表示这是合法 JSON 转义，原样保留两个字符。
    """
    if index + 1 >= len(text):
        return True  # 字符串末尾的孤立反斜杠
    char = text[index + 1]
    if char in _STANDARD_ESCAPES:
        return False
    if char == "u":
        # 合法 Unicode 转义保留；u 后不满 4 位十六进制则按非法转义修补
        return not (index + 6 <= len(text) and all(c in "0123456789abcdefABCDEF" for c in text[index + 2:index + 6]))
    if char in _COMMAND_STARTERS:
        # \frac、\beta、\times、\right：转义字符之后紧跟 ASCII 字母即 LaTeX 命令；
        # 单个 \t、\r、\b 后面不是字母（或到字符串末尾）时仍是正常转义
        return bool(_word_at(text, index + 2))
    if char == "n":
        return _word_at(text, index + 1) in N_COMMANDS
    if char in _CONTROL_ESCAPES:
        return False  # \b \f \t \r 其余情况是正常转义（如单独的 \t、换行后的空白）
    return True  # \vec、\sqrt、\cdot、\underline、\{ 等非法转义


def repair_latex_escapes(raw: str) -> tuple[str, int]:
    """只在 JSON 字符串字面量内部把 LaTeX 反斜杠补成两个，返回 (修补后文本, 修补次数)。

    字符串外的内容与已经合法的转义（``\\\\``、``\\"``、``\\/``、``\\uXXXX``）不动。
    """
    out: list[str] = []
    repairs = 0
    in_string = False
    index = 0
    length = len(raw)
    while index < length:
        char = raw[index]
        if not in_string:
            if char == '"':
                in_string = True
            out.append(char)
            index += 1
            continue
        if char == '"':
            in_string = False
            out.append(char)
            index += 1
            continue
        if char != "\\":
            out.append(char)
            index += 1
            continue
        if _needs_repair(raw, index):
            out.append("\\\\")
            repairs += 1
            index += 1
            continue
        # 合法转义：两个字符原样输出（\uXXXX 其余的十六进制由后续循环逐字符带过）
        out.append(raw[index:index + 2])
        index += 2
    return "".join(out), repairs


def strip_fence(text: str) -> str:
    """剥除单层代码围栏：以 ``` 开头时去掉首行围栏标记与结尾围栏。

    合并了命题（只认开头）与备课（要求首尾都有）两处原有写法，结果只会更宽松。
    """
    text = (text or "").strip()
    if text.startswith("```"):
        text = _FENCE.sub("", text, count=1)
        text = re.sub(r"\n?```\s*$", "", text).strip()
    return text


def load_model_json(raw: str) -> tuple[Any, int]:
    """剥除单层代码围栏 → 修补字符串内的 LaTeX 反斜杠 → json.loads。

    返回 (对象, 修补次数)。不合法时抛 ModelJSONError，消息带 json 报出的行列。
    """
    text = strip_fence(raw)
    repaired, repairs = repair_latex_escapes(text)
    try:
        obj = json.loads(repaired)
    except (json.JSONDecodeError, ValueError) as exc:
        if isinstance(exc, json.JSONDecodeError):
            message = f"模型输出不是合法 JSON（第 {exc.lineno} 行第 {exc.colno} 列：{type(exc).__name__}）"
        else:
            message = f"模型输出不是合法 JSON（{type(exc).__name__}）"
        raise ModelJSONError(message) from exc
    if not isinstance(obj, dict):
        raise ModelJSONError("模型输出不是 JSON 对象")
    return obj, repairs
