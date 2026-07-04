"""Adapter pattern: each profile source normalizes into a ProfileFragment."""
from __future__ import annotations

import re
from abc import ABC, abstractmethod

from app.domain.schemas import ProfileFragment

# Keyword dictionary used to extract a tech stack from free-form text
# (resume / LinkedIn / repo topics). Lowercased matching on word boundaries.
TECH_KEYWORDS = [
    "python", "javascript", "typescript", "java", "kotlin", "swift", "go",
    "golang", "rust", "c++", "c#", ".net", "php", "ruby", "scala", "r",
    "react", "next.js", "nextjs", "vue", "angular", "svelte", "node.js", "nodejs",
    "express", "fastapi", "flask", "django", "spring", "spring boot", "rails",
    "laravel", "graphql", "rest", "grpc",
    "postgresql", "postgres", "mysql", "sqlite", "mongodb", "redis", "elasticsearch",
    "cassandra", "dynamodb", "kafka", "rabbitmq",
    "docker", "kubernetes", "terraform", "ansible", "aws", "gcp", "azure",
    "jenkins", "github actions", "ci/cd",
    "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy", "spark", "hadoop",
    "llm", "langchain", "openai", "gemini", "huggingface",
    "html", "css", "tailwind", "sass", "webpack", "vite",
    "linux", "git", "microservices", "system design",
]


def extract_tech(text: str) -> list[str]:
    """Return the distinct known technologies mentioned in `text`."""
    if not text:
        return []
    low = text.lower()
    found: list[str] = []
    for kw in TECH_KEYWORDS:
        pattern = r"(?<![a-z0-9])" + re.escape(kw) + r"(?![a-z0-9])"
        if re.search(pattern, low) and kw not in found:
            found.append(kw)
    return found


class ProfileAdapter(ABC):
    source: str

    @abstractmethod
    async def fetch(self) -> ProfileFragment | None:
        """Return a fragment, or None if this source yields nothing usable."""
        raise NotImplementedError
