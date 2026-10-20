"""校验本轮来源编号；不把编号有效当作论断已被语义验证。"""
import hashlib
import re
from pathlib import Path

REFERENCE = re.compile(r"\[(\d+)\]")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_references(answer: str, candidates):
    """只保留回答实际使用的来源，保留原编号，剔除模型杜撰编号/链接。"""
    answer = re.sub(r"\[(\d+)\]\([^)]*\)", r"[\1]", answer)
    mapping = {c.reference_id: c for c in candidates}
    invalid = False
    used = set()
    def replace(match):
        nonlocal invalid
        ref = int(match.group(1))
        if ref not in mapping:
            invalid = True
            return "（无有效来源）"
        used.add(ref)
        return f"[{ref}]"
    answer = REFERENCE.sub(replace, answer)
    if invalid:
        answer += "\n\n部分引用编号没有本轮资料依据，已移除；相关结论尚未核实。"
    return answer, [c for c in candidates if c.reference_id in used]
