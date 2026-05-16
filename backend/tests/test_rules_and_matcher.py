import pytest

from app.services.matcher import build_match_response
from app.services.rules import extract_profile_by_rules


@pytest.mark.asyncio
async def test_profile_rule_extraction():
    text = """
    张三
    电话：13800138000
    邮箱：zhangsan@example.com
    求职意向：Python 后端开发
    本科 北京大学 计算机专业
    5年工作经验，熟悉 Python FastAPI Redis Docker
    """

    profile = extract_profile_by_rules(text)

    assert profile.basic.name == "张三"
    assert profile.basic.phone == "13800138000"
    assert profile.basic.email == "zhangsan@example.com"
    assert profile.years_of_experience == 5
    assert "python" in profile.skills


@pytest.mark.asyncio
async def test_match_response_scores_keywords():
    resume = "5年 Python 后端开发经验，熟悉 FastAPI、Redis、Docker，有大模型 RAG 项目经历。"
    profile = extract_profile_by_rules(resume)
    jd = "招聘 Python 后端工程师，要求 3年经验，熟悉 FastAPI Redis Docker，了解 RAG 优先。"

    result = await build_match_response("abc", resume, profile, jd)

    assert result.score >= 70
    assert "python" in [item.lower() for item in result.matched_keywords]
