from __future__ import annotations

from typing import Optional

from app.models import MatchResponse, ResumeProfile, ScoreBreakdown
from app.services.rules import extract_keywords_by_rules
from app.services.text_utils import normalize_keyword


async def build_match_response(
    resume_id: Optional[str],
    resume_text: str,
    profile: ResumeProfile,
    job_description: str,
    job_keywords: Optional[list[str]] = None,
) -> MatchResponse:
    keywords = job_keywords or extract_keywords_by_rules(job_description)
    normalized_resume = normalize_keyword(resume_text + " " + " ".join(profile.skills))
    normalized_keywords = [(kw, normalize_keyword(kw)) for kw in keywords]

    matched = [kw for kw, normalized in normalized_keywords if normalized and normalized in normalized_resume]
    missing = [kw for kw in keywords if kw not in matched]

    keyword_coverage = _ratio_score(len(matched), len(keywords))
    skill_match = _skill_score(profile.skills, keywords, matched)
    experience_relevance = _experience_score(profile.years_of_experience, job_description, normalized_resume)
    education_match = _education_score(profile, job_description)
    score = round(skill_match * 0.4 + experience_relevance * 0.25 + education_match * 0.15 + keyword_coverage * 0.2, 1)

    return MatchResponse(
        resume_id=resume_id,
        score=score,
        breakdown=ScoreBreakdown(
            skill_match=skill_match,
            experience_relevance=experience_relevance,
            education_match=education_match,
            keyword_coverage=keyword_coverage,
        ),
        job_keywords=keywords,
        matched_keywords=matched,
        missing_keywords=missing,
        ai_comment=_comment(score, matched, missing, profile.years_of_experience),
    )


def _ratio_score(hit: int, total: int) -> float:
    if total <= 0:
        return 60.0
    return round(min(100.0, hit / total * 100), 1)


def _skill_score(skills: list[str], keywords: list[str], matched: list[str]) -> float:
    if not keywords:
        return 60.0
    skill_hits = 0
    normalized_skills = {normalize_keyword(skill) for skill in skills}
    for keyword in keywords:
        normalized = normalize_keyword(keyword)
        if normalized in normalized_skills or keyword in matched:
            skill_hits += 1
    return _ratio_score(skill_hits, len(keywords))


def _experience_score(years: Optional[float], job_description: str, normalized_resume: str) -> float:
    required_years = _extract_required_years(job_description)
    if years is not None and required_years is not None:
        return round(min(100.0, years / required_years * 100), 1)
    if any(token in normalized_resume for token in ("项目", "负责", "上线", "优化", "架构", "owner")):
        return 72.0
    return 50.0


def _education_score(profile: ResumeProfile, job_description: str) -> float:
    degrees = " ".join(item.degree or "" for item in profile.education)
    if not profile.education:
        return 55.0
    if "本科" in job_description and any(token in degrees for token in ("本科", "硕士", "研究生", "博士")):
        return 90.0
    if "硕士" in job_description and any(token in degrees for token in ("硕士", "研究生", "博士")):
        return 90.0
    return 75.0


def _extract_required_years(text: str) -> Optional[float]:
    import re

    match = re.search(r"(\d+(?:\.\d+)?)\s*年(?:以上)?(?:工作)?经验", text)
    return float(match.group(1)) if match else None


def _comment(score: float, matched: list[str], missing: list[str], years: Optional[float]) -> str:
    if score >= 80:
        level = "匹配度较高，建议进入下一轮筛选。"
    elif score >= 60:
        level = "匹配度中等，建议结合项目细节和面试表现继续判断。"
    else:
        level = "匹配度偏低，关键要求覆盖不足。"

    hit_text = "、".join(matched[:6]) if matched else "暂无明显命中关键词"
    miss_text = "、".join(missing[:6]) if missing else "核心关键词覆盖较完整"
    year_text = f"候选人约 {years:g} 年经验。" if years is not None else "简历中未明确工作年限。"
    return f"{level}命中：{hit_text}。待确认：{miss_text}。{year_text}"
