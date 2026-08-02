"""Integration tests for the FastAPI HTTP layer.

These exercise the routers, dependency injection, and exception handlers with a
stubbed application service so no real network or model is touched. They assert
the API correctly delegates to the facade (contract + DI) rather than
reproducing business logic, which the unit tests cover.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_career_intelligence_service
from app.main import create_app
from app.services.career_intelligence import AnalysisResponse

from tests.conftest import make_github_report


class _FakeCareerService:
    """Thin stand-in exposing the facade's method signature."""

    def __init__(self) -> None:
        self.calls: dict[str, int] = {
            "analyze": 0,
            "run_pipeline": 0,
            "search_jobs": 0,
            "recommendations": 0,
            "close": 0,
        }

    def analyze_github_username(self, username: str):
        self.calls["analyze"] += 1
        return make_github_report(username)

    def run_analysis(self, github_username: str, job_preferences=None) -> AnalysisResponse:
        self.calls["run_pipeline"] += 1
        return AnalysisResponse(github_username=github_username, errors=[])

    def search_jobs(self, query):
        self.calls["search_jobs"] += 1
        return []

    def generate_recommendations(
        self, github_username, job_preferences, keywords, location, count
    ):
        self.calls["recommendations"] += 1
        raise NotImplementedError

    def close(self) -> None:
        self.calls["close"] += 1


@pytest.fixture
def client_default_delegate():
    """A TestClient with the service dependency replaced by a fake."""
    service = _FakeCareerService()
    app = create_app()
    app.dependency_overrides[get_career_intelligence_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client, service
    app.dependency_overrides.clear()


def test_health_returns_ok(client_default_delegate):
    client, _ = client_default_delegate
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert "version" in body
    assert "database" in body


def test_analysis_endpoint_delegates_to_facade(client_default_delegate):
    client, service = client_default_delegate
    response = client.post("/api/v1/analysis", json={"github_username": "octocat"})
    assert response.status_code == 200
    assert service.calls["run_pipeline"] == 1
    body = response.json()
    assert body["github_username"] == "octocat"
    assert body["errors"] == []


def test_analysis_validation_error_for_empty_username(client_default_delegate):
    client, _ = client_default_delegate
    response = client.post("/api/v1/analysis", json={"github_username": ""})
    assert response.status_code == 422


def test_github_endpoint_delegates_to_facade(client_default_delegate):
    client, service = client_default_delegate
    response = client.get("/api/v1/github/octocat")
    assert response.status_code == 200
    assert service.calls["analyze"] == 1
    assert response.json()["username"] == "octocat"


def test_unknown_route_returns_404(client_default_delegate):
    client, _ = client_default_delegate
    assert client.get("/api/v1/nope").status_code == 404


def test_unknown_user_maps_to_404(client_default_delegate):
    """The global exception map turns a service error into HTTP 404."""
    from app.services.github.analyzer import GitHubUserNotFoundError

    client, service = client_default_delegate
    service.analyze_github_username = _raise_re(GitHubUserNotFoundError("gone"))
    response = client.get("/api/v1/github/missing")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "github_user_not_found"


def _raise_re(exc):
    def _inner(*args, **kwargs):
        raise exc

    return _inner