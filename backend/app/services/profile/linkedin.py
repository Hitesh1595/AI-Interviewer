"""LinkedIn adapter: best-effort parse of pasted text or a LinkedIn PDF export.

We never scrape linkedin.com (ToS + fragile). The recruiter/candidate pastes the
About/Experience text or uploads LinkedIn's own "Save to PDF" export.
"""
from __future__ import annotations

from app.domain.schemas import ProfileFragment
from app.services.profile.base import ProfileAdapter, extract_tech
from app.services.profile.resume import extract_pdf_text

MAX_EXCERPT = 5000


class LinkedInAdapter(ProfileAdapter):
    source = "linkedin"

    def __init__(self, text: str = "", pdf_bytes: bytes | None = None) -> None:
        self._text = text or ""
        self._pdf_bytes = pdf_bytes

    async def fetch(self) -> ProfileFragment | None:
        text = self._text.strip()
        if not text and self._pdf_bytes:
            try:
                text = extract_pdf_text(self._pdf_bytes)
            except Exception:
                text = ""
        if not text:
            return None

        tech = extract_tech(text)
        # Heuristic headline = first non-empty line.
        headline = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
        excerpt = text[:MAX_EXCERPT]
        summary = (
            f"LinkedIn profile provided. Headline: {headline[:140] or 'n/a'}. "
            f"Detected technologies: {', '.join(tech) or 'none detected'}."
        )
        return ProfileFragment(
            source=self.source,
            summary=summary,
            signals={"headline": headline, "tech": tech},
            raw_excerpt=excerpt,
        )
