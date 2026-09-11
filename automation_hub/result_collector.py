from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .rooms import RoomRegistry
from .status_schema import make_status

API = "https://api.github.com"


def _request(url: str, token: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _status(run: dict) -> str:
    state = str(run.get("status") or "").lower()
    conclusion = str(run.get("conclusion") or "").lower()
    if state in {"queued", "waiting", "requested", "pending"}:
        return "DISPATCHED"
    if state == "in_progress":
        return "RUNNING"
    if conclusion == "success":
        return "SUCCESS"
    if conclusion in {"failure", "cancelled", "timed_out", "startup_failure"}:
        return "FAILED"
    return "READY"


def _room_tokens(room) -> set[str]:
    values = {
        room.room_id,
        room.name,
        room.source_id,
        room.account_id,
        room.destination_id,
    }
    tokens: set[str] = set()
    for value in values:
        raw = str(value or "").strip().lower()
        if not raw:
            continue
        tokens.add(raw)
        if raw.startswith("http://") or raw.startswith("https://"):
            host = urllib.parse.urlparse(raw).netloc.lower().removeprefix("www.")
            if host:
                tokens.add(host)
        elif "." in raw and "/" not in raw:
            tokens.add(raw.removeprefix("www."))
    return {t for t in tokens if len(t) >= 4}


def _run_text(run: dict) -> str:
    return " ".join(
        str(run.get(key) or "").lower()
        for key in ("name", "display_title", "head_branch", "path")
    )


def _match_run(room, runs: list[dict], workflow_room_count: int) -> tuple[dict | None, str]:
    if not runs:
        return None, "none"
    if workflow_room_count == 1:
        return runs[0], "unique_workflow"
    tokens = _room_tokens(room)
    for run in runs:
        text = _run_text(run)
        if any(token in text for token in tokens):
            return run, "run_metadata_match"
    return None, "shared_workflow_unattributed"


def collect(repo: str, token: str, per_workflow: int = 10) -> dict:
    registry = RoomRegistry.load()
    workflow_counts = Counter(r.workflow for r in registry.rooms if r.workflow)
    workflows = sorted(workflow_counts)
    runs_by_workflow: dict[str, list[dict]] = {}
    for workflow in workflows:
        payload = _request(
            f"{API}/repos/{repo}/actions/workflows/{workflow}/runs?event=workflow_dispatch&per_page={per_workflow}",
            token,
        )
        runs_by_workflow[workflow] = payload.get("workflow_runs") or []

    rows = []
    unattributed_shared = 0
    for room in registry.rooms:
        runs = runs_by_workflow.get(room.workflow) or []
        run, match_method = _match_run(room, runs, workflow_counts.get(room.workflow, 0))
        if not run:
            if match_method == "shared_workflow_unattributed" and runs:
                unattributed_shared += 1
            status = "EMPTY" if not room.enabled and room.status == "EMPTY" else ("PAUSED" if not room.enabled else "READY")
            details = {"name": room.name, "result_source": match_method}
            if runs:
                details["latest_workflow_run_id"] = str(runs[0].get("id") or "")
                details["latest_workflow_run_url"] = runs[0].get("html_url") or ""
                details["note"] = "Shared workflow run exists but was not safely attributable to this room."
            rows.append(
                make_status(
                    room_id=room.room_id,
                    platform=room.platform,
                    status=status,
                    workflow=room.workflow,
                    publish_policy=room.publish_policy,
                    next_run=room.next_run,
                    details=details,
                ).to_dict()
            )
            continue

        mapped_status = _status(run)
        rows.append(
            make_status(
                room_id=room.room_id,
                platform=room.platform,
                status=mapped_status,
                workflow=room.workflow,
                run_id=str(run.get("id") or ""),
                started_at=run.get("run_started_at") or run.get("created_at") or "",
                completed_at=run.get("updated_at") or "",
                artifact_url=run.get("html_url") or "",
                publish_policy=room.publish_policy,
                failure_reason=(run.get("conclusion") or "") if mapped_status == "FAILED" else "",
                next_run=room.next_run,
                details={
                    "name": room.name,
                    "result_source": "github_actions",
                    "match_method": match_method,
                    "event": run.get("event") or "",
                    "run_number": run.get("run_number") or "",
                },
            ).to_dict()
        )

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total": len(rows),
            "by_status": counts,
            "shared_workflow_unattributed_rooms": unattributed_shared,
        },
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/automation-room-results.json")
    args = parser.parse_args()
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    token = os.environ.get("GH_RESULTS_TOKEN", "").strip() or os.environ.get("GITHUB_TOKEN", "").strip()
    if not repo or not token:
        raise SystemExit("GITHUB_REPOSITORY and GH_RESULTS_TOKEN/GITHUB_TOKEN are required")
    payload = collect(repo, token)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False))
    print(f"RESULTS_WRITTEN={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
