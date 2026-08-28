from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path

DEFAULT_PLAN = Path("artifacts/automation-room-dispatch.json")
ALLOWED_PLATFORMS = {"wordpress", "blogger", "youtube", "tistory"}


def load_items(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw
    for key in ("dispatches", "selected", "items"):
        if isinstance(raw.get(key), list):
            return raw[key]
    return []


def choose_canaries(items: list[dict], platforms: set[str], limit_per_platform: int = 1) -> list[dict]:
    chosen: list[dict] = []
    counts: dict[str, int] = {}
    for item in items:
        platform = str(item.get("platform") or "")
        if platform not in platforms or counts.get(platform, 0) >= limit_per_platform:
            continue
        inputs = dict(item.get("inputs") or {})
        # Non-negotiable public safety guard.
        if "publication_approved" in inputs:
            inputs["publication_approved"] = False
        item = dict(item)
        item["inputs"] = inputs
        chosen.append(item)
        counts[platform] = counts.get(platform, 0) + 1
    return chosen


def dispatch(repo: str, item: dict, token: str) -> None:
    workflow = item["workflow"]
    payload = json.dumps({"ref": "main", "inputs": item.get("inputs") or {}}).encode()
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/actions/workflows/{workflow}/dispatches",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        if response.status not in (200, 201, 204):
            raise RuntimeError(f"dispatch failed: HTTP {response.status}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", default=str(DEFAULT_PLAN))
    parser.add_argument("--platforms", default="wordpress,blogger,youtube")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    platforms = {p.strip() for p in args.platforms.split(",") if p.strip()} & ALLOWED_PLATFORMS
    canaries = choose_canaries(load_items(Path(args.plan)), platforms)
    report = {"mode": "EXECUTE_CANARY" if args.execute else "DRY_RUN_CANARY", "public_allowed": False, "canaries": canaries}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not args.execute:
        return 0
    if os.getenv("CANARY_EXECUTION_APPROVED", "false").lower() != "true":
        raise SystemExit("CANARY_EXECUTION_APPROVED=true is required")
    token = os.environ.get("GH_DISPATCH_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repo:
        raise SystemExit("missing GH_DISPATCH_TOKEN or GITHUB_REPOSITORY")
    for item in canaries:
        dispatch(repo, item, token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
