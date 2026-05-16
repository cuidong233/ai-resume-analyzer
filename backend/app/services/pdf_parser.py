from __future__ import annotations

from io import BytesIO

from fastapi import HTTPException, UploadFile
from pypdf import PdfReader

from app.services.text_utils import clean_resume_text, split_sections


async def parse_pdf_upload(file: UploadFile, max_upload_mb: int) -> tuple[str, list[str]]:
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="仅支持 PDF 文件上传")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空")

    max_bytes = max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"文件不能超过 {max_upload_mb}MB")

    try:
        reader = PdfReader(BytesIO(content))
        page_texts = []
        for page in reader.pages:
            page_texts.append(page.extract_text() or "")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="PDF 解析失败，请确认文件未加密且可复制文本") from exc

    text = clean_resume_text("\n\n".join(page_texts))
    if not text:
        raise HTTPException(status_code=422, detail="未能从 PDF 中提取文本，扫描件请先 OCR")

    return text, split_sections(text)
