"""VPS new-item detector. Polling a feed never implies publishing a quota."""
import hashlib
import html
import re
import json
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from pathlib import Path

NEWSROOM_COST_HOLD = Path("/etc/korea365/newsroom-cost-hold")

import requests

from .operations import Conflict


def parse_feed(text):
    root = ET.fromstring(text)
    if root.tag.split("}")[-1] not in {"rss", "feed", "RDF"}:
        raise ValueError("not an RSS or Atom feed")
    items = []
    for item in root.iter():
        if item.tag.split("}")[-1] not in {"item", "entry"}:
            continue
        children = {c.tag.split("}")[-1]: c for c in item}
        def value(name):
            node = children.get(name)
            return "" if node is None else "".join(node.itertext()).strip()
        link = children.get("link")
        url = (link.get("href") or value("link")) if link is not None else ""
        parsed = urlparse(url)
        if parsed.scheme not in {"https", "http"} or not parsed.hostname:
            continue
        date = value("pubDate") or value("published") or value("updated") or value("date")
        try:
            at = parsedate_to_datetime(date) if "," in date else datetime.fromisoformat(date.replace("Z", "+00:00"))
            at = at.replace(tzinfo=timezone.utc) if not at.tzinfo else at
            published = at.timestamp()
        except (ValueError, TypeError):
            published = None
        if value("title"):
            summary = value("description") or value("summary") or value("content")
            summary = re.sub(r"<[^>]+>", " ", summary)
            items.append({"title": value("title"), "url": url.split("#")[0], "published": published,
                          "summary": re.sub(r"\s+", " ", html.unescape(summary)).strip()[:5000]})
    return items


