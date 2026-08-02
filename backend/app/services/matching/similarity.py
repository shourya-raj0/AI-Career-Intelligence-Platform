"""Cosine similarity primitives for matching.

Pure numerical helpers. Vectors are compared as-is; empty or shape-mismatched
inputs score 0.0 rather than raising, so one malformed job never fails ranking.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np


def cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    """Return the cosine similarity between two vectors in ``[0.0, 1.0]``."""
    if not vec_a or not vec_b:
        return 0.0
    a = np.asarray(vec_a, dtype=np.float32)
    b = np.asarray(vec_b, dtype=np.float32)
    if a.shape != b.shape:
        return 0.0
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denominator == 0.0:
        return 0.0
    return float(np.dot(a, b) / denominator)


def similarity_to_many(vec: Sequence[float], vectors: Sequence[Sequence[float]]) -> list[float]:
    """Return cosine similarity of ``vec`` against every vector in ``vectors``."""
    if not vec or not vectors:
        return [0.0] * len(vectors)
    target = np.asarray(vec, dtype=np.float32)
    matrix = np.asarray(vectors, dtype=np.float32)
    if matrix.ndim != 2 or matrix.shape[1] != target.shape[0]:
        return [0.0] * len(vectors)
    norms = np.linalg.norm(matrix, axis=1)
    denominator = np.linalg.norm(target) * norms
    if np.any(denominator == 0.0):
        return [0.0] * len(vectors)
    similarities = (matrix @ target) / denominator
    return similarities.tolist()
