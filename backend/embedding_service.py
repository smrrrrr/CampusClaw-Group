"""向量化服务（design.md 决策 2/3）。

字符 n-gram 哈希向量：对文本做字符 bigram/trigram 哈希 + TF 加权，得到定长稠密向量。
离线可用、零外部依赖，适用于"限定班级召回相关片段"。

向量持久化：嵌入服务输出 list[float]，调用方负责存为 BLOB（float32 bytes）。
"""

from __future__ import annotations

import hashlib
import math

from config import settings

# 与持久化 BLOB 配套：向量元素均为 float32
_NGRAM_SIZES = (2, 3)


def _hashed_index(part: str, dim: int) -> int:
    """对 n-gram 片段做确定性哈希，映射到 [0, dim)。"""
    h = hashlib.md5(part.encode("utf-8")).hexdigest()
    return int(h[:8], 16) % dim


def embed_text(text: str) -> list[float]:
    """将文本向量化为 dim 维字符串-哈希向量（bigram/trigram + TF 加权）。

    输出为定长 list[float]，向量元素不做缩放（余弦相似度会归一化，无需 L2 归一化存储）。
    """
    dim = settings.embed_dim
    vec = [0.0] * dim
    text = (text or "").strip()
    if not text:
        return vec

    safetext = text.lower()
    for size in _NGRAM_SIZES:
        for i in range(len(safetext) - size + 1):
            part = safetext[i : i + size]
            if not part.strip():
                continue
            vec[_hashed_index(part, dim)] += 1.0

    return vec


def vector_norm(vec: list[float]) -> float:
    """返回向量 L2 范数；空向量为 0。"""
    total = 0.0
    for x in vec:
        total += x * x
    return math.sqrt(total)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """计算两向量余弦相似度（单位向量自相似度为 1，正交为 0，零向量为 0）。"""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    denom = math.sqrt(na) * math.sqrt(nb)
    if denom == 0.0:
        return 0.0
    return dot / denom


def cosine_similarity_with_norm(a: list[float], norm_a: float, b: list[float]) -> float:
    """已知左向量范数时的余弦相似度；用于同一查询对多个分块重复比较。

    与 cosine_similarity 的累加顺序一致，只省去重复计算查询范数。
    """
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        nb += y * y
    denom = norm_a * math.sqrt(nb)
    if denom == 0.0:
        return 0.0
    return dot / denom