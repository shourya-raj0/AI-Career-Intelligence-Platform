# Backend Schema

> **Status note.** This document reflects the **implemented** backend as of this
> writing. Earlier drafts described `agents/`, `rag/`, `prompts/`,
> `explainability/`, `faiss_index/` and a Laravel-style multi-table schema; those
> were **not** implemented and are now replaced by the lighter design below.

The backend is a **FastAPI** application that orchestrates deterministic,
service-based business logic behind a thin HTTP layer. A LangGraph pipeline
wraps the two repository-derived analysis stages; all heavier orchestration
(jobs, matching, recommendations) lives in an application-service facade.

---

## Project Structure (implemented)

```
backend/
│
├── app/
│   │
│   ├── main.py                 # FastAPI composition root, lifespan, /health
│   │
│   ├── api/
│   │   ├── deps.py             # Dependency injection (lru-cached shared services)
│   │   └── routes/
│   │       ├── __init__.py     # aggregates routers + optional API-key auth
│   │       ├── github.py       # GET  /api/v1/github/{username}
│   │       ├── analysis.py     # POST /api/v1/analysis
│   │       ├── jobs.py         # GET/POST /api/v1/jobs
│   │       └── recommendations.py  # POST /api/v1/recommendations
│   │
│   ├── core/
│   │   ├── config.py           # pydantic-settings Settings
│   │   ├── exceptions.py       # AppError hierarchy + HTTP handler registration
│   │   ├── logging.py          # dictConfig setup
│   │   └── security.py         # optional X-API-Key auth
│   │
│   ├── database/
│   │   └── session.py          # SQLAlchemy engine/session/health
│   │
│   ├── graph/                  # LangGraph orchestration (thin wiring only)
│   │   ├── graph.py            # build/compile pipeline, run_pipeline
│   │   ├── state.py          # PipelineState TypedDict + PipelineError
│   │   ├── nodes.py          # node functions (analyze_github, build_profile)
│   │   ├── router.py         # post-analysis routing
│   │   └── conditions.py     # pure routing predicates
│   │
│   └── services/               # almost all business logic lives here
│       ├── career_intelligence.py    # application facade (composition root)
│       │
│       ├── github/             # GitHub Intelligence
│       │   ├── analyzer.py            # fetches repos/READMEs/manifests
│       │   ├── framework_detector.py  # parse manifests, detect frameworks/libs
│       │   ├── quality_analyzer.py    # repository engineering-health scoring
│       │   └── evidence_builder.py    # links every claim to a repo/file
│       │
│       ├── developer_profile/  # Developer Profile Builder
│       │   ├── builder.py      # report -> DeveloperProfile
│       │   ├── scorer.py       # languages/skills/domains/projects/practices
│       │   ├── confidence.py   # deterministic confidence score
│       │   └── models.py      # DeveloperProfile pydantic models
│       │
│       ├── jobs/               # Job Intelligence
│       │   ├── fetcher.py      # Jobicy API client + provider factory
│       │   ├── normalizer.py   # raw payload -> structured Job
│       │   ├── parser.py       # required-skill extraction
│       │   ├── embedding.py    # sentence-transformers job embedding
│       │   ├── cache.py        # SQLite job cache (jobs.db)
│       │   ├── pipeline.py     # JobIntelligence: fetch->enrich->embed->cache
│       │   └── models.py      # Job, JobQuery, RequiredSkill
│       │
│       ├── matching/           # Matching Engine
│       │   ├── embedding.py    # developer profile -> vector
│       │   ├── similarity.py   # cosine-similarity primitives (pure numpy)
│       │   ├── skill_overlap.py# confidence-weighted skill overlap
│       │   ├── ranking.py      # JobRanker: combined 0-100 match score
│       │   └── models.py      # MatchResult, MatchBreakdown
│       │
│       ├── recommendations/    # Recommendations / Skill Gap
│       │   ├── gap_analysis.py       # SkillGapEngine
│       │   ├── roadmap.py             # week-by-week learning roadmap
│       │   ├── project_suggestions.py # portfolio project ideas
│       │   ├── retriever.py          # ResourceRetriever (grounded retrieval)
│       │   ├── corpus.py             # curated learning-resource corpus
│       │   ├── guidance.py           # CareerGuidanceEngine facade
│       │   └── models.py            # CareerGuidance pydantic models
│       │
│       └── evaluation/          # offline benchmark + metrics
│           ├── models.py      # BenchmarkCase/Report
│           ├── metrics.py     # P@K, MRR, kappa, kendall, etc.
│           ├── benchmark.py   # BenchmarkRunner
│           ├── langsmith.py  # optional LangSmith push
│           └── cli.py         # python -m app.services.evaluation.cli
│   │
├── data/
│   ├── career.db               # SQLAlchemy (no ORM tables registered yet)
│   └── jobs.db                 # SQLite job cache (Jobicy)
│
└── requirements.txt
```

