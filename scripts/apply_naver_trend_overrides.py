#!/usr/bin/env python3
"""Apply a completed same-day Naver trend brief to the persisted daily plan."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
KST = ZoneInfo("Asia/Seoul")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def apply_overrides(plan: dict, brief: dict, applied_at: datetime | None = None) -> tuple[dict, int]:
    if plan.get("date") != brief.get("date"):
        raise ValueError("plan and trend brief dates do not match")
    if brief.get("status") != "COMPLETE":
        raise ValueError("trend brief is not complete")

    candidates = {int(item["rank"]): item for item in brief.get("candidates", [])}
    overrides = brief.get("recommended_plan_overrides", {})
    changed = 0

    for site_id, ranks in overrides.items():
        jobs = sorted(
            (job for job in plan.get("jobs", []) if job.get("site_id") == site_id),
            key=lambda job: job["scheduled_local_time"],
        )
        if len(jobs) != len(ranks):
            raise ValueError(f"{site_id} has {len(jobs)} jobs but {len(ranks)} overrides")

        for job, rank in zip(jobs, ranks):
            candidate = candidates.get(int(rank))
            if candidate is None:
                raise ValueError(f"missing candidate rank {rank}")
            status = str(candidate.get("status", ""))
            if status.startswith("HOLD_") or "LOW_RELEVANCE" in status:
                raise ValueError(f"candidate rank {rank} is blocked: {status}")
            if site_id not in candidate.get("site_ids", []):
                raise ValueError(f"candidate rank {rank} is not approved for {site_id}")
            if job.get("status") != "RESEARCH_REQUIRED":
                raise ValueError(f"cannot replace started job {job.get('job_id')}")

            query = candidate["query"]
            encoded = quote_plus(query)
            desired = {
                "cluster": candidate["cluster"],
                "base_query": query,
                "title_seed": f"{query}｜오늘 확인할 공식 정보",
                "trend_candidate_rank": int(rank),
                "trend_signal": candidate["signal"],
                "trend_source_status": status,
                "topic_source": f"data/naver-trend-brief/{brief['date']}.json",
            }
            if any(job.get(key) != value for key, value in desired.items()):
                changed += 1
            job.update(desired)
            job.pop("catalog_keyword_id", None)
            research = job.setdefault("research", {})
            research.update({
                "naver_search": f"https://search.naver.com/search.naver?query={encoded}",
                "naver_news": f"https://search.naver.com/search.naver?where=news&query={encoded}",
                "official_sources": candidate["official_sources"],
            })

    now = applied_at or datetime.now(KST)
    plan["trend_brief_path"] = f"data/naver-trend-brief/{brief['date']}.json"
    plan["trend_brief_generated_at"] = brief.get("generated_at")
    plan["trend_brief_applied_at"] = now.astimezone(KST).isoformat()
    plan["trend_override_count"] = sum(len(ranks) for ranks in overrides.values())
    return plan, changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="KST date in YYYY-MM-DD format")
    parser.add_argument("--plan")
    parser.add_argument("--brief")
    args = parser.parse_args()

    plan_path = Path(args.plan) if args.plan else ROOT / "data" / "naver-daily-plans" / f"{args.date}.json"
    brief_path = Path(args.brief) if args.brief else ROOT / "data" / "naver-trend-brief" / f"{args.date}.json"
    plan, changed = apply_overrides(load_json(plan_path), load_json(brief_path))
    temporary = plan_path.with_suffix(plan_path.suffix + ".tmp")
    temporary.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(plan_path)
    print(json.dumps({"date": args.date, "changed_jobs": changed, "total_overrides": plan["trend_override_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
