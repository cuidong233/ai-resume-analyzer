from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.config import Settings, get_settings
from app.models import MatchRequest, MatchResponse, ResumeParseResponse, ResumeProfile
from app.services.ai_client import AIClient
from app.services.cache import Cache
from app.services.matcher import build_match_response
from app.services.pdf_parser import parse_pdf_upload
from app.services.text_utils import clean_resume_text, split_sections

settings = get_settings()
cache = Cache(settings.redis_url)

app = FastAPI(
    title="AI Resume Analyzer",
    description="PDF 简历解析、AI 关键信息提取、岗位匹配评分服务",
    version="1.0.0",
    docs_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def force_inline_content_disposition(request, call_next):
    response = await call_next(request)
    response.headers["Content-Disposition"] = "inline"
    return response


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"status": "ok", "ai_enabled": bool(settings.openai_api_key), "redis_enabled": bool(settings.redis_url)}


@app.get("/docs", include_in_schema=False)
async def custom_docs() -> HTMLResponse:
    return HTMLResponse(
        """
<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8" />
    <title>AI Resume Analyzer - Swagger UI</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
      async function fetchSpecWithRetry(url, retries = 4) {
        let lastError;
        for (let attempt = 0; attempt <= retries; attempt += 1) {
          try {
            const response = await fetch(url, { cache: "no-store" });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
          } catch (error) {
            lastError = error;
            await new Promise((resolve) => setTimeout(resolve, 400 * (attempt + 1)));
          }
        }
        throw lastError;
      }

      fetchSpecWithRetry("/openapi.json")
        .then((spec) => {
          SwaggerUIBundle({
            spec,
            dom_id: "#swagger-ui",
            layout: "BaseLayout",
            deepLinking: true,
            showExtensions: true,
            showCommonExtensions: true,
            presets: [
              SwaggerUIBundle.presets.apis,
              SwaggerUIBundle.SwaggerUIStandalonePreset,
            ],
          });
        })
        .catch((error) => {
          document.getElementById("swagger-ui").innerHTML =
            `<pre style="padding:24px;color:#b63838">OpenAPI 加载失败：${error.message}</pre>`;
        });
    </script>
  </body>
</html>
        """,
        headers={"Content-Disposition": "inline"},
    )


@app.post("/api/resumes", response_model=ResumeParseResponse)
async def upload_resume(file: UploadFile, current_settings: Settings = Depends(get_settings)) -> ResumeParseResponse:
    text, sections = await parse_pdf_upload(file, current_settings.max_upload_mb)
    resume_id = _resume_id(text)
    cached = cache.get(_resume_key(resume_id))
    if cached:
        cached["cache_hit"] = True
        return ResumeParseResponse.model_validate(cached)

    ai = AIClient(current_settings)
    profile = await ai.extract_profile(text)
    response = ResumeParseResponse(
        resume_id=resume_id,
        file_name=file.filename or "resume.pdf",
        text=text,
        sections=sections,
        profile=profile,
    )
    cache.set(_resume_key(resume_id), response.model_dump())
    return response


@app.post("/api/match", response_model=MatchResponse)
async def match_resume(payload: MatchRequest, current_settings: Settings = Depends(get_settings)) -> MatchResponse:
    resume_id = payload.resume_id
    resume_text = payload.resume_text
    profile = ResumeProfile()

    if resume_id:
        cached_resume = cache.get(_resume_key(resume_id))
        if not cached_resume:
            raise HTTPException(status_code=404, detail="未找到该 resume_id，请重新上传简历或传入 resume_text")
        resume_text = cached_resume["text"]
        profile = ResumeProfile.model_validate(cached_resume["profile"])
    elif resume_text:
        resume_text = clean_resume_text(resume_text)
        resume_id = _resume_id(resume_text)
        ai = AIClient(current_settings)
        profile = await ai.extract_profile(resume_text)
    else:
        raise HTTPException(status_code=400, detail="resume_id 和 resume_text 至少提供一个")

    match_key = _match_key(resume_id, payload.job_description)
    cached_match = cache.get(match_key)
    if cached_match:
        cached_match["cache_hit"] = True
        return MatchResponse.model_validate(cached_match)

    ai = AIClient(current_settings)
    job_keywords = await ai.extract_job_keywords(payload.job_description)
    base_response = await build_match_response(resume_id, resume_text, profile, payload.job_description, job_keywords)
    refined = await ai.refine_match(resume_text, payload.job_description, base_response)
    cache.set(match_key, refined.model_dump())
    return refined


@app.post("/api/resumes/text", response_model=ResumeParseResponse)
async def parse_resume_text(payload: dict[str, str], current_settings: Settings = Depends(get_settings)) -> ResumeParseResponse:
    text = clean_resume_text(payload.get("text", ""))
    if len(text) < 20:
        raise HTTPException(status_code=400, detail="简历文本过短")

    resume_id = _resume_id(text)
    cached = cache.get(_resume_key(resume_id))
    if cached:
        cached["cache_hit"] = True
        return ResumeParseResponse.model_validate(cached)

    ai = AIClient(current_settings)
    response = ResumeParseResponse(
        resume_id=resume_id,
        file_name="manual-input.txt",
        text=text,
        sections=split_sections(text),
        profile=await ai.extract_profile(text),
    )
    cache.set(_resume_key(resume_id), response.model_dump())
    return response


def _resume_id(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:20]


def _resume_key(resume_id: str) -> str:
    return f"resume:{resume_id}"


def _match_key(resume_id: Optional[str], job_description: str) -> str:
    digest = hashlib.sha256(f"{resume_id}:{job_description}".encode("utf-8")).hexdigest()[:24]
    return f"match:{digest}"
