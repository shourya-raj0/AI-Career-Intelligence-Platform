Career Intelligence Platform (Solo MVP)

Product Requirements Document (PRD)

Version | v1.0

Author | Shourya Rajput

Status | Draft





# 1. Product Vision

Career Intelligence Platform is an AI-powered application that helps software developers understand where they currently stand in their careers, discover suitable job opportunities, identify skill gaps, and receive evidence-backed learning recommendations.

Unlike traditional job portals that only recommend jobs based on keywords, the platform automatically constructs a structured developer profile using publicly available GitHub repositories and combines deterministic scoring with AI-generated explanations.

The objective is not to replace recruiters, but to help developers continuously improve their employability through actionable insights.

# 2. Problem Statement

Students and early-career developers often face several challenges:

They don't know if their GitHub profile reflects their actual skills.

They manually compare themselves against dozens of job descriptions.

They struggle to identify which missing skills actually matter.

Learning resources are scattered across multiple websites.

Most career advice is generic rather than personalized.

Current solutions either focus only on resume parsing or simply recommend jobs based on keyword matching.

There is no lightweight platform that automatically analyzes a developer's public work, identifies evidence-backed skills, compares them with real job requirements, and generates personalized recommendations.

# 3. Goals

The MVP should enable users to:

Analyze a public GitHub profile.

Build a structured developer profile.

Match the profile against live job postings.

Identify missing skills.

Explain why each job matches.

Recommend learning resources.

Suggest portfolio projects to close skill gaps.

# 4. Non Goals

The MVP will NOT include:

Resume optimization

ATS score prediction

LinkedIn scraping

LinkedIn authentication

Automatic job applications

Fine-tuning custom LLMs

Real-time recruiter dashboards

User authentication

Team collaboration

These are future roadmap items.

# 5. Target Users

## Primary

Computer Science students

Fresh graduates

Internship seekers

Junior software engineers

## Secondary

Bootcamp students

Open-source contributors

Career switchers

# 6. User Journey

## Step 1

User enters GitHub username.

↓

## Step 2

System analyzes repositories.

↓

## Step 3

System builds Developer Profile.

↓

## Step 4

User selects:

Desired role

Location

Experience level

↓

## Step 5

Platform retrieves live job postings.

↓

## Step 6

System ranks jobs.

↓

## Step 7

Platform identifies:

Strengths

Missing skills

Match confidence

↓

## Step 8

Platform generates:

Learning roadmap

Portfolio project suggestions

Plain-language explanation

# 7. Core Features (MVP)

## Feature 1 — GitHub Intelligence

Input:

GitHub username

Output:

Languages

Frameworks

Repository quality

Engineering practices

Developer confidence

Structured Developer Profile

## Feature 2 — Career Matching

Input:

Developer Profile

Live Job

Output:

Match score

Confidence

Skill overlap

## Feature 3 — Skill Gap Analysis

Output:

Missing skills

Priority order

Difficulty

Importance

## Feature 4 — Learning Roadmap

Generate:

Week-by-week learning plan

Grounded using retrieved learning resources.

## Feature 5 — Portfolio Project Suggestions

Instead of only saying

Learn Docker

Suggest

Build a FastAPI microservice and deploy it with Docker.

Every missing skill should map to one or more practical project ideas.

## Feature 6 — Explainability

Instead of

83%

Show

Why matched

Missing requirements

Strongest evidence

Confidence level

# 8. Developer Profile

This is the heart of the product.

Every downstream module consumes one structured object.

Developer Profile

Languages

Frameworks

Libraries

Domains

Projects

Repository Quality

Engineering Practices

Evidence

Confidence

This object becomes the single source of truth.

# 9. Evidence-Based Skills

Every inferred skill must include evidence.

Example

FastAPI

Confidence

96%

Evidence

Repository — AI Job Matcher — requirements.txt — FastAPI

Repository — Portfolio — main.py — FastAPI()

No black-box AI.

Every recommendation should be explainable.

# 10. Functional Requirements

The system shall:

Analyze multiple repositories.

Infer frameworks from dependency files.

Build a unified developer profile.

Fetch live job postings.

Rank jobs.

Identify missing skills.

Generate learning roadmap.

Suggest portfolio projects.

Explain recommendations.

Cache repeated requests.

