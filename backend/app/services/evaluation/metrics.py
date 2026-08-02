"""Evaluation metrics.

Pure functions (no I/O, no service dependencies) so they can be unit-tested in
isolation. ``ranked`` is a list of job ids in system order (best first);
``relevant`` is the set of job ids a human judged relevant. Human agreement is
measured two ways: the binary agreement of system relevance decisions against
human labels (Cohen's kappa + agreement rate) and, when human ranks exist, the
rank correlation between system and human orderings (Kendall tau).
"""

from __future__ import annotations

import math

_PRECISION_KS = (1, 3, 5)


def precision_at_k(ranked: list[str], relevant: set[str], k: int) -> float | None:
    """Proportion of relevant jobs among the top ``k`` of ``ranked``."""
    if k > len(ranked):
        return None
    top = ranked[:k]
    return sum(1 for job_id in top if job_id in relevant) / k


def precision_at_all_ks(
    ranked: list[str], relevant: set[str]
) -> dict[str, float | None]:
    """Precision@K for the standard K values."""
    return {f"precision_at_{k}": precision_at_k(ranked, relevant, k) for k in _PRECISION_KS}


def recall_at_k(ranked: list[str], relevant: set[str], k: int) -> float | None:
    """Fraction of all relevant jobs found in the top ``k`` of ``ranked``."""
    if not relevant or k > len(ranked):
        return None
    top = ranked[:k]
    return sum(1 for job_id in top if job_id in relevant) / len(relevant)


def average_precision(ranked: list[str], relevant: set[str], k: int = 10) -> float:
    """Average precision up to rank ``k`` (AP@k)."""
    hits = 0
    sum_precision = 0.0
    for position, job_id in enumerate(ranked[:k], start=1):
        if job_id in relevant:
            hits += 1
            sum_precision += hits / position
    return sum_precision / len(relevant) if relevant else 0.0


def reciprocal_rank(ranked: list[str], relevant: set[str]) -> float:
    """Inverse of the first rank at which a relevant job appears."""
    for position, job_id in enumerate(ranked, start=1):
        if job_id in relevant:
            return 1.0 / position
    return 0.0


def binarize(scores: list[float], threshold: float) -> list[int]:
    """Convert continuous match scores into 1/0 relevance decisions."""
    return [1 if score >= threshold else 0 for score in scores]


def agreement_rate(binary_a: list[int], binary_b: list[int]) -> float:
    """Proportion of positions where two binary labelings agree."""
    if not binary_a or len(binary_a) != len(binary_b):
        return 0.0
    return sum(1 for a, b in zip(binary_a, binary_b) if a == b) / len(binary_a)


def cohens_kappa(binary_a: list[int], binary_b: list[int]) -> float | None:
    """Cohen's kappa for two binary labelings, corrected for chance."""
    if not binary_a or len(binary_a) != len(binary_b):
        return None
    n = len(binary_a)
    if n == 0:
        return None
    observed = agreement_rate(binary_a, binary_b)
    p_pos_a = sum(binary_a) / n
    p_pos_b = sum(binary_b) / n
    chance = p_pos_a * p_pos_b + (1 - p_pos_a) * (1 - p_pos_b)
    if chance >= 1.0:
        return 1.0 if observed == 1.0 else 0.0
    return (observed - chance) / (1 - chance)


def kendall_tau(rank_a: list[float], rank_b: list[float]) -> float | None:
    """Kendall tau rank correlation between two orderings (lower rank = better).

    Positions where either rank is missing are ignored, mirroring how the
    system only ranks the jobs it matched.
    """
    pairs = [(a, b) for a, b in zip(rank_a, rank_b) if a is not None and b is not None]
    n = len(pairs)
    if n < 2:
        return None
    concordant = 0
    discordant = 0
    for i in range(n):
        for j in range(i + 1, n):
            a_i, b_i = pairs[i]
            a_j, b_j = pairs[j]
            a_order = -1 if a_i < a_j else 1 if a_i > a_j else 0
            b_order = -1 if b_i < b_j else 1 if b_i > b_j else 0
            if a_order == 0 or b_order == 0:
                continue
            if a_order == b_order:
                concordant += 1
            else:
                discordant += 1
    total = concordant + discordant
    if total == 0:
        return 0.0
    return (concordant - discordant) / total


def percentile(values: list[float], p: float) -> float:
    """Nearest-rank ``p``-th percentile of ``values``."""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    rank = max(1, math.ceil(len(sorted_values) * p / 100.0))
    return sorted_values[min(rank, len(sorted_values)) - 1]
