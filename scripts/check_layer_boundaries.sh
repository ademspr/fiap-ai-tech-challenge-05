#!/usr/bin/env bash
# Fails if application/domain import infrastructure, or presentation imports infra outside deps.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PATTERN='hackathon_api\.infrastructure|hackathon_worker\.infrastructure'

fail() {
  echo "check_layer_boundaries: $*" >&2
  exit 1
}

check_dir_clean() {
  local label=$1
  shift
  local dir=$1
  if [[ ! -d "$dir" ]]; then
    return 0
  fi
  if grep -r -E --include='*.py' "$PATTERN" "$dir" >/dev/null 2>&1; then
    echo "--- $label (forbidden imports) ---" >&2
    grep -r -E -n --include='*.py' "$PATTERN" "$dir" >&2 || true
    fail "$label must not import infrastructure packages"
  fi
}

# API: application and domain never touch infrastructure
check_dir_clean "services/api application" "$ROOT/services/api/src/hackathon_api/application"
check_dir_clean "services/api domain" "$ROOT/services/api/src/hackathon_api/domain"

# API: only deps.py in presentation may wire infrastructure
PRES="${ROOT}/services/api/src/hackathon_api/presentation"
if [[ -d "$PRES" ]]; then
  while IFS= read -r -d '' f; do
    base=$(basename "$f")
    if [[ "$base" == "deps.py" ]]; then
      continue
    fi
    if [[ "$base" == "__init__.py" ]]; then
      continue
    fi
    if grep -E -q "$PATTERN" "$f" 2>/dev/null; then
      echo "--- presentation file (must not import infrastructure): $f ---" >&2
      grep -E -n "$PATTERN" "$f" >&2
      fail "presentation only deps.py may import hackathon_api.infrastructure"
    fi
  done < <(find "$PRES" -name '*.py' -print0 2>/dev/null)
fi

# Worker: application never touches infrastructure
check_dir_clean "services/worker application" "$ROOT/services/worker/src/hackathon_worker/application"

# Worker: domain
check_dir_clean "services/worker domain" "$ROOT/services/worker/src/hackathon_worker/domain"

# Worker: only deps.py in presentation may wire infrastructure
PRESW="${ROOT}/services/worker/src/hackathon_worker/presentation"
if [[ -d "$PRESW" ]]; then
  while IFS= read -r -d '' f; do
    base=$(basename "$f")
    if [[ "$base" == "deps.py" ]]; then
      continue
    fi
    if [[ "$base" == "__init__.py" ]]; then
      continue
    fi
    if grep -E -q "$PATTERN" "$f" 2>/dev/null; then
      echo "--- worker presentation (must not import infrastructure): $f ---" >&2
      grep -E -n "$PATTERN" "$f" >&2
      fail "worker presentation only deps.py may import hackathon_worker.infrastructure"
    fi
  done < <(find "$PRESW" -name '*.py' -print0 2>/dev/null)
fi

echo "Layer boundary checks passed."
