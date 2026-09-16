"""VPS operations worker + London Project durable activity mirror/PM loop."""
import json
import os
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from control_center.app import _operation_worker
from control_center import london_activity, london_orchestrator
from control_center.audit_engine import verify_web_publication

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_STATUS = Path(os.environ.get(
    "LONDON_RUNTIME_STATUS",
    ROOT / "data" / "london_project_runtime.json",
))
_RUNTIME_LOCK = threading.Lock()
_RUNTIME = {
    "project": "london-project",
    "process_started_at": time.time(),
    "operations_worker": "starting",
    "activity_mirror": "starting",
    "pm_loop": "starting",
    "activity_mirror_heartbeat": 0,
    "pm_loop_heartbeat": 0,
    "active_pm": "unknown",
    "last_pm_task_id": "",
    "provider_configured": {
        "openai": bool(os.environ.get("OPENAI_API_KEY", "").strip()),
        "anthropic": bool(os.environ.get("ANTHROPIC_API_KEY", "").strip()),
        "gemini": bool(os.environ.get("GEMINI_API_KEY", "").strip()),
    },
}


def _write_runtime(**updates):
    with _RUNTIME_LOCK:
        _RUNTIME.update(updates)
        _RUNTIME["written_at"] = time.time()
        RUNTIME_STATUS.parent.mkdir(parents=True, exist_ok=True)
        tmp = RUNTIME_STATUS.with_suffix(".tmp")
        tmp.write_text(json.dumps(_RUNTIME, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, RUNTIME_STATUS)


PHASE_STATE = {
    "accepted": "REQUESTED",
    "dispatching": "ASSIGNED",
    "queued": "ASSIGNED",
    "working": "RUNNING",
    "publishing": "RUNNING",
    "review_ready": "REVIEW_REQUIRED",
    "attention": "NEEDS_ATTENTION",
    "stopped": "CANCELLED",
    "failed": "FAILED",
}


def _audit_backfill_seconds():
    try:
        return max(0, int(os.environ.get("LONDON_LEDGER_BACKFILL_AUDIT_HOURS", "24"))) * 3600
    except ValueError:
        return 24 * 3600


def _ensure_task(job):
    task_id = str(job["id"])
    try:
        return london_activity.get_task(task_id)
    except KeyError:
        london_activity.create_task(
            f"{job.get('platform', 'publication')} · {job.get('label') or job.get('site_id') or task_id}",
            platform=str(job.get("platform", "")),
            target=str(job.get("site_url") or job.get("label") or ""),
            requested_by="operations",
            assigned_role="vps/github",
            acceptance_criteria=["external publication/review evidence must match this exact job"],
            payload={
                "pm_managed": False,
                "operation_job_id": task_id,
                "operation_request_id": job.get("request_id", ""),
                "group": job.get("group", ""),
            },
            correlation_id=str(job.get("request_id") or task_id),
            task_id=task_id,
        )
        return london_activity.get_task(task_id)


def _evidence(job):
    result = []
    for key in ("run_id", "run_url", "public_url", "review_url", "checked_at"):
        value = job.get(key)
        if value:
            result.append({"type": key, "value": value})
    return result


def _mirror_job(job):
    snapshot = _ensure_task(job)
    task = snapshot["task"]
    current = str(task["state"]).upper()
    if current == "VERIFIED_COMPLETE":
        return
    phase = str(job.get("phase", ""))

    if phase == "published":
        public_url = str(job.get("public_url", ""))
        site_url = str(job.get("site_url", ""))
        if not public_url or not site_url:
            if current != "NEEDS_ATTENTION":
                london_activity.transition(
                    str(job["id"]), "NEEDS_ATTENTION", actor="operations_mirror",
                    evidence=_evidence(job),
                    detail={"phase": phase, "reason": "published phase lacks public URL/site identity"},
                )
            return

        created_at = float(job.get("created_at") or 0)
        if created_at and time.time() - created_at > _audit_backfill_seconds():
            if current != "READY_FOR_AUDIT":
                london_activity.transition(
                    str(job["id"]), "READY_FOR_AUDIT", actor="operations_mirror",
                    evidence=_evidence(job),
                    detail={"phase": phase, "historical_backfill": True, "automatic_refetch": False},
                )
            return
        if current in {"REWORK_REQUIRED", "NEEDS_ATTENTION"}:
            return
        if current != "AUDITING":
            london_activity.transition(
                str(job["id"]), "AUDITING", actor="operations_mirror",
                evidence=_evidence(job), detail={"phase": phase},
            )
        audit = verify_web_publication(public_url, site_url)
        london_activity.record_audit_result(
            str(job["id"]),
            passed=audit.verified,
            evidence=[audit.evidence],
            detail={"reason": audit.reason, "platform": audit.platform, "target": audit.target},
        )
        return

    desired = PHASE_STATE.get(phase)
    if not desired or desired == current:
        return
    london_activity.transition(
        str(job["id"]), desired, actor="operations_mirror",
        evidence=_evidence(job),
        detail={"operation_phase": phase, "detail": job.get("detail", "")},
        error=str(job.get("connection_warning", "")) if desired in {"NEEDS_ATTENTION", "FAILED"} else "",
    )


def _activity_mirror_loop():
    _write_runtime(activity_mirror="active", activity_mirror_heartbeat=time.time())
    while True:
        try:
            for job in _operation_worker.store.snapshot():
                try:
                    _mirror_job(job)
                except Exception as exc:
                    task_id = str(job.get("id", ""))
                    if task_id:
                        try:
                            london_activity.record_note(
                                task_id, actor="operations_mirror", event_type="MIRROR_ERROR",
                                detail={"error": str(exc)[:500]},
                            )
                        except Exception:
                            pass
            _write_runtime(activity_mirror="active", activity_mirror_heartbeat=time.time())
        except Exception as exc:
            _write_runtime(activity_mirror="degraded", activity_mirror_heartbeat=time.time(),
                           activity_mirror_error=str(exc)[:300])
        time.sleep(5)


def _pm_loop():
    _write_runtime(pm_loop="active", pm_loop_heartbeat=time.time())
    while True:
        task_id = ""
        try:
            status = london_orchestrator.status()
            active_pm = str(status.get("runtime", {}).get("active_pm", "unknown"))
            task_id = london_orchestrator.next_work_task_id()
            _write_runtime(pm_loop="active", pm_loop_heartbeat=time.time(),
                           active_pm=active_pm, last_pm_task_id=task_id)
            if task_id:
                london_orchestrator.run_task(task_id)
        except Exception as exc:
            _write_runtime(pm_loop="degraded", pm_loop_heartbeat=time.time(),
                           last_pm_task_id=task_id, pm_loop_error=str(exc)[:300])
            if task_id:
                try:
                    london_activity.record_note(
                        task_id, actor="london_pm_worker", event_type="PM_LOOP_ERROR",
                        detail={"error": str(exc)[:500]},
                    )
                except Exception:
                    pass
        time.sleep(5 if not task_id else 1)


if __name__ == "__main__":
    _write_runtime(operations_worker="active")
    threading.Thread(target=_activity_mirror_loop, daemon=True, name="london-activity-mirror").start()
    threading.Thread(target=_pm_loop, daemon=True, name="london-pm-loop").start()
    _operation_worker.run()
