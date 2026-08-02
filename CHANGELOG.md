# Changelog

All notable changes to the Career Intelligence Platform (MVP → production-quality
portfolio) are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/)
and this project tracks the seven production-readiness milestones below.

## [Unreleased]

### Added
- **Automated test suite** (`backend/tests/`): unit tests for matching, GitHub
  analysis, developer-profile building, skill-gap ranking, job retrieval, and
  input validation; integration tests for FastAPI + dependency-injection wiring.
  64 deterministic, offline tests via `python -m pytest` from `backend/`.
  Test fixtures (`tests/conftest.py`) use small fakes (fake embedder, canned
  analyses/jobs) so no model downloads or network calls are needed.
- **GitHub username validation** (`app/core/validation.py`): shared
  `validate_github_username` applied in the `/analysis` request model,
  `/github/{username}` route, and the application service facade (422 on
  invalid input).
- **Dashboard orchestration facade** (`CareerIntelligenceService.generate_dashboard`):
  single entry point the Streamlit frontend reuses (pipeline + job fetch + rank
  + guidance), returning a `DashboardResult` with a `warnings` field for the
  "live jobs unavailable → show cached" path.

### Fixed
- **Frontend duplicated orchestration**: `frontend/backend_client.py` previously
  constructed fresh `JobIntelligence`/`JobRanker`/`CareerGuidanceEngine` and ran
  the pipeline directly, re-implementing logic and loading services independently.
  It now delegates to the shared `CareerIntelligenceService` facade fetched through
  the DI provider, so the orchestrator/embeddings/HTTP clients are built once.

### Changed
- **Performance — shared embedding model**: all `JobEmbedder` instances now share
  a process-wide `SentenceTransformer` cache keyed by model name, so the embedding
  model is loaded at most once per process instead of once per service
  (`JobIntelligence`, `JobRanker`, `ResourceRetriever`).
- **Resource lifecycle**: `JobicyFetcher` and the `JobFetcher` ABC gained
  `close()`; `JobIntelligence.close()` now closes the fetcher's `httpx.Client` in
  addition to the job cache (wired to app shutdown).
- **Dead code removal**: removed the unused `app/repositories/` package and unused
  graph predicates (`has_errors`, `has_github_username`, `has_developer_profile`).
- **Documentation alignment** across `README.md`, `Backend_Schema.md`, PRD, TRD,
  App Flow, and `Implementation_Plan.md` — records implemented vs. planned
  features (e.g. Markdown export implemented / PDF planned).

### Tested
- `cd backend && python -m pytest` → 64 passed.
- `python -m compileall -q app tests` for the backend; `py_compile` for frontend
  modules.
- `create_app()` app factory builds and serves `/health`, `/docs`, and the
  `/api/v1/*` route set.