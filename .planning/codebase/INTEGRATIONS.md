# External Integrations

**Analysis Date:** 2026-03-11

## APIs & External Services

**LLM Services:**
- OpenAI - LLM inference for patch generation
  - SDK/Client: `langchain-openai` 0.3.2
  - Auth: `OPENAI_API_KEY` environment variable
  - Used in: `components/patchagent/` for code analysis and patch generation

- Anthropic - Alternative LLM provider
  - Auth: `ANTHROPIC_API_KEY` environment variable
  - Proxy: Routed through LiteLLM service for unified interface

- DeepSeek - LLM alternative
  - Auth: `DEEPSEEK_API_KEY` environment variable
  - Proxy: Routed through LiteLLM

- Google APIs - Search and inference capabilities
  - Auth: `GOOGLE_API_KEY` environment variable

**LLM Orchestration:**
- LiteLLM (ghcr.io/berriai/litellm:main-latest) - LLM proxy and load balancing
  - Database: Separate PostgreSQL database (`litellm-db-{env}`)
  - Connection: `LITELLM_CONNECTION_STRING` for tracking and caching
  - Kubernetes: Deployed via Helm chart `charts/litellm/`
  - Configuration: `deployment/crs-k8s/b3yond-crs/charts/litellm/files/config.yaml`

**Competition API:**
- Competition Server - External scoring/submission system
  - URL: `COMPETITION_API_URL` environment variable (default mock: `http://b3yond-mock:8080`)
  - Auth: `COMPETITION_API_KEY_ID`, `COMPETITION_API_KEY_TOKEN`
  - Used by: `components/submitter/` for submitting patches

**GitHub:**
- GitHub API - Repository access for patch application
  - Auth: `GITHUB_TOKEN`, `GITHUB_USERNAME`, `GITHUB_EMAIL`
  - SDK: GitPython library (components/patchagent/)
  - Used for: Cloning repos, applying patches, creating commits

## Data Storage

**Databases:**
- PostgreSQL 16 (Azure Database for PostgreSQL Flexible Server)
  - Connection: `DATABASE_CONNECTION_STRING` in Kubernetes env
  - Client: GORM ORM (Go), SQLAlchemy (Python)
  - Databases created:
    - `b3yond-db-{env}` - Primary application database (scheduler, gateway, bandfuzz)
    - `litellm-db-{env}` - LiteLLM tracking and caching database
  - Managed by Terraform:
    - `deployment/crs-infra/modules/database/main.tf`
    - SKU varies by environment (B_Standard_B8ms for dev, GP_Standard_D64s_v3 for prod)
    - Storage: 32GB dev, 128GB test, 256GB prod
  - Firewall: All IPs allowed (0.0.0.0 - 255.255.255.255) - configured in Terraform

**Message Queue:**
- RabbitMQ - Async task processing
  - Connection: `RABBITMQ_URL` environment variable
  - Clients: pika (Python), amqp091-go (Go)
  - Deployed: Kubernetes Helm chart (bitnami/rabbitmq)
  - Auth: Username/password (default: user/secret in values.yaml)
  - Configuration:
    - Channel max: 10239
    - Consumer timeout: 1036800000ms (~12 days)
    - Used by: scheduler, bandfuzz, patchagent for task distribution
  - Priority queues: Patch generation uses priority-based delivery

**Caching/Job Queue:**
- Redis (with Sentinel for HA)
  - Connection: `REDIS_URL` environment variable
  - Clients: go-redis (Go), redis-py (Python)
  - Deployed: Kubernetes Helm chart (bitnami/redis)
  - Configuration:
    - Sentinel enabled for high availability
    - Master/replica replication
    - useHostnames: true for DNS resolution
  - Use cases:
    - RQ (Redis Queue) for Python job distribution (prime-build, seedgen)
    - Distributed locks and state tracking
    - Fuzzer run state persistence (`prime:fuzzer_run:{task_id}:{harness}`)
    - Reproduction state (`reproduction:{task_id}:{harness}:{testcase}`)

**File Storage:**
- Local filesystem - Persistent volumes in Kubernetes
  - PVC name: `crs-share`
  - Shared between components:
    - `prime-local` - Prime fuzzer artifacts
    - `seed-local` - Seed corpus storage
  - Mounted on pods for artifact persistence across restarts

## Authentication & Identity

**Auth Provider:**
- Custom API Key Authentication
  - Implementation: Key ID + Token pair for CRS and Competition APIs
  - CRS credentials: `CRS_KEY_ID`, `CRS_KEY_TOKEN`
  - Competition credentials: `COMPETITION_API_KEY_ID`, `COMPETITION_API_KEY_TOKEN`
  - Location: `deployment/values.yaml` (hardcoded "b3yond" defaults)

**Network Auth:**
- Tailscale - Zero-trust networking
  - OAuth: `TS_CLIENT_ID`, `TS_CLIENT_SECRET`
  - Operator tag: `TS_OP_TAG`
  - Hostname: `TS_HOSTNAME`
  - Deployed: Kubernetes operator for cluster connectivity
  - Kubernetes manifest: `deployment/crs-k8s/b3yond-crs/charts/tailscale-operator/`

