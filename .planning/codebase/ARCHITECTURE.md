# Architecture

**Analysis Date:** 2026-03-11

## Pattern Overview

**Overall:** Distributed microservices architecture with layered components communicating via RabbitMQ message queues and shared PostgreSQL database.

**Key Characteristics:**
- Modular, independently deployable services (16 components)
- Dependency injection via Uber's fx framework (Go components)
- Event-driven communication through RabbitMQ message queues
- Centralized PostgreSQL database with GORM ORM
- Kubernetes deployment with Helm charts
- Clear separation of concerns with handler/service/repository layers

## Layers

**API/Gateway Layer:**
- Purpose: REST API entry point and request routing
- Location: `components/gateway/` (Go)
- Contains: OpenAPI/Swagger-based REST handlers, request/response marshaling, authentication
- Depends on: database, services, middleware
- Used by: External clients and internal services

**Service Layer:**
- Purpose: Business logic implementation
- Location: `components/*/internal/services/` (Go) and task-specific Python services
- Contains: Task services, status services, SARIF parsing, bug management
- Depends on: repositories, database, external APIs
- Used by: handlers and routines

**Repository Layer:**
- Purpose: Data access abstraction
- Location: `components/*/repository/` (Go components)
- Contains: Database queries, bug repositories, task repositories
- Depends on: GORM models, database connection
- Used by: service layer

**Message Queue Layer:**
- Purpose: Asynchronous inter-service communication
- Location: `components/scheduler/internal/messaging/` (RabbitMQ)
- Contains: Connection pooling, channel management, queue operations
- Depends on: RabbitMQ server, configuration
- Used by: scheduler, submitter, worker services

**Worker/Task Execution Layer:**
- Purpose: Asynchronous job processing
- Location: `components/submitter/workers.py`, `components/seedgen/task_handler.py`
- Contains: Worker routines for submission, confirmation, triage operations
- Depends on: database, Redis sentinel, RabbitMQ
- Used by: scheduler orchestration

**Infrastructure Layer:**
- Purpose: System configuration and cross-cutting concerns
- Location: `components/*/internal/config/`, `components/*/internal/logger/`, `components/*/internal/database/`
- Contains: Configuration loading, structured logging (Zap), database connection pooling, telemetry
- Depends on: external services (PostgreSQL, Redis, RabbitMQ)
- Used by: all other layers

## Data Flow

**Task Processing Pipeline:**

1. **Task Intake**: API client submits task via `POST /v1/task` to gateway
2. **Task Storage**: Gateway handler writes task to PostgreSQL with `pending` status
3. **Task Scheduling**: Scheduler component fetches pending tasks every 60 seconds
4. **Task Publishing**: Scheduler publishes task to RabbitMQ queue (e.g., `seedgen_queue`, `prime_queue`)
5. **Task Processing**: Worker service (seedgen, primefuzz, etc.) consumes from queue
6. **Result Handling**: Worker updates task status to `processing`, generates results
7. **Bug Collection**: Submitter fetches bugs for processing tasks, groups by profile
8. **Bug Submission**: Submitter sends bugs to competition API, tracks via Redis sets
9. **Result Confirmation**: Confirmation worker updates database with submission status
10. **Task Completion**: Task status transitions to `succeeded` or `failed`

**State Management:**

- **Database**: PostgreSQL stores persistent state
  - Tasks (status, type, source)
  - Bugs (crash reports, profiles)
  - Patches (generated fixes)
  - SARIF results (vulnerability data)
  - Users (authentication)
  - Messages (API audit logs)

- **Redis Sentinel**: Stores temporary state
  - Task sets (pending submissions)
  - Confirm sets (confirmed submissions)
  - Bundle sets (bundled patches)
  - Submission tracking

- **RabbitMQ**: Asynchronous work queues
  - Task queues (seedgen, prime, general, directed)
  - Ack/Nack acknowledgment handling
  - Connection pooling with heartbeat recovery

## Key Abstractions

**Task Abstraction:**
- Purpose: Represents a fuzzing task with type and source information
- Examples: `components/gateway/internal/db/model.go`, `components/scheduler/models/`
- Pattern: GORM model with status enums (pending, processing, succeeded, failed, etc.)
- Types: TaskTypeFull, TaskTypeDelta, FuzzerType (seedgen, prime, general, directed)

**Message Queue Abstraction:**
- Purpose: Decouple task producers from consumers
- Examples: `components/scheduler/internal/messaging/mq.go`
- Pattern: RabbitMQ interface with connection pooling, automatic reconnection
- Queues: Fuzzer-specific task queues + response queues for ACK/NACK

