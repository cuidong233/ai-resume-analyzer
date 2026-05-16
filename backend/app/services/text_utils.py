import re


SECTION_TITLES = (
    "基本信息",
    "个人信息",
    "求职意向",
    "教育经历",
    "教育背景",
    "工作经历",
    "项目经历",
    "专业技能",
    "技能清单",
    "自我评价",
)


def clean_resume_text(raw_text: str) -> str:
    text = raw_text.replace("\x00", " ").replace("\u3000", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"(?m)^\s*第\s*\d+\s*页\s*$", "", text)
    text = re.sub(r"(?m)^\s*page\s*\d+\s*$", "", text, flags=re.IGNORECASE)
    return text.strip()


def split_sections(text: str) -> list[str]:
    normalized = clean_resume_text(text)
    if not normalized:
        return []

    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    sections: list[str] = []
    current: list[str] = []

    for line in lines:
        is_title = any(title in line for title in SECTION_TITLES) and len(line) <= 20
        if is_title and current:
            sections.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)

    if current:
        sections.append("\n".join(current).strip())

    if len(sections) <= 1 and len(normalized) > 900:
        paragraphs = re.split(r"\n\s*\n", normalized)
        sections = [paragraph.strip() for paragraph in paragraphs if paragraph.strip()]

    return sections[:24]


def normalize_keyword(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())
