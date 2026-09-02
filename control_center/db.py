from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .states import CREATED, require_transition


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / ".local" / "control_center" / "control_center.sqlite3"
_LOCK = threading.RLock()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or os.environ.get("CONTROL_CENTER_DB", DEFAULT_DB))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.migrate()

    @contextmanager
    def connect(self, *, immediate: bool = False) -> Iterator[sqlite3.Connection]:
        with _LOCK:
            con = sqlite3.connect(self.path, timeout=30, isolation_level=None)
            con.row_factory = sqlite3.Row
            con.execute("PRAGMA foreign_keys=ON")
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
            try:
                yield con
                con.commit()
            except Exception:
                con.rollback()
                raise
            finally:
                con.close()

    def migrate(self) -> None:
        with self.connect(immediate=True) as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    site_id TEXT NOT NULL,
                    keyword TEXT NOT NULL,
                    text_model TEXT NOT NULL DEFAULT 'gemini-2.5-flash',
                    image_model TEXT NOT NULL DEFAULT 'black-forest-labs/flux-schnell',
                    state TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    meta_description TEXT NOT NULL DEFAULT '',
                    content_html TEXT NOT NULL DEFAULT '',
                    labels_json TEXT NOT NULL DEFAULT '[]',
                    image_queries_json TEXT NOT NULL DEFAULT '[]',
                    quality_score INTEGER,
                    quality_failures_json TEXT NOT NULL DEFAULT '[]',
                    wp_post_id TEXT NOT NULL DEFAULT '',
                    wp_edit_url TEXT NOT NULL DEFAULT '',
                    wp_preview_url TEXT NOT NULL DEFAULT '',
                    error TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    detail_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(job_id) REFERENCES jobs(id)
                );
                CREATE INDEX IF NOT EXISTS idx_jobs_state ON jobs(state);
                CREATE INDEX IF NOT EXISTS idx_events_job ON events(job_id, id);
            """)
            columns = {row["name"] for row in con.execute("PRAGMA table_info(jobs)").fetchall()}
            if "text_model" not in columns:
                con.execute("ALTER TABLE jobs ADD COLUMN text_model TEXT NOT NULL DEFAULT 'gemini-2.5-flash'")
            if "image_model" not in columns:
                con.execute("ALTER TABLE jobs ADD COLUMN image_model TEXT NOT NULL DEFAULT 'black-forest-labs/flux-schnell'")

    def create_job(self, *, site_id: str, keyword: str, text_model: str = "gemini-2.5-flash", image_model: str = "black-forest-labs/flux-schnell") -> dict[str, Any]:
        normalized = " ".join(keyword.lower().split())
        key = f"wordpress:{site_id}:{normalized}:{text_model}:{image_model}:v2"
        stamp = now_iso()
        with self.connect(immediate=True) as con:
            existing = con.execute("SELECT * FROM jobs WHERE idempotency_key=?", (key,)).fetchone()
            if existing:
                return self._decode(existing)
            job_id = f"wp-{uuid.uuid4().hex[:16]}"
            con.execute(
                "INSERT INTO jobs(id,idempotency_key,site_id,keyword,text_model,image_model,state,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (job_id, key, site_id, keyword.strip(), text_model, image_model, CREATED, stamp, stamp),
            )
            self._event(con, job_id, "JOB_CREATED", {"site_id": site_id, "keyword": keyword.strip()})
            return self._decode(con.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone())

    def transition(self, job_id: str, target: str, **fields: Any) -> dict[str, Any]:
        with self.connect(immediate=True) as con:
            row = con.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if not row:
                raise KeyError(job_id)
            require_transition(row["state"], target)
            allowed = {
                "title", "meta_description", "content_html", "labels_json",
                "image_queries_json", "quality_score", "quality_failures_json",
                "wp_post_id", "wp_edit_url", "wp_preview_url", "error",
            }
            unsafe = set(fields) - allowed
            if unsafe:
                raise ValueError(f"unsupported fields: {sorted(unsafe)}")
            values = {**fields, "state": target, "updated_at": now_iso()}
            sql = ",".join(f"{name}=?" for name in values)
            con.execute(f"UPDATE jobs SET {sql} WHERE id=?", (*values.values(), job_id))
            self._event(con, job_id, "STATE_CHANGED", {"from": row["state"], "to": target})
            return self._decode(con.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone())

    def get(self, job_id: str) -> dict[str, Any]:
        with self.connect() as con:
            row = con.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if not row:
                raise KeyError(job_id)
            return self._decode(row)

    def list_jobs(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as con:
            return [self._decode(row) for row in con.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()]

    @staticmethod
    def _event(con: sqlite3.Connection, job_id: str, event_type: str, detail: dict[str, Any]) -> None:
        con.execute(
            "INSERT INTO events(job_id,event_type,detail_json,created_at) VALUES(?,?,?,?)",
            (job_id, event_type, json.dumps(detail, ensure_ascii=False), now_iso()),
        )

    @staticmethod
    def _decode(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        for source, target in (
            ("labels_json", "labels"),
            ("image_queries_json", "image_queries"),
            ("quality_failures_json", "quality_failures"),
        ):
            try:
                item[target] = json.loads(item.get(source) or "[]")
            except json.JSONDecodeError:
                item[target] = []
        return item
