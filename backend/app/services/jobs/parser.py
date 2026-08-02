"""Required-skill extraction from job postings.

Deterministic, catalog-based extraction: the job title and description are
scanned for known skill phrases (word-boundary matched). A skill mentioned in
the title carries higher confidence than one only in the description. This is
pure business logic with no network or LLM dependency.
"""

from __future__ import annotations

import re
from enum import Enum

from app.services.jobs.models import RequiredSkill


class SkillCategory(str, Enum):
    """High-level category a required skill belongs to."""

    LANGUAGE = "language"
    FRAMEWORK = "framework"
    AI_ML = "ai_ml"
    CLOUD_DEVOPS = "cloud_devops"
    DATABASE = "database"
    TESTING = "testing"
    TOOLS = "tools"
    CONCEPTS = "concepts"


_RAW_CATALOG: list[tuple[tuple[str, ...], str, SkillCategory]] = [
    # Languages
    (("python",), "Python", SkillCategory.LANGUAGE),
    (("javascript",), "JavaScript", SkillCategory.LANGUAGE),
    (("typescript",), "TypeScript", SkillCategory.LANGUAGE),
    (("java",), "Java", SkillCategory.LANGUAGE),
    (("golang", "go language", "go programming"), "Go", SkillCategory.LANGUAGE),
    (("rust",), "Rust", SkillCategory.LANGUAGE),
    (("c++",), "C++", SkillCategory.LANGUAGE),
    (("c#",), "C#", SkillCategory.LANGUAGE),
    (("ruby",), "Ruby", SkillCategory.LANGUAGE),
    (("php",), "PHP", SkillCategory.LANGUAGE),
    (("swift",), "Swift", SkillCategory.LANGUAGE),
    (("kotlin",), "Kotlin", SkillCategory.LANGUAGE),
    (("scala",), "Scala", SkillCategory.LANGUAGE),
    (("dart",), "Dart", SkillCategory.LANGUAGE),
    (("bash", "shell scripting"), "Bash/Shell", SkillCategory.LANGUAGE),
    (("html",), "HTML", SkillCategory.LANGUAGE),
    (("css",), "CSS", SkillCategory.LANGUAGE),
    (("elixir",), "Elixir", SkillCategory.LANGUAGE),
    (("solidity",), "Solidity", SkillCategory.LANGUAGE),
    # Frameworks
    (("react",), "React", SkillCategory.FRAMEWORK),
    (("react native",), "React Native", SkillCategory.FRAMEWORK),
    (("angular",), "Angular", SkillCategory.FRAMEWORK),
    (("vue",), "Vue.js", SkillCategory.FRAMEWORK),
    (("svelte",), "Svelte", SkillCategory.FRAMEWORK),
    (("next.js", "nextjs"), "Next.js", SkillCategory.FRAMEWORK),
    (("nuxt",), "Nuxt.js", SkillCategory.FRAMEWORK),
    (("express",), "Express", SkillCategory.FRAMEWORK),
    (("fastify",), "Fastify", SkillCategory.FRAMEWORK),
    (("nestjs", "nest.js"), "NestJS", SkillCategory.FRAMEWORK),
    (("node.js", "nodejs"), "Node.js", SkillCategory.FRAMEWORK),
    (("django",), "Django", SkillCategory.FRAMEWORK),
    (("flask",), "Flask", SkillCategory.FRAMEWORK),
    (("fastapi",), "FastAPI", SkillCategory.FRAMEWORK),
    (("spring boot",), "Spring Boot", SkillCategory.FRAMEWORK),
    (("ruby on rails",), "Ruby on Rails", SkillCategory.FRAMEWORK),
    (("laravel",), "Laravel", SkillCategory.FRAMEWORK),
    (("asp.net",), "ASP.NET", SkillCategory.FRAMEWORK),
    (("flutter",), "Flutter", SkillCategory.FRAMEWORK),
    (("swiftui",), "SwiftUI", SkillCategory.FRAMEWORK),
    (("jetpack compose",), "Jetpack Compose", SkillCategory.FRAMEWORK),
    (("apache spark", "spark"), "Apache Spark", SkillCategory.FRAMEWORK),
    (("apache kafka", "kafka"), "Apache Kafka", SkillCategory.FRAMEWORK),
    (("grpc",), "gRPC", SkillCategory.FRAMEWORK),
    # AI / ML
    (("machine learning",), "Machine Learning", SkillCategory.AI_ML),
    (("deep learning",), "Deep Learning", SkillCategory.AI_ML),
    (("nlp", "natural language processing"), "NLP", SkillCategory.AI_ML),
    (("computer vision",), "Computer Vision", SkillCategory.AI_ML),
    (("tensorflow",), "TensorFlow", SkillCategory.AI_ML),
    (("pytorch",), "PyTorch", SkillCategory.AI_ML),
    (("keras",), "Keras", SkillCategory.AI_ML),
    (("scikit-learn", "sklearn"), "scikit-learn", SkillCategory.AI_ML),
    (("hugging face",), "Hugging Face", SkillCategory.AI_ML),
    (("transformers",), "Transformers", SkillCategory.AI_ML),
    (("langchain",), "LangChain", SkillCategory.AI_ML),
    (("langgraph",), "LangGraph", SkillCategory.AI_ML),
    (("llm", "large language model"), "LLM", SkillCategory.AI_ML),
    (("generative ai", "genai"), "Generative AI", SkillCategory.AI_ML),
    (("rag", "retrieval-augmented generation"), "RAG", SkillCategory.AI_ML),
    (("mlops",), "MLOps", SkillCategory.AI_ML),
    (("opencv",), "OpenCV", SkillCategory.AI_ML),
    (("recommendation system",), "Recommendation Systems", SkillCategory.AI_ML),
    # Cloud / DevOps
    (("aws", "amazon web services"), "AWS", SkillCategory.CLOUD_DEVOPS),
    (("azure",), "Azure", SkillCategory.CLOUD_DEVOPS),
    (("gcp", "google cloud"), "Google Cloud", SkillCategory.CLOUD_DEVOPS),
    (("docker",), "Docker", SkillCategory.CLOUD_DEVOPS),
    (("kubernetes", "k8s"), "Kubernetes", SkillCategory.CLOUD_DEVOPS),
    (("helm",), "Helm", SkillCategory.CLOUD_DEVOPS),
    (("terraform",), "Terraform", SkillCategory.CLOUD_DEVOPS),
    (("ansible",), "Ansible", SkillCategory.CLOUD_DEVOPS),
    (("ci/cd",), "CI/CD", SkillCategory.CLOUD_DEVOPS),
    (("github actions",), "GitHub Actions", SkillCategory.CLOUD_DEVOPS),
    (("gitlab ci",), "GitLab CI", SkillCategory.CLOUD_DEVOPS),
    (("jenkins",), "Jenkins", SkillCategory.CLOUD_DEVOPS),
    (("serverless",), "Serverless", SkillCategory.CLOUD_DEVOPS),
    (("aws lambda", "lambda"), "AWS Lambda", SkillCategory.CLOUD_DEVOPS),
    (("prometheus",), "Prometheus", SkillCategory.CLOUD_DEVOPS),
    (("grafana",), "Grafana", SkillCategory.CLOUD_DEVOPS),
    (("cloudformation",), "CloudFormation", SkillCategory.CLOUD_DEVOPS),
    # Database
    (("sql",), "SQL", SkillCategory.DATABASE),
    (("postgresql", "postgres"), "PostgreSQL", SkillCategory.DATABASE),
    (("mysql",), "MySQL", SkillCategory.DATABASE),
    (("mongodb",), "MongoDB", SkillCategory.DATABASE),
    (("redis",), "Redis", SkillCategory.DATABASE),
    (("sqlite",), "SQLite", SkillCategory.DATABASE),
    (("elasticsearch",), "Elasticsearch", SkillCategory.DATABASE),
    (("dynamodb",), "DynamoDB", SkillCategory.DATABASE),
    (("cassandra",), "Cassandra", SkillCategory.DATABASE),
    (("snowflake",), "Snowflake", SkillCategory.DATABASE),
    (("bigquery",), "BigQuery", SkillCategory.DATABASE),
    (("redshift",), "Redshift", SkillCategory.DATABASE),
    (("nosql",), "NoSQL", SkillCategory.DATABASE),
    (("sqlalchemy",), "SQLAlchemy", SkillCategory.DATABASE),
    (("prisma",), "Prisma", SkillCategory.DATABASE),
    (("hibernate",), "Hibernate", SkillCategory.DATABASE),
    # Testing
    (("jest",), "Jest", SkillCategory.TESTING),
    (("pytest",), "pytest", SkillCategory.TESTING),
    (("cypress",), "Cypress", SkillCategory.TESTING),
    (("playwright",), "Playwright", SkillCategory.TESTING),
    (("selenium",), "Selenium", SkillCategory.TESTING),
    (("junit",), "JUnit", SkillCategory.TESTING),
    (("mocha",), "Mocha", SkillCategory.TESTING),
    (("rspec",), "RSpec", SkillCategory.TESTING),
    (("vitest",), "Vitest", SkillCategory.TESTING),
    (("test-driven development", "tdd"), "TDD", SkillCategory.TESTING),
    (("unit testing", "unit test"), "Unit Testing", SkillCategory.TESTING),
    (("integration testing", "integration test"), "Integration Testing", SkillCategory.TESTING),
    # Tools
    (("git",), "Git", SkillCategory.TOOLS),
    (("github",), "GitHub", SkillCategory.TOOLS),
    (("gitlab",), "GitLab", SkillCategory.TOOLS),
    (("jira",), "Jira", SkillCategory.TOOLS),
    (("confluence",), "Confluence", SkillCategory.TOOLS),
    (("postman",), "Postman", SkillCategory.TOOLS),
    (("figma",), "Figma", SkillCategory.TOOLS),
    (("vs code", "vscode"), "VS Code", SkillCategory.TOOLS),
    (("webpack",), "Webpack", SkillCategory.TOOLS),
    (("vite",), "Vite", SkillCategory.TOOLS),
    (("npm",), "npm", SkillCategory.TOOLS),
    (("yarn",), "Yarn", SkillCategory.TOOLS),
    (("pnpm",), "pnpm", SkillCategory.TOOLS),
    (("poetry",), "Poetry", SkillCategory.TOOLS),
    (("maven",), "Maven", SkillCategory.TOOLS),
    (("gradle",), "Gradle", SkillCategory.TOOLS),
    (("pandas",), "pandas", SkillCategory.TOOLS),
    (("numpy",), "NumPy", SkillCategory.TOOLS),
    # Concepts
    (("microservices",), "Microservices", SkillCategory.CONCEPTS),
    (("rest api", "restful"), "REST API", SkillCategory.CONCEPTS),
    (("graphql",), "GraphQL", SkillCategory.CONCEPTS),
    (("agile",), "Agile", SkillCategory.CONCEPTS),
    (("scrum",), "Scrum", SkillCategory.CONCEPTS),
    (("kanban",), "Kanban", SkillCategory.CONCEPTS),
    (("etl",), "ETL", SkillCategory.CONCEPTS),
    (("data pipeline",), "Data Pipelines", SkillCategory.CONCEPTS),
    (("data engineering",), "Data Engineering", SkillCategory.CONCEPTS),
    (("big data",), "Big Data", SkillCategory.CONCEPTS),
    (("distributed systems",), "Distributed Systems", SkillCategory.CONCEPTS),
    (("system design",), "System Design", SkillCategory.CONCEPTS),
    (("object-oriented programming", "oop"), "OOP", SkillCategory.CONCEPTS),
    (("data structures and algorithms", "dsa"), "Data Structures & Algorithms", SkillCategory.CONCEPTS),
    (("event-driven",), "Event-Driven", SkillCategory.CONCEPTS),
    (("monorepo",), "Monorepo", SkillCategory.CONCEPTS),
    (("devsecops",), "DevSecOps", SkillCategory.CONCEPTS),
]


def _build_matchers() -> list[tuple[list[re.Pattern[str]], str, SkillCategory]]:
    matchers: list[tuple[list[re.Pattern[str]], str, SkillCategory]] = []
    for phrases, name, category in _RAW_CATALOG:
        patterns = [
            re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)
            for phrase in phrases
        ]
        matchers.append((patterns, name, category))
    return matchers


class SkillParser:
    """Extracts required skills from a job title and description."""

    def __init__(self) -> None:
        self._matchers = _build_matchers()

    def extract_skills(self, title: str, description: str) -> list[RequiredSkill]:
        """Return the required skills detected in ``title`` and ``description``."""
        title_text = title.lower()
        description_text = description.lower()
        found: dict[str, RequiredSkill] = {}

        for patterns, name, category in self._matchers:
            in_title = any(pattern.search(title_text) for pattern in patterns)
            in_description = any(pattern.search(description_text) for pattern in patterns)
            if in_title and in_description:
                confidence = 0.95
            elif in_title:
                confidence = 0.9
            elif in_description:
                confidence = 0.7
            else:
                continue
            found[name] = RequiredSkill(name=name, category=category.value, confidence=confidence)

        return sorted(found.values(), key=lambda skill: (-skill.confidence, skill.name))
