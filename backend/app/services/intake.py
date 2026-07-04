"""Shared candidate-intake helpers used by both the direct-session and
invite-based flows: PDF validation and profile-context aggregation."""
from __future__ import annotations

from fastapi import HTTPException, UploadFile

from app.config import get_settings
from app.domain.schemas import CandidateContext
from app.services.profile.aggregator import ProfileService, build_adapters

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


async def read_pdf(upload: UploadFile | None) -> bytes | None:
    if upload is None:
        return None
    if upload.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(400, f"{upload.filename}: only PDF uploads are allowed")
    data = await upload.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(400, f"{upload.filename}: file exceeds 5 MB limit")
    return data or None


async def build_candidate_context(
    *,
    github_url: str = "",
    linkedin_text: str = "",
    linkedin_pdf: bytes | None = None,
    resume_pdf: bytes | None = None,
) -> CandidateContext:
    adapters = build_adapters(
        github_url=github_url,
        linkedin_text=linkedin_text,
        linkedin_pdf=linkedin_pdf,
        resume_pdf=resume_pdf,
        github_token=get_settings().github_token,
    )
    if not adapters:
        raise HTTPException(
            400,
            "Provide at least one profile source: a GitHub URL, LinkedIn text/PDF, "
            "or a resume PDF.",
        )
    return await ProfileService(adapters).build_context()
