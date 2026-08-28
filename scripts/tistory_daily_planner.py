#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import random
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "tistory_portfolio.json"
KST = ZoneInfo("Asia/Seoul")


def load_config(path: Path = CONFIG) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _daily_rng(site_id: str, day: str) -> random.Random:
    seed = int(hashlib.sha256(f"{site_id}:{day}".encode()).hexdigest()[:16], 16)
    return random.Random(seed)


def _pick_time(site: dict, day: str) -> str:
    start, end = site.get("daily_window", [8, 20])
    rng = _daily_rng(site["site_id"], day)
    hour = rng.randint(int(start), int(end))
    minute = rng.choice([7, 11, 17, 23, 29, 37, 43, 47, 53])
    return f"{hour:02d}:{minute:02d}"


def _pick_seed_topic(site: dict, day: str) -> str:
    topics = site.get("seed_topics") or []
    if not topics:
        return ""
    return _daily_rng(site["site_id"], day + ":topic").choice(topics)


def build_plan(now: datetime | None = None) -> dict:
    now = now or datetime.now(KST)
    cfg = load_config()
    day = now.date().isoformat()
    jobs = []
    for site in cfg["sites"]:
        jobs.append({
            "job_id": f"{site['site_id']}:{day}",
            "site_id": site["site_id"],
            "title": site["title"],
            "language": site["language"],
            "audience": site["audience"],
            "scheduled_local_time": _pick_time(site, day),
            "publish_policy": cfg.get("default_publish_policy", "awaiting_approval"),
            "duplicate_guard": True,
            "trend_mode": bool(site.get("trend_mode")),
            "official_source_required": bool(site.get("official_source_required")),
            "categories": site.get("categories", []),
            "intent": site.get("intent", []),
            "seed_topic": _pick_seed_topic(site, day),
            "status": "PLANNED",
            "public_allowed": False,
            "notes": "Generate an original article brief/content. Never copy another site. Queue for review; no automatic public publishing."
        })
    return {
        "generated_at": now.isoformat(),
        "date": day,
        "timezone": "Asia/Seoul",
        "daily_posts_per_site": 1,
        "public_allowed": False,
        "jobs": jobs,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/tistory-daily-plan.json")
    args = parser.parse_args()
    plan = build_plan()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"date": plan["date"], "jobs": len(plan["jobs"]), "public_allowed": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