**Worker Pattern:**
- Purpose: Encapsulate periodic or event-driven tasks
- Examples: `components/submitter/workers.py` (db_worker, submit_worker, confirm_worker)
- Pattern: Async functions consuming from Redis sets and processing tasks
- Uses: SQLAlchemy for database access, Redis for coordination

**Service Routine Pattern:**
- Purpose: Encapsulate repeated scheduler tasks
- Examples: `components/scheduler/service/` (TaskRoutine, SarifRoutine, BugRoutine, CancelRoutine)
- Pattern: Interfaces implementing Run() and Cancel() methods, registered via fx.Annotated groups
- Trigger: Scheduler invokes periodically (1-minute interval)

**Handler Pattern:**
- Purpose: HTTP request handling with dependency injection
- Examples: `components/gateway/internal/handlers/`
- Pattern: fx-provided structs with method receivers for each API endpoint
- Structure: GetStatusHandler, PostV1TaskHandler, DeleteV1TaskHandler, PostV1SarifHandler

**Repository Pattern:**
- Purpose: Isolate data access logic
- Examples: `components/scheduler/repository/task_repository.go`
- Pattern: Interface-based repositories with GORM query builders
- Methods: Queries for filtering tasks by status, creation/update operations

## Entry Points

**Gateway Entry Point:**
- Location: `components/gateway/cmd/crs-gateway/main.go`
- Triggers: Container startup, API requests on port 8080
- Responsibilities:
  - Loads configuration via dotenv
  - Initializes database connection and GORM
  - Creates Zap logger
  - Wires up fx dependency graph
  - Starts REST API server with OpenAPI spec
  - Registers all handlers and middleware

**Scheduler Entry Point:**
- Location: `components/scheduler/cmd/scheduler/main.go`
- Triggers: Container startup
- Responsibilities:
  - Loads config, database, RabbitMQ connections
  - Initializes Redis client, telemetry, tracing
  - Wires up all service routines via fx groups
  - Starts scheduler loop (1-minute tick)
  - Publishes tasks to appropriate queues

**Submitter Entry Point:**
- Location: `components/submitter/app.py`
- Triggers: Container startup
- Responsibilities:
  - Initializes database engine (SQLAlchemy)
  - Connects to Redis Sentinel for task coordination
  - Spawns async workers (db_worker, submit_worker, confirm_worker, bundle_worker)
  - Fetches tasks with status="processing"
  - Manages bug submission lifecycle

**Python Worker Entry Points:**
- Seedgen: `components/seedgen/task_handler.py` (task queue consumer)
- Primefuzz: `components/primefuzz/run.py` (fuzzer orchestration)
- Triage: `components/triage/task_handler.py` (result analysis)
- Slice: `components/slice/slice.py` (program slicing)
- Corpus Grabber: `components/corpusgrabber/task_handler.py` (corpus collection)

## Error Handling

**Strategy:** Layered error handling with logging and status transitions

**Patterns:**

- **Database Errors**: Logged via Zap, status updates to `errored` state, manual retry via API
- **Message Queue Errors**: Connection pooling with automatic reconnection, NACK requeue on handler failure
- **HTTP Errors**: Structured error responses from handlers (error.go), including validation and auth errors
- **Python Task Handlers**: Try-catch with logging, task status update to failed, exception propagation to scheduler

**Recovery Mechanisms:**
- RabbitMQ connection pool auto-reconnect with backoff
- Redis Sentinel automatic failover for session storage
- Database connection pooling with ping health checks
- Task retry via scheduler re-publishing on NACK

## Cross-Cutting Concerns

**Logging:**
- Go: Structured logging via Zap (components/*/internal/logger/)
- Python: Standard logging module with OTLP export (components/submitter/otlp.py)
- All errors logged with context: request ID, task ID, timestamps

**Validation:**
- API: OpenAPI schema validation via go-openapi/validate
- Database: Model constraints, enum validation via GORM tags
- Tasks: Source type validation (repo, fuzz_tooling, diff)

**Authentication:**
- Gateway: HTTP Basic Auth via BasicAuthAuth handler
- Credentials: Loaded from environment variables (API_USER, API_PASS)
- Database: User table with hashed passwords (production deployment)

**Telemetry:**
- Tracing: OpenTelemetry via components/scheduler/internal/telemetry/
- Metrics: OTLP HTTP exporter (components/submitter/otlp.py)
- Spans: Request tracing for task processing pipeline
- Endpoint: Configurable via OTEL_EXPORTER_OTLP_ENDPOINT

**Database Access:**
- ORM: GORM for all components with PostgreSQL driver
- Connection: Pool recycling every 5 minutes (DATA_REFRESH_INTERVAL)
- Models: Defined per-component with soft deletes and timestamps
- Migrations: Schema version tracking, manual schema.sql files (components/db/schema.sql)

---

*Architecture analysis: 2026-03-11*
