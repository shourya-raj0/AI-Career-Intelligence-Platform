"""Skill overlap between a developer profile and a job.

Deterministically compares the skills a job requires against the skills present
in a developer profile. The overlap score is confidence-weighted over the
job's required skills, so meeting a high-confidence requirement contributes
more than meeting a minor one.
"""

from __future__ import annotations

from app.services.developer_profile.models import DeveloperProfile
from app.services.jobs.models import Job
from app.services.matching.models import SkillOverlapResult


class SkillOverlapEngine:
    """Computes which required job skills a developer already has."""

    def compute(self, profile: DeveloperProfile, job: Job) -> SkillOverlapResult:
        """Compare ``job`` requirements against ``profile`` skills."""
        developer_skills = profile.skill_names()
        matched: list[str] = []
        missing: list[str] = []
        matched_weight = 0.0
        total_weight = 0.0

        for skill in job.required_skills:
            total_weight += skill.confidence
            if skill.name.lower() in developer_skills:
                matched.append(skill.name)
                matched_weight += skill.confidence
            else:
                missing.append(skill.name)

        overlap = matched_weight / total_weight if total_weight > 0.0 else 0.0
        return SkillOverlapResult(
            overlap_score=round(overlap, 4),
            matched_skills=matched,
            missing_skills=missing,
        )
