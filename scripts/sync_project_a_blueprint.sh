#!/usr/bin/env bash
set -euo pipefail

ROOT="${PROJECT_A_REPO_ROOT:-/opt/korea365}"
DOC_SRC="$ROOT/docs/PROJECT_A_BLUEPRINT.md"
POLICY_SRC="$ROOT/config/project_a_blueprint.json"
DOC_DST="${PROJECT_A_VPS_BLUEPRINT:-/opt/korea365/docs/PROJECT_A_BLUEPRINT.md}"
POLICY_DST="${PROJECT_A_VPS_POLICY:-/opt/korea365/config/project_a_blueprint.json}"
RECEIPT="${PROJECT_A_VPS_RECEIPT:-/opt/korea365/data/project_a_blueprint_version.json}"

for source in "$DOC_SRC" "$POLICY_SRC"; do
  if [[ ! -f "$source" ]]; then
    echo "missing Project A source: $source" >&2
    exit 2
  fi
done

mkdir -p "$(dirname "$DOC_DST")" "$(dirname "$POLICY_DST")" "$(dirname "$RECEIPT")"

install -m 0644 "$DOC_SRC" "$DOC_DST"
install -m 0644 "$POLICY_SRC" "$POLICY_DST"

GIT_SHA="unknown"
if command -v git >/dev/null 2>&1 && git -C "$ROOT" rev-parse HEAD >/dev/null 2>&1; then
  GIT_SHA="$(git -C "$ROOT" rev-parse HEAD)"
fi

DOC_SHA256="$(sha256sum "$DOC_DST" | awk '{print $1}')"
POLICY_SHA256="$(sha256sum "$POLICY_DST" | awk '{print $1}')"
SYNCED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

TMP="${RECEIPT}.tmp"
cat > "$TMP" <<JSON
{
  "project": "Project A",
  "git_sha": "$GIT_SHA",
  "synced_at_utc": "$SYNCED_AT",
  "blueprint_path": "$DOC_DST",
  "blueprint_sha256": "$DOC_SHA256",
  "policy_path": "$POLICY_DST",
  "policy_sha256": "$POLICY_SHA256"
}
JSON
mv "$TMP" "$RECEIPT"
chmod 0644 "$RECEIPT"

echo "Project A blueprint synced: git=$GIT_SHA receipt=$RECEIPT"
