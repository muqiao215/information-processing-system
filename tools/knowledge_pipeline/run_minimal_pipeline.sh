#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ -n "${WORKSPACE_ROOT:-}" ]]; then
  WORKSPACE_ROOT="$WORKSPACE_ROOT"
elif [[ "$(basename "$(dirname "$REPO_ROOT")")" == "repos" ]]; then
  WORKSPACE_ROOT="$(dirname "$(dirname "$REPO_ROOT")")"
else
  WORKSPACE_ROOT="$(dirname "$REPO_ROOT")"
fi
OUTPUT_ROOT="${OUTPUT_ROOT:-$WORKSPACE_ROOT/output_to_user}"
BUILDERPULSE_ROOT="${BUILDERPULSE_ROOT:-$WORKSPACE_ROOT/vendor/BuilderPulse}"
BUNDLE_PATH="${BUNDLE_PATH:-/tmp/follow_builders_bundle.json}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
UV_BIN="${UV_BIN:-uv}"
ARXIV_PYTHON="${ARXIV_PYTHON:-}"

log() {
  printf '[pipeline] %s\n' "$*"
}

fail() {
  printf '[pipeline][error] %s\n' "$*" >&2
  exit 1
}

run_arxiv() {
  if [[ -n "$ARXIV_PYTHON" ]]; then
    "$ARXIV_PYTHON" "$REPO_ROOT/skills/arxiv-llm-memory-discovery/scripts/discover_llm_memory_paper.py"
    return
  fi

  if command -v "$UV_BIN" >/dev/null 2>&1; then
    "$UV_BIN" run --python 3.12 python \
      "$REPO_ROOT/skills/arxiv-llm-memory-discovery/scripts/discover_llm_memory_paper.py"
    return
  fi

  "$PYTHON_BIN" "$REPO_ROOT/skills/arxiv-llm-memory-discovery/scripts/discover_llm_memory_paper.py"
}

log "repo_root=$REPO_ROOT"
log "workspace_root=$WORKSPACE_ROOT"

mkdir -p "$OUTPUT_ROOT"

log "fetching follow-builders bundle"
"$PYTHON_BIN" "$REPO_ROOT/cron_tasks/ai-builders-digest-5briefs/scripts/fetch_follow_builders.py" > "$BUNDLE_PATH"

log "building AI builders digest outputs"
"$PYTHON_BIN" \
  "$REPO_ROOT/cron_tasks/ai-builders-digest-5briefs/scripts/build_digest_outputs.py" \
  --bundle-path "$BUNDLE_PATH"

if [[ ! -d "$BUILDERPULSE_ROOT/.git" ]]; then
  fail "BuilderPulse repo missing at $BUILDERPULSE_ROOT"
fi

log "refreshing BuilderPulse repo"
git -C "$BUILDERPULSE_ROOT" pull --ff-only || true

log "building BuilderPulse opportunity radar"
"$PYTHON_BIN" \
  "$REPO_ROOT/cron_tasks/daily-builderpulse-opportunity-radar/scripts/build_builderpulse_radar.py" \
  --repo-root "$BUILDERPULSE_ROOT"

log "discovering arXiv memory paper"
run_arxiv

log "building knowledge pack"
"$PYTHON_BIN" "$REPO_ROOT/tools/knowledge_pipeline/normalization/build_knowledge_pack.py"

log "done"
log "knowledge_pack_json=$OUTPUT_ROOT/knowledge_pack_latest.json"
log "knowledge_pack_md=$OUTPUT_ROOT/knowledge_pack_latest.md"
