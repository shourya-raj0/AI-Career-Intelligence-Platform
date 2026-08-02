"""Career Guidance (Recommendation) services.

Exposes the :class:`CareerGuidanceEngine` entry point, the output models, and
the individual gap-analysis / roadmap / project-suggestion / retrieval
services. Every recommendation is grounded in retrieved learning resources.
"""

from app.services.recommendations.gap_analysis import SkillGapEngine
from app.services.recommendations.guidance import CareerGuidanceEngine
from app.services.recommendations.models import (
    CareerGuidance,
    ExplainabilityReport,
    GapSkill,
    LearningResource,
    LearningRoadmap,
    PortfolioProject,
    RetrievedResource,
    RoadmapStep,
    SkillGap,
)
from app.services.recommendations.project_suggestions import ProjectSuggestionEngine
from app.services.recommendations.retriever import ResourceRetriever
from app.services.recommendations.roadmap import RoadmapGenerator

__all__ = [
    "CareerGuidance",
    "CareerGuidanceEngine",
    "ExplainabilityReport",
    "GapSkill",
    "LearningResource",
    "LearningRoadmap",
    "PortfolioProject",
    "ProjectSuggestionEngine",
    "ResourceRetriever",
    "RetrievedResource",
    "RoadmapGenerator",
    "RoadmapStep",
    "SkillGap",
    "SkillGapEngine",
]
