"""Career Guidance output models.

A :class:`CareerGuidance` report contains the skill gap, a grounded learning
roadmap, portfolio project suggestions, and an explainability summary. Every
roadmap step and project carries retrieved learning resources so each
recommendation is grounded, and gap skills cite the jobs that demand them.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LearningResource(BaseModel):
    """A single entry in the learning-resource corpus."""

    id: str
    title: str
    url: str
    source: str
    resource_type: str
    description: str
    skills: list[str] = Field(default_factory=list)
    difficulty: str = "Medium"


class RetrievedResource(BaseModel):
    """A corpus resource retrieved as grounding for a recommendation."""

    id: str
    title: str
    url: str
    source: str
    resource_type: str
    description: str
    difficulty: str
    score: float


class GapSkill(BaseModel):
    """A missing skill and its priority for the developer."""

    name: str
    importance: float
    difficulty: str
    priority: int
    demand_count: int
    demanded_by: list[str] = Field(default_factory=list)


class SkillGap(BaseModel):
    """The set of skills missing from the developer profile."""

    missing_skills: list[GapSkill] = Field(default_factory=list)
    total_requirement_count: int = 0


class RoadmapStep(BaseModel):
    """One week of the grounded learning roadmap."""

    week: int
    title: str
    goal: str
    skills: list[str] = Field(default_factory=list)
    resources: list[RetrievedResource] = Field(default_factory=list)
    driven_by: list[str] = Field(default_factory=list)


class LearningRoadmap(BaseModel):
    """A week-by-week plan to close the identified skill gaps."""

    total_weeks: int
    steps: list[RoadmapStep] = Field(default_factory=list)


class PortfolioProject(BaseModel):
    """A project idea that closes one or more skill gaps."""

    title: str
    summary: str
    skills: list[str] = Field(default_factory=list)
    difficulty: str
    estimated_weeks: int
    resources: list[RetrievedResource] = Field(default_factory=list)
    rationale: str


class ExplainabilityReport(BaseModel):
    """Plain-language summary tying recommendations to evidence."""

    summary: str
    top_gap_skills: list[str] = Field(default_factory=list)
    grounded_resources: list[RetrievedResource] = Field(default_factory=list)


class CareerGuidance(BaseModel):
    """The full career guidance output for a developer profile."""

    github_username: str
    skill_gap: SkillGap = Field(default_factory=SkillGap)
    roadmap: LearningRoadmap = Field(default_factory=lambda: LearningRoadmap(total_weeks=0))
    portfolio_projects: list[PortfolioProject] = Field(default_factory=list)
    explainability: ExplainabilityReport = Field(default_factory=ExplainabilityReport)
