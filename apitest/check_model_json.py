"""模型 JSON 解析与 LaTeX 反斜杠修补的离线单元用例（harden-model-json-escapes，tasks 4.1）。

不使用数据库、不启动服务、不调用网关，只验证 backend/model_json.py 的修补规则
与 design §7 列出的各类情况；样本由 2026-10-23 的真实失败输出提炼为最小片段，
真实输出含教师资料改编的题目与答案，不入仓库。

修补只作用于 JSON 字符串字面量内部，因此下面的片段都放进一个字段里再测。

用法（项目根）：
    PYTHONPATH=backend backend/.venv/bin/python apitest/check_model_json.py
"""

import json

from model_json import (
    N_COMMANDS,
    ModelJSONError,
    has_control_chars,
    load_model_json,
    repair_latex_escapes,
    strip_fence,
)

checks = []


def check(name, passed):
    checks.append((name, bool(passed)))


def in_string(fragment):
    """把片段包进一个 JSON 字段，得到模型输出里真实出现的形态。"""
    return '{"stem": "' + fragment + '"}'


def repaired(fragment):
    """修补后取回字段值与修补次数，便于按「还原成的 LaTeX」断言。"""
    text, count = repair_latex_escapes(in_string(fragment))
    return json.loads(text)["stem"], count


BS = "\\"  # 模型输出里的单个反斜杠
DBS = "\\\\"  # 模型输出里已正确转义的反斜杠

# ---- 1. 真实失败样本骨架：同一字符串混用两种写法（design §7）----
mixed = "由 $" + DBS + "overrightarrow{AB}=(1,0,1)$，$" + BS + "overrightarrow{AF}=(0,1,1)$，" \
        + BS + "vec{a}" + BS + "cdot" + BS + "vec{b}=|" + BS + "vec{a}|" + BS + "vec{b}|" + BS + "cos" + BS + "theta$，" \
        + "型 " + BS + "sqrt{2}" + BS + "neq 0$，$" + BS + "begin{cases}x=1" + DBS + "y=2" + BS + "end{cases}$，$" \
        + DBS + "frac{1}{2}$ 与 $" + BS + "frac{3}{4}$"
value, count = repaired(mixed)
# 单反斜杠命令依次为 \overrightarrow \vec \cdot \vec \vec \vec \cos \theta \sqrt \neq \begin \end \frac
check("混用样本：单反斜杠命令逐一修补（共 13 处）", count == 13)
check("混用样本：\\overrightarrow 两处都还原", value.count("\\overrightarrow{") == 2)
check("混用样本：\\vec \\cdot \\cos \\theta 还原", all(x in value for x in ("\\vec{a}", "\\cdot", "\\cos", "\\theta")))
check("混用样本：\\sqrt \\neq \\begin \\end 还原", all(x in value for x in ("\\sqrt{2}", "\\neq", "\\begin{cases}", "\\end{cases}")))
check("混用样本：\\frac 两处都还原为 LaTeX", value.count("\\frac{") == 2)
check("混用样本：不含任何控制字符", not has_control_chars(value))

# 已经写成 \\ 的合法转义不动：解出来仍是单个反斜杠命令
value, count = repaired("$" + DBS + "vec{a}$ 与 $" + DBS + "overrightarrow{AF}$ 与 $" + DBS + "frac{1}{2}$")
check("已是双反斜杠：不重复修补", count == 0)
check("已是双反斜杠：解出单个反斜杠命令", value == "$\\vec{a}$ 与 $\\overrightarrow{AF}$ 与 $\\frac{1}{2}$")

# ---- 2. \b \f \t \r 后紧跟字母：视为 LaTeX 命令 ----
for command in ["frac{1}{2}", "beta", "times", "right)", "begin{cases}", "rightleftharpoons"]:
    value, count = repaired("$ " + BS + command + " $")
    check(f"控制字符转义 + 字母补成 LaTeX：{command}", count == 1 and value == "$ \\" + command + " $")

