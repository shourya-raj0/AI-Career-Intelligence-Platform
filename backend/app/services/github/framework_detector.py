"""Framework detection service for the GitHub Intelligence layer.

Detects the frameworks, libraries, and ecosystems a developer uses by
parsing repository dependency manifests (``requirements.txt``,
``package.json``, ``pyproject.toml``, ``Cargo.toml``, ``go.mod``, etc.)
and by scanning README text for well-known technology markers.

This module is pure business logic: it performs no network I/O and never
calls an LLM. It is intentionally decoupled from PyGithub so it can be
unit-tested against raw strings.
"""

from __future__ import annotations

import json
import re
import tomllib
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import PurePosixPath

from pydantic import BaseModel, Field


class FrameworkCategory(str, Enum):
    """High-level category a detected technology belongs to."""

    BACKEND = "backend"
    FRONTEND = "frontend"
    AI_ML = "ai_ml"
    DATA = "data"
    TESTING = "testing"
    DEVOPS = "devops_cloud"
    DATABASE = "database"
    MOBILE = "mobile"
    GENERAL = "general"


class DependencyKind(str, Enum):
    """Whether a detected technology is a framework or a library."""

    FRAMEWORK = "framework"
    LIBRARY = "library"


class DependencyFile(BaseModel):
    """A parsed dependency manifest from a repository."""

    path: str
    ecosystem: str
    manifest_type: str
    dependencies: list[str] = Field(default_factory=list)


class DetectedDependency(BaseModel):
    """A single framework or library detected from a dependency file."""

    name: str
    category: FrameworkCategory
    kind: DependencyKind
    source_file: str
    confidence: float
    aliases: list[str] = Field(default_factory=list)


class FrameworkDetectionResult(BaseModel):
    """Aggregated framework detection output for a single repository."""

    ecosystem: str | None = None
    files: list[DependencyFile] = Field(default_factory=list)
    frameworks: list[DetectedDependency] = Field(default_factory=list)
    libraries: list[DetectedDependency] = Field(default_factory=list)
    readme_matches: list[DetectedDependency] = Field(default_factory=list)
    primary_frameworks: list[str] = Field(default_factory=list)

    def all_dependencies(self) -> list[DetectedDependency]:
        """Return every detected framework and library as a flat list."""
        return self.frameworks + self.libraries


@dataclass(frozen=True)
class _FrameworkEntry:
    """Static catalogue metadata for one framework or library."""

    display_name: str
    category: FrameworkCategory
    kind: DependencyKind


@dataclass(frozen=True)
class _ManifestSpec:
    """Parser specification for one manifest file type."""

    ecosystem: str
    manifest_type: str
    parser: Callable[[str], list[str]]


_CONFIDENCE_FRAMEWORK = 0.9
_CONFIDENCE_LIBRARY = 0.75
_CONFIDENCE_README = 0.5

