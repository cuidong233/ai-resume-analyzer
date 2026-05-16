from __future__ import annotations

import re
from typing import Optional

from app.models import BasicInfo, EducationItem, ProjectItem, ResumeProfile


SKILL_TERMS = {
    "python",
    "java",
    "go",
    "golang",
    "javascript",
    "typescript",
    "react",
    "vue",
    "fastapi",
    "flask",
    "django",
    "spring",
    "mysql",
    "postgresql",
    "redis",
    "mongodb",
    "docker",
    "kubernetes",
    "linux",
    "aws",
    "阿里云",
    "函数计算",
    "机器学习",
    "深度学习",
    "nlp",
    "大模型",
    "rag",
    "langchain",
    "pytorch",
    "tensorflow",
    "数据分析",
}


def extract_profile_by_rules(text: str) -> ResumeProfile:
    email = _first_match(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    phone = _first_match(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)", text)
    name = _guess_name(text)
    address = _first_match(r"(?:地址|现居|所在地)[:： ]{0,3}([^\n]{2,40})", text)
    salary = _first_match(r"(?:期望薪资|薪资期望)[:： ]{0,3}([^\n]{2,30})", text)
    intention = _first_match(r"(?:求职意向|应聘岗位|目标岗位)[:： ]{0,3}([^\n]{2,40})", text)
    years = _guess_years(text)
    skills = sorted({term for term in SKILL_TERMS if re.search(re.escape(term), text, re.IGNORECASE)})

    return ResumeProfile(
        basic=BasicInfo(name=name, phone=phone, email=email, address=address),
        job_intention=intention,
        expected_salary=salary,
        years_of_experience=years,
        education=_guess_education(text),
        skills=skills,
        projects=_guess_projects(text),
        summary=_make_summary(text),
    )


def extract_keywords_by_rules(text: str, limit: int = 24) -> list[str]:
    found = {term for term in SKILL_TERMS if re.search(re.escape(term), text, re.IGNORECASE)}
    cn_terms = re.findall(r"[\u4e00-\u9fa5A-Za-z0-9+#.]{2,20}", text)
    stop_words = {"岗位", "负责", "要求", "经验", "能力", "熟悉", "优先", "相关", "以上", "以及"}
    for term in cn_terms:
        if term.lower() in found or term in stop_words:
            continue
        if any(token in term.lower() for token in ("python", "java", "react", "redis", "sql", "docker")):
            found.add(term)
        elif term in {"大模型", "机器学习", "自然语言处理", "数据分析", "后端开发", "前端开发"}:
            found.add(term)
    return sorted(found, key=lambda item: (-len(item), item.lower()))[:limit]


def _first_match(pattern: str, text: str) -> Optional[str]:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    return (match.group(1) if match.lastindex else match.group(0)).strip(" ：:\t")


def _guess_name(text: str) -> Optional[str]:
    for line in text.splitlines()[:8]:
        line = line.strip()
        if not line or any(token in line for token in ("电话", "手机", "邮箱", "@", "简历")):
            continue
        if re.fullmatch(r"[\u4e00-\u9fa5]{2,4}", line):
            return line
        labeled = re.search(r"(?:姓名|Name)[:： ]{0,3}([\u4e00-\u9fa5A-Za-z ]{2,30})", line, re.IGNORECASE)
        if labeled:
            return labeled.group(1).strip()
    return None


def _guess_years(text: str) -> Optional[float]:
    match = re.search(r"(\d+(?:\.\d+)?)\s*年(?:以上)?(?:工作)?经验", text)
    return float(match.group(1)) if match else None


def _guess_education(text: str) -> list[EducationItem]:
    degree = _first_match(r"(博士|硕士|研究生|本科|大专|专科)", text)
    school = _first_match(r"([\u4e00-\u9fa5A-Za-z ]{2,30}(?:大学|学院|University|College))", text)
    major = _first_match(r"(?:专业)[:： ]{0,3}([^\n]{2,30})", text)
    return [EducationItem(school=school, degree=degree, major=major)] if any([degree, school, major]) else []


def _guess_projects(text: str) -> list[ProjectItem]:
    projects: list[ProjectItem] = []
    chunks = re.split(r"(?:项目经历|项目经验)", text, maxsplit=1)
    if len(chunks) == 2:
        for block in re.split(r"\n\s*\n", chunks[1])[:3]:
            clean = block.strip()
            if len(clean) > 20:
                projects.append(ProjectItem(description=clean[:260]))
    return projects


def _make_summary(text: str) -> str:
    one_line = re.sub(r"\s+", " ", text).strip()
    return one_line[:180]
