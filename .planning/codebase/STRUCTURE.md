# Codebase Structure

**Analysis Date:** 2026-03-11

## Directory Layout

```
42-directed/
├── components/              # 16 microservice components
│   ├── gateway/            # REST API entry point
│   ├── scheduler/          # Task scheduling and queue publishing
│   ├── submitter/          # Bug submission orchestrator
│   ├── seedgen/            # Seed generation via static analysis
│   ├── primefuzz/          # Prime symbolic execution fuzzer
│   ├── bandfuzz/           # Band-based fuzzing
│   ├── cminplusplus/       # C++ calculator and controller
│   ├── directed/           # Directed fuzzing
│   ├── triage/             # Result deduplication and triage
│   ├── corpusgrabber/      # Corpus collection
│   ├── slice/              # Program slicing
│   ├── patchagent/         # Patch generation and submission
│   ├── javaslicer/         # Java program analysis
│   ├── sarif/              # SARIF result evaluation
│   ├── prime-build/        # Build system for prime fuzzer
│   └── db/                 # Database schema and initialization
├── deployment/             # Infrastructure-as-Code
│   ├── crs-infra/          # Terraform configurations (Azure)
│   ├── crs-k8s/            # Kubernetes Helm charts
│   ├── kubernetes/         # Additional K8s manifests
│   ├── scripts/            # Deployment utilities
│   └── Makefile            # Deployment orchestration
├── .planning/              # GSD planning artifacts
│   └── codebase/           # This directory
├── .github/                # GitHub Actions workflows
├── notes/                  # Documentation and notes
├── .env.example            # Environment configuration template
├── README.md               # Project overview
└── LICENSE                 # GPLv3 License
```

## Directory Purposes

**Gateway Component:**
- Purpose: REST API server for task submission and status queries
- Contains: OpenAPI-generated handlers, database models, middleware, services
- Tech: Go 1.23, go-openapi, GORM, Zap logging
- Key directories:
  - `cmd/crs-gateway/`: Entry point (main.go)
  - `gen/`: OpenAPI-generated code from Swagger spec
  - `internal/handlers/`: HTTP request handlers
  - `internal/services/`: Business logic
  - `internal/db/`: GORM models and database utilities
  - `internal/config/`: Configuration loading
  - `internal/logger/`: Logging setup
  - `internal/middle/`: HTTP middleware
  - `swagger/`: OpenAPI specification files

**Scheduler Component:**
- Purpose: Orchestrates task scheduling and queue publishing
- Contains: Task fetching routines, RabbitMQ client, database access
- Tech: Go 1.23, GORM, amqp091-go, Redis client
- Key directories:
  - `cmd/scheduler/`: Entry point
  - `internal/scheduler/`: Scheduler loop and routine registry
  - `internal/messaging/`: RabbitMQ connection pooling
  - `internal/database/`: PostgreSQL and Redis clients
  - `internal/api/`: Health/status endpoints
  - `internal/telemetry/`: OpenTelemetry tracing
  - `repository/`: Data access layer
  - `service/`: Business logic (task routines)
  - `models/`: Data structures

**Submitter Component:**
- Purpose: Manages bug submission workflow to competition API
- Contains: Database queries, Redis coordination, async workers
- Tech: Python 3, SQLAlchemy, Redis Sentinel, aiohttp
- Key files:
  - `app.py`: Entry point, async main loop
  - `workers.py`: Async worker routines (db_worker, submit_worker, confirm_worker, bundle_worker)
  - `tasks.py`: Task submission implementation
  - `db.py`: SQLAlchemy models and database utilities
  - `redisio.py`: Redis Sentinel client wrappers
  - `submission.py`: Submission data preparation
  - `otlp.py`: OpenTelemetry tracing setup

