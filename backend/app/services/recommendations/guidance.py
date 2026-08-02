"""Career Guidance orchestration.

Ties skill-gap analysis, grounded roadmap generation, and portfolio project
suggestions into one :class:`CareerGuidance` report with an explainability
summary. Pure business logic; no LLM.
"""

from __future__ import annotations

from app.services.developer_profile.models import DeveloperProfile
from app.services.matching.models import MatchResult
from app.services.recommendations.gap_analysis import SkillGapEngine
from app.services.recommendations.models import CareerGuidance, ExplainabilityReport
from app.services.recommendations.project_suggestions import ProjectSuggestionEngine
from app.services.recommendations.retriever import ResourceRetriever
from app.services.recommendations.roadmap import RoadmapGenerator

_TOP_GAPS_IN_SUMMARY = 5


class CareerGuidanceEngine:
    """Generates the full career guidance report for a developer."""

    def __init__(
        self,
        gap_engine: SkillGapEngine | None = None,
        retriever: ResourceRetriever | None = None,
        roadmap_generator: RoadmapGenerator | None = None,
        project_engine: ProjectSuggestionEngine | None = None,
    ) -> None:
        self._gap_engine = gap_engine or SkillGapEngine()
        self._retriever = retriever or ResourceRetriever()
        self._roadmap = roadmap_generator or RoadmapGenerator(self._retriever)
        self._projects = project_engine or ProjectSuggestionEngine(self._retriever)

    def generate(
        self,
        profile: DeveloperProfile,
        ranked_jobs: list[MatchResult],
    ) -> CareerGuidance:
        """Generate the career guidance report for ``profile``."""
        skill_gap = self._gap_engine.compute(profile, ranked_jobs)
        roadmap = self._roadmap.generate(skill_gap)
        projects = self._projects.suggest(skill_gap)
        resources = _all_grounded_resources(roadmap, projects)
        top_gaps = [gap.name for gap in skill_gap.missing_skills[:_TOP_GAPS_IN_SUMMARY]]
        summary = _build_summary(skill_gap, top_gaps, len(resources))

        return CareerGuidance(
            github_username=profile.github_username,
            skill_gap=skill_gap,
            roadmap=roadmap,
            portfolio_projects=projects,
            explainability=ExplainabilityReport(
                summary=summary,
                top_gap_skills=top_gaps,
                grounded_resources=resources,
            ),
        )


def _all_grounded_resources(roadmap, projects) -> list:
    seen: set[str] = set()
    resources = []
    for step in roadmap.steps:
        for resource in step.resources:
            if resource.id in seen:
                continue
            seen.add(resource.id)
            resources.append(resource)
    for project in projects:
        for resource in project.resources:
            if resource.id in seen:
                continue
            seen.add(resource.id)
            resources.append(resource)
    return resources


def _build_summary(skill_gap, top_gaps: list[str], resource_count: int) -> str:
    count = len(skill_gap.missing_skills)
    if count == 0:
        return (
            "No skill gaps were found: your profile already covers the requirements "
            "of your top matched jobs. Focus on applying and strengthening the skills you have."
        )
    focus = ", ".join(top_gaps) if top_gaps else "none identified"
    return (
        f"{count} skill gaps were identified across your top matched jobs. "
        f"Highest priority: {focus}. Every roadmap step and project suggestion is "
        f"grounded in {resource_count} retrieved learning resources."
    )
