# Manual testing with curl (step by step)

**Prerequisites:** Docker and Docker Compose. The public API is behind **Traefik** at `http://localhost:8080`. Use the same `INTERNAL_TOKEN` for the API and worker (`.env` at the repo root, from `.env.example`).

**Security:** `/internal/...` must not be reachable on the **public** Traefik entrypoint. The internal entrypoint (`8081`) is not published on the host by default; for debugging, use the `docker-compose exec api` examples below.

---

## 1. Start the stack and check health

```bash
docker-compose up -d --build
```

Wait until Postgres, RabbitMQ, and the API are up (first run applies migrations on API startup).

```bash
curl -sS http://localhost:8080/health
```

Expected: JSON with `"status": "ok"`.

---

## 2. Create a client and save the Bearer token

The full token is printed **once** by the seed command:

```bash
docker-compose exec api python -m hackathon_api.seed
```

Copy the printed value and export it:

```bash
export TOKEN='<paste bearer here>'
```

---

## 3. Token balance

```bash
curl -sS -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/v1/clients/me/token-balance
```

---

## 4. Create an analysis job (upload)

Create a temporary test image (1×1 PNG) and upload it:

```bash
printf '%s' 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==' | base64 -d > /tmp/test-diagram.png
curl -sS -D /tmp/analysis-job-headers.txt \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/test-diagram.png" \
  http://localhost:8080/v1/analysis-jobs
```

You can replace `/tmp/test-diagram.png` with any real PNG, JPEG, or PDF path.

- Response body: JSON with `id` and `status` (typically `RECEIVED`).
- `Location` header: URL of the created resource.

Extract `JOB_ID` from headers (Linux/macOS with grep/sed):

```bash
export JOB_ID=$(grep -i '^Location:' /tmp/analysis-job-headers.txt | sed 's/.*analysis-jobs\///' | tr -d '\r\n ')
echo "$JOB_ID"
```

Alternative with JSON only (requires/jq):

```bash
export JOB_ID=$(curl -sS -H "Authorization: Bearer $TOKEN" -F "file=@/tmp/test-diagram.png" \
  http://localhost:8080/v1/analysis-jobs | jq -r .id)
echo "$JOB_ID"
```

---

## 5. Poll job status

Processing is **asynchronous** (queue + worker). Poll until `ANALYZED` or `ERROR`:

```bash
curl -sS -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/v1/analysis-jobs/$JOB_ID"
```

Repeat until the status changes.

---

## 6. Fetch the technical report (JSON)

When `status` is `ANALYZED`:

```bash
curl -sS -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/v1/analysis-jobs/$JOB_ID/report"
```

If the job is not finished yet, the API may return a conflict or “not ready” response; confirm step 5.

---

## 7. Internal routes (optional debugging)

The host usually has **no** port bound for `8081`. To hit the internal API **inside** the API container (Uvicorn on `8000`), set the same secret as in `.env`:

```bash
export INTERNAL_TOKEN='<same value as INTERNAL_TOKEN in .env>'
```

Example `PATCH` to `PROCESSING` (the host expands `JOB_ID` before the command runs in the container):

```bash
docker-compose exec api curl -sS -X PATCH \
  -H "Content-Type: application/json" \
  -H "X-Internal-Token: $INTERNAL_TOKEN" \
  -d '{"status":"PROCESSING"}' \
  "http://127.0.0.1:8000/internal/v1/analysis-jobs/$JOB_ID"
```

This is mainly for **debugging**; in normal operation the **worker** calls the internal API after consuming the queue.

---

## Variables (summary)

| Variable | Purpose |
|----------|---------|
| `TOKEN` | Client Bearer token (public API) |
| `JOB_ID` | Analysis job UUID |
| `INTERNAL_TOKEN` | `X-Internal-Token` header (`/internal/...`) |

Architecture and data flow: [architecture-and-data-flow.md](architecture-and-data-flow.md).
