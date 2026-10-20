"""教师组内 Markdown 图文入库、学生版草稿与发布准备。"""
import hashlib
import io
import json
import re
import zipfile
from pathlib import PurePosixPath
from urllib.parse import unquote

from material_service import MAX_FILE_SIZE, validate_upload_file

IMAGE = re.compile(r"!\[([^\]\n]*)\]\(([^)\n]+)\)")
TEACHER_LABEL = re.compile(r"(?:\*\*|【|^#{1,6}\s*)(?:参考)?(?:答案|解答|解法|解析|详解|分析|教学提示|条件说明|教师用|教师版)", re.M)


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def safe_name(raw: str) -> str:
    name = unquote(raw).replace("\\", "/")
    parts = PurePosixPath(name).parts
    if not name or name.startswith("/") or any(p in ("..", ".") for p in parts) or ":" in name or "\x00" in name:
        raise ValueError("资料包包含非法路径")
    return "/".join(parts)


def unpack_markdown(data: bytes, filename: str) -> tuple[str, bytes, str, dict]:
    if len(data) > MAX_FILE_SIZE:
        raise ValueError("文件不能超过 50MB")
    assets = {}
    if filename.lower().endswith(".zip"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                entries = [e for e in z.infolist() if not e.is_dir()]
                if len(entries) > 100 or sum(e.file_size for e in entries) > MAX_FILE_SIZE:
                    raise ValueError("资料包最多 100 个文件，解压总量不能超过 50MB")
                names = [safe_name(e.filename) for e in entries]
                if len(set(names)) != len(names) or any((e.external_attr >> 16) & 0o170000 == 0o120000 for e in entries):
                    raise ValueError("资料包存在重复路径或符号链接")
                documents = [(e, n) for e, n in zip(entries, names) if n.lower().endswith(".md")]
                if len(documents) != 1:
                    raise ValueError("资料包需要且只能包含一份 Markdown")
                entry, document_name = documents[0]
                raw = z.read(entry)
                parent = PurePosixPath(document_name).parent
                for e, name in zip(entries, names):
                    if name == document_name or name.lower().endswith(".json"):
                        continue  # 来源核对记录不发布给学生。
                    if not name.lower().endswith((".png", ".jpg", ".jpeg")):
                        raise ValueError("资料包只允许 Markdown、PNG/JPG 和来源 JSON")
                    relative = str(PurePosixPath(name).relative_to(parent)) if parent != PurePosixPath('.') else name
                    content = z.read(e)
                    mime, _ = validate_upload_file(content, relative)
                    if not mime.startswith("image/"):
                        raise ValueError("配图类型不正确")
                    assets[relative] = (content, mime)
                filename = PurePosixPath(document_name).name
        except (zipfile.BadZipFile, KeyError, RuntimeError) as exc:
            raise ValueError("资料包无法读取") from exc
    elif filename.lower().endswith(".md"):
        raw = data
        filename = PurePosixPath(filename.replace('\\', '/')).name
    else:
        raise ValueError("当前教师资料导入支持 .md 或包含 Markdown 与配图的 .zip")
    if len(filename) > 255:
        raise ValueError("文件名过长")
    text = raw.decode("utf-8-sig")
    if not text.strip():
        raise ValueError("Markdown 内容为空")
    for _, target in IMAGE.findall(text):
        name = safe_name(target.strip())
        if name not in assets:
            raise ValueError("Markdown 引用了缺失配图，请将 Markdown 与配图一起打包导入")
    return filename, raw, text, assets


def student_draft(text: str) -> str:
    """只提取明确的知识点区和例题题干；遇到未知格式不猜测答案边界。"""
    title = next((line.removeprefix('# ').strip() for line in text.splitlines() if line.startswith('# ')), '学习讲义')
    output = [f"# {title}（学生版）"]
    knowledge = re.search(r"(?ms)^##\s*二[、.．].*?(?=^##\s|\Z)", text)
    if knowledge:
        # 教师特别提示也不混入学生知识点区。
        body = re.sub(r"(?m)^\*\*(?:教学提示|条件说明).*\n?", "", knowledge[0])
        output.append(body.strip())
    count = 0
    for block in re.split(r"(?m)(?=^###\s+例题\s)", text):
        if not block.startswith("###"):
            continue
        question = re.search(r"(?s)\*\*题干\*\*[：:]?\s*(.*?)(?=\*\*(?:参考)?(?:答案|解答|解法|解析|详解)|\Z)", block)
        if not question:
            continue
        heading = block.splitlines()[0]
        question_text = re.split(r"(?m)^##\s", question[1])[0].strip()
        if not question_text:
            continue
        output.extend([heading, question_text, "**作答区**：\n\n______________________________"])
        count += 1
    if not count:
        raise ValueError("未识别到明确的例题题干与答案分区，请先按“### 例题 / **题干** / **答案**”整理教师版")
    result = '\n\n'.join(output) + '\n'
    validate_student_text(result)
    return result


def validate_student_text(text: str) -> None:
    if not text.strip() or len(text.encode('utf-8')) > 2 * 1024 * 1024:
        raise ValueError("学生版内容为空或超过 2MB")
    if TEACHER_LABEL.search(text):
        raise ValueError("学生版仍包含答案、解析或教师说明标记，请检查后再发布")
    # 禁止学生稿链接教师源文件、私有接口和不受管理的资源。
    without_images = IMAGE.sub('', text)
    if re.search(r"\[[^\]]*\]\(|</?[A-Za-z][A-Za-z0-9:-]*(?:\s+[^<>]*?)?\s*/?>|<!--|<!DOCTYPE|https?://|file:|/api/", without_images, re.I):
        raise ValueError("学生版只允许正文和组内配图，不得包含外部链接或教师原文链接")
    for _, target in IMAGE.findall(text):
        safe_name(target.strip())
