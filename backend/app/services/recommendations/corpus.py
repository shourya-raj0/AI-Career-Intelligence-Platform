"""Learning resource corpus for grounded recommendations.

A curated set of free and well-known learning resources, each tagged with the
skills it teaches. The corpus is embedded and searched by
:class:`app.services.recommendations.retriever.ResourceRetriever` to ground
roadmap steps and portfolio projects. This is the MVP seed corpus; it can be
replaced by a fuller RAG pipeline later.
"""

from __future__ import annotations

from app.services.recommendations.models import LearningResource

_RAW_CORPUS: list[dict] = [
    # Languages
    {"id": "py-tutorial", "title": "The Python Tutorial", "url": "https://docs.python.org/3/tutorial/", "source": "Official Docs", "type": "docs", "skills": ["python"], "diff": "Easy", "desc": "Official Python tutorial covering core language features, data structures, and modules."},
    {"id": "js-mdn", "title": "JavaScript Guide", "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide", "source": "MDN", "type": "docs", "skills": ["javascript"], "diff": "Easy", "desc": "Comprehensive JavaScript language guide from MDN."},
    {"id": "ts-docs", "title": "TypeScript Handbook", "url": "https://www.typescriptlang.org/docs/handbook/intro.html", "source": "Official Docs", "type": "docs", "skills": ["typescript"], "diff": "Easy", "desc": "The TypeScript handbook: types, classes, and modern tooling."},
    {"id": "java-udemy", "title": "Java Programming Masterclass", "url": "https://www.udemy.com/course/java-the-complete-java-developer-course/", "source": "Udemy", "type": "course", "skills": ["java"], "diff": "Medium", "desc": "Complete Java course from basics to advanced features and OOP."},
    {"id": "go-tour", "title": "A Tour of Go", "url": "https://go.dev/tour/", "source": "Official Docs", "type": "course", "skills": ["go"], "diff": "Easy", "desc": "Interactive introduction to the Go programming language."},
    {"id": "rust-book", "title": "The Rust Programming Language", "url": "https://doc.rust-lang.org/book/", "source": "Official Docs", "type": "docs", "skills": ["rust"], "diff": "Hard", "desc": "The official Rust book covering ownership, concurrency, and tooling."},
    # Frontend frameworks
    {"id": "react-learn", "title": "React Documentation (Learn)", "url": "https://react.dev/learn", "source": "Official Docs", "type": "docs", "skills": ["react"], "diff": "Medium", "desc": "React's official interactive learning path from components to hooks."},
    {"id": "vue-guide", "title": "Vue.js Guide", "url": "https://vuejs.org/guide/introduction", "source": "Official Docs", "type": "docs", "skills": ["vue"], "diff": "Medium", "desc": "The Vue.js core guide covering reactivity, components, and tooling."},
    {"id": "angular-tutorial", "title": "Angular Tutorial (First App)", "url": "https://angular.dev/tutorials/first-app", "source": "Official Docs", "type": "tutorial", "skills": ["angular"], "diff": "Medium", "desc": "Build your first Angular application with the official tutorial."},
    {"id": "nextjs-learn", "title": "Next.js Learn", "url": "https://nextjs.org/learn", "source": "Official Docs", "type": "tutorial", "skills": ["next.js"], "diff": "Medium", "desc": "Learn Next.js by building a full-stack app with React."},
    {"id": "node-learn", "title": "Node.js Learn", "url": "https://nodejs.org/en/learn", "source": "Official Docs", "type": "docs", "skills": ["node.js"], "diff": "Medium", "desc": "Official Node.js learning resources: modules, npm, and async patterns."},
    {"id": "express-guide", "title": "Express Starter Guide", "url": "https://expressjs.com/en/starter/installing.html", "source": "Official Docs", "type": "docs", "skills": ["express"], "diff": "Easy", "desc": "Get started with Express routing, middleware, and error handling."},
    # Backend / Python web
    {"id": "fastapi-tutorial", "title": "FastAPI Tutorial", "url": "https://fastapi.tiangolo.com/tutorial/", "source": "Official Docs", "type": "tutorial", "skills": ["fastapi"], "diff": "Easy", "desc": "FastAPI official tutorial: path ops, Pydantic models, and dependency injection."},
    {"id": "django-intro", "title": "Django Tutorial (Polls App)", "url": "https://docs.djangoproject.com/en/stable/intro/", "source": "Official Docs", "type": "tutorial", "skills": ["django"], "diff": "Medium", "desc": "Build a complete web app with Django: models, views, templates, and forms."},
    {"id": "flask-tutorial", "title": "Flask Tutorial", "url": "https://flask.palletsprojects.com/en/stable/tutorial/", "source": "Official Docs", "type": "tutorial", "skills": ["flask"], "diff": "Easy", "desc": "The Flask official tutorial building a blog application step by step."},
    {"id": "spring-guides", "title": "Spring Boot Getting Started", "url": "https://spring.io/guides/gs/spring-boot", "source": "Official Docs", "type": "guide", "skills": ["spring boot"], "diff": "Medium", "desc": "Build a production-grade Spring Boot application with the official guide."},
    # DevOps / Cloud
    {"id": "docker-started", "title": "Docker Get Started", "url": "https://docs.docker.com/get-started/", "source": "Official Docs", "type": "tutorial", "skills": ["docker"], "diff": "Easy", "desc": "Learn containers, images, volumes, and compose with Docker's official guide."},
    {"id": "k8s-tutorials", "title": "Kubernetes Tutorials", "url": "https://kubernetes.io/docs/tutorials/", "source": "Official Docs", "type": "tutorial", "skills": ["kubernetes"], "diff": "Hard", "desc": "Kubernetes official tutorials: deployments, services, and scaling."},
    {"id": "terraform-tutorials", "title": "Terraform Tutorials", "url": "https://developer.hashicorp.com/terraform/tutorials", "source": "HashiCorp", "type": "tutorial", "skills": ["terraform"], "diff": "Hard", "desc": "Infrastructure as code with Terraform, from basic to advanced workflows."},
    {"id": "aws-hands-on", "title": "AWS Hands-On Tutorials", "url": "https://aws.amazon.com/getting-started/hands-on/", "source": "AWS", "type": "tutorial", "skills": ["aws"], "diff": "Hard", "desc": "Step-by-step AWS tutorials for compute, storage, and serverless."},
    {"id": "azure-learn", "title": "Azure Learning Paths", "url": "https://learn.microsoft.com/en-us/training/azure/", "source": "Microsoft Learn", "type": "course", "skills": ["azure"], "diff": "Hard", "desc": "Microsoft Learn paths covering Azure fundamentals and services."},
    {"id": "gcp-training", "title": "Google Cloud Training", "url": "https://cloud.google.com/training", "source": "Google Cloud", "type": "course", "skills": ["google cloud"], "diff": "Hard", "desc": "Google Cloud courses and labs across core cloud services."},
    {"id": "gha-docs", "title": "GitHub Actions Documentation", "url": "https://docs.github.com/en/actions", "source": "GitHub Docs", "type": "docs", "skills": ["github actions", "ci/cd"], "diff": "Medium", "desc": "Automate CI/CD with GitHub Actions workflows and runners."},
    {"id": "git-book", "title": "Pro Git Book", "url": "https://git-scm.com/book/en/v2", "source": "Git", "type": "docs", "skills": ["git"], "diff": "Easy", "desc": "The complete Pro Git book: branching, rebasing, and collaboration."},
    # Databases
    {"id": "sql-tutorial", "title": "SQL Tutorial", "url": "https://www.w3schools.com/sql/", "source": "W3Schools", "type": "tutorial", "skills": ["sql"], "diff": "Easy", "desc": "Interactive SQL tutorial covering queries, joins, and aggregation."},
    {"id": "pg-docs", "title": "PostgreSQL Documentation", "url": "https://www.postgresql.org/docs/", "source": "Official Docs", "type": "docs", "skills": ["postgresql"], "diff": "Medium", "desc": "PostgreSQL official documentation on data types, queries, and tuning."},
    {"id": "mongo-tutorial", "title": "MongoDB Manual", "url": "https://www.mongodb.com/docs/manual/tutorial/", "source": "MongoDB Docs", "type": "docs", "skills": ["mongodb"], "diff": "Medium", "desc": "MongoDB tutorials covering the document model, CRUD, and indexes."},
    {"id": "redis-docs", "title": "Redis Documentation", "url": "https://redis.io/docs/latest/", "source": "Redis Docs", "type": "docs", "skills": ["redis"], "diff": "Medium", "desc": "Redis docs on data structures, caching, and persistence."},
    # Testing
    {"id": "pytest-docs", "title": "pytest Documentation", "url": "https://docs.pytest.org/en/stable/", "source": "Official Docs", "type": "docs", "skills": ["pytest"], "diff": "Easy", "desc": "pytest official docs: fixtures, parametrize, and best practices."},
    {"id": "jest-docs", "title": "Jest Getting Started", "url": "https://jestjs.io/docs/getting-started", "source": "Official Docs", "type": "docs", "skills": ["jest"], "diff": "Easy", "desc": "Write your first Jest tests with the official getting-started guide."},
    # AI / ML
    {"id": "ml-crash", "title": "Machine Learning Crash Course", "url": "https://developers.google.com/machine-learning/crash-course", "source": "Google", "type": "course", "skills": ["machine learning"], "diff": "Hard", "desc": "Google's ML crash course covering core concepts with exercises."},
    {"id": "dl-specialization", "title": "Deep Learning Specialization", "url": "https://www.deeplearning.ai/courses/deep-learning-specialization/", "source": "DeepLearning.AI", "type": "course", "skills": ["deep learning"], "diff": "Hard", "desc": "Andrew Ng's deep learning specialization: NNs, CNNs, and sequence models."},
    {"id": "pytorch-tutorials", "title": "PyTorch Tutorials", "url": "https://pytorch.org/tutorials/", "source": "Official Docs", "type": "tutorial", "skills": ["pytorch"], "diff": "Hard", "desc": "PyTorch official tutorials from tensors to training neural networks."},
    {"id": "tf-tutorials", "title": "TensorFlow Tutorials", "url": "https://www.tensorflow.org/tutorials", "source": "Official Docs", "type": "tutorial", "skills": ["tensorflow"], "diff": "Hard", "desc": "TensorFlow official tutorials for beginners and advanced workflows."},
    {"id": "sklearn-tutorial", "title": "scikit-learn Tutorials", "url": "https://scikit-learn.org/stable/tutorial/", "source": "Official Docs", "type": "tutorial", "skills": ["scikit-learn"], "diff": "Medium", "desc": "scikit-learn tutorial on modeling, preprocessing, and evaluation."},
    {"id": "nlp-specialization", "title": "Natural Language Processing Specialization", "url": "https://www.coursera.org/specializations/natural-language-processing", "source": "Coursera", "type": "course", "skills": ["nlp"], "diff": "Hard", "desc": "NLP specialization covering text classification, attention, and transformers."},
    {"id": "llm-courses", "title": "LLM Short Courses", "url": "https://www.deeplearning.ai/short-courses/", "source": "DeepLearning.AI", "type": "course", "skills": ["llm"], "diff": "Hard", "desc": "Short hands-on courses on LLMs, prompt engineering, and agents."},
    {"id": "langchain-tutorials", "title": "LangChain Tutorials", "url": "https://python.langchain.com/docs/tutorials/", "source": "Official Docs", "type": "tutorial", "skills": ["langchain"], "diff": "Hard", "desc": "Build LLM applications with LangChain tutorials: chains, agents, and retrieval."},
    {"id": "langgraph-docs", "title": "LangGraph Documentation", "url": "https://langchain-ai.github.io/langgraph/", "source": "Official Docs", "type": "docs", "skills": ["langgraph"], "diff": "Hard", "desc": "LangGraph docs for building stateful, graph-based agent workflows."},
    {"id": "rag-tutorial", "title": "RAG Tutorial with LangChain", "url": "https://python.langchain.com/docs/tutorials/rag/", "source": "Official Docs", "type": "tutorial", "skills": ["rag"], "diff": "Hard", "desc": "End-to-end retrieval-augmented generation tutorial with vector stores."},
    {"id": "mlops-course", "title": "MLOps Specialization", "url": "https://www.deeplearning.ai/courses/machine-learning-engineering-for-production-mlops-specialization/", "source": "DeepLearning.AI", "type": "course", "skills": ["mlops"], "diff": "Hard", "desc": "MLOps specialization: model deployment, monitoring, and production systems."},
    # Architecture / concepts
    {"id": "microservices-io", "title": "Microservices Patterns", "url": "https://microservices.io/patterns/index.html", "source": "microservices.io", "type": "article", "skills": ["microservices"], "diff": "Medium", "desc": "Catalog of microservices patterns from decomposition to deployment."},
    {"id": "graphql-learn", "title": "GraphQL Learn", "url": "https://graphql.org/learn/", "source": "GraphQL", "type": "docs", "skills": ["graphql"], "diff": "Medium", "desc": "Learn the GraphQL query language, schemas, and resolvers."},
    {"id": "rest-api-design", "title": "REST API Design Best Practices", "url": "https://restfulapi.net/", "source": "restfulapi.net", "type": "article", "skills": ["rest api"], "diff": "Medium", "desc": "REST API design guide: resources, methods, status codes, and versioning."},
    {"id": "system-design", "title": "System Design Primer", "url": "https://github.com/donnemartin/system-design-primer", "source": "GitHub", "type": "article", "skills": ["system design", "distributed systems"], "diff": "Hard", "desc": "The System Design Primer: large-scale system design and interview prep."},
    {"id": "airflow-docs", "title": "Apache Airflow Documentation", "url": "https://airflow.apache.org/docs/", "source": "Official Docs", "type": "docs", "skills": ["data pipelines"], "diff": "Hard", "desc": "Orchestrate data pipelines with Apache Airflow DAGs."},
]

_CORPUS: list[LearningResource] = [
    LearningResource(
        id=item["id"],
        title=item["title"],
        url=item["url"],
        source=item["source"],
        resource_type=item["type"],
        description=item["desc"],
        skills=[skill.lower() for skill in item["skills"]],
        difficulty=item["diff"],
    )
    for item in _RAW_CORPUS
]

_CORPUS_BY_ID: dict[str, LearningResource] = {resource.id: resource for resource in _CORPUS}


def get_corpus() -> list[LearningResource]:
    """Return the full learning resource corpus."""
    return list(_CORPUS)


def get_resource(resource_id: str) -> LearningResource | None:
    """Return a corpus resource by id, or ``None``."""
    return _CORPUS_BY_ID.get(resource_id)
