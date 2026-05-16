from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import Settings
from app.models import MatchResponse, ResumeProfile, ScoreBreakdown
from app.services.rules import extract_keywords_by_rules, extract_profile_by_rules


PROFILE_SCHEMA: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "resume_profile",
        "schema": ResumeProfile.model_json_schema(),
        "strict": False,
    },
}


class AIClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self.settings.openai_api_key)

    async def extract_profile(self, text: str) -> ResumeProfile:
        fallback = extract_profile_by_rules(text)
        if not self.enabled:
            return fallback

        prompt = (
            "请从候选人简历中提取结构化信息。只输出符合 schema 的 JSON。"
            "如果字段缺失，使用 null 或空数组，不要编造。"
        )
        try:
            data = await self._chat_json(
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text[:12000]},
                ],
                response_format=PROFILE_SCHEMA,
            )
            parsed = ResumeProfile.model_validate(data)
            return _merge_profile(fallback, parsed)
        except Exception:
            return fallback

    async def refine_match(
        self,
        resume_text: str,
        job_description: str,
        base_response: MatchResponse,
    ) -> MatchResponse:
        if not self.enabled:
            return base_response

        schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "match_result",
                "schema": MatchResponse.model_json_schema(),
                "strict": False,
            },
        }
        prompt = (
            "你是招聘简历筛选助手。请基于简历和岗位 JD 复核匹配度。"
            "评分范围 0-100，维度评分也为 0-100。保持关键词客观，不要编造候选人经历。"
        )
        try:
            data = await self._chat_json(
                messages=[
                    {"role": "system", "content": prompt},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "resume_text": resume_text[:9000],
                                "job_description": job_description[:5000],
                                "base_result": base_response.model_dump(),
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
                response_format=schema,
            )
            refined = MatchResponse.model_validate(data)
            refined.resume_id = base_response.resume_id
            return refined
        except Exception:
            return base_response

    async def extract_job_keywords(self, job_description: str) -> list[str]:
        fallback = extract_keywords_by_rules(job_description)
        if not self.enabled:
            return fallback

        try:
            data = await self._chat_json(
                messages=[
                    {"role": "system", "content": "从岗位 JD 中提取招聘筛选关键词，输出 JSON: {\"keywords\": string[]}。"},
                    {"role": "user", "content": job_description[:5000]},
                ],
                response_format={"type": "json_object"},
            )
            keywords = data.get("keywords", [])
            if isinstance(keywords, list):
                merged = [str(item).strip() for item in keywords if str(item).strip()]
                return list(dict.fromkeys([*merged, *fallback]))[:30]
        except Exception:
            return fallback

        return fallback

    async def _chat_json(self, messages: list[dict[str, str]], response_format: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.settings.openai_base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self.settings.openai_model,
            "messages": messages,
            "temperature": 0.1,
            "response_format": response_format,
        }
        headers = {"Authorization": f"Bearer {self.settings.openai_api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)


def _merge_profile(rule_profile: ResumeProfile, ai_profile: ResumeProfile) -> ResumeProfile:
    data = ai_profile.model_dump()
    rule_data = rule_profile.model_dump()

    for key, value in rule_data["basic"].items():
        if not data["basic"].get(key) and value:
            data["basic"][key] = value

    for key in ("skills", "education", "projects"):
        if not data.get(key):
            data[key] = rule_data.get(key, [])

    for key in ("job_intention", "expected_salary", "years_of_experience", "summary"):
        if data.get(key) is None and rule_data.get(key) is not None:
            data[key] = rule_data[key]

    return ResumeProfile.model_validate(data)
