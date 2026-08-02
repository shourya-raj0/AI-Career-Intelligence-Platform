"""Matching Engine services.

Exposes the :class:`JobRanker` entry point, the result models, and the
individual embedding/similarity/skill-overlap primitives.
"""

from app.services.matching.embedding import DeveloperEmbedder, profile_to_text
from app.services.matching.models import MatchBreakdown, MatchResult, SkillOverlapResult
from app.services.matching.ranking import JobRanker
from app.services.matching.similarity import cosine_similarity, similarity_to_many
from app.services.matching.skill_overlap import SkillOverlapEngine

__all__ = [
    "DeveloperEmbedder",
    "JobRanker",
    "MatchBreakdown",
    "MatchResult",
    "SkillOverlapEngine",
    "SkillOverlapResult",
    "cosine_similarity",
    "profile_to_text",
    "similarity_to_many",
]
