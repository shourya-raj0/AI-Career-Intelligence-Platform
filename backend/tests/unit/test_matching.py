"""Unit tests for the JobRanker (Matching Engine) and its primitives."""

from __future__ import annotations

import pytest

from app.services.matching.ranking import JobRanker
from app.services.matching.similarity import cosine_similarity, similarity_to_many
from app.services.matching.skill_overlap import SkillOverlapEngine

from tests.conftest import make_job, make_profile


def test_cosine_similarity_identical_vectors():
    assert cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0]) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_is_zero():
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_similarity_empty_inputs_score_zero():
    assert cosine_similarity([], []) == 0.0
    assert cosine_similarity([1.0, 0.0], None or []) == 0.0


def test_cosine_similarity_shape_mismatch_is_zero():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0]) == 0.0


def test_similarity_to_many_vectorized():
    vec = [1.0, 0.0, 0.0]
    scores = similarity_to_many(vec, [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    assert scores[0] == pytest.approx(1.0)
    assert scores[1] == pytest.approx(0.0)


def test_skill_overlap_matched_and_missing():
    profile = make_profile(languages=["Python"])
    job = make_job("Backend Engineer", required=[("Python", 0.9), ("Docker", 0.7)])
    result = SkillOverlapEngine().compute(profile, job)
    assert "Python" in result.matched_skills
    assert "Docker" in result.missing_skills
    # confidence-weighted: 0.9 matched out of 1.6 total
    assert result.overlap_score == pytest.approx(0.9 / 1.6, abs=0.01)


def test_skill_overlap_no_requirements_scores_zero():
    profile = make_profile(languages=["Python"])
    job = make_job("Cleaner", required=[])
    result = SkillOverlapEngine().compute(profile, job)
    assert result.overlap_score == 0.0


def test_ranker_ranks_better_skills_first(embedder):
    profile = make_profile(languages=["Python"])
    # job_one overlaps the profile, job_two does not.
    job_one = make_job("Python Engineer", required=[("Python", 0.9)])
    job_two = make_job("Rust Engineer", required=[("Rust", 0.9)])
    ranked = JobRanker(embedder=embedder).rank(profile, [job_two, job_one])
    assert [r.job.title for r in ranked] == ["Python Engineer", "Rust Engineer"]
    assert ranked[0].match_score > ranked[1].match_score


def test_ranker_empty_jobs(embedder):
    profile = make_profile(languages=["Python"])
    assert JobRanker(embedder=embedder).rank(profile, []) == []


def test_ranker_output_is_deterministic(embedder):
    profile = make_profile(languages=["Python"])
    jobs = [make_job(f"Role {i}", required=[("Python", 0.8)]) for i in range(3)]
    a = JobRanker(embedder=embedder).rank(profile, jobs)
    b = JobRanker(embedder=embedder).rank(profile, jobs)
    assert [r.match_score for r in a] == [r.match_score for r in b]