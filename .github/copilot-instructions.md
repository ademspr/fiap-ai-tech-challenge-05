# Copilot Instructions

## Repository Overview

FIAP AI Tech Challenge 05 — a Python microservices system for architecture diagram analysis. Users upload diagrams; the API queues them for AI analysis; the worker processes them and stores structured reports.

## Project Layout

```
packages/
  contracts/      # hackathon_contracts — shared Pydantic messages, RabbitMQ topology, report schemas
  platform/       # hackathon_platform  — shared structlog logging setup and MinIO utilities
services/
  api/            # FastAPI service: diagram upload, job status, report retrieval, internal worker callbacks
  worker/         # RabbitMQ consumer: AI analysis pipeline, calls api internal routes on completion
```

Each package and service is an independent `uv`-managed project with its own `pyproject.toml`.

## Build, Test, and Lint Commands

**Install all packages (from repo root):**
```bash
pip install -e "./packages/platform"
pip install -e "./packages/contracts[dev]"
pip install -e "./services/api[dev]"
pip install -e "./services/worker[dev]"
```

**Lint with Ruff (line-length 100, rules E/F/I/UP):**
```bash
ruff check packages/platform/src packages/platform/tests packages/contracts/tests \
  services/api/src services/api/tests services/worker/src services/worker/tests
```

**Check layer boundaries (CI-enforced):**
```bash
bash scripts/check_layer_boundaries.sh
```

**Run all tests with coverage (≥70% required):**
```bash
PYTHONPATH=services/api/src:services/worker/src:packages/contracts/src:packages/platform/src \
pytest packages/contracts/tests packages/platform/tests services/api/tests services/worker/tests \
  --cov=hackathon_contracts --cov=hackathon_platform --cov=hackathon_api --cov=hackathon_worker \
  --cov-config=.coveragerc --cov-report=term-missing -v
```

**Run a single test file:**
```bash
PYTHONPATH=services/api/src:services/worker/src:packages/contracts/src:packages/platform/src \
pytest services/api/tests/test_jobs_domain.py -v
```

**Start the full stack:**
```bash
docker compose up
```

**Alembic migrations (from `services/api/`):**
```bash
alembic upgrade head
alembic revision --autogenerate -m "description"
```

## Architecture

### Layered (Clean) Architecture — Both Services

Each service follows a strict four-layer structure:

| Layer | Location | Rule |
|-------|----------|------|
| `domain/` | entities, enums, exceptions, policies | No framework or infrastructure imports |
| `application/` | use cases (`jobs.py`), port interfaces (`ports.py`) | No infrastructure imports; uses only domain types |
| `infrastructure/` | DB repos, RabbitMQ, MinIO, Prometheus | Implements ports; can use any library |
| `presentation/` | FastAPI routers, Pydantic schemas | Only `deps.py` may import infrastructure |

**The layer boundary is enforced by `scripts/check_layer_boundaries.sh` and runs in CI.** Violations cause a build failure.

### Inter-Service Communication

1. **API → Worker** (async): API publishes `AnalyzeDiagramJobV1` to RabbitMQ exchange `hackathon.diagrams` with routing key `analyze`. Queue: `diagram.analysis` (with DLQ: `diagram.analysis.dlq`).
2. **Worker → API** (HTTP): Worker calls API internal routes (`/internal/v1/...`) authenticated via `X-Internal-Token` header (shared secret from `INTERNAL_TOKEN` env var).

### Shared Packages

- **`hackathon_contracts`**: All cross-service types live here — `AnalyzeDiagramJobV1` (queue message), `JobPatchV1`, `JobCompletionV1` (internal API bodies), `TechnicalReportV1` (report schema), and `messaging_topology` (exchange/queue names).
- **`hackathon_platform`**: `configure_logging()` (structlog JSON), `minio_io.ensure_bucket()`, `object_keys`.

### Gateway

Traefik proxies external traffic to the API (port 8080 → public; port 8082 → internal). The worker calls the API via `http://traefik:8081` (internal network) so that internal routes stay off the external port.

## Key Conventions

### Ports as Protocols
Application-layer interfaces are defined as `typing.Protocol` classes in `application/ports.py`. Infrastructure adapters implement these protocols without explicit inheritance (structural subtyping). Tests inject fakes by satisfying the same interface.

### Infrastructure Wiring Only in `deps.py`
`presentation/deps.py` is the single file allowed to import from `infrastructure/`. FastAPI dependency injection (`Depends`) wires concrete implementations to router handlers. Integration tests override dependencies via `app.dependency_overrides`.

### Integration Test Setup
Tests use:
- SQLite (`aiosqlite`) instead of PostgreSQL (same SQLAlchemy models)
- `httpx.AsyncClient` with `ASGITransport` (no real HTTP server)
- `app.dependency_overrides` to replace MinIO storage and RabbitMQ publisher
- Fake publisher classes that capture or fail on publish (e.g., `ListPublisher`, `FailingListPublisher`)

### Domain Entities
`AnalysisJob` and `Client` are plain `dataclasses` (frozen/slotted where appropriate). Domain logic (e.g., `client.require_minimum_balance_for_upload()`, `client.debited()`) lives on the entity — not in services or routers.

### Logging
All services use `structlog` with JSON output in production (`configure_logging(json_logs=True, service_name=...)`). Use `structlog.get_logger(__name__)` and pass context as keyword args: `log.info("job_completed", job_id=str(job_id), tokens_used=tokens_used)`.

### Settings
`pydantic-settings` (`BaseSettings`) loads config from environment variables or a `.env` file. A singleton `settings` object is imported from `config.py` in each service. See `.env.example` for the relevant variables.

### Worker AI Placeholder
`hackathon_worker/application/ai_placeholder.py` is the stub for the AI model call. When replacing with a real model, keep the same signature: `run_placeholder_analysis(diagram_bytes: bytes, content_type: str) -> tuple[TechnicalReportV1, int]`.