**Cloud Provider Auth:**
- Azure (Terraform provisioning)
  - Tenant: `ARM_TENANT_ID`
  - Client: `ARM_CLIENT_ID`, `ARM_CLIENT_SECRET`
  - Subscription: `ARM_SUBSCRIPTION_ID`
  - Used for: AKS cluster, PostgreSQL, resource group creation

## Monitoring & Observability

**Tracing & Metrics:**
- OpenTelemetry - Distributed tracing (v1.35.0 for traces, v0.11.0 for logs)
  - Exporter endpoint: `OTEL_EXPORTER_OTLP_ENDPOINT` (default: `http://otel-backend:4317`)
  - Protocol: `OTEL_EXPORTER_OTLP_PROTOCOL` (default: gRPC)
  - Headers: `OTEL_EXPORTER_OTLP_HEADERS` (optional)
  - Used by: Go components (scheduler, gateway, bandfuzz) with SDK integration
  - Libraries: go.opentelemetry.io/otel/* for Go instrumentation

**Logging:**
- Structured JSON logging
  - Go: uber/zap logger
  - Python: loguru for structured output
  - Destination: Stdout (captured by Kubernetes container logs)
  - OpenTelemetry collector: Receives logs via OTLP gRPC

**Error Tracking:**
- Not explicitly configured - Relies on OpenTelemetry and application logging

## CI/CD & Deployment

**Hosting:**
- Microsoft Azure - Cloud platform
  - Region: Configurable (default in Terraform)
  - Compute: Azure Kubernetes Service (AKS)
  - Database: Azure Database for PostgreSQL (Flexible Server)
  - Authentication: Azure Service Principal

**Orchestration:**
- Kubernetes (AKS) - Container orchestration
  - Namespace: default and dedicated namespaces per component
  - Node selector: `b3yond.org/role=user` for workload placement
  - KEDA - Kubernetes Event Autoscaling (for dynamic scaling)
  - PDB (Pod Disruption Budget) - Availability guarantees

**Deployment Tool:**
- Helm 3 - Kubernetes package management
  - Chart location: `deployment/crs-k8s/b3yond-crs/`
  - Values files: `values.yaml` (default), `values.{ENV}.yaml` for environment-specific
  - Dependency management: `helm dependency update` before deployment
  - Commands in Makefile: `helm upgrade --install`

**Infrastructure-as-Code:**
- Terraform - Azure resource provisioning
  - Config: `deployment/crs-infra/`
  - Modules: `database/`, `k8s/`
  - Workspaces: Per-environment (dev, test, prod)
  - Commands: init, plan, apply, destroy via Makefile

**Container Registry:**
- GitHub Container Registry (GHCR)
  - Public image: `ghcr.io/berriai/litellm:main-latest` for LiteLLM
  - Private registry secret: `ghcr-registry` (configured in Helm values)

## Environment Configuration

**Required env vars (from .env.example):**

**Azure Infrastructure:**
- `ARM_TENANT_ID` - Azure tenant ID
- `ARM_CLIENT_ID` - Azure service principal client ID
- `ARM_CLIENT_SECRET` - Azure service principal secret
- `ARM_SUBSCRIPTION_ID` - Azure subscription ID

**GitHub Integration:**
- `GITHUB_USERNAME` - Git user for patch operations
- `GITHUB_TOKEN` - GitHub API token
- `GITHUB_EMAIL` - Git user email

**Tailscale VPN:**
- `TS_CLIENT_ID` - Tailscale OAuth client ID
- `TS_CLIENT_SECRET` - Tailscale OAuth secret
- `TS_OP_TAG` - Tailscale operator tag
- `TS_HOSTNAME` - Tailscale hostname

**API Endpoints:**
- `CRS_API_HOSTNAME` - CRS API public hostname
- `COMPETITION_API_URL` - Competition server endpoint
- `COMPETITION_API_KEY_ID` - Competition API credentials
- `COMPETITION_API_KEY_TOKEN` - Competition API credentials
- `CRS_KEY_ID` - CRS API credentials
- `CRS_KEY_TOKEN` - CRS API credentials

**OpenTelemetry:**
- `OTEL_EXPORTER_OTLP_ENDPOINT` - Collector endpoint (e.g., `http://otel-backend:4317`)
- `OTEL_EXPORTER_OTLP_HEADERS` - Additional headers (optional)
- `OTEL_EXPORTER_OTLP_PROTOCOL` - Protocol type (e.g., grpc)

**LLM Providers:**
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `DEEPSEEK_API_KEY` - DeepSeek API key (optional)
- `GOOGLE_API_KEY` - Google API key (optional)

**Secrets location:**
- `.env` file at repository root (not committed - listed in .gitignore)
- Kubernetes secrets generated by: `deployment/crs-k8s/scripts/generate-secrets.sh`
- Secret values file: `deployment/crs-k8s/b3yond-crs/secret-values.yaml` (not committed)
- Azure Key Vault support: Not currently integrated

## Webhooks & Callbacks

**Incoming:**
- None explicitly configured - Competition API integration is pull-based via REST

**Outgoing:**
- Patch submission to Competition API - Synchronous REST call
  - Component: `components/submitter/`
  - Triggered by: Successful patch generation completion
  - Payload: Patch diff and metadata

---

*Integration audit: 2026-03-11*
