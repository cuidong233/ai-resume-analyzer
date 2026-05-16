from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class BasicInfo(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


class EducationItem(BaseModel):
    school: Optional[str] = None
    degree: Optional[str] = None
    major: Optional[str] = None
    period: Optional[str] = None


class ProjectItem(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    description: Optional[str] = None
    technologies: list[str] = Field(default_factory=list)


class ResumeProfile(BaseModel):
    basic: BasicInfo = Field(default_factory=BasicInfo)
    job_intention: Optional[str] = None
    expected_salary: Optional[str] = None
    years_of_experience: Optional[float] = None
    education: list[EducationItem] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    summary: Optional[str] = None


class ResumeParseResponse(BaseModel):
    resume_id: str
    file_name: str
    text: str
    sections: list[str]
    profile: ResumeProfile
    cache_hit: bool = False


class MatchRequest(BaseModel):
    job_description: str = Field(min_length=10)
    resume_id: Optional[str] = None
    resume_text: Optional[str] = None


class ScoreBreakdown(BaseModel):
    skill_match: float
    experience_relevance: float
    education_match: float
    keyword_coverage: float


class MatchResponse(BaseModel):
    resume_id: Optional[str] = None
    score: float
    breakdown: ScoreBreakdown
    job_keywords: list[str]
    matched_keywords: list[str]
    missing_keywords: list[str]
    ai_comment: str
    cache_hit: bool = False
