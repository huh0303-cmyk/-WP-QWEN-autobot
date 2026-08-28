from __future__ import annotations

import argparse
import json
import os
import urllib.request
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


def collect(repo: str, token: str, per_workflow: int = 5) -> dict:
    registry = RoomRegistry.load()
    workflows = sorted({r.workflow for r in registry.rooms if r.workflow})
    latest_by_workflow: dict[str, dict] = {}
    for workflow in workflows:
        payload = _request(
            f"{API}/repos/{repo}/actions/workflows/{workflow}/runs?event=workflow_dispatch&per_page={per_workflow}",
            token,
        )
        runs = payload.get("workflow_runs") or []
        if runs:
            latest_by_workflow[workflow] = runs[0]

    rows = []
    for room in registry.rooms:
        run = latest_by_workflow.get(room.workflow)
        if not run:
            status = "EMPTY" if not room.enabled and room.status == "EMPTY" else ("PAUSED" if not room.enabled else "READY")
            rows.append(
                make_status(
                    room_id=room.room_id,
                    platform=room.platform,
                    status=status,
                    workflow=room.workflow,
                    publish_policy=room.publish_policy,
                    next_run=room.next_run,
                    details={"name": room.name, "result_source": "none"},
                ).to_dict()
            )
            continue
        rows.append(
            make_status(
                room_id=room.room_id,
                platform=room.platform,
                status=_status(run),
                workflow=room.workflow,
                run_id=str(run.get("id") or ""),
                started_at=run.get("run_started_at") or run.get("created_at") or "",
                completed_at=run.get("updated_at") or "",
                artifact_url=run.get("html_url") or "",
                publish_policy=room.publish_policy,
                failure_reason=(run.get("conclusion") or "") if _status(run) == "FAILED" else "",
                next_run=room.next_run,
                details={
                    "name": room.name,
                    "result_source": "github_actions",
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
        "summary": {"total": len(rows), "by_status": counts},
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
