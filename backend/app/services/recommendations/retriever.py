"""Retrieval of learning resources to ground recommendations.

Scores every corpus resource against a query using a mix of exact skill-key
match, keyword overlap, and embedding similarity (the same sentence-transformer
model used for jobs and profiles). Retrieval is deterministic; resource
embeddings are computed once and cached in memory.
"""

from __future__ import annotations

import re

from app.services.jobs.embedding import JobEmbedder
from app.services.matching.similarity import cosine_similarity
from app.services.recommendations.corpus import get_corpus
from app.services.recommendations.models import LearningResource, RetrievedResource

_TOKEN_RE = re.compile(r"[a-z0-9+#.-]+")

_WEIGHT_SKILL_HIT = 0.5
_WEIGHT_KEYWORD = 0.2
_WEIGHT_EMBEDDING = 0.3


class ResourceRetriever:
    """Retrieves top learning resources for a skill query."""

    def __init__(self, embedder: JobEmbedder | None = None) -> None:
        self._embedder = embedder or JobEmbedder()
        self._corpus = get_corpus()
        self._corpus_embeddings: list[list[float]] | None = None

    def retrieve(self, query: str, top_k: int = 3) -> list[RetrievedResource]:
        """Return the top ``top_k`` resources for ``query``."""
        if not query.strip():
            return []
        query_vector = self._embedder.embed_documents([query])[0]
        corpus_vectors = self._embed_embeddings()

        scored: list[tuple[float, LearningResource]] = []
        for resource, resource_vector in zip(self._corpus, corpus_vectors):
            score = self._score(query, query_vector, resource, resource_vector)
            scored.append((score, resource))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            self._to_retrieved(resource, round(score, 4))
            for score, resource in scored[:top_k]
        ]

    def _score(
        self,
        query: str,
        query_vector: list[float],
        resource: LearningResource,
        resource_vector: list[float],
    ) -> float:
        lowered = query.lower().strip()
        skill_hit = any(
            lowered == skill or lowered in skill or skill in lowered
            for skill in resource.skills
        )
        keyword = self._keyword_overlap(lowered, resource)
        embedding = cosine_similarity(query_vector, resource_vector)
        return (
            _WEIGHT_SKILL_HIT * float(skill_hit)
            + _WEIGHT_KEYWORD * keyword
            + _WEIGHT_EMBEDDING * embedding
        )

    @staticmethod
    def _keyword_overlap(query: str, resource: LearningResource) -> float:
        tokens = set(_TOKEN_RE.findall(query))
        if not tokens:
            return 0.0
        haystack = f"{resource.title} {resource.description} {' '.join(resource.skills)}".lower()
        hits = sum(1 for token in tokens if token in haystack)
        return hits / len(tokens)

    def _embed_embeddings(self) -> list[list[float]]:
        if self._corpus_embeddings is None:
            texts = [
                f"{resource.title}. {resource.description} {' '.join(resource.skills)}"
                for resource in self._corpus
            ]
            self._corpus_embeddings = self._embedder.embed_documents(texts)
        return self._corpus_embeddings

    @staticmethod
    def _to_retrieved(resource: LearningResource, score: float) -> RetrievedResource:
        return RetrievedResource(
            id=resource.id,
            title=resource.title,
            url=resource.url,
            source=resource.source,
            resource_type=resource.resource_type,
            description=resource.description,
            difficulty=resource.difficulty,
            score=score,
        )
