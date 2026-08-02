"""Grounded learning roadmap generation.

Groups the top missing skills into weekly steps, each backed by retrieved
learning resources and the job titles driving the recommendation.
"""

from __future__ import annotations

from app.services.recommendations.models import LearningRoadmap, RoadmapStep
from app.services.recommendations.retriever import ResourceRetriever

_SKILLS_PER_WEEK = 2
_RESOURCES_PER_SKILL = 2
_MAX_ROADMAP_SKILLS = 6
_MAX_DRIVEN_BY = 3


class RoadmapGenerator:
    """Builds a week-by-week roadmap from a :class:`SkillGap`."""

    def __init__(self, retriever: ResourceRetriever | None = None) -> None:
        self._retriever = retriever or ResourceRetriever()

    def generate(self, skill_gap) -> LearningRoadmap:
        """Generate a grounded roadmap for the top gap skills."""
        skills = [gap for gap in skill_gap.missing_skills[: _MAX_ROADMAP_SKILLS]]
        if not skills:
            return LearningRoadmap(total_weeks=0, steps=[])

        steps: list[RoadmapStep] = []
        for index in range(0, len(skills), _SKILLS_PER_WEEK):
            chunk = skills[index : index + _SKILLS_PER_WEEK]
            week = index // _SKILLS_PER_WEEK + 1
            names = [gap.name for gap in chunk]

            resources = []
            for gap in chunk:
                resources.extend(
                    self._retriever.retrieve(gap.name, top_k=_RESOURCES_PER_SKILL)
                )
            resources = _dedupe_resources(resources)

            driven_by = _dedupe_strings(
                title
                for gap in chunk
                for title in gap.demanded_by
            )[:_MAX_DRIVEN_BY]

            goal = f"Master {', '.join(names)} with hands-on practice and build a small project that applies it."
            steps.append(
                RoadmapStep(
                    week=week,
                    title=f"Week {week}: {', '.join(names)}",
                    goal=goal,
                    skills=names,
                    resources=resources,
                    driven_by=driven_by,
                )
            )
        return LearningRoadmap(total_weeks=len(steps), steps=steps)


def _dedupe_resources(resources: list) -> list:
    seen: set[str] = set()
    result = []
    for resource in resources:
        if resource.id in seen:
            continue
        seen.add(resource.id)
        result.append(resource)
    return result


def _dedupe_strings(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
