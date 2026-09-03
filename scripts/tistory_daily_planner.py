#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import random
import os
import re
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


def _golden_keyword_score(topic: str, site: dict) -> tuple[int, dict[str, int]]:
    """Deterministic common keyword gate; never pick a topic at random."""
    low = topic.lower()
    intents = [str(x).lower() for x in site.get("intent", [])]
    categories = [str(x).lower() for x in site.get("categories", [])]
    freshness_words = ("오늘", "신청", "기간", "지급", "시간표", "예매", "deadline", "schedule", "booking")
    value_words = ("비용", "보험", "대출", "금리", "청구", "예약", "cost", "hotel", "booking")
    breakdown = {
        "search_intent": min(35, 15 + 10 * sum(word in low for word in intents)),
        "site_fit": min(25, 15 + 5 * sum(word in low for word in categories)),
        "freshness": 20 if any(word in low for word in freshness_words) else 8,
        "value": 10 if any(word in low for word in value_words) else 5,
        "specificity": 10 if len(topic.replace(" ", "")) >= 14 else 6,
    }
    return sum(breakdown.values()), breakdown


def _pick_seed_topic(site: dict, day: str) -> tuple[str, int, dict[str, int]]:
    topics = site.get("seed_topics") or []
    if not topics:
        return "", 0, {}
    ranked = []
    for topic in topics:
        score, breakdown = _golden_keyword_score(topic, site)
        tie = hashlib.sha256(f"{site['site_id']}:{day}:{topic}".encode()).hexdigest()
        ranked.append((score, tie, topic, breakdown))
    score, _, topic, breakdown = max(ranked)
    return topic, score, breakdown


def build_plan(now: datetime | None = None) -> dict:
    now = now or datetime.now(KST)
    cfg = load_config()
    day = now.date().isoformat()
    run_key = os.environ.get("TISTORY_RUN_KEY", "").strip() or day
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", run_key):
        raise ValueError("TISTORY_RUN_KEY must contain only letters, numbers, dot, underscore or hyphen")
    jobs = []
    enabled_sites = sorted(
        (site for site in cfg["sites"] if site.get("launch_enabled") is True),
        key=lambda site: int(site.get("launch_order", 999)),
    )
    for site in enabled_sites:
        seed_topic, keyword_score, keyword_breakdown = _pick_seed_topic(site, day)
        jobs.append({
            "job_id": f"{site['site_id']}:{run_key}",
            "site_id": site["site_id"],
            "title": site["title"],
            "language": site["language"],
            "audience": site["audience"],
            "description": site.get("description", ""),
            "url": site.get("url", ""),
            "launch_order": site.get("launch_order"),
            "scheduled_local_time": _pick_time(site, day),
            "publish_policy": cfg.get("default_publish_policy", "awaiting_approval"),
            "duplicate_guard": True,
            "trend_mode": bool(site.get("trend_mode")),
            "official_source_required": bool(site.get("official_source_required")),
            "official_sources": site.get("official_sources", []),
            "categories": site.get("categories", []),
            "intent": site.get("intent", []),
            "seed_topic": seed_topic,
            "keyword_selection": "golden_keyword_score",
            "keyword_score": keyword_score,
            "keyword_score_breakdown": keyword_breakdown,
            "status": "PLANNED",
            "public_allowed": False,
            "notes": "Create a new search intent, title, outline, examples and FAQ for this platform. Copying sentences, paragraphs or another platform's outline is forbidden. Queue for review; no automatic public publishing."
        })
    return {
        "generated_at": now.isoformat(),
        "date": day,
        "run_key": run_key,
        "timezone": "Asia/Seoul",
        "daily_posts_per_site": 1,
        "portfolio_sites": len(cfg["sites"]),
        "enabled_sites": len(enabled_sites),
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