# 11. Non-Functional Requirements

The system should:

Complete analysis within 20–40 seconds for typical GitHub profiles.

Handle GitHub API rate limits gracefully.

Remain usable on free-tier infrastructure.

Produce deterministic match scores.

Generate reproducible recommendations.

Keep architecture modular for future expansion.

# 12. Success Metrics

The MVP will be considered successful if it can:

Analyze public GitHub profiles without crashing.

Produce consistent rankings for repeated inputs.

Correctly infer common frameworks from repositories.

Generate grounded learning roadmaps.

Provide explanations that align with deterministic scores.

Be deployed publicly and demonstrated through a live demo.

# 13. Technical Constraints

The project must:

Be buildable by one developer.

Use free APIs and free deployment tiers.

Run locally without paid cloud infrastructure.

Avoid scraping restricted websites.

Avoid requiring GPU servers.

# 14. Future Roadmap

Future releases may include:

Resume parser

ATS optimization

LinkedIn integration

Feedback-based ranking improvements

User accounts

Historical career progress

Recruiter dashboard

Resume generation

Interview preparation agent

# 15. Why This Product Exists

The platform is designed to bridge the gap between a developer's public work and real-world job requirements.

Rather than acting as another chatbot, it functions as an explainable career intelligence system that combines deterministic engineering analysis with AI-generated guidance, helping developers understand not only which jobs fit them, but why, what they're missing, and how to improve.

# 16. Implementation Status

This section records, per feature, whether it is **implemented** in the current
MVP or **planned** for a future release. It exists so the PRD's earlier
"Core Features" text is never mistaken for a promise that every item is already
built.

## Implemented Features

| Feature | Notes |
|---|---|
| GitHub Intelligence (Feature 1) | Done. Analyzes public repos, parses dependency manifests + READMEs, detects languages/frameworks/libraries, scores repository quality. |
| Structured Developer Profile | Done — single `DeveloperProfile` object with languages, frameworks, libraries, domains, projects, quality score, confidence, evidence. |
| Job Intelligence | Done — fetches live Jobicy postings, normalizes, extracts required skills, embeds, caches in SQLite. |
| Matching Engine (Feature 2) | Done — deterministic 0–100 match score (semantic 0.4 + confidence-weighted skill overlap 0.4 + repository quality 0.2), High/Medium/Low confidence. |
| Skill Gap Analysis (Feature 3) | Done — missing skills, priority, difficulty, importance, demanded-by job titles. |
| Learning Roadmap (Feature 4) | Done — grounded week-by-week roadmap with retrieved resources. |
| Portfolio Project Suggestions (Feature 5) | Done — gap skills map to concrete project ideas. |
| Explainability (Feature 6) | Done — component breakdown, evidence links, confidence; the summary is currently deterministic (no LLM). |
| Response caching | Done — job results cached per query with a TTL. |
| FastAPI HTTP service | Done — `/health` + `/api/v1/*` routers with optional API-key auth. |
| Evaluation / benchmark CLI | Done — offline metrics incl. Precision@K, MRR, kappa, kendall, latency; optional LangSmith. |

## 16.2 Planned Future Enhancements

|Area | Planned capability |
|---|---|
| Resume parsing & ATS scoring | Not implemented (explicitly out of MVP scope). |
| LinkedIn / external profile ingestion | Not implemented. |
| User accounts, auth, saved history | Not implemented (only optional shared `X-API-Key`). |
| Recruiter/dashboard views | Not implemented. |
| Fully autonomous graph nodes for jobs/matching/recommendations | Currently orchestrated in the app-service facade; turning each into its own LangGraph node is a future refactor. |
| Expanded learning-resource corpus / true vector RAG | Corpus retrieval is in-memory today; a fuller, freshness-checked RAG pipeline is planned. |
| PDF report export | Markdown export is implemented; PDF is a future step. |
| Manual skills entry for thin profiles | Referenced in the App Flow "Error Flow" as (Phase 2); not yet implemented. |
| Interview-prep agent / feedback-based ranking | Future roadmap items. |

> Non-Goals from §4 remain non-goals and are repeated here for clarity: resume
> optimization, ATS prediction, LinkedIn scraping/auth, automatic applications,
> fine-tuning custom LLMs, real-time recruiter dashboards, user authentication,
> and team collaboration.