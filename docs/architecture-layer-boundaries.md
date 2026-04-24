# Layer boundaries (API + Worker)

**Goal:** domain and application layers do **not** import `infrastructure` (no ORM, concrete HTTP clients, Prometheus adapters, etc.).

## API

**Presentation** wires ports to implementations in the composition root at [`services/api/src/hackathon_api/presentation/deps.py`](../services/api/src/hackathon_api/presentation/deps.py) — the only file in that folder allowed to import `hackathon_api.infrastructure` (besides `main.py` and `seed.py`). The name `deps` follows common **FastAPI** convention; `dependencies.py` would be equivalent.

The transactional port and job repositories live in `application/persistence.py` (`UnitOfWork` type); the SQLAlchemy implementation is `infrastructure/sqlalchemy_unit_of_work.py` (`SqlAlchemyUnitOfWork`). In routes and use cases the instance is named `job_persistence` and the FastAPI provider is `get_job_persistence`.

## Worker

Same pattern: [`services/worker/src/hackathon_worker/presentation/deps.py`](../services/worker/src/hackathon_worker/presentation/deps.py) is the **only** file under `presentation/` that may import `hackathon_worker.infrastructure` (composition of `InternalApiClient`, Prometheus metrics, and the Prometheus scrape HTTP server). [`main.py`](../services/worker/src/hackathon_worker/main.py) orchestrates the loop (RabbitMQ, `httpx.AsyncClient`, message consumption) and wiring from `deps`, similar to how the API ties Uvicorn + `deps`.

Async processing (`execute_diagram_job`) depends on `WorkerInternalApiPort` (no `httpx` in the application layer) and `WorkerPipelineMetricsPort`. Prometheus **Counters** (`worker_state_transitions_total`, `diagram_jobs_processed_total`) are defined in `infrastructure/observability/metrics.py`; the port implementation that increments them is `infrastructure/observability/prometheus_worker_pipeline_metrics.py` (`PrometheusWorkerPipelineMetrics`), registered in `presentation/deps.py`.

## Summary rules

| Layer | May import `...infrastructure`? |
|-------|----------------------------------|
| `application/` | No |
| `domain/` | No |
| `presentation/*.py` (except empty `__init__.py`) | Only `deps.py` |
| `main.py` / `seed.py` | Yes (composition root) |
| `infrastructure/**` | Yes |

## Shared domain and contracts

- **`packages/contracts` (`hackathon_contracts`)** — integration kernel: queue payloads, internal completion/patch DTOs, `TechnicalReportV1`, and RabbitMQ topology constants (`messaging_topology`). Do not duplicate these DTOs in another package.
- **Per-service domain** — the API models `JobStatus` and persistence entities; the worker models a local FSM (`WorkerJobPhase`, etc.) for consumption. Do not merge into a generic `packages/hackathon-domain`: the concepts differ on purpose.
- **Infrastructure** (Prometheus, DB, broker) stays **per service**; there is no shared ORM/broker package. **`packages/platform` (`hackathon_platform`)** holds only minimal cross-cutting helpers (today: shared structlog `configure_logging`) to avoid duplication between API and worker.

## Local verification

```bash
bash scripts/check_layer_boundaries.sh
```

CI runs the same check along with `ruff` and `pytest` (see [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)).

## Contract and platform dependencies

You may import `hackathon_contracts` in application code — shared boundary DTOs, not a concrete framework implementation from another service. The `hackathon_platform` package is reserved for **small technical shared code** without business semantics (e.g. logging bootstrap); do not put DTOs or business rules there.
