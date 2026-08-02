# Career Intelligence Platform

Understand where you stand, find jobs that actually fit, and close the skill
gaps in between — all from a GitHub username.

Enter a GitHub username and the platform analyzes your public repositories,
builds a structured developer profile, fetches live job postings, ranks them
against your skills, and generates an evidence-backed learning roadmap with
curated resources (never hallucinated ones).

## What it does

- **GitHub Intelligence** — fetches your public repositories, parses dependency
  manifests and READMEs, detects languages/frameworks/libraries, and scores
  repository quality (tests, CI/CD, documentation).
- **Developer Profile** — a single structured object (languages, frameworks,
  libraries, domains, quality score, confidence, evidence) consumed by every
  downstream module. Every skill claim links back to a real repo and file.
- **Job Intelligence** — fetches live job postings (Jobicy free API),
  normalizes them, extracts required skills, and embeds them locally.
- **Matching Engine** — deterministic, no-LLM scoring: sentence-embedding
  similarity (40%) + confidence-weighted skill overlap (40%) + repository
  quality (20%), producing a 0–100 match score and High/Medium/Low confidence.
- **Recommendations** — skill-gap analysis, a week-by-week learning roadmap,
  and portfolio project ideas. Roadmap steps and projects are *grounded* in a
  curated corpus of real resources via retrieval — the LLM never invents
  course names.
- **Explainability** — every score decomposes into components, every skill
  claim has evidence, and every recommendation cites the gap that drives it.
- **Evaluation (Sprint 8)** — a benchmark CLI computing Precision@K, MRR,
  rank correlation, Cohen's kappa (human agreement), and per-stage latency,
  with optional LangSmith tracing and dataset upload.

## Architecture

Orchestrated as a **LangGraph pipeline**; almost all business logic lives in
pure, testable services. Nodes are graph wiring only.

```
GitHub Analyzer ──► Developer Profile Builder ──► Matching ──► Recommendations ──► Guidance
     (parallel with) Job Fetcher
```

The current frontend (Streamlit) imports the backend Python APIs directly
(through `frontend/backend_client.py`) — it does **not** talk to the HTTP layer.
A complete FastAPI HTTP service already exists under `backend/app` (with a
`/health` endpoint, `X-API-Key` auth, and `/api/v1/*` routers) and is the
documented path for a future split; the MVP runs one deployed unit that serves
the Streamlit UI.

## Tech stack

- **Backend:** Python, LangGraph, pydantic, PyGithub, sentence-transformers
  (local embeddings, `all-MiniLM-L6-v2`), SQLite (job cache)
- **Frontend:** Streamlit
- **Observability/eval:** LangSmith (optional, free tier)
- **Deployment:** Docker, Render / Railway

## Repository layout

```
backend/
  app/
    main.py           FastAPI composition root + /health
    api/              routers (github, analysis, jobs, recommendations) + DI (deps.py)
    core/             config (pydantic-settings), exceptions, logging, security (API key)
    database/         SQLAlchemy session + health
    graph/            LangGraph pipeline (state, nodes, routing, retries)
    services/
      career_intelligence.py  application facade (composition root)
      github/         fetch + analyze repositories, detect frameworks, evidence
      developer_profile/  structured DeveloperProfile + confidence
      jobs/           fetch/normalize/parse/embed/cache job postings
      matching/       embedding, similarity, skill overlap, ranking
      recommendations/ gap analysis, grounded roadmap, project suggestions, retriever
      evaluation/     Sprint 8: metrics, benchmark runner, LangSmith integration
  data/
    evaluation_dataset.json   labeled benchmark dataset (3 cases)
    evaluation_reports/       JSON reports written by the benchmark CLI
    jobs.db                   SQLite cache written by the job intelligence layer
frontend/
  app.py              Streamlit UI (dashboard, jobs, roadmap, projects, export)
  backend_client.py   the single seam between the UI and the backend
  report.py           Markdown report export
Dockerfile            single-container image (backend + frontend)
render.yaml           Render Blueprint
railway.json          Railway config
Procfile              fallback for Nixpacks/Heroku-style PaaS builds
docker-compose.yml    local dev with volume-persisted model + job cache
```

## HTTP API

The backend ships a complete FastAPI app (`backend/app/main.py`) even though the
MVP Streamlit frontend calls the Python services directly. It exposes:

- `GET /health` — liveness + database reachability
- `GET /api/v1/github/{username}` — analyze a GitHub profile
- `POST /api/v1/analysis` — run the full pipeline (profile + report)
- `GET|POST /api/v1/jobs` — search and prepare jobs
- `POST /api/v1/recommendations` — build profile, match jobs, generate guidance

