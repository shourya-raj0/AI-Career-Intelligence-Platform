"""Unit tests for the ResourceRetriever (grounded retrieval)."""

from __future__ import annotations

from app.services.recommendations.retriever import ResourceRetriever

from tests.conftest import FakeEmbedder


class RecordingEmbedder(FakeEmbedder):
    """Fake embedder that counts how many times it is asked to embed."""

    def __init__(self) -> None:
        super().__init__()
        self.documents_computed = 0

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.documents_computed += 1
        return super().embed_documents(texts)


def test_retrieve_returns_top_k(embedder):
    retriever = ResourceRetriever(embedder=embedder)
    results = retriever.retrieve("fastapi", top_k=3)
    assert 0 < len(results) <= 3
    for resource in results:
        assert resource.score >= 0.0


def test_empty_query_returns_empty(embedder):
    assert ResourceRetriever(embedder=embedder).retrieve("   ", top_k=3) == []


def test_corpus_embeddings_are_cached():
    retriever = ResourceRetriever(embedder=FakeEmbedder())
    retriever.retrieve("docker")
    cached = retriever._corpus_embeddings
    assert cached is not None
    retriever.retrieve("aws")
    # The corpus vectors object is reused, not recomputed per query.
    assert retriever._corpus_embeddings is cached


def test_skill_hit_ranks_high(embedder):
    retriever = ResourceRetriever(embedder=embedder)
    docker = retriever.retrieve("docker", top_k=1)
    assert docker
    assert "docker" in docker[0].title.lower() or "container" in docker[0].title.lower()


def test_retrieve_is_deterministic(embedder):
    r1 = [r.score for r in ResourceRetriever(embedder=embedder).retrieve("python", top_k=3)]
    r2 = [r.score for r in ResourceRetriever(embedder=embedder).retrieve("python", top_k=3)]
    assert r1 == r2