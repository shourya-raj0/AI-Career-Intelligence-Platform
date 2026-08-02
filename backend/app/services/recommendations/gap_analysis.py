"""Skill gap analysis for career guidance.

Deterministically aggregates the skills required by the top-ranked matched jobs
that the developer does not yet have. Each gap skill is scored by importance
(weighted by job rank and requirement confidence), assigned a difficulty, and
linked to the job titles that demand it.
"""

from __future__ import annotations

from app.services.developer_profile.models import DeveloperProfile
from app.services.matching.models import MatchResult
from app.services.recommendations.models import GapSkill, SkillGap

_DIFFICULTY_MAP: dict[str, str] = {
    "git": "Easy",
    "github": "Easy",
    "sql": "Easy",
    "html": "Easy",
    "css": "Easy",
    "javascript": "Easy",
    "python": "Easy",
    "npm": "Easy",
    "pytest": "Easy",
    "jest": "Easy",
    "docker": "Medium",
    "react": "Medium",
    "typescript": "Medium",
    "fastapi": "Medium",
    "flask": "Medium",
    "django": "Medium",
    "node.js": "Medium",
    "express": "Medium",
    "graphql": "Medium",
    "rest api": "Medium",
    "microservices": "Medium",
    "postgresql": "Medium",
    "mysql": "Medium",
    "mongodb": "Medium",
    "redis": "Medium",
    "ci/cd": "Medium",
    "aws": "Hard",
    "azure": "Hard",
    "google cloud": "Hard",
    "kubernetes": "Hard",
    "terraform": "Hard",
    "machine learning": "Hard",
    "deep learning": "Hard",
    "pytorch": "Hard",
    "tensorflow": "Hard",
    "nlp": "Hard",
    "llm": "Hard",
    "langchain": "Hard",
    "langgraph": "Hard",
    "rag": "Hard",
    "mlops": "Hard",
    "system design": "Hard",
    "distributed systems": "Hard",
    "apache spark": "Hard",
    "apache kafka": "Hard",
    "elasticsearch": "Hard",
    "data pipelines": "Hard",
}


def _difficulty(name: str) -> str:
    return _DIFFICULTY_MAP.get(name.lower(), "Medium")


class SkillGapEngine:
    """Computes the skill gap between a profile and ranked jobs."""

    def __init__(self, top_jobs: int = 10) -> None:
        self._top_jobs = top_jobs

    def compute(
        self,
        profile: DeveloperProfile,
        ranked_jobs: list[MatchResult],
    ) -> SkillGap:
        """Return the aggregated missing skills for ``profile``."""
        developer_skills = profile.skill_names()
        aggregates: dict[str, dict[str, object]] = {}

        for rank, result in enumerate(ranked_jobs[: self._top_jobs]):
            rank_weight = 1.0 / (1.0 + rank)
            for skill in result.job.required_skills:
                key = skill.name.lower()
                if key in developer_skills:
                    continue
                aggregate = aggregates.setdefault(
                    key,
                    {"name": skill.name, "weight": 0.0, "count": 0, "jobs": set()},
                )
                aggregate["weight"] += rank_weight * skill.confidence
                aggregate["count"] += 1
                aggregate["jobs"].add(result.job.title)

        if not aggregates:
            return SkillGap(missing_skills=[], total_requirement_count=0)

        max_weight = max(float(aggregate["weight"]) for aggregate in aggregates.values())
        gaps = [
            GapSkill(
                name=str(aggregate["name"]),
                importance=round(100.0 * float(aggregate["weight"]) / max_weight, 1),
                difficulty=_difficulty(str(aggregate["name"])),
                priority=0,
                demand_count=int(aggregate["count"]),
                demanded_by=sorted(set(aggregate["jobs"])),
            )
            for aggregate in aggregates.values()
        ]
        gaps.sort(key=lambda gap: gap.importance, reverse=True)
        for index, gap in enumerate(gaps):
            gap.priority = index + 1

        return SkillGap(
            missing_skills=gaps,
            total_requirement_count=sum(
                int(aggregate["count"]) for aggregate in aggregates.values()
            ),
        )
