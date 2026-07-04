"""GitHub adapter: pulls public profile + repos via the free GitHub REST API."""
from __future__ import annotations

import re

import httpx

from app.domain.schemas import ProfileFragment, ProjectSignal
from app.services.profile.base import ProfileAdapter

_GITHUB_API = "https://api.github.com"


def parse_username(github_url: str) -> str | None:
    url = github_url.strip()
    if not url:
        return None
    if "github.com" in url:
        m = re.search(r"github\.com/([^/?#]+)", url)
        if m:
            return m.group(1)
        return None
    # Allow passing a bare username.
    return url.split("/")[0] or None


class GitHubAdapter(ProfileAdapter):
    source = "github"

    def __init__(self, github_url: str, token: str = "") -> None:
        self._username = parse_username(github_url)
        self._token = token

    def _headers(self) -> dict:
        headers = {"Accept": "application/vnd.github+json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def fetch(self) -> ProfileFragment | None:
        if not self._username:
            return None
        async with httpx.AsyncClient(timeout=15.0, headers=self._headers()) as client:
            user_resp = await client.get(f"{_GITHUB_API}/users/{self._username}")
            if user_resp.status_code != 200:
                return None
            user = user_resp.json()
            repos_resp = await client.get(
                f"{_GITHUB_API}/users/{self._username}/repos",
                params={"sort": "pushed", "per_page": 30, "type": "owner"},
            )
            repos = repos_resp.json() if repos_resp.status_code == 200 else []

        if not isinstance(repos, list):
            repos = []

        # Rank by stars then recency; keep non-fork repos first.
        own = [r for r in repos if not r.get("fork")]
        own.sort(key=lambda r: r.get("stargazers_count", 0), reverse=True)
        top = own[:6]

        projects: list[ProjectSignal] = []
        languages: dict[str, int] = {}
        for r in top:
            lang = r.get("language")
            topics = r.get("topics") or []
            tech = [t for t in ([lang] + topics) if t]
            projects.append(
                ProjectSignal(
                    name=r.get("name", ""),
                    description=(r.get("description") or "").strip(),
                    tech=tech,
                    url=r.get("html_url", ""),
                    source="github",
                )
            )
        for r in own:
            lang = r.get("language")
            if lang:
                languages[lang] = languages.get(lang, 0) + 1

        top_langs = sorted(languages, key=languages.get, reverse=True)[:8]
        summary = (
            f"GitHub user @{self._username} ({user.get('name') or 'no name'}): "
            f"{user.get('public_repos', 0)} public repos, "
            f"{user.get('followers', 0)} followers. "
            f"Bio: {user.get('bio') or 'n/a'}. "
            f"Primary languages: {', '.join(top_langs) or 'unknown'}."
        )
        return ProfileFragment(
            source=self.source,
            summary=summary,
            signals={
                "username": self._username,
                "name": user.get("name"),
                "languages": top_langs,
                "projects": [p.model_dump() for p in projects],
            },
            raw_excerpt=summary,
        )
