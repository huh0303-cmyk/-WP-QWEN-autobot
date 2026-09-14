"""Translate exact GitHub runs and publication receipts into operator states."""
import io
import json
import time
import zipfile
from urllib.parse import quote, urlparse

import requests


def public_url(value, site_url):
    try:
        parsed, site = urlparse(str(value)), urlparse(str(site_url))
        return (parsed.scheme == "https" and parsed.hostname == site.hostname
                and bool(parsed.path.strip("/")) and not parsed.username
                and not any(part in parsed.path.lower() for part in ("wp-admin", "manage/", "preview")))
    except ValueError:
        return False


def publication_receipt(files, job):
    """Only verified publisher records for this site/job qualify, never exit code 0."""
    for name, text in files.items():
        if name.endswith("newsroom_publish_result.json"):
            for row in json.loads(text).get("records", []):
                if (row.get("status") == "✅ OK" and row.get("site", "").rstrip("/") == job["site_url"].rstrip("/")
                        and public_url(row.get("url"), job["site_url"])):
                    return row["url"]
        if name.endswith("platform-worker.log"):
            for line in text.splitlines():
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if (isinstance(row, dict) and row.get("job_id") == job.get("publish_job_id")
                        and row.get("site_id") == job["site_id"] and row.get("ok") is True
                        and row.get("status") == "published" and public_url(row.get("public_url"), job["site_url"])):
                    return row["public_url"]
    return ""


def publication_wait(files, job):
    """A verified daily cap is a deferral, never a failed or published article."""
    for name, text in files.items():
        if not name.endswith("platform-worker.log"):
            continue
        for line in text.splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if (isinstance(row, dict) and job.get("publish_job_id")
                    and row.get("job_id") == job["publish_job_id"]
                    and row.get("site_id", job["site_id"]) == job["site_id"]
                    and row.get("status") == "waiting"
                    and row.get("reason") == "daily_limit_reached"):
                return True
    return False


