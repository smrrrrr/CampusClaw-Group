"""从资料标题、知识点标题提取有文本依据的标签，不调用模型猜测。"""
import re


TOPICS = {
    "math": (
        "立体几何", "空间向量", "平面向量", "解析几何", "圆锥曲线", "椭圆", "双曲线", "抛物线",
        "三角函数", "解三角形", "二次函数", "指数函数", "对数函数", "函数", "导数", "数列",
        "一元二次方程", "不等式", "集合", "复数", "概率", "统计", "排列组合", "二项式定理",
    ),
    "physics": (
        "运动学", "匀变速直线运动", "牛顿运动定律", "力与运动", "圆周运动", "万有引力",
        "动量", "机械能", "电场", "电路", "磁场", "电磁感应", "机械振动", "机械波", "光学", "热学", "光电效应",
    ),
    "chinese": ("文言文", "古诗词", "现代文阅读", "议论文", "写作", "小说", "散文"),
    "english": ("定语从句", "名词性从句", "状语从句", "非谓语动词", "时态", "语态", "阅读理解", "写作"),
    "chemistry": ("物质的量", "氧化还原反应", "离子反应", "化学平衡", "电化学", "有机化学", "化学反应速率"),
    "biology": ("细胞", "遗传", "进化", "光合作用", "细胞呼吸", "稳态", "生态系统"),
}


def knowledge_tags(filename: str, content: str, subject: str) -> list[str]:
    topics = TOPICS.get(subject, ())
    titles = '\n'.join(re.findall(r'^#\s+(.+)$', content, re.M))
    # 文件名和一级标题优先于例题中偶然出现的其他知识点。
    chapter = re.sub(r'\s+', '', filename + '\n' + titles)
    result = [topic for topic in topics if topic in chapter]
    if not result:
        headings = '\n'.join(re.findall(r'^#{2,6}\s+(.+)$', content, re.M))
        result = [topic for topic in topics if topic in headings]
    if not result:
        # 标题没有可识别主题时，仅接受正文多次出现的明确术语。
        result = [topic for topic in topics if content.count(topic) >= 2]
    if '立体几何' in result:
        result = [topic for topic in result if topic != '空间向量']
    if any(topic != '函数' and topic.endswith('函数') for topic in result):
        result = [topic for topic in result if topic != '函数']
    return result[:3]
