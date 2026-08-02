"""Job ranking.

Combines semantic similarity, skill overlap, and the developer profile's
repository-quality score into one deterministic 0-100 match score, then ranks
jobs in descending order. This engine never generates explanations and never
calls an LLM.
"""

from __future__ import annotations

from app.services.developer_profile.models import DeveloperProfile
from app.services.jobs.models import Job
from app.services.matching.embedding import DeveloperEmbedder
from app.services.matching.models import MatchBreakdown, MatchResult
from app.services.matching.similarity import cosine_similarity
from app.services.matching.skill_overlap import SkillOverlapEngine

_WEIGHT_SEMANTIC = 0.40
_WEIGHT_OVERLAP = 0.40
_WEIGHT_QUALITY = 0.20

_HIGH_THRESHOLD = 70.0
_MEDIUM_THRESHOLD = 45.0


class JobRanker:
    """Ranks jobs against a developer profile."""

    def __init__(
        self,
        embedder: DeveloperEmbedder | None = None,
        skill_overlap_engine: SkillOverlapEngine | None = None,
    ) -> None:
        self._embedder = embedder or DeveloperEmbedder()
        self._overlap = skill_overlap_engine or SkillOverlapEngine()

    def rank(self, profile: DeveloperProfile, jobs: list[Job]) -> list[MatchResult]:
        """Return ``jobs`` ranked by match score for ``profile``."""
        if not jobs:
            return []
        profile_vector = self._embedder.embed_profile(profile)
        profile_quality = profile.quality_score / 100.0

        results = [
            self._match_one(profile, job, profile_vector, profile_quality)
            for job in jobs
        ]
        return sorted(results, key=lambda result: result.match_score, reverse=True)

    def _match_one(
        self,
        profile: DeveloperProfile,
        job: Job,
        profile_vector: list[float],
        profile_quality: float,
    ) -> MatchResult:
        semantic = cosine_similarity(profile_vector, job.embedding)
        overlap = self._overlap.compute(profile, job)

        match_score = round(
            100.0
            * (
                _WEIGHT_SEMANTIC * semantic
                + _WEIGHT_OVERLAP * overlap.overlap_score
                + _WEIGHT_QUALITY * profile_quality
            ),
            1,
        )
        confidence = (
            "High" if match_score >= _HIGH_THRESHOLD
            else "Medium" if match_score >= _MEDIUM_THRESHOLD
            else "Low"
        )

        return MatchResult(
            job=job,
            match_score=match_score,
            confidence=confidence,
            matched_skills=overlap.matched_skills,
            missing_skills=overlap.missing_skills,
            breakdown=MatchBreakdown(
                semantic_similarity=round(semantic, 4),
                skill_overlap=overlap.overlap_score,
                quality_score=profile.quality_score,
                weight_semantic=_WEIGHT_SEMANTIC,
                weight_overlap=_WEIGHT_OVERLAP,
                weight_quality=_WEIGHT_QUALITY,
            ),
        )
