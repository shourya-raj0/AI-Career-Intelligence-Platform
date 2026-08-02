# AI-Powered Job Match Engine — Revised Plan (v3, Multi-Agent + LangGraph + RAG)

**v2 → v3 changes:** v2 fixed the legal/scraping issues, the fake accuracy claim, and added real technical depth (framework detection, rate limits, scoring formula). v3 restructures the backend as a **multi-agent LangGraph pipeline** instead of a linear script, adds a **small RAG layer** to ground the learning-roadmap feature in real curated resources instead of LLM guesswork, and wires in **LangSmith** for tracing and evaluation. Nothing here is added for buzzword value — each piece is justified below, including the honest "isn't this overkill?" answer, the same way v2 was honest about FAISS.

Everything below still uses only free tools/APIs and can run entirely on your laptop + a free deployment tier.

---

## What It Does (User Journey) — unchanged, now agent-driven

1. User connects GitHub
   ↓
2. **GitHub Analyzer Agent** extracts software engineering signals from their repos (not "understanding" the code)
   - Languages, inferred frameworks, project types
   - Engineering-health signals: README quality, tests folder present, CI config present, commit activity, repo size
   - Soft-skill proxies (testing present, docs present, structure)
   ↓
   > Wording note (unchanged from v2): never say "AI analyzes the code." Say **"extracts software engineering signals from repository metadata and structure."**
   ↓
3. User enters job preferences (roles, location, company size)
   ↓
4. **Job Fetcher Agent** pulls real postings from a legitimate free API (not scraped) — runs **in parallel** with step 2, since the two don't depend on each other
   ↓
5. **Matcher Agent** scores fit (embeddings + skill overlap + quality), **Gap Analysis** does a deterministic set-difference
   ↓
