"""按班级、学科、任课教师解析学生助手；不共享或覆盖其他教师配置。"""
import json
import re
from typing import Literal

from fastapi import HTTPException
from models import AgentConfig, Role, User

Subject = Literal["math", "chinese", "english", "physics", "chemistry", "biology"]
SUBJECT_NAMES = {"math": "数学", "chinese": "语文", "english": "英语", "physics": "物理", "chemistry": "化学", "biology": "生物"}


FOLLOWUP_WORDS = {
    '不会', '不知道', '不懂', '没懂', '不明白', '明白了', '懂了', '是', '不是', '对', '不对',
    '会', '能', '不能', '继续', '下一步', '然后呢', '接下来呢', '为什么', '为什么呢',
    '怎么做', '怎么算', '怎么来的', '再讲一遍', '再解释一下', '提示一下', '给个提示',
    '为什么是这样', '是这样吗', '对吗', '这样对吗',
}


def _is_short_followup(text: str) -> bool:
    compact = re.sub(r'[\s，。！？、,.!?；;：:]+', '', text)
    if compact in FOLLOWUP_WORDS:
        return True
    # 数值或简短公式作答；带中文的独立新问题不被当成前题追问。
    return bool(compact and len(compact) <= 80
                and not re.search(r'[\u3400-\u9fff]', compact)
                and not re.search(r'[A-Za-z]{5,}', compact)
                and re.search(r'\d', compact)
                and (not re.search(r'[A-Za-z]', compact) or re.search(r'[=+\-*/^<>≤≥≠]', compact))
                and re.fullmatch(r'[A-Za-z0-9_\s+\-*/^=().,<>≤≥≠±×÷√π²³{}\\$|]+', compact))


def followup_retrieval_query(question: str, history: list[tuple[str, str]]) -> str:
    """仅为明确短追问补充最近用户题目；重新检索，不沿用历史引用。"""
    if not _is_short_followup(question):
        return question
    for role, text in reversed(history[-12:]):
        if role == 'user' and text.strip() and not _is_short_followup(text):
            # 过长题目不截断条件，直接维持本轮查询；历史仍供对话理解。
            if len(text) <= 2000:
                return f'{text}\n学生追问：{question}'
            break
    return question


def resolve_assistant(db, class_id: int, subject: str, teacher_id: int | None = None):
    teachers = db.query(User).filter(User.role == Role.teacher, User.subject == subject).order_by(User.id).all()
    eligible = []
    for teacher in teachers:
        try:
            if class_id in json.loads(teacher.teaching_classes or "[]"):
                eligible.append(teacher)
        except (ValueError, TypeError):
            continue
    if teacher_id is not None:
        eligible = [t for t in eligible if t.id == teacher_id]
        if not eligible:
            raise HTTPException(status_code=409, detail="任课老师已调整，请新建本学科对话")
    if not eligible:
        return None, None
    configs = db.query(AgentConfig).filter(
        AgentConfig.class_id == class_id, AgentConfig.subject == subject,
        AgentConfig.teacher_id.in_([t.id for t in eligible]),
    ).order_by(AgentConfig.updated_at.desc(), AgentConfig.id.desc()).all()
    cfg = configs[0] if configs else None
    teacher = next(t for t in eligible if t.id == cfg.teacher_id) if cfg else eligible[0]
    return cfg, teacher
