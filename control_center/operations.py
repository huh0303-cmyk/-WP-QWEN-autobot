"""Durable, per-site operation receipts. Workflow success is not publication."""
from __future__ import annotations

import json
import os
import secrets
import sqlite3
import threading
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

LABELS = {
    "accepted": "요청 접수", "dispatching": "요청 접수", "queued": "요청 접수",
    "working": "작업 중", "review_ready": "검토 준비", "publishing": "게시 중",
    "published": "게시 완료", "stopped": "중단", "failed": "실패",
    "attention": "확인 필요",
}
TERMINAL = {"published", "stopped", "failed"}
# 2026-09-12: a job with no terminal outcome (most often 'attention', which
# nothing ever auto-clears) blocked that one site's conflict check forever -
# and inside a batch (wp25 / blogspot33 / tistory5), one such site aborted
# the ENTIRE batch's transaction before any of the other 32 got inserted.
# A job stuck this long is dead, not "in progress"; treat it as no longer
# active rather than let it block every future request for that site.
# Measured from `created`, not `updated`: an 'attention' job keeps getting
# reclaimed and re-polled by the worker (confirmed live - five real jobs
# stayed at "0.0h since last update" while sitting stuck for 20+ hours),
# so `updated` never ages and the staleness check never fired.
STALE_ACTIVE_JOB_SECONDS = 6 * 3600


