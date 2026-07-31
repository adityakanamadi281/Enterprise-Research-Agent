from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from pypdf import PdfReader

from app.config import settings

ALLOWED_TYPES = {"application/pdf", "text/plain", "text/markdown", "text/csv", "application/json"}


async def store_and_extract(upload: UploadFile) -> tuple[Path, str, int]:
    if upload.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, "Supported uploads: PDF, TXT, Markdown, CSV, and JSON")
    data = await upload.read()
    if not data:
        raise HTTPException(422, "Uploaded file is empty")
    if len(data) > settings().max_upload_bytes:
        raise HTTPException(
            413, f"File exceeds {settings().max_upload_bytes // (1024 * 1024)} MB limit"
        )
    target_dir = Path(settings().upload_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(upload.filename or "upload").name
    path = target_dir / f"{uuid4()}-{safe_name}"
    path.write_bytes(data)
    if upload.content_type == "application/pdf":
        try:
            text = "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
        except Exception as exc:
            raise HTTPException(422, "Could not extract text from this PDF") from exc
    else:
        text = data.decode("utf-8", errors="replace")
    if not text.strip():
        raise HTTPException(422, "No extractable text found in the uploaded file")
    return path, text, len(data)
