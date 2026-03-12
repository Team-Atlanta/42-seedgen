# Technology Stack

**Analysis Date:** 2026-03-11

## Languages

**Primary:**
- Go 1.23.4-1.23.5 - Core system components (scheduler, gateway, bandfuzz)
- Python 3.11-3.12 - AI/ML components (patchagent, prime-build, seedgen, triage)

**Secondary:**
- YAML - Configuration and deployment manifests
- Terraform HCL - Infrastructure-as-Code for Azure deployment
- Bash - Deployment scripts and utilities

## Runtime

**Environment:**
- Docker - Container runtime for all components
- Kubernetes - Container orchestration platform for production deployment
- Alpine Linux - Base image for Go components (lightweight production)
- Ubuntu Noble - Base image for Python components (development tools, Docker-in-Docker support)

**Package Manager:**
- Go Modules - Go dependency management
  - Lockfile: `go.sum` present in each Go module
- pip/setuptools - Python dependency management
  - Lockfile: `pyproject.toml` in Python components

## Frameworks

**Core:**
- GORM v1.25.12 - ORM for database operations (Go)
- Uber Fx v1.23.0 - Dependency injection framework (Go)
- SQLAlchemy 2.0.39+ - ORM for database operations (Python)
- LangChain 0.3.15 - LLM orchestration and agentic workflows (Python)

**API & Web:**
- go-openapi - OpenAPI/Swagger specification and validation (Go gateway component)

**Message Queue:**
- RabbitMQ client (pika 1.3.2+ Python, amqp091-go v1.10.0 Go) - Async task processing
- Redis (go-redis/v9, python redis module) - Caching and job queue backend (RQ)

**Testing:**
- pytest 8.3.5+ - Python test framework
- black 25.1.0 - Python code formatting
- flake8 7.1.2+ - Python linting
- mypy 1.15.0+ - Python type checking
- go test - Go standard library testing

**Build/Dev:**
- Docker buildx - Multi-architecture Docker image building
- Helm 3 - Kubernetes package management
- Terraform 1.x - Infrastructure provisioning
- Make - Build automation (`Makefile` in deployment/)

## Key Dependencies

**Critical:**
- gorm.io/gorm v1.25.12 - Database persistence layer (used across scheduler, gateway, bandfuzz)
- github.com/rabbitmq/amqp091-go v1.10.0 - Task queue integration for scheduler and bandfuzz
- github.com/redis/go-redis/v9 v9.5.1-9.7.1 - Distributed caching and job queue
- langchain v0.3.15 / langchain-openai v0.3.2 - LLM integration for patch generation (patchagent)
- opentelemetry (v1.35.0 for traces, v0.11.0 for logs) - Distributed tracing and observability

**Infrastructure:**
- gorm.io/driver/postgres v1.5.11 - PostgreSQL driver (primary database)
- github.com/joho/godotenv v1.5.1 - Environment variable loading from .env files
- github.com/google/uuid v1.6.0 - UUID generation for request tracking
- go.uber.org/zap v1.27.0 - Structured JSON logging

**Code Quality:**
- rq (Redis Queue) - Python job queue system (prime-build, seedgen)
- loguru - Python structured logging
- GitPython 3.1.44+ - Git operations for patch generation
- tree-sitter v0.24.0 - Code parsing for C-like and Java languages
- clang 16.0.1 - C/C++ compilation and analysis

## Configuration

**Environment:**
- `.env` file pattern - Load from environment variables with godotenv/python-dotenv
- Template provided: `.env.example` in deployment/ directory
- Critical configs:
  - `RABBITMQ_URL` - Message queue connection string
  - `REDIS_URL` - Redis connection string
  - `DATABASE_CONNECTION_STRING` - PostgreSQL connection (GORM format)
  - `OTEL_EXPORTER_OTLP_ENDPOINT` - OpenTelemetry collector endpoint
  - Cloud credentials (ARM_* for Azure, GITHUB_TOKEN for GitHub)
  - LLM API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY)

**Build:**
- `pyproject.toml` - Python project configuration in `components/patchagent/` and `components/prime-build/`
- `go.mod` / `go.sum` - Go module definitions in scheduler, gateway, bandfuzz
- `Dockerfile` files - Component-specific containerization
- `deployment/Makefile` - Main entry point for infrastructure and application deployment

## Platform Requirements

**Development:**
- Docker daemon (for building images)
- Go 1.23.4+ (for building Go components)
- Python 3.11+ (for running Python components)
- kubectl - Kubernetes CLI for cluster management
- Helm 3 - For deploying to Kubernetes
- Terraform 1.x - For infrastructure provisioning

**Production:**
- Microsoft Azure - Deployment target (Kubernetes cluster + PostgreSQL managed service)
- Azure Kubernetes Service (AKS) - Managed Kubernetes
- Azure Database for PostgreSQL - Managed PostgreSQL 16
- Kubernetes 1.x (via AKS)

---

*Stack analysis: 2026-03-11*