class GitHubGateway:
    def __init__(self, repo, token, queue_rows):
        self.base = f"https://api.github.com/repos/{repo}"
        self.repo = repo
        self.headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2026-03-10"}
        self.queue_rows = queue_rows

    def get(self, path):
        response = requests.get(self.base + path, headers=self.headers, timeout=15)
        response.raise_for_status()
        return response.json()

    def dispatch(self, job):
        state = self.get(f"/actions/workflows/{job['workflow']}").get("state")
        if state in {"disabled_manually", "disabled_inactivity", "disabled_fork", "deleted"}:
            job.update(phase="stopped", detail="발행 작업이 일시 중지되어 있습니다. 비용·운영 중지 설정을 확인하세요. 글 작성이나 게시를 실행하지 않았습니다.", checked_at=time.time())
            return
        if state != "active":
            job.update(phase="attention", detail="발행 작업의 활성 상태를 확인하지 못했습니다. 실행하지 않았습니다.", checked_at=time.time())
            return
        response = requests.post(self.base + f"/actions/workflows/{job['workflow']}/dispatches",
                                 headers=self.headers, json={"ref": "main", "inputs": job["inputs"], "return_run_details": True}, timeout=30)
        if response.status_code in {400, 401, 403, 404, 422}:
            job.update(phase="failed", detail=f"실행 요청이 거부되었습니다 (HTTP {response.status_code}). 연결 설정을 확인하세요.")
            return
        if response.status_code != 200:
            job.update(phase="attention", detail="실행 요청의 접수 결과가 불확실합니다. 중복 요청은 보내지 않습니다.")
            return
        run_id = response.json().get("workflow_run_id")
        if not isinstance(run_id, int) or run_id <= 0:
            job.update(phase="attention", detail="정확한 실행 번호를 받지 못했습니다. 실행 기록 확인이 필요합니다.")
            return
        job.update(run_id=run_id, run_url=f"https://github.com/{self.repo}/actions/runs/{run_id}",
                   phase="queued", detail="실행 서버 접수 완료 · 순서 대기", checked_at=time.time())
        job.pop("connection_warning", None)

    def artifacts(self, run_id):
        listing = self.get(f"/actions/runs/{run_id}/artifacts?per_page=100")
        files = {}
        for artifact in listing.get("artifacts", []):
            if not artifact["name"].startswith(("blog-publish-result-", "newsroom-result-", "platform-publish-result-", "control-handoff-")):
                continue
            if artifact.get("expired") or artifact.get("size_in_bytes", 0) > 10_000_000:
                continue
            response = requests.get(self.base + f"/actions/artifacts/{int(artifact['id'])}/zip", headers=self.headers, timeout=20)
            response.raise_for_status()
            if len(response.content) > 10_000_000:
                raise ValueError("artifact too large")
            with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                for info in archive.infolist():
                    if info.file_size <= 2_000_000 and info.filename.endswith(("newsroom_publish_result.json", "platform-worker.log", "control-handoff.json")):
                        # Read in memory only. No archive paths are extracted.
                        files[info.filename] = archive.read(info).decode("utf-8", errors="replace")
        return files

    def poll_queue(self, job):
        exact_id = job.get("review_job_id") or job.get("publish_job_id")
        if not exact_id:
            return False
        row = next((r for r in self.queue_rows() if r.get("job_id") == exact_id and r.get("site_id") == job["site_id"]), None)
        if not row:
            return False
        status = row.get("status", "").strip().lower()
        if status == "published" and public_url(row.get("public_url"), job["site_url"]):
            job.update(phase="published", public_url=row["public_url"], detail="게시 기록과 공개 글 주소 확인", checked_at=time.time())
            return True
        if status == "processing":
            job.update(phase="publishing", detail="등록기가 해당 글의 게시를 처리 중", checked_at=time.time())
            return True
        if job["platform"] == "tistory" and status in {"ready", "drafted", "review_ready"} and row.get("title") and row.get("content_html"):
            job.update(phase="review_ready", detail="검토본 준비 완료 · 내용을 확인하고 승인하세요. 공개 게시 전입니다.",
                       review_url="/review/tistory/" + quote(exact_id, safe=":"), checked_at=time.time())
            return True
        if status in {"failed", "verification_failed", "auth_required"}:
            job.update(phase="attention", detail="등록 결과 확인 필요 · " + (row.get("error_code") or status), checked_at=time.time())
            return True
        return False

    def poll(self, job):
        if job.get("review_job_id"):
            if self.poll_queue(job):
                job.pop("connection_warning", None)
                return
        run = self.get(f"/actions/runs/{job['run_id']}")
        job.update(checked_at=time.time())
        job.pop("connection_warning", None)
        if run.get("head_sha") and job["platform"] in {"wordpress", "news"}:
            try:
                checks = self.get(f"/commits/{run['head_sha']}/check-runs?check_name=publication-progress-{job['run_id']}&per_page=100")
                matching = [c for c in checks.get("check_runs", []) if str(c.get("external_id")) == str(job["run_id"])]
                for check in sorted(matching, key=lambda c:c.get("id",0), reverse=True):
                    checkpoint = json.loads(check.get("output", {}).get("summary", "{}"))
                    if (str(checkpoint.get("run_id")) != str(job["run_id"]) or checkpoint.get("site_url", "").rstrip("/") != job["site_url"].rstrip("/")):
                        continue
                    phase = checkpoint.get("phase")
                    if phase == "published" and public_url(checkpoint.get("public_url"), job["site_url"]):
                        job.update(phase="published", public_url=checkpoint["public_url"], detail="공개 페이지 검증 완료", milestones=checkpoint.get("events", []))
                        return
                    if phase in {"working", "publishing"} and run.get("status") != "completed":
                        job.update(phase=phase, detail=checkpoint.get("detail", ""), milestones=checkpoint.get("events", []))
                        return
            except (requests.RequestException, ValueError, TypeError):
                # Existing runs may not have telemetry; fall back to observed
                # workflow steps without inventing a publication checkpoint.
                pass
        if run.get("status") != "completed":
            if run.get("status") in {"queued", "waiting", "pending", "requested"}:
                job.update(phase="queued" if not job.get("publish_job_id") else "publishing", detail="실행 서버에서 순서 대기")
            else:
                steps = self.get(f"/actions/runs/{job['run_id']}/jobs?per_page=100")
                names = [s["name"] for j in steps.get("jobs", []) for s in j.get("steps", []) if s.get("status") == "in_progress"]
                # WP/news combine authoring and publishing inside one step.
                # Do not invent a more precise stage than the worker exposes.
                job.update(phase="publishing" if job.get("publish_job_id") else "working",
                           detail=("공개 게시 처리 중" if job.get("publish_job_id") else "글 작성·검수·게시 작업 실행 중") + (" · " + ", ".join(names) if names else ""))
            return
        files = self.artifacts(job["run_id"])
        if publication_wait(files, job):
            job.update(phase="attention", detail="오늘 발행 한도 충족 · 이 추가 글은 다음 발행 차례를 기다립니다. 실패하거나 새로 게시된 글이 아닙니다.",
                       deferred_reason="daily_limit_reached")
            return
        receipt = publication_receipt(files, job)
        if receipt:
            job.update(phase="published", public_url=receipt, detail="게시 결과 확인 완료 · 공개 글을 확인하세요.")
            return
        if job["platform"] == "blogger" and not job.get("publish_job_id"):
            for name, text in files.items():
                if not name.endswith("control-handoff.json"):
                    continue
                handoff = json.loads(text)
                if (str(handoff.get("parent_run_id")) == str(job["run_id"]) and handoff.get("site_id") == job["site_id"]
                        and isinstance(handoff.get("workflow_run_id"), int) and handoff.get("job_id")):
                    job.update(parent_run_id=job["run_id"], run_id=handoff["workflow_run_id"], publish_job_id=handoff["job_id"],
                               run_url=f"https://github.com/{self.repo}/actions/runs/{handoff['workflow_run_id']}",
                               phase="publishing", detail="글 준비 완료 · 해당 글의 게시 작업으로 연결됨")
                    return
        if self.poll_queue(job):
            return
        conclusion = run.get("conclusion")
        if conclusion in {"cancelled", "timed_out"}:
            job.update(phase="stopped", detail="실행 서버에서 작업 중단 확인 · " + conclusion)
        elif conclusion in {"failure", "startup_failure", "action_required"}:
            steps = self.get(f"/actions/runs/{job['run_id']}/jobs?per_page=100")
            failures = [s["name"] for j in steps.get("jobs", []) for s in j.get("steps", []) if s.get("conclusion") == "failure"]
            job.update(phase="failed", detail="실행 실패 · " + (", ".join(failures) or conclusion))
            for name, text in files.items():
                if name.endswith("newsroom_publish_result.json"):
                    records = json.loads(text).get("records", [])
                    errors = [r.get("error") for r in records if r.get("site", "").rstrip("/") == job["site_url"].rstrip("/") and r.get("error")]
                    if errors:
                        job["detail"] += " · " + str(errors[-1])[:700]
        else:
            job.update(phase="attention", detail="실행은 종료됐지만 게시 결과를 확인하지 못했습니다. 완료로 처리하지 않고 다시 확인합니다.")
