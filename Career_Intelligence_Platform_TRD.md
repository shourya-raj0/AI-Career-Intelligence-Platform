Technical Requirements Document (TRD)

Career Intelligence Platform

> **Status note.** This document records the target technical design. Where the
> implemented code differs, the implemented choice is noted inline. Current
> implemented stack: Python 3.12, FastAPI, LangGraph, pydantic, PyGithub, httpx,
> sentence-transformers (`all-MiniLM-L6-v2`), SQLite. Groq/LangChain/FAISS are
> **not** used — see the implementation-status note at the bottom.



# 1. Introduction

Purpose

Scope

Technical Goals

# 2. System Architecture

High-level architecture

Main components

Frontend

Backend

LangGraph

Database

External APIs

# 3. Technology Stack

## Frontend

Streamlit (imports backend Python APIs directly via `backend_client.py`)

## Backend

FastAPI (HTTP layer, `/api/v1/*` + `/health`)
pydantic (models/validation)
PyGithub (GitHub API client)
httpx (job API client)
SQLAlchemy (career DB session)

## AI

LangGraph (pipeline for GitHub → Developer Profile)
Sentence Transformers (`all-MiniLM-L6-v2`, local embeddings)

> LangChain, Groq, and FAISS are listed for awareness but are **not** used in the
> current implementation.

## Storage

SQLite (job cache `jobs.db`; empty career DB)
In-memory curated learning-resource corpus (replaces an earlier FAISS design)

## Monitoring

LangSmith

# 4. Core Components

## 4.1 GitHub Intelligence

### Purpose

Analyze repositories

Extract developer signals

### Input

GitHub Username

### Output

Repository Signals

Evidence

Confidence

## 4.2 Developer Profile Builder

### Purpose

Convert GitHub signals into one structured developer profile

### Output

Skills

Frameworks

Domains

Quality

Evidence

Confidence

## 4.3 Job Intelligence

### Purpose

Fetch and normalize job postings

## 4.4 Matching Engine

### Purpose

Rank jobs

### Uses

Embeddings

Skill overlap

Repository quality

### Output

Match Score

Match Breakdown

## 4.5 Skill Gap Engine

### Purpose

Compare required vs existing skills

### Output

Missing Skills

Priority

## 4.6 Recommendation Engine

### Purpose

Generate learning roadmap

Suggest portfolio projects

### Uses

RAG

## 4.7 Explainability Engine

### Purpose

Explain why a job matched

Show evidence

Show confidence

# 5. LangGraph Workflow

Document

Nodes

State

Conditional Routing

Parallel Execution

Retry Logic

# 6. Data Flow

GitHub

↓

GitHub Intelligence

↓

Developer Profile

↓

Job Intelligence

↓

Matching

↓

Gap Analysis

↓

Recommendation

↓

Explainability

↓

Dashboard

# 7. Database

## Tables

Implemented

jobs (SQLite job cache: query_key, normalized fields, required_skills, embedding, fetched_at)

Planned / not yet implemented in the MVP

github_cache
developer_profiles
evaluation_dataset
RAG documents / embeddings (in-memory corpus today, persisted RAG is future)

# 8. External Integrations

GitHub API (implemented, optional token)
Jobicy Job API (implemented)
LangSmith (optional tracing/evals)

> Groq is not an external integration in the implemented system (no LLM is used
> for scoring or guidance generation).

# 9. Security

Environment Variables

API Keys

Rate Limiting

Input Validation

# 10. Performance

Caching

Parallel Execution

Batch Embeddings

Retry Strategy

# 11. Evaluation

## Metrics

Precision@K

Human Agreement

Latency

Response Time

# 12. Limitations

GitHub-only users

Limited free job APIs

Small RAG corpus

Deterministic scoring assumptions

---

## Implementation Status Summary (TRD)

Implemented

- FastAPI HTTP layer (`/health`, `/api/v1/*`) with optional `X-API-Key` auth.
- LangGraph pipeline with two nodes (`analyze_github`, `build_profile`); jobs →
  matching → recommendations are orchestrated in the app-service facade.
- Local embeddings via sentence-transformers; SQLite job cache.
- Deterministic matching, skill-gap analysis, grounded roadmap + portfolio
  projects, and an offline evaluation CLI.

Not implemented (planned / deferred)

- LangChain chains, Groq LLM calls, and FAISS vector store.
- Persisted RAG documents, embeddings table, and evaluation-dataset table.
- Full multi-node graph with per-stage parallel execution for jobs/matching/
  recommendations.
- User accounts and resume/ATS features.