_RAW_CATALOG: list[tuple[str, str, FrameworkCategory, DependencyKind, tuple[str, ...]]] = [
    # Python
    ("django", "Django", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ("djangorestframework",)),
    ("flask", "Flask", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ("flask-restful", "flask-sqlalchemy")),
    ("fastapi", "FastAPI", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ()),
    ("starlette", "Starlette", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ()),
    ("aiohttp", "Aiohttp", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ()),
    ("sanic", "Sanic", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ()),
    ("tornado", "Tornado", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ()),
    ("torch", "PyTorch", FrameworkCategory.AI_ML, DependencyKind.FRAMEWORK, ("pytorch", "torchvision", "torchaudio")),
    ("tensorflow", "TensorFlow", FrameworkCategory.AI_ML, DependencyKind.FRAMEWORK, ("keras",)),
    ("transformers", "Hugging Face Transformers", FrameworkCategory.AI_ML, DependencyKind.FRAMEWORK, ()),
    ("langchain", "LangChain", FrameworkCategory.AI_ML, DependencyKind.FRAMEWORK, ("langchain-core", "langchain-openai")),
    ("langgraph", "LangGraph", FrameworkCategory.AI_ML, DependencyKind.FRAMEWORK, ()),
    ("llama-index", "LlamaIndex", FrameworkCategory.AI_ML, DependencyKind.FRAMEWORK, ()),
    ("scikit-learn", "scikit-learn", FrameworkCategory.AI_ML, DependencyKind.FRAMEWORK, ("sklearn",)),
    ("xgboost", "XGBoost", FrameworkCategory.AI_ML, DependencyKind.FRAMEWORK, ()),
    ("lightgbm", "LightGBM", FrameworkCategory.AI_ML, DependencyKind.FRAMEWORK, ()),
    ("opencv-python", "OpenCV", FrameworkCategory.AI_ML, DependencyKind.FRAMEWORK, ("opencv-contrib-python",)),
    ("spacy", "spaCy", FrameworkCategory.AI_ML, DependencyKind.FRAMEWORK, ()),
    ("nltk", "NLTK", FrameworkCategory.AI_ML, DependencyKind.FRAMEWORK, ()),
    ("gensim", "Gensim", FrameworkCategory.AI_ML, DependencyKind.FRAMEWORK, ()),
    ("numpy", "NumPy", FrameworkCategory.DATA, DependencyKind.LIBRARY, ()),
    ("pandas", "pandas", FrameworkCategory.DATA, DependencyKind.LIBRARY, ()),
    ("scipy", "SciPy", FrameworkCategory.DATA, DependencyKind.LIBRARY, ()),
    ("matplotlib", "Matplotlib", FrameworkCategory.DATA, DependencyKind.LIBRARY, ()),
    ("seaborn", "seaborn", FrameworkCategory.DATA, DependencyKind.LIBRARY, ()),
    ("plotly", "Plotly", FrameworkCategory.DATA, DependencyKind.LIBRARY, ()),
    ("beautifulsoup4", "Beautiful Soup", FrameworkCategory.DATA, DependencyKind.LIBRARY, ("bs4",)),
    ("scrapy", "Scrapy", FrameworkCategory.DATA, DependencyKind.LIBRARY, ()),
    ("requests", "requests", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    ("httpx", "httpx", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    ("pydantic", "Pydantic", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    ("sqlalchemy", "SQLAlchemy", FrameworkCategory.DATABASE, DependencyKind.LIBRARY, ()),
    ("psycopg2-binary", "PostgreSQL", FrameworkCategory.DATABASE, DependencyKind.LIBRARY, ("psycopg2", "psycopg")),
    ("pymysql", "MySQL", FrameworkCategory.DATABASE, DependencyKind.LIBRARY, ()),
    ("pymongo", "MongoDB", FrameworkCategory.DATABASE, DependencyKind.LIBRARY, ("motor",)),
    ("redis", "Redis", FrameworkCategory.DATABASE, DependencyKind.LIBRARY, ()),
    ("celery", "Celery", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ()),
    ("pytest", "pytest", FrameworkCategory.TESTING, DependencyKind.FRAMEWORK, ()),
    ("mypy", "mypy", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    ("ruff", "Ruff", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    ("black", "Black", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    ("flake8", "Flake8", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    ("selenium", "Selenium", FrameworkCategory.TESTING, DependencyKind.FRAMEWORK, ()),
    ("playwright", "Playwright", FrameworkCategory.TESTING, DependencyKind.FRAMEWORK, ()),
    ("streamlit", "Streamlit", FrameworkCategory.FRONTEND, DependencyKind.FRAMEWORK, ()),
    ("gradio", "Gradio", FrameworkCategory.FRONTEND, DependencyKind.FRAMEWORK, ()),
    ("boto3", "AWS SDK", FrameworkCategory.DEVOPS, DependencyKind.LIBRARY, ()),
    ("kubernetes", "Kubernetes", FrameworkCategory.DEVOPS, DependencyKind.FRAMEWORK, ()),
    ("openai", "OpenAI", FrameworkCategory.AI_ML, DependencyKind.LIBRARY, ()),
    ("anthropic", "Anthropic", FrameworkCategory.AI_ML, DependencyKind.LIBRARY, ()),
    ("groq", "Groq", FrameworkCategory.AI_ML, DependencyKind.LIBRARY, ()),
    # JavaScript / TypeScript
    ("react", "React", FrameworkCategory.FRONTEND, DependencyKind.FRAMEWORK, ()),
    ("next", "Next.js", FrameworkCategory.FRONTEND, DependencyKind.FRAMEWORK, ()),
    ("vue", "Vue.js", FrameworkCategory.FRONTEND, DependencyKind.FRAMEWORK, ()),
    ("nuxt", "Nuxt.js", FrameworkCategory.FRONTEND, DependencyKind.FRAMEWORK, ()),
    ("svelte", "Svelte", FrameworkCategory.FRONTEND, DependencyKind.FRAMEWORK, ()),
    ("@angular/core", "Angular", FrameworkCategory.FRONTEND, DependencyKind.FRAMEWORK, ()),
    ("express", "Express", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ()),
    ("fastify", "Fastify", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ()),
    ("@nestjs/core", "NestJS", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ()),
    ("koa", "Koa", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ()),
    ("hapi", "Hapi", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ()),
    ("socket.io", "Socket.IO", FrameworkCategory.BACKEND, DependencyKind.LIBRARY, ()),
    ("graphql", "GraphQL", FrameworkCategory.BACKEND, DependencyKind.LIBRARY, ()),
    ("typescript", "TypeScript", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    ("axios", "Axios", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    ("lodash", "Lodash", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    ("zod", "Zod", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    ("rxjs", "RxJS", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    ("tailwindcss", "Tailwind CSS", FrameworkCategory.FRONTEND, DependencyKind.FRAMEWORK, ()),
    ("bootstrap", "Bootstrap", FrameworkCategory.FRONTEND, DependencyKind.LIBRARY, ()),
    ("@reduxjs/toolkit", "Redux", FrameworkCategory.FRONTEND, DependencyKind.LIBRARY, ()),
    ("react-native", "React Native", FrameworkCategory.MOBILE, DependencyKind.FRAMEWORK, ()),
    ("expo", "Expo", FrameworkCategory.MOBILE, DependencyKind.FRAMEWORK, ()),
    ("three", "Three.js", FrameworkCategory.FRONTEND, DependencyKind.LIBRARY, ()),
    ("d3", "D3.js", FrameworkCategory.FRONTEND, DependencyKind.LIBRARY, ()),
    ("webpack", "Webpack", FrameworkCategory.FRONTEND, DependencyKind.LIBRARY, ()),
    ("vite", "Vite", FrameworkCategory.FRONTEND, DependencyKind.LIBRARY, ()),
    ("esbuild", "esbuild", FrameworkCategory.FRONTEND, DependencyKind.LIBRARY, ()),
    ("rollup", "Rollup", FrameworkCategory.FRONTEND, DependencyKind.LIBRARY, ()),
    ("jest", "Jest", FrameworkCategory.TESTING, DependencyKind.FRAMEWORK, ()),
    ("vitest", "Vitest", FrameworkCategory.TESTING, DependencyKind.FRAMEWORK, ()),
    ("mocha", "Mocha", FrameworkCategory.TESTING, DependencyKind.FRAMEWORK, ()),
    ("cypress", "Cypress", FrameworkCategory.TESTING, DependencyKind.FRAMEWORK, ()),
    ("puppeteer", "Puppeteer", FrameworkCategory.TESTING, DependencyKind.FRAMEWORK, ()),
    ("eslint", "ESLint", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    ("prettier", "Prettier", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    ("jquery", "jQuery", FrameworkCategory.FRONTEND, DependencyKind.LIBRARY, ()),
    ("chart.js", "Chart.js", FrameworkCategory.FRONTEND, DependencyKind.LIBRARY, ()),
    # Java
    ("spring-boot", "Spring Boot", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ("spring-boot-starter-web",)),
    ("hibernate-core", "Hibernate", FrameworkCategory.DATABASE, DependencyKind.FRAMEWORK, ("hibernate",)),
    ("mybatis", "MyBatis", FrameworkCategory.DATABASE, DependencyKind.LIBRARY, ()),
    ("junit", "JUnit", FrameworkCategory.TESTING, DependencyKind.FRAMEWORK, ()),
    ("mockito", "Mockito", FrameworkCategory.TESTING, DependencyKind.LIBRARY, ()),
    ("lombok", "Lombok", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    ("jackson-databind", "Jackson", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    ("kafka-clients", "Apache Kafka", FrameworkCategory.DATA, DependencyKind.LIBRARY, ()),
    # Go
    ("gin", "Gin", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ("gin-gonic/gin",)),
    ("gorilla/mux", "Gorilla Mux", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ()),
    ("echo", "Echo", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ("labstack/echo",)),
    ("fiber", "Fiber", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ("gofiber/fiber",)),
    ("chi", "Chi", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ("go-chi/chi",)),
    ("google.golang.org/grpc", "gRPC", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ()),
    ("gorm", "GORM", FrameworkCategory.DATABASE, DependencyKind.LIBRARY, ("gorm.io/gorm",)),
    ("sqlx", "SQLx", FrameworkCategory.DATABASE, DependencyKind.LIBRARY, ("jmoiron/sqlx",)),
    ("pgx", "pgx", FrameworkCategory.DATABASE, DependencyKind.LIBRARY, ("jackc/pgx/v5",)),
    ("cobra", "Cobra", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ("spf13/cobra",)),
    ("viper", "Viper", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ("spf13/viper",)),
    ("testify", "Testify", FrameworkCategory.TESTING, DependencyKind.LIBRARY, ("stretchr/testify",)),
    ("zerolog", "zerolog", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ("rs/zerolog",)),
    ("terraform", "Terraform", FrameworkCategory.DEVOPS, DependencyKind.FRAMEWORK, ("hashicorp/terraform",)),
    ("prometheus", "Prometheus", FrameworkCategory.DEVOPS, DependencyKind.LIBRARY, ("prometheus/client_golang",)),
    # Rust
    ("actix-web", "Actix Web", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ()),
    ("actix", "Actix", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ()),
    ("axum", "Axum", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ()),
    ("rocket", "Rocket", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ()),
    ("warp", "Warp", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ()),
    ("tokio", "Tokio", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ()),
    ("tonic", "Tonic", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ()),
    ("serde", "Serde", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    ("serde_json", "Serde JSON", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    ("tokio-postgres", "PostgreSQL", FrameworkCategory.DATABASE, DependencyKind.LIBRARY, ("postgres",)),
    ("diesel", "Diesel", FrameworkCategory.DATABASE, DependencyKind.FRAMEWORK, ()),
    ("rusqlite", "SQLite", FrameworkCategory.DATABASE, DependencyKind.LIBRARY, ()),
    ("redis-rs", "Redis", FrameworkCategory.DATABASE, DependencyKind.LIBRARY, ()),
    ("clap", "Clap", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    ("anyhow", "Anyhow", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    ("thiserror", "thiserror", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    ("reqwest", "Reqwest", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    ("chrono", "Chrono", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    # Ruby
    ("rails", "Ruby on Rails", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ()),
    ("sinatra", "Sinatra", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ()),
    ("rspec", "RSpec", FrameworkCategory.TESTING, DependencyKind.FRAMEWORK, ()),
    ("rubocop", "RuboCop", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    ("sidekiq", "Sidekiq", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ()),
    ("nokogiri", "Nokogiri", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    ("devise", "Devise", FrameworkCategory.BACKEND, DependencyKind.LIBRARY, ()),
    # PHP
    ("laravel/framework", "Laravel", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ("laravel",)),
    ("symfony", "Symfony", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK, ()),
    ("phpunit", "PHPUnit", FrameworkCategory.TESTING, DependencyKind.FRAMEWORK, ()),
    # .NET
    ("microsoft.entityframeworkcore", "EF Core", FrameworkCategory.DATABASE, DependencyKind.FRAMEWORK, ()),
    ("dapper", "Dapper", FrameworkCategory.DATABASE, DependencyKind.LIBRARY, ()),
    ("newtonsoft.json", "Json.NET", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    ("xunit", "xUnit", FrameworkCategory.TESTING, DependencyKind.FRAMEWORK, ()),
    ("nunit", "NUnit", FrameworkCategory.TESTING, DependencyKind.FRAMEWORK, ()),
    ("moq", "Moq", FrameworkCategory.TESTING, DependencyKind.LIBRARY, ()),
    ("mstest", "MSTest", FrameworkCategory.TESTING, DependencyKind.FRAMEWORK, ()),
    ("automapper", "AutoMapper", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    ("serilog", "Serilog", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    # Dart / Flutter
    ("flutter", "Flutter", FrameworkCategory.MOBILE, DependencyKind.FRAMEWORK, ()),
    ("flutter_bloc", "flutter_bloc", FrameworkCategory.MOBILE, DependencyKind.LIBRARY, ()),
    ("riverpod", "Riverpod", FrameworkCategory.MOBILE, DependencyKind.LIBRARY, ()),
    ("get", "GetX", FrameworkCategory.MOBILE, DependencyKind.FRAMEWORK, ()),
    ("dio", "Dio", FrameworkCategory.GENERAL, DependencyKind.LIBRARY, ()),
    # Cloud / DevOps
    ("aws-cdk-lib", "AWS CDK", FrameworkCategory.DEVOPS, DependencyKind.FRAMEWORK, ("aws-cdk",)),
    ("helm", "Helm", FrameworkCategory.DEVOPS, DependencyKind.FRAMEWORK, ("helm.sh/helm/v3",)),
    ("ansible", "Ansible", FrameworkCategory.DEVOPS, DependencyKind.FRAMEWORK, ()),
    ("grafana", "Grafana", FrameworkCategory.DEVOPS, DependencyKind.FRAMEWORK, ()),
]

_CATALOG: dict[str, _FrameworkEntry] = {}
for _key, _name, _category, _kind, _aliases in _RAW_CATALOG:
    _entry = _FrameworkEntry(display_name=_name, category=_category, kind=_kind)
    _CATALOG[_key] = _entry
    for _alias in _aliases:
        _CATALOG[_alias] = _entry
del _key, _name, _category, _kind, _aliases, _entry

_PREFIX_RULES_RAW: list[tuple[str, str, FrameworkCategory, DependencyKind]] = [
    ("microsoft.entityframework", "EF Core", FrameworkCategory.DATABASE, DependencyKind.FRAMEWORK),
    ("microsoft.aspnetcore", "ASP.NET Core", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK),
    ("react-native", "React Native", FrameworkCategory.MOBILE, DependencyKind.FRAMEWORK),
    ("@nestjs/", "NestJS", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK),
    ("@angular/", "Angular", FrameworkCategory.FRONTEND, DependencyKind.FRAMEWORK),
    ("@vue/", "Vue.js", FrameworkCategory.FRONTEND, DependencyKind.FRAMEWORK),
    ("@mui/", "MUI", FrameworkCategory.FRONTEND, DependencyKind.LIBRARY),
    ("google-cloud-", "Google Cloud", FrameworkCategory.DEVOPS, DependencyKind.FRAMEWORK),
    ("tensorflow", "TensorFlow", FrameworkCategory.AI_ML, DependencyKind.FRAMEWORK),
    ("psycopg", "PostgreSQL", FrameworkCategory.DATABASE, DependencyKind.LIBRARY),
    ("spring", "Spring Boot", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK),
    ("flask-", "Flask", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK),
    ("fastapi-", "FastAPI", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK),
    ("django", "Django", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK),
    ("pydantic-", "Pydantic", FrameworkCategory.GENERAL, DependencyKind.LIBRARY),
    ("pytest-", "pytest", FrameworkCategory.TESTING, DependencyKind.FRAMEWORK),
    ("opencv", "OpenCV", FrameworkCategory.AI_ML, DependencyKind.FRAMEWORK),
    ("sqlalchemy", "SQLAlchemy", FrameworkCategory.DATABASE, DependencyKind.LIBRARY),
    ("azure-", "Azure", FrameworkCategory.DEVOPS, DependencyKind.FRAMEWORK),
    ("aws-sdk", "AWS SDK", FrameworkCategory.DEVOPS, DependencyKind.LIBRARY),
    ("aws-cdk", "AWS CDK", FrameworkCategory.DEVOPS, DependencyKind.FRAMEWORK),
    ("mysql", "MySQL", FrameworkCategory.DATABASE, DependencyKind.LIBRARY),
    ("express-", "Express", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK),
    ("next-", "Next.js", FrameworkCategory.FRONTEND, DependencyKind.FRAMEWORK),
    ("kafka", "Apache Kafka", FrameworkCategory.DATA, DependencyKind.LIBRARY),
    ("redux", "Redux", FrameworkCategory.FRONTEND, DependencyKind.LIBRARY),
    ("react", "React", FrameworkCategory.FRONTEND, DependencyKind.FRAMEWORK),
    ("vue", "Vue.js", FrameworkCategory.FRONTEND, DependencyKind.FRAMEWORK),
]
_PREFIX_RULES: dict[str, _FrameworkEntry] = {
    prefix: _FrameworkEntry(display_name=name, category=category, kind=kind)
    for prefix, name, category, kind in sorted(
        _PREFIX_RULES_RAW, key=lambda item: len(item[0]), reverse=True
    )
}

_README_MARKERS: list[tuple[str, str, FrameworkCategory, DependencyKind]] = [
    ("react native", "React Native", FrameworkCategory.MOBILE, DependencyKind.FRAMEWORK),
    ("spring boot", "Spring Boot", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK),
    ("hugging face", "Hugging Face Transformers", FrameworkCategory.AI_ML, DependencyKind.FRAMEWORK),
    ("scikit-learn", "scikit-learn", FrameworkCategory.AI_ML, DependencyKind.FRAMEWORK),
    ("next.js", "Next.js", FrameworkCategory.FRONTEND, DependencyKind.FRAMEWORK),
    ("tensorflow", "TensorFlow", FrameworkCategory.AI_ML, DependencyKind.FRAMEWORK),
    ("kubernetes", "Kubernetes", FrameworkCategory.DEVOPS, DependencyKind.FRAMEWORK),
    ("terraform", "Terraform", FrameworkCategory.DEVOPS, DependencyKind.FRAMEWORK),
    ("streamlit", "Streamlit", FrameworkCategory.FRONTEND, DependencyKind.FRAMEWORK),
    ("gradio", "Gradio", FrameworkCategory.FRONTEND, DependencyKind.FRAMEWORK),
    ("tailwind", "Tailwind CSS", FrameworkCategory.FRONTEND, DependencyKind.FRAMEWORK),
    ("graphql", "GraphQL", FrameworkCategory.BACKEND, DependencyKind.LIBRARY),
    ("postgresql", "PostgreSQL", FrameworkCategory.DATABASE, DependencyKind.LIBRARY),
    ("mongodb", "MongoDB", FrameworkCategory.DATABASE, DependencyKind.LIBRARY),
    ("redis", "Redis", FrameworkCategory.DATABASE, DependencyKind.LIBRARY),
    ("langchain", "LangChain", FrameworkCategory.AI_ML, DependencyKind.FRAMEWORK),
    ("langgraph", "LangGraph", FrameworkCategory.AI_ML, DependencyKind.FRAMEWORK),
    ("llamaindex", "LlamaIndex", FrameworkCategory.AI_ML, DependencyKind.FRAMEWORK),
    ("pytorch", "PyTorch", FrameworkCategory.AI_ML, DependencyKind.FRAMEWORK),
    ("django", "Django", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK),
    ("fastapi", "FastAPI", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK),
    ("flask", "Flask", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK),
    ("express", "Express", FrameworkCategory.BACKEND, DependencyKind.FRAMEWORK),
    ("angular", "Angular", FrameworkCategory.FRONTEND, DependencyKind.FRAMEWORK),
    ("react", "React", FrameworkCategory.FRONTEND, DependencyKind.FRAMEWORK),
    ("vue.js", "Vue.js", FrameworkCategory.FRONTEND, DependencyKind.FRAMEWORK),
    ("docker", "Docker", FrameworkCategory.DEVOPS, DependencyKind.FRAMEWORK),
    ("aws", "AWS", FrameworkCategory.DEVOPS, DependencyKind.FRAMEWORK),
    ("jest", "Jest", FrameworkCategory.TESTING, DependencyKind.FRAMEWORK),
    ("pytest", "pytest", FrameworkCategory.TESTING, DependencyKind.FRAMEWORK),
    ("cypress", "Cypress", FrameworkCategory.TESTING, DependencyKind.FRAMEWORK),
    ("flutter", "Flutter", FrameworkCategory.MOBILE, DependencyKind.FRAMEWORK),
    ("kafka", "Apache Kafka", FrameworkCategory.DATA, DependencyKind.LIBRARY),
]

_PKG_TOKEN_RE = re.compile(r"[=<>!~\[\s;]+")


def _normalize_package_name(raw: str) -> str:
    """Strip version specifiers, extras, and quoting from a dependency name."""
    token = _PKG_TOKEN_RE.split(raw.strip(), maxsplit=1)[0]
    return token.strip("'\"`").lower()


def _parse_requirements(content: str) -> list[str]:
    """Parse a pip ``requirements.txt`` file into package names."""
    names: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "-", "--")):
            continue
        if stripped.startswith("-e ") or stripped.startswith("--editable"):
            continue
        names.append(_normalize_package_name(stripped))
    return names


def _parse_pyproject(content: str) -> list[str]:
    """Parse a PEP 621 / Poetry ``pyproject.toml`` into package names."""
    try:
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError:
        return []
    names: list[str] = []
    project = data.get("project", {})
    names.extend(str(dep) for dep in (project.get("dependencies") or []))
    for extra in (project.get("optional-dependencies") or {}).values():
        names.extend(str(dep) for dep in (extra or []))
    poetry = (data.get("tool", {}).get("poetry", {}).get("dependencies") or {})
    names.extend(name for name in poetry if name != "python")
    return [_normalize_package_name(name) for name in names]


def _parse_pipfile(content: str) -> list[str]:
    """Parse a ``Pipfile`` into package names."""
    try:
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError:
        return []
    names: list[str] = []
    for section in ("packages", "dev-packages"):
        names.extend((data.get(section) or {}).keys())
    return [_normalize_package_name(name) for name in names]


def _parse_setup_py(content: str) -> list[str]:
    """Extract package names from a ``setup.py`` ``install_requires`` block."""
    match = re.search(r"install_requires\s*=\s*\[(.*?)\]", content, re.DOTALL)
    if not match:
        return []
    return [_normalize_package_name(name) for name in re.findall(r"['\"]([^'\"]+)['\"]", match.group(1))]


def _parse_package_json(content: str) -> list[str]:
    """Parse a Node.js ``package.json`` into dependency names."""
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return []
    names: list[str] = []
    for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        names.extend((data.get(key) or {}).keys())
    return [_normalize_package_name(name) for name in names]


def _parse_cargo(content: str) -> list[str]:
    """Parse a Rust ``Cargo.toml`` into crate names."""
    try:
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError:
        return []
    names: list[str] = []
    for section in ("dependencies", "dev-dependencies", "build-dependencies"):
        names.extend((data.get(section) or {}).keys())
    workspace = data.get("workspace", {}).get("dependencies") or {}
    names.extend(workspace.keys())
    return [_normalize_package_name(name) for name in names]


_GO_REQUIRE_RE = re.compile(r"^\s*([A-Za-z0-9_.\-/]+?)(?:\s+v[\w.\-+]+)?\s*$")


def _parse_go_mod(content: str) -> list[str]:
    """Parse a Go ``go.mod`` into module dependency paths."""
    names: list[str] = []
    in_block = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("require ("):
            in_block = True
            continue
        if in_block:
            if stripped == ")":
                in_block = False
                continue
            match = _GO_REQUIRE_RE.match(stripped)
            if match:
                names.append(match.group(1))
            continue
        if stripped.startswith("require "):
            rest = stripped[len("require "):].strip()
            if rest:
                names.append(rest.split()[0])
    return names


def _parse_pom(content: str) -> list[str]:
    """Extract artifact IDs from a Maven ``pom.xml``."""
    return re.findall(r"<artifactId>([^<]+)</artifactId>", content)


_GRADLE_DEPS_RE = re.compile(
    r"(?:implementation|api|compile|runtimeOnly|testImplementation|testCompileOnly)"
    r"\s+['\"]([^'\"]+)['\"]"
)


def _parse_gradle(content: str) -> list[str]:
    """Extract dependencies from a Gradle ``build.gradle`` file."""
    names: list[str] = []
    for raw in _GRADLE_DEPS_RE.findall(content):
        parts = raw.split(":")
        names.append(parts[1] if len(parts) >= 2 else parts[0])
    return [_normalize_package_name(name) for name in names]


def _parse_gemfile(content: str) -> list[str]:
    """Extract gem names from a Ruby ``Gemfile``."""
    return re.findall(r"""gem\s+['"]([^'"]+)['"]""", content)


def _parse_composer(content: str) -> list[str]:
    """Parse a PHP ``composer.json`` into package names."""
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return []
    names: list[str] = []
    for key in ("require", "require-dev"):
        names.extend((data.get(key) or {}).keys())
    return [_normalize_package_name(name) for name in names]


def _parse_pubspec(content: str) -> list[str]:
    """Extract dependencies from a Dart ``pubspec.yaml``."""
    names: list[str] = []
    started = False
    for line in content.splitlines():
        if not started:
            if line.strip() == "dependencies:":
                started = True
            continue
        if line and not line[0].isspace():
            break
        match = re.match(r"^\s+([A-Za-z_][A-Za-z0-9_]*):", line)
        if match:
            names.append(match.group(1))
    return names


def _parse_packages_config(content: str) -> list[str]:
    """Extract package IDs from a .NET ``packages.config`` file."""
    return re.findall(r'<package\s+id="([^"]+)"', content)


def _parse_csproj(content: str) -> list[str]:
    """Extract package references from a .NET ``*.csproj`` file."""
    return re.findall(r'<PackageReference\s+Include="([^"]+)"', content)


def _parse_mix_exs(content: str) -> list[str]:
    """Extract dependencies from an Elixir ``mix.exs`` file."""
    return re.findall(r"\{:([\w]+),", content)


_MANIFEST_SPECS: dict[str, _ManifestSpec] = {
    "requirements.txt": _ManifestSpec("python", "pip", _parse_requirements),
    "pyproject.toml": _ManifestSpec("python", "poetry_pip", _parse_pyproject),
    "Pipfile": _ManifestSpec("python", "pipenv", _parse_pipfile),
    "setup.py": _ManifestSpec("python", "setuptools", _parse_setup_py),
    "package.json": _ManifestSpec("node", "npm", _parse_package_json),
    "Cargo.toml": _ManifestSpec("rust", "cargo", _parse_cargo),
    "go.mod": _ManifestSpec("go", "go_modules", _parse_go_mod),
    "pom.xml": _ManifestSpec("java", "maven", _parse_pom),
    "build.gradle": _ManifestSpec("java", "gradle", _parse_gradle),
    "build.gradle.kts": _ManifestSpec("java", "gradle_kts", _parse_gradle),
    "Gemfile": _ManifestSpec("ruby", "bundler", _parse_gemfile),
    "composer.json": _ManifestSpec("php", "composer", _parse_composer),
    "pubspec.yaml": _ManifestSpec("dart", "pub", _parse_pubspec),
    "packages.config": _ManifestSpec("dotnet", "nuget", _parse_packages_config),
    "mix.exs": _ManifestSpec("elixir", "hex", _parse_mix_exs),
}


def _dedupe(values: Iterable[str]) -> list[str]:
    """Deduplicate an iterable while preserving first-seen order."""
    return list(dict.fromkeys(values))


class FrameworkDetector:
    """Detects frameworks and libraries from dependency manifests and READMEs."""

    def is_manifest(self, path: str) -> bool:
        """Return whether ``path`` points to a supported dependency manifest."""
        basename = PurePosixPath(path).name
        return basename in _MANIFEST_SPECS or basename.endswith(".csproj")

    def parse_manifest(self, path: str, content: str) -> DependencyFile | None:
        """Parse ``content`` into a :class:`DependencyFile`.

        Returns ``None`` when the path is not a supported manifest type.
        Unparseable manifests yield a file with an empty dependency list
        rather than raising, so one broken file never fails the whole scan.
        """
        basename = PurePosixPath(path).name
        if basename.endswith(".csproj"):
            spec = _ManifestSpec("dotnet", "csproj", _parse_csproj)
        else:
            spec = _MANIFEST_SPECS.get(basename)
            if spec is None:
                return None
        try:
            dependencies = _dedupe(spec.parser(content))
        except Exception:
            dependencies = []
        return DependencyFile(
            path=path,
            ecosystem=spec.ecosystem,
            manifest_type=spec.manifest_type,
            dependencies=dependencies,
        )

    def _match(self, dependency: str) -> _FrameworkEntry | None:
        """Resolve a dependency name against the static catalogue."""
        candidates = [dependency]
        if "/" in dependency:
            candidates.append(dependency.split("/")[-1])
        for candidate in candidates:
            entry = _CATALOG.get(candidate)
            if entry is not None:
                return entry
        for prefix, entry in _PREFIX_RULES.items():
            for candidate in candidates:
                if candidate.startswith(prefix):
                    return entry
        return None

    def detect(self, files: Iterable[DependencyFile]) -> FrameworkDetectionResult:
        """Detect frameworks and libraries from a set of parsed manifests."""
        frameworks: list[DetectedDependency] = []
        libraries: list[DetectedDependency] = []
        ecosystem_counts: dict[str, int] = {}

        for dependency_file in files:
            ecosystem_counts[dependency_file.ecosystem] = (
                ecosystem_counts.get(dependency_file.ecosystem, 0) + 1
            )
            for raw in dependency_file.dependencies:
                entry = self._match(raw)
                if entry is None:
                    continue
                confidence = (
                    _CONFIDENCE_FRAMEWORK
                    if entry.kind is DependencyKind.FRAMEWORK
                    else _CONFIDENCE_LIBRARY
                )
                detected = DetectedDependency(
                    name=entry.display_name,
                    category=entry.category,
                    kind=entry.kind,
                    source_file=dependency_file.path,
                    confidence=confidence,
                    aliases=[raw],
                )
                if entry.kind is DependencyKind.FRAMEWORK:
                    frameworks.append(detected)
                else:
                    libraries.append(detected)

        primary_ecosystem = max(ecosystem_counts, key=ecosystem_counts.get) if ecosystem_counts else None
        frameworks = self._dedupe_detections(frameworks)
        libraries = self._dedupe_detections(libraries)
        primary_frameworks = [
            item.name
            for item in sorted(
                frameworks, key=lambda item: frameworks.count(item), reverse=True
            )[:5]
        ]
        return FrameworkDetectionResult(
            ecosystem=primary_ecosystem,
            files=list(files),
            frameworks=frameworks,
            libraries=libraries,
            primary_frameworks=_dedupe(primary_frameworks),
        )

    def detect_from_readme(self, readme_text: str) -> list[DetectedDependency]:
        """Detect technologies mentioned in a repository README.

        README matches are weaker signals than manifest declarations, so
        they carry a lower confidence and are never treated as primary.
        """
        lowered = readme_text.lower()
        matches: list[DetectedDependency] = []
        for marker, name, category, kind in _README_MARKERS:
            if marker in lowered:
                matches.append(
                    DetectedDependency(
                        name=name,
                        category=category,
                        kind=kind,
                        source_file="README.md",
                        confidence=_CONFIDENCE_README,
                        aliases=[marker],
                    )
                )
        return self._dedupe_detections(matches)

    @staticmethod
    def _dedupe_detections(items: list[DetectedDependency]) -> list[DetectedDependency]:
        """Merge duplicate detections of the same technology in one file."""
        merged: dict[tuple[str, str], DetectedDependency] = {}
        for item in items:
            key = (item.name, item.source_file)
            existing = merged.get(key)
            if existing is None:
                merged[key] = item
            else:
                existing.aliases.extend(alias for alias in item.aliases if alias not in existing.aliases)
        return list(merged.values())
