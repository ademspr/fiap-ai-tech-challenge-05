#!/usr/bin/env bash
# Brings up the full Compose stack, checks HTTP health, and verifies Loki has streams
# for api and worker logs. Run from repo root: bash scripts/integration_compose_observability.sh
# Requires: docker-compose, curl, jq. Linux is the reference environment for Promtail+Loki.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

cleanup() {
  local exit_code=$?
  if [[ "${KEEP_COMPOSE_UP:-}" != "1" ]]; then
    docker-compose down -v --remove-orphans || true
  fi
  exit "$exit_code"
}
trap cleanup EXIT

wait_for_http() {
  local url=$1
  local name=$2
  local max_attempts=${3:-45}
  local i=0
  while ! curl -fsS "$url" >/dev/null 2>&1; do
    i=$((i + 1))
    if [[ "$i" -ge "$max_attempts" ]]; then
      echo "integration_compose_observability: timeout waiting for $name ($url)" >&2
      docker-compose ps >&2 || true
      exit 1
    fi
    sleep 2
  done
  echo "OK: $name"
}

loki_query_range() {
  local query=$1
  local end_ns start_ns
  end_ns=$(($(date +%s) * 1000000000))
  start_ns=$((end_ns - 900000000000))
  curl -fsS -G "http://127.0.0.1:3100/loki/api/v1/query_range" \
    --data-urlencode "query=${query}" \
    --data-urlencode "limit=100" \
    --data-urlencode "start=${start_ns}" \
    --data-urlencode "end=${end_ns}"
}

assert_loki_nonempty() {
  local query=$1
  local label=$2
  local body
  body=$(loki_query_range "$query")
  if echo "$body" | jq -e '.data.result | length > 0' >/dev/null 2>&1; then
    echo "Loki OK: $label ($(echo "$body" | jq '.data.result | length')) stream(s)"
    return 0
  fi
  echo "Loki: empty result for $label (query=$query)" >&2
  echo "$body" | head -c 4000 >&2 || true
  return 1
}

echo "Starting full stack (build)..."
docker-compose up -d --build

echo "Waiting for HTTP readiness..."
wait_for_http "http://127.0.0.1:8080/health" "traefik-public-health" 40
wait_for_http "http://127.0.0.1:3100/ready" "loki-ready" 40
wait_for_http "http://127.0.0.1:3000/api/health" "grafana-health" 50

echo "Generating traffic / logs..."
for _ in $(seq 1 15); do
  curl -fsS "http://127.0.0.1:8080/health" >/dev/null || true
done

echo "Waiting for Promtail → Loki (retry query)..."
ok_api=0
ok_worker=0
for attempt in $(seq 1 12); do
  sleep 10
  body=$(loki_query_range '{compose_service="api"}')
  if echo "$body" | jq -e '.data.result | length > 0' >/dev/null 2>&1; then
    ok_api=1
  fi
  body_w=$(loki_query_range '{compose_service="worker"}')
  if echo "$body_w" | jq -e '.data.result | length > 0' >/dev/null 2>&1; then
    ok_worker=1
  fi
  if [[ "$ok_api" -eq 1 && "$ok_worker" -eq 1 ]]; then
    echo "Loki OK: api + worker streams (after ${attempt} attempt(s))"
    break
  fi
  echo "  attempt $attempt: api=$ok_api worker=$ok_worker"
done

if [[ "$ok_api" -ne 1 ]]; then
  if ! assert_loki_nonempty '{container=~".*api.*"}' 'container regex api (fallback)'; then
    exit 1
  fi
fi

if [[ "$ok_worker" -ne 1 ]]; then
  echo "integration_compose_observability: worker logs missing in Loki" >&2
  exit 1
fi

echo "integration_compose_observability: all checks passed."