class RSSWatcher:
    def __init__(self, store, config_path, targets):
        self.store, self.targets = store, targets
        self.config = json.loads(config_path.read_text(encoding="utf-8"))
        with store.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS rss_feeds (key TEXT PRIMARY KEY, initialized INTEGER NOT NULL DEFAULT 0, checked REAL, error TEXT, etag TEXT, modified TEXT);
                CREATE TABLE IF NOT EXISTS rss_items (id TEXT PRIMARY KEY, newsroom TEXT NOT NULL, source TEXT NOT NULL, url TEXT NOT NULL, title TEXT NOT NULL, published REAL, detected REAL NOT NULL, state TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS rss_item_evidence (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            """)

    def ingest(self, source, items):
        now = time.time()
        key = "koreanews365" if source["language"] == "ko" else "theseouljournal"
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            feed = db.execute("SELECT initialized FROM rss_feeds WHERE key=?", (source["key"],)).fetchone()
            initialized = bool(feed and feed[0])
            for item in items:
                identity = hashlib.sha256((key + "|" + item["url"].rstrip("/")).encode()).hexdigest()
                # First successful read establishes a baseline, so starting a
                # new VPS cannot republish a backlog of old stories.
                state = "waiting" if initialized else "baseline"
                if item["published"] is not None and now - item["published"] > 72 * 3600:
                    state = "expired"
                db.execute("INSERT OR IGNORE INTO rss_items VALUES (?,?,?,?,?,?,?,?)", (identity, key, source["key"], item["url"], item["title"], item["published"], now, state))
                evidence = dict(item, source_key=source['key'], detected=now)
                db.execute("INSERT OR IGNORE INTO rss_item_evidence VALUES (?,?)", (identity, json.dumps(evidence, ensure_ascii=False)))
                db.execute("UPDATE rss_items SET state='waiting' WHERE id=? AND state='awaiting_source'", (identity,))
            db.execute("INSERT INTO rss_feeds(key,initialized,checked,error) VALUES (?,1,?,'') ON CONFLICT(key) DO UPDATE SET initialized=1,checked=excluded.checked,error=''", (source["key"], now))

    def scan(self):
        # Coordinate the monitor service and all web workers. A restart recovers
        # after lease expiry; insertion and request IDs are also idempotent.
        now = time.time()
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT value FROM settings WHERE key='rss_scan_lease'").fetchone()
            if row and float(row[0]) > now:
                return
            db.execute("INSERT INTO settings VALUES ('rss_scan_lease',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(now + 180),))
        for source in self.config["sources"]:
            try:
                response = requests.get(source["feed"], headers={"User-Agent":"Korea365 RSS Monitor/1.0"}, timeout=12)
                response.raise_for_status()
                self.ingest(source, parse_feed(response.text))
            except (requests.RequestException, ValueError, ET.ParseError):
                with self.store.connect() as db:
                    db.execute("INSERT INTO rss_feeds(key,checked,error) VALUES (?,?,?) ON CONFLICT(key) DO UPDATE SET checked=excluded.checked,error=excluded.error",
                               (source["key"], time.time(), "RSS 연결 또는 형식 확인 실패"))
        if NEWSROOM_COST_HOLD.exists():
            # Continue recording fresh RSS evidence while paid writing is held.
            # Do not repeatedly dispatch a disabled workflow and report 422s.
            with self.store.connect() as db:
                db.execute("UPDATE settings SET value=? WHERE key='rss_scan_lease'", (str(time.time() + self.config["poll_seconds"]),))
            return
        targets = {t["label"].split(".")[0]: t for t in self.targets()}
        with self.store.connect() as db:
            waiting = db.execute("SELECT * FROM rss_items WHERE state='waiting' ORDER BY CASE WHEN title LIKE '%속보%' OR title LIKE '%긴급%' OR title LIKE '%breaking%' THEN 0 ELSE 1 END, detected,published LIMIT 200").fetchall()
        for item in waiting:
            if item["newsroom"] not in targets:
                continue
            with self.store.connect() as db:
                evidence = db.execute("SELECT payload FROM rss_item_evidence WHERE id=?", (item['id'],)).fetchone()
                if not evidence:
                    db.execute("UPDATE rss_items SET state='awaiting_source' WHERE id=?", (item['id'],))
                    continue
                if item['published'] is None or not -600 <= time.time()-item['published'] <= 72*3600:
                    db.execute("UPDATE rss_items SET state='expired' WHERE id=?", (item['id'],))
                    continue
            descriptor = dict(targets[item["newsroom"]], source="rss", source_title=item["title"], source_url=item["url"])
            descriptor["inputs"] = dict(descriptor["inputs"], source_url=item["url"], source_item=evidence[0])
            try:
                self.store.submit("news2", [descriptor], "rss-" + item["id"])
            except Conflict:
                continue
            with self.store.connect() as db:
                db.execute("UPDATE rss_items SET state='accepted' WHERE id=?", (item["id"],))
        with self.store.connect() as db:
            db.execute("UPDATE settings SET value=? WHERE key='rss_scan_lease'", (str(time.time() + self.config["poll_seconds"]),))

    def status(self):
        with self.store.connect() as db:
            feeds = [dict(row) for row in db.execute("SELECT key,initialized,checked,error FROM rss_feeds")]
            waiting = db.execute("SELECT COUNT(*) FROM rss_items WHERE state='waiting'").fetchone()[0]
        names = {s["key"]:s["name"] for s in self.config["sources"]}
        for feed in feeds:
            feed["name"] = names.get(feed["key"],feed["key"])
        stale = any(not f["checked"] or time.time()-f["checked"] > 180 for f in feeds)
        failed = sum(bool(f["error"]) for f in feeds)
        message = "RSS 새 기사 감지 → 작성·검수·게시 · 일일 발행 횟수 제한 없음"
        if NEWSROOM_COST_HOLD.exists():
            message = "RSS 새 기사 감지 중 · 비용 중지로 작성·게시 대기"
        message += f" · 대기 기사 {waiting}건"
        if not feeds:
            message += " · 감시 시작 확인 대기"
        elif failed or stale:
            message += f" · 연결 실패 {failed}개" + (" · 감시 확인 지연" if stale else "")
        return {"message": message, "feeds": feeds, "waiting": waiting}
