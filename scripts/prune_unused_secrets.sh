#!/usr/bin/env bash
# Delete GitHub repo secrets that no workflow references. Dry-run by default.
# Usage (on your PC, gh logged in with repo admin):  bash scripts/prune_unused_secrets.sh [--apply]
set -euo pipefail
R="${REPO:-huh0303-cmyk/-WP-QWEN-autobot}"
cd "$(dirname "$0")/.."
gh secret list -R "$R" --json name -q '.[].name' | sort > /tmp/have.txt
grep -rhoE "secrets\.[A-Za-z0-9_]+" .github | sed 's/secrets\.//' | sort -u > /tmp/used.txt
comm -23 /tmp/have.txt /tmp/used.txt > /tmp/unused.txt
echo "have=$(wc -l </tmp/have.txt) used=$(comm -12 /tmp/have.txt /tmp/used.txt | wc -l) unused=$(wc -l </tmp/unused.txt)"
cat /tmp/unused.txt
if [ "${1:-}" = "--apply" ]; then
  while read -r n; do [ -n "$n" ] && gh secret delete "$n" -R "$R" && echo "deleted $n"; done < /tmp/unused.txt
else
  echo "(dry-run: add --apply to delete)"
fi