> Frontend lives under `frontend/` and imports the backend Python APIs directly
> (via `backend_client.py`) — it does not go through FastAPI/HTTP in the MVP
> deployment. See the README.

---

## Module Responsibilities

### API Layer (`app/api`)
- Receives requests, validates, and returns pydantic-serialized responses.
- **No business logic.** All orchestration is delegated to the application
  service facade (`app.services.career_intelligence`).
- **Auth:** optional `X-API-Key` dependency applied at the router level
  (`app/api/routes/__init__.py`), enforced only when `REQUIRE_API_KEY=true` and
  an `API_KEY` is configured.

### Graph (`app/graph`)
Contains only orchestration wiring for the LangGraph pipeline:
- Nodes (`nodes.py`) are thin adapters that call services and translate service
  exceptions into `PipelineError` records.
- Conditional routing (`router.py` + `conditions.py`) decides retry vs. fail vs.
  continue; retries respect `MAX_ANALYSIS_ATTEMPTS`.

The pipeline currently has **two** nodes: `analyze_github` and `build_profile`.
Jobs/matching/recommendations are **not** graph nodes; they are orchestrated
directly in the application service facade. This is intentional and mirrors the
async, fetch-heavy work that would otherwise block a single analysis run.

### Services (`app/services`)
This is where nearly all business logic lives, organized by domain:

- **GitHub Service** — fetches public repos, parses dependency manifests and
  READMEs, detects frameworks/libraries, computes repository-quality, and builds
  evidence. *Never calls an LLM.*
- **Developer Profile Service** — the heart of the project. Converts a
  `GitHubAnalysisReport` into the single structured `DeveloperProfile` consumed
  by every downstream module.
- **Job Intelligence Service** — fetches (Jobicy), normalizes, extracts skills,
  embeds, and caches job postings (`jobs.db`).
- **Matching Service** — deterministic: embedding similarity + skill overlap +
  repository quality -> ranked `MatchResult`s. *Never generates explanations.*
- **Recommendation Service** — gap analysis, grounded learning roadmap, and
  portfolio project suggestions. All grounded in a curated local corpus via
  retrieval — no invented resources.
- **Evaluation Service** — offline benchmark CLI, metrics, and optional
  LangSmith integration.

### Application Service (`app/services/career_intelligence.py`)
- :class:`CareerIntelligenceService` is the single application-level entry point
  the API talks to. It composes the diagrams service above into a few
  orchestration methods (`analyze_github_username`, `run_analysis`,
  `search_jobs`, `generate_recommendations`, `close`).
- It does **not** re-implement business logic; it only coordinates.

---

## Data Storage

| Data | Store | Notes |
|---|---|---|
| Jobs cache | SQLite (`backend/data/jobs.db`) | `JobCache`, keyed by resolved query, TTL from `JOB_CACHE_TTL_HOURS` |
| Career SQLAlchemy DB | SQLite (`backend/data/career.db`) | Engine defined; **no ORM models or tables registered in the MVP** |
| GitHub analysis | derived at runtime | not persisted in the MVP |
| Learning-resource corpus | in-memory curated list (`corpus.py`) | replaced RAG/`faiss` design; embeddings cached in memory |

---

## LangGraph State

```python
class PipelineState(TypedDict, total=False):
    github_username: str
    github_report: GitHubAnalysisReport
    developer_profile: DeveloperProfile
    job_preferences: dict | None
    job_postings: list | None      # reserved
    ranked_jobs: list | None        # reserved
    recommendations: list | None    # reserved
    explanations: list | None        # reserved
    errors: list[PipelineError]
    retries: int
```

Fields for stage outputs that are **not yet graph nodes** (jobs, matching,
recommendations, explanations) are present in the contract so the schema is
stable while those stages land.

---

## Request Flow (HTTP API, via FastAPI)

```
Client ─► FastAPI (/api/v1/...) ─► CareerIntelligenceService ─► services
   ▲                                                              │
   └──────────────────────── pydantic response ◄─────────────────┘
```

For the GitHub analysis path specifically:

```
FastAPI /analysis
   └─► run_analysis()
         └─► run_pipeline()   (LangGraph)
                ├─ analyze_github Node ─► GitHubAnalyzer
                └─ build_profile Node ─► DeveloperProfileBuilder
```

GitHub jobs/matching/recommendations are reached via
`generate_recommendations()` which calls `run_pipeline()` then the
`JobIntelligence`, `JobRanker`, and `CareerGuidanceEngine` services.

---

## Key Architecture Facts

- **One clean `DeveloperProfile` object** is the single source of truth between
  GitHub analysis and matching/gap/recommendations — the original "Matcher reads
  raw GitHub output" design was replaced by a dedicated builder between steps.
- **Deterministic scoring** everywhere that counts (matching, skill overlap,
  confidence, gap importance); no LLM is called for scoring.
- **Service instances are shared** through `@lru_cache(maxsize=1)` in
  `app/api/deps.py`, so the embedding model and HTTP clients are constructed
  once per process.
- Everything runs on the CPU locally or in Docker.