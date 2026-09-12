"""Public, unauthenticated daily+total visit counter for Blogger sites.

Blogger has no server-side code of its own (unlike WordPress's
daily_visitor_counter.php Code Snippet), so the counting has to happen here
and be read back in by a small script embedded in each Blogger post."""
import os
import re
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

from flask import jsonify, request

BOT_RE = re.compile(r'bot|crawl|spider|slurp|bingpreview|facebookexternalhit|pingdom|uptime|ahrefs|semrush|mj12', re.I)
KST = timezone(timedelta(hours=9))
SITE_KEY_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def _today():
    return datetime.now(KST).strftime('%Y-%m-%d')


def _connect(path):
    conn = sqlite3.connect(path, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS daily (site_key TEXT NOT NULL, date TEXT NOT NULL, count INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(site_key, date));
        CREATE TABLE IF NOT EXISTS total (site_key TEXT PRIMARY KEY, count INTEGER NOT NULL DEFAULT 0);
    """)
    return conn


def install(module):
    app = module.app
    root = Path(module.__file__).resolve().parents[1]
    db_path = os.environ.get("BLOG_VISITOR_DB", str(root / "data/blog-visitor-counts.sqlite3"))
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def read_counts(site_key):
        with _connect(db_path) as conn:
            today = _today()
            day = conn.execute("SELECT count FROM daily WHERE site_key=? AND date=?", (site_key, today)).fetchone()
            total = conn.execute("SELECT count FROM total WHERE site_key=?", (site_key,)).fetchone()
            return (day["count"] if day else 0), (total["count"] if total else 0)

    def increment_counts(site_key):
        with _connect(db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            today = _today()
            conn.execute(
                "INSERT INTO daily(site_key,date,count) VALUES(?,?,1) "
                "ON CONFLICT(site_key,date) DO UPDATE SET count=count+1", (site_key, today))
            conn.execute(
                "INSERT INTO total(site_key,count) VALUES(?,1) "
                "ON CONFLICT(site_key) DO UPDATE SET count=count+1", (site_key,))
            day = conn.execute("SELECT count FROM daily WHERE site_key=? AND date=?", (site_key, today)).fetchone()["count"]
            total = conn.execute("SELECT count FROM total WHERE site_key=?", (site_key,)).fetchone()["count"]
            return day, total

    def with_cors(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.route("/api/blog-visits/<site_key>", methods=["GET", "POST", "OPTIONS"])
    def blog_visits(site_key):
        if not SITE_KEY_RE.match(site_key):
            return with_cors(jsonify({"error": "invalid site_key"})), 400
        if request.method == "OPTIONS":
            return with_cors(jsonify({}))
        if request.method == "GET":
            today, total = read_counts(site_key)
            return with_cors(jsonify({"today": today, "total": total, "counted": False}))
        ua = request.headers.get("User-Agent", "")
        if not ua or BOT_RE.search(ua):
            today, total = read_counts(site_key)
            return with_cors(jsonify({"today": today, "total": total, "counted": False}))
        today, total = increment_counts(site_key)
        return with_cors(jsonify({"today": today, "total": total, "counted": True}))