**Seedgen Component:**
- Purpose: Generates seed inputs using static analysis and constraint solving
- Contains: LLVM analysis, constraint generation, seed generation engines
- Tech: Python, C++, LLVM bindings, tree-sitter
- Key subdirectories:
  - `seedd/`: Server daemon for seed generation (Go gRPC service)
  - `seedgen2/`: Second-generation seed generator
  - `argus/`: Static analysis engine
  - `bandld/`: Band-based load analysis
  - `callgraph/`: Call graph extraction
  - `getcov/`: Coverage extraction utilities

**Primefuzz Component:**
- Purpose: Symbolic execution and prime-based fuzzing
- Contains: Fuzzer implementation, sentinel service, database models
- Tech: Python, custom fuzzer backend
- Key files:
  - `run.py`: Main fuzzer entry point
  - `workflow.py`: Fuzzing workflow orchestration
  - `sentinel.py`: Sentinel monitoring service
  - `run_sentinel.py`: Sentinel execution wrapper
  - `db/`: Database models and utilities

**Triage Component:**
- Purpose: Deduplicates and triages crash results
- Contains: Crash clustering, duplicate detection, result parsing
- Tech: Python
- Key subdirectories:
  - `parser/`: Result parsing from fuzzer output
  - `dedup/`: Crash deduplication logic
  - `infra/`: Infrastructure utilities

**Patchagent Component:**
- Purpose: Generates and submits patches for discovered bugs
- Contains: Patch generation, submission mechanics, reproducers
- Tech: Python, C++
- Key subdirectories:
  - `patchagent/`: Main patch generation logic
  - `patch_generator/`: Patch creation from diffs
  - `patch_submitter/`: Competition API submission
  - `reproducer/`: Bug reproduction setup
  - `aixcc/`: AIxCC integration utilities

**Database Component:**
- Purpose: Database initialization and schema definition
- Contains: SQL schema files
- Tech: PostgreSQL
- Key files:
  - `schema.sql`: Complete schema with tables for tasks, bugs, patches, users, etc.
  - `Dockerfile`: Database image definition

**Deployment Directory:**
- Purpose: Infrastructure-as-Code and deployment orchestration
- Contains: Terraform modules, Helm charts, Kubernetes manifests
- Tech: Terraform (Azure provider), Helm, Kubernetes
- Key subdirectories:
  - `crs-infra/`: Terraform root module for cloud infrastructure
    - `environment/`: Environment-specific tfvars files (dev, prod)
    - `modules/`: Reusable Terraform modules
  - `crs-k8s/`: Helm chart for application deployment
    - `b3yond-crs/`: Main Helm chart
    - `charts/`: Sub-charts for components (submitter, seedgen, triage-timeout, litellm, patch-claude)
  - `kubernetes/`: Additional K8s manifests for storage, networking, scaling
    - `storage/`: PersistentVolume and PersistentVolumeClaim definitions
    - `tailscale/`: VPN networking configuration
    - `keda/`: Kubernetes Event Autoscaler definitions

## Key File Locations

**Entry Points:**
- `components/gateway/cmd/crs-gateway/main.go`: API server startup
- `components/scheduler/cmd/scheduler/main.go`: Scheduler service startup
- `components/submitter/app.py`: Submitter service startup
- `components/seedgen/seedd/cmd/seedd/main.go`: Seed daemon startup
- `deployment/Makefile`: Infrastructure deployment orchestration

**Configuration:**
- `components/gateway/internal/config/config.go`: Gateway config loading
- `components/scheduler/config/`: Scheduler configuration
- `deployment/.env.example`: Required environment variables template

**Core Logic:**
- `components/gateway/internal/services/`: Gateway business logic
- `components/gateway/internal/handlers/`: API endpoint handlers
- `components/scheduler/internal/scheduler/`: Scheduling loop
- `components/scheduler/repository/`: Task and bug data access
- `components/submitter/workers.py`: Async submission workers
- `components/submitter/db.py`: Database models for submission tracking

