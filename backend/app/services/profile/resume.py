"""Resume adapter: extracts text + tech signals from an uploaded PDF."""
from __future__ import annotations

import io

from pypdf import PdfReader

from app.domain.schemas import ProfileFragment
from app.services.profile.base import ProfileAdapter, extract_tech

MAX_EXCERPT = 6000


def extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(parts).strip()


class ResumeAdapter(ProfileAdapter):
    source = "resume"

    def __init__(self, pdf_bytes: bytes) -> None:
        self._pdf_bytes = pdf_bytes

    async def fetch(self) -> ProfileFragment | None:
        if not self._pdf_bytes:
            return None
        try:
            text = extract_pdf_text(self._pdf_bytes)
        except Exception:
            return None
        if not text:
            return None

        tech = extract_tech(text)
        excerpt = text[:MAX_EXCERPT]
        summary = (
            f"Resume parsed ({len(text)} chars). "
            f"Detected technologies: {', '.join(tech) or 'none detected'}."
        )
        return ProfileFragment(
            source=self.source,
            summary=summary,
            signals={"tech": tech},
            raw_excerpt=excerpt,
        )
