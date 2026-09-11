from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path

DEFAULT_PLAN = Path("artifacts/automation-room-dispatch.json")
ALLOWED_PLATFORMS = {"wordpress", "blogger", "youtube", "tistory"}
PUBLIC_TRUE_KEYS = {"publication_approved", "publish_now", "public", "is_public", "auto_publish"}


def load_items(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw
    for key in ("dispatches", "selected", "items"):
        if isinstance(raw.get(key), list):
            return raw[key]
    return []


def _truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "public", "publish"}


def _sanitize_inputs(platform: str, inputs: dict) -> dict:
    safe = dict(inputs)
    # Non-negotiable public safety guards.
    for key in PUBLIC_TRUE_KEYS:
        if key in safe:
            safe[key] = False
    # YouTube automation must never request a scheduled/public transition.
    if platform == "youtube":
        safe["publish_delay_hours"] = ""
        for key in ("publish_at", "publishAt", "privacy_status", "privacyStatus"):
            if key in safe:
                safe[key] = "private" if "privacy" in key.lower() else ""
    return safe


def _unsafe_payload(platform: str, inputs: dict) -> str:
    for key in PUBLIC_TRUE_KEYS:
        if key in inputs and _truthy(inputs[key]):
            return f"unsafe public input: {key}"
    if platform == "youtube":
        for key in ("publish_at", "publishAt"):
            if str(inputs.get(key, "")).strip():
                return f"youtube scheduled publication blocked: {key}"
        for key in ("privacy_status", "privacyStatus"):
            value = str(inputs.get(key, "")).strip().lower()
            if value and value != "private":
                return f"youtube privacy must be private: {key}={value}"
    return ""


def choose_canaries(items: list[dict], platforms: set[str], limit_per_platform: int = 1) -> list[dict]:
    chosen: list[dict] = []
    counts: dict[str, int] = {}
    for item in items:
        platform = str(item.get("platform") or "")
        if platform not in platforms or counts.get(platform, 0) >= limit_per_platform:
            continue
        publish_policy = str(item.get("publish_policy") or "")
        expected = {"wordpress": "draft", "blogger": "draft", "youtube": "private", "tistory": "awaiting_approval"}.get(platform)
        if expected and publish_policy != expected:
            continue
        inputs = _sanitize_inputs(platform, dict(item.get("inputs") or {}))
        if _unsafe_payload(platform, inputs):
            continue
        candidate = dict(item)
        candidate["inputs"] = inputs
        chosen.append(candidate)
        counts[platform] = counts.get(platform, 0) + 1
    return chosen


def dispatch(repo: str, item: dict, token: str) -> None:
    platform = str(item.get("platform") or "")
    inputs = _sanitize_inputs(platform, dict(item.get("inputs") or {}))
    unsafe = _unsafe_payload(platform, inputs)
    if unsafe:
        raise RuntimeError(unsafe)
    workflow = item["workflow"]
    ref = os.environ.get("GITHUB_REF_NAME", "main") or "main"
    payload = json.dumps({"ref": ref, "inputs": inputs}).encode()
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