**Testing:**
- `components/seedgen/test_cot.py`: Seedgen testing
- `components/triage/test_parser.py`: Triage parser testing
- Individual component tests co-located with source files

## Naming Conventions

**Files:**
- Go entry points: `cmd/{component}/main.go`
- Go packages: `internal/{subsystem}/{feature}.go`
- Python modules: `snake_case.py`
- Dockerfiles: `Dockerfile` or `Dockerfile.{variant}` for multi-image components

**Directories:**
- Go packages: `internal/`, `repository/`, `service/`, `models/`
- Components: kebab-case (e.g., `prime-build`, `corpus-grabber`)
- Kubernetes charts: `crs-k8s/b3yond-crs/charts/{component}/`

**Types and Structs (Go):**
- PascalCase: `TaskService`, `RabbitMQ`, `ServerParams`
- Enums with Type: `TaskTypeEnum`, `TaskStatusEnum`, `FuzzerTypeEnum`
- Interfaces with suffix: `Repository`, `Service`, `Handler`

**Functions (Go):**
- Constructor functions: `New{TypeName}` (e.g., `NewTaskService`, `NewRabbitMQ`)
- Methods: camelCase (e.g., `GetTaskCount()`, `IsReady()`)

**Variables (Python):**
- Local: snake_case (e.g., `task_list`, `msg_set`)
- Classes: PascalCase (e.g., `MessageSet`, `RedisStore`)

## Where to Add New Code

**New Feature in Gateway:**
- Primary code: `components/gateway/internal/services/{feature}.go`
- Handler: `components/gateway/internal/handlers/{feature}_handler.go`
- Database access: `components/gateway/internal/db/` (extend model.go)
- API spec: `components/gateway/swagger/crs-swagger-v1.3.0.yaml`

**New Component/Microservice:**
- Go component structure:
  - `components/{component}/cmd/{component}/main.go`
  - `components/{component}/internal/config/`, `logger/`, `database/`
  - `components/{component}/Dockerfile`
  - Add to deployment: `deployment/crs-k8s/b3yond-crs/charts/{component}/`
- Python component structure:
  - `components/{component}/` with .py files at root or in subdirectories
  - `components/{component}/Dockerfile`
  - Add task handler if queued: `components/{component}/task_handler.py`

**New Worker/Task Handler:**
- Co-locate with component: `components/{component}/task_handler.py`
- Register with scheduler: Add import to `components/scheduler/service/service.go`
- Define queue name in RabbitMQ config

**Shared Utilities:**
- Go: Add to `components/gateway/internal/` (reusable packages)
- Python: Create in relevant component's utils subdirectory
- Cross-component sharing: Consider creating new lightweight component

**Database Schema Changes:**
- Add migration to `components/db/schema.sql`
- Update GORM models: `components/gateway/internal/db/model.go`
- Create database access methods in relevant repository files

**Kubernetes Deployment:**
- Component Helm chart: `deployment/crs-k8s/b3yond-crs/charts/{component}/`
- Include: `Chart.yaml`, `values.yaml`, `templates/{kind}.yaml`
- Reference in main values: `deployment/crs-k8s/b3yond-crs/values.yaml`

## Special Directories

**Generated Code:**
- Location: `components/gateway/gen/`
- Generated by: OpenAPI generator from Swagger spec
- Committed: Yes
- Manual edits: No - regenerate from swagger file

**Build Artifacts:**
- `.next/` (Next.js notes site): Generated, not committed
- `node_modules/`: Generated, not committed
- Removed from tracking via `.gitignore`

**Dev Containers:**
- Location: `components/*/.devcontainer/`
- Purpose: Standardized development environment setup
- File: `devbox.json` for Nix-based reproducible development

**Deployment Scripts:**
- Location: `deployment/scripts/`
- Purpose: Helper scripts for Terraform, Helm, Kubernetes operations
- Examples: `generate-secrets.sh` for Helm secret generation

---

*Structure analysis: 2026-03-11*