# 单独的 \t、\r、\b 后面不是字母：保留为合法转义（换行、制表、回车原样）
# 注意 design §2：只有「\b \f \t \r 后紧跟 ASCII 字母」才补，其余情况保留
for label, fragment, expect in [
    ("换行 \\n 后接中文正文", "第一行" + BS + "n第二行", "第一行\n第二行"),
    ("换行 \\n 后接中文数字", "解：" + BS + "nx=2", "解：\nx=2"),
    ("单独的制表符（后面是引号）", "a" + BS + "t", "a\t"),
    ("单独的回车（后面是引号）", "a" + BS + "r", "a\r"),
    ("单独的退格（后面是引号）", "a" + BS + "b", "a\b"),
]:
    value, count = repaired(fragment)
    check(f"控制字符转义其余情况保留：{label}", count == 0 and value == expect)

# design §2 的取舍：\t \r \b 后只要紧跟字母就按 LaTeX 修补
value, count = repaired("a" + BS + "tb")
check("\\t 后紧跟字母按 LaTeX 修补（design §2 取舍）", count == 1 and value == "a\\tb")

# ---- 3. \n：白名单补，非白名单保留 ----
for command in ["neq", "nabla", "not", "nu", "nleq", "nsubseteq"]:
    value, count = repaired("$" + BS + command + "$")
    check(f"n 白名单命令补成 LaTeX：{command}", count == 1 and value == "$\\" + command + "$")
check("n 白名单与 design §2 一致（27 个）", len(N_COMMANDS) == 27
      and {"neq", "nabla", "not", "nu", "nolimits"} <= N_COMMANDS)
for fragment in [BS + "n第二步", BS + "nx=2", BS + "n ", BS + "n"]:
    value, count = repaired(fragment)
    check(f"n 非白名单保留为换行：{fragment!r}", count == 0)
# design §Risks 明示的误修补：以 \n 开头、恰好拼成白名单命令名的正文会被当成命令
value, count = repaired(BS + "ne")
check("n 起点正文恰为 \\ne 时按设计误修补（design §Risks）", count == 1 and value == "\\ne")

# ---- 4. 合法转义不动 ----
value, count = repaired(DBS + "frac \\\" 中文 " + BS + "/ " + BS + "u4e2d")
check("合法转义 \\\\、\\\"、\\/、\\uXXXX 均不修补", count == 0)
check("合法转义解出原字符", value == "\\frac \" 中文 / 中")
value, count = repaired(BS + "u12")
check("u 后不满 4 位十六进制按非法转义补", count == 1 and value == "\\u12")
value, count = repaired(BS + "uzzzz")
check("u 后不是十六进制按非法转义补", count == 1 and value == "\\uzzzz")
value, count = repaired("$" + BS + "u00b1$")
check("u 后 4 位十六进制保留为 Unicode 转义", count == 0 and value == "$±$")

# ---- 5. 其他非法转义补成两个 ----
for command in ["vec", "sqrt{2}", "cdot", "underline{x}", "{", "left(", "pmatrix"]:
    value, count = repaired("$ " + BS + command + " $")
    check(f"非法转义补成两个：{command}", count == 1 and value == "$ \\" + command + " $")
value, count = repair_latex_escapes('{"stem": "abc' + BS)
check("字符串末尾的孤立反斜杠补成两个", count == 1 and value == '{"stem": "abc' + DBS)

# ---- 6. 字符串外不动 ----
outside = '{"stem": "' + BS + 'vec a", "note": 1}\n{"second": "' + BS + 'frac"}'
value, count = repair_latex_escapes(outside)
check("两处字段各自修补、字符串外结构与引号不动",
      count == 2 and value == '{"stem": "' + DBS + 'vec a", "note": 1}\n{"second": "' + DBS + 'frac"}')