class Conflict(Exception):
    pass


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, group_id TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, request_id TEXT NOT NULL, site_id TEXT NOT NULL,
                    group_id TEXT NOT NULL, phase TEXT NOT NULL, payload TEXT NOT NULL,
                    created REAL NOT NULL, updated REAL NOT NULL, lease REAL NOT NULL DEFAULT 0,
                    next_poll REAL NOT NULL DEFAULT 0);
                CREATE INDEX IF NOT EXISTS jobs_site ON jobs(site_id, created);
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY, job_id TEXT NOT NULL, at REAL NOT NULL,
                    phase TEXT NOT NULL, detail TEXT NOT NULL);
            """)
        os.chmod(self.path, 0o600)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        return db

    def secret(self, key):
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO settings VALUES (?, ?)", (key, secrets.token_urlsafe(48)))
            return db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()[0]

    def submit(self, group, descriptors, request_id):
        """Commit acceptance before responding. A single-site request still
        rejects cleanly if that one site has a live job. A multi-site batch
        never lets one blocked site abort the rest - it skips that site and
        accepts every other one, returning which (if any) were skipped."""
        now = time.time()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT group_id FROM requests WHERE id=?", (request_id,)).fetchone()
            if existing:
                if existing[0] != group:
                    raise Conflict("같은 요청 번호가 다른 그룹에서 사용되었습니다.")
                return request_id, []
            accepted, skipped = [], []
            for target in descriptors:
                active = db.execute(
                    "SELECT id FROM jobs WHERE site_id=? AND phase NOT IN ('published','stopped','failed') AND created>? LIMIT 1",
                    (target["site_id"], now - STALE_ACTIVE_JOB_SECONDS),
                ).fetchone()
                if active:
                    if len(descriptors) == 1:
                        raise Conflict(f"{target['label']}: 진행 중이거나 확인이 필요한 요청이 있습니다. 기존 작업 상태를 확인하세요.")
                    skipped.append(target["label"])
                    continue
                accepted.append(target)
            if not accepted:
                raise Conflict("모든 대상이 이미 진행 중이거나 확인이 필요합니다.")
            db.execute("INSERT INTO requests VALUES (?, ?)", (request_id, group))
            for target in accepted:
                job_id = secrets.token_hex(16)
                payload = dict(target, id=job_id, request_id=request_id, group=group,
                               phase="accepted", detail="통제실에 저장됨 · 실행 대기", run_id=None,
                               run_url="", public_url="", review_url="", checked_at=None)
                if target["platform"] == "tistory":
                    payload["inputs"] = dict(target["inputs"], run_key=job_id)
                    payload["review_job_id"] = target["site_id"] + ":" + job_id
                db.execute("INSERT INTO jobs (id, request_id, site_id, group_id, phase, payload, created, updated) VALUES (?,?,?,?,?,?,?,?)",
                           (job_id, request_id, target["site_id"], group, "accepted", json.dumps(payload, ensure_ascii=False), now, now))
                db.execute("INSERT INTO events(job_id,at,phase,detail) VALUES (?,?,?,?)", (job_id, now, "accepted", payload["detail"]))
        return request_id, skipped

    def snapshot(self):
        with self.connect() as db:
            # Latest request per site plus recent history. Old receipts remain stored.
            rows = db.execute("SELECT * FROM jobs WHERE phase NOT IN ('published','stopped','failed') OR id IN (SELECT id FROM jobs ORDER BY created DESC LIMIT 1500) ORDER BY created DESC").fetchall()
            result = []
            for row in rows:
                data = json.loads(row["payload"])
                data.pop("inputs", None)
                data.update(created_at=row["created"], updated_at=row["updated"], phase_label=LABELS[data["phase"]])
                data["history"] = [dict(event) for event in db.execute("SELECT at,phase,detail FROM events WHERE job_id=? ORDER BY id", (row["id"],))]
                result.append(data)
            return result

    def observe_run(self, descriptor, run):
        """Import scheduled work without dispatching anything or replacing manual work."""
        now = time.time()
        job_id = "github-" + str(run["id"])
        created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00")).timestamp()
        with self.connect() as db:
            if db.execute("SELECT id FROM jobs WHERE id=?", (job_id,)).fetchone():
                return
            payload = dict(descriptor, id=job_id, request_id=job_id, group="news2", phase="queued",
                           source="schedule", detail="RSS 자동 예약 실행 접수", run_id=run["id"], run_url=run.get("html_url", ""),
                           public_url="", review_url="", checked_at=None, scheduled_at=run.get("created_at"))
            db.execute("INSERT OR IGNORE INTO jobs (id,request_id,site_id,group_id,phase,payload,created,updated) VALUES (?,?,?,?,?,?,?,?)",
                       (job_id, job_id, descriptor["site_id"], "news2", "queued", json.dumps(payload, ensure_ascii=False), created, now))
            db.execute("INSERT INTO events(job_id,at,phase,detail) VALUES (?,?,?,?)", (job_id, now, "queued", payload["detail"]))

    def claim(self):
        now = time.time()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM jobs WHERE phase NOT IN ('published','stopped','failed') AND lease<? AND next_poll<=? ORDER BY next_poll,created LIMIT 1", (now, now)).fetchone()
            if row is None:
                return None
            data = json.loads(row["payload"])
            if data["phase"] == "accepted":
                # Record intent before the external side effect. A crash here is
                # ambiguous and must never blindly send the request a second time.
                data.update(phase="dispatching", detail="실행 서버에 요청 전달 중")
            db.execute("UPDATE jobs SET lease=?,phase=?,payload=? WHERE id=?", (now + 180, data["phase"], json.dumps(data, ensure_ascii=False), row["id"]))
            data["_new_dispatch"] = row["phase"] == "accepted"
            return data

    def save(self, data):
        data.pop("_new_dispatch", None)
        now = time.time()
        with self.connect() as db:
            old = db.execute("SELECT payload FROM jobs WHERE id=?", (data["id"],)).fetchone()
            previous = json.loads(old[0])
            if (previous["phase"], previous.get("detail")) != (data["phase"], data.get("detail")):
                db.execute("INSERT INTO events(job_id,at,phase,detail) VALUES (?,?,?,?)", (data["id"], now, data["phase"], data.get("detail", "")))
            delay = 60 if data["phase"] in {"review_ready", "attention"} else 15
            db.execute("UPDATE jobs SET phase=?,payload=?,updated=?,lease=0,next_poll=? WHERE id=?",
                       (data["phase"], json.dumps(data, ensure_ascii=False), now, now + delay, data["id"]))


class Worker:
    """One process-local poller; SQLite leases coordinate all gunicorn workers."""
    def __init__(self, store, gateway):
        self.store, self.gateway = store, gateway
        self.lock = threading.Lock()
        self.thread = None
        self.discover = lambda: None
        self.last_discovery = 0

    def start(self):
        with self.lock:
            if not self.thread or not self.thread.is_alive():
                self.thread = threading.Thread(target=self.run, daemon=True, name="publication-receipts")
                self.thread.start()

    def tick(self):
        data = self.store.claim()
        if not data:
            return
        try:
            if data.pop("_new_dispatch", False):
                self.gateway.dispatch(data)
            elif not data.get("run_id"):
                data.update(phase="attention", detail="요청 전달 결과를 확인하지 못했습니다. 중복 게시 방지를 위해 재실행을 보류했습니다.")
            else:
                self.gateway.poll(data)
        except Exception:
            # Never label an API timeout as a publication failure or leak tokens.
            data["connection_warning"] = "작업 서버 연결 지연 · 자동으로 다시 확인합니다."
        self.store.save(data)

    def run(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            discovery = None
            while True:
                if time.time() - self.last_discovery > 60 and (discovery is None or discovery.done()):
                    self.last_discovery = time.time()
                    discovery = pool.submit(self.discover)
                futures = [pool.submit(self.tick) for _ in range(4)]
                for future in futures:
                    try:
                        future.result()
                    except Exception:
                        # Durable leases recover after storage / process failures.
                        pass
                time.sleep(4)
