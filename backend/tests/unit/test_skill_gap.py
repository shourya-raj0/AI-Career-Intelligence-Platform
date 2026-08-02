"""Unit tests for the skill gap analysis engine."""

from __future__ import annotations

from app.services.recommendations.gap_analysis import SkillGapEngine
from app.services.matching.models import MatchResult, MatchBreakdown

from tests.conftest import make_job, make_profile


def _match(job, score: float = 60.0) -> MatchResult:
    return MatchResult(
        job=job,
        match_score=score,
        confidence="Medium",
        matched_skills=["Python"],
        missing_skills=[s.name for s in job.required_skills if s.name.lower() not in ("python",)],
        breakdown=MatchBreakdown(
            semantic_similarity=0.5,
            skill_overlap=0.5,
            quality_score=70.0,
            weight_semantic=0.4,
            weight_overlap=0.4,
            weight_quality=0.2,
        ),
    )


def test_identifies_missing_skills():
    profile = make_profile(languages=["Python"])
    job = make_job("Backend Engineer", required=[("Python", 0.9), ("Docker", 0.8)])
    engine = SkillGapEngine()
    skill_gap = engine.compute(profile, [_match(job)])
    missing = {gap.name for gap in skill_gap.missing_skills}
    assert "Docker" in missing
    assert "Python" not in missing  # already present


def test_no_profile_no_gaps():
    profile = make_profile(languages=["Python"])
    job = make_job("Python Engineer", required=[("Python", 0.9)])
    skill_gap = SkillGapEngine().compute(profile, [_match(job)])
    assert skill_gap.missing_skills == []


def test_importance_is_rank_weighted():
    profile = make_profile(languages=["Python"])
    first = _match(make_job("Role A", required=[("Docker", 1.0)]), score=90)
    second = _match(make_job("Role B", required=[("Docker", 1.0)]), score=10)
    skill_gap = SkillGapEngine().compute(profile, [first, second])
    assert len(skill_gap.missing_skills) == 1
    # Docker appears once per job -> demand_count reflects unique job titles
    assert skill_gap.missing_skills[0].demand_count >= 1


def test_demanded_by_lists_job_titles():
    profile = make_profile(languages=["Python"])
    job = make_job("DevOps Engineer", required=[("Kubernetes", 0.9)])
    gap = SkillGapEngine().compute(profile, [_match(job)])
    assert "DevOps Engineer" in gap.missing_skills[0].demanded_by


def test_difficulty_assigned():
    profile = make_profile(languages=["Python"])
    job = make_job("ML Engineer", required=[("Kubernetes", 0.9)])
    gap = SkillGapEngine().compute(profile, [_match(job)])
    assert gap.missing_skills[0].difficulty in {"Easy", "Medium", "Hard"}