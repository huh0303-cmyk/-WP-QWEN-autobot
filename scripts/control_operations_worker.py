"""VPS operations worker + London Project durable activity mirror/PM loop."""
import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from control_center.app import _operation_worker
from control_center import london_activity, london_orchestrator
from control_center.audit_engine import verify_web_publication


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


def _json(value, default):
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return default


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
    while True:
        try:
            for job in _operation_worker.store.snapshot():
                try:
                    _mirror_job(job)
                except Exception as exc:
                    # Mirror failures must never stop the publication receipt worker.
                    task_id = str(job.get("id", ""))
                    if task_id:
                        try:
                            london_activity.record_note(
                                task_id, actor="operations_mirror", event_type="MIRROR_ERROR",
                                detail={"error": str(exc)[:500]},
                            )
                        except Exception:
                            pass
        except Exception:
            pass
        time.sleep(5)


def _pm_loop():
    while True:
        task_id = ""
        try:
            task_id = london_orchestrator.next_work_task_id()
            if task_id:
                london_orchestrator.run_task(task_id)
        except Exception as exc:
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
    threading.Thread(target=_activity_mirror_loop, daemon=True, name="london-activity-mirror").start()
    threading.Thread(target=_pm_loop, daemon=True, name="london-pm-loop").start()
    _operation_worker.run()