Errors use a consistent envelope `{"error": {"code", "message", "details"}}`.
Optional `X-API-Key` auth is enforced only when `REQUIRE_API_KEY=true` and an
`API_KEY` is configured.

## Getting started (local)

Prerequisites: Python 3.11+.

```bash
# 1. Backend
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows; on macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# 2. Frontend
cd ../frontend
pip install -r requirements.txt

# 3. Run
cd ..
streamlit run frontend/app.py
# open http://localhost:8501
```

Optional: create a `.env` from `.env.example` with a GitHub token to raise the
API limit from 60 to 5,000 requests/hour (no scopes needed).

## Running with Docker

```bash
docker compose up --build
# open http://localhost:8501
```

Or build/run the image directly:

```bash
docker build -t career-intelligence-platform .
docker run -p 8501:8501 career-intelligence-platform
```

The image installs **CPU-only torch** to avoid the multi-GB CUDA wheel. The
embedding model (~90 MB) downloads on first use — expect a slower cold start
and slower first analysis, then warm caches (model + `jobs.db`).

## Deploying to Render

1. Push this repository to GitHub.
2. In Render: **New → Blueprint**, select the repo. `render.yaml` is
   auto-detected; replace the `repo:` URL in it first.
3. After the first deploy, set the secrets (`GITHUB_TOKEN`,
   `LANGSMITH_API_KEY`) in the service's **Environment** tab.
4. The service starts on the Starter plan (the embedding model needs >512 MB).
   Health check hits `/_stcore/health`.

## Deploying to Railway

1. In Railway: **New Project → Deploy from GitHub repo**, pick the repo.
2. Railway detects the root `Dockerfile` automatically (see `railway.json`).
3. Add variables `GITHUB_TOKEN`, `LANGSMITH_API_KEY` in the service settings.

## Evaluation (benchmark + metrics)

Run the offline benchmark against the labeled dataset:

```bash
cd backend
python -m app.services.evaluation.cli                 # offline, seed dataset
python -m app.services.evaluation.cli --live          # build profiles via the pipeline
python -m app.services.evaluation.cli --langsmith     # push dataset + report to LangSmith
```

Reported metrics: Precision@1/3/5, Average Precision@10, Recall@3, MRR,
Kendall tau (system vs. human ranking), human agreement rate and Cohen's kappa
(system relevance decisions vs. human labels), plus per-stage latency
(mean and p95). Reports are written to `backend/data/evaluation_reports/`.

Seed-dataset results (Sprint 8): P@1 = 1.0, P@3 ≈ 0.89, MRR = 1.0,
kappa ≈ 0.56, kendall ≈ 0.6.

### LangSmith

Tracing and evaluation activate automatically when credentials are present;
everything degrades gracefully offline.

```
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=career-intelligence-evaluation
```

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `GITHUB_TOKEN` | — | Raise GitHub API limit 60 → 5,000 req/hr |
| `LANGSMITH_API_KEY` | — | Optional LangSmith tracing/evals |
| `LANGSMITH_TRACING` | `false` | Enable tracing when a key is set |
| `LANGSMITH_PROJECT` | `career-intelligence-evaluation` | LangSmith project name |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model |
| `JOB_API_PROVIDER` | `jobicy` | Job API provider (only `jobicy` implemented) |
| `JOB_CACHE_TTL_HOURS` | `6` | Job cache freshness window |
| `JOB_CACHE_DB` | `backend/data/jobs.db` | SQLite cache path |

## Honest limitations

- Free job APIs (Jobicy) cover far fewer postings than LinkedIn/Indeed.
- Analysis only covers public GitHub repositories; thin profiles get a low
  confidence score rather than a misleadingly confident one.
- The learning-resource corpus is a small, curated seed — bigger than MVP is a
  future step, and resources are not yet freshness-checked.
- Matching is deterministic and assumption-based (weights, skill extraction);
  it scores fit, it does not decide for you.
- Docker images are large (~3 GB) because of torch/sentence-transformers.

## Project docs

Detailed requirements live in the repo:

- `Career_Intelligence_Platform_PRD.md` — product requirements
- `Career_Intelligence_Platform_TRD.md` — technical requirements (incl.
  §11 Evaluation metrics)
- `Career_Intelligence_Platform_App_Flow.md` — user flow
- `Backend_Schema.md` — module responsibilities and state contract
- `Implementation_Plan.md` — phased roadmap (Sprint 8 = Evaluation,
  Sprint 9 = Deployment)