value, count = repair_latex_escapes(BS + 'vec {"a": "' + BS + 'vec"}')
check("字符串外的反斜杠不改动", count == 1 and value == BS + 'vec {"a": "' + DBS + 'vec"}')
check("多处字符串各自修补并累计",
      repair_latex_escapes('{"a":"' + BS + 'vec","b":"' + BS + 'sqrt"}') ==
      ('{"a":"' + DBS + 'vec","b":"' + DBS + 'sqrt"}', 2))

# ---- 7. 围栏剥除 ----
check("剥除 json 围栏", strip_fence('```json\n{"a":1}\n```') == '{"a":1}')
check("剥除无语言标记围栏", strip_fence('```\n{"a":1}\n```') == '{"a":1}')
check("未闭合的结尾围栏也剥除", strip_fence('```json\n{"a":1}') == '{"a":1}')
check("首尾空白先去掉", strip_fence('  \n{"a":1}\n  ') == '{"a":1}')

# ---- 8. 修补计数与解析结果 ----
raw = '```json\n{"api": "' + BS + 'vec", "keep": "' + BS + 'frac", "p": "$' + DBS + 'frac$"}\n```'
obj, count = load_model_json(raw)
check("load_model_json 返回对象与修补次数", count == 2)
check("修补后字段还原为 LaTeX 命令", obj == {"api": "\\vec", "keep": "\\frac", "p": "$\\frac$"})
obj, count = load_model_json('{"a": 1}')
check("无需修补时计数为 0", count == 0 and obj == {"a": 1})

# ---- 9. 不可修补：截断、正文、非对象仍失败 ----
truncated = '{"questions": [\n' + "\n" * 10 + '{"stem": "半截'
try:
    load_model_json(truncated)
    check("第 12 行中途截断抛 ModelJSONError", False)
except ModelJSONError as exc:
    check("截断失败消息带行号", "第 12 行" in str(exc) and "列" in str(exc))
try:
    load_model_json("## 立体几何\n\n这是正文，不是 JSON。")
    check("Markdown 正文抛 ModelJSONError", False)
except ModelJSONError as exc:
    check("正文失败消息带行列", "第 1 行" in str(exc) and "列" in str(exc))
try:
    load_model_json('["a", "b"]')
    check("JSON 数组而非对象抛 ModelJSONError", False)
except ModelJSONError as exc:
    check("非对象失败消息说明类型", "不是 JSON 对象" in str(exc))
check("缺 gaps 由调用方检查，解析本身成功", load_model_json('{"questions": []}')[0] == {"questions": []})

# ---- 10. 控制字符兜底 ----
check("检测换页 U+000C", has_control_chars("a\fb") is True)
check("检测退格 U+0008", has_control_chars("a\bb") is True)
check("制表符与回车不纳入兜底", has_control_chars("a\tb\rc") is False)
check("普通文本与空值不命中", has_control_chars("abc") is False and has_control_chars(None) is False)
# 模型若写成 \b{ 这种反斜杠后不是字母的形态，会保留为退格，由兜底拦截
decoded, _ = load_model_json('{"stem": "$' + BS + 'b{x}$"}')
check("\\b 后非字母保留为退格，能被兜底识别", has_control_chars(decoded["stem"]) is True)
# 合法写法解出的公式不含控制字符，不会被兜底误杀
obj, _ = load_model_json('{"stem": "$' + DBS + 'frac{1}{2}$ 与 $' + DBS + 'beta$"}')
check("合法双反斜杠公式不含控制字符", obj["stem"] == "$\\frac{1}{2}$ 与 $\\beta$" and not has_control_chars(obj["stem"]))

print("\n".join(("  ✓ " if ok else "  ✗ ") + name for name, ok in checks))
print(f"\n结果：{sum(1 for _, ok in checks if ok)}/{len(checks)} 通过")
failed = [name for name, ok in checks if not ok]
if failed:
    print("失败项：", failed)
    raise SystemExit(1)
