"""Aggregate multiple profile adapters into a single CandidateContext.

`build_adapters` is the Factory that turns raw inputs into the set of active
adapters; `ProfileService` runs them concurrently (isolating failures) and
merges their signals into a deduplicated context.
"""
from __future__ import annotations

import asyncio

from app.domain.schemas import (
    CandidateContext,
    ProfileFragment,
    ProjectSignal,
)
from app.services.profile.base import ProfileAdapter
from app.services.profile.github import GitHubAdapter
from app.services.profile.linkedin import LinkedInAdapter
from app.services.profile.resume import ResumeAdapter


def build_adapters(
    *,
    github_url: str = "",
    linkedin_text: str = "",
    linkedin_pdf: bytes | None = None,
    resume_pdf: bytes | None = None,
    github_token: str = "",
) -> list[ProfileAdapter]:
    adapters: list[ProfileAdapter] = []
    if github_url.strip():
        adapters.append(GitHubAdapter(github_url, token=github_token))
    if linkedin_text.strip() or linkedin_pdf:
        adapters.append(LinkedInAdapter(text=linkedin_text, pdf_bytes=linkedin_pdf))
    if resume_pdf:
        adapters.append(ResumeAdapter(resume_pdf))
    return adapters


class ProfileService:
    def __init__(self, adapters: list[ProfileAdapter]) -> None:
        self._adapters = adapters

    async def build_context(self) -> CandidateContext:
        results = await asyncio.gather(
            *(a.fetch() for a in self._adapters), return_exceptions=True
        )
        fragments: list[ProfileFragment] = [
            r for r in results if isinstance(r, ProfileFragment)
        ]

        tech_stack: list[str] = []
        projects: list[ProjectSignal] = []
        highlights: list[str] = []
        available_sources: list[str] = []
        candidate_name: str | None = None

        for frag in fragments:
            available_sources.append(frag.source)
            highlights.append(frag.summary)

            for t in frag.signals.get("tech", []) or []:
                if t not in tech_stack:
                    tech_stack.append(t)
            for lang in frag.signals.get("languages", []) or []:
                if lang.lower() not in [t.lower() for t in tech_stack]:
                    tech_stack.append(lang)

            for proj in frag.signals.get("projects", []) or []:
                projects.append(ProjectSignal.model_validate(proj))
                for t in proj.get("tech", []) or []:
                    if t and t not in tech_stack:
                        tech_stack.append(t)

            if candidate_name is None:
                candidate_name = frag.signals.get("name")

        return CandidateContext(
            candidate_name=candidate_name,
            fragments=fragments,
            tech_stack=tech_stack,
            projects=projects,
            highlights=highlights,
            available_sources=available_sources,
        )
