"""Best-effort live checkpoints; a telemetry outage must not repeat publication."""
import json
import os
import time

import requests

_check_id = None
_events = []


def report(phase, site_url, *, public_url="", detail="", site_id="", job_id=""):
    global _check_id
    token = os.environ.get("GH_TOKEN", "")
    repo, run_id, sha = (os.environ.get(key, "") for key in ("GITHUB_REPOSITORY", "GITHUB_RUN_ID", "GITHUB_SHA"))
    if not all((token, repo, run_id, sha)):
        return
    event = dict(phase=phase, site_url=site_url, public_url=public_url, detail=detail,
                 site_id=site_id, job_id=job_id, run_id=run_id, at=time.time())
    _events.append(event)
    headers = {"Authorization":f"Bearer {token}","Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2026-03-10"}
    payload = {"name":f"publication-progress-{run_id}", "output":{"title":phase,"summary":json.dumps(dict(event, events=_events[-20:]),ensure_ascii=False)},
               "status":"completed" if phase in {"published","failed"} else "in_progress"}
    if payload["status"] == "completed":
        payload["conclusion"] = "success" if phase == "published" else "failure"
    try:
        if _check_id is None:
            payload.update(head_sha=sha,external_id=run_id)
            response=requests.post(f"https://api.github.com/repos/{repo}/check-runs",headers=headers,json=payload,timeout=5)
            response.raise_for_status()
            _check_id=response.json()["id"]
        else:
            response=requests.patch(f"https://api.github.com/repos/{repo}/check-runs/{_check_id}",headers=headers,json=payload,timeout=5)
            response.raise_for_status()
    except (requests.RequestException, ValueError, KeyError):
        print("Publication checkpoint delivery delayed; the publication itself is not retried.")
