"""Portfolio project suggestions that close skill gaps.

Maps every missing skill to one or more practical project ideas grounded in
retrieved learning resources, so the developer builds real evidence rather than
just adding a skill to a list. Skills without a curated template fall back to a
generic hands-on project scaffold.
"""

from __future__ import annotations

from app.services.recommendations.models import PortfolioProject
from app.services.recommendations.retriever import ResourceRetriever

_RESOURCES_PER_PROJECT = 2
_MAX_PROJECTS = 8

_ESTIMATED_WEEKS = {"Easy": 1, "Medium": 2, "Hard": 3}

_PROJECT_TEMPLATES: dict[str, tuple[str, str]] = {
    "fastapi": (
        "FastAPI microservice with Docker",
        "Build a REST microservice with FastAPI and Pydantic, add pytest coverage, then containerize it with Docker and a Compose file.",
    ),
    "docker": (
        "Containerize a web application",
        "Dockerize an existing app with a multi-stage Dockerfile, add docker-compose with a database service, and document the setup.",
    ),
    "kubernetes": (
        "Deploy an app to Kubernetes",
        "Write a Kubernetes deployment, service, and horizontal autoscaler for a small app, then roll it out with kubectl and explain each manifest.",
    ),
    "postgresql": (
        "Data-driven app with PostgreSQL",
        "Build an application backed by PostgreSQL with proper schema design, indexes, and migrations.",
    ),
    "sql": (
        "Analytics dashboard with SQL",
        "Build a small analytics dashboard that queries a SQL dataset with joins, aggregations, and window functions.",
    ),
    "mongodb": (
        "Document-store backend with MongoDB",
        "Create a backend that models data with MongoDB documents and indexes, exposing CRUD over a REST API.",
    ),
    "redis": (
        "Cache layer with Redis",
        "Add a Redis cache layer to an API, implement cache invalidation, and benchmark the speedup.",
    ),
    "machine learning": (
        "End-to-end ML model pipeline",
        "Train a scikit-learn model, build a training/eval pipeline, and serve predictions through a small API.",
    ),
    "deep learning": (
        "Deep learning from scratch project",
        "Train a neural network on a public dataset with PyTorch or TensorFlow, visualize results, and document experiments.",
    ),
    "pytorch": (
        "PyTorch model training project",
        "Implement training and evaluation loops in PyTorch for a small vision or text dataset with clear metrics.",
    ),
    "nlp": (
        "NLP text analysis tool",
        "Build a tool that applies NLP techniques (classification or extraction) to a real text corpus with a clean CLI or API.",
    ),
    "llm": (
        "LLM-powered assistant",
        "Build an LLM assistant for a focused domain with prompt templates, context retrieval, and evaluation of outputs.",
    ),
    "langchain": (
        "Retrieval app with LangChain",
        "Assemble a document Q&A app with LangChain: chunking, embeddings, a vector store, and a chat interface.",
    ),
    "rag": (
        "RAG chatbot with citations",
        "Build a retrieval-augmented generation chatbot that answers questions over your own documents and cites sources.",
    ),
    "aws": (
        "Serverless app on AWS",
        "Deploy a serverless API on AWS with Lambda, API Gateway, and DynamoDB, including IAM and CI/CD.",
    ),
    "azure": (
        "Cloud app on Azure",
        "Deploy a web app on Azure with a database and monitoring, using infrastructure as code.",
    ),
    "google cloud": (
        "Data pipeline on Google Cloud",
        "Build a small data pipeline on Google Cloud using Cloud Storage, BigQuery, and scheduled jobs.",
    ),
    "terraform": (
        "Infrastructure as code with Terraform",
        "Provision a cloud environment with Terraform modules and state management, documented with a README.",
    ),
    "ci/cd": (
        "CI/CD pipeline for a project",
        "Add a GitHub Actions pipeline that runs lint, tests, and a build, then deploys on merge.",
    ),
    "react": (
        "Interactive React dashboard",
        "Build a client-side dashboard in React with state management, data fetching, and reusable components.",
    ),
    "typescript": (
        "Type-safe TypeScript app",
        "Build a TypeScript application with strict typing, interfaces, and generics shared across client and server.",
    ),
    "node.js": (
        "Node.js backend with realtime updates",
        "Build a Node.js backend with REST endpoints, WebSockets, and persistent storage.",
    ),
    "graphql": (
        "GraphQL API layer",
        "Build a GraphQL API with resolvers, schema types, and query batching in front of a data store.",
    ),
    "pytest": (
        "Tested library with pytest",
        "Write a small Python library with thorough pytest suites: fixtures, parametrization, and coverage reports.",
    ),
    "jest": (
        "Tested frontend with Jest",
        "Add Jest unit and integration tests to a frontend project, including mocking and snapshot tests.",
    ),
    "microservices": (
        "Two-service microservice demo",
        "Build two small services that communicate over a message queue or REST, with docker-compose orchestration.",
    ),
    "system design": (
        "Design and build a scaled system",
        "Design a high-level system (rate limiter, URL shortener) and implement a working subset with tests.",
    ),
}


class ProjectSuggestionEngine:
    """Generates grounded portfolio project ideas for gap skills."""

    def __init__(
        self,
        retriever: ResourceRetriever | None = None,
        max_projects: int = _MAX_PROJECTS,
    ) -> None:
        self._retriever = retriever or ResourceRetriever()
        self._max_projects = max_projects

    def suggest(self, skill_gap) -> list[PortfolioProject]:
        """Return portfolio project suggestions for the gap skills."""
        projects: list[PortfolioProject] = []
        for gap in skill_gap.missing_skills[: self._max_projects]:
            title, summary = self._template_for(gap.name)
            resources = self._retriever.retrieve(gap.name, top_k=_RESOURCES_PER_PROJECT)
            estimated_weeks = _ESTIMATED_WEEKS.get(gap.difficulty, 2)
            rationale = (
                f"Builds verifiable evidence for {gap.name}, which is required by "
                f"{gap.demand_count} of your top matched jobs."
            )
            projects.append(
                PortfolioProject(
                    title=title,
                    summary=summary,
                    skills=[gap.name],
                    difficulty=gap.difficulty,
                    estimated_weeks=estimated_weeks,
                    resources=resources,
                    rationale=rationale,
                )
            )
        return projects

    @staticmethod
    def _template_for(skill_name: str) -> tuple[str, str]:
        template = _PROJECT_TEMPLATES.get(skill_name.lower())
        if template is not None:
            return template
        return (
            f"Hands-on {skill_name} project",
            f"Build a small application that uses {skill_name} end-to-end: define a minimal scope, "
            "implement it, add tests, and document the result to add verifiable evidence to your GitHub profile.",
        )