6. **RAG Roadmap Agent** turns the gap into a week-by-week plan, grounded in a small retrieved corpus of real learning resources (not hallucinated from the LLM's parametric memory)
   ↓
7. **Explainer Agent** turns score + gap + roadmap into plain-language "why you match / what's missing"
   ↓
8. User gets a ranked list:
   ```json
   [
     {
       "job": "Backend Engineer at Stripe",
       "match_score": 0.87,
       "confidence": "Medium",
       "why_match": ["5 Python projects", "System design experience"],
       "gaps": ["Payment processing experience"],
       "roadmap": ["Week 1: Stripe API docs", "Week 2: Build a small payments app"],
       "salary_range": "Not always available — see note below"
     }
   ]
   ```

> Note (unchanged): free job APIs often don't include salary data reliably. Don't fabricate it.

---

## Why Multi-Agent + LangGraph At All? (The Honest Answer)

Be ready for this question, the same way v2 pre-empted "why FAISS for 500 jobs?":

**Them:** "Isn't this pipeline basically linear? Why do you need a graph framework and multiple agents for that?"

**You:** "Most of it *is* sequential, and I don't dress that up. The real reasons I used LangGraph instead of a plain function-call chain:
1. **Genuine parallelism** — GitHub analysis and job fetching don't depend on each other, so they run as parallel branches that join before matching. That's real wall-clock time saved, not decoration.
2. **Conditional routing, not just a straight line** — if GitHub confidence is too low (e.g., a near-empty profile), the graph routes to a fallback node instead of silently producing a misleading high-confidence score.
3. **Retry/error handling as a graph loop, not scattered try/except** — a rate-limited node increments a retry counter in state and a conditional edge decides whether to loop back or fall through to an error node, instead of ad-hoc exception handling copy-pasted into every function.
4. **State is explicit and typed** — every agent reads/writes a single shared, typed state object, so debugging a bad output means inspecting one state trace, not chasing variables across files.
5. **It gave me a real trace of the pipeline in LangSmith** (below), which is genuinely useful for debugging and for talking about evals in interviews.

If the pipeline were *purely* linear with no branching, no parallelism, and no failure handling, I'd agree LangGraph would be overkill — a plain Python pipeline would be the honest choice. The branching and parallelism here are real, so the framework earns its place."

This is the answer you give — memorize the shape of it, not the words.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│ Frontend (Streamlit — free, local or HF Spaces)  │
│ - GitHub username input                          │
│ - Job preferences form                            │
│ - Results dashboard with match scores + roadmap   │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│ LangGraph Orchestrator (StateGraph, shared state) │
│                                                    │
│        ┌──────────────┐   ┌──────────────────┐   │
│        │ GitHub        │   │ Job Fetcher       │   │
│  ┌────▶│ Analyzer Agent│   │ Agent             │◀──┐│
│  │     └──────┬───────┘   └────────┬──────────┘  ││
│  │            │  (parallel, async — both run,    ││
│  │            │   router below runs once both     ││
│  │            └───────────┬───────────────────────┘│
│  │                        │   finish; no separate  │
│  │                        ▼   join node needed)     │
│  │              ┌──────────────────┐                 │
│  │  low         │ Confidence Router │                 │
│  └──confidence──┤ (conditional edge)│                 │
│     fallback    └─────────┬────────┘                 │
│     (ask for              ▼                          │
│     resume/manual  ┌──────────────┐                  │
│     skills input)  │ Matcher Agent │                  │
│                     │ (embeddings + │                  │
│                     │ skill overlap│                  │
│                     │ + quality)    │                  │
│                     └──────┬───────┘                  │
│                            ▼                           │
│                     ┌──────────────┐                  │
│                     │ Gap Analysis  │ (deterministic,  │
│                     │ node          │  no LLM)         │
│                     └──────┬───────┘                  │
│                            ▼                           │
│                  ┌───────────────────┐                │
│                  │ RAG Roadmap Agent  │                │
│                  │ (retrieves learning│                │
│                  │ resources, then LLM│                │
│                  │ sequences them)    │                │
│                  └─────────┬─────────┘                │
│                            ▼                           │
│                  ┌───────────────────┐                │
│                  │ Explainer Agent     │                │
│                  │ (LLM: plain-language│                │
│                  │ why-match / gaps)   │                │
│                  └─────────┬─────────┘                │
│                            ▼                           │
│                     back to Streamlit                  │
│                                                          │
│  Every node emits a trace event → LangSmith             │
└──────────────────────────────────────────────────────────┘
```

---

## Core Features (Realistic MVP)

### Phase 1 — MVP (aim for 3 weeks, not 2)

**1. GitHub Analyzer Agent — same feasibility notes as v2, now a graph node**

There's no simple API that tells you "this project uses Django" — same manifest-parsing approach as v2:
- Parse `requirements.txt`/`pyproject.toml`, `package.json`, `pom.xml`, `Cargo.toml`, `go.mod`
- Match known package names against a lookup table to infer frameworks
- Code-quality signals: README, tests folder, CI workflow, commit count/recency, stars/forks, repo size
- Multi-repo aggregation into **one combined weighted profile-text** (unchanged from v2 — this is still what gets embedded)
- Always authenticate to GitHub (5,000 req/hour vs 60), cache every response in SQLite

**As a LangGraph node:** this agent reads `github_username` from shared state and writes `repo_signals`, `profile_text`, and a `confidence` field back to state. Low confidence (e.g., fewer than 3 real repos, or all forks with no original commits) is what the Confidence Router checks before deciding whether to proceed or fall back.

**2. Job Fetcher Agent — same free/legal sources as v2, now runs in parallel**
- Adzuna / Remotive / RemoteOK / USAJobs — pick one, free tier or key-free
- Normalize into a common schema, store in SQLite
- Runs concurrently with the GitHub Analyzer Agent since it needs only the job-preferences input, not the GitHub output — the graph joins both branches before the Matcher Agent runs

**3. Matcher Agent — same formula as v2**
- Embed the combined profile-text and each job description with a local Sentence-Transformers model
- Weighted score, same as v2:
  ```
  score = 0.7 * cosine_similarity(profile, job)
        + 0.2 * skill_overlap(profile_skills, job_skills)
        + 0.1 * quality_score(repo_signals)
  ```
- Plain cosine similarity via scikit-learn is enough at this scale; FAISS is optional practice, same honest caveat as v2 — and note FAISS is now doing double duty (see RAG section below)

**4. Gap Analysis — still deterministic, not an "agent"**
- Simple set difference, same as v2: `job_skills - profile_skills = gap`
- Explicitly *not* an LLM call — kept as a plain graph node so the pipeline stays auditable

**5. RAG Roadmap Agent — new in v3**

v2's "Learning Roadmap" feature asked the LLM to generate a week-by-week plan from scratch. That works, but it's ungrounded — the LLM can invent a plausible-sounding but generic or subtly wrong curriculum. v3 grounds it:

- Build a small curated corpus (aim for **~30–40** short documents to start — see timeline note below) of real learning resources: official doc summaries, "roadmap.sh"-style skill breakdowns, freeCodeCamp/MDN topic summaries — written or curated by you, not scraped, so there's no licensing question
- Embed the corpus with the same Sentence-Transformers model, store in a **second FAISS index** (separate from the job-matching index)
- For each missing skill in the gap, retrieve the top-2–3 most relevant resource chunks
- Pass the retrieved chunks + the gap list to the LLM with an explicit instruction: *sequence these retrieved resources into a week-by-week plan, don't invent resources not given to you*
- This is a legitimate, small-scale RAG use case — retrieval genuinely changes the output (grounded resource names) rather than being decorative

**Why this is real RAG and not just "add a vector DB":** the retrieval step directly constrains what the LLM is allowed to cite as a resource. Without it, the LLM would just be free-associating plausible course names, some of which may not exist or may be outdated. With it, every resource mentioned in the roadmap came from a corpus you can point to.

**6. Explainer Agent — same job as v2's "LLM Analysis", still explains, never scores**
- Takes `score`, `overlap`, `gap`, and the roadmap from state
- Turns them into plain-language "why you match / what's missing" — deterministic inputs, LLM only for wording
- Free-tier LLM API (Groq or similar), cache outputs in SQLite

**7. Streamlit UI — unchanged from v2**
- Dashboard, score display, confidence, roadmap, star-rating breakdown
- Export (PDF/Markdown) — still build this last

### Phase 1.5 — Same memorable features as v2, now agent outputs

- **Learning Roadmap** — now RAG-grounded (see above), not just LLM freeform
- **Confidence Score** — now explicitly computed inside the GitHub Analyzer Agent and used by the Confidence Router to decide whether to proceed or fall back, not just a cosmetic label
- **Explainability breakdown** (star ratings per skill) — unchanged from v2
- **Known bias** (repo count vs. quality) — unchanged from v2, still worth raising proactively in interviews

**Phase 2 (still future work, not built now):** users without GitHub upload a resume/PDF or manually enter skills instead. In the v3 architecture this becomes a real fallback branch the Confidence Router can route to, rather than a separate disconnected feature — worth mentioning as "the graph structure already has the branch point for this, I just haven't built the resume-parsing node yet."

---

## Multi-Agent Architecture with LangGraph — Implementation Notes

**Shared state (a single TypedDict, not a dict-of-dicts):**
```python
from typing import Annotated
import operator

class PipelineState(TypedDict):
    github_username: str
    job_prefs: dict
    repo_signals: dict | None
    profile_text: str | None
    confidence: str | None       # "High" / "Medium" / "Low"
    job_postings: list | None
    match_results: list | None
    gaps: dict | None
    roadmap: dict | None
    explanations: dict | None
    errors: Annotated[list, operator.add]   # needs a reducer — see note below
    retries: dict                # per-node retry counters
```

**Important implementation detail — reducers for parallel writes:** `github_analyzer` and `job_fetcher` run in the same graph step and write to *different* keys (`repo_signals`/`profile_text`/`confidence` vs. `job_postings`), so those fields are fine as plain values — no conflict. But `errors` is a field either node might append to in that same step, and LangGraph raises `INVALID_CONCURRENT_GRAPH_UPDATE` if two parallel nodes write to the same key without a merge strategy. Marking it `Annotated[list, operator.add]` tells LangGraph to concatenate both nodes' error lists instead of throwing. This is a real crash you'll hit in testing if skipped, not a style preference.

**Graph shape:**
- `github_analyzer` and `job_fetcher` as parallel entry nodes (both read from `START`) — for the parallelism to actually save wall-clock time (not just look parallel on the diagram), implement both as `async def` nodes and invoke the graph with `.ainvoke()`; synchronous blocking calls to two different APIs won't overlap their I/O wait just because LangGraph scheduled them in the same step
- Both feed directly into `confidence_router` — no separate "join" node needed, since a node with two incoming edges only runs once both predecessors complete; the router itself is the join point
- `confidence_router` is a **conditional edge**: routes to `matcher` normally, or to a `fallback_request_manual_input` node if confidence is "Low"
- `matcher → gap_analysis → rag_roadmap → explainer → END`
- Rate-limit/API-failure handling: each external-API node (`github_analyzer`, `job_fetcher`) tracks its own attempt count in `retries`; a conditional edge checks that count on failure and either loops back to the same node (with a backoff delay implemented in plain Python, not a graph feature) or routes to an `error` node once a cap (e.g. 3 attempts) is hit, so the user gets a clear message instead of a crash

**What NOT to over-engineer:** don't add a "supervisor LLM" that dynamically decides the whole routing at runtime — that's a common LangGraph demo pattern but it's unjustified complexity here. The routing logic (confidence threshold, retry count) is simple, deterministic Python inside conditional edge functions. Keep the LLM calls confined to the two nodes that actually need language generation (`rag_roadmap`, `explainer`).

---

## LangSmith — Tracing and Evaluation

- Enable LangSmith tracing (free Developer tier) by setting the tracing environment variables — every node run, LLM call, and retriever call is automatically logged. `LANGCHAIN_TRACING_V2`/`LANGCHAIN_API_KEY` still work, but LangChain has been shifting toward `LANGSMITH_TRACING`/`LANGSMITH_API_KEY` in newer docs — either works, don't be thrown by seeing both
- Build the manually-labeled set of profile-job pairs (already part of v2's validation plan) as a **LangSmith dataset**, and run it as a periodic eval instead of a one-off manual check — this gives you a repeatable accuracy number instead of a single validation run you can't easily re-check after tuning weights
- Use per-node traces to answer "why is this slow" honestly — e.g., if the embedding step or the LLM explainer is the bottleneck, the trace shows it, rather than guessing
- Free-tier note: the Developer plan gives 5,000 traces/month with **14-day retention** — enough for active development and a demo, but you can't pull up a trend from a month ago on the free tier. If asked about long-term monitoring, the honest answer is "that needs the paid Plus tier"

**Interview value:** "I could point to a specific trace and say exactly which node was the bottleneck or where a bad output came from, instead of describing my debugging process in the abstract."

---

## Tech Stack (100% Free)

| Component | Technology | Cost |
|---|---|---|
| Frontend | Streamlit | Free |
| Orchestration | LangGraph (StateGraph) | Free (open source) |
| Observability/Eval | LangSmith (free developer tier) | Free |
| GitHub API | PyGithub | Free |
| Job Data | Adzuna / Remotive / RemoteOK API | Free |
| Embeddings | Sentence-Transformers (local) | Free |
| Similarity / RAG index | scikit-learn cosine similarity + FAISS (job matching AND roadmap corpus) | Free |
| LLM | Groq free tier (or similar), called via LangChain's model wrappers | Free |
| Data models | pydantic | Free |
| Code metrics (optional stretch) | radon (Python only) | Free |
| HTTP | requests / httpx | Free |
| Data Storage | SQLite (local) | Free |
| Deployment | Hugging Face Spaces | Free |

Same caveats as v2 still apply: manually test whichever job API you pick before architecting around it, and cache aggressively everywhere (GitHub responses, embeddings, job postings, LLM outputs, and now retriever results too).

---

## Project Structure

```
job-matcher-ai/
├── app/
│   ├── __init__.py
│   ├── agents/
│   │   ├── github_analyzer.py      # Agent: analyze GitHub profiles
│   │   ├── job_fetcher.py          # Agent: pull postings from free job APIs
│   │   ├── matcher.py              # Agent: embeddings + scoring
│   │   ├── gap_analysis.py         # Deterministic node, not an LLM agent
│   │   ├── rag_roadmap.py          # Agent: retrieval + roadmap generation
│   │   └── explainer.py            # Agent: LLM plain-language explanations
│   ├── graph.py                    # LangGraph StateGraph definition, edges, routing
│   ├── state.py                    # Shared PipelineState TypedDict
│   ├── rag/
│   │   ├── corpus/                 # Curated learning-resource documents
│   │   ├── build_index.py          # Embeds corpus into FAISS
│   │   └── retriever.py            # Top-k retrieval for a given skill gap
│   ├── embeddings.py                # Shared embedding utilities
│   └── database.py                  # SQLite management (cache + storage)
├── data/
│   └── jobs.db                      # Job + cache database
├── streamlit_app.py                 # Main UI, invokes the compiled graph
├── Dockerfile
├── requirements.txt
├── README.md
└── .gitignore
```

---

## Realistic Timeline (3 Weeks, Solo)

**Days 1–4: GitHub Analyzer Agent**
- GitHub API integration, auth, framework inference, engineering-health signals
- Multi-repo aggregation into weighted profile-text
- Add confidence scoring here — this feeds the router later

**Days 5–7: Job Fetcher Agent + LangGraph Skeleton**
- Test and integrate chosen job API, normalize schema, cache in SQLite
- Stand up the basic StateGraph: two parallel entry nodes joining into a placeholder downstream node, confirm parallelism actually works before adding real logic

**Days 8–10: Matcher + Gap Analysis Nodes**
- Embeddings, weighted score formula, set-difference gap
- Wire the confidence router's conditional edge (route to fallback vs. matcher)
- Sanity-check against manual examples

**Days 11–13: RAG Roadmap Agent**
- Curate a **~30–40 document** learning-resource corpus covering the most common gap skills (Docker, Kubernetes, AWS, SQL, testing, CI/CD, system design) — treat 100+ docs as a post-MVP stretch goal, not a day-11-13 target; writing that many good short docs by hand realistically takes longer than 3 days on top of everything else
- Build the second FAISS index, retrieval function, and the roadmap-generation prompt that's restricted to retrieved resources

**Days 14–15: Explainer Agent + LangSmith Wiring**
- Prompt design for why-match/gaps, still deterministic scoring underneath
- Turn on LangSmith tracing, confirm you can see a full run trace across all nodes

**Days 16–17: Streamlit UI**
- Dashboard, score/confidence/roadmap display, invoke the compiled graph from the UI

**Days 18–19: Testing & Polish**
- Test with 15–20 real GitHub profiles
- Build the LangSmith eval dataset from manually labeled profile-job pairs, run it, record the agreement number
- Fix bugs, tune weights, think through the repo-count-vs-quality bias

**Days 20–21: Deploy + Document**
- Docker setup, deploy to HF Spaces (Sentence-Transformers models are 100MB+, expect a slower cold start)
- README honest about scope, limitations, and the multi-agent design decisions

---

## Resume Line (Rewritten)

> Built a multi-agent job-matching pipeline orchestrated with LangGraph — parallel agents extract software engineering signals from GitHub repositories and fetch live job postings, a deterministic scoring node combines sentence-embedding similarity with rule-based skill overlap, and a RAG agent grounds a generated learning roadmap in a curated resource corpus (retrieved via FAISS) rather than free-form LLM generation. Used LangSmith to trace agent execution and run evaluations against a manually labeled set of profile-job pairs, achieving [X]% agreement with human judgment.

Same rule as v2: fill in `[X]%` only after you've actually run that eval. If not done yet, say "validated on a manually labeled sample" instead.

---

## Interview Story (Rewritten)

**Them:** "Walk me through your job matcher project."

**You:**
"Job searching is overwhelming, especially early in your career. I built a multi-agent pipeline with LangGraph:
- A GitHub Analyzer agent and a Job Fetcher agent run in parallel, since neither depends on the other
- Their outputs join at a confidence router — if the GitHub profile is too thin to trust, it routes to a fallback instead of producing a misleadingly confident score
- A Matcher agent combines embedding similarity with a rule-based skill-overlap score — deterministic, not an LLM decision
- A RAG agent turns the skill gap into a week-by-week roadmap, but only using resources retrieved from a corpus I curated — so it's not inventing course names
- An Explainer agent turns the numbers into plain language — the LLM explains, it never scores

I used LangSmith to trace every node, which let me actually see which step was slow or wrong instead of guessing, and to run a repeatable eval against a labeled set of profile-job pairs."

**Them:** "Isn't LangGraph overkill for what sounds like a mostly linear pipeline?"

**You:** *(see the "Why Multi-Agent + LangGraph At All?" section above — give that answer, don't overclaim.)*

**Them:** "Why not just have the LLM generate the roadmap directly?"

**You:** "I tried that first, and it worked, but it would sometimes recommend resources that were outdated or didn't quite exist as described. Restricting it to retrieve-then-sequence from a corpus I control means every resource mentioned is something I can vouch for."

**Them:** "Why not scrape LinkedIn for more job coverage?" / "Why FAISS if you only have a few hundred job postings?"
— Same honest answers as v2; unchanged.

**Them:** "How would you scale this?"

**You:**
- Move job data refresh to a scheduled background job
- Cache embeddings and retrieval results, not just LLM outputs
- Add a feedback loop ("good match / bad match") and fold it into the LangSmith eval dataset over time
- Expand the RAG corpus as the roadmap feature gets used more
- Possible B2B angle: colleges/bootcamps; freemium: free basic matching, paid deeper gap-analysis reports

---

## Why This Project Still Wins

✅ Differentiated — not another RAG chatbot or code-review agent, and the RAG usage here is narrow and justified, not bolted on
✅ Real problem — job-search paralysis is universal
✅ Shows technical range — multi-agent orchestration, embeddings, RAG, LLM reasoning, basic static analysis
✅ Shows product + ethical judgment — you can explain *why* you avoided scraping, and *why* (and why not) you used LangGraph, RAG, and LangSmith, which is a stronger maturity signal than using them silently
✅ Fully free to build
✅ Deployable — HF Spaces, live demo link on your resume
✅ Defensible — every claim in the resume line and story can survive a follow-up question, including "isn't this overkill"

---

## Libraries Worth Getting Familiar With Before You Start

- `PyGithub` — GitHub API wrapper
- `langgraph` — agent orchestration, StateGraph, conditional edges
- `langsmith` — tracing and evals (works alongside LangGraph out of the box)
- `langchain-core` — model wrappers, prompt templates (only what you need, not the whole LangChain ecosystem)
- `sentence-transformers` — local embeddings
- `scikit-learn` — cosine similarity (start here, not FAISS)
- `faiss` — job-matching index and, in v3, the RAG resource-corpus index
- `sqlite3` — caching and storage
- `streamlit` — UI
- `requests` / `httpx` — API calls
- `pydantic` — keeps state and data models clean and typed
- `radon` — optional, Python-only code metrics

---

## Future Improvements (Good Answers to "What Would You Add Next?")

- User feedback loop ("good match" / "bad match"), fed back into the LangSmith eval dataset
- Hybrid retrieval for job matching: combine semantic similarity with keyword matching
- Resume/PDF upload as an alternative to GitHub — now a natural fallback branch off the confidence router
- Expand the RAG corpus and add source freshness checks (flag resources that haven't been reviewed in N months)
- Background jobs to periodically refresh postings, re-embed, and re-run LangSmith evals
- Auth so users can save and revisit past matches
- Simple analytics across recommended jobs and roadmap coverage (which skills come up as gaps most often)

---

## Honest Limitations to Include in Your README

- Free job APIs have narrower coverage than LinkedIn
- Salary data may be missing or estimated
- Matching quality depends on GitHub activity being a good skill proxy — imperfect for people without much public open-source work
- The RAG roadmap is only as good as the curated corpus — a narrow corpus means a narrow set of recommendable resources, and this needs periodic upkeep
- LLM-generated explanations can occasionally be generic; treat as a starting point, not ground truth
- Multi-repo weighting can favor quantity over quality depending on tuning
- LangGraph adds real value here (parallelism, routing, retries) but would be unjustified complexity for a truly linear pipeline — worth stating plainly rather than implying it was required
- Users without a public GitHub profile can't use the tool in its current form (see Phase 2 / future improvements)
